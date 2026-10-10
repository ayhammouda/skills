# Git safety for project cleanup

Read when worktrees or branches are in scope. Commands below use Git directly; honor any required command wrapper. Substitute only observed, quoted values. Use argument arrays or literal pathspecs for filenames; never parse whitespace-separated `branch -vv` output into deletion commands.

Requires Git 2.36 or later (`git --version`), including `worktree list --porcelain -z`. On older Git or unsupported/failed inventory commands, report findings only; do not improvise a destructive fallback. Disable automatic maintenance for cleanup mutations with command-local `git -c maintenance.auto=false …`; fetch also uses `--no-auto-maintenance`. This does not stop independently scheduled maintenance: if other writers cannot be excluded during retirement, keep the target.

## Inventory and identity

Resolve the Git top level and common directory for the project and each worktree. Request absolute paths, then canonicalize filesystem paths before comparing; an unrelated clone's `.git` is not the same repository. Capture the current checkout, branch/HEAD, staged/unstaged changes, untracked files, and protected integration branches. Read the project's instructions and established integration target; do not assume `origin/main` or use whichever branch happens to be checked out.

Useful commands, with `repo` and `wt` set to observed absolute paths:

```sh
git -C "$repo" rev-parse --path-format=absolute --show-toplevel --git-common-dir
git -C "$repo" worktree list --porcelain -z
git --no-optional-locks -C "$wt" status --porcelain=v1 -z --untracked-files=normal --ignored=traditional --ignore-submodules=none
git -C "$wt" ls-files -v -z
git -C "$repo" for-each-ref --format='%(refname)%00%(refname:lstrip=2)%00%(objectname)%00%(upstream)%00%(upstream:remotename)%00%(upstream:remoteref)' refs/heads/
```

Parse worktree/status/file output by NUL records, respecting each command's format (status renames have an extra path). For `for-each-ref`, split records on newline, then each record into six NUL-separated fields; Git always adds a newline and refnames cannot contain one. Do not split the whole ref stream on NUL. Field 2 is the exact local branch name for `branch -d`.

The status command is an overview that collapses directories where possible and avoids optional index writes/locks. Capture and parse full output outside the model context; show bounded summaries without treating truncation as a complete inventory. Inspect candidate directories individually before deletion; `.env` files, databases, and unique notes are not disposable build output. Record names and classification without exposing secret values. In sparse checkouts, verify index entries and tracked consumers too; absence from disk is not evidence of obsolescence.

Check task/app attachments and relevant running processes to establish ownership. An old commit date, merged PR, absent lock, or quiet process list alone does not establish inactivity. Keep current, primary, locked, pinned, shared, actively used, and ownership-unknown worktrees. Do not stop services or other agents merely to make cleanup possible.

Check each worktree for interrupted operations. For each `operation` in `rebase-merge`, `rebase-apply`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `BISECT_LOG`, `BISECT_START`, and `sequencer`, resolve its private state path:

```sh
git -C "$wt" rev-parse --path-format=absolute --git-path "$operation"
```

Any existing marker means active: keep the worktree and defer local branch deletion in that repository until the operation is resolved. A clean status and a retained HEAD do not preserve rebase todo lists or bisect state. Do not abort an operation to enable cleanup.

## Removing existing worktrees

Before removal, all of these must hold:

1. The worktree is identified, in scope, inactive, and eligible for retirement.
2. Every tracked modification, untracked file, ignored file, and nested repository is accounted for, including the checks below. Ordinary removal requires no unexplained dirty state. Submodules and embedded repositories require separate handling; Git can silently delete an ignored nested repository without force.
3. History remains recoverable after the planned operation. For attached branches, retain the branch when branch cleanup is off; verify its exact tip. For a detached HEAD, identify a durable retained branch/tag containing the commit or a verified recoverable archive. Reflogs and a written SHA alone are not durable preservation. Also consider older local-only work in its per-worktree reflog before destroying that recovery record; retain or archive it when uncertain.
4. Knowledge retention is resolved for material inside this worktree. Proposed docs must live in a retained checkout before its source disappears.

**Hidden tracked edits:** parse `ls-files -v -z` as NUL records with a one-byte tag, a space, and a path. `S` means skip-worktree; lowercase tags mean assume-unchanged (including `s` when both apply). Status can hide edits to these files. If any flagged path exists on disk, including a dangling symlink, retain the worktree for separate review and verified preservation; do not clear flags to make it removable. Missing skip-worktree files can be expected in sparse checkouts, but missing assume-unchanged files require review too. Flag checks are additional to ordinary status.

**Nested repositories:** before retiring an inactive candidate, inspect all its directories, including hidden, ignored, dependency, and build directories. Do not follow symlinks. Find nested `.git` files or directories with:

```sh
find "$wt" -mindepth 2 -name .git -prune -print0
```

Also check for bare repositories, which lack a `.git` child (repository layout such as `HEAD`, `objects`, and `refs`; verify candidate directories with Git). Any nested repository or incomplete/unreadable inspection means keep for separate handling. A collapsed ignored-directory status entry is not a complete inventory. Do not rely on `worktree remove` to detect nested repositories.

**Managed worktrees:** use the owning application's lifecycle. In Codex, inspect `list_artifacts` and pass its exact worktree identity to `archive_worktree`. It snapshots tracked changes, unpushed commits, and non-ignored untracked files. Preserve needed ignored files separately and verify the archive result before reporting success. The tool rejects primary/pinned/shared worktrees and checkouts with submodules or embedded repositories. If the tool is unavailable, the worktree belongs to another task, or archival is refused, keep it and report the reason; do not bypass the owner with filesystem deletion. Managed snapshots do not justify deleting the snapshot's recovery refs later.

**Ordinary worktrees:** after the checks, use `git -c maintenance.auto=false -C "$repo" worktree remove -- "$wt"` without force. This command can delete ignored files and hidden tracked edits even when ordinary status is clean. Moving files out, copying data, or removing a checkout is a mutation, so respect the established cleanup scope. Keep the branch by default. A failure is a reason to reassess, not add `--force`.

## Missing worktree records

Use the worktree inventory to identify missing paths. Verify each checkout is genuinely abandoned rather than moved or on an offline volume; check ownership, locks, retained history, and its private administrative state/reflog before removal. If the checkout is absent, inspect the corresponding validated per-worktree Git directory read-only; inability to account for its operation state or history means keep. A moved tree may need `worktree repair`. Recommend `worktree lock` for intermittently mounted checkouts; never unlock one to enable cleanup.

For an individually approved ordinary missing record, recheck its identity and path absence immediately before removing it by its exact absolute path:

```sh
git -c maintenance.auto=false -C "$repo" worktree remove -- "$missing_wt"
```

If the path reappears, restart the existing-worktree checks. Git still refuses locked records. Verify only the selected record disappeared and every other record remains. Prefer the owning app's lifecycle for managed records; do not edit `.git/worktrees` manually.

Do not use repository-wide `worktree prune` for this cleanup: without `--expire` it has no grace period. The three-month default belongs to GC's `gc.worktreePruneExpire`, not the standalone command. A dry run also cannot protect a different checkout that goes missing before a later batch prune.

## Optional local branches deleted upstream

Without branch-cleanup authorization, report candidates only. Exclude protected/default/integration/release branches, worktree-held branches (including other checkouts), no-upstream branches, local (`.`) upstreams, and ambiguous multi-upstream configuration. Use configured remote and full merge ref; local and remote branch names may differ.

The upstream formatting atoms expose only the first configured merge ref. For each candidate, read all values before querying a remote:

```sh
git -C "$repo" config --null --get-all "branch.$branch.merge"
git -C "$repo" config --null --get-all "branch.$branch.remote"
```

Require exactly one nonempty NUL-delimited value from each, consistent with the inventory. Missing, multiple, malformed, or failed results mean retain the branch; never silently select the first value. Recheck this configuration before deletion too.

Verify upstream absence against its actual remote:

```sh
git -C "$repo" ls-remote --exit-code --refs "$upstream_remote" "$upstream_ref"
```

Confirm the returned ref matches exactly. Exit 0 with that ref means it exists; 2 with no match means it is absent from the authenticated remote's advertised refs; other failures mean unknown. A local `[gone]` marker, missing remote configuration, restricted fetch refspec, or failed authentication is insufficient. If the remote endpoint or visibility changed, keep the branch for review.

Determine the intended integration target from current project/PR evidence. Pin both its commit and the candidate tip. If a remote target needs refreshing during authorized cleanup, inspect the remote/refspec configuration first and fetch only that branch with pruning and tag fetching disabled:

```sh
git -c maintenance.auto=false -C "$repo" fetch --no-auto-maintenance --no-prune --no-prune-tags --no-tags --recurse-submodules=no --refmap= "$target_remote" "$target_ref"
git -C "$repo" rev-parse --verify 'FETCH_HEAD^{commit}'
```

This updates local objects and FETCH_HEAD; it is not a read-only audit command. Capture its single verified result immediately as `target_oid`; do not later depend on mutable FETCH_HEAD. For an audit, query advertised refs and use already available objects or report missing evidence. Do not fetch all remotes, prune tags, change global config, or remove remote branches.

```sh
git -C "$repo" merge-base --is-ancestor "$branch_oid" "$target_oid"
```

Only exit 0 proves ancestry; 1 means not proven integrated, and other nonzero codes are errors. Shallow history can leave proof incomplete. Squash/rebase merges require separate review; matching trees or a merged PR label alone do not prove every local commit is included. Keep these branches by default. Intentional disposal of unique history requires a separate specific instruction and a verified recovery plan.

Immediately before deletion, confirm the branch still has the reviewed OID, still has no worktree, still lacks its upstream remotely, and is not protected. Serialize cleanup against other writers; if concurrent changes cannot be ruled out, keep the target. Use `git -c maintenance.auto=false -C "$repo" branch -d -- "$branch"`. This is an additional safety check, not a substitute for intended-target ancestry: `-d` may use a different upstream or current HEAD. If it refuses, retain and report it; do not rewrite upstream config, switch the user's checkout, or upgrade to `-D` to obtain a clean report.

## Final checks and sources

Rerun worktree/ref inventory and compare with the exact action list. Recheck retained checkout status against the starting state. Confirm archive/backup locations and restore instructions. Cleanup is partial when a target remains uncertain; state that directly.

Primary references: [worktree](https://git-scm.com/docs/git-worktree), [worktree implementation](https://github.com/git/git/blob/master/builtin/worktree.c), [status](https://git-scm.com/docs/git-status), [ls-files](https://git-scm.com/docs/git-ls-files), [for-each-ref](https://git-scm.com/docs/git-for-each-ref), [branch](https://git-scm.com/docs/git-branch), [ls-remote](https://git-scm.com/docs/git-ls-remote), [merge-base](https://git-scm.com/docs/git-merge-base), [fetch](https://git-scm.com/docs/git-fetch), [Git 2.36 release notes](https://github.com/git/git/blob/v2.36.0/Documentation/RelNotes/2.36.0.txt).
