# Axis ceiling + forbidden-language map

`neuroclaim_compile` reports a claim across several axes. The honest reported
strength = the **weakest binding axis** (the ceiling), and the claim's *verb* is
bounded by the *type* of evidence, not by the most lenient axis that passed.

## The ceiling rule

Take the per-axis statuses (e.g. `supported_within_scope` / `weakened` /
`unresolved` / `refuted`). The claim card's headline status is the **weakest** axis
that is *binding* for the claim:

| Axis (example) | What it tests |
|---|---|
| structure | is the claim structurally complete / well-typed |
| association | does the association hold at the lenient bar |
| strict-bar | does it survive the strict evidence profile |
| specificity | is it specific to the named region/term (not everywhere) |
| network | is it robust across the network axis (not one fragile pair) |

Report: "supported on <axes>; **weakened/unresolved on <the binding axis>** → overall
ceiling = <weakest>." Never headline the lenient pass while a stricter axis fails.

## Forbidden-language map (evidence type → allowed verb)

| Evidence you have | May say | Must NOT say |
|---|---|---|
| association / coordinate | "is associated with", "co-activates with" | "causes", "drives", "is necessary for", "mechanism" |
| within-dataset only | "in <dataset>, …" | "externally validated", "generalizes" |
| group-level | "at the group level" | "predicts for an individual", "clinically predictive" |
| no clinical outcome tie | — | "biomarker", "diagnostic" |

A result "cannot be reported as causal, mechanistic, externally validated,
clinically predictive, or a biomarker unless the corresponding evidence exists."
The calibration's job is to make that boundary explicit in the claim card.

## Worked (from the cases)

- Working-memory demo: broad association passes but the strict-evidence profile
  weakens it → status `weakened`, ceiling = strict-bar axis.
- Response-inhibition boundary demo: network axis `unresolved` → the claim is capped
  at `unresolved` on the network axis regardless of the association pass.
