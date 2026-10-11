# Updated clean-project end-to-end results

**PASS — 2026-10-11.** Tested skill commit [`22d6c1b`](https://github.com/ayhammouda/skills/commit/22d6c1b3821d01796a8c25c419fa78719e65e0e7) on macOS with Git 2.56.0 and Python 3.14.5. No skill changes were needed.

The primary session applied the updated skill to a new disposable project and local bare remote. The fixture/verifier created inputs and checked outcomes; cleanup decisions and exact-path mutations were performed separately. Git configuration was isolated. All project data was synthetic; no real project or external remote was cleaned.

## Full workflow

| Phase | Observed outcome |
| --- | --- |
| Baseline | Project tests, healthcheck, and documented greeting command passed. The cleanup outcome verifier failed on the still-present obsolete audit, demonstrating a non-vacuous check. |
| Audit | Exact state comparison passed: no project content, refs, index bytes/flags, config, or retained worktree administrative state changed. |
| Default cleanup | **66 outcome checks passed**, plus the review preservation comparison. Removed 3 obsolete tracked sources and 5 archived non-Git files. Retired one eligible checkout and one genuinely abandoned missing record by exact path. Kept every local branch. |
| Branch opt-in | **66 outcome checks passed again**, plus preservation comparison. Deleted only `finished-task`, after exact upstream absence, pinned target ancestry, configuration, OID, and worktree checks. All other local refs and all remote refs stayed unchanged. Only that branch's configuration section was removed. |
| Recovery | Restored **all 8 removed sources byte-identically**: five from a private archive outside the worktrees and three from the baseline Git commit. |
| Repeat | Reassessment identified no new eligible action. Exact final-state comparison passed. |
| Resumed work | Added real clean paused rebase and bisect sessions, plus an otherwise eligible branch. A subsequent authorized cleanup deferred branch deletion. Whole-state equality confirmed preservation of the notes, operation state, indexes, refs, and eligible branch. No operation was aborted or continued to enable cleanup. |
| Teardown | Removed the entire owned fixture only after verification. This was test teardown, separate from skill cleanup. Local evidence remains outside the deleted fixture. |

These phases reuse assertions, so the counts are not a total of distinct test cases.

## User work and knowledge preservation

- Preserved both the staged version and a different unstaged version of `user-staged.md`, along with unrelated modified notes, an untracked draft, ignored local data, and an out-of-scope symlink target.
- Preserved active agent instructions/configuration, ongoing planning, unresolved findings, and the referenced AI healthcheck used by Makefile/CI.
- Consolidated primary and retiring-worktree handoffs into `docs/architecture.md` and `docs/getting-started.md` before removing their sources. Retained verified entrypoints, tested commands, the runpy healthcheck relationship, the rationale for offline standard-library use, the rejected network-service alternative, and unresolved personalized greetings. Repaired inbound links and created no empty FAQ.
- Retained dirty, ignored-data, locked, and unique detached-history worktrees. Their contents and private administrative state stayed unchanged.
- Correctly reported the fixture's Git-ref handoff as **needs review**: cleanup/docs were uncommitted and unrelated user work remained unfinished. The test did not stage, reset, or commit that work merely to obtain clean status.

## Review fixes exercised in the workflow

| Case | Evidence |
| --- | --- |
| Hidden index edits | Skip-worktree and assume-unchanged checkouts had clean ordinary status. Both edits, index flags, and index bytes survived. |
| Nested repositories | An ignored nested repository and an ignored bare repository retained their notes, files, and exact refs. |
| Interrupted operations | Private rebase/bisect markers blocked retirement and later branch cleanup despite clean status. Whole administrative-directory snapshots matched. |
| Fetch maintenance | Trace2 recorded no maintenance or GC child for the targeted fetch. Offline records and retained history remained intact. |
| Missing records | Exact-path retirement removed only the abandoned record; both unlocked and locked offline records survived. No batch prune ran. |
| Ref identity/configuration | NUL-field/newline-record parsing and canonical common-directory checks were used. A branch with two configured merge refs was retained. |
| Inventory side effects | Status used the collapsed overview and disabled optional locks. Retained index bytes and flags remained unchanged. |

The public recipe regression suite also passed **13/13**, including repeat installation, output summarization, and repository identity. Skill validation passed. Run the command tests with `python3 -B tests/test_git_safety.py`; those tests do not replay this full conversational cleanup.

## Evidence boundaries

This is same-session skill application with independent outcome assertions, not a fresh-agent compliance evaluation. The larger fixture/verifier and detailed before/after snapshots remain in the local task workspace; this report publishes the sanitized results. A case-sensitive retention assertion was corrected in the harness after the first cleanup check; the expected information was already present. No skill change was made to obtain a pass.

Not exercised: Codex-managed archive APIs, simultaneous external writers, actual volume unmounting, hosted remote authentication, or a Git/OS version matrix. Offline volume conditions were simulated by moving owned fixture checkouts. The README intentionally continues to clone `develop` while `main` is empty.
