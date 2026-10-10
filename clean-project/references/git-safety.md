# Git safety for project cleanup

Read when worktrees or branches are in scope. Commands below use Git directly; honor any required command wrapper. Substitute only observed, quoted values. Use argument arrays or literal pathspecs for filenames; never parse whitespace-separated `branch -vv` output into deletion commands.

## Inventory and identity

Resolve the Git top level and common directory; worktrees must belong to that common directory. Capture the current checkout, branch/HEAD, staged/unstaged changes, untracked files, and protected integration branches. Read the project's instructions and established integration target; do not assume `origin/main` or use whichever branch happens to be checked out.

Useful commands, with `repo` and `wt` set to observed absolute paths:

```sh
git -C "$repo" rev-parse --show-toplevel --git-common-dir
git -C "$repo" worktree list --porcelain -z
git -C "$wt" status --porcelain=v1 -z --untracked-files=all --ignore-submodules=none
git -C "$wt" status --porcelain=v1 -z --untracked-files=normal --ignored=matching --ignore-submodules=none
git -C "$repo" for-each-ref --format='%(refname)%00%(objectname)%00%(upstream)%00%(upstream:remotename)%00%(upstream:remoteref)%00' refs/heads/
```

Interpret NUL-delimited output programmatically when paths are unusual. The second status pass inventories ignored entries without expanding every ignored build directory. Inspect candidate ignored directories individually; `.env` files, databases, and unique notes are not disposable build output. Record names and classification without exposing secret values. In sparse checkouts, verify index entries and tracked consumers too; absence from disk is not evidence of obsolescence.

Check task/app attachments and relevant running processes to establish ownership. An old commit date, merged PR, absent lock, or quiet process list alone does not establish inactivity. Keep current, primary, locked, pinned, shared, actively used, and ownership-unknown worktrees. Do not stop services or other agents merely to make cleanup possible.

## Removing existing worktrees

Before removal, all of these must hold:

1. The worktree is identified, in scope, inactive, and eligible for retirement.
2. Every tracked modification, untracked file, ignored file, and nested repository is accounted for. Ordinary removal requires no unexplained dirty state. Submodules and embedded repositories require separate handling; never force through Git's refusal.
3. History remains recoverable after the planned operation. For attached branches, retain the branch when branch cleanup is off; verify its exact tip. For a detached HEAD, identify a durable retained branch/tag containing the commit or a verified recoverable archive. Reflogs and a written SHA alone are not durable preservation. Also consider older local-only work in its per-worktree reflog before destroying that recovery record; retain or archive it when uncertain.
4. Knowledge retention is resolved for material inside this worktree. Proposed docs must live in a retained checkout before its source disappears.

**Managed worktrees:** use the owning application's lifecycle. In Codex, inspect `list_artifacts` and pass its exact worktree identity to `archive_worktree`. It snapshots tracked changes, unpushed commits, and non-ignored untracked files. Preserve needed ignored files separately and verify the archive result before reporting success. The tool rejects primary/pinned/shared worktrees and checkouts with submodules or embedded repositories. If the tool is unavailable, the worktree belongs to another task, or archival is refused, keep it and report the reason; do not bypass the owner with filesystem deletion. Managed snapshots do not justify deleting the snapshot's recovery refs later.

**Ordinary worktrees:** after the checks, use `git -C "$repo" worktree remove -- "$wt"` without force. This command can delete ignored files even when ordinary status is clean. Moving files out, copying data, or removing a checkout is a mutation, so respect the established cleanup scope. Keep the branch by default. A failure is a reason to reassess, not add `--force`.

## Missing worktree records

Preview with `git -C "$repo" worktree prune --dry-run --verbose`. It addresses missing administrative records, not existing directories. Verify that each listed checkout is genuinely gone rather than moved or on an offline volume; check locks, ownership, and history recovery first. A moved tree may need `worktree repair`, not pruning.

Prune is repository-wide. Run it only when every record in the immediate preview is eligible and the same expiry policy is used. Otherwise leave pruning pending. Do not add `--expire now` to make more records eligible or edit `.git/worktrees` manually. Prefer the owning app's lifecycle for managed records.

## Optional local branches deleted upstream

Without branch-cleanup authorization, report candidates only. Exclude protected/default/integration/release branches, worktree-held branches (including other checkouts), no-upstream branches, local (`.`) upstreams, and ambiguous multi-upstream configuration. Use configured remote and full merge ref; local and remote branch names may differ.

Verify upstream absence against its actual remote:

```sh
git -C "$repo" ls-remote --exit-code --refs "$upstream_remote" "$upstream_ref"
```

Confirm the returned ref matches exactly. Exit 0 with that ref means it exists; 2 with no match means it is absent from the authenticated remote's advertised refs; other failures mean unknown. A local `[gone]` marker, missing remote configuration, restricted fetch refspec, or failed authentication is insufficient. If the remote endpoint or visibility changed, keep the branch for review.

Determine the intended integration target from current project/PR evidence. Pin both its commit and the candidate tip. If a remote target needs refreshing during authorized cleanup, inspect the remote/refspec configuration first and fetch only that branch with pruning and tag fetching disabled:

```sh
git -C "$repo" fetch --no-prune --no-prune-tags --no-tags --recurse-submodules=no --refmap= "$target_remote" "$target_ref"
git -C "$repo" rev-parse --verify 'FETCH_HEAD^{commit}'
```

This updates local objects and FETCH_HEAD; it is not a read-only audit command. Capture its single verified result immediately as `target_oid`; do not later depend on mutable FETCH_HEAD. For an audit, query advertised refs and use already available objects or report missing evidence. Do not fetch all remotes, prune tags, change global config, or remove remote branches.

```sh
git -C "$repo" merge-base --is-ancestor "$branch_oid" "$target_oid"
```

Only exit 0 proves ancestry; 1 means not proven integrated, and other nonzero codes are errors. Shallow history can leave proof incomplete. Squash/rebase merges require separate review; matching trees or a merged PR label alone do not prove every local commit is included. Keep these branches by default. Intentional disposal of unique history requires a separate specific instruction and a verified recovery plan.

Immediately before deletion, confirm the branch still has the reviewed OID, still has no worktree, still lacks its upstream remotely, and is not protected. Serialize cleanup against other writers; if concurrent changes cannot be ruled out, keep the target. Use `git -C "$repo" branch -d -- "$branch"`. This is an additional safety check, not a substitute for intended-target ancestry: `-d` may use a different upstream or current HEAD. If it refuses, retain and report it; do not rewrite upstream config, switch the user's checkout, or upgrade to `-D` to obtain a clean report.

## Final checks and sources

Rerun worktree/ref inventory and compare with the exact action list. Recheck retained checkout status against the starting state. Confirm archive/backup locations and restore instructions. Cleanup is partial when a target remains uncertain; state that directly.

Primary references: [worktree](https://git-scm.com/docs/git-worktree), [worktree implementation](https://github.com/git/git/blob/master/builtin/worktree.c), [status](https://git-scm.com/docs/git-status), [branch](https://git-scm.com/docs/git-branch), [ls-remote](https://git-scm.com/docs/git-ls-remote), [merge-base](https://git-scm.com/docs/git-merge-base), [fetch](https://git-scm.com/docs/git-fetch).
