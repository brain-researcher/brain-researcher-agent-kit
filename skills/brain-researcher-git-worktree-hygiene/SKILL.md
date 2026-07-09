---
name: brain-researcher-git-worktree-hygiene
description: Brain Researcher git/worktree cleanup and safety workflow. Use when inspecting or cleaning branches, linked worktrees, stale refs, dirty shared checkouts, or local cleanup state in this repository.
---

# Brain Researcher Git Worktree Hygiene

## Scope

Use this skill when the task involves:

- branch or worktree cleanup
- deciding whether a branch/worktree is safe to delete
- diagnosing linked worktree access failures
- answering whether cleanup implies merge, push, or rollout status
- preparing a clean worktree for PR work while the shared checkout is dirty

This skill is about local repository hygiene. It is not proof of product
correctness, public release status, or live prod rollout.

## Preflight

Start with read-only inventory:

```bash
git status --short --branch
git worktree list --porcelain
git branch -vv --all
git remote -v
git stash list
```

If remote freshness matters and the user did not forbid git commands, run:

```bash
git fetch --prune origin
```

For the shared checkout, identify the branch explicitly before any commit,
push, merge, or deletion:

```bash
git rev-parse --abbrev-ref HEAD
```

## Classification

Classify each candidate before deletion:

- `current-shared-checkout`: never delete as cleanup.
- `dirty-worktree`: preserve unless the user explicitly approves archive/delete.
- `remote-backed-clean`: can usually be removed after rechecking clean state.
- `patch-equivalent-clean`: use `git cherry -v origin/master <branch>` or the
  appropriate default branch to confirm no unique patch remains.
- `local-unique-clean`: create and verify a bundle backup before deleting.
- `protected`: preserve branches such as backups, `git-annex`, or named
  long-lived branches unless the user explicitly asks otherwise.

Do not infer "merged" from deletion. Say whether a branch was merged,
patch-equivalent, remote-backed, or backed up.

## Safe Removal

Before deleting a worktree, re-run a clean check in that worktree when possible.

Preferred path:

```bash
git worktree remove <path>
git worktree prune -v
```

If `git worktree remove` fails because the linked worktree `.git` marker is
nonstandard or symlinked, direct directory removal is allowed only after:

1. the path was rechecked and classified as safe,
2. any unique content was backed up,
3. the user approved the cleanup scope, and
4. follow-up `git worktree prune -v` and filesystem checks verify removal.

For local-unique candidates, back up first:

```bash
git bundle create .git/br-cleanup-backups/<name>.bundle <branch>
git bundle verify .git/br-cleanup-backups/<name>.bundle
```

## Reporting

Always separate:

- local cleanup status
- merge status
- push status
- rollout necessity
- gross disk space freed
- net disk space after backups

Use risk labels such as:

- `uncommitted-local`
- `unrelated-dirty-worktree`
- `generated-artifact`
- `partial-validation`

## Guardrails

- Never stage or delete unrelated dirty work.
- Never treat branch deletion as proof that changes landed on `master` or
  `main`.
- Never claim a rollout is needed or complete from cleanup alone.
- If shell or patch tools cannot read the target worktree, stop and report
  `environment-blocked` instead of speculating from remote refs.
