# Claude Code Prompt: BR vs Host Benchmark

Use this block when Claude Code runs or re-scores the BR-vs-no-BR benchmark
(NIK / tool-calling) in the Brain Researcher repository.

```text
Evaluate Brain Researcher against a strong no-BR model *fairly*, not favorably.

1. Locate the canonical matrix launcher under benchmarks/ before running
   anything: grep -rl "with_br_proper\|without_br" benchmarks/. Reuse it; do
   not hand-roll an invocation.
2. Resolve the prod BR-MCP token via scripts/mcp/resolve_br_mcp_token.sh
   (BR_MCP_FORCE_PROD=1). Never inline the token.
3. Scope cells (task × model × mode). Run ONLY unfinished cells; do NOT re-run
   the whole matrix. Modes: with_br_proper, without_br, forced-citation.
4. Kill leftover runners/orchestrators/model children before any rerun; stale
   runners produce mixed results. Background long runs and poll with Monitor.
5. LLM-judge by spawning Claude Code (Opus, high reasoning) subagents that read
   the traces. Do NOT use the Anthropic SDK / claude-api path.
6. Report stratified honest metrics: verified/claimed, supportable/claimed,
   spam, cannot_judge, latency. A valid no-BR DOI/PMID citation counts as
   correct. Do not report a broken composite (VGR) as a real signal.
7. No MCQ gold key: NIK is open-ended, there is no valid Correct_Answer to
   score against. Report claude_opus47 as "Claude Code / Claude Opus 4.8".
```

Good final handoff shape:

```text
cells_run: <task × model × mode actually completed>
launcher: <canonical launcher path reused>
metrics: <verified/claimed, supportable/claimed, spam, cannot_judge, latency>
caveats: <parser-bias re-score, un-merged-image, label-split PR>
```
