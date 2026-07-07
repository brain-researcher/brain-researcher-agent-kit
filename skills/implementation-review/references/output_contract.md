# Output contract

`scripts/implementation_review.py` prints one JSON object. On success it is the
Brain Researcher `CodeReviewVerdict` (identical to what the MCP tools
`qsm_implementation_review` / `rapidtide_implementation_review` return via
`model_dump()`), wrapped with an `ok` flag.

## Envelope

```json
{ "ok": true,  "...": "verdict fields below" }
{ "ok": false, "error": "code_required" }
```

`ok:false` errors (parity with the MCP tools): `code_required`,
`task_profile_required`, `method_contract_must_be_object`, `unknown_method`,
`input_must_be_object`. Process exit code is `0` whenever a JSON verdict is
produced (including a `block` decision); it is non-zero only for malformed CLI
usage or unreadable/invalid input files.

## CodeReviewVerdict fields

| field | type | meaning |
| --- | --- | --- |
| `decision` | `approve` \| `approve_with_warnings` \| `revise` \| `block` | roll-up over findings |
| `risk_level` | `low` \| `medium` \| `high` \| `critical` | roll-up over findings |
| `findings` | list of ReviewFinding | one entry per triggered rule |
| `kg_rules_consulted` | list | always `[]` here (no KG in these deterministic rubrics) |
| `checklist_generated` | list of str | the audit checklist attached to every run |
| `reviewer_rationale` | str | one-line human summary of the decision + findings |

QSM verdicts also carry a `domain_invariant_review` block
(`task_type`, `advice_mode: audit_only`, `hard_constraints`,
`non_displacement_notice`, `qc_protocol`, `forbidden_guidance`).

## ReviewFinding fields

| field | type | meaning |
| --- | --- | --- |
| `rule_id` | str | stable rule identifier (see the per-method YAML) |
| `severity` | `warn` \| `error` \| `critical` | drives the roll-up |
| `action` | `block` \| `warn` | `block` forces a `block` decision |
| `message` | str | what was detected |
| `suggested_fix` | str | how to make it canonical |
| `step_id` | str \| null | unused here (always null) |
| `artifact_name` | str \| null | subject id for observed rapidtide railing findings |
| `kg_evidence` | list | always `[]` |
| `reason_tags` | list | `["qsm_reconstruction","domain_invariant","anti_pitfall"]` or `["rapidtide","slfo_lag","method_appropriateness"]` |
| `novelty` | str \| null | unused here (always null) |

## Decision meaning

- `block` — a hard, invalidating error (critical severity or any `block`
  action). Do not accept the pipeline until it is fixed.
- `revise` — an `error`-severity finding; correct before trusting the result.
- `approve_with_warnings` — only `warn`-severity findings; note them.
- `approve` — no findings.

These rubrics are **non-displacive**: a clean `approve` is *not* an
endorsement of the whole pipeline, only confirmation that none of the specific
known-bad patterns fired. Never use them to author or replace a reconstruction
recipe.
