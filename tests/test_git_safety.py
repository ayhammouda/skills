"""Disposable Git recipe checks; these do not prove an agent follows the skill."""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "clean-project/references/git-safety.md"


class GitSafety(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="clean-project-review-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "repo"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_TERMINAL_PROMPT="0", GIT_EDITOR="true",
                        GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
                        GIT_AUTHOR_EMAIL="fixture@example.invalid",
                        GIT_COMMITTER_EMAIL="fixture@example.invalid")
        self.git("init", "-b", "main", "--template=", str(self.repo), cwd=self.root)
        (self.repo / "settings").write_text("default\n")
        (self.repo / ".gitignore").write_text("vendor/\n*.o\n")
        self.git("add", ".")
        self.git("commit", "-m", "initial")

    def run_command(self, argv, cwd=None, env=None, check=True):
        result = subprocess.run(argv, cwd=cwd or self.repo, env=env or self.env,
                                capture_output=True, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result

    def git(self, *args, cwd=None, env=None, check=True):
        return self.run_command(["git", *args], cwd, env, check)

    def recipe(self, needle, **values):
        lines = [line for line in REFERENCE.read_text().splitlines()
                 if line.startswith(("git ", "find ")) and needle in line]
        self.assertEqual(len(lines), 1, f"Expected one documented recipe for {needle!r}")
        values = {"repo": self.repo, "wt": self.repo, **values}
        argv = shlex.split(lines[0])
        return [re.sub(r"\$([a-z_]+)", lambda m: str(values[m[1]]), arg) for arg in argv]

    def worktree(self, name):
        path = self.root / name
        self.git("worktree", "add", "-b", name, str(path))
        return path

    def overview(self, wt):
        return self.run_command(self.recipe(" status ", wt=wt)).stdout

    def test_flagged_edits_are_visible_even_when_status_is_clean(self):
        for flag, tag in [("skip-worktree", b"S"), ("assume-unchanged", b"h")]:
            with self.subTest(flag=flag):
                wt = self.worktree(flag)
                self.git("update-index", "--" + flag, "settings", cwd=wt)
                (wt / "settings").write_text("unique local override\n")
                self.assertEqual(self.git("status", "--porcelain", cwd=wt).stdout, b"")
                flags = self.run_command(self.recipe(" ls-files ", wt=wt)).stdout.split(b"\0")
                self.assertIn(tag + b" settings", flags)
                self.assertEqual((wt / "settings").read_text(), "unique local override\n")
                # Characterize why ordinary removal is not a data-preservation check.
                self.git("worktree", "remove", "--", str(wt))
                self.assertFalse(wt.exists())

    def test_sparse_absence_differs_from_present_flagged_data(self):
        wt = self.worktree("sparse")
        self.git("update-index", "--skip-worktree", "settings", cwd=wt)
        (wt / "settings").unlink()
        flags = self.run_command(self.recipe(" ls-files ", wt=wt)).stdout
        self.assertIn(b"S settings\0", flags)
        self.assertFalse(os.path.lexists(wt / "settings"))

    def test_nested_repository_markers_include_ignored_directories(self):
        wt = self.worktree("nested")
        nested = wt / "vendor/lib"
        self.git("init", "--template=", str(nested))
        self.git("commit", "--allow-empty", "-m", "only copy", cwd=nested)
        linked = wt / "vendor/linked"
        self.git("worktree", "add", "--detach", str(linked), cwd=nested)
        self.assertEqual(self.git("status", "--porcelain", cwd=wt).stdout, b"")
        markers = self.run_command(self.recipe("find ", wt=wt)).stdout.split(b"\0")
        self.assertIn(os.fsencode(nested / ".git"), markers)
        self.assertIn(os.fsencode(linked / ".git"), markers)
        self.git("worktree", "remove", "--", str(wt))
        self.assertFalse(nested.exists(), "Git unexpectedly protected the ignored nested repo")

    def test_clean_paused_rebase_and_bisect_have_operation_state(self):
        editor = self.root / "edit-todo.py"
        editor.write_text("import pathlib,sys\np=pathlib.Path(sys.argv[1])\np.write_text(p.read_text().replace('pick ', 'edit ', 1))\n")
        for operation, marker in [("rebase", "rebase-merge"), ("bisect", "BISECT_LOG")]:
            with self.subTest(operation=operation):
                wt = self.worktree(operation)
                for i in range(2):
                    (wt / f"change{i}").write_text(str(i))
                    self.git("add", ".", cwd=wt)
                    self.git("commit", "-m", str(i), cwd=wt)
                if operation == "rebase":
                    env = {**self.env, "GIT_SEQUENCE_EDITOR": shlex.join([sys.executable, str(editor)])}
                    self.git("rebase", "-i", "main", cwd=wt, env=env)
                else:
                    self.git("bisect", "start", "HEAD", "main", cwd=wt)
                self.assertEqual(self.git("status", "--porcelain", cwd=wt).stdout, b"")
                path = self.run_command(self.recipe('--git-path "$operation"', wt=wt, operation=marker)).stdout
                self.assertTrue(Path(os.fsdecode(path.rstrip(b"\n"))).exists())

    def test_targeted_fetch_does_not_launch_maintenance_or_prune_tags(self):
        remote = self.root / "remote.git"
        self.git("clone", "--bare", str(self.repo), str(remote))
        self.git("remote", "add", "origin", str(remote))
        self.git("tag", "local-only")
        for key in ["fetch.prune", "fetch.pruneTags", "remote.origin.prune"]:
            self.git("config", key, "true")
        self.git("config", "--add", "remote.origin.fetch", "+refs/tags/*:refs/tags/*")
        trace = self.root / "fetch-trace.json"
        argv = self.recipe(" fetch ", target_remote="origin", target_ref="refs/heads/main")
        self.run_command(argv, env={**self.env, "GIT_TRACE2_EVENT": str(trace)})
        children = [event.get("argv", []) for line in trace.read_text().splitlines()
                    if (event := json.loads(line)).get("event") == "child_start"]
        self.assertFalse(any("maintenance" in args or "gc" in args for args in children), children)
        self.git("show-ref", "--verify", "refs/tags/local-only")
        self.assertEqual(self.git("rev-parse", "FETCH_HEAD").stdout, self.git("rev-parse", "main").stdout)

    def test_missing_removal_is_exact_and_keeps_locked_records(self):
        removed, retained, locked = (self.worktree(name) for name in ["removed", "retained", "locked"])
        self.git("worktree", "lock", "--reason", "offline", str(locked))
        for wt in [removed, retained, locked]:
            wt.rename(wt.with_name(wt.name + "-offline"))
        self.run_command(self.recipe('worktree remove -- "$missing_wt"', missing_wt=removed))
        output = self.git("worktree", "list", "--porcelain", "-z").stdout
        self.assertNotIn(b"worktree " + os.fsencode(removed) + b"\0", output)
        for wt in [retained, locked]:
            self.assertIn(b"worktree " + os.fsencode(wt) + b"\0", output)
        result = self.run_command(self.recipe('worktree remove -- "$missing_wt"', missing_wt=locked), check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_prune_without_expiry_includes_just_missing_record(self):
        wt = self.worktree("recent")
        wt.rename(self.root / "moved")
        immediate = self.git("worktree", "prune", "--dry-run", "--verbose")
        grace = self.git("worktree", "prune", "--dry-run", "--verbose", "--expire", "3.months.ago")
        self.assertIn(b"recent", immediate.stdout + immediate.stderr)
        self.assertEqual(grace.stdout + grace.stderr, b"")

    def test_ref_records_have_six_fields_and_exact_names(self):
        self.git("branch", "feature/finished")
        output = self.run_command(self.recipe(" for-each-ref ")).stdout
        records = [line.split(b"\0") for line in output.split(b"\n") if line]
        self.assertTrue(all(len(fields) == 6 for fields in records), records)
        self.assertEqual({fields[0] for fields in records}, {b"refs/heads/main", b"refs/heads/feature/finished"})
        self.assertEqual({fields[1] for fields in records}, {b"main", b"feature/finished"})

    def test_common_directories_match_only_for_related_worktrees(self):
        wt = self.worktree("linked")
        clone = self.root / "clone"
        self.git("clone", str(self.repo), str(clone))
        paths = []
        for repo in [self.repo, wt, clone]:
            output = self.run_command(self.recipe("--show-toplevel", repo=repo)).stdout
            common = Path(os.fsdecode(output.splitlines()[1]))
            self.assertTrue(common.is_absolute(), common)
            paths.append(common.resolve())
        self.assertEqual(paths[0], paths[1])
        self.assertNotEqual(paths[0], paths[2])

    def test_all_upstream_config_values_are_available(self):
        self.git("branch", "multi")
        for key, values in [("merge", ["refs/heads/gone", "refs/heads/main"]), ("remote", ["origin", "backup"])]:
            for value in values:
                self.git("config", "--add", "branch.multi." + key, value)
            result = self.run_command(self.recipe('"branch.$branch.' + key + '"', branch="multi"))
            self.assertEqual(result.stdout.rstrip(b"\0").split(b"\0"), [v.encode() for v in values])

    def test_overview_summarizes_ignored_and_untracked_directories(self):
        for dirname, suffix in [("build", ".o"), ("untracked", ".txt")]:
            folder = self.repo / dirname
            folder.mkdir()
            for i in range(200):
                (folder / f"{i}{suffix}").touch()
        self.assertEqual(set(self.overview(self.repo).split(b"\0")), {b"!! build/", b"?? untracked/", b""})

    def test_overview_does_not_refresh_index(self):
        tracked = self.repo / "settings"
        stat = tracked.stat()
        os.utime(tracked, ns=(stat.st_atime_ns, stat.st_mtime_ns - 10_000_000_000))
        index = self.repo / ".git/index"
        before = index.read_bytes()
        self.assertEqual(self.overview(self.repo), b"")
        self.assertEqual(index.read_bytes(), before)

    def test_install_preserves_existing_destinations(self):
        blocks = re.findall(r"```sh\n(.*?)```", (ROOT / "README.md").read_text(), re.S)
        install = next(block for block in blocks if "ln -s" in block)
        for kind in ["absent", "directory", "dangling", "installed"]:
            with self.subTest(kind=kind):
                fixture_home = self.root / kind
                dest = fixture_home / ".agents/skills/clean-project"
                dest.parent.mkdir(parents=True)
                checkout = self.root / (kind + "-checkout")
                source = checkout / "clean-project"
                source.mkdir(parents=True)
                (source / "SKILL.md").write_text("fixture")
                if kind == "directory":
                    dest.mkdir()
                    (dest / "keep").write_text("existing installation")
                elif kind == "dangling":
                    dest.symlink_to(fixture_home / "missing")
                elif kind == "installed":
                    dest.symlink_to(source)
                # Substitute only the documented HOME reference; keep the process HOME unchanged.
                script = install.replace('"$HOME/.agents/skills', '"' + str(fixture_home) + '/.agents/skills')
                self.assertNotIn("$HOME", script)
                for _ in range(2):
                    self.run_command(["sh", "-c", script], cwd=checkout)
                self.assertEqual({p.name for p in source.iterdir()}, {"SKILL.md"})
                if kind == "directory":
                    self.assertEqual({p.name for p in dest.iterdir()}, {"keep"})
                elif kind == "dangling":
                    self.assertEqual(os.readlink(dest), str(fixture_home / "missing"))
                else:
                    self.assertEqual(dest.resolve(), source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
