---
name: brain-researcher-docs-public-prune
description: Brain Researcher public docs cleanup and release-branch workflow. Use when pruning or reorganizing public docs, stale docs references, README/release docs, changelog links, MkDocs surfaces, or clean PR branches while the shared checkout may contain unrelated WIP.
---

# Brain Researcher Docs Public Prune

## Overview

Use this skill to turn a docs cleanup request into a clean, reviewable branch
without disturbing unrelated work in the shared checkout. It is for public
surface cleanup, not a general docs audit.

## Workflow

1. Read `AGENTS.md` and inspect current state:
   - `git status --short`
   - `git branch --show-current`
   - `git worktree list`
   - `git fetch origin` when a clean branch from `origin/master` is needed
2. If the shared checkout is dirty or on an unrelated branch, create a separate
   temporary worktree from `origin/master` and do the public docs cleanup there.
3. Keep scope explicit. Common public-prune surfaces have included:
   - `docs/archive/`
   - `docs/audits/`
   - `docs/api/`
   - `docs/runbooks/`
   - stale links in `docs/review/`, `docs/CHANGELOG.md`, and
     `docs/how-to-add-tool.md`
4. Inventory before deleting. Preserve examples/templates and active docs unless
   the requested cleanup scope already makes deletion clear.
5. Remove stale references after moving or deleting docs. Use targeted `rg`
   searches for the exact paths and filenames.
6. Validate the clean branch, push it, and open a PR only when the user asked for
   publishing.

## Commands

Typical command pattern:

```bash
git status --short
git worktree list
git fetch origin
tmpdir="${TMPDIR:-/tmp}/br-docs-prune-publish"
git worktree add -b chore/docs-public-surface-prune "$tmpdir" origin/master
git diff origin/master..HEAD --check
python -m mkdocs build -f mkdocs-simple.yml --quiet
```

If cherry-picking a prior docs-prune stack creates modify/delete conflicts on
legacy docs, resolve in favor of deletion only when that is the accepted branch
intent. If `git worktree remove` fails for a temporary worktree, verify the
branch is pushed and no other session owns it before using `rm -rf <worktree>`
followed by `git worktree prune`.

## Guardrails

- Never revert, delete, or stage unrelated dirty work from the shared checkout.
- Do not treat a clean PR branch as proof that the main checkout is clean.
- Do not relitigate every subdirectory when the user has already accepted a
  broad cleanup scope, but still check stale references before pushing.
- Separate docs cleanup, release readiness, and prod rollout status.

## Handoff

Report the branch, PR URL if created, validation commands, intentionally
preserved dirty work, temporary worktrees removed, and the next command for
review. Use `unrelated-dirty-worktree` or `uncommitted-local` labels when
appropriate.
