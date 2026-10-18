# Researching a persona profile

A persona profile describes the voice of a public figure or character, built once from research and reused from disk. It follows the format in `references/profile-schema.md`. Paths use `<skill>` for this skill's directory and `<home>` for `$GHOSTWRITER_HOME`, default `~/.config/ghostwriter`.

1. **Check what exists.** Run `python3 -I <skill>/scripts/validate_profile.py --list`. A matching slug in either location means the profile is ready: use it and skip the research.
2. **Pick the variant.** Many voices have several incarnations: a character in film and in comics, an actor as narrator and in interviews. Choose the best-known variant for the request and record it in Provenance. Ask the person only when two variants would produce very different drafts.
3. **Research with web search** from four angles, aiming for three or more independent sources:
   - interviews, transcripts, or scripts where the voice speaks at length;
   - critical or linguistic analyses of how the voice sounds;
   - official material from the writers, the studio, or the person;
   - fan wikis for catchphrases, running jokes, and recurring devices.

   Without web access, build from model knowledge, set `confidence: low`, and tell the person.
4. **Extract into the twelve sections.**

   | Look for | Section |
   | --- | --- |
   | Worldview, attitude toward the listener, recurring concerns | Identity and stance |
   | Formality, warmth, humor type, swagger or humility | Register |
   | Sentence length, pauses, pacing, monologue versus quips | Rhythm and shape |
   | Catchphrases, pet words, nicknames, swearing level | Lexicon |
   | Contractions, address forms, punctuation the voice implies | Syntax and mechanics |
   | Fourth-wall breaks, metaphors, asides, callbacks | Devices |
   | Signature openings and sign-offs | Openers and closers |
   | How the voice compresses to a tweet or stretches in a thread | Channel dials |

5. **Write `<home>/drafts/<slug>.md`** from `references/tones/_template.md`:
   - `kind: persona`, `default_intensity: 3`, the source URLs in `sources`, and `confidence`: `high` with three or more independent sources covering lexicon and rhythm, `medium` with fewer, `low` without web access.
   - At most five quotes from the sources, each under 15 words.
   - Four to six exemplars synthesized in the style, each under 40 words, written without quotation marks.
   - Anti-tells that name what breaks the voice: wrong era, wrong register, overused catchphrases.
   - For a real person, the real-person rule below in Anti-tells.
6. **Validate** with `python3 -I <skill>/scripts/validate_profile.py <home>/drafts/<slug>.md` until it prints `OK`.
7. **Confirm and save.** Show the person the variant, five traits, and the confidence, then move the file to `<home>/tones/<slug>.md` and validate it there.

## Real-person rule

A persona of a real person is a style reference. Every draft in that style is the user's own message, signed as the user. Decline drafts that put words in the real person's mouth: invented statements, endorsements, or messages presented as coming from them.

## Intensity

Intensity semantics live in `references/profile-schema.md`. At draft time, scale catchphrase density, devices, and profanity to the requested level, and keep the user's message intact at every level.
