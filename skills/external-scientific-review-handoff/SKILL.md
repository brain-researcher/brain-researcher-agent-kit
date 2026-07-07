---
name: external-scientific-review-handoff
description: Run a scientific review when Brain Researcher can supply the review criteria but cannot see the artifacts itself — BR issues a review directive/schema, an external agent actually inspects the evidence, and only an inspection-backed verdict is submitted back. Use when the artifacts to review live outside BR's reach (a private repo, a local workspace, an external system).
---

# External Scientific Review Handoff

## Overview

Some artifacts cannot be read by the Brain Researcher server — a private repo, a
local workspace, an external system. In that case BR provides the *review criteria
and schema*, an external agent does the actual inspection, and a schema-valid verdict
is submitted back. This skill's cardinal rule: **a verdict is submitted only after
the external agent has genuinely inspected the evidence** — never a plausible-looking
verdict produced without looking.

Use it when the review target is outside BR's reach. Do **not** use it when BR can
read the run itself (that is `run_scientific_review` via the `scientific-self-critique`
skill).

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Request the directive.** `request_external_scientific_review_directive` — BR
   returns the review criteria + the verdict schema BR expects. This is the contract
   the external review must satisfy.
2. **Inspect the actual evidence.** The external agent reads the real artifacts
   (code, outputs, data) against the directive's criteria. This step is not
   skippable — the verdict must rest on what was actually seen.
3. **Assemble a schema-valid verdict** — every criterion in the directive addressed,
   with the evidence that supports each judgment, in the schema BR asked for.
4. **Submit** with `submit_external_scientific_review_verdict` **only after** step 2
   actually happened. A verdict with unaddressed criteria or no inspected evidence is
   not submittable.
5. **Report** what was reviewed, against which criteria, and the verdict — noting it
   is an *external* review (BR did not see the artifacts directly).

If BR is unreachable or the handoff tools are missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not submit a verdict you cannot back with inspection.

## Anti-patterns

- **Do not** submit a verdict before the external agent actually inspected the
  evidence — a verdict without inspection is fabrication.
- **Do not** submit a verdict that leaves the directive's criteria unaddressed or
  breaks its schema.
- **Do not** use this path when BR *can* read the run — use the in-BR review instead.
- **Do not** relabel an external review as if BR certified the artifacts; BR issued
  criteria, the external agent inspected.
- **Do not** paste the raw directive/verdict JSON into the answer; summarize the
  criteria covered and the outcome.

## Resources

None — a clean directive → inspect → verdict discipline. The inspection-before-submit
rule is in the Workflow and Anti-patterns.

## Example user requests

- "Review this analysis that lives in my private repo BR can't see."
- "Give me the review criteria, I'll run the check on my machine and report back."
- "Submit the external review verdict for the artifacts I just inspected."
- "Set up an external scientific review handoff for this off-platform run."
