# Skills

Reusable agent skills. The initial skill is on `develop`; `main` intentionally contains no files until the pull request is merged.

## Clean Project

[clean-project](clean-project/SKILL.md) prepares an old project, completed milestone, or release for handoff. It assesses obsolete files and stale worktrees, offers to retain useful decisions in maintained documentation, and preserves unfinished work and recovery options.

Local branch deletion is opt-in. AI authorship, filenames, and age alone never justify removal. Read the [Git safety reference](clean-project/references/git-safety.md) before worktree or branch cleanup.

## Install in Codex

Clone the working branch:

```sh
git clone --branch develop https://github.com/ayhammouda/skills.git
cd skills
```

If `~/.codex/skills/clean-project` is not already installed, link this checkout:

```sh
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD/clean-project" "$HOME/.codex/skills/clean-project"
```

Invoke `$clean-project` with the project path and desired scope. A bare invocation produces a proposal. For example: “Recover this project into a shareable state; ask before consolidating useful decisions into docs.”
