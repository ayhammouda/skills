# Building a profile from the person's own writing

Two kinds of profile come from real text: `self`, built from the person's Claude Code prompts on this machine, and `sample`, built from text the person supplies. Both follow the format in `references/profile-schema.md`.

Paths below use `<skill>` for this skill's directory and `<home>` for `$GHOSTWRITER_HOME`, default `~/.config/ghostwriter`.

## Self profile (`me`)

1. **Check for an existing profile.** If `<home>/tones/me.md` exists and the person did not ask for a refresh, use it. Done.
2. **Extract the corpus.** First tell the person, in one line, that this reads their Claude Code prompts under `~/.claude/`, processes them on this machine, and keeps the results in `<home>/corpus/`. Continue once they agree.

   ```bash
   python3 -I <skill>/scripts/build_corpus.py
   ```

   Add `--since YYYY-MM-DD` when the person wants only their recent voice. The script prints a JSON summary. Exit code 2 means no usable prompts: say so and offer the sample flow below.
3. **Measure it.**

   ```bash
   python3 -I <skill>/scripts/style_stats.py <home>/corpus/me.corpus.jsonl
   ```

4. **Read the evidence:** `<home>/corpus/me.stats.json` and `<home>/corpus/me.sample.md`, both in full. These two files are the whole evidence base; the full corpus stays unread.
5. **Draft `<home>/drafts/me.md`** from `references/tones/_template.md`, then make it private with `chmod 700 <home>/drafts && chmod 600 <home>/drafts/me.md`:
   - Front matter: `kind: self`, `slug: me`, `confidence: medium`, and the `corpus` block (`items`, `words`, and the first and last dates, `YYYY-MM-DD`) from the stats.
   - **Rhythm and shape:** median and 90th-percentile reply length and sentence length, turned into length targets.
   - **Syntax and mechanics:** the rates for lowercase starts, missing end punctuation, space before `?` and `:`, contractions, emoji, and em dashes, each stated as a habit with its number.
   - **Lexicon:** voice markers from the top words, n-grams, markers, openers, and closers. Keep function phrases (connectors, hedges, intensifiers, requests) and leave out topic words such as project or tool names.
   - **Exemplars:** three to six passages from the sample that show voice rather than task detail, each under 40 words, with names, projects, and placeholders removed.
   - **Channel dials:** email `standard`, reddit `loose`, tweet `loose`, other `standard`, with lengths scaled from the measured medians.
   - **Provenance:** the corpus span and size, and this known gap: prompts to an AI assistant are their own register, more imperative and less polite than replies to people. Tuning after the first real replies closes the gap.
6. **Validate the draft.**

   ```bash
   python3 -I <skill>/scripts/validate_profile.py <home>/drafts/me.md
   ```

   The result is `OK`; fix every `FAIL` line before moving on.
7. **Confirm with the person.** Show eight traits, one line each, and six numbers: items, date span, median reply length in words, lowercase-start rate, space-before-question-mark rate, and missing-end-punctuation rate. Show traits, never corpus text. Ask what is wrong or missing.
8. **Save.** Apply the corrections, mostly as Do / Don't lines. Move the file to `<home>/tones/me.md`, run `chmod 700 <home>/tones && chmod 600 <home>/tones/me.md`, and validate it again. Validation fails on a profile other users can read. The profile is saved once validation prints `OK` for the new path.

## Sample profile

The person supplies text they wrote, such as sent emails or old posts, as a file path or pasted text. Pasted text is saved to `<home>/corpus/<slug>.txt` first: create the file private before any content lands in it, with `mkdir -p <home>/corpus && chmod 700 <home> <home>/corpus && install -m 600 /dev/null <home>/corpus/<slug>.txt`, then write the text into that file.

```bash
python3 -I <skill>/scripts/build_corpus.py --from-file PATH --slug <slug>
python3 -I <skill>/scripts/style_stats.py <home>/corpus/<slug>.corpus.jsonl
```

Then follow steps 4 to 8 with `kind: sample` and no `corpus` block. Confidence follows the measured word count: `low` under 300 words, `medium` under 2,000, `high` above. A sample of the person's replies to people is the best evidence for their reply voice; a sample beside the `me` profile can become a channel-specific profile such as `me-email`.

## Refresh

Rerun steps 2 to 8 on an existing profile. Replace the measured sections (Rhythm and shape, Syntax and mechanics, Lexicon, Exemplars) and the `corpus` block. Keep the Do / Don't list and other hand edits. Increase `version` and set `updated`.

## Tune

Feedback such as "I would never say that" or "shorter, more direct" becomes one Do or Don't line per point. Increase `version`, set `updated`, and validate. A shipped profile is copied to `<home>/tones/` before its first tune, so the shipped file stays unchanged.

## Delete

After the person confirms, create the trash directory with `mkdir -p <home>/trash && chmod 700 <home>/trash`, move `<home>/tones/<slug>.md` to `<home>/trash/<slug>-<date>.md`, and offer the same for `<home>/corpus/<slug>.*`. The person empties `<home>/trash/` themselves.
