# Skills

Reusable [Agent Skills](https://agentskills.io/specification) for project maintenance and technical learning.

| Skill | Purpose |
| --- | --- |
| [clean-project](clean-project/SKILL.md) | Prepare old projects, milestones, and releases for handoff while preserving user work and useful decisions. |
| [mentor](mentor/SKILL.md) | Build a focused learning path from current documentation, with reading guidance and optional deeper topics. |

The **v0.1** release contains `clean-project` only. The commands below use `main` for the current collection.

## What Clean Project does

Prepare an old dirty project, a completed milestone, or a new release for sharing with another person:

- Identify obsolete reports, temporary AI files and scripts, outdated documentation, and stale Git worktrees.
- Offer to preserve useful decisions, rationale, setup notes, and answers in maintained documentation, such as `docs/architecture.md`, `docs/getting-started.md`, and `docs/faq.md`.
- Remove confirmed obsolete artifacts with recovery in place, while preserving unfinished work and uncertain items.
- Optionally remove eligible local branches whose upstream branches were deleted.

This is an instruction package for a coding agent, not an automatic cleanup executable. **A bare invocation produces a proposal; local branch deletion is always opt-in.** AI authorship, filenames, and age alone never justify deletion. Active agent configuration and useful historical records are preserved. See the [workflow](clean-project/SKILL.md) and [Git safety reference](clean-project/references/git-safety.md).

## What Mentor does

[Mentor](mentor/SKILL.md) helps you learn a technical subject through a short, sequenced reading path. It prefers current official documentation, explains what to notice in each resource, offers useful references to inspect, and identifies topics to defer. It adapts to your background, goal, and time budget. Exercises and setup commands are included only when you request practice.

The package includes [example outputs](mentor/examples), a [JSON output schema](mentor/references/schema.json), and [evaluation scenarios](mentor/evals/evals.json). Its instructions and resources are imported unchanged from [ayhammouda/mentor at `160a5c3`](https://github.com/ayhammouda/mentor/tree/160a5c391cfd3f124ce8127c37cc31b910b75f4d); the bundled validator checks the files included in this collection.

## Requirements

- A current coding harness with Agent Skills support and access to the installed skill files.
- **Clean Project:** project filesystem access and shell tools; Git **2.36 or later** for the worktree and branch checks. Unsupported Git inventory leaves those operations in report-only mode; projects without Git can still receive file assessment.
- **Mentor:** web search or a current documentation lookup tool to verify learning resources.
- The tested installer, Skills CLI **1.7.2**, needs Node.js **22.20 or later** and `npx`. Manual installation needs neither Node.js nor Python. Validation needs Python 3 for Clean Project and Node.js 18+ for Mentor.

## Install with the Skills CLI

From the project where you want to use the skill, run:

```sh
npx skills add ayhammouda/skills --skill clean-project
```

For Mentor, use:

```sh
npx skills add ayhammouda/skills --skill mentor
```

To choose from the collection interactively, omit `--skill`:

```sh
npx skills add ayhammouda/skills
```

This installs from the repository's current `main` branch. Choose your harness or harnesses in the prompts and review the destination before confirming. The default scope is the current project; add `--global` to install for your user across projects. These commands work in macOS/Linux terminals and Windows PowerShell with Node.js and Git installed.

To pin Clean Project to **v0.1** and the installer to the tested version, use:

```sh
npx skills@1.7.2 add https://github.com/ayhammouda/skills/tree/v0.1 --skill clean-project
```

To choose specific harnesses, add their IDs from the table below, for example:

```sh
npx skills add ayhammouda/skills --skill clean-project --agent codex claude-code cursor
```

Add `--list` to inspect available skills without installing. Use `--copy` if you prefer independent copies to symlinks. Preserve any local customizations before reinstalling. The [Skills CLI documentation](https://github.com/vercel-labs/skills#readme) describes agent selection, scope, and installation options.

## Publishing and discovery on skills.sh

The skills are distributed directly from this public GitHub repository. No npm package or separate registry submission is required: `npx` runs the Skills CLI, which downloads the selected skill from GitHub.

To publish an addition or update, put its complete folder with a valid `SKILL.md` on `main`; users can then install it with `npx skills add ayhammouda/skills --skill <name>`. Tags provide fixed versions for users who prefer a release over the current branch. Existing releases do not gain skills added later.

The [skills.sh directory](https://skills.sh) discovers and ranks skills automatically through installation telemetry. Installations with telemetry disabled do not contribute to the listing; directory visibility is separate from being installable through the CLI. See the [official FAQ](https://skills.sh/docs/faq) and [telemetry documentation](https://skills.sh/docs/cli#telemetry). This repository does not require telemetry to install or use its skills.

## Manual installation and harness locations

Clone the current `main` branch into a new directory, or download and extract its [source archive](https://github.com/ayhammouda/skills/archive/refs/heads/main.zip):

```sh
git clone --depth 1 https://github.com/ayhammouda/skills.git
cd skills
```

For the original Clean Project release, add `--branch v0.1` to the clone command instead.

Copy the **entire folder of each skill you want** (`clean-project/` or `mentor/`), including its supporting files and `LICENSE`, into one of the locations below. The resulting path must end in `skills/clean-project/SKILL.md` or `skills/mentor/SKILL.md`. Choose project scope to share the skill through version control, or user scope for your own projects. Do not replace an existing installation without preserving your changes.

Paths below are native manual-install locations from the linked harness documentation. The installer may use a shared `.agents/skills/` directory instead. `~` means your home directory (`%USERPROFILE%` on Windows); custom configuration roots may differ.

| Harness and documentation | Installer ID | Project skills directory | User skills directory |
| --- | --- | --- | --- |
| [Codex CLI / IDE / app](https://developers.openai.com/codex/skills) | `codex` | `.agents/skills/` | `~/.agents/skills/` |
| [Claude Code](https://code.claude.com/docs/en/skills) | `claude-code` | `.claude/skills/` | `~/.claude/skills/` |
| [GitHub Copilot / VS Code](https://code.visualstudio.com/docs/copilot/customization/agent-skills) | `github-copilot` | `.github/skills/` | `~/.copilot/skills/` |
| [Cursor](https://cursor.com/docs/skills) | `cursor` | `.cursor/skills/` | `~/.cursor/skills/` |
| [Gemini CLI](https://geminicli.com/docs/cli/skills/) | `gemini-cli` | `.gemini/skills/` | `~/.gemini/skills/` |
| [OpenCode](https://opencode.ai/docs/skills/) | `opencode` | `.opencode/skills/` | `~/.config/opencode/skills/` |
| [Windsurf / Cascade](https://docs.windsurf.com/windsurf/cascade/skills) | `windsurf` | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` |
| [Cline](https://docs.cline.bot/customization/skills) | `cline` | `.cline/skills/` | `~/.cline/skills/` |
| [Roo Code](https://docs.roocode.com/features/skills) | `roo` | `.roo/skills/` | `~/.roo/skills/` |
| [Amp](https://ampcode.com/docs/customize/skills) | `amp` | `.agents/skills/` | `~/.config/agents/skills/` |
| [Google Antigravity](https://antigravity.google/docs/skills) | `antigravity` | `.agents/skills/` | `~/.gemini/config/skills/` |

Cline's documentation recommends its native directories; if an installer-created shared path is not discovered by your version, use the manual location above. Newer Windsurf/Devin Desktop versions also support `.devin/skills/`. Antigravity CLI uses `~/.gemini/antigravity-cli/skills/` and installer ID `antigravity-cli`.

For Codex on macOS/Linux, you can link a cloned skill folder instead of copying it. This Clean Project example runs from the cloned repository root; existing directories and links are left untouched. To link Mentor, replace both occurrences of `clean-project` with `mentor`:

```sh
mkdir -p "$HOME/.agents/skills"
skill_dest="$HOME/.agents/skills/clean-project"
[ -e "$skill_dest" ] || [ -L "$skill_dest" ] || ln -sn "$PWD/clean-project" "$skill_dest"
```

Keep that checkout in place while using the link. On Windows, copy the folder or use the installer with `--copy` to avoid symlink requirements. If you already installed this skill through an older Codex `~/.codex/skills` path, avoid adding a duplicate installation.

## Use the skills

Start a new session or reload your harness's skills, then confirm the installed names appear in its skill picker/list. In Codex, invoke **`$clean-project`** or **`$mentor`**. In other supporting harnesses, explicitly ask to use the named skill.

### Clean Project

Include the project path and desired scope:

> Use clean-project to assess this repository for handoff. Propose cleanup and useful notes to retain; make no changes yet.

> Use clean-project to clean this repository after the release. Remove confirmed obsolete artifacts and eligible worktrees. Ask whether useful decisions should be consolidated into docs. Keep local branches.

> Also include eligible local branches whose upstreams were deleted; preserve branches with unique or uncertain work.

Expect a concrete plan, a decision about useful notes, recoverable cleanup, and a final account of removed, retained, and unresolved items. Existing authorization is reused; a Git-ref handoff is not ready until its intended changes are committed. Publishing requires its own authorization.

For Codex-managed worktrees, use the owner application's archive lifecycle; if unavailable, retain them for that owner.

### Mentor

Give your topic and any useful background or time limit:

> Use mentor to help me learn Rust. I know Python and have a weekend. Point me to official documentation and explain what to notice as I read.

> Use mentor for Terraform modules. I understand basic Terraform and want a focused reading path, without exercises.

Request structured JSON explicitly if you need output conforming to the bundled schema. The default is a Markdown reading path.

If a skill is missing, check the destination, folder name, and full contents, then reload the harness. If it lacks native skill discovery, explicitly ask it to read the skill's `SKILL.md` and required references before acting. Cloud and remote sessions need the skill installed in that environment; a local user installation alone is insufficient.

## Verification

From this repository, with Python 3 and Git 2.36 or later:

```sh
python3 -B tests/test_git_safety.py
```

These checks exercise documented commands in disposable repositories with isolated Git configuration. Some deliberately demonstrate unsafe native Git behavior inside those fixtures. They never clean your projects and do not prove that every model follows the skill.

The [dated end-to-end report](docs/testing/2026-10-11-clean-project-e2e.md) covers temporary artifacts, stale worktrees, deleted upstream branches, useful notes retained in docs, and preservation of user work. Installation guidance is based on the linked vendor documentation; cleanup behavior has not been tested in every harness or on every operating system.

For Mentor, with Node.js 18 or later and no dependency installation:

```sh
node mentor/scripts/validate.mjs
```

This validates the schema, evaluation-case structure, resource modes, example structure, and resource deduplication. It does not execute the evaluation prompts against a model or verify that every example URL is still current.

## License

[MIT](LICENSE), copyright 2026 Aymen Hammouda. A copy of the license is included inside each skill so it travels with standalone installations.
