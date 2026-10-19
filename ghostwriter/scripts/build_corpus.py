#!/usr/bin/env python3
"""Build a writing corpus for a Ghostwriter tone profile.

Default source: local Claude Code prompts, read from ~/.claude/history.jsonl
(the "display" field only, never pasted contents) and from session transcripts
one level under ~/.claude/projects/ (subagent transcripts are never read).
With --from-file, the paragraphs of one text file are used instead.

The script keeps text the person typed. It removes harness blocks, pasted
material, quoted lines, code, and logs; drops machine-written prompts; scrubs
emails, URLs, phone numbers, IP addresses, and secrets; deduplicates; and
writes <out-dir>/<slug>.corpus.jsonl with owner-only permissions.

Standard library only. Run as: python3 -I build_corpus.py [options]
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import chain
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Iterator


HARNESS_TAGS = (
    "system-reminder", "task-notification", "pasted_content", "command-name",
    "command-message", "command-args", "local-command-stdout", "local-command-stderr",
    "local-command-caveat", "side-sessions-event", "ci-monitor-event", "ide_selection",
    "ide_opened_file", "user-prompt-submit-hook",
)
_TAG_ALTERNATION = "|".join(re.escape(tag) for tag in HARNESS_TAGS)
BLOCK_RE = re.compile(rf"<({_TAG_ALTERNATION})\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
OPEN_TAG_RE = re.compile(rf"<(?:{_TAG_ALTERNATION})\b[^>]*>", re.IGNORECASE)
CLOSE_TAG_RE = re.compile(rf"</(?:{_TAG_ALTERNATION})\s*>", re.IGNORECASE)
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
MARKER_RE = re.compile(r"\[(?:Pasted text #\d+(?: \+\d+ lines)?|Image #\d+)\]")
MARKUP_RE = re.compile(r"<[a-z][a-z0-9_-]*(\s[^<>]*)?/?>")

QUOTE_LINE_RE = re.compile(r"^\s*>")
INTERRUPT_LINE_RE = re.compile(r"^\s*\[Request interrupted")
LOG_LINE_RE = re.compile(
    r"^\s*(?:\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}"
    r"|\[\d"
    r"|at \S+(?: \(.*\))?:\d+"
    r"|at \S+ \("
    r"|Traceback \(most recent call last\)"
    r"|\w*(?:Error|Exception): "
    r"|(?:WARN|WARNING|INFO|DEBUG|ERROR)\b)"
)
CODE_LINE_RE = re.compile(
    r"""^\s*(?:
        import\s+[\w.]+(?:\s*,\s*[\w.]+)*(?:\s+as\s+\w+)?\s*;?\s*$
      | import\s.+\sfrom\s+['"]
      | from\s+[\w.]+\s+import\s
      | (?:def|class)\s+\w+\s*[(:]
      | (?:const|let|var)\s+[\w$]+\s*=
      | function\b\s*[\w$]*\s*\(
      | \$\s
      | \#!/
      | [{}]
    )""",
    re.VERBOSE,
)
PROSE_PUNCTUATION = set("'’‘\",.?!:;()-–—…/<>")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TOKEN_RE = re.compile(
    r"\b(?:sk-|ghp_|gho_|xox[abp]-|AKIA|AIza)[A-Za-z0-9_\-]{8,}"
    r"|(?<=Bearer\s)\S+"
    r"|[A-Za-z0-9+/_=\-]{32,}"
)
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
PHONE_RE = re.compile(r"\+?\d(?:[ .]?\d){8,14}")

DROP_REASONS = ("slash", "short", "long", "markup", "duplicate", "skipped_record", "before_since")
SKIP_REASONS = ("malformed", "sidechain", "meta", "compact", "sdk", "origin")


@dataclass
class Item:
    text: str
    source: str
    timestamp: str | None
    project: str | None


def _symbol_heavy(line: str) -> bool:
    chars = [c for c in line if not c.isspace()]
    if len(chars) < 4:
        return False
    outside = sum(1 for c in chars
                  if not (c.isalnum() or c in PROSE_PUNCTUATION or EMOJI_RE.match(c)))
    return outside / len(chars) > 0.30


def _keep_line(line: str) -> bool:
    return not (QUOTE_LINE_RE.match(line) or INTERRUPT_LINE_RE.match(line)
                or LOG_LINE_RE.match(line) or CODE_LINE_RE.match(line) or _symbol_heavy(line))


def clean_text(text: str) -> str:
    """Return the person's own words from one prompt, on a single line."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = BLOCK_RE.sub(" ", text)
    text = CLOSE_TAG_RE.sub(" ", text)
    unclosed = OPEN_TAG_RE.search(text)
    if unclosed:
        text = text[:unclosed.start()]
    text = FENCE_RE.sub("\n", text)
    if "```" in text:
        text = text[:text.index("```")]
    text = MARKER_RE.sub(" ", text)
    kept = [line for line in text.split("\n") if _keep_line(line)]
    return re.sub(r"\s+", " ", "\n".join(kept)).strip()


def scrub(text: str) -> str:
    """Replace contact details and secret-like strings with placeholders."""
    text = URL_RE.sub("<URL>", text)
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = TOKEN_RE.sub("<TOKEN>", text)
    text = IP_RE.sub("<IP>", text)
    return PHONE_RE.sub("<PHONE>", text)


def normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _iso_from_ms(value) -> str | None:
    try:
        moment = datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_from_string(value) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json_lines(path: Path, counts: Counter):
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                counts["skipped_record"] += 1
                counts["skip_malformed"] += 1
                continue
            if isinstance(record, dict):
                yield record


def iter_history(path: Path, counts: Counter | None = None) -> Iterator[Item]:
    """Yield prompts from history.jsonl, skipping slash commands."""
    counts = Counter() if counts is None else counts
    for row in _read_json_lines(path, counts):
        counts["history_rows"] += 1
        display = row.get("display")
        if not isinstance(display, str):
            continue
        if display.lstrip().startswith("/"):
            counts["slash"] += 1
            continue
        stamp = row.get("timestamp")
        timestamp = _iso_from_ms(stamp) if isinstance(stamp, (int, float)) else _iso_from_string(stamp)
        project = row.get("project")
        yield Item(display, "history", timestamp,
                   Path(project).name if isinstance(project, str) and project else None)


def _skip_reason(record: dict) -> str | None:
    """Name why a user record was not typed by the person, or None when it was."""
    for flag, reason in (("isSidechain", "sidechain"), ("isMeta", "meta"), ("isCompactSummary", "compact")):
        if record.get(flag):
            return reason
    entrypoint = record.get("entrypoint")
    if isinstance(entrypoint, str) and entrypoint.startswith("sdk-"):
        return "sdk"
    origin = record.get("origin")
    if isinstance(origin, dict) and "kind" in origin and origin["kind"] != "human":
        return "origin"
    return None


def iter_transcripts(projects_dir: Path, counts: Counter | None = None) -> Iterator[Item]:
    """Yield typed user turns from session transcripts one level under projects_dir."""
    counts = Counter() if counts is None else counts
    for path in sorted(projects_dir.glob("*/*.jsonl")):
        for record in _read_json_lines(path, counts):
            if record.get("type") != "user":
                continue
            message = record.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                blocks = [b for b in content if isinstance(b, dict)]
                if any(b.get("type") == "tool_result" for b in blocks):
                    continue
                text = " ".join(b.get("text", "") for b in blocks
                                if b.get("type") == "text" and isinstance(b.get("text"), str))
            elif isinstance(content, str):
                text = content
            else:
                continue
            counts["transcript_records"] += 1
            reason = _skip_reason(record)
            if reason:
                counts["skipped_record"] += 1
                counts[f"skip_{reason}"] += 1
                continue
            cwd = record.get("cwd")
            project = Path(cwd).name if isinstance(cwd, str) and cwd else path.parent.name
            yield Item(text, "transcript", _iso_from_string(record.get("timestamp")), project)


def iter_sample(path: Path) -> Iterator[Item]:
    """Yield each blank-line-separated paragraph of a text file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    for paragraph in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        if paragraph.strip():
            yield Item(paragraph, "sample", None, None)


def _ensure_private_dir(path: Path, tighten_existing: bool = False) -> None:
    """Create path and its missing parents with mode 0o700.

    An existing leaf directory keeps its mode unless tighten_existing is set,
    which the default location under the Ghostwriter home opts into; a
    user-chosen --out-dir is never re-permissioned.
    """
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        os.chmod(directory, 0o700)
    if not missing and tighten_existing and os.name != "nt":
        if path.stat().st_mode & 0o077:
            os.chmod(path, 0o700)


def _write_private(path: Path, items: list[Item], tighten_dir: bool = False) -> None:
    _ensure_private_dir(path.parent, tighten_existing=tighten_dir)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def build(claude_dir: Path, out_dir: Path, slug: str, since: str | None, min_words: int,
          max_words: int, from_file: Path | None, tighten_dir: bool = False) -> dict:
    counts = Counter()
    if from_file is not None:
        source = iter_sample(from_file)
    else:
        source = chain(iter_history(claude_dir / "history.jsonl", counts),
                       iter_transcripts(claude_dir / "projects", counts))
    dropped = dict.fromkeys(DROP_REASONS, 0)
    seen, kept = set(), []
    for item in source:
        text = clean_text(item.text)
        if MARKUP_RE.search(text):
            dropped["markup"] += 1
            continue
        text = scrub(text)
        words = len(text.split())
        if words < min_words:
            dropped["short"] += 1
            continue
        if words > max_words:
            dropped["long"] += 1
            continue
        if since and (item.timestamp is None or item.timestamp[:10] < since):
            dropped["before_since"] += 1
            continue
        key = normalize_key(text)
        if key in seen:
            dropped["duplicate"] += 1
            continue
        seen.add(key)
        kept.append(Item(text, item.source, item.timestamp, item.project))
    dropped["slash"] = counts["slash"]
    dropped["skipped_record"] = counts["skipped_record"]
    out_path = out_dir / f"{slug}.corpus.jsonl"
    if kept:
        _write_private(out_path, kept, tighten_dir=tighten_dir)
    return {"items": len(kept), "history_rows": counts["history_rows"],
            "transcript_records": counts["transcript_records"], "dropped": dropped,
            "skipped": {reason: counts[f"skip_{reason}"] for reason in SKIP_REASONS},
            "out": str(out_path)}


def _default_home() -> Path:
    raw = os.environ.get("GHOSTWRITER_HOME")
    return Path(os.path.expanduser(raw)) if raw else Path.home() / ".config" / "ghostwriter"


def _date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from None
    return value


def _slug(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
        raise argparse.ArgumentTypeError("slug must be lowercase letters, digits, and hyphens")
    return value


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--claude-dir", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="default: $GHOSTWRITER_HOME/corpus or ~/.config/ghostwriter/corpus")
    parser.add_argument("--slug", type=_slug, default="me")
    parser.add_argument("--since", type=_date, default=None)
    parser.add_argument("--min-words", type=int, default=3)
    parser.add_argument("--max-words", type=int, default=400)
    parser.add_argument("--from-file", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.min_words < 1 or args.max_words < args.min_words:
        parser.error("need 1 <= --min-words <= --max-words")
    if args.from_file is not None and not args.from_file.is_file():
        print(f"error: {args.from_file} is not a readable file", file=sys.stderr)
        return 1
    out_dir = args.out_dir.expanduser() if args.out_dir else _default_home() / "corpus"
    summary = build(args.claude_dir.expanduser(), out_dir, args.slug, args.since,
                    args.min_words, args.max_words, args.from_file, tighten_dir=args.out_dir is None)
    print(json.dumps(summary))
    if summary["items"] == 0:
        print("no items survived the filters; nothing written", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
