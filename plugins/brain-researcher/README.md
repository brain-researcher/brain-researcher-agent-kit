# Brain Researcher — Claude Code plugin

Connects Claude Code (and any MCP client) to the hosted **Brain Researcher** MCP
server at `https://brain-researcher.com/mcp`: a neuroimaging research-agent
surface with BR knowledge-graph search, method-condition lookup, autoresearch,
scientific review, and run management.

The plugin ships only the client-side connection config. The MCP server is
hosted, so there is nothing to build or run locally.

## Install

```text
/plugin marketplace add brain-researcher/brain-researcher-agent-kit
/plugin install brain-researcher@brain-researcher-agent-kit
```

## Authenticate (required)

The server needs a personal MCP token.

1. Open <https://brain-researcher.com/mcp/setup>, sign in, and generate a
   personal MCP token. Format: `brk_<kid>.<secret>`. There is one active token
   per user — regenerating rotates the previous one immediately.
2. Give the token to the plugin when prompted, or set it explicitly:

   ```text
   /plugin configure brain-researcher@brain-researcher-agent-kit
   ```

   Claude Code stores the token as a **sensitive** per-user config value (in the
   OS keychain / your Claude credentials), substitutes it into the
   `Authorization: Bearer …` header at connect time, and never writes it into
   the repo or the plugin. This works regardless of which shell launched Claude
   Code.

   From the CLI you can also pass it at install time:
   `claude plugin install brain-researcher@brain-researcher-agent-kit --config BR_MCP_TOKEN=brk_<kid>.<secret>`

## Verify

Run `/mcp` in Claude Code and confirm `brain-researcher` shows **connected**.
Then:

```text
Check Brain Researcher MCP: call server_info and system_self_test and report both concisely.
```

Healthy = `server_info: ok=true` and `system_self_test: overall=pass`. A `401`
means the token is missing, rotated, or was entered with a `Bearer ` prefix
(store only the raw `brk_…` value — the plugin adds `Bearer ` itself).

## Token cost

The plugin adds **~0 always-on tokens**. `brain-researcher` is an HTTP MCP
server whose tool schemas are resolved at runtime and support MCP tool-search
deferral, so its (large) tool surface is not loaded into every turn.

## Other clients

For Cursor, Codex CLI, Windsurf, the `claude mcp add` CLI path, and the
environment-variable (`BR_MCP_TOKEN`) form used by those clients, see
[`MCP_SETUP.md`](https://github.com/brain-researcher/brain-researcher-agent-kit/blob/main/MCP_SETUP.md)
or the canonical page at <https://brain-researcher.com/mcp/setup>.

## License

MIT © Brain Researcher contributors
