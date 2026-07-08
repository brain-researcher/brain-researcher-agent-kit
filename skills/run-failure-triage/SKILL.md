---
name: run-failure-triage
description: Diagnose a failed or degraded Brain Researcher run from its persisted evidence and turn it into an actionable bug digest + repair context, without guessing at causes the artifacts don't support. Use when a run failed, stalled, or produced a surprising error and the user wants to know what went wrong and how to fix it.
---

# Run Failure Triage

## Overview

When a run fails, the honest path is to read its persisted evidence — status,
logs, metrics, bundle — and let BR's diagnostic generators turn that into a bug
digest and repair context. This skill's discipline is *diagnose from the artifacts,
not from a guess*: the reported cause must trace to something actually in the run's
logs/observation, and a proposed fix is a hypothesis to verify, not a certainty.

Use it when a run failed / stalled / errored surprisingly and the user wants "what
went wrong and how do I fix it?". Do **not** use it for a *successful* run's quality
review (that is scientific/code review), or to claim a fix worked without a re-run.

Authored against Brain Researcher MCP `contract_version >= 2026-07-08`.

## Workflow

1. **Establish the failure.** `run_get` for status + step records; `run_metrics` for
   timing/cost/status; note the failing step and its error string. Confirm it truly
   failed vs. stalled vs. degraded — they triage differently.
2. **Read the evidence.** `run_logs` for the log payloads and `run_bundle_get` for
   the normalized observation bundle (violations, policy_issues, step errors). The
   real cause lives here, not in the top-level wrapper message.
3. **Generate the digest.** `generate_bug_digest` over the run/candidate to get a
   structured failure summary. Treat it as the evidence-grounded cause, and quote
   the specific log/violation it rests on.
4. **Generate repair context.** `generate_repo_repair_context` for a
   repair-oriented synthesis (what to change, where). Present the fix as a
   *hypothesis*, with the exact evidence that motivates it.
5. **State cause → fix → how-to-verify.** Name the grounded cause, the proposed fix,
   and the concrete way to confirm it (usually a re-run). Do not declare it fixed.

If BR is unreachable or a generator is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do the manual read of `run_get`/`run_logs` and label the cause as
provisional.

## Anti-patterns

- **Do not** report a cause the artifacts do not support — trace every claimed cause
  to a specific log line, violation, or step error.
- **Do not** trust the top-level wrapper error over the step's real error in the
  bundle (wrappers can mask the true failure).
- **Do not** present a proposed repair as a confirmed fix; it is a hypothesis until
  a re-run passes.
- **Do not** conflate stalled / degraded / failed — each has a different remedy.
- **Do not** paste the full raw bundle/log JSON into the answer; quote the decisive
  lines and summarize.

## Resources

- `references/failure-triage-table.md` — failure class (policy / execution / data /
  timeout / AI-response) → which signal confirms it and which generator to lean on.

## Example user requests

- "This run failed — what went wrong?"
- "Give me a bug digest and a fix for run br_2026..._abc."
- "Why did my pipeline stall, and how do I unblock it?"
- "Diagnose this error and tell me what to change."
