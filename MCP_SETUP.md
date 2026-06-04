# Brain Researcher MCP setup

Canonical reference: <https://brain-researcher.com/mcp/setup>

This file is the short repo-local setup path. Use the canonical page for the
latest UI, token-management, and client-tab details.

## 1. Get a personal MCP token

1. Open <https://brain-researcher.com/mcp/setup>.
2. Sign in.
3. Generate a personal MCP token.
4. Copy it immediately.

Token format:

```text
brk_<kid>.<secret>
```

There is one active token per user. Generating a new token rotates the previous
one immediately. Treat the token like a password.

## 2. Add the token to your shell

Use the shell startup file your terminal actually reads. Common choices:

- macOS or zsh: `~/.zshrc`
- Linux bash: `~/.bashrc`

Add:

```bash
# Brain Researcher MCP
export BR_MCP_TOKEN="brk_<kid>.<secret>"
export BR_MCP_AUTH_HEADER="Bearer ${BR_MCP_TOKEN}"
```

Reload:

```bash
source ~/.zshrc  # or: source ~/.bashrc
test -n "$BR_MCP_TOKEN" && echo "BR_MCP_TOKEN is set"
```

Keep `BR_MCP_TOKEN` as the raw `brk_...` token. Do not include the `Bearer `
prefix inside `BR_MCP_TOKEN`.

## 3. Configure your MCP client

Brain Researcher's cloud MCP endpoint is:

```text
https://brain-researcher.com/mcp
```

### Cursor

For a project-local Cursor config, create `.cursor/mcp.json` in the project
root. For a global Cursor config, create `~/.cursor/mcp.json`.

Use environment-variable interpolation so the token is not committed:

```json
{
  "mcpServers": {
    "brain-researcher": {
      "type": "streamable-http",
      "url": "https://brain-researcher.com/mcp",
      "headers": {
        "Authorization": "Bearer ${env:BR_MCP_TOKEN}",
        "Accept": "application/json, text/event-stream"
      }
    }
  }
}
```

Restart Cursor or reload the window after saving the file. To check from Cursor
CLI when available:

```bash
cursor-agent mcp list
cursor-agent mcp enable brain-researcher   # if list says "needs approval"
cursor-agent mcp list-tools brain-researcher
```

If your Cursor version does not accept `streamable-http`, use `"type": "http"`
with the same `url` and `headers`; current Cursor CLI accepts both forms.

### Windsurf and other MCP JSON clients

Use the same server URL and headers. Some clients do not support environment
variable interpolation in JSON; in that case paste the full token into your
private user config, not into a project file:

```json
{
  "mcpServers": {
    "brain-researcher": {
      "type": "http",
      "url": "https://brain-researcher.com/mcp",
      "headers": {
        "Authorization": "Bearer brk_<kid>.<secret>",
        "Accept": "application/json, text/event-stream"
      }
    }
  }
}
```

### Codex CLI

Put the token in your shell as shown above, then run:

```bash
codex mcp add brain-researcher \
  --url https://brain-researcher.com/mcp \
  --bearer-token-env-var BR_MCP_TOKEN
```

If you prefer to edit `~/.codex/config.toml` by hand, the equivalent entry is:

```toml
[mcp_servers.brain-researcher]
url = "https://brain-researcher.com/mcp"
bearer_token_env_var = "BR_MCP_TOKEN"

[mcp_servers.brain-researcher.http_headers]
Accept = "application/json, text/event-stream"
```

Restart Codex from the same shell after setting `BR_MCP_TOKEN`.

### Claude Code

Option A, local private config via CLI:

```bash
claude mcp add --transport http brain-researcher https://brain-researcher.com/mcp \
  --header "Authorization: Bearer ${BR_MCP_TOKEN}" \
  --header "Accept: application/json, text/event-stream"
```

This is easy, but the shell expands `${BR_MCP_TOKEN}` before Claude writes the
config, so treat the resulting local Claude config as secret-bearing.

Option B, project `.mcp.json` with environment-variable expansion:

```json
{
  "mcpServers": {
    "brain-researcher": {
      "type": "http",
      "url": "https://brain-researcher.com/mcp",
      "headers": {
        "Authorization": "Bearer ${BR_MCP_TOKEN}",
        "Accept": "application/json, text/event-stream"
      }
    }
  }
}
```

Claude Code supports `type: "http"` and also accepts `streamable-http` as an
alias in JSON config. Run `claude`, approve the project MCP server if prompted,
then use `/mcp` inside Claude Code to confirm that `brain-researcher` connected.
You can also inspect the saved config from the shell:

```bash
claude mcp list
claude mcp get brain-researcher
```

## 4. Verify the connection

Start or restart your agent after configuring the server, then paste:

```text
show me the status of brain_researcher_mcp. Use the Brain Researcher MCP server_info and system_self_test tools. Keep the answer concise.
```

Expected result:

- `server_info` returns `ok=true`
- `system_self_test` returns `overall=pass`

If the client cannot see those tools, ask it to inspect the exposed MCP tool
names before trying another function.

## 5. Try a workflow handoff

This prepares a recipe. It is not completed hosted execution unless artifacts
are actually produced and inspected.

```text
Use Brain Researcher MCP to prepare a runnable recipe for resting-state connectivity on ds000114. First inspect the available MCP tools, then call server_info and system_self_test. Use workflow_search for resting-state connectivity and then get_execution_recipe with tool_id="workflow_rest_connectome_e2e", target_runtime="python", params={"dataset_id":"ds000114"}. Return the exact recipe command, required inputs, expected artifacts, and any blockers before claiming execution is possible.
```

## Troubleshooting

- No `brain-researcher` server in the client: the MCP config was not loaded, or
  the client needs a restart.
- `401` or `403`: token is missing, expired, rotated, or has the wrong `Bearer`
  placement. Re-source your shell and restart the client.
- `server_info` missing: inspect the active MCP tool list first. Do not call
  tools from memory.
- `system_self_test` failing: report the failing component verbatim.
- A recipe was produced but no artifacts exist: that is expected. A recipe is a
  handoff, not execution.

## Agent rule

When the user asks whether Brain Researcher MCP is working, call `server_info`
and `system_self_test`, then report both results concisely. Do not paste raw
JSON unless the user asks for it.
