# Ghostwriter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `ghostwriter` skill: humanizer-style AI-pattern removal plus stored tone profiles, with Aymen's own voice built from his local Claude Code prompts and two researched example personas.

**Architecture:** One self-contained skill folder. `SKILL.md` holds the workflow and guardrails; `references/` holds the profile schema, the AI-tell list, the two profile-building playbooks, and the shipped tone files; three stdlib Python scripts extract the local corpus, measure it, and validate profiles. Profiles created at runtime live in `~/.config/ghostwriter/`, never in the repository.

**Tech Stack:** Markdown + YAML front matter; Python 3.10+ standard library (`json`, `re`, `pathlib`, `argparse`, `random`, `statistics`, `unittest`); Git.

**Spec:** `docs/design/2026-10-18-ghostwriter-design.md`

## Global Constraints

- Scripts: Python 3.10+ standard library only; invoked as `python3 -I <script>`; no imports between sibling scripts (`-I` implies `-P` on 3.11+); every script has `main(argv) -> int` and `if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))`.
- `SKILL.md` is harness-neutral: tools are named generically ("web search", "read the file", "run the script"); no Claude-only tool names; under 500 lines; references one level deep (`references/<file>.md`, `scripts/<file>.py`).
- Agent Skills spec: `name: ghostwriter` equals the folder name; `description` 1 to 1024 characters and must not claim a bare "humanize this text" with no voice named.
- Repository conventions: `ghostwriter/LICENSE` is a byte-for-byte copy of `./LICENSE`; `ghostwriter/agents/openai.yaml` mirrors `clean-project/agents/openai.yaml`; `ghostwriter/evals/evals.json` follows `mentor/evals/evals.json`; tests live in `tests/test_ghostwriter.py` and run with `python3 -B tests/test_ghostwriter.py`.
- Profile locations: user directory `~/.config/ghostwriter/` (override `GHOSTWRITER_HOME`, `~` expanded) with `tones/` and `corpus/`; shipped directory `ghostwriter/references/tones/`; user profile shadows shipped on the same slug; directories created `0o700`, files `0o600`.
- Corpus sources: `~/.claude/history.jsonl` (`display` only, never `pastedContents`) and `~/.claude/projects/*/*.jsonl` one level deep (never `subagents/`).
- Privacy: scrub emails, URLs, phone numbers, IP addresses, and token-like strings to `<EMAIL>`, `<URL>`, `<PHONE>`, `<IP>`, `<TOKEN>` before writing; profile exemplars carry no names, emails, URLs, keys, or project names; the end-to-end report carries counts, rates, and pass/fail only.
- Copyright: persona quotes under 15 words, at most 5 per profile; exemplars synthesized.
- Polish levels `loose`, `standard`, `clean`; defaults reddit `loose`, tweet `loose`, email `standard`; no level inserts misspellings. Persona intensity 1 to 5, default 3.
- Twelve profile sections, in order: Identity and stance; Register; Rhythm and shape; Lexicon; Syntax and mechanics; Devices; Openers and closers; Channel dials; Do / Don't; Exemplars; Anti-tells; Provenance. Channel dials has `### email`, `### reddit`, `### tweet`, `### other`.
- Git: work on `develop` (tracking `origin/develop`, fast-forwarded to `main`); commit messages in the repository's imperative style ending with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; never push.

## Review Focus

1. Subagent transcripts under `~/.claude/projects/<project>/<session>/subagents/**/*.jsonl` contain "user" turns written by the agent; a person expects none of that text in their voice profile. Pinned in Task 2 (`test_subagent_transcripts_excluded`).
2. Harness-injected user turns (`<task-notification>…`, `<system-reminder>…`) and pasted HTML, logs, or code inside a prompt are not the user's writing; they must be removed or the item dropped. Pinned in Task 2 (`test_harness_blocks_and_pastes`).
3. An empty or tiny corpus (fresh machine, `--since` in the future) must produce a clear message, not a traceback or a stats file full of division errors. Pinned in Task 3 (`test_empty_corpus_exits_2`).
4. Profiles hand-edited on Windows arrive with CRLF line endings and a BOM; the validator must still read them. Pinned in Task 4 (`test_crlf_and_bom_profile_passes`).
5. `GHOSTWRITER_HOME` containing `~`, and a user profile shadowing a shipped one, must resolve the way the spec says, or the agent silently edits the wrong file. Pinned in Task 4 (`test_list_expands_home_and_marks_shadowing`).

---

### Task 1: Branch and commit the design documents

**Files:**
- Commit: `docs/design/2026-10-18-ghostwriter-design.md`, `docs/design/2026-10-18-ghostwriter-plan.md`

- [ ] **Step 1: Create the local `develop` branch from `origin/develop` and fast-forward it to `main`**

```bash
git fetch origin develop
git checkout -b develop origin/develop
git merge --ff-only main
```

Expected: `git branch --show-current` prints `develop`; `git rev-parse develop main` prints the same hash twice.

- [ ] **Step 2: Commit the two documents**

```bash
git add docs/design/2026-10-18-ghostwriter-design.md docs/design/2026-10-18-ghostwriter-plan.md
git commit -m "Add Ghostwriter design and implementation plan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `git status --short` prints nothing.

---

### Task 2: Corpus extraction script

**Files:**
- Create: `ghostwriter/scripts/build_corpus.py`
- Create: `tests/test_ghostwriter.py`

**Interfaces:**
- Produces: `python3 -I ghostwriter/scripts/build_corpus.py [--claude-dir DIR] [--out-dir DIR] [--slug SLUG] [--since YYYY-MM-DD] [--min-words 3] [--max-words 400] [--from-file PATH]`. Defaults: `--claude-dir ~/.claude`, `--out-dir $GHOSTWRITER_HOME/corpus` falling back to `~/.config/ghostwriter/corpus`, `--slug me`. Writes `<out-dir>/<slug>.corpus.jsonl`, one object per line: `{"text": str, "source": "history" | "transcript" | "sample", "timestamp": "YYYY-MM-DDTHH:MM:SSZ" | null, "project": str | null}`. Prints a one-line JSON summary to stdout: `{"items": int, "history_rows": int, "transcript_records": int, "dropped": {"slash": int, "short": int, "long": int, "markup": int, "duplicate": int, "skipped_record": int, "before_since": int}, "out": str}`. Exit 0 on success, 2 when zero items survive (the summary is still printed; no corpus file is written).
- Produces, for `--from-file PATH`: each blank-line-separated paragraph of the file becomes one item with `source: "sample"`, `timestamp: null`, `project: null`; the two Claude sources are not read.
- Produces module functions (loaded by tests via `importlib.util.spec_from_file_location`): `clean_text(text: str) -> str`, `scrub(text: str) -> str`, `normalize_key(text: str) -> str`, `iter_history(path: Path) -> Iterator[Item]`, `iter_transcripts(projects_dir: Path) -> Iterator[Item]`, `build(claude_dir: Path, out_dir: Path, slug: str, since: str | None, min_words: int, max_words: int, from_file: Path | None) -> dict`, `main(argv: list[str]) -> int`. `Item` is a dataclass with fields `text: str`, `source: str`, `timestamp: str | None`, `project: str | None`.

Decided cleaning rules for `clean_text`, in this order: remove whole blocks for the tags `system-reminder`, `task-notification`, `pasted_content`, `command-name`, `command-message`, `command-args`, `local-command-stdout`, `local-command-stderr`, `local-command-caveat`, `side-sessions-event`, `ci-monitor-event` (opening tag may carry attributes; match case-insensitively, across newlines); remove fenced code blocks (```…```); remove `[Pasted text #N +M lines]` and `[Image #N]` markers; drop lines that start with `>` after optional spaces, lines starting with `[Request interrupted`, log-like lines (`^\s*(\d{4}-\d{2}-\d{2}|\[\d|at |Traceback|Error:|WARN|INFO|DEBUG|ERROR)`), and code-like lines (`^\s*(import |from |def |class |const |let |var |function |\$ |#!/|[{}])` or more than 30% of non-space characters outside `[A-Za-z0-9'’,.?!:;()-]`; HTML lines are left in place so the markup rule below can drop the whole item); collapse all whitespace to single spaces; strip. `clean_text` does not scrub.

Decided record rules for `iter_transcripts`: files matching `projects_dir/*/*.jsonl` only; parse each line as JSON and skip lines that fail; keep records with `type == "user"` where none of `isSidechain`, `isMeta`, `isCompactSummary` is truthy; `message.content` string is the text; a list is skipped if any block has `type == "tool_result"`, otherwise the `text` of `type == "text"` blocks joined by a space (image and other blocks ignored); `project` is the basename of the record's `cwd` when present, else the directory name; `timestamp` normalized from the record's ISO string.

Decided record rules for `iter_history`: skip rows whose `display` starts with `/`; `timestamp` from the epoch-milliseconds field when present, else `null`; `project` is the basename of `project`.

Decided `build` order: history items first, then transcript items; `clean_text`, then `scrub`, then word count against `min_words`/`max_words` (`text.split()`); an item still containing an HTML-like tag (`<[a-z][a-z0-9-]*(\s[^<>]*)?/?>`) counts as `markup` and is dropped; dedup on `normalize_key` (lowercase, whitespace collapsed), first occurrence wins; `--since` drops items dated before the date and, when given, undated items too.

Decided `scrub` patterns, applied in this order: URLs (`https?://\S+` and `www\.\S+`) → `<URL>`; emails → `<EMAIL>`; token-like strings (prefixes `sk-`, `ghp_`, `gho_`, `xox[abp]-`, `AKIA`, `AIza`, the word after `Bearer ` via `(?<=Bearer\s)\S+`, or any run of 32+ `[A-Za-z0-9+/_=-]` characters) → `<TOKEN>`; IPv4 (`\b\d{1,3}(\.\d{1,3}){3}\b`) → `<IP>`; phone numbers (`\+?\d(?:[ .]?\d){8,14}`, so dates with dashes or colons are left alone) → `<PHONE>`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ghostwriter.py` (unittest, same header style as `tests/test_git_safety.py`, `ROOT = Path(__file__).resolve().parents[1]`, `SCRIPTS = ROOT / "ghostwriter/scripts"`, a module loader `load(name)` using `importlib.util`), add a `make_claude_dir(root: Path) -> Path` fixture helper that writes:

`history.jsonl` rows (fields `display`, `pastedContents`, `timestamp`, `project: "/x/proj-a"`, `sessionId`):
1. `/mcp` → dropped (slash)
2. `please fix the login bug, it fails on refresh`, timestamp `1766499160000`
3. `what do you think of this : [Pasted text #1 +12 lines]` with `pastedContents: {"1": {"id": 1, "type": "text", "content": "SECRET PASTE"}}`
4. `contact me at aymen@example.com or https://example.com/x?token=abc123 key sk-abcdefghijklmnopqrstuvwxyz0123456789`
5. `ok` → dropped (short)
6. `let's commit the current state of the code`
7. the malformed line `{"display": "broken` → skipped without error
8. `undated prompt here please` with no `timestamp` field

`projects/-x-proj-a/session1.jsonl` records (`type: "user"`, `cwd: "/x/proj-a"`, `timestamp: "2026-03-01T10:00:00.000Z"` unless noted):
- a. string `let's commit the current state of the code` → duplicate of history 6
- b. string `can we do that ?\r\nI would go as far as saying yes`
- c. list with a `tool_result` block → skipped
- d. `isSidechain: true`, string `You are a subagent, do X and report back` → skipped
- e. `isMeta: true`, string `meta record text here please` → skipped
- f. `isCompactSummary: true`, string `summary of the conversation so far` → skipped
- g. list `[{"type": "text", "text": "analyze this screen"}, {"type": "image", "source": {}}]`
- h. string `<task-notification><task-id>1</task-id><summary>done</summary></task-notification>` → dropped
- i. string `<system-reminder>stuff</system-reminder>why is the mcp file under a folder called unknown`
- j. string ``look at this\n```python\nimport os\nprint(1)\n```\nand tell me what breaks``
- k. string of 500 repetitions of `word ` → dropped (long)
- l. string `<p>Hello</p><div>pasted email</div>` → dropped (markup)
- m. string `2026-01-01 10:00:00 ERROR something\nat foo.js:1\nis the report agent stuck ?`
- n. `type: "assistant"` record → ignored
- o. string `> quoted reply line\nmy actual answer here ok`

`projects/-x-proj-a/session1/subagents/agent-1.jsonl`: user string `Review this change for security vulnerabilities in detail`.

`projects/-x-proj-b/session2.jsonl`: user string `bring back the toggle style light mode dark mode slider`, `cwd: "/x/proj-b"`, timestamp `2025-12-01T09:00:00.000Z`.

Tests:

```python
class BuildCorpus(unittest.TestCase):
    def run_build(self, *extra):
        out = self.root / "out"
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "build_corpus.py"),
                                 "--claude-dir", str(self.claude), "--out-dir", str(out), *extra],
                                capture_output=True, text=True, timeout=60)
        items = [json.loads(l) for l in (out / "me.corpus.jsonl").read_text().splitlines()] if (out / "me.corpus.jsonl").exists() else []
        return result, items

    def test_default_run_keeps_exactly_the_expected_items(self):
        result, items = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        texts = sorted(i["text"] for i in items)
        self.assertEqual(texts, sorted([
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
        _, items = self.run_build()
        self.assertNotIn("SECRET PASTE", json.dumps(items))

    def test_subagent_transcripts_excluded(self):
        _, items = self.run_build()
        self.assertNotIn("security vulnerabilities", json.dumps(items))

    def test_harness_blocks_and_pastes(self):
        _, items = self.run_build()
        blob = json.dumps(items)
        for needle in ("task-notification", "system-reminder", "pasted email", "import os", "quoted reply", "ERROR something"):
            self.assertNotIn(needle, blob)

    def test_dedup_keeps_history_first(self):
        _, items = self.run_build()
        dup = [i for i in items if i["text"] == "let's commit the current state of the code"]
        self.assertEqual([i["source"] for i in dup], ["history"])

    def test_metadata_fields(self):
        _, items = self.run_build()
        by_text = {i["text"]: i for i in items}
        self.assertEqual(by_text["please fix the login bug, it fails on refresh"]["timestamp"], "2025-12-23T14:12:40Z")
        self.assertEqual(by_text["analyze this screen"]["timestamp"], "2026-03-01T10:00:00Z")
        self.assertEqual(by_text["analyze this screen"]["project"], "proj-a")
        self.assertIsNone(by_text["undated prompt here please"]["timestamp"])

    def test_since_drops_older_and_undated(self):
        _, items = self.run_build("--since", "2026-01-01")
        blob = json.dumps(items)
        self.assertNotIn("toggle style", blob)
        self.assertNotIn("undated prompt", blob)
        self.assertIn("analyze this screen", blob)

    def test_output_permissions(self):
        self.run_build()
        self.assertEqual(oct((self.root / "out").stat().st_mode & 0o777), "0o700")
        self.assertEqual(oct((self.root / "out" / "me.corpus.jsonl").stat().st_mode & 0o777), "0o600")

    def test_from_file_paragraphs(self):
        sample = self.root / "sample.txt"
        sample.write_text("first paragraph of the sample text\n\nsecond paragraph here too\n")
        result, items = self.run_build("--from-file", str(sample), "--slug", "me")
        self.assertEqual([i["source"] for i in items], ["sample", "sample"])

    def test_empty_result_exits_2(self):
        result, items = self.run_build("--since", "2099-01-01")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(items, [])
```

Also unit tests on the loaded module: `test_scrub_patterns` asserting `scrub("call +33 6 12 34 56 78 at 10.0.0.1 token ghp_abcdefghijklmnopqrstuvwxyz0123456789 Bearer abc.def")` equals `"call <PHONE> at <IP> token <TOKEN> Bearer <TOKEN>"`, and `test_clean_text_keeps_user_words` asserting `clean_text("Hello\r\n\r\nworld   again")` equals `"Hello world again"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: FAIL, the loader raises `FileNotFoundError` for `build_corpus.py`.

- [ ] **Step 3: Implement `ghostwriter/scripts/build_corpus.py`**

Signatures from the Interfaces block. Timestamp normalization: `datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` for history; for transcripts, `datetime.fromisoformat(value.replace("Z", "+00:00"))` converted to UTC and formatted the same way, `null` when absent or unparsable. Open every file with `encoding="utf-8", errors="replace"`. Create `out_dir` with `mode=0o700` (and `chmod` after, since `mkdir` honors the umask) and write the file then `chmod(0o600)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: `OK` with every `BuildCorpus` test passing.

- [ ] **Step 5: Commit**

```bash
git add ghostwriter/scripts/build_corpus.py tests/test_ghostwriter.py
git commit -m "Add Ghostwriter corpus extraction script" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Stylometrics and sampling script

**Files:**
- Create: `ghostwriter/scripts/style_stats.py`
- Modify: `tests/test_ghostwriter.py`

**Interfaces:**
- Consumes: the corpus JSONL from Task 2 (`text`, `source`, `timestamp`, `project`).
- Produces: `python3 -I ghostwriter/scripts/style_stats.py CORPUS [--stats-out PATH] [--sample-out PATH] [--sample-size 80] [--seed 7]`. Defaults derive from the corpus name: `me.corpus.jsonl` → `me.stats.json` and `me.sample.md` beside it. Exit 0 on success; exit 2 with `empty corpus: nothing to measure` on stderr when the corpus has zero items, writing nothing.
- Produces `me.stats.json` with keys: `items`, `words`, `sources` (counts per source), `date_span` (`{"first": str|null, "last": str|null}`), `language` (`{"en": n, "fr": n, "other": n}`), `item_words` (`{"mean", "median", "p90", "max"}`), `sentence_length` (`{"count", "mean", "median", "p90"}`), `rates` (`lowercase_start`, `no_terminal_punct`, `question`, `exclamation`, `ellipsis`, `em_dash`, `emoji`, `contraction`, `imperative_start`, `space_before_question`, `space_before_colon`, `space_before_exclaim`), `markers` (counts for `please`, `thanks`, `like`, `basically`, `actually`, `just`, `i think`, `maybe`, `kind of`, `let's`), `top_words` (50 `[word, count]` pairs, stopwords removed), `top_bigrams` and `top_trigrams` (25 each), `top_openers` (first two words, 20), `top_closers` (last three words, 20).
- Produces `me.sample.md`: a header with item count, date span, and the sample size, then the sampled items grouped under `## short`, `## medium`, `## long`, each item as `- (source, date, N words) text`.
- Module functions: `words(text) -> list[str]` (regex `[A-Za-zÀ-ſ][A-Za-zÀ-ſ'’]*`, lowercased), `sentences(text) -> list[str]` (split on `(?<=[.!?])\s+` and newlines, empty parts dropped), `compute_stats(items: list[dict]) -> dict`, `stratified_sample(items: list[dict], size: int, seed: int) -> list[dict]`, `render_sample(items, stats, picked) -> str`, `main(argv) -> int`.

Decided definitions: item-level rates are fractions of items rounded to 3 decimals; `lowercase_start` is true when the first alphabetic character is lowercase; `no_terminal_punct` when the last non-space character is not in `.!?`; `question` when the item contains `?`; `contraction` when the regex `\b\w+['’](s|t|re|ve|ll|d|m)\b` matches; `imperative_start` when the first word is in the list `add make fix create update remove delete check run use write show give generate implement analyze review explain look find try keep put move change test build start stop open close read search list help do go bring export plan prepare clean set install deploy commit push merge rename replace refactor document describe compare verify ensure continue proceed apply convert fetch pull save send think`; the three `space_before_*` rates are occurrence ratios `count(" X") / count("X")` for `?`, `:`, `!` (0 when the mark never occurs); `emoji` matches `[\U0001F300-\U0001FAFF☀-➿]`; language per item from the larger of the English and French stopword shares when it exceeds 0.12 (English list `the a an and to of is it that for you this with on are be i we can in`; French list `le la les des une est pas pour que qui dans avec sur je tu nous vous et ou mais donc`), `other` otherwise; mean and median from `statistics`, `p90` by nearest rank (`sorted[ceil(0.9 * n) - 1]`); stopwords for `top_words` are the English list plus `me my your our it's its as at by from or if so not do have has was were will would just`.

Decided sampling: three length buckets by word-count terciles (`short` below the 33rd percentile, `long` above the 67th, `medium` otherwise), each split into older and newer halves by the median timestamp (undated items join `newer`); allocate `size // 6` per bucket, fill round-robin from a `random.Random(seed)` shuffle of each bucket until `size` items or the corpus runs out. The sample file always prints the three length headings; an empty bucket shows `(none)`.

- [ ] **Step 1: Write the failing tests**

Fixture corpus of six items (timestamps `2026-01-0{1..6}T10:00:00Z`, source `history`):
1. `can we do that ?`
2. `Please fix the login bug.`
3. `let's commit the current state of the code`
4. `Fix it now!`
5. `It's basically a hero banner : the picture is here.`
6. `why is the mcp file under a folder called unknown`

```python
class StyleStats(unittest.TestCase):
    def run_stats(self, items, *extra):
        corpus = self.root / "me.corpus.jsonl"
        corpus.write_text("".join(json.dumps(i) + "\n" for i in items))
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "style_stats.py"), str(corpus), *extra],
                                capture_output=True, text=True, timeout=60)
        stats = json.loads((self.root / "me.stats.json").read_text()) if (self.root / "me.stats.json").exists() else None
        return result, stats

    def test_counts_and_rates(self):
        result, s = self.run_stats(SIX_ITEMS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(s["items"], 6)
        self.assertEqual(s["words"], 39)
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
        self.assertEqual(s["markers"]["please"], 1)
        self.assertEqual(s["markers"]["basically"], 1)
        self.assertEqual(s["markers"]["let's"], 1)
        self.assertEqual(s["sentence_length"], {"count": 6, "mean": 6.5, "median": 6.5, "p90": 10})
        self.assertIn(["fix", 2], s["top_words"])
        self.assertNotIn("the", [w for w, _ in s["top_words"]])
        self.assertEqual(s["language"], {"en": 6, "fr": 0, "other": 0})
        self.assertEqual(s["date_span"], {"first": "2026-01-01T10:00:00Z", "last": "2026-01-06T10:00:00Z"})

    def test_sample_is_deterministic_and_sized(self):
        self.run_stats(SIX_ITEMS, "--sample-size", "4", "--seed", "7")
        first = (self.root / "me.sample.md").read_text()
        self.run_stats(SIX_ITEMS, "--sample-size", "4", "--seed", "7")
        self.assertEqual(first, (self.root / "me.sample.md").read_text())
        self.assertEqual(first.count("\n- ("), 4)
        for heading in ("## short", "## medium", "## long"):
            self.assertIn(heading, first)

    def test_empty_corpus_exits_2(self):
        result, s = self.run_stats([])
        self.assertEqual(result.returncode, 2)
        self.assertIn("empty corpus", result.stderr)
        self.assertIsNone(s)
        self.assertFalse((self.root / "me.sample.md").exists())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: FAIL, `FileNotFoundError` for `style_stats.py`.

- [ ] **Step 3: Implement `ghostwriter/scripts/style_stats.py`** with the signatures and definitions above.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add ghostwriter/scripts/style_stats.py tests/test_ghostwriter.py
git commit -m "Add Ghostwriter stylometrics and sampling script" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Profile schema, template, and validator

**Files:**
- Create: `ghostwriter/references/profile-schema.md`
- Create: `ghostwriter/references/tones/_template.md`
- Create: `ghostwriter/scripts/validate_profile.py`
- Modify: `tests/test_ghostwriter.py`

**Interfaces:**
- Produces: `python3 -I ghostwriter/scripts/validate_profile.py [PATH ...] [--all] [--list] [--home DIR] [--shipped DIR]`. `--home` defaults to `$GHOSTWRITER_HOME` (with `~` expanded) or `~/.config/ghostwriter`; `--shipped` defaults to the script's own `../references/tones`. `--all` validates every `*.md` in `<home>/tones` and `<shipped>`. `--list` prints one line per profile, `<slug>\t<kind>\t<location>` where location is `user`, `shipped`, or `user (shadows shipped)`, skipping `_template.md`. Validation prints `OK <path>` or `FAIL <path>: <message>` per file; exit 0 only when every file passes.
- Produces module functions: `parse_front_matter(text: str) -> tuple[dict, str]` (returns the mapping and the body; supports `key: value`, inline lists `[a, b]`, block lists, and one nested mapping level such as `corpus:`), `validate(path: Path) -> list[str]` (empty list means valid), `list_profiles(home: Path, shipped: Path) -> list[tuple[str, str, str]]`, `main(argv) -> int`.

Decided validation rules (each failure is one message, exact wording used by the tests in brackets):
1. Front matter fenced by `---` lines at the top; BOM and CRLF tolerated. [`missing front matter`]
2. Required keys `name`, `slug`, `kind`, `version`, `created`, `updated`, `language`, `sources`, `confidence`, `channels`. [`missing key: <key>`]
3. `kind` in `self`, `persona`, `sample`; `confidence` in `low`, `medium`, `high`; `version` a positive integer; `created` and `updated` `YYYY-MM-DD`. [`invalid <key>: <value>`]
4. `slug` equals the file stem and matches `^[a-z0-9][a-z0-9-]*$`; stems starting with `_` are templates and skip rules 7 and 8. [`slug does not match filename`]
5. `default_intensity` required for `persona`, integer 1 to 5; `corpus` block with `items`, `words`, `first`, `last` required for `self`. [`missing key: default_intensity`, `missing key: corpus.items`]
6. Exactly the twelve `## ` headings from Global Constraints, in order; `## Channel dials` contains `### email`, `### reddit`, `### tweet`, `### other`. [`missing heading: <title>`, `headings out of order`, `missing channel: <name>`]
7. Exemplars: list items (`- `) under `## Exemplars`, 3 to 6 of them, each at most 40 words. [`exemplar count <n> (need 3 to 6)`, `exemplar <i> has <n> words (max 40)`]
8. For `persona`: every passage inside straight double quotes in the body is under 15 words. [`quote of <n> words (max 15)`]
9. Body (not front matter) contains no email, no URL, no token-like string (same patterns as Task 2). [`email in body`, `url in body`, `token in body`]

- [ ] **Step 1: Write the failing tests**

Add a `VALID_PROFILE` constant to the test file: a `sample` profile, slug `valid`, with all keys, the twelve sections, the four channel subsections, and three exemplars of under 40 words. Add `PERSONA_PROFILE`, the same with `kind: persona` and `default_intensity: 3`.

```python
class ValidateProfile(unittest.TestCase):
    def validate(self, name, text, *extra, env=None):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"), str(path), *extra],
                              capture_output=True, text=True, timeout=60, env=env)

    def test_valid_profile_passes(self):
        result = self.validate("valid.md", VALID_PROFILE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("OK "))

    def test_missing_heading_fails(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("## Devices\n", ""))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing heading: Devices", result.stdout)

    def test_long_exemplar_fails(self):
        long_item = "- " + " ".join(["word"] * 41) + "\n"
        result = self.validate("valid.md", VALID_PROFILE.replace("- Third exemplar", long_item + "- Third exemplar"))
        self.assertIn("has 41 words (max 40)", result.stdout)

    def test_email_in_body_fails(self):
        result = self.validate("valid.md", VALID_PROFILE.replace("## Provenance\n", "## Provenance\nwrite to foo@bar.com\n"))
        self.assertIn("email in body", result.stdout)

    def test_persona_long_quote_fails(self):
        quote = '"' + " ".join(["w"] * 16) + '"'
        result = self.validate("persona.md", PERSONA_PROFILE.replace("## Lexicon\n", "## Lexicon\nSays " + quote + "\n"))
        self.assertIn("quote of 16 words (max 15)", result.stdout)

    def test_slug_mismatch_fails(self):
        result = self.validate("other.md", VALID_PROFILE)
        self.assertIn("slug does not match filename", result.stdout)

    def test_crlf_and_bom_profile_passes(self):
        result = self.validate("valid.md", "﻿" + VALID_PROFILE.replace("\n", "\r\n"))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_template_validates_structurally(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"),
                                 str(ROOT / "ghostwriter/references/tones/_template.md")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_all_shipped_profiles_pass(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"), "--all",
                                 "--home", str(self.root / "empty-home")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_list_expands_home_and_marks_shadowing(self):
        home = self.root / "cfg"
        (home / "tones").mkdir(parents=True)
        (home / "tones" / "me.md").write_text(VALID_PROFILE.replace("slug: valid", "slug: me"))
        (home / "tones" / "deadpool.md").write_text(PERSONA_PROFILE.replace("slug: valid", "slug: deadpool"))
        shipped = self.root / "shipped"
        shipped.mkdir()
        (shipped / "deadpool.md").write_text(PERSONA_PROFILE.replace("slug: valid", "slug: deadpool"))
        (shipped / "_template.md").write_text(VALID_PROFILE.replace("slug: valid", "slug: _template"))
        env = {**os.environ, "HOME": str(self.root), "GHOSTWRITER_HOME": "~/cfg"}
        result = subprocess.run([sys.executable, "-I", str(SCRIPTS / "validate_profile.py"), "--list",
                                 "--shipped", str(shipped)], capture_output=True, text=True, env=env)
        self.assertEqual(result.stdout.splitlines(), ["deadpool\tpersona\tuser (shadows shipped)", "me\tsample\tuser"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: FAIL, `FileNotFoundError` for `validate_profile.py`.

- [ ] **Step 3: Write `ghostwriter/references/profile-schema.md`**

Contents: the front matter keys with types and allowed values (from the rules above); the twelve sections with two to four lines each on what to record (for `self` profiles, sections 3 and 5 carry the measured numbers from `me.stats.json`); the channel dial fields `length`, `formality`, `polish`, `sign-off` with the default polish per channel; the polish level definitions; the sanitization rule for exemplars; the quote rule for personas; versioning (`version` increments on every edit, `updated` follows); the lookup order and shadowing rule; `GHOSTWRITER_HOME`.

- [ ] **Step 4: Write `ghostwriter/references/tones/_template.md`**

Front matter with every key and placeholder values that satisfy the validator (`slug: _template`, `kind: sample`, `version: 1`, dates `2026-10-18`, `confidence: low`, `channels: [email, reddit, tweet, other]`, `sources: []`). The twelve headings in order, one guidance line each, the four channel subsections with the dial fields, and an empty exemplar list comment (`<!-- three to six items, under 40 words each -->`).

- [ ] **Step 5: Implement `ghostwriter/scripts/validate_profile.py`** with the signatures and rules above.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add ghostwriter/references/profile-schema.md ghostwriter/references/tones/_template.md ghostwriter/scripts/validate_profile.py tests/test_ghostwriter.py
git commit -m "Add Ghostwriter profile schema, template, and validator" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Reference documents: AI tells and the two playbooks

**Files:**
- Create: `ghostwriter/references/ai-tells.md`
- Create: `ghostwriter/references/self-profile.md`
- Create: `ghostwriter/references/research-playbook.md`

**Interfaces:**
- Consumes: the humanizer pattern list at `~/.claude/skills/humanizer/SKILL.md` (29 numbered patterns), the scripts' CLIs from Tasks 2 to 4.
- Produces: files `SKILL.md` (Task 6) links to by relative path.

- [ ] **Step 1: Write `ghostwriter/references/ai-tells.md`**

A numbered list, exactly 29 entries, each one line: pattern name, words to watch, the fix. Keep humanizer's numbering and names. End with a "Soul check" paragraph (vary rhythm, hold opinions, let one aside in) and the two-prompt audit (`What makes the below so obviously AI generated?` then `Now make it not obviously AI generated.`). Credit line: "Condensed from blader/humanizer v2.5.1 (MIT) and Wikipedia's Signs of AI writing (WikiProject AI Cleanup)."

- [ ] **Step 2: Write `ghostwriter/references/self-profile.md`**

The `self` flow: check whether `<home>/tones/me.md` exists; run `python3 -I <skill>/scripts/build_corpus.py` then `python3 -I <skill>/scripts/style_stats.py <home>/corpus/me.corpus.jsonl`; read `me.stats.json` and `me.sample.md` (never the full corpus); draft the profile from the template with measured numbers in Rhythm and shape and Syntax and mechanics; show the user eight traits and six numbers, ask for corrections, then save and validate with `validate_profile.py`. The `sample` flow: `build_corpus.py --from-file PATH --slug <slug>` then the same steps, with `confidence: low` under 300 words of input. Refresh: rerun, replace the measured sections, keep Do / Don't, increment `version`. Tune: append one line to Do or Don't per piece of feedback, increment `version`; copy a shipped profile to `<home>/tones/` before the first tune.

- [ ] **Step 3: Write `ghostwriter/references/research-playbook.md`**

The `persona` flow: check both profile locations first; four search angles (interviews or transcripts, critical or linguistic analyses, official material from the writers or the person, fan wikis for catchphrases); the extraction grid mapped to the twelve sections; confidence rules (`high` with three or more independent sources covering lexicon and rhythm, `low` without web access); quotes under 15 words and at most 5; exemplars synthesized, under 40 words; intensity semantics (1 faint hints, 3 clearly recognizable, 5 full caricature; profanity only at 3 and above, and only when the persona swears); the real-person rule (style reference only, never presented as the person's words, fabricated statements or endorsements declined); save to `<home>/tones/<slug>.md` and validate.

- [ ] **Step 4: Verify**

Run:
```bash
grep -c '^[0-9]\{1,2\}\. ' ghostwriter/references/ai-tells.md
grep -c 'blader/humanizer' ghostwriter/references/ai-tells.md
grep -c 'build_corpus.py\|style_stats.py\|validate_profile.py' ghostwriter/references/self-profile.md
grep -c '15 words' ghostwriter/references/research-playbook.md
```
Expected: `29`, `1` or more, `3` or more, `1` or more.

- [ ] **Step 5: Commit**

```bash
git add ghostwriter/references/ai-tells.md ghostwriter/references/self-profile.md ghostwriter/references/research-playbook.md
git commit -m "Add Ghostwriter AI-tell list and profile playbooks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: SKILL.md, package files, and evals

**Files:**
- Create: `ghostwriter/SKILL.md`
- Create: `ghostwriter/LICENSE` (copy of `./LICENSE`)
- Create: `ghostwriter/agents/openai.yaml`
- Create: `ghostwriter/evals/evals.json`
- Modify: `tests/test_ghostwriter.py`

**Interfaces:**
- Consumes: every reference file and script name from Tasks 2 to 5, by relative path.

- [ ] **Step 1: Write the failing tests**

```python
class SkillPackage(unittest.TestCase):
    def test_skill_frontmatter(self):
        text = (ROOT / "ghostwriter/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front, body = text.split("---\n", 2)[1:]
        name = re.search(r"^name:\s*(\S+)", front, re.M)[1]
        self.assertEqual(name, "ghostwriter")
        description = re.search(r"^description:\s*(.+?)(?=^\S|\Z)", front, re.M | re.S)[1]
        self.assertTrue(1 <= len(description.strip()) <= 1024)
        self.assertLess(len(text.splitlines()), 500)
        for ref in ("references/ai-tells.md", "references/profile-schema.md", "references/self-profile.md",
                    "references/research-playbook.md", "scripts/build_corpus.py", "scripts/style_stats.py",
                    "scripts/validate_profile.py"):
            self.assertIn(ref, body)
            self.assertTrue((ROOT / "ghostwriter" / ref).exists(), ref)

    def test_license_copy_and_agent_metadata(self):
        self.assertEqual((ROOT / "ghostwriter/LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        yaml_text = (ROOT / "ghostwriter/agents/openai.yaml").read_text()
        self.assertIn('display_name: "Ghostwriter"', yaml_text)

    def test_evals_json(self):
        data = json.loads((ROOT / "ghostwriter/evals/evals.json").read_text())
        self.assertEqual(data["skill_name"], "ghostwriter")
        self.assertGreaterEqual(len(data["evals"]), 8)
        for case in data["evals"]:
            for key in ("id", "category", "prompt", "expected_output", "assertions"):
                self.assertIn(key, case)
            for assertion in case["assertions"]:
                self.assertEqual(set(assertion), {"text", "type"})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: FAIL with `FileNotFoundError` for `ghostwriter/SKILL.md`.

- [ ] **Step 3: Write `ghostwriter/SKILL.md`**

Front matter: `name: ghostwriter`; `description` (under 1024 characters) saying it drafts or rewrites replies, posts, and emails in a named voice with AI writing patterns removed, using stored tone profiles: the user's own voice built from their local Claude Code prompts, researched personas, or a supplied sample. Trigger phrases to include verbatim: "reply in my voice", "write this as me", "ghostwrite", "draft a reply", "draft a tweet", "in my tone", "as Deadpool", "in the style of", "tone profile", "humanize this as me". State it does not trigger for plain "humanize this text" with no voice named, and never posts or sends. Optional `license: MIT` and `metadata: {author: ayhammouda, version: "1.0"}`.

Body sections, in this order, each short: purpose (two sentences); where profiles live (user directory with `GHOSTWRITER_HOME`, shipped directory, shadowing); the seven-step workflow from the spec (resolve tone, load or create, understand the exchange, draft, audit tells, audit fidelity, deliver) with the create step pointing to `references/self-profile.md` and `references/research-playbook.md`; channel defaults and polish levels; intensity; profile management phrases (list, show, create, refresh, tune, delete) with the exact script commands; guardrails (drafts only, no invented stance or facts, real-person personas are style only, profile data stays in the user directory, language follows the exchange with a one-line fidelity note outside English); output format (final text only; "show your work" adds tells and profile checks). Under 200 lines.

- [ ] **Step 4: Copy the license and write the metadata and evals**

```bash
cp LICENSE ghostwriter/LICENSE
mkdir -p ghostwriter/agents ghostwriter/evals
```

`ghostwriter/agents/openai.yaml`:
```yaml
interface:
  display_name: "Ghostwriter"
  short_description: "Draft replies, posts, and emails in your voice or a researched persona"
```

`ghostwriter/evals/evals.json` in the Mentor format (`skill_name`, `version: "v1-tone-profiles"`, `evals`), eight cases: Reddit reply as `me`; email reply as `me`; tweet as `me` (assert under 280 characters); Deadpool at intensity 2 (assert no profanity) and 5; Morgan Freeman narrator; missing profile triggers creation and a confirmation question before saving; missing stance triggers one question, no invented opinion; request to post the result is declined with the draft still delivered. Assertion types: `structural`, `voice_fidelity`, `ai_tell_guard`, `guardrail`, `clarification`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B tests/test_ghostwriter.py`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add ghostwriter/SKILL.md ghostwriter/LICENSE ghostwriter/agents/openai.yaml ghostwriter/evals/evals.json tests/test_ghostwriter.py
git commit -m "Add Ghostwriter skill instructions, metadata, and evals" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Example persona: Deadpool

**Files:**
- Create: `ghostwriter/references/tones/deadpool.md`

**Interfaces:**
- Consumes: `references/research-playbook.md` (Task 5), `references/tones/_template.md` and `scripts/validate_profile.py` (Task 4).

- [ ] **Step 1: Research** with web search, following the playbook's four angles for the film Deadpool (Wade Wilson as written for the 2016 and 2018 films): fourth-wall breaks, pop-culture asides, self-deprecation, rapid tonal swings, profanity, nicknames for others. Collect at most 5 quotes, each under 15 words, and at least 3 source URLs for `sources`.

- [ ] **Step 2: Write the profile** from the template: `kind: persona`, `default_intensity: 3`, `confidence` per the playbook, `channels: [email, reddit, tweet, other]`. Channel dials describe how the voice compresses to a tweet and stretches in a Reddit thread. Four to six synthesized exemplars under 40 words. Provenance names the film variant and the intensity-to-profanity rule.

- [ ] **Step 3: Verify**

Run: `python3 -I ghostwriter/scripts/validate_profile.py ghostwriter/references/tones/deadpool.md && python3 -B tests/test_ghostwriter.py`
Expected: `OK ghostwriter/references/tones/deadpool.md`, then `OK`.

- [ ] **Step 4: Commit**

```bash
git add ghostwriter/references/tones/deadpool.md
git commit -m "Add Deadpool example tone profile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Example persona: Morgan Freeman, narrator

**Files:**
- Create: `ghostwriter/references/tones/morgan-freeman.md`

**Interfaces:** as Task 7.

- [ ] **Step 1: Research** the documentary-narrator persona (narration work such as "March of the Penguins" and "Through the Wormhole", public interviews): measured cadence, plain words, warmth, understatement, aphorism, pauses rendered as short sentences. Same quote and source limits as Task 7.

- [ ] **Step 2: Write the profile**: `kind: persona`, `default_intensity: 3`. Anti-tells must say the output is never presented as Morgan Freeman's own words and that endorsements or statements attributed to him are declined. Provenance names the narrator variant.

- [ ] **Step 3: Verify**

Run: `python3 -I ghostwriter/scripts/validate_profile.py --all --home /tmp/ghostwriter-empty-home && python3 -B tests/test_ghostwriter.py`
Expected: `OK` for `_template.md`, `deadpool.md`, `morgan-freeman.md`, then `OK`.

- [ ] **Step 4: Commit**

```bash
git add ghostwriter/references/tones/morgan-freeman.md
git commit -m "Add Morgan Freeman narrator example tone profile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Edit the README**

Add a `ghostwriter` row to the skills table ("Draft replies, posts, and emails in your own voice or a researched persona, with AI writing patterns removed, from stored tone profiles."). Add a "What Ghostwriter does" section after "What Mentor does": profiles, the three kinds, where they live, drafts only. Add to Requirements: Python 3 for the scripts, web search for persona research, read access to `~/.claude` for the `me` profile. Add `npx skills add ayhammouda/skills --skill ghostwriter` beside the other install commands and extend the manual-install sentence to include `ghostwriter/`. Add a "Ghostwriter" subsection under "Use the skills" with three example prompts (Reddit reply, email reply, tweet) and one persona example. Add to Verification: `python3 -B tests/test_ghostwriter.py` and `python3 -I ghostwriter/scripts/validate_profile.py --all`, and a sentence that the profile created on a machine lives in `~/.config/ghostwriter/` and is never part of the repository.

- [ ] **Step 2: Verify**

Run: `grep -c 'ghostwriter' README.md && python3 -B tests/test_ghostwriter.py`
Expected: a count of 8 or more, then `OK`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document the Ghostwriter skill" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Build Aymen's `me` profile (interactive)

**Files:**
- Create (outside the repository): `~/.config/ghostwriter/corpus/me.corpus.jsonl`, `me.stats.json`, `me.sample.md`, `~/.config/ghostwriter/tones/me.md`

**Interfaces:**
- Consumes: the scripts from Tasks 2 to 4 and `references/self-profile.md`.

- [ ] **Step 1: Extract and measure**

Run:
```bash
python3 -I ghostwriter/scripts/build_corpus.py
python3 -I ghostwriter/scripts/style_stats.py ~/.config/ghostwriter/corpus/me.corpus.jsonl
```
Expected: a JSON summary with `items` above 1,000, then `me.stats.json` and `me.sample.md` written.

- [ ] **Step 2: Draft the profile** by reading `me.stats.json` and `me.sample.md` only, following `references/self-profile.md`, into `~/.config/ghostwriter/tones/me.md` with `kind: self`, the `corpus` block filled from the stats, measured numbers in sections 3 and 5, channel dials for email `standard`, reddit `loose`, tweet `loose`, and three to six sanitized exemplars.

- [ ] **Step 3: Confirm with Aymen**: present eight traits and six numbers, apply his corrections to Do / Don't, then validate.

Run: `python3 -I ghostwriter/scripts/validate_profile.py ~/.config/ghostwriter/tones/me.md && stat -f '%Lp' ~/.config/ghostwriter ~/.config/ghostwriter/tones/me.md`
Expected: `OK …/me.md`, then `700` and `600`.

No commit: nothing in this task touches the repository.

---

### Task 11: End-to-end run and report

**Files:**
- Create: `docs/testing/2026-10-18-ghostwriter-e2e.md`

- [ ] **Step 1: Run three drafts as `me`** from inputs Aymen supplies (or, if he prefers, synthetic ones he approves): one Reddit reply, one email reply, one tweet. For each, run the tell audit against `references/ai-tells.md` and the fidelity audit against `me.md`; record pass or fail per audit and the character count of the tweet (must be under 280).

- [ ] **Step 2: Run one persona draft** (Deadpool at intensity 2) on the same Reddit input; record that it contains no profanity.

- [ ] **Step 3: Write the report** in the style of `docs/testing/2026-10-11-clean-project-e2e.md`: date, commit tested, Python version, corpus item count and date span, the six headline rates from `me.stats.json`, a table of the four drafts with pass/fail per audit, and the limits (one machine, one model). No exemplars, n-grams, project names, or draft text.

- [ ] **Step 4: Verify the whole branch**

Run: `python3 -B tests/test_git_safety.py && python3 -B tests/test_ghostwriter.py && node mentor/scripts/validate.mjs && python3 -I ghostwriter/scripts/validate_profile.py --all`
Expected: every command prints its success line and exits 0.

- [ ] **Step 5: Commit**

```bash
git add docs/testing/2026-10-18-ghostwriter-e2e.md
git commit -m "Document Ghostwriter end-to-end results" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Then tell Aymen the branch is ready for his pull request from `develop` to `main`; do not push.
