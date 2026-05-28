# AGENTS · brain-researcher

Drop this template into your agent's `AGENTS.md` (or the equivalent system-prompt file) when the agent will talk to a Brain Researcher MCP server. It assumes the server exposes the stable-tier surface declared in `contracts/tools/*.json` (contract_version ≥ 2026-05-27).

## Health check

When the user asks whether Brain Researcher MCP is working / healthy / reachable, call `server_info` and `system_self_test` and report the two results in one short paragraph. Do not paste the raw JSON unless the user asks for it. Healthy response is `server_info: ok=true` and `system_self_test: overall=pass`. See `MCP_SETUP.md` at the repo root for the full terminal-side setup and live-check flow.

## Required Brain Researcher check

- For neuroimaging or research-related tasks, first check whether `brain_researcher_mcp` is active and which tools it exposes.
- If `brain_researcher_mcp` is active, use its available tools when they are relevant for prior context, memory lookup, research synthesis, analysis planning, plan validation, scientific self-critique, or final reporting.
- Inspect the actual exposed tool names before invoking them. Do not invent SDK-style function names unless the current MCP client actually exposes them.
- If the MCP server is inactive or unavailable, state that `brain_researcher_mcp` is unavailable and continue with the closest reasonable fallback.

## Brain Researcher MCP functions

Treat this as an inventory of Brain Researcher MCP functions to look for. The active client may expose only a subset, so inspect the current MCP tool list first and then choose from the functions that are actually available.

- **Status, health, and inventory**: use `server_info` to inspect server configuration, contract version, toolset hash, capabilities, and deprecated tools. Use `system_self_test` for health/dependency probes and `loop_profile_get` for machine-readable loop policies. Read these before claiming that the MCP server can execute, validate, or access a resource.
- **Tool and workflow discovery**: use `tool_search` for capability search, `workflow_search` for workflow-level routes, `tool_search_structured` for method/software/version-style lookup, `tool_resolve` to map a method/software/op key to a concrete tool, and `tool_get` to inspect a known tool and its schema. Use `get_execution_recipe` when the next step should be a runnable local, container, or cluster recipe.
- **Planning and handoff surfaces**: use `plan_preflight` to check dataset facts, missing inputs, blockers, and candidate tools before committing to a plan. Use `plan_create` to create a read-only plan contract with display and execution envelopes. Use `get_latest_plan` only to recover an existing validated handoff block.
- **Plan validation and pre-execution critique**: use `pipeline_plan_validate` for schema normalization, path/policy checks, and validation issues. Use `pipeline_plan_review` for domain critique of ordering, parameter ranges, modality/space compatibility, and plan completeness. Use `qsm_implementation_review` for QSM-specific code hazards such as direct inversion or incorrect local-field dataflow.
- **Manual / admin execution surfaces**: `tool_execute`, `pipeline_execute`, and `run_cancel` are not the default agent path. Prefer `get_execution_recipe` plus explicit local execution unless the user specifically asks for MCP execution, cancellation, or admin control. Never describe `plan_preflight`, `plan_create`, `pipeline_plan_validate`, or `get_execution_recipe` as having executed an analysis.
- **Research memory**: use `memory_search` for prior context, saved decisions, hypotheses, datasets, papers, or earlier results. Use `memory_get` after a specific memory card is identified. Use `memory_write` only when the user explicitly asks to persist a derived memory card or relation.
- **Research logging and session summaries**: use `log_research_event` for the start of real work and rare rationale notes, `write_session_snapshot` before final handoff, `research_session_digest` for one session, and `research_log_summary` for cross-session summaries.
- **Session learning tools** (when exposed): use `session_risk_classify` and `session_lesson_extract` to inspect one session, `session_open_risks_query` to find repeated blockers, `session_policy_cards_generate` to propose durable agent-policy candidates, and `session_learning_report_generate` for periodic reports.
- **Session KG backfill**: `session_backfill_to_kg` is dry-run by default. Use `dry_run=false` only when Neo4j env vars are configured and the user explicitly wants KG writes; otherwise treat its returned rows and query examples as a preview.
- **Run inspection**: use `run_list` to discover runs, `run_get` for status and step records, `run_bundle_get` for normalized observation bundles, `run_scorecard` for scorecards, `run_compare` for run-to-run comparisons, `run_metrics` for timing/cost/status metrics, `run_logs` for log payloads, `run_find_latest_reviewable` to locate review/report candidates, and `run_request_summary` for historical request-type summaries.
- **Artifact inspection**: use `artifact_list` to enumerate run artifacts, `artifact_read_text` for text artifacts, `artifact_get_metadata` for size/time/checksum metadata, and `artifact_read_bytes` for small binary artifacts. Do not assume the deployed MCP server can read arbitrary local workspace paths.
- **Code and scientific review**: use `run_code_review` for post-execution artifact/domain review. Use `run_scientific_review` for correctness, completeness, and judgment review of a persisted run. Use `run_autoresearch_scientific_review` for autoresearch workspaces. Use `request_scientific_review` when the right review path may be a run, autoresearch directory, or external-review directive.
- **External review handoff**: use `request_external_scientific_review_directive` when BR should provide review criteria/schema but cannot read the external artifacts itself. Use `submit_external_scientific_review_verdict` only after an external agent has actually inspected the evidence and produced a schema-valid verdict.
- **Report generation and rendering**: use `scientific_report_generate` when producing a research-facing report from reviewed evidence. Use `latex_report_render` only to render supplied structured sections; it does not perform scientific review by itself.
- **KG and dataset lookup**: use `kg_search_nodes`, `kg_get_node`, and `kg_neighbors` for KG node lookup and neighborhoods. Use `kg_search_datasets`, `kg_related_datasets`, `dataset_get_resources`, and `kg_list_dataset_onvoc_links` for dataset discovery / resources / ontology links. Use `kg_behavior_to_fmri_retrieval` for behavior-to-task-fMRI evidence and `kg_multihop_qa` for multi-hop KG questions; report degraded or timeout results explicitly.
- **KG hypothesis verification and critique**: use `kg_verify_hypothesis` to check a claim against KG evidence. Use `kg_probe` for structural leverage, contradiction motifs/frontiers, assumption cracks, or analogy transfers.
- **KG hypothesis generation and candidate workflows**: use `kg_hypothesis_workflow` for sample/verify workflows, `kg_hypothesis_candidate_cards` for synchronous candidate cards, `hypothesis_hot_load_research` for the full hot-load path, and `hypothesis_run_start` / `run_get` for longer hypothesis runs.
- **Literature, paper, file-search, and grounding tools**: use `google_deep_research` for current web-grounded synthesis, or `google_deep_research_start` for async deep research. Use `deepxiv` for arXiv/PMC paper search and reading. Use `google_file_search` only for configured Google File Search stores. Use `grounding_resolve` to resolve evidence anchors and `grounding_gate_evidence_basis` to downgrade weak or unresolved final evidence claims.
- **Diagnostics and synthesis helpers**: use `companion_diagnostic_suggester` for metric-specific companion checks, `refuted_landscape_summary` to summarize supported/refuted/inconclusive directions from structured findings, `generate_research_trajectory_and_insights` for durable trajectory summaries, `generate_bug_digest` for run/candidate failure summaries, and `generate_repo_repair_context` for repair-context synthesis.
- **Environment-specific helpers**: use `slurm_guide` and `slurm_submit` for SLURM workflow guidance and debugging. (`sherlock_guide` / `sherlock_slurm` remain as deprecated aliases for one release cycle.)
- **Direct lookup rule**: there is no generic `br.lookup` MCP function unless a client exposes one. For known items, use the specific lookup surface: `memory_get`, `tool_get`, `run_get`, `artifact_read_text`, `kg_get_node`, `dataset_get_resources`, or the relevant review/report getter.

## Self-critique checkpoint

- After obtaining an initial research result, do not write the final report immediately. First run a self-critique pass, using Brain Researcher MCP review tools when they are active and relevant.
- **Interest check**: if a reviewer's first reaction would be "so what?" rather than "interesting," the analysis is not finished. Refine the framing, comparison, visualization, or follow-up analysis until the result has a clear scientific point.
- **Null-result diagnosis**: if the main effect is weak or non-significant, do not immediately report it as a final null. First check whether the null may be caused by methodological choices such as the wrong analysis granularity, uncontrolled confounders, weak labels, placeholder categories, insufficient filtering, or an overly broad outcome definition.
- **Exploratory follow-up**: run at least one reasonable post-hoc exploration before concluding. For example, check whether a weak overall effect hides signal in a subgroup, condition, feature family, brain network, network pair, task contrast, dataset split, or quality-controlled subset. Clearly label these findings as exploratory.
- Only proceed to the final report after this checkpoint is completed. The report should state what was tested, what was found, what was checked after the initial result, and which findings are confirmatory versus exploratory.

## Research logging harness

- Treat research logging as `start + optional enrichment + final snapshot`, not as per-turn commentary.
- At the start of real work, call `log_research_event(kind="start", content=..., session_id=..., source="agent", source_client=...)`.
- Always pass `source_client` when the client is known: use `codex`, `codex_cli`, or `claude_code` rather than leaving it null. If the client exposes a native thread/chat/session id, pass it as `client_session_id`; otherwise use one stable descriptive `session_id` for the continuous task.
- Mid-session `kind="note"` is optional and should be used only for rationale that server-side telemetry cannot infer from traces.
- Before the final answer, call `write_session_snapshot(session_id=..., goal=..., done=[...], open=[...], next_command=..., source="agent", source_client=...)` exactly once for the continuous task.
- Prefer one `session_id` per continuous coding session. Reuse the same id across the session unless a tool directive says otherwise.
- If a BR tool response includes `_agent_directive.research_logging`, follow it and reuse the provided `session_id`.
- If a closeout directive includes `review_session_snapshot_hygiene`, treat it as advisory feedback for future sessions or follow-up policy work. Do not imply the persisted snapshot was rejected or amended.
- Do not paste the full raw JSON response from `log_research_event` or `write_session_snapshot` into the user-facing final answer unless the user asks for it. Summarize the logged `run_id` / `session_id`, what was captured, and any open follow-up instead.
- Treat lingering `status="running"` research-logging sessions as incomplete closeout unless the work is intentionally still in progress; close them with a snapshot when the task is done.

## Verification checkpoints

Before claiming this template is in effect, confirm:

- `server_info` returns a `contract_version` your tooling recognizes. Refuse to run if the version is older than your minimum, or fall back to a degraded mode that announces the mismatch.
- The `stable_tools` array in `server_info` lists the 10 closed-loop tools you expect. If anything you rely on is in `deprecated_tools`, plan for the rename within one release cycle.
- The `capabilities` flags you depend on (`planning`, `pipeline_execution`, `scientific_review`, `grounding`, `run_observability`) are all `true`.
