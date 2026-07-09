---
name: repo-github-workflow
description: Repository-local GitHub workflow discipline for PR review comments, GitHub Actions CI failures, commit/push/PR publishing, and mixed-worktree safety.
---

# Repo GitHub Workflow

## Scope

Use this skill when a Brain Researcher agent is asked to:

- inspect or address GitHub PR review comments
- debug failing GitHub Actions checks
- commit, push, or open a PR
- decide what belongs in a GitHub-bound change when the worktree is mixed

This is workflow guidance, not a product API. Prefer the active GitHub connector
when it exposes the needed repo, issue, PR, comment, or label operation. Use
local `git` and `gh` when connector coverage is incomplete, especially for
Actions logs, current-branch PR discovery, branch operations, and pushing.

## Preflight

1. Identify the repo and target PR or branch.
2. Run `git status --short` and inspect the relevant diff before staging or
   publishing.
3. If GitHub writes or Actions logs are needed, check `gh auth status`.
4. Keep unrelated dirty files out of the operation unless the user explicitly
   says the whole worktree belongs in scope.

## PR Review Comments

For review feedback, separate three surfaces:

- PR metadata and changed files
- top-level comments
- thread-aware inline review comments

Thread state matters. Flat comment APIs often lose `resolved`, `outdated`, and
inline location context. If unresolved inline comments are material, use `gh api
graphql` or a connector surface that exposes review threads. Group actionable
items by file or behavior area, then fix only the selected actionable threads.

Do not resolve threads, submit reviews, or post replies unless the user asks for
that write action.

## CI Failures

For GitHub Actions failures:

1. Resolve the PR or branch SHA.
2. Inspect failing checks before changing code.
3. Pull the failing job log or run summary with `gh run view` / `gh pr checks`.
4. Summarize root cause, the check name, and the smallest local validation that
   should reproduce or cover the issue.
5. Treat non-GitHub Actions providers as report-only unless the user requests a
   separate provider-specific investigation.

Do not infer root cause from a red check name alone. Logs or reproduced local
failures are the evidence.

## Publishing

When the user asks to commit, push, or open a PR:

1. Confirm intended scope from `git status` and diffs.
2. Stage explicit paths in a mixed worktree.
3. Commit with a terse message tied to the actual change.
4. Run the narrow validation that supports the change if it has not already run.
5. Push the current branch with upstream tracking.
6. Open a draft PR by default unless the user asked for ready-for-review.

The PR body should state what changed, why it changed, the user/developer
impact, root cause for fixes, and validation run.

## Guardrails

- Never silently stage unrelated user changes.
- Never push without understanding the branch and target remote.
- Do not claim CI is fixed until the relevant check reruns or a local
  reproduction is validated.
- If auth, repo scope, or PR identity is missing, report that blocker directly.
