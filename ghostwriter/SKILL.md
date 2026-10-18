---
name: ghostwriter
description: >-
  Use when the user wants text written in their own voice or a named persona's
  voice: replies to emails, Reddit comments and threads, tweets, or posts
  ("reply in my voice", "write this as me", "ghostwrite", "draft a reply",
  "draft a tweet", "in my tone", "humanize this as me", "as Deadpool",
  "in the style of"), or wants to create, list, refresh, or tune a tone
  profile. Not for a plain "humanize this text" with no voice named. Drafts
  only; never posts or sends.
license: MIT
metadata:
  author: ayhammouda
  version: "1.0"
---

# Ghostwriter

Draft and rewrite messages in a stored voice: the person's own, built from their Claude Code prompts, or a researched persona. Every draft is audited for AI tells and for fidelity to the voice, then handed over as paste-ready text for the person to send.

## Profiles

- `$GHOSTWRITER_HOME/tones/`, default `~/.config/ghostwriter/tones/`: every profile made on this machine, including the person's own, `me`.
- `references/tones/` in this skill: the shipped examples `deadpool` and `morgan-freeman`, and `_template.md`.
- A user profile shadows a shipped profile with the same slug. `references/profile-schema.md` defines the format, polish levels, and intensity.

`<skill>` below is this skill's directory, the folder holding this file. Run scripts through the interpreter, such as `python3 -I <skill>/scripts/validate_profile.py --list`.

## Workflow

1. **Resolve the request.**
   - Tone: `me` unless the request names a voice; a named voice becomes a slug such as `morgan-freeman`.
   - Channel: `email`, `reddit`, `tweet`, or `other`, from the request or the text being answered.
   - Polish: the request's word (loose, standard, clean), else the profile's channel dial, else the channel default below.
   - Intensity, for personas: the request's number from 1 to 5, else the profile's `default_intensity`.

   Done when tone, channel, polish, and intensity are known.
2. **Load the profile.** Run `scripts/validate_profile.py --list` and read the matching file in full. When none exists, build it first, then return here with the original request:
   - `me`, or "from my history": `references/self-profile.md`, which runs `scripts/build_corpus.py` and `scripts/style_stats.py`.
   - A named persona: `references/research-playbook.md`.
   - Text the person supplies: the sample flow in `references/self-profile.md`.

   Building ends when the person has confirmed the new profile and it is saved. Done when the profile file has been read.
3. **Pin the content.** Read the thread, email, or post being answered. List what the reply must say: the person's position, facts, decisions, and dates, each taken from the person's request or the material they gave. When the position or a needed fact is missing, ask one question or offer two candidate stances, then wait for the answer.

   Done when every point the draft will make traces to the person or the material.
4. **Draft in the voice.** Follow the profile's channel dial for length and sign-off, its Rhythm and Syntax habits at the chosen polish, and its Lexicon, Devices, and Openers and closers. Reuse the person's own phrasing from the request where it fits: it is the freshest sample of their voice. Scale persona devices to the intensity.
5. **Audit for tells.** Check the draft against `references/ai-tells.md`, including the Reply tells, and against the profile's Anti-tells. Run the two-prompt audit at the end of that file, then revise.
6. **Audit for fidelity.** Check every Do / Don't line, the length target, and the mechanics at the chosen polish: a profile that records lowercase starts gets lowercase starts at loose polish. Check that every point from step 3 is present and that no new claim crept in. Revise.

   Done when no tell remains and every Do / Don't line holds.
7. **Deliver** by the output contract.

## Output contract

The reply is the final text in one fenced `text` block, ready to paste, written as the person and signed with their name where the channel dial says so. Nothing follows the block. A required note, such as the language note below, goes in one line before it. When the person asks to "show your work", add after the block the tells found and fixed and the result of each Do / Don't check.

## Channels

| Channel | Default polish | Length |
| --- | --- | --- |
| email | standard | profile dial |
| reddit | loose | profile dial |
| tweet | loose | under 280 characters |
| other | standard | profile dial |

## Managing profiles

| Request | Action |
| --- | --- |
| List tones | `python3 -I <skill>/scripts/validate_profile.py --list` |
| Show a tone | Read the file and summarize its traits; never quote corpus text. |
| Create from my history, from research, or from a sample | Step 2's playbooks. |
| Refresh `me` | Refresh in `references/self-profile.md`. |
| Tune ("I would never say that") | Tune in `references/self-profile.md`. |
| Delete a tone | Delete in `references/self-profile.md`; the file moves to `$GHOSTWRITER_HOME/trash/`. |
| Check every profile | `python3 -I <skill>/scripts/validate_profile.py --all` |

## Guardrails

- **Drafts only.** The person sends, posts, or publishes the text themselves. Asked to post, deliver the draft and say it is ready for them to post.
- **The person's content.** Opinions, facts, commitments, and decisions come from the person or the material they gave, as pinned in step 3.
- **Written as the person.** A persona shapes style; the message stays the user's own, in their first person and signed as them. A fictional character speaks in character only when the request asks for an in-character post. A real person never signs, endorses, or says anything in a draft; decline drafts presented as their words.
- **Private data stays home.** Profiles and the corpus stay under `$GHOSTWRITER_HOME`. Summaries show traits and numbers. New profiles pass through `drafts/` and the person's confirmation before they are saved.
- **Language.** Reply in the language of the exchange. Outside English, the one line before the block says the profile was built from English text.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| A thanks or praise opener, or a closing offer | Start with the answer; end on the content or the next step. |
| Notes or alternatives after the draft | Settle questions in step 3; the reply ends with the block. |
| A placeholder such as [Your name] | Use the profile's sign-off; ask once if it has none. |
| Catchphrase stuffing in a persona | One signature phrase per reply; devices scaled to intensity. |
| Over-polishing a loose channel | Follow the profile's measured habits at loose polish. |
| A date, opinion, or promise the person never gave | Ask one question or offer two candidate stances. |
