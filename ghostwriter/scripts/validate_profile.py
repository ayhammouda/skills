#!/usr/bin/env python3
"""Validate Ghostwriter tone profiles and list the profiles an agent can use.

A profile is Markdown with YAML front matter and twelve fixed sections; see
references/profile-schema.md. Profiles live in two places: the user directory
($GHOSTWRITER_HOME/tones, default ~/.config/ghostwriter/tones) and the shipped
directory (references/tones beside this script). A user profile shadows a
shipped one with the same slug.

Standard library only. Run as:
  python3 -I validate_profile.py PATH [PATH ...]   validate files
  python3 -I validate_profile.py --all             validate every profile
  python3 -I validate_profile.py --list            list slug, kind, location, path
"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import sys


SECTIONS = (
    "Identity and stance", "Register", "Rhythm and shape", "Lexicon", "Syntax and mechanics",
    "Devices", "Openers and closers", "Channel dials", "Do / Don't", "Exemplars", "Anti-tells",
    "Provenance",
)
CHANNELS = ("email", "reddit", "tweet", "other")
REQUIRED_KEYS = ("name", "slug", "kind", "version", "created", "updated", "language", "sources",
                 "confidence", "channels")
KINDS = ("self", "persona", "sample")
CONFIDENCE = ("low", "medium", "high")
CORPUS_KEYS = ("items", "words", "first", "last")
EXEMPLAR_MAX_WORDS = 39   # spec: "under 40 words"
QUOTE_MAX_WORDS = 14      # spec: quotes "under 15 words"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
QUOTE_RE = re.compile(r"[\"“]([^\"”\n]+)[\"”]")

# Same patterns as build_corpus.py; scripts stay self-contained under python3 -I.
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TOKEN_RE = re.compile(
    r"\b(?:sk-|ghp_|gho_|xox[abp]-|AKIA|AIza)[A-Za-z0-9_\-]{8,}"
    r"|(?<=Bearer\s)\S+"
    # A run of 32+ key-like characters, tested once at its start. A run with a slash and no
    # digit is a path such as references/research-playbook.md, not a key.
    r"|(?<![A-Za-z0-9+/_=\-])(?:(?=[A-Za-z+/_=\-]*\d)|(?![A-Za-z0-9+_=\-]*/))[A-Za-z0-9+/_=\-]{32,}"
)


COMMENT_RE = re.compile(r"(?:^|\s+)#.*$")   # YAML: a comment starts the value or follows whitespace
QUOTES = ('"', "'")


class Quoted(str):
    """A front-matter value written in quotes; messages show it with them."""

    def __new__(cls, value: str, quote: str):
        self = super().__new__(cls, value)
        self.quote = quote
        return self


def _shown(value) -> str:
    return f"{value.quote}{value}{value.quote}" if isinstance(value, Quoted) else str(value)


def _uncomment(value: str) -> str:
    """Drop a trailing comment, leaving a '#' inside a quoted value alone."""
    if value[:1] in QUOTES:
        closing = value.find(value[0], 1)
        if closing > 0:
            return value[:closing + 1] + COMMENT_RE.sub("", value[closing + 1:])
    return COMMENT_RE.sub("", value)


def _scalar(raw: str):
    """Parse one value: None when empty, a quoted or plain string, an int, or an inline list."""
    value = _uncomment(raw.strip())
    if not value:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in QUOTES:
        return Quoted(value[1:-1], value[0])
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(part) for part in inner.split(",")] if inner else []
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Return (mapping, body). Supports scalars, inline and block lists, one nested mapping."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing front matter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("missing front matter") from None
    data, key = {}, None
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] not in " \t":
            if ":" not in line:
                raise ValueError(f"line {number} is not 'key: value'")
            key, _, raw = line.partition(":")
            key = key.strip()
            data[key] = _scalar(raw)
            continue
        if key is None:
            raise ValueError(f"line {number} is indented without a parent key")
        item = line.strip()
        if item.startswith("- "):
            if data[key] is None:
                data[key] = []
            if not isinstance(data[key], list):
                raise ValueError(f"line {number} mixes a list into {key}")
            data[key].append(_scalar(item[2:]))
        else:
            if data[key] is None:
                data[key] = {}
            if not isinstance(data[key], dict) or ":" not in item:
                raise ValueError(f"line {number} is not a 'key: value' under {key}")
            sub, _, raw = item.partition(":")
            data[key][sub.strip()] = _scalar(raw)
    return data, "\n".join(lines[end + 1:])


def _sections(body: str) -> list[tuple[str, list[str]]]:
    sections, current = [], None
    for line in body.split("\n"):
        if line.startswith("## "):
            current = (line[3:].strip(), [])
            sections.append(current)
        elif current is not None:
            current[1].append(line)
    return sections


def _exemplars(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif items and line.strip() and line[:1] in " \t":
            items[-1] += " " + line.strip()
    return items


def _check_keys(data: dict, stem: str, template: bool) -> list[str]:
    problems = [f"missing key: {key}" for key in REQUIRED_KEYS if data.get(key) in (None, "")
                and not (key == "sources" and data.get(key) == [])]
    for key, allowed in (("kind", KINDS), ("confidence", CONFIDENCE)):
        if key in data and data[key] not in allowed:
            problems.append(f"invalid {key}: {_shown(data[key])}")
    if "version" in data and not (isinstance(data["version"], int) and data["version"] > 0):
        problems.append(f"invalid version: {_shown(data['version'])}")
    for key in ("created", "updated"):
        value = data.get(key)
        if value is not None:
            try:
                valid = bool(DATE_RE.match(str(value))) and bool(datetime.strptime(str(value), "%Y-%m-%d"))
            except ValueError:
                valid = False
            if not valid:
                problems.append(f"invalid {key}: {_shown(value)}")
    for key in ("sources", "channels"):
        if data.get(key) is not None and not isinstance(data[key], list):
            problems.append(f"invalid {key}: expected a list")
    slug = data.get("slug")
    if slug is not None:
        if str(slug) != stem:
            problems.append("slug does not match filename")
        elif not template and not SLUG_RE.match(str(slug)):
            problems.append(f"invalid slug: {_shown(slug)}")
    if data.get("kind") == "persona":
        intensity = data.get("default_intensity")
        if intensity is None:
            problems.append("missing key: default_intensity")
        elif not (isinstance(intensity, int) and 1 <= intensity <= 5):
            problems.append(f"invalid default_intensity: {_shown(intensity)}")
    if data.get("kind") == "self":
        corpus = data.get("corpus") if isinstance(data.get("corpus"), dict) else {}
        problems += [f"missing key: corpus.{key}" for key in CORPUS_KEYS if corpus.get(key) in (None, "")]
    return problems


def _check_body(body: str, kind, template: bool) -> list[str]:
    problems = []
    sections = _sections(body)
    titles = [title for title, _ in sections]
    problems += [f"missing heading: {title}" for title in SECTIONS if title not in titles]
    problems += [f"unexpected heading: {title}" for title in titles if title not in SECTIONS]
    problems += [f"duplicate heading: {title}" for title in SECTIONS if titles.count(title) > 1]
    present = [title for title in titles if title in SECTIONS]
    if present != sorted(present, key=SECTIONS.index):
        problems.append("headings out of order")
    content = {title: lines for title, lines in sections}
    if "Channel dials" in content:
        subsections = {line[4:].strip().lower() for line in content["Channel dials"] if line.startswith("### ")}
        problems += [f"missing channel: {name}" for name in CHANNELS if name not in subsections]
    if not template and "Exemplars" in content:
        items = _exemplars(content["Exemplars"])
        if not 3 <= len(items) <= 6:
            problems.append(f"exemplar count {len(items)} (need 3 to 6)")
        for index, item in enumerate(items, start=1):
            size = len(item.split())
            if size > EXEMPLAR_MAX_WORDS:
                problems.append(f"exemplar {index} has {size} words (max {EXEMPLAR_MAX_WORDS})")
    if not template and kind == "persona":
        for quote in QUOTE_RE.findall(body):
            size = len(quote.split())
            if size > QUOTE_MAX_WORDS:
                problems.append(f"quote of {size} words (max {QUOTE_MAX_WORDS})")
    for pattern, label in ((EMAIL_RE, "email"), (URL_RE, "url"), (TOKEN_RE, "token")):
        if pattern.search(body):
            problems.append(f"{label} in body")
    return problems


def _permission_problems(path: Path, home: Path | None) -> list[str]:
    """Profiles under the user directory must be regular files private to their owner (POSIX only).

    Paths are compared without following symlinks, so a link inside the user
    directory is reported instead of silently checking (or skipping) its target.
    """
    if home is None or os.name == "nt":
        return []
    absolute, root = Path(os.path.abspath(path)), Path(os.path.abspath(home))
    if root not in absolute.parents:
        return []
    problems = []
    try:
        if absolute.is_symlink():
            return [f"symlink in user directory, expected a regular file: {path}"]
        directory_mode = absolute.parent.stat().st_mode & 0o777
        if directory_mode & 0o077:
            problems.append(f"directory mode {directory_mode:o}, expected 700 (chmod 700 {absolute.parent})")
        mode = absolute.stat().st_mode & 0o777
        if mode & 0o077:
            problems.append(f"mode {mode:o}, expected 600 (chmod 600 {path})")
    except OSError:
        return problems
    return problems


def validate(path: Path, home: Path | None = None) -> list[str]:
    """Return the problems found in one profile; an empty list means valid."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        return [f"unreadable: {error}"]
    try:
        data, body = parse_front_matter(text)
    except ValueError as error:
        return [str(error) if str(error) == "missing front matter" else f"invalid front matter: {error}"]
    template = path.stem.startswith("_")
    return (_check_keys(data, path.stem, template) + _check_body(body, data.get("kind"), template)
            + _permission_problems(path, home))


def _profiles(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        return {}
    return {path.stem: path for path in sorted(directory.glob("*.md")) if not path.stem.startswith("_")}


def _kind(path: Path) -> str:
    try:
        data, _ = parse_front_matter(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError):
        return "?"
    return str(data.get("kind", "?"))


def list_profiles(home: Path, shipped: Path) -> list[tuple[str, str, str, str]]:
    """Return (slug, kind, location, path) per profile, the user directory shadowing shipped."""
    user, bundled = _profiles(home / "tones"), _profiles(shipped)
    rows = []
    for slug in sorted(set(user) | set(bundled)):
        if slug in user:
            location = "user (shadows shipped)" if slug in bundled else "user"
            rows.append((slug, _kind(user[slug]), location, str(user[slug])))
        else:
            rows.append((slug, _kind(bundled[slug]), "shipped", str(bundled[slug])))
    return rows


def _default_home() -> Path:
    raw = os.environ.get("GHOSTWRITER_HOME")
    return Path(os.path.expanduser(raw)) if raw else Path.home() / ".config" / "ghostwriter"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--all", action="store_true", help="validate every user and shipped profile")
    parser.add_argument("--list", action="store_true",
                        help="list slug, kind, location, and path, tab-separated")
    parser.add_argument("--home", type=Path, default=None,
                        help="default: $GHOSTWRITER_HOME or ~/.config/ghostwriter")
    parser.add_argument("--shipped", type=Path, default=Path(__file__).resolve().parent.parent / "references/tones")
    args = parser.parse_args(argv)
    home = args.home.expanduser() if args.home else _default_home()
    shipped = args.shipped.expanduser()
    if args.list:
        for row in list_profiles(home, shipped):
            print("\t".join(row))
    targets = [path.expanduser() for path in args.paths]
    if args.all:
        for directory in (home / "tones", shipped):
            if directory.is_dir():
                targets += sorted(directory.glob("*.md"))
    if not targets:
        if args.list:
            return 0
        parser.print_usage(sys.stderr)
        return 2
    failed = False
    for path in targets:
        problems = validate(path, home)
        if problems:
            failed = True
            for problem in problems:
                print(f"FAIL {path}: {problem}")
        else:
            print(f"OK {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
