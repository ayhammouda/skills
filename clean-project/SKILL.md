---
name: clean-project
description: "Use when recovering an old dirty project, finishing a major milestone or release, or preparing a project for handoff, and obsolete files, temporary AI artifacts, outdated documentation, or stale Git worktrees need cleanup. Also applies to requested local branch cleanup after upstream deletion. Not for general code refactoring or dependency upgrades."
---

# Clean Project

Prepare a project for another person to use after recovery, a major milestone, or a release. Remove obsolete project and AI artifacts while preserving important decisions, useful knowledge, and unfinished work. AI authorship, filenames, age, and ignore rules identify candidates; they do not establish obsolescence.

## Establish scope

Resolve the requested project, current branch/release baseline, instructions, docs conventions, Git status, and worktree ownership. Establish the handoff target: Git refs or a filesystem package; default to a repository handoff when unspecified. A bare invocation or audit produces a proposal. Explicit cleanup authorizes confirmed obsolete files and eligible worktrees within scope; local branch deletion is opt-in. Reuse existing authorization and ask only for unresolved choices after preparing a concrete plan.

Stay within the project and its verified linked worktrees. Global AI histories, skills, caches, other repositories, remote branches, and tags require separate scope. Read [Git safety](references/git-safety.md) before assessing worktrees or branches. Without Git, perform file assessment only.

## Classify before deleting

Inspect candidate content, provenance, status/history, and references from callers, tests, fixtures, config, exports, CI, and docs. Include ordinary obsolete reports, scripts, exports, and release/milestone handoffs, even without AI-related names. Include hidden/ignored candidates deliberately; avoid dependency/build-tree scans and secret contents. Enumerate exact paths, not deletion patterns; do not follow symlinks outside scope.

| Decision | Evidence |
| --- | --- |
| Remove | Completed one-off artifact, no live references or unique knowledge, recovery established |
| Consolidate | Useful verified information missing from maintained docs |
| Keep | Active instructions/tooling/planning, referenced script, product asset, or unrelated changes |
| Review | Unknown ownership, unresolved findings, unique commits, or ambiguous usefulness |

Preserve active `AGENTS.md`, `CLAUDE.md`, skills, agent settings, and ongoing planning state. Retire specifically obsolete components only after checking consumers. Never run repository-wide `git clean`, hard reset, force removal, or broad recursive deletion as a cleanup shortcut.

## Offer knowledge retention

For relevant information, draft a concise proposed excerpt and destination before asking once: consolidate into docs, keep the source, or discard it. Follow any retention preference already given. While unanswered, keep the source and continue independent authorized cleanup.

Reuse existing documentation; otherwise choose:

- `docs/architecture.md`: verified components, boundaries, and accepted design decisions.
- `docs/getting-started.md`: tested setup, configuration names, and run/test commands.
- `docs/faq.md`: concrete recurring questions and validated answers.

Create only files with useful content. Deduplicate, verify against current code/config, retain dates on historical evidence, and keep unresolved claims distinct. Exclude secrets and raw session transcripts. Apply approved consolidation and repair inbound links before removing sources, including sources inside retiring worktrees.

Preserve decision rationale, constraints, rejected alternatives when informative, and unresolved questions. Reuse existing decision records; otherwise consolidate into architecture docs. A superseded decision or dated release record can remain valuable history: label its applicability instead of treating age as obsolescence.

## Prepare the handoff

Reconcile maintained README/setup/architecture guidance with the chosen baseline: paths, commands, configuration examples, and release/milestone references. Keep historical documentation clearly dated rather than rewriting it as current. Verify documented commands with focused checks; report anything unverified.

Inspect the actual sharing file list for stale artifacts, machine-specific paths, and local credentials/private data without exposing values. Preserve local-only data outside the shared set. Git ignore rules do not exclude already tracked files; flag tracked sensitive content and any required remediation. A folder/package may include ignored files unless explicitly excluded.

Preserve unfinished user work. If it prevents handoff, report the exact unresolved paths and decision needed; do not reset, discard, or stage it merely to obtain a clean status. Cleanup preparation alone does not authorize publishing or remote changes.

## Execute and verify

Present exact actions, evidence, keep/review items, documentation changes, and recovery locations. Recheck candidate contents, refs, ownership, and status immediately before mutation; changed evidence requires reassessment. Preserve pre-existing modifications. Use recoverable trash or a verified private archive outside the retiring trees for untracked/ignored data before deleting it; a remembered path or commit hash is not a backup.

Use the Git reference for managed archival and ordinary removals. Check the final diff/status, references, docs links, and affected checks; confirm requested paths/refs disappeared and retained work remains. Report removed, consolidated, retained, and blocked items, recovery instructions, and validation limits. State whether the chosen handoff target is ready or needs review, with exact blockers. Distinguish prepared local files from committed/published refs; uncommitted cleanup is not yet in a Git-ref handoff. Do not create another cleanup report inside the project unless requested.

Example: “Recover this old project into a shareable state, include eligible branches deleted upstream, and ask before consolidating useful decisions into docs.”
