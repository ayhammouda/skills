# Skills

Reusable [Agent Skills](https://agentskills.io/specification) for project maintenance. The first release, **v0.1**, includes [clean-project](clean-project/SKILL.md).

## What Clean Project does

Prepare an old dirty project, a completed milestone, or a new release for sharing with another person:

- Identify obsolete reports, temporary AI files and scripts, outdated documentation, and stale Git worktrees.
- Offer to preserve useful decisions, rationale, setup notes, and answers in maintained documentation, such as `docs/architecture.md`, `docs/getting-started.md`, and `docs/faq.md`.
- Remove confirmed obsolete artifacts with recovery in place, while preserving unfinished work and uncertain items.
- Optionally remove eligible local branches whose upstream branches were deleted.

This is an instruction package for a coding agent, not an automatic cleanup executable. **A bare invocation produces a proposal; local branch deletion is always opt-in.** AI authorship, filenames, and age alone never justify deletion. Active agent configuration and useful historical records are preserved. See the [workflow](clean-project/SKILL.md) and [Git safety reference](clean-project/references/git-safety.md).

## Requirements

- A coding harness with Agent Skills support, project filesystem access, and shell tools. Use a current version of your harness.
- Git **2.36 or later** for the documented worktree and branch checks. Unsupported Git inventory leaves those operations in report-only mode; projects without Git can still receive file assessment.
- Node.js **22.20 or later** and `npx` only for the optional installer below. Manual installation needs neither Node.js nor Python. Python 3 is needed only to run this repository's tests.

## Install with the Skills CLI

From the project where you want to use the skill, run:

```sh
npx skills@1.7.2 add https://github.com/ayhammouda/skills/tree/v0.1 --skill clean-project
```

Choose your harness or harnesses in the prompts and review the destination before confirming. This pins the skill to **v0.1** and the installer to the tested version. The default scope is the current project; add `--global` to install for your user across projects. These commands work in macOS/Linux terminals and Windows PowerShell with Node.js and Git installed.

To choose specific harnesses, add their IDs from the table below, for example:

```sh
npx skills@1.7.2 add https://github.com/ayhammouda/skills/tree/v0.1 --skill clean-project --agent codex claude-code cursor
```

Add `--list` to inspect available skills without installing. Use `--copy` if you prefer independent copies to symlinks. Preserve any local customizations before reinstalling. The [Skills CLI documentation](https://github.com/vercel-labs/skills#readme) describes agent selection, scope, and installation options.

## Manual installation and harness locations

Clone the release into a new directory, or download and extract its [source archive](https://github.com/ayhammouda/skills/archive/refs/tags/v0.1.zip):

```sh
git clone --branch v0.1 --depth 1 https://github.com/ayhammouda/skills.git
cd skills
```

Copy the **entire `clean-project` folder**, including `references/`, `agents/`, and `LICENSE`, into one of the locations below. The resulting path must end in `skills/clean-project/SKILL.md`. Choose project scope to share the skill through version control, or user scope for your own projects. Do not replace an existing installation without preserving your changes.

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

For Codex on macOS/Linux, you can link the cloned folder instead of copying it. Run this from the cloned repository root; existing directories and links are left untouched:

```sh
mkdir -p "$HOME/.agents/skills"
skill_dest="$HOME/.agents/skills/clean-project"
[ -e "$skill_dest" ] || [ -L "$skill_dest" ] || ln -sn "$PWD/clean-project" "$skill_dest"
```

Keep that checkout in place while using the link. On Windows, copy the folder or use the installer with `--copy` to avoid symlink requirements. If you already installed this skill through an older Codex `~/.codex/skills` path, avoid adding a duplicate installation.

## Use the skill

Start a new session or reload your harness's skills, then confirm `clean-project` appears in its skill picker/list. In Codex, invoke **`$clean-project`** with the project path and desired scope. In any supporting harness, explicitly ask it to use the **clean-project** skill:

> Use clean-project to assess this repository for handoff. Propose cleanup and useful notes to retain; make no changes yet.

> Use clean-project to clean this repository after the release. Remove confirmed obsolete artifacts and eligible worktrees. Ask whether useful decisions should be consolidated into docs. Keep local branches.

> Also include eligible local branches whose upstreams were deleted; preserve branches with unique or uncertain work.

Expect a concrete plan, a decision about useful notes, recoverable cleanup, and a final account of removed, retained, and unresolved items. Existing authorization is reused; a Git-ref handoff is not ready until its intended changes are committed. Publishing requires its own authorization.

If the skill is missing, check the destination, folder name, and full contents, then reload the harness. If it lacks native skill discovery, explicitly ask it to read `clean-project/SKILL.md` and its linked reference before acting. Cloud and remote sessions need the skill installed in that environment; a local user installation alone is insufficient. For Codex-managed worktrees, use the owner application's archive lifecycle; if unavailable, retain them for that owner.

## Verification

From this repository, with Python 3 and Git 2.36 or later:

```sh
python3 -B tests/test_git_safety.py
```

These checks exercise documented commands in disposable repositories with isolated Git configuration. Some deliberately demonstrate unsafe native Git behavior inside those fixtures. They never clean your projects and do not prove that every model follows the skill.

The [dated end-to-end report](docs/testing/2026-10-11-clean-project-e2e.md) covers temporary artifacts, stale worktrees, deleted upstream branches, useful notes retained in docs, and preservation of user work. Installation guidance is based on the linked vendor documentation; cleanup behavior has not been tested in every harness or on every operating system.

## License

[MIT](LICENSE), copyright 2026 Aymen Hammouda. A copy of the license is included inside the skill so it travels with standalone installations.
