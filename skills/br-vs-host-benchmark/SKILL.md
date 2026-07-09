---
name: br-vs-host-benchmark
description: Run the BR-vs-no-BR benchmark (NIK / tool-calling) across models × modes via the canonical launcher, monitor long runs, then LLM-judge both traces into stratified honest metrics. Use when asked to "run / re-score the BR benchmark", "does BR beat the no-BR model", or "re-score opus48 vs opus47".
---

# br-vs-host-benchmark

Honestly evaluate whether Brain Researcher beats a strong no-BR model on the NeuroimageKnowledge
(NIK) and tool-calling benchmarks. The point is a *fair* comparison, not a favorable one — this
skill encodes the anti-overclaiming discipline the user re-derives every time.

## When To Use

- "run / re-score the BR benchmark", "BR vs no-BR", "re-score both models fairly".
- NOT for: authoring new benchmark tasks (that is `tb-science-task-authoring`); a one-off single
  question (just call the BR MCP tools directly).

## Prerequisites

- **Locate the canonical launcher first** — there is no single fixed `run_matrix.sh`; the matrix
  launchers live under `benchmarks/` (e.g. `benchmarks/UNIFIED_BENCHMARK_BUNDLE/...`,
  `benchmarks/tool_routing_validation/...`). Run `grep -rl "with_br_proper\|without_br" benchmarks/`
  to find the current one, and **reuse it** rather than an ad-hoc invocation, so runs stay
  comparable across models.
- Prod BR-MCP token via `scripts/mcp/resolve_br_mcp_token.sh` (`BR_MCP_FORCE_PROD=1`) — never
  inline it.
- Conda env active; long runs launched in the background with `Monitor`.

## Client Prompt Artifacts

- `agents/openai.yaml` for Codex/OpenAI skill launch metadata.
- `agents/claude_code.md` for a compact Claude Code instruction block.

Keep both adapters in this skill directory. Repo pointer invariant:
do not duplicate the policy into `CLAUDE.md` (repo convention: instructions live in AGENTS.md; CLAUDE.md only points there).

## Workflow

1. **Scope the cells** — a cell = one task × one model × one mode. Run ONLY the unfinished cells; do
   NOT re-run the whole matrix (this over-reach recurred and had to be corrected twice). Modes:
   `with_br_proper`, `without_br`, and (for the calling artifact) `forced-citation`.
2. **Clean before rerun** — kill contaminated / leftover runners, orchestrators, and model child
   processes first (`pgrep`/`pkill` the launcher + children); stale runners produce mixed results.
3. **Launch + monitor** — background the run; poll with `Monitor`; background shells can span
   session boundaries, so record a completion marker for provenance.
4. **Judge the traces** — LLM-judge by spawning **Claude Code (Opus, high reasoning) subagents that
   read the traces**, NOT the Anthropic SDK / `/claude-api` (the user redirects away from the SDK
   path every time).
5. **Score with stratified, honest metrics** — report `verified/claimed`, `supportable/claimed`,
   `spam`, `cannot_judge`, and latency separately. A valid no-BR DOI/PMID citation counts as
   correct. A broken composite (e.g. VGR) must not be reported as a real signal.
6. **Honest attribution split** — keep label cleanup in a SEPARATE PR (no routing code) and report 3
   cells to separate label-correction from retrieval delta: `baseline-labels+old-routing`,
   `cleaned-labels+old-routing`, `cleaned-labels+new-routing`.

## Honesty / Invariants

- **No MCQ gold key.** NIK tasks were converted MCQ → open-ended; there is NO valid `Correct_Answer`
  key — do not use it to score.
- Naming: report the internal trace id `claude_opus47` as **"Claude Code / Claude Opus 4.8"**.
- Watch for parser false-negatives (label/parser bias) that unfairly depress one model — if numbers
  look systematically off, fix the parser and re-score BOTH models, don't ship the biased run.
- Deploy the image the run used from a merged branch, or note the un-merged-image caveat explicitly.

## Related Memory

`project_br_calling_protocol_spam_artifact`, `project_review_layer_calibration_bench`,
`project_kg_search_datasets_prod_defects`, `feedback_verify_mechanism_engaged`.
