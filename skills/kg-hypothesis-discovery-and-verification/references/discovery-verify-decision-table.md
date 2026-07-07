# Discovery + verify: operation & status decision table

The discipline: sampling produces *questions*; only verification produces
*answers*. This table maps the knobs to the right call and the honest status word.

## Which call

| You have | Call | Notes |
|---|---|---|
| a topic, want candidates | `kg_hypothesis_workflow(operation="sample")` or `kg_hypothesis_candidate_cards` | sync; returns candidate cards |
| candidates, want them screened | `kg_verify_hypothesis` per candidate | the acceptance step |
| topic → candidates → screened, one shot | `kg_hypothesis_workflow(operation="sample_and_verify")` | still report per-candidate verdicts |
| a large / slow sample run | `kg_hypothesis_candidate_cards_start` → `..._get` | async; poll the get |
| want literature folded in | `kg_verify_hypothesis(use_external_literature=True)` | adds a literature lane to KG evidence |

## Strictness / lane knobs

- `strictness` (e.g. `high_recall`) and `candidate_lane_mode` (`broad` / `strict`)
  widen or tighten candidate recall. A `broad` lane surfaces more *questions*; it
  does **not** lower the bar for acceptance.
- Higher recall ⇒ more candidates to screen, not more findings.

## Status wording (from the verify verdict)

| Verify returns | Report it as | Never say |
|---|---|---|
| supporting evidence at required tier, low conflict | **supported** (state the tier) | — |
| supporting + non-trivial conflicting | **mixed / contested** (show both) | "supported" unqualified |
| insufficient / degraded_timeout | **insufficient evidence** (open question) | "refuted" or "supported" |
| conflicting dominates | **not supported / refuted** | "supported" |

Always: name the confidence tier, show conflicting evidence, and keep the retrieval
rank separate from the acceptance decision.
