# Security policy

`brain-researcher-agent-kit` ships skills, AGENTS templates, MCP adapters, and demos. It does **not** ship a network service; security review focuses on the supply chain and the patterns these artifacts encourage.

## Reporting a vulnerability

Email security disclosures to **micochan0622@gmail.com**. Do not file public GitHub issues for security-sensitive defects.

We will acknowledge receipt within 5 business days. Coordinated-disclosure timelines are negotiated case-by-case; default to 90 days unless circumstances warrant otherwise.

## Scope

In scope:

- Skill scripts that execute on the user's machine. A malicious or vulnerable script here can compromise the user.
- Adapter map / fallback policy that incorrectly routes around BR's gating tools (e.g. silently bypassing `grounding_gate_evidence_basis`).
- AGENTS templates that encourage unsafe patterns (e.g. claiming hosted execution where only a local recipe ran).
- Bundled prompts / fixtures that contain real credentials, hostnames, or subject IDs.

Out of scope:

- Vulnerabilities in `brain-researcher-public` itself. Report those to the brain-researcher-public repo per its own `SECURITY.md`.
- Vulnerabilities in third-party MCP servers connected through this kit's adapter pattern.
- Misconfiguration of the agent platform (Codex CLI, Claude Code, etc.) that invokes the kit.

## Contract divergence vs vulnerability

If the kit's `adapter-map.json` declares a `contract_version_required` that the live `brain-researcher-public` server doesn't satisfy, that is **not** a vulnerability — it is the kit refusing to dispatch by design. File those as regular issues, not security reports.

## Secrets

This repo must never contain real secrets. CI runs an automated secret/trace scan (`python scripts/redaction_guard.py`) on every push and pull request. If you accidentally commit a secret:

1. Rotate the secret immediately at the provider.
2. Open a security report so we can scrub the history if needed.
