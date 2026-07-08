---
name: survival-gated-claim-adjudication
description: Adjudicate an autonomous or predictive run's claim over its gathered evidence and required falsifiers BEFORE reporting a winner or dispatching gated compute — so a refuted claim's score is withheld and a bare-magnitude ranking can never win. Use when an autonomous/predictive run produced candidates and you're about to rank them or send work to the cluster.
---

# Survival-Gated Claim Adjudication

## Overview

This skill enforces the verification-bench discipline: an autonomous or predictive
run's candidates are **adjudicated against required falsifiers before** any winner
is reported or any gated compute is dispatched. A claim whose required falsifier
*refuted* it has its score **withheld** — it cannot win a magnitude ranking. Bare
magnitude never selects.

Use it when an autonomous/predictive run produced candidate results and you're about
to report a winner/ranking or dispatch external (SLURM) compute. Do **not** use it
for the full governed run demonstration (`governed-autoresearch-episode`) — this is
the lightweight commit + gate + compare discipline any autonomous run hits.

Authored against Brain Researcher MCP `contract_version >= 2026-07-08`.

## Workflow

1. **Adjudicate the claim** over already-gathered evidence:
   `claim_commit(run_dir=..., evidence_payload_path=..., required_falsifiers=[...])`.
   This runs the required-falsifier battery and produces the survival-gated verdict
   *before* the first gated dispatch. Feed **raw arrays only** — never a precomputed
   `retained_pct` / p-value (that is an answer-proof channel).
2. **Respect the gates** (see `references/vb-gates.md`):
   - VB-1: a required axis with **no verdict** blocks finalize.
   - VB-2: a claim whose required falsifier **refuted** it has its score withheld —
     it cannot win a magnitude ranking.
   - VB-3: an **incomplete battery** blocks external dispatch.
3. **Dispatch only if the battery is complete.** `slurm_submit` (the VB-3 dispatch
   gate reads `{run_dir}/society`). If the gate blocks, do not force the submit.
4. **Show gated vs bare-magnitude.** `run_compare` + `run_scorecard` (+
   `loop_profile_get`) to display how survival-gating re-ranks candidates versus a
   naive magnitude sort — the winner must be the *gated* one.
5. **Report the survivor, not the loudest.** State which candidates were withheld and
   why (which falsifier refuted them).

If BR is unreachable or `claim_commit` is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not report a winner you could not adjudicate.

## Anti-patterns

- **Do not** report a bare-magnitude winner/ranking without adjudication.
- **Do not** let a claim whose required falsifier refuted it win — its score is
  withheld (VB-2).
- **Do not** finalize while a required axis has no verdict (VB-1), or dispatch with
  an incomplete battery (VB-3).
- **Do not** feed a precomputed `retained_pct` / p-value into `claim_commit` — raw
  arrays only; a precomputed summary is an answer-proof leak.
- **Do not** describe adjudication as having produced the scientific result — it
  gates which result may be reported.

## Resources

- `references/vb-gates.md` — the VB-1 / VB-2 / VB-3 gates, the raw-arrays
  answer-proof rule, and the `BR_VB_ADJUDICATE_AUTONOMOUS` behavior note.

## Example user requests

- "Rank these autonomous-run candidates and tell me the winner."
- "Before I send this to SLURM, is the falsifier battery complete?"
- "Show me how survival-gating changes the ranking vs raw effect size."
- "Adjudicate this predictive run's claim against its required falsifiers."
