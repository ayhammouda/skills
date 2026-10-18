"""Ghostwriter script checks on synthetic fixtures.

These exercise corpus extraction, stylometrics, and profile validation. They do
not prove that an agent follows the skill or that a profile sounds like anyone.
"""

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "ghostwriter/scripts"


def load(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"ghostwriter_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(row if isinstance(row, str) else json.dumps(row))
            handle.write("\n")


def user(content, **extra):
    record = {"type": "user", "cwd": "/x/proj-a", "timestamp": "2026-03-01T10:00:00.000Z",
              "entrypoint": "cli", "message": {"role": "user", "content": content}}
    record.update(extra)
    return record


def history_row(display, ts=1772000000000, **extra):
    row = {"display": display, "pastedContents": {}, "project": "/x/proj-a", "sessionId": "s1"}
    if ts is not None:
        row["timestamp"] = ts
    row.update(extra)
    return row


def make_claude_dir(root):
    claude = root / "claude"
    write_jsonl(claude / "history.jsonl", [
        history_row("/mcp"),
        history_row("please fix the login bug, it fails on refresh", ts=1766499160000),
        history_row("what do you think of this : [Pasted text #1 +12 lines]",
                    pastedContents={"1": {"id": 1, "type": "text", "content": "SECRET PASTE"}}),
        history_row("contact me at aymen@example.com or https://example.com/x?token=abc123 "
                    "key sk-abcdefghijklmnopqrstuvwxyz0123456789"),
        history_row("ok"),
        history_row("let's commit the current state of the code"),
        '{"display": "broken',
        history_row("undated prompt here please", ts=None),
    ])
    write_jsonl(claude / "projects/-x-proj-a/session1.jsonl", [
        user("let's commit the current state of the code"),
        user("can we do that ?\r\nI would go as far as saying yes",
             entrypoint="claude-desktop", origin={"kind": "human"}),
        user([{"type": "tool_result", "tool_use_id": "t1", "content": "tool output text here"}]),
        user("You are a subagent, do X and report back", isSidechain=True),
        user("meta record text here please", isMeta=True),
        user("summary of the conversation so far", isCompactSummary=True),
        user([{"type": "text", "text": "analyze this screen"}, {"type": "image", "source": {}}]),
        user("<task-notification><task-id>1</task-id><summary>done</summary></task-notification>"),
        user("<system-reminder>stuff</system-reminder>why is the mcp file under a folder called unknown"),
        user("look at this\n```python\nimport os\nprint(1)\n```\nand tell me what breaks"),
        user("word " * 500),
        user("<p>Hello</p><div>pasted email</div>"),
        user("2026-01-01 10:00:00 ERROR something\nat foo.js:1\nis the report agent stuck ?"),
        {"type": "assistant", "message": {"role": "assistant", "content": "assistant words here"}},
        user("> quoted reply line\nmy actual answer here ok"),
        user("Condense the tool payload below please", entrypoint="sdk-py"),
        user("Background command finished with exit code zero", origin={"kind": "task-notification"}),
    ])
    write_jsonl(claude / "projects/-x-proj-a/session1/subagents/agent-1.jsonl", [
        user("Review this change for security vulnerabilities in detail"),
    ])
    write_jsonl(claude / "projects/-x-proj-b/session2.jsonl", [
        user("bring back the toggle style light mode dark mode slider", cwd="/x/proj-b",
             timestamp="2025-12-01T09:00:00.000Z"),
    ])
    return claude


class TempDirCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ghostwriter-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class BuildCorpus(TempDirCase):
    def setUp(self):
        super().setUp()
        self.claude = make_claude_dir(self.root)

    def run_build(self, *extra):
        out = self.root / "out"
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "build_corpus.py"),
                                 "--claude-dir", str(self.claude), "--out-dir", str(out), *extra],
                                capture_output=True, text=True, timeout=60)
        corpus = out / "me.corpus.jsonl"
        items = [json.loads(line) for line in corpus.read_text().splitlines()] if corpus.exists() else []
        return result, items

    def build_ok(self, *extra):
        result, items = self.run_build(*extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(items, "corpus is empty")
        return result, items

    def test_default_run_keeps_exactly_the_expected_items(self):
        result, items = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(i["text"] for i in items), sorted([
            "please fix the login bug, it fails on refresh",
            "what do you think of this :",
            "contact me at <EMAIL> or <URL> key <TOKEN>",
            "let's commit the current state of the code",
            "undated prompt here please",
            "can we do that ? I would go as far as saying yes",
            "analyze this screen",
            "why is the mcp file under a folder called unknown",
            "look at this and tell me what breaks",
            "is the report agent stuck ?",
            "my actual answer here ok",
            "bring back the toggle style light mode dark mode slider",
        ]))
        summary = json.loads(result.stdout)
        self.assertEqual(summary["items"], 12)
        self.assertEqual(summary["dropped"]["duplicate"], 1)
        self.assertEqual(summary["dropped"]["markup"], 1)

    def test_pasted_contents_never_read(self):
        _, items = self.build_ok()
        self.assertNotIn("SECRET PASTE", json.dumps(items))

    def test_subagent_transcripts_excluded(self):
        _, items = self.build_ok()
        self.assertNotIn("security vulnerabilities", json.dumps(items))

    def test_machine_prompts_excluded(self):
        _, items = self.build_ok()
        blob = json.dumps(items)
        self.assertNotIn("Condense the tool payload", blob)
        self.assertNotIn("Background command finished", blob)

    def test_harness_blocks_and_pastes(self):
        _, items = self.build_ok()
        blob = json.dumps(items)
        for needle in ("task-notification", "system-reminder", "pasted email", "import os",
                       "quoted reply", "ERROR something"):
            self.assertNotIn(needle, blob)

    def test_dedup_keeps_history_first(self):
        _, items = self.build_ok()
        dup = [i for i in items if i["text"] == "let's commit the current state of the code"]
        self.assertEqual([i["source"] for i in dup], ["history"])

    def test_metadata_fields(self):
        _, items = self.build_ok()
        by_text = {i["text"]: i for i in items}
        self.assertEqual(by_text["please fix the login bug, it fails on refresh"]["timestamp"],
                         "2025-12-23T14:12:40Z")
        self.assertEqual(by_text["analyze this screen"]["timestamp"], "2026-03-01T10:00:00Z")
        self.assertEqual(by_text["analyze this screen"]["project"], "proj-a")
        self.assertEqual(by_text["analyze this screen"]["source"], "transcript")
        self.assertIsNone(by_text["undated prompt here please"]["timestamp"])

    def test_since_drops_older_and_undated(self):
        _, items = self.build_ok("--since", "2026-01-01")
        blob = json.dumps(items)
        self.assertNotIn("toggle style", blob)
        self.assertNotIn("undated prompt", blob)
        self.assertIn("analyze this screen", blob)

    def test_output_permissions(self):
        self.build_ok()
        self.assertEqual(oct((self.root / "out").stat().st_mode & 0o777), "0o700")
        self.assertEqual(oct((self.root / "out/me.corpus.jsonl").stat().st_mode & 0o777), "0o600")

    def test_from_file_paragraphs(self):
        sample = self.root / "sample.txt"
        sample.write_text("first paragraph of the sample text\n\nsecond paragraph here too\n")
        result, items = self.run_build("--from-file", str(sample))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([i["source"] for i in items], ["sample", "sample"])
        self.assertEqual([i["text"] for i in items],
                         ["first paragraph of the sample text", "second paragraph here too"])

    def test_empty_result_exits_2(self):
        result, items = self.run_build("--since", "2099-01-01")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(items, [])
        self.assertEqual(json.loads(result.stdout)["items"], 0)


class CleanText(unittest.TestCase):
    def setUp(self):
        self.mod = load("build_corpus")

    def test_scrub_patterns(self):
        self.assertEqual(
            self.mod.scrub("call +33 6 12 34 56 78 at 10.0.0.1 token "
                           "ghp_abcdefghijklmnopqrstuvwxyz0123456789 Bearer abc.def"),
            "call <PHONE> at <IP> token <TOKEN> Bearer <TOKEN>")

    def test_clean_text_keeps_user_words(self):
        self.assertEqual(self.mod.clean_text("Hello\r\n\r\nworld   again"), "Hello world again")

    def test_prose_that_resembles_code_survives(self):
        text = ("let me know if this works\nfrom now on use tabs\n"
                "at this point I think it's fine\nimport the data first")
        self.assertEqual(self.mod.clean_text(text),
                         "let me know if this works from now on use tabs "
                         "at this point I think it's fine import the data first")

    def test_code_lines_dropped(self):
        text = ("const x = 1\nfrom os import path\nlet y = 2;\nimport os\ndef run(arg):\n"
                "    at Object.run (/x/y.js:10:5)\nkeep this line")
        self.assertEqual(self.mod.clean_text(text), "keep this line")


if __name__ == "__main__":
    unittest.main(verbosity=2)
