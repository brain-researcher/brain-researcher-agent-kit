# Brain Researcher MCP — terminal setup and live checks

Canonical reference: <https://brain-researcher.com/mcp/setup>

This file is the kit-local mirror of the same flow, so an agent or a new contributor can confirm in ~2 minutes that the Brain Researcher MCP server is reachable before relying on anything in `agents/AGENTS.brain-researcher.md` or `adapters/br-adapter-map.json`.

## 1. Put the token in your shell rc

Pick the file your login shell actually reads — `~/.zshrc` on macOS (default since Catalina) and on Linux when you use zsh, `~/.bashrc` on most Linux distros where bash is the default. If unsure, `echo $SHELL` tells you which one.

Open it:

```bash
nano ~/.zshrc      # macOS, or Linux with zsh
# or
nano ~/.bashrc     # Linux with bash
```

Add:

```bash
# Brain Researcher MCP
export BR_MCP_TOKEN="brk_<kid>.<secret>"
export BR_MCP_AUTH_HEADER="Bearer ${BR_MCP_TOKEN}"
```

Reload and verify:

```bash
source ~/.zshrc    # or: source ~/.bashrc
test -n "$BR_MCP_TOKEN" && echo "BR_MCP_TOKEN is set"
```

Do **not** put `Bearer ` inside `BR_MCP_TOKEN`; only the raw `brk_...` token. The `Bearer` prefix belongs in `BR_MCP_AUTH_HEADER` only.

On Linux, if you also use a login-only shell (SSH, some terminal multiplexers), `~/.bashrc` may not be sourced — append the same two lines to `~/.bash_profile` or `~/.profile` and re-login, or have `~/.bash_profile` source `~/.bashrc`.

## 2. Live-check from Codex

```bash
codex
```

Then paste:

> show me the status of brain_researcher_mcp. Use the Brain Researcher MCP `server_info` and `system_self_test` tools. Keep the answer concise.

Healthy response: `server_info: ok=true` and `system_self_test: overall=pass`.

## 3. Live-check from Claude Code

```bash
claude
```

If Claude prompts to trust the workspace or approve the `brain-researcher` MCP server, approve only what is needed for this project/server.

Then paste:

> show me the status of brain_researcher_mcp. Use the brain-researcher MCP `server_info` and `system_self_test` tools. Keep the answer concise.

Healthy response: `brain-researcher MCP status: healthy` and `Self-test (quick): overall=pass`.

## 4. What to do when it is *not* healthy

- `server_info` missing or returning an old `contract_version` → check the BR MCP server side; the kit's `br-fallback-policy.md` describes how an agent should degrade.
- `system_self_test` reports a failing dependency → surface the failing component verbatim; do not paper over it.
- Token rejected (401/403) → re-source `~/.zshrc`, confirm `BR_MCP_TOKEN` has no `Bearer ` prefix and no surrounding quotes.
- No `brain-researcher` server listed in the client at all → the MCP server entry is missing from the client's config; consult the canonical setup page above.

## Agent rule (one line for `AGENTS.brain-researcher.md`)

> When the user asks whether Brain Researcher MCP is working / healthy / reachable, call `server_info` and `system_self_test` and report the two results in one short paragraph. Do not paste the raw JSON unless the user asks for it.
