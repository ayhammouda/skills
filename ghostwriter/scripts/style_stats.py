#!/usr/bin/env python3
"""Measure a Ghostwriter corpus and draw a reading sample from it.

Reads a corpus written by build_corpus.py (one JSON object per line with text,
source, timestamp, project). Writes <base>.stats.json with stylometric counts
and rates, and <base>.sample.md with a fixed-seed sample stratified by length
and date, for an agent to read instead of the full corpus. Both files are
created with owner-only permissions.

Standard library only. Run as: python3 -I style_stats.py CORPUS [options]
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from math import ceil
import os
from pathlib import Path
import random
import re
import statistics
import sys
import tempfile


WORD_RE = re.compile(r"[A-Za-zÀ-ſ][A-Za-zÀ-ſ'’]*")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
CONTRACTION_RE = re.compile(r"\b\w+['’](s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
PLACEHOLDER_RE = re.compile(r"<(?:URL|EMAIL|TOKEN|IP|PHONE)>")

ENGLISH = set("the a an and to of is it that for you this with on are be i we can in".split())
FRENCH = set("le la les des une est pas pour que qui dans avec sur je tu nous vous et ou mais donc".split())
STOPWORDS = ENGLISH | set(
    "me my your our it's its as at by from or if so not do have has was were will would just".split())
IMPERATIVES = set("""add make fix create update remove delete check run use write show give generate
implement analyze review explain look find try keep put move change test build start stop open close
read search list help do go bring export plan prepare clean set install deploy commit push merge rename
replace refactor document describe compare verify ensure continue proceed apply convert fetch pull save
send think""".split())
MARKERS = {
    "please": r"\bplease\b", "thanks": r"\bthanks\b", "like": r"\blike\b",
    "basically": r"\bbasically\b", "actually": r"\bactually\b", "just": r"\bjust\b",
    "i think": r"\bi think\b", "maybe": r"\bmaybe\b", "kind of": r"\bkind of\b",
    "let's": r"\blet['’]s\b",
}
LENGTHS = ("short", "medium", "long")
HALVES = ("older", "newer")


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(PLACEHOLDER_RE.sub(" ", text))]


def sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part and part.strip()]


def _p90(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[ceil(0.9 * len(ordered)) - 1]


def _summary(values: list[int]) -> dict:
    return {"mean": round(statistics.mean(values), 2), "median": round(statistics.median(values), 2),
            "p90": _p90(values)}


def _rate(flags) -> float:
    flags = list(flags)
    return round(sum(flags) / len(flags), 3) if flags else 0.0


def _spacing(texts: list[str], mark: str) -> float:
    total = sum(t.count(mark) for t in texts)
    spaced = sum(t.count(" " + mark) for t in texts)
    return round(spaced / total, 3) if total else 0.0


def _language(tokens: list[str]) -> str:
    if not tokens:
        return "other"
    english = sum(t in ENGLISH for t in tokens) / len(tokens)
    french = sum(t in FRENCH for t in tokens) / len(tokens)
    label, share = ("en", english) if english >= french else ("fr", french)
    return label if share > 0.12 else "other"


def _first_alpha_lower(text: str) -> bool:
    for char in text:
        if char.isalpha():
            return char.islower()
    return False


def _pairs(counter: Counter, limit: int) -> list[list]:
    return [[key, count] for key, count in counter.most_common(limit)]


def compute_stats(items: list[dict]) -> dict:
    texts = [PLACEHOLDER_RE.sub(" ", item["text"]).strip() for item in items]
    tokens = [words(text) for text in texts]
    sentence_lengths = [len(words(s)) for t in texts for s in sentences(t) if words(s)]
    dated = sorted(item["timestamp"] for item in items if item.get("timestamp"))
    language = Counter(_language(t) for t in tokens)
    unigrams, bigrams, trigrams, openers, closers = Counter(), Counter(), Counter(), Counter(), Counter()
    for toks in tokens:
        unigrams.update(t for t in toks if t not in STOPWORDS)
        bigrams.update(" ".join(toks[i:i + 2]) for i in range(len(toks) - 1))
        trigrams.update(" ".join(toks[i:i + 3]) for i in range(len(toks) - 2))
        if toks:
            openers[" ".join(toks[:2])] += 1
            closers[" ".join(toks[-3:])] += 1
    lowered = [t.lower() for t in texts]
    item_lengths = [len(t) for t in tokens] or [0]
    return {
        "items": len(items),
        "words": sum(len(t) for t in tokens),
        "sources": dict(Counter(item.get("source") for item in items)),
        "date_span": {"first": dated[0] if dated else None, "last": dated[-1] if dated else None},
        "language": {key: language.get(key, 0) for key in ("en", "fr", "other")},
        "item_words": {**_summary(item_lengths), "max": max(item_lengths)},
        "sentence_length": {"count": len(sentence_lengths),
                            **(_summary(sentence_lengths) if sentence_lengths
                               else {"mean": 0, "median": 0, "p90": 0})},
        "rates": {
            "lowercase_start": _rate(_first_alpha_lower(t) for t in texts),
            "no_terminal_punct": _rate(t.rstrip()[-1:] not in ".!?" for t in texts),
            "question": _rate("?" in t for t in texts),
            "exclamation": _rate("!" in t for t in texts),
            "ellipsis": _rate("..." in t or "…" in t for t in texts),
            "em_dash": _rate("—" in t for t in texts),
            "emoji": _rate(bool(EMOJI_RE.search(t)) for t in texts),
            "contraction": _rate(bool(CONTRACTION_RE.search(t)) for t in texts),
            "imperative_start": _rate(bool(t) and t[0] in IMPERATIVES for t in tokens),
            "space_before_question": _spacing(texts, "?"),
            "space_before_colon": _spacing(texts, ":"),
            "space_before_exclaim": _spacing(texts, "!"),
        },
        "markers": {name: sum(len(re.findall(pattern, t)) for t in lowered)
                    for name, pattern in MARKERS.items()},
        "top_words": _pairs(unigrams, 50),
        "top_bigrams": _pairs(bigrams, 25),
        "top_trigrams": _pairs(trigrams, 25),
        "top_openers": _pairs(openers, 20),
        "top_closers": _pairs(closers, 20),
    }


def _length_bucket(items: list[dict]):
    counts = sorted(len(words(item["text"])) for item in items)
    low = counts[max(0, ceil(0.33 * len(counts)) - 1)]
    high = counts[max(0, ceil(0.67 * len(counts)) - 1)]

    def bucket(item: dict) -> str:
        size = len(words(item["text"]))
        return "short" if size < low else "long" if size > high else "medium"
    return bucket


def stratified_sample(items: list[dict], size: int, seed: int) -> list[dict]:
    """Pick up to size items, round-robin over length terciles and older/newer halves."""
    if not items or size <= 0:
        return []
    bucket = _length_bucket(items)
    dated = sorted(item["timestamp"] for item in items if item.get("timestamp"))
    middle = dated[len(dated) // 2] if dated else None
    groups = {(length, half): [] for length in LENGTHS for half in HALVES}
    for item in items:
        stamp = item.get("timestamp")
        half = "older" if middle and stamp and stamp < middle else "newer"
        groups[(bucket(item), half)].append(item)
    rng = random.Random(seed)
    for key in groups:
        rng.shuffle(groups[key])
    picked = []
    while len(picked) < size and any(groups.values()):
        for key in groups:
            if groups[key] and len(picked) < size:
                picked.append(groups[key].pop())
    return picked


def render_sample(items: list[dict], stats: dict, picked: list[dict]) -> str:
    bucket = _length_bucket(items)
    span = stats["date_span"]
    first = span["first"][:10] if span["first"] else "undated"
    last = span["last"][:10] if span["last"] else "undated"
    lines = ["# Writing sample", "",
             f"Corpus items: {stats['items']}. Dates: {first} to {last}. Sampled items: {len(picked)}.",
             "Read these for voice. Placeholders such as <URL> replace scrubbed details."]
    for length in LENGTHS:
        chosen = sorted((item for item in picked if bucket(item) == length),
                        key=lambda item: (item.get("timestamp") or "9999", item["text"]))
        lines += ["", f"## {length}"]
        if not chosen:
            lines.append("(none)")
        for item in chosen:
            date = item["timestamp"][:10] if item.get("timestamp") else "undated"
            lines.append(f"- ({item.get('source')}, {date}, {len(words(item['text']))} words) {item['text']}")
    return "\n".join(lines) + "\n"


def _write_private(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _load(path: Path) -> list[dict]:
    items = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and isinstance(record.get("text"), str) and record["text"].strip():
                items.append(record)
    return items


def _defaults(corpus: Path) -> tuple[Path, Path]:
    name = corpus.name
    base = name[:-len(".corpus.jsonl")] if name.endswith(".corpus.jsonl") else corpus.stem
    return corpus.parent / f"{base}.stats.json", corpus.parent / f"{base}.sample.md"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--stats-out", type=Path, default=None)
    parser.add_argument("--sample-out", type=Path, default=None)
    parser.add_argument("--sample-size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    corpus = args.corpus.expanduser()
    if not corpus.is_file():
        print(f"error: corpus not found: {corpus}", file=sys.stderr)
        return 1
    items = _load(corpus)
    if not items:
        print("empty corpus: nothing to measure", file=sys.stderr)
        return 2
    stats_out, sample_out = _defaults(corpus)
    stats_out = args.stats_out.expanduser() if args.stats_out else stats_out
    sample_out = args.sample_out.expanduser() if args.sample_out else sample_out
    stats = compute_stats(items)
    picked = stratified_sample(items, args.sample_size, args.seed)
    _write_private(stats_out, json.dumps(stats, indent=2, ensure_ascii=False) + "\n")
    _write_private(sample_out, render_sample(items, stats, picked))
    print(json.dumps({"items": stats["items"], "words": stats["words"], "sampled": len(picked),
                      "stats": str(stats_out), "sample": str(sample_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
