---
name: codex-review-operator
description: Prompting and result-handling discipline for using Codex or other reviewer agents on Brain Researcher code, reviews, and adversarial checks.
---

# Codex Review Operator

## Scope

Use this skill when asking a secondary coding or review agent for help, or when
presenting that agent's output back to the user. The goal is to preserve the
review boundary: review output should not silently become edits, and uncertain
findings should not be upgraded into facts.

## Prompt Shape

Use compact, block-structured prompts for delegated work:

- `task`: exact job, target files or branch, and expected end state
- `output_contract`: required answer shape and ordering
- `default_follow_through_policy`: what the agent should do without asking
- `verification_loop`: checks required before finalizing
- `grounding_rules`: what evidence is allowed and how inference is labeled
- `action_safety`: write scope, dirty-worktree handling, and irreversible actions

Prefer one clear task per delegated run. Split unrelated code review, product
QA, manuscript edits, and deployment work into separate prompts.

## Review-Only Boundary

For review tasks:

1. Findings come first, ordered by severity.
2. Each finding needs a file/line anchor, failure mode, impact, and concrete
   recommendation.
3. If there are no findings, say that clearly and include only brief residual
   risk.
4. Stop after presenting review findings. Do not apply fixes until the user asks
   which findings to fix.

This boundary matters because review mode and implementation mode have different
evidence standards.

## Adversarial Review

Use adversarial review when the question is "should this approach ship?" rather
than "are there syntax or unit-test bugs?"

Prioritize high-cost failure surfaces:

- auth, permission, tenant, and trust boundaries
- data loss, corruption, duplication, and irreversible state changes
- retries, rollback, partial failure, idempotency, and race conditions
- stale state, schema drift, migrations, and compatibility gaps
- empty, null, timeout, and degraded dependency behavior
- observability gaps that would hide failure or block recovery

Report only material findings. A single defensible blocker is better than a long
list of weak concerns.

## Result Handling

When another agent returns output:

- preserve its verdict, severity ordering, file paths, and line numbers
- keep "observed fact", "inference", "uncertainty", and "open question"
  distinct
- do not convert failed or malformed helper output into a guessed result
- if the helper made edits, list touched files when available
- if the helper did not run, say so instead of synthesizing a substitute answer

For Brain Researcher handoffs, combine this with
`brain-researcher-session-handoff` when durable session state should be
recoverable.
