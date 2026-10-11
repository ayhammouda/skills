# Contributing

Start with a failure observed in a real task or a concrete new use case. Keep a skill focused and retain its complete supporting files. The [architecture](docs/architecture.md) and [testing strategy](docs/testing/strategy.md) explain the collection's checks.

## Package contract

- Keep each skill in a top-level directory named with lowercase ASCII letters, numbers, and single hyphens. Match its frontmatter name; do not add a root-level `SKILL.md`.
- Use the [Agent Skills format](https://agentskills.io/specification): a `SKILL.md` with YAML frontmatter, a useful name/description, and actionable instructions. Duplicate YAML keys and unknown frontmatter fields fail validation.
- This repository additionally requires `license: MIT`, a bundled complete MIT license preserving attribution, and no more than 500 lines in the entrypoint. The latter is an authoring recommendation promoted to collection policy.
- Keep references inside the package. Use Markdown links for required resources, including schemas; the validator checks link targets in instructions and supporting Markdown. It checks file existence, not heading fragments or external URL freshness.
- Supporting folders are optional. Add scripts, examples, evaluations, or assets only when the task needs them. Do not ship symlinks, repository metadata, dependencies, bytecode, or local temporary files.
- Add the skill to the README catalog. Discovery comes from the actual entrypoints; there is no second registry to maintain.
- Put harness-specific presentation metadata in its supported location. Any new frontmatter extension needs a documented compatibility decision and a validation test.

## Validate a change

The maintained validation environments are macOS and Linux, with Python 3.11+, Git 2.36+, and Node.js 18+ for offline checks. The pinned installer also requires Node.js 22.20+ and `npx`.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -B scripts/validate.py
```

Before a PR or release, also exercise real package installation:

```sh
.venv/bin/python -B scripts/validate.py --install --report /tmp/skills-validation.json
```

The report must be outside the checkout. It records source hashes as well as the base commit and dirty state, so results from an uncommitted change cannot be mistaken for proof of that commit alone. The installer is pinned in `scripts/validate.py`; changing it requires rerunning the package tests. Telemetry is disabled and installs use disposable project directories, not user installations.

For a behavior change, add a regression that fails before the fix. Run the relevant native checks as well as collection acceptance. A new skill with executable behavior needs its own applicable checks discovered under `tests/test_*.py`; a green metadata check is not behavioral proof.

## Review and release

1. Check the intended diff, attribution, catalog, and complete package contents.
2. Require the full acceptance run on the source being reviewed. Inspect failed or skipped stages and the evidence limitations.
3. For instruction changes, use the manual model-evaluation protocol in the testing strategy when claiming model behavior. Keep deterministic and model evidence distinct.
4. Release only the reviewed commit, and link or retain its validation evidence. Fixed tags describe their own snapshot; later additions on `main` do not change old releases.
5. Preserve historical reports. Add a dated applicability note when surrounding checkout or release context changes.

Validation does not publish, merge, tag, or clean any real project.
