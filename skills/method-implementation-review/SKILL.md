---
name: method-implementation-review
description: Run Brain Researcher's dedicated deterministic critics over a QSM or rapidtide implementation before trusting it, treating a critic finding as a blocker rather than a soft warning. Use when about to accept or rely on a QSM (susceptibility mapping) or rapidtide (lag-mapping) pipeline implementation or method contract.
---

# Method Implementation Review

## Overview

QSM and rapidtide have method-specific implementation hazards that a generic plan
review will miss (e.g. direct dipole inversion, incorrect local-field dataflow for
QSM; lag-mapping pitfalls for rapidtide). Brain Researcher ships dedicated
deterministic critics for exactly these. This skill runs the right critic before the
implementation is trusted, and holds the discipline that a BLOCK-family finding is a
**blocker**, not a soft warning.

Use it when about to accept or rely on a QSM or rapidtide implementation / method
contract. It is narrow by design — two methods. For general plan critique use
`plan-validation`.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Route to the method.** QSM → `qsm_implementation_review`; rapidtide →
   `rapidtide_implementation_review`. Pass the caller-supplied implementation
   config/code and method contract.
2. **Read the findings by family.** BLOCK-family findings are correctness hazards;
   WARN-family are advisories. Treat a BLOCK as a stop.
3. **Add companion checks** where a metric warrants: `companion_diagnostic_suggester`
   for metric-specific companion diagnostics. Its `observed_value` is **advisory** —
   it never gates.
4. **Gate acceptance.** Do not accept the implementation while a BLOCK finding
   stands. Report each finding, its family, and what would clear it.
5. **State what was checked.** Name the critic that ran and the method contract it
   checked; a review is not an execution of the pipeline.

If BR is unreachable or a critic is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not hand-wave a method-specific hazard as fine.

## Anti-patterns

- **Do not** treat a BLOCK-family critic finding as a soft warning — it is a blocker
  on acceptance.
- **Do not** let the companion suggester's `observed_value` gate a decision — it is
  advisory only.
- **Do not** run the wrong critic (QSM config through the rapidtide critic or vice
  versa).
- **Do not** substitute generic `pipeline_plan_review` for the method-specific critic
  on QSM/rapidtide — the specific hazards need the specific critic.
- **Do not** describe the review as having run the pipeline.

## Resources

None — a clean two-tool routing discipline. The BLOCK-vs-WARN gate is in the
Workflow and Anti-patterns.

## Example user requests

- "Review my QSM reconstruction implementation before I trust it."
- "Check this rapidtide lag-mapping config for method hazards."
- "Is there a dipole-inversion problem in this susceptibility pipeline?"
- "Run the dedicated critic on this method contract."
