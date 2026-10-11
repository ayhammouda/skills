"""Check failure propagation, source identity, and bounded process lifetime."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate import run_command


class ValidationRunner(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="validation-runner-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "collection"
        self.root.mkdir()
        self.report = Path(self.temp.name) / "result.json"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        PYTHONDONTWRITEBYTECODE="1")
        files = {
            "README.md": "[Example](example/SKILL.md)\n",
            "example/SKILL.md": "---\nname: example\ndescription: Use when testing.\nlicense: MIT\n---\n# Example\nDo the task.\n",
            "mentor/scripts/validate.mjs": "console.log('Synthetic native check passed');\n",
            "tests/test_smoke.py": "import unittest\nclass Smoke(unittest.TestCase):\n def test_valid(self): self.assertTrue(True)\n",
        }
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        (self.root / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/validate.py", self.root / "scripts/validate.py")
        for name in ["LICENSE", "example/LICENSE"]:
            shutil.copyfile(ROOT / "LICENSE", self.root / name)
        self.git("init", "--template=", "--initial-branch=main")
        self.git("config", "user.name", "Validation fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")

    def git(self, *args):
        return subprocess.run(["git", "-c", "maintenance.auto=false", "-C", str(self.root), *args],
                              env=self.env, check=True, capture_output=True, timeout=20)

    def run_validation(self, *args, env=None):
        return run_command([sys.executable, "-B", "scripts/validate.py", "--report", str(self.report), *args],
                           cwd=self.root, env=env or self.env, timeout=30)

    def test_failed_native_check_cannot_produce_pass(self):
        (self.root / "mentor/scripts/validate.mjs").write_text("process.exit(7);\n")
        result = self.run_validation()
        report = json.loads(self.report.read_text())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["stages"][-1]["name"], "Mentor packaged content")
        self.assertEqual(report["stages"][-1]["status"], "failed")

    def test_dirty_inputs_are_identified_by_content(self):
        skill = self.root / "example/SKILL.md"
        skill.write_text(skill.read_text() + "\nAdditional instruction.\n")
        result = self.run_validation()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.report.read_text())
        self.assertTrue(report["source"]["dirty"])
        self.assertEqual(report["source"]["sha256"]["example/SKILL.md"], hashlib.sha256(skill.read_bytes()).hexdigest())

    def test_mutating_check_invalidates_evidence(self):
        (self.root / "tests/test_smoke.py").write_text(
            "from pathlib import Path\nimport unittest\nclass Mutation(unittest.TestCase):\n"
            " def test_mutation(self): Path('README.md').write_text('changed by test')\n")
        result = self.run_validation()
        self.assertEqual(result.returncode, 1)
        report = json.loads(self.report.read_text())
        self.assertEqual(report["stages"][-1]["name"], "source preservation")
        self.assertEqual(report["status"], "failed")

    def test_empty_or_skipped_suite_cannot_pass(self):
        for source in [
            "import unittest\n",
            "import unittest\n@unittest.skip('missing prerequisite')\n"
            "class Skipped(unittest.TestCase):\n def test_skipped(self): pass\n",
        ]:
            with self.subTest(source=source):
                (self.root / "tests/test_smoke.py").write_text(source)
                result = self.run_validation()
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(self.report.read_text())["status"], "failed")

    def test_git_only_mutations_invalidate_evidence(self):
        commands = [
            ["git", "add", "tests/test_smoke.py"],
            ["git", "config", "fixture.changed", "true"],
            ["git", "checkout", "-b", "unexpected"],
            ["git", "branch", "unexpected-ref"],
            ["git", "config", "extensions.worktreeConfig", "true"],
            ["git", "config", "--worktree", "fixture.changed", "true"],
        ]
        for command in commands:
            with self.subTest(command=command):
                (self.root / "tests/test_smoke.py").write_text(
                    "import subprocess, unittest\nclass Mutation(unittest.TestCase):\n"
                    f" def test_mutation(self): subprocess.run({command!r}, check=True, capture_output=True)\n")
                result = self.run_validation()
                report = json.loads(self.report.read_text())
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertEqual(report["stages"][-1]["name"], "source preservation")
                self.assertEqual(report["status"], "failed")

    def test_acceptance_from_linked_worktree(self):
        checkout = Path(self.temp.name) / "linked"
        self.git("worktree", "add", "--detach", str(checkout), "HEAD")
        result = run_command(
            [sys.executable, "-B", "scripts/validate.py", "--report", str(self.report)],
            cwd=checkout, env=self.env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.report.read_text())["status"], "passed")

    def test_report_cannot_modify_the_tested_checkout(self):
        self.report = self.root / "evidence.json"
        result = self.run_validation()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.report.exists())
        self.assertEqual(self.git("status", "--porcelain").stdout, b"")

    def test_optimized_python_is_rejected(self):
        result = self.run_validation(env={**self.env, "PYTHONOPTIMIZE": "1"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("outcome assertions", result.stderr)
        self.assertFalse(self.report.exists())

    def test_timeout_stops_descendants(self):
        started, late = Path(self.temp.name) / "started", Path(self.temp.name) / "late"
        child = ("from pathlib import Path; import time; "
                 f"Path({str(started)!r}).touch(); time.sleep(2); Path({str(late)!r}).touch()")
        parent = f"import subprocess,sys; subprocess.run([sys.executable, '-c', {child!r}])"
        with self.assertRaises(subprocess.TimeoutExpired):
            run_command([sys.executable, "-c", parent], cwd=self.root, env=self.env, timeout=1)
        self.assertTrue(started.exists(), "Child did not start; timeout test would be vacuous")
        time.sleep(1.2)
        self.assertFalse(late.exists(), "Timed-out child kept running")


if __name__ == "__main__":
    unittest.main()
