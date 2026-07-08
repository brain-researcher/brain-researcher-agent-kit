---
name: plan-validate
description: Deterministically validate a proposed neuroimaging analysis plan for feasibility and internal consistency using an offline, stdlib-only rule engine (no live knowledge graph) — checks tool ordering, parameter ranges (TR, FWHM, high-pass, group N, DWI b-value/directions), modality/space compatibility, and design/method appropriateness, then rolls the findings up into an approve / approve-with-warnings / block verdict. Use before executing or committing a plan to catch mis-ordered steps, unit errors, and design-method mismatches; use when a reviewer wants an auditable, re-runnable checklist of what plan review actually did; and prefer this over the knowledge-graph-backed reviewer whenever the plan can be judged from its own structure and parameters.
---

# Plan Validate

## Overview

This skill ports the Brain Researcher `pipeline_plan_validate` MCP tool in its
**rule-engine mode** (`use_kg=False`) into a self-contained, offline validator.
Given an analysis plan (a list of tool steps with parameters), it deterministically
reports the violations and warnings a plan-time reviewer would raise, plus an
independent checklist and a rolled-up verdict.

It is the *interpretation* half of plan review — the part that reads from the
plan's own structure and a curated rule set, with no server, no Neo4j, no
registry, and no network. Because the rules live in versioned JSON
(`references/`) and the logic is a small deterministic script, a reviewer can
read the exact rubric and re-run it bit-for-bit. This is exactly the
"reproducibility / show-what-review-did" property that motivated carving it out
of the MCP (`mcp_to_skills_carve_assessment.md`: `pipeline_plan_validate` is a
`skill_candidate`, movable because its core is a rule engine).

What it checks (all ported verbatim from BR — see `references/rules.md`):

- **Step ordering** — registration before atlas/parcellation, skull-strip before
  registration, confound regression before GLM.
- **Parameter ranges** — TR, smoothing FWHM, GLM high-pass and events/condition,
  group N (parametric and second-level), DWI b-value and gradient directions.
- **Modality/space compatibility** — EEG/MEG with a volumetric MNI atlas, DWI
  tools on BOLD data, mixed MNI template versions.
- **Design ↔ method appropriateness** — e.g. an independent-samples t-test on a
  repeated-measures design (from the curated compatibility seed).

### When to use the offline validator vs. the KG-backed one

| Use **this skill** (offline) | Call the **MCP tool** instead |
| --- | --- |
| Judge a plan from its own structure + parameters | Ground a parameter against literature priors (GLMDesignPrior high-pass, task-conditioned ranges) — needs the live graph |
| Want an auditable, re-runnable rubric a reviewer can inspect | Confirm each tool exists / is allowed (registry preflight) |
| No server / offline / CI / pre-commit | Resolve + sandbox the run workspace, or produce a run bundle |
| Advisory feasibility & consistency check | You need the *certified* server verdict of record |

The KG-backed path stays an MCP call — it is `pipeline_plan_validate` (the tool
sets `use_kg=False` internally but still does registry preflight + workspace
resolution) and `pipeline_plan_review(plan, use_kg=True)` (adds KG parameter
grounding). Those two MCP calls are the server-backed handoff. This skill does
**not** certify that a plan is runnable — only that it is internally consistent
and scientifically well-formed.

## Workflow

### Step 1 — Assemble the plan dict

Collect the proposed pipeline into the plan schema (`references/plan_input_schema.md`):
a non-empty `steps` list, each step `{tool, params, step_id?}`. Put parameters
under the keys the rules read (e.g. `tr`, `fwhm`, `high_pass`, `n_subjects`,
`b_value`, `modality`, `target_space`, `design_type`, `statistical_method`) —
that table lists exactly where each rule looks. Write it to a JSON file.

### Step 2 — Run the validator

```bash
python scripts/validate_plan.py <plan.json>
# or pipe it in:
cat plan.json | python scripts/validate_plan.py -
# add --compact for one-line JSON
```

The script loads the rules from `references/plan_review_rules.json` and the
design/method seed from `references/method_compatibility_seed.json`, evaluates
every plan-mode rule, and prints a JSON verdict. Exit code is `0` when `ok`
(approve / approve-with-warnings) and `1` when blocked or a schema error was
raised.

### Step 3 — Read the verdict

The output mirrors the `code_review` verdict of the MCP tool:

- `ok` — `true` unless there is an error/critical finding, a block action, or a
  schema failure.
- `decision` / `risk_level` — the roll-up (`approve` / `approve_with_warnings` /
  `revise` / `block` × `low` / `medium` / `high` / `critical`). See the roll-up
  table in `references/rules.md`.
- `findings` — each with `rule_id`, `severity`, `action`, `message`,
  `suggested_fix`, and the `step_id` it anchors to (method-appropriateness
  findings also carry `detected_design` / `detected_method` / `kg_evidence`).
- `checklist_generated` — the independent structural checklist (generated before
  rule evaluation, so it does not depend on which rules fired).
- `schema_error` — non-null only when the plan was rejected at coercion.

### Step 4 — Act on findings

- **`block` / error findings** (e.g. `REVIEW_REGISTRATION_ORDER`,
  `REVIEW_FWHM_LOW`, `REVIEW_METHOD_APPROPRIATENESS`) are hard consistency /
  feasibility problems — fix the plan (apply the `suggested_fix`) and re-run
  before proceeding.
- **`warn` findings** are advisory (unit-sanity, power, aggressive filtering) —
  confirm they are intentional; the plan is still `ok`.
- Report each finding with its `rule_id` so the judgment is traceable to the
  auditable rule in `references/`. Do **not** invent additional rules or soften
  a block into a warning — the rule set is the contract.

### Step 5 — Escalate to the server only when needed

If a finding depends on a literature prior, a registry check, or a certified
verdict of record, hand off to the MCP: call
`pipeline_plan_review` with `use_kg=true` for KG-grounded parameter review, or
`pipeline_plan_validate` for the full server-side normalize + registry preflight
+ workspace resolution. State explicitly that the offline pass is advisory and
the server pass is authoritative.

## Resources

### references/

- `plan_review_rules.json` — machine-readable rule set the script loads
  (metric rules, structural rules, tool sets, roll-up spec). The auditable core.
- `method_compatibility_seed.json` — curated design↔method compatibility seed
  (aliases + rules) for `REVIEW_METHOD_APPROPRIATENESS`.
- `rules.md` — human-readable catalog of every rule, the roll-up semantics, the
  provenance mapping back to BR source files, and the offline-vs-KG boundary.
- `plan_input_schema.md` — the accepted plan dict shape and which param keys
  each rule reads.

### scripts/

- `validate_plan.py` — deterministic, stdlib-only validator. Loads the rule
  references, coerces + validates the plan, evaluates all plan-mode rules, and
  prints the JSON verdict. Runnable as `python scripts/validate_plan.py <input.json>`.

### examples/

- `plan_clean.json` — a well-formed plan (verdict: approve).
- `plan_bad_ordering.json` — atlas-before-registration, mixed MNI, unit errors
  (verdict: block).
- `plan_method_mismatch.json` — repeated-measures design with an independent
  t-test (verdict: block).
