---
name: research-trajectory-synthesis
description: Synthesize a durable research trajectory and insights across a set of Brain Researcher runs — what was tried, what held, where the line is going — grounded in the run bundles, not in a narrative gloss. Use when a user wants a cross-run "where has this research gone and what did we learn" summary rather than a single-run review.
---

# Research Trajectory Synthesis

## Overview

Over a series of runs, the useful artifact is a *trajectory*: what was tried, what
held up, what got abandoned, and where the line is heading. This skill wraps BR's
trajectory/insight generator with the discipline that the narrative stays **grounded
in the run bundles** — every "we learned X" traces to a run's evidence, and an
unverified insight is labeled as such, not folded into the story as fact.

Use it when the user wants a cross-run "where has this gone / what did we learn"
synthesis. Do **not** use it for a single-run review (`scientific-self-critique`),
session-lesson→memory promotion (`session-lessons-to-memory-promotion`), or a final
report over one result (`final-report-gate`).

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Scope the runs.** Identify the runs in the trajectory (the user's own runs). Use
   `run_bundle_get` per run to read the grounded evidence each contributes.
2. **Synthesize.** `generate_research_trajectory_and_insights` over the run evidence
   to produce the durable trajectory + insights.
3. **Ground each insight.** Every claimed insight must trace to a run's bundle
   (result, verdict, or failure). An insight without a backing run is a hypothesis —
   label it, do not assert it.
4. **Separate confirmed from open.** Confirmed directions (verdict-backed) vs. open
   threads (tried, inconclusive) vs. abandoned (refuted) — keep the three distinct.
5. **Report the arc** — what was tried, what held, what's next — with the runs each
   claim rests on. Do not promote any insight to memory/KG here (that is a separate,
   verdict-gated step).

**Privacy:** operate over the *specified* runs via `run_bundle_get`. Do **not** reach
for whole-store-scan tools (`research_log_summary`, `session_learning_report_generate`,
`session_signal_report_generate`) — they scan every user's runs (a cross-user
surface).

If BR is unreachable or the generator is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not narrate a trajectory you could not ground in bundles.

## Anti-patterns

- **Do not** state an insight that no run bundle supports — trace each to its run.
- **Do not** blur confirmed / open / abandoned directions into one confident arc.
- **Do not** use whole-store-scan tools (privacy: they cross user boundaries); stay on
  per-run `run_bundle_get`.
- **Do not** promote a trajectory insight to accepted memory/KG without a verdict.
- **Do not** paste raw bundle JSON; summarize the arc with its grounding runs.

## Resources

None — a clean per-run synthesis discipline. The grounding rule and the privacy
exclusion are in the Workflow and Anti-patterns.

## Example user requests

- "Summarize where this line of research has gone across my last several runs."
- "What have we learned overall — what held up and what didn't?"
- "Give me the research trajectory + insights for this project's runs."
- "Which directions are confirmed vs still open across these runs?"
