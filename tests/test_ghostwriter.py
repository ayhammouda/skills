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
        self.assertIn("no items survived the filters", result.stderr)

    def test_no_claude_data_names_the_directory(self):
        empty = self.root / "no-claude"
        empty.mkdir()
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "build_corpus.py"),
                                 "--claude-dir", str(empty), "--out-dir", str(self.root / "out")],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["items"], 0)
        self.assertTrue(result.stderr.startswith(f"no Claude Code data under {empty}"), result.stderr)
        self.assertNotIn("survived", result.stderr)

    def test_from_file_with_nothing_kept_reports_filters(self):
        sample = self.root / "sample.txt"
        sample.write_text("one\n\ntwo\n")
        result, items = self.run_build("--from-file", str(sample))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(items, [])
        self.assertIn("no items survived the filters", result.stderr)
        self.assertNotIn("Claude Code data", result.stderr)

    def test_from_file_rejects_since(self):
        sample = self.root / "sample.txt"
        sample.write_text("first paragraph of the sample text\n")
        result, items = self.run_build("--from-file", str(sample), "--since", "2026-01-01")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(items, [])
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertIn("--since", result.stderr)
        self.assertIn("--from-file", result.stderr)

    def test_skip_reasons_are_counted(self):
        result, _ = self.build_ok()
        summary = json.loads(result.stdout)
        self.assertEqual(summary["skipped"], {"malformed": 1, "sidechain": 1, "meta": 1, "compact": 1,
                                              "sdk": 1, "origin": 1})
        self.assertEqual(summary["dropped"]["skipped_record"], 6)

    def test_ide_and_hook_blocks_removed(self):
        claude = self.root / "claude-ide"
        write_jsonl(claude / "projects/-x-p/s.jsonl", [
            user([{"type": "text", "text": "<ide_selection>The user selected the lines 10 to 20 from app.py: "
                                           "if token == SECRET: grant()</ide_selection>"},
                  {"type": "text", "text": "why does this fail on refresh"}]),
            user("<ide_opened_file>The user opened the file app.py in the IDE. This may or may not be "
                 "related.</ide_opened_file>can you fix the login bug please"),
            user("<user-prompt-submit-hook>[11:32 CEST -- someone]</user-prompt-submit-hook>"
                 "keep the header as it is please"),
            user("make the footer logo bigger please <system-reminder>unclosed reminder text the harness wrote"),
        ])
        out = self.root / "out-ide"
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "build_corpus.py"),
                                 "--claude-dir", str(claude), "--out-dir", str(out)],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        texts = [json.loads(line)["text"] for line in (out / "me.corpus.jsonl").read_text().splitlines()]
        self.assertEqual(sorted(texts), sorted(["why does this fail on refresh", "can you fix the login bug please",
                                                "keep the header as it is please",
                                                "make the footer logo bigger please"]))


class CleanText(unittest.TestCase):
    def setUp(self):
        self.mod = load("build_corpus")

    def test_scrub_patterns(self):
        self.assertEqual(
            self.mod.scrub("call +33 6 12 34 56 78 at 10.0.0.1 token "
                           "ghp_abcdefghijklmnopqrstuvwxyz0123456789 Bearer abc.def"),
            "call <PHONE> at <IP> token <TOKEN> Bearer <TOKEN>")

    def test_scrub_leaves_long_paths_without_digits(self):
        text = "see ghostwriter/references/research-playbook.md and tests/test_ghostwriter.py"
        self.assertEqual(self.mod.scrub(text), text)

    def test_scrub_replaces_long_runs_with_a_digit(self):
        self.assertEqual(self.mod.scrub("key abcdefghijklmnopqrstuvwxyz0123456789ab ok"), "key <TOKEN> ok")
        self.assertEqual(self.mod.scrub("aws wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"), "aws <TOKEN>")

    def test_scrub_replaces_long_digit_free_runs_without_a_slash(self):
        self.assertEqual(self.mod.scrub("key abcdefghijklmnopqrstuvwxyzabcdef ok"), "key <TOKEN> ok")
        self.assertEqual(self.mod.scrub("see docs/design/ghostwriter-design-notes.md"),
                         "see docs/design/ghostwriter-design-notes.md")

    def test_token_pattern_matches_the_validator(self):
        self.assertEqual(self.mod.TOKEN_RE.pattern, load("validate_profile").TOKEN_RE.pattern)

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


SIX_ITEMS = [
    {"text": text, "source": "history", "timestamp": f"2026-01-0{n}T10:00:00Z", "project": "proj-a"}
    for n, text in enumerate([
        "can we do that ?",
        "Please fix the login bug.",
        "let's commit the current state of the code",
        "Fix it now!",
        "It's basically a hero banner : the picture is here.",
        "why is the mcp file under a folder called unknown",
    ], start=1)
]


class StyleStats(TempDirCase):
    def run_stats(self, items, *extra):
        corpus = self.root / "me.corpus.jsonl"
        corpus.write_text("".join(json.dumps(i) + "\n" for i in items))
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "style_stats.py"), str(corpus), *extra],
                                capture_output=True, text=True, timeout=60)
        stats_path = self.root / "me.stats.json"
        stats = json.loads(stats_path.read_text()) if stats_path.exists() else None
        return result, stats

    def test_counts_and_rates(self):
        result, s = self.run_stats(SIX_ITEMS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(s["items"], 6)
        self.assertEqual(s["words"], 39)
        self.assertEqual(s["sources"], {"history": 6})
        r = s["rates"]
        self.assertEqual(r["lowercase_start"], 0.5)
        self.assertEqual(r["no_terminal_punct"], 0.333)
        self.assertEqual(r["question"], 0.167)
        self.assertEqual(r["exclamation"], 0.167)
        self.assertEqual(r["contraction"], 0.333)
        self.assertEqual(r["imperative_start"], 0.167)
        self.assertEqual(r["space_before_question"], 1.0)
        self.assertEqual(r["space_before_colon"], 1.0)
        self.assertEqual(r["space_before_exclaim"], 0.0)
        self.assertEqual(r["em_dash"], 0.0)
        self.assertEqual(s["markers"]["please"], 1)
        self.assertEqual(s["markers"]["basically"], 1)
        self.assertEqual(s["markers"]["let's"], 1)
        self.assertEqual(s["markers"]["thanks"], 0)
        self.assertEqual(s["sentence_length"], {"count": 6, "mean": 6.5, "median": 6.5, "p90": 10})
        self.assertEqual(s["item_words"], {"mean": 6.5, "median": 6.5, "p90": 10, "max": 10})
        self.assertIn(["fix", 2], s["top_words"])
        self.assertNotIn("the", [w for w, _ in s["top_words"]])
        self.assertIn(["the current state", 1], s["top_trigrams"])
        self.assertIn(["fix it", 1], s["top_openers"])
        self.assertIn(["picture is here", 1], s["top_closers"])
        self.assertEqual(s["language"], {"en": 6, "fr": 0, "other": 0})
        self.assertEqual(s["date_span"], {"first": "2026-01-01T10:00:00Z", "last": "2026-01-06T10:00:00Z"})

    def test_language_detects_french(self):
        mod = load("style_stats")
        stats = mod.compute_stats([{"text": "je pense que le code est pas fini", "source": "sample",
                                    "timestamp": None, "project": None}])
        self.assertEqual(stats["language"], {"en": 0, "fr": 1, "other": 0})
        self.assertEqual(stats["date_span"], {"first": None, "last": None})

    def test_placeholders_are_not_words(self):
        mod = load("style_stats")
        self.assertEqual(mod.words("check <URL> now, ping <EMAIL> please"), ["check", "now", "ping", "please"])
        stats = mod.compute_stats([{"text": "check <URL> now please", "source": "history",
                                    "timestamp": None, "project": None}])
        self.assertEqual(stats["words"], 3)
        self.assertNotIn("url", [w for w, _ in stats["top_words"]])

    def test_sample_is_deterministic_and_sized(self):
        self.run_stats(SIX_ITEMS, "--sample-size", "4", "--seed", "7")
        first = (self.root / "me.sample.md").read_text()
        self.run_stats(SIX_ITEMS, "--sample-size", "4", "--seed", "7")
        self.assertEqual(first, (self.root / "me.sample.md").read_text())
        self.assertEqual(first.count("\n- ("), 4)
        for heading in ("## short", "## medium", "## long"):
            self.assertIn(heading, first)

    def test_sample_larger_than_corpus_takes_everything(self):
        self.run_stats(SIX_ITEMS, "--sample-size", "80")
        sample = (self.root / "me.sample.md").read_text()
        self.assertEqual(sample.count("\n- ("), 6)
        self.assertIn("- (history, 2026-01-04, 3 words) Fix it now!", sample)

    def test_outputs_are_private(self):
        self.run_stats(SIX_ITEMS)
        for name in ("me.stats.json", "me.sample.md"):
            self.assertEqual(oct((self.root / name).stat().st_mode & 0o777), "0o600", name)

    def test_empty_corpus_exits_2(self):
        result, s = self.run_stats([])
        self.assertEqual(result.returncode, 2)
        self.assertIn("empty corpus", result.stderr)
        self.assertIsNone(s)
        self.assertFalse((self.root / "me.sample.md").exists())

    def test_out_paths_in_missing_directories_are_created_privately(self):
        stats_out = self.root / "new/deep/me.stats.json"
        sample_out = self.root / "new/me.sample.md"
        result, _ = self.run_stats(SIX_ITEMS, "--stats-out", str(stats_out), "--sample-out", str(sample_out))
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in (stats_out, sample_out):
            self.assertEqual(oct(path.stat().st_mode & 0o777), "0o600", path)
        for path in (self.root / "new", self.root / "new/deep"):
            self.assertEqual(oct(path.stat().st_mode & 0o777), "0o700", path)
        self.assertEqual(json.loads(result.stdout)["stats"], str(stats_out))

    def test_out_path_blocked_by_a_file_fails_with_one_line(self):
        blocker = self.root / "blocker"
        blocker.write_text("not a directory")
        result, _ = self.run_stats(SIX_ITEMS, "--stats-out", str(blocker / "me.stats.json"))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertTrue(result.stderr.startswith("error: "), result.stderr)
        self.assertIn(str(blocker), result.stderr)


VALID_PROFILE = """---
name: Valid Example
slug: valid
kind: sample
version: 1
created: 2026-10-18
updated: 2026-10-18
language: en
sources:
  - pasted sample
confidence: low
channels: [email, reddit, tweet, other]
---

# Valid Example

## Identity and stance
A calm engineer who answers the question first.

## Register
Plain, warm, direct.

## Rhythm and shape
Short sentences, two paragraphs at most.

## Lexicon
Uses ok and sure. Never uses leverage.

## Syntax and mechanics
Contractions, sentence case, no emoji.

## Devices
Explains with one concrete example.

## Openers and closers
Opens with the answer. Closes with the next step.

## Channel dials
### email
length: short; formality: medium; polish: standard; sign-off: first name
### reddit
length: short; formality: low; polish: loose; sign-off: none
### tweet
length: one line; formality: low; polish: loose; sign-off: none
### other
length: as needed; formality: medium; polish: standard; sign-off: none

## Do / Don't
- Do answer first.
- Don't apologize.

## Exemplars
- First exemplar of the voice, short and plain.
- Second exemplar that answers a question directly.
- Third exemplar with a concrete next step.

## Anti-tells
No rule of three, no em dashes.

## Provenance
Built from a pasted sample on 2026-10-18.
"""
PERSONA_PROFILE = VALID_PROFILE.replace("kind: sample", "kind: persona\ndefault_intensity: 3")


class ValidateProfile(TempDirCase):
    def validate(self, name, text, *extra, env=None):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"), str(path), *extra],
                              capture_output=True, text=True, timeout=60, env=env)

    def quote_profile(self, size):
        quote = '"' + " ".join(["w"] * size) + '"'
        return PERSONA_PROFILE.replace("## Lexicon\n", "## Lexicon\nSays " + quote + "\n")

    def test_valid_profile_passes(self):
        result = self.validate("valid.md", VALID_PROFILE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("OK "))

    def test_missing_heading_fails(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("## Devices\n", ""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing heading: Devices", result.stdout)

    def test_headings_out_of_order_fail(self):
        swapped = VALID_PROFILE.replace("## Register\n", "## TMP\n").replace(
            "## Identity and stance\n", "## Register\n").replace("## TMP\n", "## Identity and stance\n")
        result = self.validate("valid.md", swapped)
        self.assertIn("headings out of order", result.stdout)

    def test_missing_channel_fails(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("### tweet\n", ""))
        self.assertIn("missing channel: tweet", result.stdout)

    def test_missing_key_and_bad_values_fail(self):
        broken = VALID_PROFILE.replace("confidence: low\n", "").replace("kind: sample", "kind: robot")
        result = self.validate("valid.md", broken)
        self.assertIn("missing key: confidence", result.stdout)
        self.assertIn("invalid kind: robot", result.stdout)

    def test_inline_comments_in_front_matter_are_ignored(self):
        text = (VALID_PROFILE.replace("version: 1\n", "version: 1  # bump on every edit\n")
                .replace("confidence: low\n", "confidence: low # from a short sample\n")
                .replace("channels: [email, reddit, tweet, other]\n",
                         "channels: [email, reddit, tweet, other] # all four\n")
                .replace("  - pasted sample\n", "  - pasted sample # one message\n"))
        result = self.validate("valid.md", text)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_front_matter_comments_respect_quotes(self):
        mod = load("validate_profile")
        data, _ = mod.parse_front_matter('---\nname: "C# dev" # alias\nnote: # nothing yet\nversion: 2 # bumped\n'
                                         "sources: # listed below\n  - sample # typed\n---\nbody")
        self.assertEqual(data, {"name": "C# dev", "note": None, "version": 2, "sources": ["sample"]})

    def test_quoted_version_is_reported_with_its_quotes(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("version: 1\n", 'version: "1"\n'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('invalid version: "1"', result.stdout)
        result = self.validate("valid.md", VALID_PROFILE.replace("version: 1\n", "version: one\n"))
        self.assertIn("invalid version: one", result.stdout)

    def test_forty_word_exemplar_fails(self):
        long_item = "- " + " ".join(["word"] * 40) + "\n"
        result = self.validate("valid.md", VALID_PROFILE.replace("- Third exemplar", long_item + "- Third exemplar"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("exemplar 3 has 40 words (max 39)", result.stdout)

    def test_too_few_exemplars_fail(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("- Third exemplar with a concrete next step.\n", ""))
        self.assertIn("exemplar count 2 (need 3 to 6)", result.stdout)

    def test_email_in_body_fails(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("## Provenance\n", "## Provenance\nwrite to foo@bar.com\n"))
        self.assertIn("email in body", result.stdout)

    def test_repository_path_in_body_passes(self):
        text = VALID_PROFILE.replace("## Provenance\n",
                                     "## Provenance\nResearched per ghostwriter/references/research-playbook.md.\n")
        result = self.validate("valid.md", text)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_secret_like_run_in_body_fails(self):
        text = VALID_PROFILE.replace("## Provenance\n", "## Provenance\nkey abcdefghijklmnopqrstuvwxyz0123456789ab\n")
        self.assertIn("token in body", self.validate("valid.md", text).stdout)

    def test_url_allowed_in_sources_but_not_body(self):
        with_source = VALID_PROFILE.replace("  - pasted sample", "  - https://example.com/interview")
        self.assertEqual(self.validate("valid.md", with_source).returncode, 0)
        in_body = with_source.replace("## Provenance\n", "## Provenance\nsee https://example.com/x\n")
        self.assertIn("url in body", self.validate("valid.md", in_body).stdout)

    def test_persona_fifteen_word_quote_fails(self):
        result = self.validate("valid.md", self.quote_profile(15))
        self.assertEqual(result.returncode, 1)
        self.assertIn("quote of 15 words (max 14)", result.stdout)

    def test_persona_fourteen_word_quote_passes(self):
        result = self.validate("valid.md", self.quote_profile(14))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_persona_needs_intensity(self):
        result = self.validate("valid.md", PERSONA_PROFILE.replace("default_intensity: 3\n", ""))
        self.assertIn("missing key: default_intensity", result.stdout)

    def test_self_profile_needs_corpus_block(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("kind: sample", "kind: self"))
        self.assertIn("missing key: corpus.items", result.stdout)
        corpus = "kind: self\ncorpus:\n  items: 742\n  words: 14436\n  first: 2026-01-30\n  last: 2026-10-18"
        self.assertEqual(self.validate("valid.md", VALID_PROFILE.replace("kind: sample", corpus)).returncode, 0)

    def test_slug_mismatch_fails(self):
        result = self.validate("other.md", VALID_PROFILE)
        self.assertIn("slug does not match filename", result.stdout)

    def test_crlf_and_bom_profile_passes(self):
        result = self.validate("valid.md", "\ufeff" + VALID_PROFILE.replace("\n", "\r\n"))
        self.assertEqual(result.returncode, 0, result.stdout)

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_user_profile_with_open_permissions_fails(self):
        home = self.root / "cfg"
        (home / "tones").mkdir(parents=True)
        path = home / "tones/valid.md"
        path.write_text(VALID_PROFILE)
        os.chmod(path, 0o644)
        command = [sys.executable, "-I", str(SCRIPTS / "validate_profile.py"), str(path), "--home", str(home)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn("mode 644, expected 600", result.stdout)
        os.chmod(path, 0o600)
        self.assertEqual(subprocess.run(command, capture_output=True, text=True, timeout=60).returncode, 0)

    def test_template_validates_structurally(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"),
                                 str(ROOT / "ghostwriter/references/tones/_template.md")],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_all_shipped_profiles_pass(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"), "--all",
                                 "--home", str(self.root / "empty-home")], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("_template.md", result.stdout)

    def test_list_expands_home_and_marks_shadowing(self):
        home = self.root / "cfg"
        (home / "tones").mkdir(parents=True)
        (home / "tones/me.md").write_text(VALID_PROFILE.replace("slug: valid", "slug: me"))
        (home / "tones/deadpool.md").write_text(PERSONA_PROFILE.replace("slug: valid", "slug: deadpool"))
        shipped = self.root / "shipped"
        shipped.mkdir()
        (shipped / "deadpool.md").write_text(PERSONA_PROFILE.replace("slug: valid", "slug: deadpool"))
        (shipped / "_template.md").write_text(VALID_PROFILE.replace("slug: valid", "slug: _template"))
        env = {**os.environ, "HOME": str(self.root), "GHOSTWRITER_HOME": "~/cfg"}
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"), "--list",
                                 "--shipped", str(shipped)], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(result.stdout.splitlines(),
                         ["deadpool\tpersona\tuser (shadows shipped)", "me\tsample\tuser"])


class SkillPackage(unittest.TestCase):
    def test_skill_frontmatter_and_references(self):
        text = (ROOT / "ghostwriter/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front, body = text.split("---\n", 2)[1:]
        self.assertEqual(re.search(r"^name:\s*(\S+)", front, re.M)[1], "ghostwriter")
        description = re.search(r"^description:\s*(.+?)(?=^\S|\Z)", front, re.M | re.S)[1]
        self.assertTrue(1 <= len(description.strip()) <= 1024, len(description))
        self.assertLess(len(text.splitlines()), 500)
        for ref in ("references/ai-tells.md", "references/profile-schema.md", "references/self-profile.md",
                    "references/research-playbook.md", "scripts/build_corpus.py", "scripts/style_stats.py",
                    "scripts/validate_profile.py"):
            self.assertIn(ref, body)
            self.assertTrue((ROOT / "ghostwriter" / ref).exists(), ref)

    def test_license_copy_and_agent_metadata(self):
        self.assertEqual((ROOT / "ghostwriter/LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        self.assertIn('display_name: "Ghostwriter"', (ROOT / "ghostwriter/agents/openai.yaml").read_text())

    def test_evals_json(self):
        data = json.loads((ROOT / "ghostwriter/evals/evals.json").read_text())
        self.assertEqual(data["skill_name"], "ghostwriter")
        self.assertGreaterEqual(len(data["evals"]), 8)
        self.assertEqual(len({case["id"] for case in data["evals"]}), len(data["evals"]))
        for case in data["evals"]:
            for key in ("id", "category", "prompt", "expected_output", "assertions"):
                self.assertIn(key, case)
            self.assertTrue(case["assertions"])
            for assertion in case["assertions"]:
                self.assertEqual(set(assertion), {"text", "type"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
