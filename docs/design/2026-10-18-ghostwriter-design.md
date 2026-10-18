# Ghostwriter skill: design

Date: 2026-10-18. Status: draft for approval. Author of the requirements: Aymen Hammouda. Design choices marked **(my call)** were made by the assistant and can be overridden.

## Intent

Aymen replies to emails, answers comments and threads on Reddit, and sometimes publishes tweets. He wants an agent to draft those replies for him without the result reading as AI-generated, and without losing the identity and voice people already know him by. The installed [humanizer skill](https://github.com/blader/humanizer) (v2.5.1, MIT) removes AI writing patterns and can calibrate to a pasted writing sample, but the sample has to be supplied every time and nothing is remembered.

Ghostwriter is a sibling skill: humanizer's AI-pattern removal plus **stored tone profiles**. A profile is a local file that describes how one voice writes. The default profile is Aymen's own voice, derived from his previous conversations with Claude. Other profiles describe public personas (the examples given were Morgan Freeman and Deadpool) and are built once through web research, then reused from disk.

## Goals

1. Rewrite or draft text in a named tone, with AI tells removed, ready to paste into an email, a Reddit reply, or a tweet.
2. Build Aymen's own profile from his Claude Code prompts already on this machine, not from a self-description.
3. Build a persona profile through research on first use, store it locally, and never research it again unless asked.
4. Keep profiles portable, human-editable, and improvable from feedback ("I would never say that").
5. Ship as one self-contained folder in this collection, installable with the Skills CLI in any supporting harness.

## Non-goals (v1)

- Posting, sending, or scheduling anything. Ghostwriter produces text; publishing stays a separate, manual action.
- Ingesting Reddit, GitHub, email, or tweet archives. Aymen chose Claude Code prompts as the only corpus for his profile. The corpus builder should make adding a source later easy, but ships with this one source.
- Scoring or classifying the tone of arbitrary third-party text. Profiles are built from a corpus, from research, or from a sample the user hands over; there is no standalone "tone analyzer" output.
- Profiles in languages other than English. The corpus is 99% English; the profile may note French-influenced habits. Replies follow the language of the exchange, and the skill says once that fidelity is lower outside English **(my call)**.
- Any model training, embeddings, or external service.

## Anti-goals

The skill has failed, even if every step runs, when:

- the output reads as AI-generated (the humanizer pattern list is the test);
- the output puts an opinion, fact, promise, or decision in Aymen's mouth that he did not express;
- his personal profile or corpus ends up in this public repository or in any skill folder that gets reinstalled;
- a persona has to be researched again on each use;
- the skill fakes authenticity by inserting misspellings;
- a persona profile reproduces long passages of copyrighted script or presents output as a real person's actual words.

## Constraints

- **Cross-harness.** The repository targets Codex, Claude Code, Gemini CLI, Cursor, and others. `SKILL.md` must describe tools generically ("web search", "read the file", "run the script") and must not depend on Claude-only features. Scripts are Python 3.10+ standard library only, run as `python3 -I`, no third-party packages, no Node.
- **Agent Skills spec.** `name` equals the folder name, lowercase with hyphens; `description` under 1024 characters and written to trigger on the use cases below; supporting material in `references/` and `scripts/`. The description must not claim a bare "humanize this text" with no voice named; the humanizer skill keeps that trigger **(my call)**.
- **Repository conventions.** Design notes live under `docs/design/` **(my call)**. A `LICENSE` copy inside the skill folder, an `agents/openai.yaml` with display metadata, an `evals/evals.json` in the Mentor format, tests under `tests/` runnable with `python3 -B tests/<file>.py`, a README row plus a "What Ghostwriter does" section, and later a dated end-to-end report under `docs/testing/`.
- **Licensing and attribution.** MIT. The vendored AI-pattern list credits blader/humanizer and Wikipedia's "Signs of AI writing" page.
- **Privacy.** Corpus and personal profile live outside the repository and outside the installed skill folder. The corpus is scrubbed of secrets and contact details before it is written. Profile exemplars contain no names, emails, URLs, keys, or project names.
- **Copyright.** Persona profiles describe style. Quoted catchphrases stay under 15 words, a handful at most; exemplars are synthesized in the style, not copied.

## What has been decided

### Name and placement (my call)

The skill is `ghostwriter`, folder `ghostwriter/` at the repository root, next to `clean-project/` and `mentor/`. The name is free in the local harness skill directories.

### Where profiles live (my call)

Two locations, searched in this order:

1. **User directory**, `~/.config/ghostwriter/` (override with the `GHOSTWRITER_HOME` environment variable). Contains `tones/<slug>.md` for every profile created on this machine, including Aymen's own, and `corpus/` for the extracted text, stats, and samples. Survives reinstalling the skill. Never committed.
2. **Shipped directory**, `ghostwriter/references/tones/`. Read-only at runtime. Contains `_template.md` and the worked examples `deadpool.md` and `morgan-freeman.md`.

A user-directory profile shadows a shipped one with the same slug. Slugs are lowercase with hyphens; Aymen's profile is `me`.

### Profile kinds (my call)

- `self`: built from the local Claude Code corpus by the scripts below.
- `persona`: built by the research playbook (web search when the harness has it; otherwise from model knowledge, flagged as low confidence).
- `sample`: built from writing the user pastes or points to. This covers humanizer's one-off calibration and lets Aymen profile any voice he has text for.

### Profile format (my call)

Markdown with YAML front matter and fixed section headings, so people can edit it and a script can validate it.

Front matter: `name`, `slug`, `kind`, `version`, `created`, `updated`, `language`, `sources` (list), `confidence` (low, medium, high), `default_intensity` (1 to 5, personas only), `channels` (list), and for `self` profiles a `corpus` block with item count, word count, and date span.

Sections, in order:

1. **Identity and stance**: who is speaking, attitude toward the reader, what they tend to care about.
2. **Register**: formality, warmth, directness, humor type, confidence, hedging habits.
3. **Rhythm and shape**: sentence length (with the measured numbers for `self`), paragraphing, fragments, lists versus prose, typical reply length.
4. **Lexicon**: signature words and phrases, verbal tics, connectors, intensifiers, swearing level, words this voice never uses.
5. **Syntax and mechanics**: contractions, capitalization, punctuation habits (for Aymen this includes the space before `?` and `:`), emoji, how slips show up naturally.
6. **Devices**: how the voice explains, argues, jokes, references things.
7. **Openers and closers**, per channel.
8. **Channel dials**: one block each for `email`, `reddit`, `tweet`, and `other`, with target length, formality, polish level, and sign-off.
9. **Do / Don't**: short, testable statements. Feedback from use lands here.
10. **Exemplars**: three to six passages under 40 words each. For `self`, sanitized real passages or close paraphrases; for `persona`, synthesized passages in the style.
11. **Anti-tells**: what would expose the text as AI or as not this voice, on top of the shared AI-pattern list.
12. **Provenance**: how the profile was built, when to refresh, known gaps.

### Polish levels (my call)

`loose` allows lowercase openers, casual punctuation, and unfinished-thought endings where the corpus shows them. `standard` uses sentence case and normal punctuation while keeping the voice's words and rhythm. `clean` is proofread, for email to people who expect it. Defaults: reddit and tweet `loose`, email `standard`. No level inserts misspellings. The user can override per request ("clean reddit reply").

### The workflow in `SKILL.md`

1. **Resolve the tone.** Default `me`. A named tone maps to a slug. Intensity for personas defaults to 3 of 5.
2. **Load or create the profile.** Look in the user directory, then the shipped directory. If missing: `self` runs the corpus scripts and drafts the profile from the stats and the sample; `persona` follows the research playbook; `sample` reads the provided text. Show the user a short summary of the drafted profile (traits, not corpus text) and ask them to confirm or correct before saving. Saved profiles are reused silently afterwards.
3. **Understand the exchange.** Read the thread, email, or prompt being answered. Identify what the reply must do. If Aymen's position, decision, or facts are missing, ask one question or offer two candidate stances; never invent them.
4. **Draft in the voice** at the requested channel and polish level, following the profile's lexicon, rhythm, openers, and closers.
5. **Audit for AI tells** against `references/ai-tells.md` and the profile's anti-tells; revise.
6. **Audit for fidelity** against the profile's Do / Don't, lexicon, and length targets; revise.
7. **Deliver** the final text alone, paste-ready. On request ("show your work"), add the tells found and the profile checks. Never post or send.

Profile management phrases the skill must recognize: list tones, show a tone, create a tone (from history, from research, from a sample), refresh `me`, tune a tone from feedback, delete a tone. Tuning appends to Do / Don't and bumps `version` and `updated`; tuning a shipped profile first copies it into the user directory, so the shipped file stays untouched. Refreshing `me` rebuilds the measured sections, keeps the Do / Don't list, and bumps `version` **(my call)**.

### Guardrails in `SKILL.md`

- Drafts only; the skill never publishes.
- No invented facts, opinions, commitments, or quotes in the user's name.
- Personas of real people are style references. Output is never presented as that person's words, and requests to fabricate statements, endorsements, or messages purporting to come from the real person are declined.
- Profiles and corpus never leave the user directory; exemplars follow the sanitization rule above.

### Corpus extraction (decided filters)

Sources, Claude Code only:

- `~/.claude/history.jsonl`: one JSON object per line with `display`, `pastedContents`, `timestamp`, `project`, `sessionId`. Use `display`. Skip entries whose `display` starts with `/` (slash commands). Remove `[Pasted text #N +M lines]` markers. Never read `pastedContents`.
- `~/.claude/projects/*/*.jsonl`: session transcripts. Keep records with `type` equal to `user`. Skip records where `isSidechain`, `isMeta`, or `isCompactSummary` is true (sidechain "user" turns are written by the agent to its subagents). Skip records whose `message.content` array contains a `tool_result` block. Text is `message.content` when it is a string, otherwise the joined `text` blocks.

Cleaning, in order: remove harness blocks (`<system-reminder>`, `<task-notification>`, `<pasted_content>`, `<command-name>`, `<command-message>`, `<command-args>`, `<local-command-stdout>`, `<local-command-stderr>`, `<local-command-caveat>`, `<side-sessions-event>`, `<ci-monitor-event>`); remove fenced code blocks and `[Pasted text …]` / `[Image …]` markers; drop quoted lines (`>`), lines starting with `[Request interrupted`, log-like lines, and code-like lines; collapse whitespace. Drop items that still contain HTML-like tags (pasted markup), items with fewer than 3 words, and items with more than 400 words (default, adjustable; the transcript median is 19 words and the long tail is pasted material). Deduplicate on lowercased, whitespace-collapsed text, since prompts appear in both sources. Subagent transcripts under `<session>/subagents/` are never read: their "user" turns are written by the agent.

Scrubbing before anything is written: replace emails, phone numbers, IP addresses, URLs, and token-like strings (common key prefixes, Bearer tokens, 32+ character hex or base64 runs) with placeholders such as `<EMAIL>` and `<URL>`.

Outputs, in `~/.config/ghostwriter/corpus/`, created with owner-only permissions: `me.corpus.jsonl` (text, source, timestamp, project basename), `me.stats.json`, and `me.sample.md`, a fixed-seed sample of about 80 items stratified by length and date for the agent to read. The agent reads the stats and the sample, never the full corpus.

Measured on this machine today: 1,851 history rows, 445 unique prompts of 40+ characters, spanning 2026-01-30 to 2026-08-15; 197 session transcripts (plus 594 subagent transcripts, excluded) holding about 1,240 usable user turns, of which only 34 also appear in the history file, so the transcripts are the main source. Observed traits to expect in the profile: lowercase openers, typos left in, "let's" and "please", a space before `?` and `:`, "can we do that ?", "I would go as far as saying", dictated run-on sentences with "like" and "basically".

### Stylometrics (minimum set)

Item and word counts; sentence length mean, median, and 90th percentile; item length distribution; lowercase-start rate; rate of items without terminal punctuation; question rate; space-before-punctuation rate for `?`, `:`, `!`; exclamation, ellipsis, em dash, and emoji rates; contraction rate; top 50 words with stopwords removed; top bigrams and trigrams; top openers (first two words) and closers (last three words); politeness, hedge, and filler markers (please, thanks, like, basically, actually, just, I think, maybe, kind of); share of items starting with an imperative verb; language mix; date span.

### Research playbook for personas

Stored at `references/research-playbook.md`. Sources in priority order: interviews and transcripts, published linguistic or critical analyses of the voice, the character's writers and official material, fan wikis for catchphrases and recurring devices. Extract into the profile sections above; mark `confidence`; keep quotes under 15 words and few; synthesize exemplars; record the sources in front matter. Without web access, build from model knowledge and set `confidence: low`.

### Vendored AI-pattern list

`references/ai-tells.md` condenses humanizer's 29 patterns to one line each: name, words to watch, the fix. Credits blader/humanizer (MIT) and Wikipedia. The installed humanizer skill is not a dependency; if present, the agent may run it as an extra pass.

### Scripts, tests, and evals

- `scripts/build_corpus.py`: extraction, cleaning, scrubbing, deduplication, outputs. Flags for output directory, since-date, sample size, seed.
- `scripts/style_stats.py`: the stylometrics report from a corpus file (may be folded into the first script; builder's choice).
- `scripts/validate_profile.py`: checks front matter keys, required headings in order, exemplar length, quote length for personas, and absence of emails, URLs, or key-like strings in the body (front-matter `sources` may hold URLs). Also lists profiles found in both directories, skipping `_template.md`.
- Each script is self-contained with no imports between them: `python3 -I` implies `-P` on Python 3.11+, so sibling imports would fail **(my call)**.
- `tests/test_ghostwriter.py`: fixture JSONL exercising every filter above (sidechain and meta skipped, tool results skipped, pasted and reminder blocks removed, dedup across sources, scrubbing), stats sanity on a known fixture, validator passing on every shipped profile and failing on a deliberately broken one.
- `ghostwriter/evals/evals.json`: scenarios covering a Reddit reply as `me`, an email reply as `me`, a tweet as `me`, Deadpool at two intensities, Morgan Freeman, a missing profile triggering creation, a missing stance triggering a question, and a request to post being declined.

### Shipped examples

`deadpool.md` and `morgan-freeman.md` are built during implementation with the research playbook, so the playbook is exercised before release. Both carry `confidence` and sources. Variants **(my call)**: the film Deadpool (fourth-wall breaks, pop-culture asides, profanity scaled by intensity, none at 1 or 2) and Morgan Freeman as documentary narrator (measured cadence, warmth, plain aphorisms), each recorded in Provenance. `_template.md` holds the empty structure with one-line guidance per section.

### Documentation

README: a table row, a "What Ghostwriter does" section mirroring the existing ones, requirements (Python 3 for the scripts, web search for persona research, access to `~/.claude` for the `me` profile), install commands, usage examples for the three channels, and the verification command. A dated end-to-end report under `docs/testing/` after the first real run on this machine, carrying counts, rates, and pass/fail only: no n-grams, exemplars, or project names **(my call)**.

### Build order and branching (my call)

Everything except the `me` profile ships without Aymen: skill files, scripts, tests, example personas, README. Creating the `me` profile and the end-to-end run need his confirmation step, so they form the last, interactive phase. Work happens on the `develop` branch tracking `origin/develop`, matching the two earlier pull requests; Aymen opens the pull request to `main` as before.

## Left to the builder

- Exact `SKILL.md` wording, length, and the split between `SKILL.md` and `references/` (keep `SKILL.md` focused on the workflow and guardrails; details go to references).
- Whether stats are one script or two; CLI flag names; the sampling algorithm.
- The validator's exact rules and messages.
- The template's per-section guidance text.
- How the agent detects available web tools in each harness.
- Eval prompt wording and assertion lists.
- Research sources actually used for the two example personas.

## Builder check

A fresh reviewer read this document on 2026-10-18 as the builder and reported "nothing important left". The defaults it would have taken are adopted above and marked **(my call)**.
