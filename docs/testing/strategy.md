# Testing strategy

Trust comes from specific, reproducible claims. A structural check, Git recipe regression, scripted workflow replay, and model evaluation answer different questions.

## Coverage and failure cases

| Area | Test surface | Required outcomes |
| --- | --- | --- |
| Package contract | `validate_collection`, also called by the maintainer entrypoint | Reject malformed/duplicate metadata, invalid names, missing licenses, absent catalog entries, broken resources, absolute/escaping paths, and package symlinks; accept valid multiline metadata and new packages without registry edits. |
| Git safety recipes | Existing documented-command tests | Preserve hidden edits, sparse state, nested repositories, locked/offline records, paused operations, indexes, upstream identity, and unrelated refs; verify targeted fetch has no automatic maintenance. |
| Cleanup workflow | Disposable real repositories and local bare remote | Audit without mutation; archive before deletion; preserve staged and unstaged user work, ignored data, active configuration, unique history, and useful notes; default branch retention; exact opt-in deletion; byte-identical recovery; repeat assessment; defer interrupted operations. |
| Failure detection | Corrupted or changed fixture state | Abort on changed candidates; retain a branch changed during fetch; do not treat remote failure as absence; detect lost user work, missing decision rationale, and corrupt backups. |
| Mentor package | Bundled validator in isolated copies | Accept the standalone package; reject broken schema references, malformed JSON, duplicate evaluation IDs, unknown modes, missing required sections, and malformed resource lines. |
| Distribution | Pinned Skills CLI and real packages | Discover every skill; install every file and license for the documented agent IDs in both modes; compare bytes; retain the global lock; remove disposable projects. |
| Evidence | Source and Git state before/after all checks | Reject source/index/configuration/ref mutations, empty or skipped suites, and failed checks; record commit plus dirty input hashes and actual stage results; stop timed-out descendants; never claim hosted or model execution from local structural checks. |

Use negative examples to prove rejection, not a percentage of lines executed. The positive cleanup scenario checks both behavior and preservation; its assertions are reused across phases and must not be added up as distinct test cases.

## Running and interpreting results

Follow [the contribution commands](../../CONTRIBUTING.md#validate-a-change). The default run is offline after development dependencies are installed. `--install` additionally requires the pinned CLI in cache or network access. Native commands remain available for focused debugging.

CI runs the same entrypoint on Ubuntu with Python 3.11 / Node 22 and macOS with Python 3.14 / Node 24. The workflow grants read-only repository permissions, pins actions to immutable commits, and publishes version-scoped result artifacts even when validation fails. A configured matrix is not evidence that a run has passed; inspect the actual run and report.

The scripted replay is derived from the earlier same-session [cleanup experiment](2026-10-11-clean-project-e2e.md). It replays a predetermined plan against new synthetic data and verifies the same preservation requirements. It does not invoke an agent or discover a safe plan for arbitrary user projects.

## Manual model-evaluation protocol

Use this protocol before claiming that a model reliably follows changed instructions:

1. Record the skill content hashes, harness/model/version, tool permissions, task prompt, expected outcomes, and source commit or dirty state.
2. Use a fresh disposable project. For Clean Project, adapt the published fixture to the exact scenario; never point an evaluation at real user data. For Mentor, use the bundled evaluation prompts and rubrics.
3. Include an audit-only task, an explicitly authorized cleanup with branches off, branch opt-in, useful notes awaiting a retention choice, changed or ambiguous evidence, and preservation of unfinished work. For Mentor, include unclear goals, unavailable/current sources, narrow and broad topics, and optional practice.
4. Let the model choose its actions without feeding it the scripted replay or expected answers. Record tool failures and interventions.
5. Assess final filesystem/refs/index and retained information with the independent outcome assertions. Assess Mentor's actual output and source quality, rather than merely validating the evaluation definitions.
6. Compare representative runs with and without the skill. Report failures, retries, model/harness dependence, and untested cases. Do not relabel an authored example as a fresh-model run.

Model evaluations are manual and separately authorized. No model evaluation framework or additional agent delegation is required for deterministic collection acceptance.

## Limits

The automated suite does not cover Codex-managed archival, a real offline volume, independent simultaneous writers, hosted remote authentication, every Git version, every harness's runtime behavior, or Windows cleanup execution. Remote failures and intervening ref changes are simulated. Installation proves file delivery; it does not prove skill invocation or judgment.

External example URLs are checked for syntax and structure, not ongoing availability or correctness. Mentor must verify current sources when it runs.
