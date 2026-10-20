# Ghostwriter end-to-end results

**PASS — 2026-10-18.** Tested skill commit [`49289e2`](https://github.com/ayhammouda/skills/commit/49289e2) on macOS with Python 3.14.5; the test suite also passed on Python 3.9.6, 3.12.13, and 3.13.7. Four fresh agents, each reading `SKILL.md` cold, drafted one message each on the author's machine. The author's `me` profile was built from his own Claude Code prompts in the same session, reviewed by him, and saved before the drafts. No real correspondence was used: the inputs were synthetic messages written for the test. Nothing was posted or sent.

## Corpus and profile

The `me` profile was built by `scripts/build_corpus.py` and `scripts/style_stats.py` from the local Claude Code history and session transcripts, after dropping slash commands, machine-written turns (SDK sessions, task notifications, compaction summaries, metadata records), pasted markup, code, and logs.

| Measure | Value |
| --- | --- |
| Messages in corpus | 741 |
| Words | 14,292 |
| Date span | 2026-01-30 to 2026-10-18 |
| Median message length | 12 words |
| Messages starting lowercase | 78% |
| Question marks preceded by a space | 74% |
| Colons preceded by a space | 69% |
| Messages without final punctuation | 64% |
| Messages with a contraction | 26% |
| Messages with an exclamation mark | 1% |
The author confirmed eight traits and three defaults (email sign-off, a closing thanks allowed in email, French spacing kept in email) before the profile moved from the drafts directory to the tones directory. Validation passed, including the owner-only permission check.

## Drafts

Each draft was audited twice: mechanically, against the reply tells in `references/ai-tells.md` (praise openers, closing offers, placeholders, em dashes, emoji, hashtags, AI vocabulary) and the output contract (one fenced block, nothing after it); and by reading, against the profile's Do / Don't lines and the points the user asked the draft to make.

| Draft | Channel dial | Tell audit | Fidelity audit | Content check |
| --- | --- | --- | --- | --- |
| Reddit reply as `me` | loose, 27 words, one line | pass (12 checks) | pass: lowercase opener, comma-chained clauses, no final punctuation, "though" closer | both points present, nothing added |
| Email reply as `me` | standard, 42 words, 4 sentences | pass (12 checks) | pass: sentence case, "let's", "can we do that instead ?", colon spacing, signed Aymen with the confirmed closing thanks | Thursday afternoon proposed, remote-first question asked, no invented availability |
| Tweet as `me` | loose, 82 characters | pass (12 checks, under 280) | pass: lowercase opener, colon spacing, no hashtag or emoji | describes only what the user said the skill does; LINK placed |
| Reddit reply as `deadpool`, intensity 2 | loose, 54 words, two short paragraphs | pass (11 checks, no profanity) | pass: one pet name, one production joke, no catchphrase, written as the user | both points present, nothing added |

## Comparison with the baseline

Before `SKILL.md` existed, one fresh agent answered the same three `me` requests from the request text alone. Its Reddit reply already mirrored the user's phrasing. Its email opened with thanks, added "happy to chat", signed with a `[Your name]` placeholder, and appended a note after the draft. Its Deadpool tweet was written as the character hijacking the account. With the skill, every draft kept the output contract, the profile's sign-off, and the user's identity.

## Limits

One machine, one model family, one run per channel, synthetic inputs chosen by the author. The mechanical audit catches listed tells, not every tell. The profile is built from prompts to an AI assistant, a terser and less polite register than replies to people; the author's confirmed defaults compensate for the email channel, and tuning after real replies is the intended next step. Draft text, exemplars, n-grams, and project names are deliberately left out of this report.
