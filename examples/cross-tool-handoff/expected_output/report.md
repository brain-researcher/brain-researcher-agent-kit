# Cross-Tool Handoff Demo Report

## Provenance

- run_id (scored): `br_20260524_062015_e4b0197511`
- run_id (report): `br_20260528_182911_a0164bbc60`
- scorecard profile_id: `external_coding_v1`
- mcp_server: `brain-researcher-mcp`

## Claims (each traces to an output_artifact_sha256 in handoff_chain.json)

- plan_preflight returned 12 candidate tools and 8 recommended next calls for the fMRI motion-correction query; KG hit `concept:7t_fmri`. sha256: `80b9cb226a4be7a1a826d3aea2ebe0082872e3daa5cf1801c69e58b1db36fa63`
- pipeline_plan_validate on the minimal `motion_quantification` plan returned `code_review.decision = approve`, risk `low`; sole remaining issue was `input_not_found` for the sample BOLD path. sha256: `40fbb6ac9d09e5172df8a6c275f87e2486892d14bf466b1aaabb7e488b28355a`
- run_scorecard on `br_20260524_062015_e4b0197511` with profile `external_coding_v1` returned status `succeeded`, reviewability `fully_evaluable`, artifact_completeness_ratio 1.0 (5/5 required files present), duration 621 s. sha256: `8f2d0eb3f283c0a25d75f1eb5959580418d2a83154094a202da961772f6c31a6`
- scientific_report_generate produced report_run_id `br_20260528_182911_a0164bbc60` with TeX + Markdown artifacts; bundled review returned correctness `pass`, judgment `unsound`, completeness `complete`, overall `diagnose`, action `revise_report`. sha256: `29f6f69e326357708079f58861ec9754ab3217d0067538e7f1806d003fda31de`

## Handoff edges

- step1 -> step2: candidate_tools list fed tool selection in validate
- step2 -> step3: normalized plan with approved code_review handed to (caller execution)
- step3 -> step4: executed_run_id consumed as run_scorecard.run_id
- step4 -> step5: same run_id + scorecard profile fed into scientific_report_generate
