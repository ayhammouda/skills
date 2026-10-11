# Practices for a portable skills collection

Researched **2026-10-11** against `ayhammouda/skills` at [`0323703`](https://github.com/ayhammouda/skills/tree/0323703d98e2408ed36dbb1d9c984ef7ceca94a4). Matt Pocock's comparison snapshot is [`49dd158`](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336), version 1.3.1. External documentation was checked on the research date; the local installer experiment used Skills CLI 1.7.2.

**Recommendation:** retain the two existing skill folders. First make collection validation repeatable, then make behavioral test evidence reproducible. Categorization and native plugin distribution can follow demonstrated demand. These are recommendations for this repository, not requirements of the Agent Skills format.

## Format requirements and authoring guidance

A portable skill is a directory with `SKILL.md`, containing YAML frontmatter and Markdown instructions. Require `name` and `description`; the name must match the containing directory, use lowercase letters/numbers/hyphens, and satisfy the specification's length and hyphen rules. Describe the task and when the skill applies. `scripts/`, `references/`, and `assets/` are optional conventions; other supporting directories are permitted. The specification defines the individual skill, without prescribing a collection-wide category tree. [Agent Skills specification](https://agentskills.io/specification)

Use progressive disclosure: short discovery metadata, focused instructions, and supporting resources read when needed. The specification recommends fewer than 500 lines in `SKILL.md`, with relative resource paths and shallow reference chains. These are authoring recommendations, not evidence that a skill behaves correctly. [Agent Skills specification](https://agentskills.io/specification)

Anthropic recommends starting from observed failures, creating representative evaluations before expanding instructions, comparing performance with and without the skill, and iterating against real tasks. Give fragile operations precise steps; leave contextual judgment flexible. [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

Harness extensions need separate treatment. Claude Code provides invocation controls such as `disable-model-invocation`; its frontmatter acceptance is more permissive than the portable specification. Do not assume another harness implements those controls. For this collection, retain the cleanup workflow's explicit authorization and preservation rules in its instructions regardless of installation target. [Claude Code skills](https://code.claude.com/docs/en/skills), [current cleanup instructions](../../clean-project/SKILL.md)

## What Matt Pocock's repository demonstrates

| Observed practice | Application here |
| --- | --- |
| Skills are small, adaptable, and composable; the catalog distinguishes user-invoked orchestration from reusable model-invoked discipline. | Keep each skill focused; make invocation expectations explicit without assuming universal harness support. |
| Skill directories are grouped under `skills/engineering/` and `skills/productivity/`. | A useful navigation convention for a larger collection, not a migration requirement for two skills. |
| Plugin installation and editable Skills CLI installation are presented as different choices, with a warning about duplicate installation. | Document the actual update behavior of each supported channel. |

These observations come from Matt's [README at the inspected commit](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/README.md). His scope document prioritizes failures observed in actual sessions over hypothetical configuration and harness-specific expansion. That is useful curation guidance; its closed-contribution policy is specific to his project. [Scope](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/SCOPE.md)

The categorized paths are explicitly enumerated in a native plugin manifest, with separate marketplace metadata. Those files support that distribution channel; they are not part of the minimum individual-skill format. [Plugin manifest](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/.claude-plugin/plugin.json), [marketplace metadata](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/.claude-plugin/marketplace.json)

The repository's private npm package supports Changesets and plugin-version synchronization. Its release workflow creates version PRs and tags; it does not publish an npm skill package. This solves coordination across several version-bearing files. This collection has no corresponding version-synchronization problem yet. [Package metadata](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/package.json), [release workflow](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/.github/workflows/release.yml), [version synchronization](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/scripts/sync-plugin-version.mjs)

Do not copy maintainer conveniences blindly. Matt labels his linking script development-only; it replaces existing non-symlink destination directories. This collection deliberately tests preservation of existing installations. Retain that behavior. [Matt's linking script](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/scripts/link-skills.sh), [local preservation test](../../tests/test_git_safety.py#L201)

## Discovery and distribution

Skills CLI supports selection by skill name, listing without installation, local sources, and GitHub sources. Its discovery implementation recognizes both top-level skill directories and nested directories under `skills/`. Avoid a collection-level `SKILL.md`: discovery can treat it as the skill and return before discovering children. Verify discovery with the installer version you support. [Skills CLI README](https://github.com/vercel-labs/skills/blob/main/README.md), [discovery implementation documentation](https://github.com/vercel-labs/skills/blob/main/_autodocs/api-reference/discovery.md)

GitHub hosts the skill contents. Skills directory listing is driven by installation telemetry; it is separate from whether a repository can be installed. Publishing an npm package is unnecessary for this route. [Skills FAQ](https://skills.sh/docs/faq)

### Disposable experiment on this collection

Copied both real skill packages into each layout below, listed them, and installed them into disposable projects for Codex and Claude Code. The comparison included every regular file, including licenses, Git safety guidance, Mentor schema, examples, evaluations, and validator.

| Source layout | Discovery | Default symlink installation | Explicit copy installation |
| --- | --- | --- | --- |
| `<name>/SKILL.md` | Both skills | PASS | PASS |
| `skills/<name>/SKILL.md` | Both skills | PASS | PASS |
| `skills/<category>/<name>/SKILL.md` | Both skills | PASS | PASS |

Six installation runs passed, verifying four installed directories per run: the two canonical skill directories and the two Claude Code destinations. All four Clean Project files and all nine Mentor files matched their source hashes. Default installations linked the Claude destinations; explicit copy installations did not. Source files and the global installer lock stayed unchanged; disposable projects were removed. Telemetry was disabled.

The experiment used two agents because Skills CLI 1.7.2 selects copy mode for a single distinct destination. An initial assertion expecting symlink mode for Codex alone was corrected after inspecting that installer behavior; no skill or installer code was changed. The experiment covers local-source discovery and file delivery, not hosted GitHub retrieval or runtime behavior inside either harness.

To inspect discovery without installation, use the documented CLI with a local collection path:

```sh
npx skills@1.7.2 add /absolute/path/to/skills --list
```

The experiment script and detailed hashes are local research evidence, outside the repository. Its results motivate a tracked acceptance check; this document does not make that check available to other contributors yet.

## Repository fit and the smallest useful improvements

The current layout already isolates instructions and supporting resources per skill. Clean Project has 57 lines in its entrypoint and delegates detailed Git checks to a reference; Mentor has 323 lines and bundles its own validator. Both carry MIT licenses into standalone installations. Keep these properties. [Clean Project](../../clean-project/SKILL.md), [Mentor](../../mentor/SKILL.md), [license policy](../../README.md#license)

| Concern | Present evidence | Recommendation, not implemented |
| --- | --- | --- |
| Collection acceptance | Two independently documented validation commands; no tracked collection-wide installation check or workflow. | Reuse both validators and check discovery, complete package delivery, relative resources, and licenses together. Keep fast structural checks distinct from model evaluations. |
| Installation preservation | The Git safety suite executes the README's symlink recipe against a synthetic one-file skill and existing destinations. | Preserve this valuable safety check; add actual-package delivery coverage rather than replacing it or treating it as a full installer test. |
| Behavioral evidence | The cleanup report describes a larger disposable workflow whose fixture/verifier remains in the local task workspace. Mentor's validator checks evaluation definitions without running their prompts. | Retain a sanitized reproducible cleanup fixture and explicitly distinguish command checks, structural checks, model evaluations, and same-session workflow evidence. |
| Release applicability | `v0.1` contains only Clean Project; current `main` includes Mentor. README states the difference. A historical report still describes the once-empty `main`. | Bind future reports to tested commits and state their scope; preserve historical outcomes while marking superseded checkout context. |
| Contributor navigation | Catalog and installation guidance exist; package expectations and validation knowledge are spread across several files. | Add a short contribution contract when implementing collection acceptance; discover skills from their entrypoints instead of adding a second hand-maintained catalog. |

Evidence: [verification instructions](../../README.md#verification), [installation regression](../../tests/test_git_safety.py#L201), [Mentor evaluation checks](../../mentor/scripts/validate.mjs#L302), [cleanup workflow report and limitations](../testing/2026-10-11-clean-project-e2e.md).

A future move to `skills/<name>/` must update documentation, path-dependent tests, and maintained local links together. A categorized tree should wait until browsing the collection is actually difficult. A plugin manifest should wait for a supported native plugin channel. A generated catalog, registry, shared validator framework, or Changesets dependency would add maintenance without resolving an observed need in this two-skill collection. These are scope judgments from the repository inspection and the successful layout experiment.

## Verification and limits

- `main` was selected and pulled with `--ff-only`; it was already current at `0323703`.
- Clean Project's public Git recipe suite passed **13/13** on this snapshot.
- `node mentor/scripts/validate.mjs` passed. This checks packaged definitions and examples, not model execution or live URL freshness.
- Discovery and complete file delivery passed for all three layouts and both installation modes described above.
- The existing untracked `pr-1-review.md` was preserved. Production instructions, tests, configuration, and releases were not changed by this research.

Not rerun: the full conversational cleanup workflow, fresh-model evaluations, hosted installation, other operating systems, or other harnesses. No claims of those checks follow from the local installation experiment.
