# Claude Code Prompt: Brain Researcher Session Handoff

Use this block when Claude Code works in the Brain Researcher repository and
the work should be recoverable through BR session logging.

```text
Use the Brain Researcher MCP tools if they are exposed in this Claude Code
session. Inspect the actual tool list first; do not invent tool names.

Apply the Brain Researcher closed-loop hard rules even if a matching skill is
not installed:

- Evidence-backed answers and reports must pass grounding_resolve plus
  grounding_gate_evidence_basis, or be downgraded/blocked.
- plan_preflight, plan_create, pipeline_plan_validate, pipeline_plan_review,
  and get_execution_recipe are planning/validation/handoff surfaces, not
  executed analyses.
- Weak or null scientific results require self-critique before final reporting;
  label any follow-up as exploratory.
- Public demo fixtures must redact local paths, local MCP server names, and
  client-specific MCP prefixes before commit.
- If the live server surface differs from the template, inspect server_info,
  stable_tools, deprecated_tools, tool_search, and tool_get before calling.

For real Brain Researcher repo work:

1. Start once with log_research_event(kind="start", source="agent",
   source_client="claude_code", session_id=<stable task id>, content=<goal>).
2. Reuse the same session_id for the continuous task. If Claude exposes a
   native thread/session id, pass it as client_session_id.
3. Use canonical open-risk labels in handoff open items when applicable:
   uncommitted-local, unrelated-dirty-worktree, partial-validation,
   prod-auth-data-runtime, generated-artifact, pre-existing-debt,
   scientific-method-gap, logging-metadata-gap.
4. Before the final user-facing answer, call exactly one
   write_session_snapshot(..., source="agent", source_client="claude_code").
5. Put concrete validation evidence in done/open. Do not close a session as
   "done" with only vague prose such as open=["None"].
6. If the MCP response includes _agent_directive.research_logging, follow its
   actions and reuse the provided session_id. Treat
   review_session_snapshot_hygiene as advisory feedback, not as a rejected or
   amended snapshot.
7. Do not paste raw BR JSON in the final answer. Summarize changed, verified,
   open, next_command, and BR session_id/run_id.

If the BR MCP server is inactive or unavailable, say that BR logging is
unavailable and continue with the same concise local handoff format.
```

Good final handoff shape:

```text
changed: <paths and behavior>
verified: <commands or checks actually run>
open: <canonical risk label plus concrete blocker, or "none" only if true>
next_command: <one concrete command for resumption>
BR session_id: <session id> / run_id: <run id>
```
