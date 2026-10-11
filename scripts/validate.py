#!/usr/bin/env python3
"""Validate the collection; all executable checks use disposable projects."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

try:
    import yaml
    from markdown_it import MarkdownIt
except ImportError as error:
    raise SystemExit("Install validation dependencies: python -m pip install -r requirements-dev.txt") from error

ROOT = Path(__file__).resolve().parents[1]
SKILLS_CLI = "1.7.2"
AGENTS = ["codex", "claude-code", "github-copilot", "cursor", "gemini-cli",
          "opencode", "windsurf", "cline", "roo", "amp", "antigravity", "antigravity-cli"]
FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
GENERATED = {".git", "node_modules", "__pycache__", ".DS_Store"}


def run_command(command, *, cwd, env=None, timeout=300):
    # Each check owns its process group, so a timeout cannot leave installers running.
    with subprocess.Popen(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


class UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise yaml.YAMLError("mapping keys must be strings")
            if key in mapping:
                raise yaml.YAMLError(f"duplicate key: {key}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def discover_skills(root):
    return sorted(p for p in root.iterdir() if p.is_dir() and
                  ((p / "SKILL.md").is_file() or (p / "SKILL.md").is_symlink()))


def markdown_targets(text):
    def walk(tokens):
        for token in tokens:
            if token.type in {"link_open", "image"}:
                yield token.attrGet("href" if token.type == "link_open" else "src")
            if token.children:
                yield from walk(token.children)
    return list(walk(MarkdownIt("commonmark").parse(text)))


def link_problems(document, text, scope, label):
    problems = []
    for target in markdown_targets(text):
        parts = urlsplit(target)
        if parts.scheme or parts.netloc:
            if parts.scheme not in {"https", "http", "mailto"}:
                problems.append(f"{label}: unsupported link {target}")
            continue
        name = unquote(parts.path)
        if not name:
            continue
        if Path(name).is_absolute():
            problems.append(f"{label}: absolute link is not portable: {target}")
            continue
        destination = (document.parent / name).resolve()
        if not destination.is_relative_to(scope.resolve()):
            problems.append(f"{label}: link escapes skill/repository: {target}")
        elif not destination.exists():
            problems.append(f"{label}: missing link target: {target}")
    return problems


def validate_collection(root):
    root = Path(root)
    problems = []
    if (root / "SKILL.md").exists():
        problems.append("Do not put SKILL.md at the collection root; it can hide child skills.")
    skills = discover_skills(root)
    if not skills:
        problems.append("No skills found; each top-level skill needs SKILL.md.")
    elif (root / ".git").exists():
        ignored = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--others", "--ignored", "--exclude-standard",
             "-z", "--", *(p.name for p in skills)])
        problems.extend(f"{os.fsdecode(name)}: ignored package files must not ship"
                        for name in ignored.split(b"\0") if name)
    readme = root / "README.md"
    catalog = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    catalog_targets = {unquote(urlsplit(t).path) for t in markdown_targets(catalog)}
    root_license = (root / "LICENSE").read_text(encoding="utf-8")
    mit_terms = root_license.split("Permission is hereby granted", 1)[-1].strip()
    for skill in skills:
        if skill.is_symlink():
            problems.append(f"{skill.name}: skill directory is a symlink")
            continue
        if f"{skill.name}/SKILL.md" not in catalog_targets:
            problems.append(f"{skill.name}: missing from README catalog")
        files = []
        for directory, dirs, names in os.walk(skill, followlinks=False):
            for name in [*dirs, *names]:
                path = Path(directory) / name
                if path.is_symlink():
                    problems.append(f"{path.relative_to(root)}: package symlink is not portable")
                elif name in GENERATED or path.suffix in {".pyc", ".pyo"}:
                    problems.append(f"{path.relative_to(root)}: generated/private files must not ship")
                elif path.is_file():
                    files.append(path)
            dirs[:] = [d for d in dirs if d not in GENERATED and not (Path(directory) / d).is_symlink()]
        entrypoint = skill / "SKILL.md"
        if entrypoint not in files:
            continue
        text = entrypoint.read_text(encoding="utf-8")
        match = re.fullmatch(r"---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)", text, re.S)
        if not match:
            problems.append(f"{skill.name}: SKILL.md needs delimited YAML frontmatter")
            continue
        try:
            metadata = yaml.load(match[1], Loader=UniqueSafeLoader)
        except yaml.YAMLError as error:
            problems.append(f"{skill.name}: invalid YAML: {error}")
            continue
        if not isinstance(metadata, dict):
            problems.append(f"{skill.name}: frontmatter must be a mapping")
            continue
        for field in sorted(set(metadata) - FIELDS):
            problems.append(f"{skill.name}: unexpected frontmatter field {field}")
        name = metadata.get("name")
        if (not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
                or len(name) > 64 or name != skill.name):
            problems.append(f"{skill.name}: invalid name or directory mismatch")
        description = metadata.get("description")
        if not isinstance(description, str) or not description.strip() or len(description) > 1024:
            problems.append(f"{skill.name}: description must contain 1–1024 characters")
        if metadata.get("license") != "MIT":
            problems.append(f"{skill.name}: this collection requires license: MIT")
        for field, limit in [("compatibility", 500), ("allowed-tools", None)]:
            if field in metadata:
                value = metadata[field]
                if not isinstance(value, str) or not value.strip() or (limit and len(value) > limit):
                    problems.append(f"{skill.name}: invalid {field}")
        if "metadata" in metadata:
            extra = metadata["metadata"]
            if not isinstance(extra, dict) or any(not isinstance(v, str) for v in extra.values()):
                problems.append(f"{skill.name}: metadata must map string keys to string values")
        if not match[2].strip():
            problems.append(f"{skill.name}: instructions are empty")
        if len(text.splitlines()) > 500:
            problems.append(f"{skill.name}: collection authoring policy limits SKILL.md to 500 lines")
        license_file = skill / "LICENSE"
        if license_file not in files:
            problems.append(f"{skill.name}: missing bundled LICENSE")
        else:
            license_text = license_file.read_text(encoding="utf-8")
            if ("Copyright" not in license_text or "MIT License" not in license_text
                    or "Permission is hereby granted" not in license_text
                    or license_text.split("Permission is hereby granted", 1)[-1].strip() != mit_terms):
                problems.append(f"{skill.name}: LICENSE must preserve attribution and the complete MIT terms")
        for document in files:
            if document.suffix == ".md":
                body = match[2] if document == entrypoint else document.read_text(encoding="utf-8")
                problems.extend(link_problems(document, body, skill, str(document.relative_to(root))))
    documents = [*root.glob("*.md"), *root.glob("docs/**/*.md")]
    for document in documents:
        problems.extend(link_problems(document, document.read_text(encoding="utf-8"), root,
                                      str(document.relative_to(root))))
    return problems


def package_hashes(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def check_installation(root):
    expected = {p.name: package_hashes(p) for p in discover_skills(root)}
    lock = Path.home() / ".agents/.skill-lock.json"
    before = lock.read_bytes() if lock.exists() else None
    env = {**os.environ, "DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1", "CI": "1"}
    evidence = []
    try:
        with tempfile.TemporaryDirectory(prefix="skills-install-") as temporary:
            fixture = Path(temporary).resolve()
            for mode in ["symlink", "copy"]:
                project = fixture / mode
                project.mkdir()
                command = ["npx", "--yes", f"skills@{SKILLS_CLI}", "add", str(root),
                           "--skill", "*", "--agent", *AGENTS, "--yes", "--json"]
                if mode == "copy":
                    command.append("--copy")
                result = run_command(command, cwd=project, env=env, timeout=180)
                if result.returncode:
                    raise RuntimeError(result.stdout + result.stderr)
                records = json.loads(result.stdout)
                if len(records) != len(expected) or {r["name"] for r in records} != set(expected):
                    raise RuntimeError("Installer discovery differs from the complete collection")
                for record in records:
                    if (record["status"] != "installed" or record["scope"] != "project"
                            or record["mode"] != mode or len(set(record["agents"])) != len(AGENTS)):
                        raise RuntimeError(f"Incomplete installation: {record}")
                found = set()
                count = 0
                for base, _, files in os.walk(project, followlinks=True):
                    target = Path(base)
                    if not target.resolve().is_relative_to(fixture):
                        raise RuntimeError("Installer created a link outside the disposable project")
                    if "SKILL.md" not in files:
                        continue
                    if target.name not in expected or package_hashes(target) != expected[target.name]:
                        raise RuntimeError(f"Installed package differs: {target.relative_to(project)}")
                    found.add(target.name)
                    count += 1
                if found != set(expected):
                    raise RuntimeError("Not all installed skill directories were found")
                for name in expected:
                    if (project / ".claude/skills" / name).is_symlink() != (mode == "symlink"):
                        raise RuntimeError("Requested installation mode was not exercised")
                    for destination in [".agents/skills", ".claude/skills", ".roo/skills", ".windsurf/skills"]:
                        if package_hashes(project / destination / name) != expected[name]:
                            raise RuntimeError(f"Missing/incomplete destination: {destination}/{name}")
                evidence.append({"mode": mode, "agents": AGENTS, "packages": sorted(found),
                                 "directories_verified": count})
    finally:
        if (lock.read_bytes() if lock.exists() else None) != before:
            raise RuntimeError("Global installer lock changed during project-scoped validation")
    return {"cli_version": SKILLS_CLI, "runs": evidence, "source": "local checkout",
            "fixtures_disposed": True, "global_lock_unchanged": True}


def source_identity(root):
    def git(*args):
        return subprocess.check_output(["git", "--no-optional-locks", "-C", str(root), *args])
    names = git("ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")
    hashes = {}
    for name in sorted(set(n for n in names if n)):
        relative = os.fsdecode(name)
        path = root / relative
        hashes[relative] = (hashlib.sha256(path.read_bytes()).hexdigest()
                            if path.is_file() and not path.is_symlink()
                            and path.resolve().is_relative_to(root.resolve()) else "absent-or-symlink")
    state = {
        "index": ("ls-files", "--stage", "-v", "-z"),
        "status": ("status", "--porcelain=v2", "-z", "--untracked-files=all"),
        "refs": ("for-each-ref", "--format=%(refname) %(objectname)"),
        "local_config": ("config", "--local", "--null", "--list"),
    }
    config = Path(git("rev-parse", "--path-format=absolute", "--git-path", "config.worktree").decode().strip())
    return {"commit": git("rev-parse", "HEAD").decode().strip(),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD").decode().strip(),
            "dirty": bool(git("status", "--porcelain", "--untracked-files=all")),
            "git_state_sha256": {name: hashlib.sha256(git(*args)).hexdigest()
                                 for name, args in state.items()},
            "worktree_config_sha256": hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None,
            "sha256": hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Also exercise the pinned Skills CLI (network/cache required)")
    parser.add_argument("--report", type=Path, help="Write JSON evidence outside this checkout")
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without -O or PYTHONOPTIMIZE so outcome assertions are enabled")
    if args.report and args.report.resolve().is_relative_to(ROOT):
        parser.error("--report must be outside the checkout so it cannot change the tested inputs")
    identity = source_identity(ROOT)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "source": identity,
              "python": sys.version, "stages": [], "status": "failed",
              "evidence_kind": "deterministic checks and scripted fixture replay; no model evaluation"}
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PYTHONOPTIMIZE", None)
    stage = "collection metadata, resources, licenses, and catalog"
    try:
        problems = validate_collection(ROOT)
        if problems:
            raise RuntimeError("\n".join(problems))
        report["stages"].append({"name": stage, "status": "passed"})
        stage = "runtime availability"
        report["runtime"] = {"platform": platform.platform(), "python": sys.version}
        for tool in ["git", "node"]:
            version = run_command([tool, "--version"], cwd=ROOT, env=env, timeout=15)
            if version.returncode:
                raise RuntimeError(version.stderr)
            report["runtime"][tool] = version.stdout.strip()
        report["stages"].append({"name": stage, "status": "passed"})
        for stage, command in [
            ("Mentor packaged content", ["node", "mentor/scripts/validate.mjs"]),
            ("regressions and disposable cleanup replay",
             [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ]:
            result = run_command(command, cwd=ROOT, env=env, timeout=300)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            output = result.stdout + result.stderr
            if stage.startswith("regressions") and (
                re.search(r"^Ran 0 tests?\b", output, re.M)
                or re.search(r"^OK \(.*skipped=[1-9]", output, re.M)
            ):
                raise RuntimeError("Required regressions were empty or skipped:\n" + output)
            report["stages"].append({"name": stage, "status": "passed",
                                     "output": output.strip()})
        if args.install:
            stage = "installed package delivery"
            details = check_installation(ROOT)
            report["stages"].append({"name": stage, "status": "passed", "details": details})
        stage = "source preservation"
        if source_identity(ROOT) != identity:
            raise RuntimeError("Validation changed source files or repository state")
        report["stages"].append({"name": stage, "status": "passed"})
        report["status"] = "passed"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report["stages"].append({"name": stage, "status": "failed", "error": str(error)})
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for result in report["stages"]:
        print(f"{result['status'].upper()}: {result['name']}", flush=True)
        if "error" in result:
            print(result["error"], file=sys.stderr)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
