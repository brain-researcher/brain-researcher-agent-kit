---
name: prod-mcp-health-sweep
description: Health-check the brain_researcher MCP surface against prod — exercise every tool with representative prompts, list broken vs working, then after a fix reload the MCP and re-verify the previously-failing fields actually populate. Use for "double-check the BR MCP", "are the tools all solved", or triaging a reported prod MCP defect after a deploy.
---

# prod-mcp-health-sweep

Turn the recurring ad-hoc "sweep every MCP tool → find broken → fix → re-request →
confirm solved" loop into one repeatable pass with a known baseline, so regressions are
flagged instead of re-discovered by hand each time. These sweeps feed the BR-vs-host paper.

## When To Use

- "double-check the BR MCP / 都解决了吗", "which tools work on prod after this deploy", or a
  reported prod MCP defect after a rollout.
- NOT for: the fix implementation itself (hand that to `worktree-pr-cycle` + `br-rollout`);
  authoring or aligning new MCP tools (see Related).

## Step 0 — Consult Memory First

Before diagnosing, `memory_search` for prior fixes of the same class — the project keeps
auto-memory precisely so a problem isn't re-solved. The known-relevant cards are listed under
Related Memory below.

## Workflow

1. **Sweep the surface** with representative prompts and record a working/broken matrix across
   the core tools: `kg_search_nodes`, `kg_search_datasets`, `kg_get_node`, `kg_neighbors`,
   `grounding_resolve`, `kg_verify_hypothesis`, `kg_multihop_qa`, `tool_search`,
   `plan_preflight`, `run_list`, `memory_search`, `kg_method_condition_coverage_guard`.
2. **Baseline to compare against** (as of the last sweeps — re-verify, don't assume):
   - WORKING: `kg_search_nodes/datasets`, `kg_probe`, `tool_search`, `plan_preflight`,
     `run_list`, `memory_search`.
   - WATCH (Neo4j-timeout / extraction-fragile): `kg_get_node(Concept)`, `grounding_resolve`,
     `kg_verify_hypothesis` (concept-fetch timeout), `kg_multihop_qa` (seed-term extraction).
   - Contract: `kg_verify_hypothesis` is hard-bounded ~60s — a longer hang is a regression.
   - Flag any WORKING tool that regresses OR any WATCH tool that newly passes.
3. **Fix** via `worktree-pr-cycle`; deploy via `br-rollout` (prod is k3s on the GCE VM).
4. **Re-verify the mechanism engaged (load-bearing)** — after deploy, **reload the BR MCP** and
   re-probe the previously-null / failing fields; assert they are now populated. A happy-path
   log line or a green health pill is NOT proof — re-run the exact failing call.
5. **Completeness check** — when a defect is a class (e.g. a null field on one node type),
   sweep for the same class elsewhere before declaring it solved (the user pushes back on
   happy-path fixes).

## Honesty / Invariants

- Report degraded / timeout results explicitly; never smooth them over.
- Creds from `.env`; never guess or brute-force a password, never harvest creds from another
  container.
- Prod deploys need explicit per-cycle authorization (intentional gate) — do not route around it.

## Client Prompt Artifacts

- `agents/openai.yaml` for Codex/OpenAI skill launch metadata.
- `agents/claude_code.md` for a compact Claude Code instruction block.

Keep both adapters in this skill directory. The repo pointer invariant:
do not duplicate the policy into `CLAUDE.md` (repo convention: instructions live in AGENTS.md; CLAUDE.md only points there).

## Related

- `skills/brain-researcher-mcp-contract-workflow` keeps MCP tool code, schema, and tests aligned
  during development (in-repo contract hygiene). This skill is distinct: it exercises the
  deployed PROD MCP surface and re-verifies previously-failing fields after a fix. Cross-link,
  don't re-document its content here.
- Fix + deploy are delegated: `worktree-pr-cycle` (ship the fix) and `br-rollout` (prod k3s).

## Related Memory

`project_mcp_concept_node_fetch_timeout`, `project_kg_search_datasets_prod_defects`,
`project_kg_glm_prior_projection_gap`, `project_kg_verify_budget_and_neo4j_timeout`,
`project_tools_catalog_br_kg_domain_bug` (open), `feedback_verify_mechanism_engaged`.
