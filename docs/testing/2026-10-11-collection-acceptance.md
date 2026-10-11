# Collection acceptance — 2026-10-11

Both architecture-review recommendations are implemented: one collection acceptance command and a published, reproducible cleanup scenario with independent preservation assertions.

## Changes and observed defects

- Added package discovery, safe YAML/Markdown parsing, format and collection-policy checks, bundled-license checks, resource validation, catalog validation, and complete package installation checks. The two existing native validators remain in use.
- Published the sanitized cleanup fixture, its fixed replay, and independent assertions. Negative scenarios demonstrate that lost user work, missing decision rationale, corrupt archives, changed candidates, remote errors, and intervening branch changes are detected.
- Added a contribution contract, architecture explanation, glossary, test strategy, and CI on Linux/macOS. Historical evidence now states its original applicability.
- Fixed Mentor's validator silently ignoring malformed resource lines. Both malformed-link regressions failed before the fix and pass afterward.
- Hardened acceptance against empty/skipped suites, failing checks, changed source/Git state, and descendants left running after a timeout. Git-only mutation tests first demonstrated false success for staging, configuration, branch, and ref changes. A linked-worktree regression also exposed an invalid configuration-read assumption; the final implementation works in both normal checkouts and linked worktrees.

Clean Project's cleanup instructions are unchanged apart from MIT metadata. Mentor's instructions gained MIT metadata and a portable schema link; its validator contains the resource-line fix.

## Completed local runs

Each run executed the complete acceptance command with `--install`, passed all six stages, and ran **55 tests with zero skips**:

| Environment | Python | Node.js | Git | Tests | Installer modes |
| --- | --- | --- | --- | --- | --- |
| macOS 26.6.2 / ARM64 | 3.14.8 | 26.11.1 | 2.56.0 | 55 passed | Symlink and copy passed |
| macOS 26.6.2 / ARM64 | 3.12.14 | 24.19.0 | 2.56.0 | 55 passed | Symlink and copy passed |
| Debian Bookworm / ARM64 container | 3.11.2 | 22.22.2 | 2.53.0 | 55 passed | Symlink and copy passed |

The suite contains 17 package-contract tests, 13 existing Git recipe tests, 8 cleanup workflow tests, 8 Mentor tests, and 9 runner/evidence tests. Subcases and repeated phase assertions are not counted as additional independent tests.

Skills CLI 1.7.2 installed both complete packages for all 12 documented agent IDs in each mode. Those IDs share four distinct destination roots in this CLI version, so eight package directories were verified per mode. Every delivered file matched its source bytes, every package included its license, and the global installer lock was unchanged. Disposable installation directories were removed.

The cleanup replay verified audit-only preservation, archive-before-delete, useful notes retained in `docs/`, user edits and unique history retained, branches off by default, exact opt-in deletion, repeat assessment, paused-operation deferral, and byte-identical recovery of all eight removed files. It also checked that targeted fetch did not start automatic maintenance.

`actionlint` 1.7.12 accepted the workflow; shellcheck was unavailable and was disabled for that invocation. Git whitespace checks passed. The original `main` checkout, its 17 tracked files, and the user's untracked review file retained their original bytes and commit.

## Evidence and applicability

The [machine-readable summary](evidence/2026-10-11-collection-acceptance.json) records all 33 tested input-file hashes, each runtime, stage outcomes, installer scope, timestamps, and hashes of the full local JSON reports. All three runs tested identical file bytes based on `0323703d98e2408ed36dbb1d9c984ef7ceca94a4` with uncommitted implementation changes. The base commit alone does not identify the tested code.

This results note, the condensed evidence, and their README link were added after those runs. Their structure and links were checked afterward; executable inputs remained identical. The full reports stay outside the checkout, as required by the acceptance command. Future CI runs retain their own full reports as artifacts.

The Linux run used an isolated copy in a cached official Microsoft Node development container after a Docker Hub image download stalled. The owned containers were removed after completion. This is completed local Linux evidence, not a hosted GitHub Actions run.

## Limits

These results cover deterministic checks, a fixed cleanup replay, and installer file delivery. They do not establish model judgment, reliable skill invocation in each harness, or live external-resource quality. No fresh-model evaluation, hosted CI, real managed-worktree archival, Windows cleanup, independent simultaneous writers, real volume unmount, or hosted remote authentication was exercised. See the [testing strategy](strategy.md) for the separate model-evaluation protocol and remaining boundaries.
