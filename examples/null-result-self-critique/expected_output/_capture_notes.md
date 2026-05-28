# Capture notes — null-result-self-critique

Captured live against `brain-researcher-local` MCP server on 2026-05-28.

## Tool calls

### 1. `run_scientific_review`
Called with `run_id="demo_null_result_self_critique_initial_findings"` (a synthetic id — this demo
does not have a real persisted BR run; the input is a hand-written `initial_findings.json`).

Response (verbatim):

```json
{"ok": false, "error": "run not found: demo_null_result_self_critique_initial_findings"}
```

**Interpretation**: `run_scientific_review` is bound to persisted run artifacts in `RUN_ROOT`
and cannot be invoked on an inline JSON finding. The kit's self-critique step is therefore
performed in the report using the deterministic checklist documented in the tool's docstring
(correctness + completeness: design rank, cross-file consistency, contrast dimensions,
seed pinned, atlas versioned, ordering declared). The critique below is grounded in the
absence of those provenance fields from `initial_findings.json`; no LLM-judge verdict was
fabricated.

### 2. `pipeline_plan_validate` — exploratory subgroup plan, v1
First attempt used pseudo-tools (`behavior_filter`, `pearson_correlation`, `report_tagger`)
and missing required params for `seed_based_fc`. Response (verbatim, abbreviated):

```json
{"ok": false,
 "issues": [
   {"level":"error","code":"unknown_tool","message":"Unknown tool: behavior_filter"},
   {"level":"error","code":"params_missing_required","message":"Missing required params for seed_based_fc: ['img']","step_id":"seed_connectivity"},
   {"level":"error","code":"unknown_tool","message":"Unknown tool: pearson_correlation"},
   {"level":"error","code":"unknown_tool","message":"Unknown tool: report_tagger"}
 ],
 "code_review": {"decision":"approve","risk_level":"low"}}
```

### 3. `pipeline_plan_validate` — exploratory subgroup plan, v2 (final)
Reduced to a single `seed_based_fc` step with the required `img` param. Response: `ok=true`,
issues empty, code_review decision `approve`. Full response saved as `validate.json`.

No tool returned `degraded`. The kit's null-result discipline is preserved: the exploratory
follow-up is labeled exploratory in `report.md` and is NOT promoted to a confirmatory claim.
