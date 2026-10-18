# Tone profile schema

A tone profile is one Markdown file that describes how one voice writes. Drafting reads it, and `scripts/validate_profile.py` checks it. This file is the single source of truth for the format.

## Where profiles live

- **User directory:** `$GHOSTWRITER_HOME/tones/<slug>.md`, default `~/.config/ghostwriter/tones/`. Every profile created on this machine goes here, including the person's own. Directories are mode 700 and files mode 600.
- **Shipped directory:** `references/tones/` inside the skill. It holds the examples and `_template.md`, and stays unchanged at runtime.
- **Drafts:** a new or rebuilt profile is written to `$GHOSTWRITER_HOME/drafts/<slug>.md`, validated there, and moved to `tones/` once the person confirms it.
- **Lookup:** user directory first, then shipped. A user profile shadows a shipped profile with the same slug.
- **Slugs:** lowercase letters, digits, and hyphens. The person's own voice is `me`.

List what exists with `python3 -I scripts/validate_profile.py --list`.

## Front matter

| Key | Type | Values |
| --- | --- | --- |
| `name` | text | Display name. |
| `slug` | text | The file name without `.md`. |
| `kind` | text | `self` (the person's own prompts), `persona` (researched), or `sample` (text the person supplied). |
| `version` | integer | Starts at 1 and increases by 1 on every edit. |
| `created`, `updated` | date | `YYYY-MM-DD`. |
| `language` | text | Main language code, such as `en`. |
| `sources` | list | Where the profile came from. URLs belong here and nowhere else in the file. |
| `confidence` | text | `low`, `medium`, or `high`. |
| `channels` | list | Channels the dials cover: `email`, `reddit`, `tweet`, `other`. |
| `default_intensity` | integer | Persona only: 1 to 5. |
| `corpus` | mapping | Self only: `items`, `words`, `first`, `last`, copied from `<slug>.stats.json`. |

## Sections

Twelve `## ` sections, all present, in this order:

1. **Identity and stance:** who is speaking, their attitude toward the reader, what they care about.
2. **Register:** formality, warmth, directness, humor, confidence, hedging habits.
3. **Rhythm and shape:** sentence and reply length, paragraphing, fragments, lists versus prose. Self profiles quote the measured numbers.
4. **Lexicon:** signature words and phrases, verbal tics, connectors, intensifiers, swearing level, and words this voice avoids.
5. **Syntax and mechanics:** contractions, capitalization, punctuation habits, emoji, and how natural slips appear. Self profiles quote the measured rates.
6. **Devices:** how the voice explains, argues, jokes, and refers to things.
7. **Openers and closers:** how replies start and end, per channel where they differ.
8. **Channel dials:** `### email`, `### reddit`, `### tweet`, `### other`, each a line with `length`, `formality`, `polish`, and `sign-off`.
9. **Do / Don't:** short, testable lines. Feedback from use is appended here.
10. **Exemplars:** three to six list items, each under 40 words.
11. **Anti-tells:** what would expose the text as AI-written or as not this voice, beyond `references/ai-tells.md`.
12. **Provenance:** how and when the profile was built, when to refresh it, and known gaps.

## Polish levels

- **loose:** lowercase openers, casual punctuation, and unfinished endings, where the voice uses them.
- **standard:** sentence case and normal punctuation; the voice's words and rhythm stay.
- **clean:** proofread prose for readers who expect it.

The polish for a draft comes from the request, then the profile's channel dial, then the channel defaults in `SKILL.md`. Every level keeps spelling correct: authenticity comes from word choice and rhythm.

## Intensity

Persona profiles carry `default_intensity`, and a request may set another value from 1 to 5. At 1 the voice is a faint flavor on the person's message; at 3 it is clearly recognizable; at 5 it is full caricature. Profanity appears only at 3 and above, and only for a voice that swears.

## Content rules

- **Exemplars:** self and sample profiles use sanitized real passages or close paraphrases. Persona profiles use passages synthesized in the style, written without quotation marks. Exemplars carry no names, emails, URLs, keys, or project names.
- **Quotes:** a persona profile quotes at most five short lines from its source, each under 15 words.
- **Real people:** a persona of a real person describes style. Drafts in that style are the person's own message, never words attributed to the real person.
- **Secrets:** the body holds no emails, URLs, or secret-like strings; validation fails on them.

## Editing

- Every edit increases `version` and sets `updated` to today.
- Tuning appends one Do / Don't line per piece of feedback.
- Tuning a shipped profile first copies it to the user directory; the shipped file stays unchanged.
- Validate after every write: `python3 -I scripts/validate_profile.py <path>`.
