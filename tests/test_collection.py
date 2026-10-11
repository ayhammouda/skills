"""Acceptance failures must be observable through the same check used by CI."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate import validate_collection


class CollectionChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skills-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "example"
        self.skill.mkdir()
        shutil.copyfile(ROOT / "LICENSE", self.root / "LICENSE")
        shutil.copyfile(ROOT / "LICENSE", self.skill / "LICENSE")
        (self.root / "README.md").write_text("[Example](example/SKILL.md)\n")
        self.valid = "---\nname: example\ndescription: Use when testing a skill.\nlicense: MIT\n---\n# Example\nDo the requested task.\n"
        (self.skill / "SKILL.md").write_text(self.valid)

    def problems(self):
        return "\n".join(validate_collection(self.root))

    def test_real_collection(self):
        self.assertEqual(validate_collection(ROOT), [])

    def test_minimal_and_multiline_metadata(self):
        self.assertEqual(self.problems(), "")
        (self.skill / "SKILL.md").write_text(self.valid.replace(
            "description: Use when testing a skill.", "description: >\n  Use when testing\n  a skill."))
        self.assertEqual(self.problems(), "")

    def test_invalid_metadata_is_rejected(self):
        mutations = [
            ("name: example", "name: Wrong", "name"),
            ("name: example", "name: ex--ample", "name"),
            ("name: example", "name: example_", "name"),
            ("description: Use when testing a skill.", "description: false", "description"),
            ("description: Use when testing a skill.", "description: ''", "description"),
            ("description: Use when testing a skill.", "description: " + "x" * 1025, "description"),
            ("license: MIT", "license: Proprietary", "license"),
            ("license: MIT", "licence: MIT", "licence"),
            ("name: example", "name: example\nname: second", "duplicate"),
            ("name: example", "name: !!python/object:object {}", "YAML"),
            ("license: MIT", "license: MIT\nmetadata:\n  version: 1", "metadata"),
            ("license: MIT", "license: MIT\ncompatibility: " + "x" * 501, "compatibility"),
        ]
        for old, new, expected in mutations:
            with self.subTest(expected=expected, new=new[:80]):
                (self.skill / "SKILL.md").write_text(self.valid.replace(old, new))
                self.assertIn(expected, self.problems())

    def test_missing_or_empty_entrypoint(self):
        for content in ["# No frontmatter", "---\n- example\n---\nBody", self.valid.split("# Example")[0]]:
            with self.subTest(content=content):
                (self.skill / "SKILL.md").write_text(content)
                self.assertTrue(self.problems())
        (self.skill / "SKILL.md").unlink()
        self.assertIn("No skills", self.problems())

    def test_root_entrypoint_would_hide_collection(self):
        (self.root / "SKILL.md").write_text(self.valid)
        self.assertIn("collection root", self.problems())

    def test_package_license_must_travel(self):
        (self.skill / "LICENSE").unlink()
        self.assertIn("LICENSE", self.problems())

    def test_catalog_covers_discovered_skills(self):
        (self.root / "README.md").write_text("# Empty catalog\n")
        self.assertIn("catalog", self.problems())

    def test_markdown_links_and_images_are_checked(self):
        (self.skill / "SKILL.md").write_text(self.valid + "\n[Missing](references/missing.md)\n![Missing](assets/chart.png)\n")
        self.assertIn("references/missing.md", self.problems())
        self.assertIn("assets/chart.png", self.problems())

    def test_reference_links_are_parsed_and_code_examples_ignored(self):
        (self.skill / "SKILL.md").write_text(self.valid + "\n[Guide][guide]\n\n[guide]: missing.md\n")
        self.assertIn("missing.md", self.problems())
        (self.skill / "SKILL.md").write_text(self.valid + "\n```md\n[Example](not-a-file.md)\n```\n")
        self.assertEqual(self.problems(), "")

    def test_supporting_documents_cannot_escape_the_package(self):
        refs = self.skill / "references"
        refs.mkdir()
        (refs / "guide.md").write_text("[Other](../../README.md)\n")
        self.assertIn("escapes skill", self.problems())

    def test_encoded_paths_and_anchors(self):
        (self.skill / "guide with spaces.md").write_text("# Guide\n")
        (self.skill / "SKILL.md").write_text(self.valid + "\n[Guide](guide%20with%20spaces.md#guide)\n")
        self.assertEqual(self.problems(), "")

    def test_absolute_paths_are_not_portable(self):
        (self.skill / "SKILL.md").write_text(self.valid + "\n[Local](/tmp/private.md)\n")
        self.assertIn("absolute", self.problems())

    def test_symlink_files_and_directories_are_rejected(self):
        for target in [self.root / "README.md", self.root]:
            link = self.skill / "outside"
            with self.subTest(target=target):
                link.symlink_to(target)
                self.assertIn("symlink", self.problems())
                link.unlink()

    def test_symlink_entrypoint_is_not_read(self):
        (self.skill / "SKILL.md").unlink()
        (self.skill / "SKILL.md").symlink_to(self.root / "missing")
        self.assertIn("symlink", self.problems())

    def test_generated_files_do_not_ship(self):
        (self.skill / "__pycache__").mkdir()
        self.assertIn("__pycache__", self.problems())

    def test_ignored_local_files_do_not_ship(self):
        subprocess.run(["git", "-C", str(self.root), "init", "--template=", "--initial-branch=main"],
                       check=True, capture_output=True, timeout=20)
        (self.root / ".gitignore").write_text("example/private.txt\n")
        (self.skill / "private.txt").write_text("Synthetic local-only data")
        self.assertIn("ignored package files", self.problems())

    def test_third_skill_is_discovered_without_a_registry(self):
        other = self.root / "another"
        shutil.copytree(self.skill, other)
        (other / "SKILL.md").write_text(self.valid.replace("name: example", "name: another"))
        (self.root / "README.md").write_text("[Example](example/SKILL.md)\n[Another](another/SKILL.md)\n")
        self.assertEqual(self.problems(), "")


if __name__ == "__main__":
    unittest.main()
