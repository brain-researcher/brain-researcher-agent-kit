---
name: worktree-pr-cycle
description: Ship a change the SAME way as prior PRs — isolated worktree off origin/master, run the gate, Codex-review, fix, hand off to the user to merge, then prune the branch and worktree. Use when the user says "merge and clean up", "同上个 PR 的流程", "开个 worktree 做", or when a PR-shaped change to brain_researcher needs the repeatable one-change→one-PR loop.
---

# worktree-pr-cycle

The repeatable "one change → one PR" loop the user drives on essentially every PR. This is the
**non-deploy** half of shipping; hand the actual prod rollout to `br-rollout`.

## When To Use

- The user says "merge and clean up", "跟前几个 PR 一样的流程", "开一个新的 worktree".
- Any multi-commit / PR-shaped change to `brain_researcher`.
- NOT for: prod deployment (use `br-rollout`); trivial single-file edits that don't warrant a PR.

## Why A Worktree (Not The Shared Checkout)

The shared checkout `~/projects/brain_researcher` has a HEAD that **floats across concurrent
sessions** and often lags `origin/master`. Committing on it has landed changes on a parallel
session's branch (had to be reverted) and stacked commits on the wrong base. Always work in a
fresh worktree cut from `origin/master`.

## Workflow

1. **Open a clean worktree off origin/master**

   ```bash
   git -C ~/projects/brain_researcher fetch origin
   git -C ~/projects/brain_researcher worktree add /tmp/br-<task> origin/master -b <branch>
   export PYTHONPATH=/tmp/br-<task>/src
   ```

2. **Preflight-grep the enabling symbol** — if the change depends on a symbol that must already
   exist on master, `grep -rq "<symbol>" /tmp/br-<task>/src` and refuse to run if absent. Version
   skew is silent — a missing feature degrades to a plausible-wrong result, not an error.

3. **Build + run the gate** — the narrowest meaningful check for the change: focused pytest, the
   autoresearch suite, or a lint/typecheck. Activate the env first (per Bash call, since shell
   state does not persist):

   ```bash
   source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate brain_researcher
   ```

4. **Adversarial review via the Codex subagent** — delegate through the **Task/Agent tool**
   (`codex:rescue`), NOT `Skill(codex:rescue)` (that re-enters this command and hangs the session).
   Codex reviews usually come back REQUEST-CHANGES; apply fixes and re-run the gate.
   - Codex's bubblewrap sandbox cannot mount `/tmp/br-*` git-annex worktrees whose `.git` is a
     symlink — if it errors there, fall back to inline edits.
   - After Codex returns, verify the edits actually landed with `git status` / `git diff` before
     claiming them (Codex has reported edits it did not apply).

5. **Open the PR, then STOP** — the **user merges** each PR (standing protocol). Do not
   `gh pr merge --admin` (denied, and against convention). Omit the Claude `Co-Authored-By` trailer.

6. **After the user merges — prune**

   ```bash
   git -C ~/projects/brain_researcher worktree remove /tmp/br-<task>
   git -C ~/projects/brain_researcher branch -d <branch>
   ```

## Client Prompt Artifacts

- `agents/openai.yaml` for Codex/OpenAI skill launch metadata.
- `agents/claude_code.md` for a compact Claude Code instruction block. Keep this in the skill
  directory; do not duplicate the policy into `CLAUDE.md` (repo convention: instructions live in
  AGENTS.md; CLAUDE.md only points there).

## Honesty / Invariants

- `succeeded` = the gate passed on this branch, NOT that the PR is merged or deployed. Keep merge +
  rollout as explicit open items in the handoff.
- New untracked files created in the shared checkout must be **moved and committed via the
  worktree**, never staged in place on the shared checkout.
- The user merges; the agent never force-merges or force-pushes the shared checkout.

## Gotchas

- Activate conda per Bash call (shell state does not persist) or the gate runs the wrong interpreter.
- `git worktree remove` fails (exit 128 "cannot remove working tree") if the worktree is dirty —
  commit/stash or `--force` deliberately.

## Related

- `skills/brain-researcher-git-worktree-hygiene` — the bulk branch/worktree cleanup and
  safe-to-delete workflow. This skill deliberately does not re-document the hygiene-sweep details:
  when worktrees pile up or you need to decide whether a branch/worktree is safe to remove, use that
  skill for the sweep and refer back here for the per-change ship loop.
