# Collection architecture

The deliverable is a set of independent instruction packages. Each top-level skill directory contains everything needed after installation. Repository maintenance tools, research, and test fixtures remain outside those directories.

The collection has two skills, so a category hierarchy would add path and local-link migrations without solving an observed navigation problem. Native plugin manifests and release frameworks can be introduced when an actual distribution channel needs them. The [research](research/2026-10-11-skills-directory-practices.md) records the comparison with Matt Pocock's repository.

## Acceptance and evidence

`scripts/validate.py` is the maintainer entrypoint. It discovers packages, checks the documented format and collection policy, runs Mentor's packaged validator and the repository regressions, optionally exercises the real Skills CLI, and emits source-scoped evidence. It does not contain skill-specific cleanup decisions.

The two native validation implementations remain independent: Python/Git tests exercise cleanup recipes and Node validates Mentor's packaged content. YAML and Markdown parsing use maintained libraries confined to development requirements. Skill consumers do not install them.

The cleanup scenario separates construction and outcome assertions (`tests/cleanup_fixture.py`) from the fixed action plan (`tests/cleanup_replay.py`). Tests deliberately corrupt preserved work, decisions, and recovery archives to prove the assertions detect loss. This separation improves failure diagnosis; scripted actions still do not prove a model follows the instructions.

Installation acceptance compares every delivered file with the actual source package for both copy and symlink modes. Temporary projects and local Git remotes contain synthetic data. Tests preserve source files and avoid user installations.

The JSON evidence records the base commit, branch, dirty state, file hashes, Git state fingerprints, runtime, stage outcomes, and installation scope. Validation checks source bytes, index entries/flags, status, refs, and local/worktree configuration before and after running. Configuration values are hashed rather than copied into reports. CI retains evidence for the exact run. Historical narrative reports remain dated; neither a base SHA with dirty files nor an old report is evidence for a later release.

See the [glossary](../GLOSSARY.md), [contribution contract](../CONTRIBUTING.md), and [testing strategy](testing/strategy.md).
