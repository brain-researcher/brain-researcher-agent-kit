# AGENTS · research

Generic research-agent policy. No Brain Researcher dependency. Drop this into your agent's `AGENTS.md` (or equivalent) when the agent is doing scientific or analytical work and you want the same discipline that BR uses — even if no BR MCP server is involved.

## Priority rules

- Think before coding. State assumptions explicitly when they affect correctness.
- Prefer the simplest change that solves the requested problem. Avoid speculative abstractions, configurability, or error handling that is not required.
- Make surgical edits. Touch only code that is needed for the request. Do not refactor or clean up unrelated areas.
- Work from verifiable goals. Tie implementation to a concrete check: a focused test, a reproduction, a lint/typecheck run, or another clear validation step.
- Do not overclaim implementation status. When asked whether a protocol, architecture, or feature exists, distinguish clearly between `implemented`, `partial`, and `spec-only`.
- Keep planning and execution separate. When a surface is preview-only, validation-only, or handoff-only, say so explicitly instead of implying execution authority.

## Current direction

- Preserve clear boundaries between explanation, planning, validation, and execution. Do not describe a surface as doing more than it actually does.
- Prefer explicit contracts and verifiable behavior over implicit assumptions about system capabilities.
- Favor lightweight guardrails, simple routing, and incremental extensions before introducing heavier orchestration or new architectural layers.
- Avoid speculative capabilities. If a tool, protocol, route, or integration is not verified in the current surface, say that directly instead of inferring it.

## Workflow

- **Discovery before execution**: inspect existing implementations in the repo before introducing a new code path or service surface.
- Prefer extending existing entrypoints (CLIs, current service modules, existing scripts, existing test fixtures) over adding parallel abstractions.
- Keep behavior changes, refactors, and migrations separable when practical.
- Avoid hardcoded machine-specific or temporary-session paths. Prefer repo-relative paths, config, env vars, or clearly named path variables.
- If multiple technical options are viable, state trade-offs explicitly: correctness, speed, maintenance burden, operational cost, and infra/data requirements.

## Session-derived agent rules

- Treat `succeeded` as "this agent turn completed," not as proof that the product feature, deployment, or scientific claim is fully complete. Preserve remaining blockers in `open` items and the final handoff.
- For prod/runtime work, record the commit or image tag, rollout target, rollout status, health checks, and any API/browser smoke that was actually run. Do not claim hosted execution if the result is only a recipe, handoff, dry run, or local verification.
- For web/UI work, verify both the API payload and the rendered browser state when feasible. Distinguish curated/demo evidence, live analysis evidence, degraded backend health, and local environment failures.
- For repo cleanup or release-readiness work, inventory exact paths first, keep unrelated dirty work separate, preserve example/template files, and validate with focused checks such as `git diff --check`, `git status`, `git ls-files`, or `git check-ignore`.
- For code or contract changes, prefer focused tests that exercise the changed behavior and contract shape. If repo-wide lint or tests are blocked by pre-existing debt, name the narrow validation that passed and the unrelated blocker that remains.
- For scientific workflows, record the hypothesis, confirmatory test, exploratory follow-up, gate/outcome state, null-result diagnosis, and blocked assets. Clearly separate run completion, scientific validity, and manuscript/report readiness.
- When leaving work open, classify the risk before the details when practical: `uncommitted-local`, `unrelated-dirty-worktree`, `partial-validation`, `prod-auth-data-runtime`, `generated-artifact`, `pre-existing-debt`, `scientific-method-gap`, or `logging-metadata-gap`.
- A compact final handoff should include: `changed`, `verified`, `open`, `next_command`. Example: `changed: <paths and behavior>; verified: <commands actually run>; open: <risk label + concrete blocker>; next_command: <one concrete resumption command>`.

## Self-critique before final report

- After obtaining an initial result, do not write the final report immediately. Run a critique pass first.
- **Interest check**: if a reviewer's first reaction would be "so what?" rather than "interesting," the analysis is not finished.
- **Null-result diagnosis**: if the main effect is weak, check whether the null may be caused by methodological choices (wrong granularity, uncontrolled confounders, weak labels, broad outcome definition) before reporting it as a final null.
- **Exploratory follow-up**: run at least one reasonable post-hoc exploration. Label exploratory findings explicitly.
- Only proceed to the final report after this checkpoint. State what was tested, what was found, what was checked after the initial result, and which findings are confirmatory versus exploratory.

## Validation

- Validation is part of the task, not a follow-up.
- Backend logic changes should add or update focused unit tests when feasible.
- API, schema, protocol, or planning-surface changes should validate contract shape, not only happy-path behavior.
- For chat or planner-routing changes, verify the intended mode boundaries directly. Plain chat should stay plain chat; grounded requests should use verified grounding; handoff-only surfaces should not be described as executable.
- If validation cannot run, say exactly what blocked it, what was not verified, and what risk remains.
- Final handoff should summarize what changed, what was verified, and what remains open.

## Security

- Provide secrets via env vars; never commit them.
- Prefer existing data download paths and scripts over ad hoc large-file placement.
- For redaction rules in BR-adjacent work, see `REDACTION_POLICY.md` and the `br.redaction` helpers in `brain-researcher-public`.
