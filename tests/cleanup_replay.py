"""Fixed, reviewed actions for the synthetic fixture. This is not a cleanup tool.

The fixture owns every path and remote. Tests replay the recorded action plan;
they do not ask a model to interpret SKILL.md or classify an arbitrary project.
"""
from pathlib import Path
import os
import tarfile

from cleanup_fixture import ENV, OPERATIONS, digest, git, review_snapshot, snapshot


def audit(state):
    project = Path(state["project"])
    git(project, "worktree", "list", "--porcelain", "-z")
    git(project, "for-each-ref", "--format=%(refname)%00%(objectname)%00%(upstream)", "refs/heads/")
    for path in state["trees"].values():
        wt = Path(path)
        if wt.exists():
            git(wt, "status", "--porcelain=v1", "-z", "--untracked-files=normal",
                "--ignored=traditional", "--ignore-submodules=none")
            git(wt, "ls-files", "-v", "-z")
            for operation in OPERATIONS:
                git(wt, "rev-parse", "--path-format=absolute", "--git-path", operation)


def apply_reviewed_files(state):
    # Any changed evidence invalidates this fixed action plan before its first write.
    assert snapshot(state) == state["before"], "Candidate evidence changed; reassess"
    assert review_snapshot(state) == state["review_before"], "Git evidence changed; reassess"
    root, project = Path(state["root"]), Path(state["project"])
    retired = Path(state["trees"]["retired worktree"])
    recovery = root / "recovery"
    recovery.mkdir(mode=0o700)
    archive_path = recovery / "temporary-ai-files.tar"
    fd = os.open(archive_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    sources = {}
    with os.fdopen(fd, "wb") as stream, tarfile.open(fileobj=stream, mode="w") as archive:
        for name, expected in state["removed_untracked"].items():
            tree, relative = name.split("/", 1)
            source = (project if tree == "project" else retired) / relative
            assert source.is_file() and not source.is_symlink()
            assert digest(source.read_bytes()) == expected
            sources[name] = source
            archive.add(source, arcname=name, recursive=False)
    with tarfile.open(archive_path) as archive:
        assert set(archive.getnames()) == set(sources)
        for name, expected in state["removed_untracked"].items():
            assert digest(archive.extractfile(name).read()) == expected

    architecture = project / "docs/architecture.md"
    architecture.write_text(architecture.read_text() + """
The entrypoint is src/app.py and its greeting function is greet(name).
The implementation uses the Python standard library so it works offline.
scripts/ai-healthcheck.py loads the entrypoint with runpy and verifies greet('Ada').
Decision: keep the implementation usable offline.
Rejected alternative: a network service adds deployment and network requirements.
Unresolved: personalized greetings have not been designed.
""")
    (project / "docs/getting-started.md").write_text("""# Getting started

Use Python 3. No third-party dependencies are needed.

- Run: `python3 -B src/app.py` prints Hello, World!
- Test: `python3 -B -m unittest discover -s tests`
- Check: `python3 -B scripts/ai-healthcheck.py`
""")
    readme = project / "README.md"
    readme.write_text(readme.read_text().replace("notes/AI-HANDOFF.md", "docs/getting-started.md"))
    for source in sources.values():
        source.unlink()
    for name in state["removed_tracked"]:
        assert (project / name).read_bytes() == git(project, "show", state["initial"] + ":" + name).stdout
        (project / name).unlink()
    git(project, "worktree", "remove", "--", str(retired))
    git(project, "worktree", "remove", "--", str(root / "missing-retired"))


def operation_active(state):
    project = Path(state["project"])
    common = Path(git(project, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.decode().strip())
    directories = [common, *(common / "worktrees").iterdir()]
    return any((directory / marker).exists() for directory in directories for marker in OPERATIONS)


def delete_fixture_branch(state, branch="finished-task", *, authorized=False):
    if not authorized or operation_active(state):
        return False
    if branch in {"main", "develop"} or branch.startswith("release/"):
        return False
    project, remote = Path(state["project"]), Path(state["remote"])
    full_ref = "refs/heads/" + branch
    if (b"branch " + full_ref.encode()) in git(project, "worktree", "list", "--porcelain", "-z").stdout.split(b"\0"):
        return False
    oid = git(project, "rev-parse", "--verify", full_ref).stdout.strip()

    def upstream():
        values = []
        for key in ["remote", "merge"]:
            result = git(project, "config", "--null", "--get-all", f"branch.{branch}.{key}", ok=False)
            parts = result.stdout.rstrip(b"\0").split(b"\0")
            if result.returncode or len(parts) != 1 or not parts[0]:
                return None
            values.append(parts[0].decode())
        return tuple(values)

    config = upstream()
    if config is None or config[0] != "origin" or not config[1].startswith("refs/heads/"):
        return False
    if git(project, "remote", "get-url", config[0]).stdout.decode().strip() != str(remote):
        return False

    def absent():
        result = git(project, "ls-remote", "--exit-code", "--refs", *config, ok=False)
        return result.returncode == 2 and not result.stdout

    if not absent():
        return False
    trace = Path(state["root"]) / "fetch-trace.jsonl"
    git(project, "fetch", "--no-auto-maintenance", "--no-prune", "--no-prune-tags",
        "--no-tags", "--recurse-submodules=no", "--refmap=", config[0], "refs/heads/main",
        env={**ENV, "GIT_TRACE2_EVENT": str(trace)})
    target = git(project, "rev-parse", "--verify", "FETCH_HEAD^{commit}").stdout.strip()
    if git(project, "merge-base", "--is-ancestor", oid.decode(), target.decode(), ok=False).returncode:
        return False
    if (operation_active(state) or upstream() != config or not absent()
            or git(project, "rev-parse", "--verify", full_ref).stdout.strip() != oid):
        return False
    if (b"branch " + full_ref.encode()) in git(project, "worktree", "list", "--porcelain", "-z").stdout.split(b"\0"):
        return False
    common = Path(git(project, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.decode().strip())
    expected = Path(state["root"]) / "expected-config"
    expected.write_bytes((common / "config").read_bytes())
    git(project, "config", "--file", str(expected), "--remove-section", "branch." + branch)
    state["expected_config_after_branch_deletion"] = digest(expected.read_bytes())
    git(project, "branch", "-d", "--", branch)
    return True
