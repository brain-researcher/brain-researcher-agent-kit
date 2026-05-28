# Redaction policy

What gets scrubbed from this kit's outputs and source before publishing. Mirrors `brain-researcher-public`'s `REDACTION_POLICY.md`; the rules below are what the kit applies on top of the core scrubber.

## Runtime — outputs the kit emits

Adapter dispatch and demo runner output may include caller-provided paths and arguments. Before logging or surfacing those to the user:

- Use `br.redaction.scrub_text` / `br.redaction.scrub_data` from `brain-researcher-public` to strip credential-shaped strings (API keys, JWTs, bearer tokens).
- Apply path-redaction at the kit boundary: replace absolute `/home/<user>/...`, `/data/...`, `/oak/...` with `${HOME}/...` / `${WORKSPACE}/...` / `${PI_GROUP_DATA}/...` placeholders.

The kit does NOT silently scrub paths from inputs; it only redacts in the outbound direction. If you need stricter scrubbing on intake, wrap your MCP client.

## Source — what this repo must never contain

The pre-commit gitleaks hook + a simple grep catch most leaks:

```bash
grep -rln "/home/$USER\|@stanford.edu\|hai-gcp-dialogue-brain\|liu_component_v1\|sk-br-local\|russ_poldrack" \
  . --exclude-dir=.git
# Should print nothing.
```

| Pattern | Replace with |
|---|---|
| `/home/<user>/`, lab-specific roots | `${HOME}/` or `${PI_GROUP_DATA}/` |
| Personal emails | `person@example.com` |
| Internal hostnames | `host.local` |
| Subject IDs from private datasets | `subject_001`, `subject_002`, ... |
| Internal project codenames | `public-demo-project` |
| Real scientist names (when not part of a citation) | `expert_a`, `expert_b`, ... |
| Lab partition names, ACL group names | `<pi_group>`, `<pi_acl_group>` |

## Sanitization audits performed for v0.1.0

| Asset | Sanitization | Status |
|---|---|---|
| `skills/brain-researcher-session-handoff/` | None needed — uses only public-tier MCP tool names. | ✓ verified 2026-05-27 |
| Other first-party skills (when added) | Each must pass the source grep above. | Pending per-skill audit |
| `examples/*/input/` fixtures | Synthetic; no real subject IDs. | ✓ verified at scaffold time |
| `examples/*/expected_output/` | Will be captured from a live BR MCP run; capture script must apply the redaction rules before commit. | Pending capture |
| `agents/AGENTS.*.md` templates | Carved from internal `AGENTS.md`; private repo paths and codenames dropped during W3. | ✓ verified at carve time |

## Preserve list

Same as `brain-researcher-public`: do not strip schema names, error class names, status codes, relative workflow order, file shapes, tool names, or parameter names.
