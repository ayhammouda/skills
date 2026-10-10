# Skills

Reusable agent skills for project maintenance.

## Clean Project

[clean-project](clean-project/SKILL.md) prepares an old project, completed milestone, or release for handoff. It assesses obsolete files and stale worktrees, offers to retain useful decisions in maintained documentation, and preserves unfinished work and recovery options.

Local branch deletion is opt-in. AI authorship, filenames, and age alone never justify removal. Read the [Git safety reference](clean-project/references/git-safety.md) before worktree or branch cleanup.

## Install in Codex

Clone the skills branch:

```sh
git clone --branch develop https://github.com/ayhammouda/skills.git
cd skills
```

Link this checkout when the installation path is unused. Existing directories and links are preserved:

```sh
mkdir -p "$HOME/.codex/skills"
skill_dest="$HOME/.codex/skills/clean-project"
[ -e "$skill_dest" ] || [ -L "$skill_dest" ] || ln -sn "$PWD/clean-project" "$skill_dest"
```

Invoke `$clean-project` with the project path and desired scope. A bare invocation produces a proposal. For example: “Recover this project into a shareable state; ask before consolidating useful decisions into docs.”

## Verify the Git recipes

With Python 3 and Git 2.36 or later, run:

```sh
python3 -B tests/test_git_safety.py
```

These checks exercise the documented commands in disposable repositories with isolated Git configuration. Some deliberately demonstrate unsafe native Git behavior inside those fixtures. They do not run cleanup against your projects or prove agent compliance with the skill.
