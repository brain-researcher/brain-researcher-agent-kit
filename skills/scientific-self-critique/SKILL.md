---
name: scientific-self-critique
description: Applies the Brain Researcher self-critique checkpoint when an initial analysis returns a weak, null, or surprising result and someone wants to report it — first diagnosing whether the null is a methodological artifact (granularity, confounders, labels, filters, outcome definition) and requiring at least one labeled exploratory follow-up before any final conclusion, wrapping run_scientific_review / request_scientific_review with a manual-critique fallback.
---

# Scientific Self-Critique

## Overview

Use this skill the moment an initial research result is weak, non-significant,
or surprising and there is any pressure to write it up. The discipline is a
gate: a first-pass null is a *question*, not a finding. Before it becomes a
final scientific claim you must (a) diagnose whether the null is caused by
methodological choices, and (b) run at least one reasonable, clearly-labeled
exploratory follow-up. This mirrors the "Self-critique checkpoint" in
`agents/AGENTS.brain-researcher.md` and enforces its hard rule.

This is a **wrapper** skill: it wraps the Brain Researcher scientific-review
tools with the checkpoint discipline. It adds no analysis logic of its own.

**When NOT to use.** Skip it for a strong, expected, already-reviewed result
headed straight to the final-report gate; for pure read-only lookups with no
result to critique; and for pre-execution plan critique (that is
`plan-validation` / `pipeline_plan_review`, not this). Do not use it to
manufacture a positive story from noise — the follow-up is a documented
exploration, not a hunt for a headline.

Authored against BR stable-tier surface, `contract_version >= 2026-05-27`.

## Workflow

Each step names a BR tool, a check, or a decision. Inspect the live MCP surface
first; only call tools the current client actually exposes.

1. **Preflight + start logging.** Call `server_info`; confirm
   `contract_version >= 2026-05-27` and that the `scientific_review` capability
   is `true`. Open the task with
   `log_research_event(kind="start", source="agent", source_client=...)` using
   one stable `session_id`. If `server_info` fails or the review capability is
   off, follow the fallback path below.
2. **Locate the result.** Use `run_find_latest_reviewable` (or `run_list` ->
   `run_get`) to identify the persisted run, then pull its evidence with
   `run_bundle_get` and `run_scorecard`. Confirm you are critiquing the *right*
   run — a stale or empty run yields a hollow pass.
3. **Interest check ("so what?").** If a reviewer's first reaction would be "so
   what?" rather than "interesting," the analysis is not finished. Refine the
   framing, comparison, or follow-up before proceeding.
4. **Null-result diagnosis (BLOCKING).** Before treating a weak/non-significant
   main effect as a final null, check every item: analysis **granularity**,
   uncontrolled **confounders**, weak or placeholder **labels**, insufficient
   **filters/QC**, and an overly broad **outcome definition**. Use
   `companion_diagnostic_suggester` for metric-specific companion checks. See
   `references/null_result_triage.md` for the check-to-action table.
5. **Run the review pass — assert it fired.** For a persisted run call
   `run_scientific_review`; for an autoresearch workspace call
   `run_autoresearch_scientific_review`; when the correct path is ambiguous or
   the artifacts are external, `request_scientific_review` dispatches to a run,
   autoresearch directory, or an external-review directive. Optionally add
   `run_code_review` for artifact/domain hazards. Verify the review actually ran
   over real evidence — do not accept a happy-path "review complete" line on an
   empty run.
6. **At least one exploratory follow-up (REQUIRED).** Run one reasonable post-hoc
   exploration: does the weak overall effect hide signal in a subgroup,
   condition, feature family, brain network, network pair, task contrast,
   dataset split, or QC-passed subset? Use `run_compare` for split/subgroup
   deltas. **Label every such finding exploratory.**
7. **Decide and summarize honestly.** Using `references/null_result_triage.md`,
   choose: report a genuine final null, downgrade the claim to exploratory, or
   re-run at a corrected granularity/definition. `refuted_landscape_summary` can
   roll structured findings into supported / refuted / inconclusive. Only after
   this checkpoint hand off to the report gate (`final-report-gate` /
   `scientific_report_generate`).
8. **Snapshot.** Close with exactly one
   `write_session_snapshot(...)` capturing what was tested, the null diagnosis,
   the exploratory follow-up and its label, and which findings are confirmatory
   vs exploratory. Do not paste raw MCP JSON into the user-facing answer.

## Fallback

If the review capability is unreachable, version-mismatched, or the review tools
are not in `server_info.stable_tools`, follow `adapters/br-fallback-policy.md`.
The manual-critique fallback: walk the five null-result checks in step 4 by hand,
document one exploratory follow-up from step 6, and announce the degraded mode
(`degraded: scientific-self-critique -> manual critique (BR run_scientific_review
unavailable)`). Never imply a BR review ran when it did not, and still do not
report the null as final without the checks and one labeled follow-up.

## Anti-patterns

- **Reporting a weak/null result as final** before all five checks —
  granularity, confounders, labels, filters, outcome definition — have been run.
- **Skipping the exploratory follow-up**, or concluding after zero post-hoc
  exploration. At least one is required.
- **Mislabeling an exploratory follow-up as confirmatory**, or quietly promoting
  a subgroup hit to the headline effect. Exploratory findings stay labeled
  exploratory.
- **P-hacking the follow-up** — cycling subgroups until something is
  significant, then reporting only that. The follow-up is one documented,
  pre-stated exploration, not a fishing expedition.
- **Trusting a hollow review** — treating "review returned" as "review
  happened." Assert the review ran over the actual run's evidence.
- **Inventing client-specific MCP tool names** or calling review tools from
  memory. Confirm names from `server_info` / `tool_search`.
- **Skipping the checkpoint** because the result "looks clean" or because no
  reviewer explicitly asked — the gate is unconditional for weak/null/surprising
  results.
- **Pasting raw MCP JSON** into the final answer; summarize the run_id, the
  diagnosis, and the confirmatory-vs-exploratory split instead.

## Resources

### references/

- `null_result_triage.md` — the decision table mapping each null-cause check
  (granularity / confounders / labels / filters / outcome definition) to its
  diagnostic move and the resulting action (report final null vs downgrade to
  exploratory vs re-run), plus example exploratory follow-ups per axis.

## Example user requests

- "The group difference didn't reach significance — write it up as a null."
- "My connectivity effect is weak, is this result ready to report?"
- "Fingerprinting accuracy came out at chance; draft the conclusion."
- "This result is surprising / the opposite of what we expected — finalize it?"
- "Self-critique this run before I put it in the report."
- "Is this null real, or did I mess up the analysis?"
