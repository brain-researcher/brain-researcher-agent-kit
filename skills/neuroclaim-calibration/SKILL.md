---
name: neuroclaim-calibration
description: Calibrate a specific scientific claim into a bounded claim card whose reported strength equals its weakest binding axis (the ceiling), with forbidden-language enforcement. Use when a user has a concrete claim (a term–region association, a dataset contrast) and wants an honest strength — not the lenient-bar "supported" — before they state or memory-file it.
---

# NeuroClaim Calibration

## Overview

This skill turns a *specific* claim into a bounded claim card with an honest
strength. Its discipline is the claim-strength **ceiling**: the reported status is
the **weakest binding axis**, not the most lenient bar that happens to pass. It also
enforces the forbidden-language boundary — association or coordinate evidence alone
cannot license causal, mechanistic, externally-validated, clinically-predictive, or
biomarker language.

Use it when the user has a concrete claim (a term–region association, a dataset
contrast) and wants it calibrated. Do **not** use it to discover/screen candidate
hypotheses (`kg-hypothesis-discovery-and-verification`), to ground the anchors of a
claim you're about to state (`evidence-grounding`), or to gate a final report
(`final-report-gate`) — this is multi-axis *ceiling* calibration.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Compile the claim.** `neuroclaim_compile` — typechecks the claim, runs a
   sensitivity sweep, and reports per-axis statuses with uncertainty (its evidence
   backend is `kg_verify_hypothesis`).
2. **For a batch of claims**, use `report_claim_evidence_check` to check each claim's
   evidence in one pass.
3. **Find the binding axis.** Across the axes (e.g. structure / association /
   strict-bar / specificity / network), the reported status is the **weakest** one —
   the ceiling (see `references/axis-ceiling-table.md`). Do not report the lenient
   "supported" if a stricter axis is `weakened` or `unresolved`.
4. **Disclose the fragilities.** State the strict-bar result, specificity, and any
   network-axis fragility explicitly — a claim that passes broadly but fails on
   specificity is a *weakened* claim.
5. **Enforce forbidden language.** Map the evidence type to what the claim may say
   (association ≠ causal). Never upgrade the verb beyond the evidence.

If BR is unreachable or `neuroclaim_compile` is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not assign a strength you could not compute.

## Anti-patterns

- **Do not** report the lenient-bar "supported" when a stricter binding axis is
  `weakened` / `unresolved` — the ceiling is the weakest axis.
- **Do not** use causal / mechanistic / externally-validated / clinically-predictive
  / biomarker language unless the corresponding evidence axis actually supports it.
- **Do not** hide a specificity or network-fragility failure behind a broad pass.
- **Do not** treat the sensitivity sweep as optional — an un-swept claim has no
  honest ceiling.
- **Do not** promote a calibrated claim to memory here without a verdict (that is a
  separate, gated step).

## Resources

- `references/axis-ceiling-table.md` — the axis list, how the binding (weakest) axis
  sets the ceiling, and the evidence-type → allowed-verb (forbidden-language) map.

## Example user requests

- "Calibrate this claim: term X is associated with region Y."
- "How strong is this contrast finding, honestly — across the strict bar too?"
- "Give me a bounded claim card with the real ceiling for this result."
- "Check whether this claim survives a specificity / network-axis test."
