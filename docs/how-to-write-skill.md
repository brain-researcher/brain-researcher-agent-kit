# How to write a skill

A skill is a portable directory that an agent loads to gain a specific capability. This kit follows the SKILL.md convention popularized by DeepMind science-skills.

## Layout

```
skills/<your-skill>/
├── SKILL.md           # required; YAML frontmatter + workflow markdown
├── agents/            # optional; per-client launch metadata
│   ├── claude_code.md
│   └── openai.yaml
├── references/        # optional; data files the skill cites at runtime
└── scripts/           # optional; deterministic helpers the skill invokes
```

## SKILL.md frontmatter

```yaml
---
name: your-skill-name
description: One sentence saying when this skill should be invoked.
---
```

The `description` is the first thing an agent reads when deciding whether to load the skill. Keep it specific: name the situation that triggers it, not the high-level capability.

## SKILL.md body

A useful skill body has five sections:

1. **Overview** — one paragraph: the discipline this skill enforces and when not to use it.
2. **Workflow** — numbered steps the agent should follow. Each step names a tool, a check, or a decision.
3. **Anti-patterns** — explicit "don't" list. The more concrete, the more useful.
4. **Resources** — what's under `references/` and `scripts/`, with a one-line purpose for each.
5. **Example user requests** — the kinds of prompts that should trigger this skill (mirrors how `tool_search` works).

## Wrapper-skills (the common case in this kit)

Most skills in this kit don't introduce new logic — they wrap an existing Brain Researcher MCP tool with the right discipline around it. For example, `evidence-grounding/` wraps `grounding_gate_evidence_basis` with rules for when to set `partial_action="reject"` vs `"downgrade"`.

A wrapper skill's `SKILL.md` should:

- Name the BR stable-tier tool it relies on.
- Cite the `contract_version` it was authored against.
- Declare the fallback path (link to `adapters/br-fallback-policy.md`).
- Stay under 200 lines. If you find yourself writing executable Python, it probably belongs as a real tool in `brain-researcher-public`, not as a skill here.

## Sanitization checklist (before committing)

- Run `python scripts/redaction_guard.py`. It must end with `Redaction guard passed`.
- Confirm `agents/*.md` and `agents/*.yaml` don't reference internal repo paths or private codenames.
- If the skill ships any `references/*.yaml` with named individuals, see the consent rules in `SKILL_LICENSES.md`.

## Tests (when the skill has scripts/)

Add a unit test under `tests/skills/<your-skill>/`. Reuse the contract-test infrastructure from `brain-researcher-public/tests/contracts/` if your skill asserts BR tool shapes.

## Get reviewed

Open a PR. The reviewer checks: clarity of `description`, presence of anti-patterns, redaction gate clean, and that any BR tool reference is at or above the kit's `contract_version_required`.
