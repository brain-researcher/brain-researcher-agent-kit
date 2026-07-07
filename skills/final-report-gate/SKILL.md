---
name: final-report-gate
description: Gate that blocks a polished final research report when its evidence basis is weak or unresolved. Use right before generating a research-facing report or writeup — so a report is emitted only over a gated evidence basis, and otherwise a degraded handoff is returned instead of a confident-looking document.
---

# Final Report Gate

## Overview

This skill is the last checkpoint before a **polished, research-facing report**
goes out. It wraps report generation with a hard precondition: the evidence basis
must pass the grounding gate first. If it does not, the skill **blocks the report**
and returns a degraded handoff (what is known, what is unresolved, what to do next)
rather than a document that looks authoritative but rests on weak evidence.

Use it whenever the next output is a final report / manuscript section / executive
writeup of a result. Do **not** use it for interim notes, exploratory summaries, or
answers explicitly labeled as work-in-progress — the gate is about *final,
polished* emission.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Assemble the evidence basis.** Collect the claims and their anchors the report
   would assert (results, runs, citations, KG facts). If a claim's evidence was
   never grounded, run the `evidence-grounding` skill first.
2. **Gate** with `grounding_gate_evidence_basis` over the full basis. Its verdict is
   the authority: is the basis strong enough to carry a *final* report?
3. **Branch on the verdict:**
   - **Basis strong →** generate the report with `scientific_report_generate` from
     the reviewed evidence. State what was tested, found, checked, and which
     findings are confirmatory vs. exploratory.
   - **Basis weak / unresolved →** DO NOT generate the polished report. Return a
     **degraded handoff**: the resolved subset, the unresolved anchors, and the
     specific step that would unblock a full report.
4. **Never launder weak evidence** by re-scoping the report to hide it. If you
   narrow the report, say what was dropped and why.
5. **Rendering only:** `latex_report_render` renders supplied structured sections;
   it does not review or gate. Do not treat a rendered PDF as an evidence check.

If BR is unreachable or the gate/report tools are missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode and default to the degraded handoff — never emit a full report you
could not gate.

## Anti-patterns

- **Do not** emit a polished final report when the evidence basis is weak or
  unresolved. Return a degraded handoff instead.
- **Do not** treat `scientific_report_generate` as its own evidence check — it
  formats reviewed evidence; the gate is a separate, required step.
- **Do not** treat `latex_report_render` as scientific review.
- **Do not** re-scope a report to bury an unresolved anchor without naming the cut.
- **Do not** skip the self-critique checkpoint for a weak/null result and jump
  straight to the report (run the `scientific-self-critique` skill first).

## Resources

- `references/degraded-handoff.md` — what a blocked-report degraded handoff must
  contain, and the wording template.

## Example user requests

- "Write up the final report for this analysis."
- "Turn these results into a manuscript section."
- "Generate the research report for the run."
- "Give me the polished summary I can send to my PI."
