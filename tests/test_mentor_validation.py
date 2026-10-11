"""Exercise the packaged validator against corrupted copies, never user files."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MentorValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-validation-")
        self.addCleanup(self.temp.cleanup)
        self.skill = Path(self.temp.name) / "mentor"
        shutil.copytree(ROOT / "mentor", self.skill)

    def run_validator(self):
        return subprocess.run(["node", str(self.skill / "scripts/validate.mjs")],
                              cwd=self.temp.name, capture_output=True, text=True, timeout=20)

    def rejected(self):
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, "Corrupt package incorrectly passed")

    def test_valid_standalone_package(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_broken_schema_reference(self):
        path = self.skill / "references/schema.json"
        path.write_text(path.read_text().replace("#/$defs/resource", "#/$defs/missing"))
        self.rejected()

    def test_duplicate_evaluation_ids(self):
        path = self.skill / "evals/evals.json"
        data = json.loads(path.read_text())
        data["evals"][1]["id"] = data["evals"][0]["id"]
        path.write_text(json.dumps(data))
        self.rejected()

    def test_malformed_json(self):
        (self.skill / "evals/evals.json").write_text("{broken")
        self.rejected()

    def test_unknown_mode(self):
        path = self.skill / "examples/example-output-rust.md"
        path.write_text(path.read_text().replace("[Read first]", "[Unrecognized mode]", 1))
        self.rejected()

    def test_invalid_resource_line_does_not_disappear(self):
        path = self.skill / "examples/example-output-rust.md"
        path.write_text(path.read_text().replace("https://github.com/rust-lang/rustlings", "not-a-url", 1))
        self.rejected()

    def test_malformed_explore_later_resource_does_not_disappear(self):
        path = self.skill / "examples/example-output-rust.md"
        path.write_text(path.read_text().replace("https://doc.rust-lang.org/nomicon/", "not-a-url", 1))
        self.rejected()

    def test_missing_iteration_field(self):
        path = self.skill / "examples/example-output-rust.md"
        path.write_text(re.sub(r"^- \*\*Stop before:\*\*.*\n", "", path.read_text(), count=1, flags=re.M))
        self.rejected()


if __name__ == "__main__":
    unittest.main()
