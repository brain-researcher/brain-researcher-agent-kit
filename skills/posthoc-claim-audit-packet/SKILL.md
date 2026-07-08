---
name: posthoc-claim-audit-packet
description: Build an honest audit packet for an analysis that ALREADY ran without a sealed pre-registration — searching Brain Researcher for any pre-run commitment card, then emitting a claim card, a post-hoc registration, and evidence verdicts that never misrepresent the analysis as pre-registered. Use when asked "is this pre-registered / give me a claim card" for an already-run analysis.
---

# Post-hoc Claim Audit Packet

## Overview

Sometimes an analysis has already been run with no sealed commitment, and the user
still needs an audit record. This skill produces an **honest** packet: it searches
BR's surfaces for a genuine pre-run commitment card, tests provenance, and emits a
claim card that records `commitment_card_ref: null` and a `post_hoc` status when no
card exists. The cardinal rule — shared with `sealed-commitment-preregistration` —
is that a sealed commitment card is **never backfilled**, and a post-hoc packet is
never dressed up as pre-registered.

Use it when asked "is this analysis pre-registered?" / "give me a claim card / audit
record" for an analysis that already ran. Do **not** use it to seal a *new*
confirmatory analysis (that is `sealed-commitment-preregistration`).

Authored against Brain Researcher MCP `contract_version >= 2026-07-08`.

## Workflow

1. **Search for a real pre-run card.** `run_list` / `run_get` / `run_bundle_get` /
   `artifact_list` / `run_logs` over the run's surfaces to check whether a sealed
   commitment card was recorded *before* execution.
2. **Test provenance.** `report_claim_provenance_check` to check whether the claim's
   provenance matches a committed design.
3. **Decide the honest status:**
   - **Card found + provenance matches →** the claim can cite the real
     `commitment_hash`; it was pre-registered.
   - **No card found →** record `pre_run_commitment_card_found: false`, set the claim
     card's `commitment_card_ref: null`, and register `post_hoc` status explicitly.
4. **Emit the packet** (see `references/audit-packet-templates.md`): `claim_card.json`,
   `posthoc_registration.json`, `evidence_verdicts.json`. Keep the may-say /
   must-not-say language boundary.
5. **State the integrity call** plainly to the user: pre-registered vs. post-hoc,
   and what that permits the claim to say.

If BR is unreachable, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not fabricate a commitment card or a "found" result.

## Anti-patterns

- **Do not** backfill or synthesize a sealed commitment card, ever. A post-hoc
  packet with a real `commitment_card_ref: null` is honest; a fabricated hash is not.
- **Do not** represent a post-hoc packet as pre-registered / confirmatory.
- **Do not** claim `pre_run_commitment_card_found: true` without actually finding the
  card on a searched surface.
- **Do not** use forbidden language (causal / mechanistic / externally-validated /
  biomarker) that the evidence tier does not license.
- **Do not** omit the post-hoc status to make the record look stronger.

## Resources

- `references/audit-packet-templates.md` — the three JSON schemas (`claim_card`,
  `posthoc_registration`, `evidence_verdicts`) and the may-say / must-not-say
  wording table.

## Example user requests

- "Was this NeuroMark analysis pre-registered? Give me the audit record."
- "Produce a claim card for this run I already finished."
- "Build a post-hoc registration for this analysis."
- "Check the provenance of this claim against any commitment."
