# `partial_action`: reject vs downgrade

The decision `evidence-grounding` exists to make. After `grounding_resolve` +
`grounding_gate_evidence_basis`, some anchors are strong and some are weak. What
you do next depends on **which** anchor is weak, not on how many.

## Reject

Set `partial_action="reject"` — the claim does not go out — when:

- The **central** anchor of the claim is unresolved. (Without it the claim has no
  basis at all.)
- The claim would be **false or misleading** in its stated form without the weak
  anchor.
- The claim asserts a **causal / mechanistic** relationship and the causal link is
  the unresolved anchor.
- A number, effect direction, or dataset identity that the claim *states* is the
  thing that failed to resolve.

Reject is not failure — it is returning "the evidence does not support stating
this yet," plus what would need to resolve.

## Downgrade

Set `partial_action="downgrade"` — state a weaker, honestly-scoped claim — when:

- Only **peripheral / corroborating** anchors are missing; a narrower version of
  the claim still stands on the resolved anchors.
- The claim can be **re-scoped** to what *is* grounded (e.g. "reported in
  ds000114" instead of "generally established").
- The unresolved anchor adds *breadth or confidence*, not the core truth value.

A downgraded claim must name what was dropped: "supported for X (verified);
not established for Y (anchor unresolved)."

## Worked examples

| Claim | Weak anchor | Action |
|---|---|---|
| "Finger>Foot activates motor cortex, established across datasets" | the cross-dataset anchor unresolved; ds000114 resolves | **downgrade** → "shown in ds000114; broader generalization unverified" |
| "Region 904 is the causal driver of the effect" | causal-link anchor unresolved | **reject** — causal claim, causal anchor missing |
| "DLPFC supports WM maintenance (Smith 2020, Jones 2019)" | Jones 2019 unresolved, Smith 2020 resolves | **downgrade** → keep the claim, drop the unverifiable citation |
| "Dataset ds00XXXX has n=200 subjects" | the dataset id itself does not resolve | **reject** — the stated fact is the unresolved anchor |

## Default under uncertainty

When it is unclear whether an anchor is central or peripheral, treat it as central
and **reject**. Conservative grounding is the point of the skill.
