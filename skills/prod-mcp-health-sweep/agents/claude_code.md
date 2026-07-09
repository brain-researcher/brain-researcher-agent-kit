# Claude Code Prompt: Prod MCP Health Sweep

Use this block when Claude Code triages the deployed Brain Researcher MCP surface
against prod — sweeping tools, finding broken ones, and re-verifying after a fix.

```text
Use the Brain Researcher MCP tools if they are exposed in this Claude Code
session. Inspect the actual tool list first; do not invent tool names.

To health-check the prod BR MCP surface:

1. memory_search FIRST for a prior fix of the same class before diagnosing.
2. Sweep representative prompts across kg_search_nodes, kg_search_datasets,
   kg_get_node, kg_neighbors, grounding_resolve, kg_verify_hypothesis,
   kg_multihop_qa, tool_search, plan_preflight, run_list, memory_search,
   kg_method_condition_coverage_guard. Record a working/broken matrix.
3. Compare against the known baseline: flag any WORKING tool that regresses or
   any WATCH tool (Neo4j-timeout / extraction-fragile) that newly passes.
   kg_verify_hypothesis is hard-bounded ~60s; a longer hang is a regression.
4. Hand the fix to worktree-pr-cycle and the deploy to br-rollout. Prod deploys
   need explicit per-cycle authorization; do not route around that gate.
5. After deploy, reload the BR MCP and re-run the exact previously-failing call.
   Assert the null/failing fields now populate. A green health pill or a
   happy-path log line is NOT proof.
6. Report degraded / timeout results explicitly; never smooth them over. Creds
   come from .env; never guess a password or harvest creds from a container.
7. Do not paste raw BR JSON in the final answer. Summarize the matrix, what
   regressed, what was fixed, and what was re-verified.

If the BR MCP server is inactive or unavailable, say so and do not imply that a
sweep or re-verification happened.
```

Good final handoff shape:

```text
swept: <tools exercised>
broken: <tool + failing field/symptom, or "none">
fixed: <PR/deploy, or "handed off">
re-verified: <exact call re-run + field now populated, or "pending deploy">
open: <regressions or WATCH items still degraded, or "none" only if true>
```
