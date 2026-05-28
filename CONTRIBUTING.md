# Contributing

Thanks for caring about `brain-researcher-agent-kit`! The kit is the agent-facing surface of the larger Brain Researcher system. That means a useful contribution can land in three different places:

- **This kit** — a broken demo, a wrong rubric, a stale adapter route, a missing skill.
- **NeuroKG (BR-KG)** — a wrong/missing entity, mapping, or evidence link in the compiled knowledge graph.
- **BR agent behavior** — the agent in [`brain-researcher`](https://github.com/zjc062/brain-researcher) (Claude Code / Codex / web client) picked the wrong tool, hallucinated args, or skipped a checkpoint.

The rest of this page tells you where to file each kind, and what to put in the report.

For shared dev conventions (style, tests, release flow), see [`brain-researcher-public/CONTRIBUTING.md`](https://github.com/zjc062/brain-researcher-public/blob/main/CONTRIBUTING.md). By participating, you agree to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Where to take what

| You want to… | Go here |
|---|---|
| Report a kit bug (demo fails, rubric wrong, adapter routes badly, doc lies) | [Open an issue here](https://github.com/zjc062/brain-researcher-agent-kit/issues/new) with **bug** |
| Suggest a new skill, adapter intent, or example | [Open an issue here](https://github.com/zjc062/brain-researcher-agent-kit/issues/new) with **proposal** |
| Fix or add a NeuroKG entity / mapping / evidence link | Wiki PR against `brain-researcher-public` — see the [BR-KG contribution protocol](#contributing-to-neurokg-br-kg) below |
| Report a BR agent bug (wrong tool, hallucinated args, skipped self-critique, no session snapshot) | Issue in [`brain-researcher`](https://github.com/zjc062/brain-researcher/issues/new) with **agent-behavior** — see [Reporting BR agent issues](#reporting-br-agent-issues) below |
| Stale reference to a Brain Researcher MCP tool that no longer exists | Issue here with **contract-drift**; include the `contract_version` your server reports from `server_info` |
| Ask "is this the right way to use the kit?" | [GitHub Discussions](https://github.com/zjc062/brain-researcher-agent-kit/discussions) |
| Report a security or data-leak issue (token in a demo, PHI in an example) | **Do not** open a public issue. Follow [`SECURITY.md`](SECURITY.md) + [`REDACTION_POLICY.md`](REDACTION_POLICY.md) |

If you can't tell which surface owns a problem, file it here and we'll move it.

---

## Good kit bug report

You don't need a PR. A few sentences is usually enough:

1. **What you tried** — which file, which demo, which adapter intent.
2. **What you expected** — one sentence.
3. **What happened instead** — error / wrong tool / surprising rubric verdict.
4. **Your context** — the `contract_version` from `server_info`, which client (Claude Code / Codex / Cursor / Continue / custom), and whether [`MCP_SETUP.md`](MCP_SETUP.md)'s 2-line live check passed.

## Good kit proposal

We bias toward small, generic additions over project-specific ones:

- **New skill** — sketch the SKILL.md frontmatter. See [`docs/how-to-write-skill.md`](docs/how-to-write-skill.md). Wrapping a closed-loop tool already in `brain-researcher-public` is the easiest accept.
- **New adapter intent** — name the generic intent, the BR tool it would route to, and one realistic prompt that should hit it. Format mirrors `adapters/br-adapter-map.json`.
- **New example / demo** — describe the user query, the closed-loop path, and what failure mode it catches. A rubric in `evals/rubrics/` should be able to score it.

Out of scope here:
- BR MCP tool behavior changes → `brain-researcher-public`.
- Agent behavior changes → `brain-researcher`.
- Heavy executable Python — if you're writing a tool, it probably belongs upstream as a real MCP tool, not as a skill.

---

## Contributing to NeuroKG (BR-KG)

NeuroKG is not a static graph dump — it is a maintained scientific knowledge system. Reliability depends on three processes working together: source refresh (OpenNeuro, NeuroVault, Neurostore, PubMed, Cognitive Atlas, ONVOC, atlases, tool registries on explicit schedules), human contribution (corrections, mappings, evidence links), and agent contribution (structured proposals that stay candidate-only until reviewed).

The compiled graph stays schema-strict, provenance-aware, and conservative — but the **wiki layer is where corrections happen**, and that does not require Cypher or Neo4j access.

### Three-layer architecture

| Layer | Plain-language role | What can change? |
|---|---|---|
| 1. **Raw sources** | Publications, datasets, ontology trees, upstream materials. | Immutable here. Update only through source refresh. |
| 2. **Wiki layer** | Human-friendly Markdown with YAML frontmatter, one template per entity type. | Community edits via GitHub PR; schema validation gates each change. |
| 3. **Compiled graph** | Validated Neo4j graph built periodically from raw + accepted wiki records. | Only after validation + review. Snapshot date and source provenance recorded. |

Public KG claims should reference the **compiled graph snapshot**, the **source provenance**, and the **accepted wiki commit** — not a moving file path.

### Contribution flow

| Step | What happens | Quality gate |
|---|---|---|
| Edit Markdown | Edit a wiki file or create one from an entity template. | Path + YAML frontmatter must match a supported template. |
| Open PR | Human-readable rationale + machine-readable YAML. | CI runs schema check, ID normalization, graph-diff preview. |
| Validation queue | Classify by risk (correction / new finding / schema / governance). | Invalid relation types, unresolved evidence, missing fields block merge. |
| Review queue | Human reviewers + optional LLM triage. | LLMs may triage and summarize; high-impact scientific assertions need human review. |
| Compile to graph | Accepted records compiled to nodes/edges with provenance back to the wiki commit. | Edge carries source marker, contributor, review status, snapshot date. |

### v0 entity templates

Start with **finding** and **correction** first; ship **evidence**, **workflow**, **pipeline** templates so the repo is ready for expansion. A schema change is always a **separate PR**, never smuggled into an ordinary contribution.

| Template | Purpose | Required fields | Validation |
|---|---|---|---|
| `evidence` | Source-backed record (paper, dataset, source artifact). | `type, id, title/label, references, source, evidence_kind, status, schema_version` | `references` → DOI/PMID/URL/dataset ID; `evidence_kind` from allowed list. |
| `finding` | Scientific assertion linking entities (task activates region, map measures concept). | `type, id, title, claim.{subject,relation_type,object}, evidence, confidence, status, schema_version` | `relation_type` ∈ allowed graph relations, else schema-change PR required. |
| `correction` | Proposed fix to a label, alias, mapping, relation, or source attribution. | `type, id, target, correction_kind, proposed_change, rationale, evidence, status, schema_version` | `target` must resolve to an existing entity or accepted wiki record. |
| `workflow` | Human-readable workflow note for curation, validation, or review. | `type, id, title, steps, inputs, outputs, owner, status, schema_version` | `status` ∈ {draft, active, deprecated}; inputs/outputs ∈ supported artifact classes. |
| `pipeline` | Build / ingestion pipeline description. | `type, id, title, source, loader, inputs, outputs, schedule, validation, status, schema_version` | `loader` + `source` must map to known release / source registry rows. |

### Worked example — `finding`

```yaml
---
type: finding
id: finding-working-memory-dlpfc-001
schema_version: BR-KG-wiki-v0.1
status: proposed
title: Working-memory task activates a dorsolateral prefrontal cortex region
aliases:
  - working memory dlPFC activation
claim:
  subject:  {type: Task,        id: task:working_memory,       label: working memory task}
  relation_type: ACTIVATES
  object:   {type: BrainRegion, id: region:dlpfc_placeholder,  label: dorsolateral prefrontal cortex}
  qualifiers: {modality: fMRI, coordinate_space: MNI}
confidence:
  value: null
  tier: needs_review
  rationale: Example-only record; evidence must be reviewed before graph merge.
evidence:
  - {type: publication, doi: TODO, pmid: TODO, support_text: TODO short paraphrase}
provenance:
  contributor: github:example-user
  created_at: 2026-05-04
review:
  required: human
  suggested_reviewers: [cognitive-neuroscience, neuroimaging]
---
```

CI emits a **compiled-graph diff preview** (not executed):

```cypher
CREATE (:Finding {
  id: "finding-working-memory-dlpfc-001",
  title: "Working-memory task activates a dorsolateral prefrontal cortex region",
  status: "proposed", source: "wiki_contribution",
  schema_version: "BR-KG-wiki-v0.1"
})
MATCH (task:Task {id: "task:working_memory"})
MATCH (region:BrainRegion {id: "region:dlpfc_placeholder"})
CREATE (task)-[:ACTIVATES {
  source: "wiki_contribution",
  source_file: "findings/finding-working-memory-dlpfc-001.md",
  status: "proposed", confidence_tier: "needs_review",
  created_at: "2026-05-04"
}]->(region);
```

Expected warnings: `region:dlpfc_placeholder` must resolve to an atlas-backed `BrainRegion`; DOI/PMID are TODO; `confidence.value` null → human review required.

### Worked example — bad PR rejection

```yaml
claim:
  subject:       {type: Task, id: task:working_memory}
  relation_type: causes_increase_in     # invalid in v0
  object:        {type: BrainRegion, id: region:dlpfc_placeholder}
```

CI:

```
FAIL: relation_type "causes_increase_in" is not in the v0 allowed relation vocabulary.
Suggested fixes:
  1. Use an existing relation: ACTIVATES, MEASURES, RELATED_TO, SUGGESTS_MEASURES.
  2. Open a separate schema-change PR proposing causes_increase_in,
     including directionality, allowed node types, evidence requirements, review policy.
```

---

## Reporting BR agent issues

If the BR agent (Claude Code / Codex / web client, or any agent running with this kit's templates) misbehaves, that's almost always a `brain-researcher` issue, not a kit issue — but knowing what to capture is the same regardless of where you file.

### Failure modes worth a report

- **Wrong tool selection** — agent picked a tool that doesn't match the intent (e.g., called `pipeline_execute` for a planning request).
- **Invented tool name** — called a name that isn't in `server_info.stable_tools` or `deprecated_tools`.
- **Hallucinated arguments** — args didn't appear in the user prompt and don't come from a prior tool result.
- **Skipped self-critique** — went straight from initial result to final report, no "interest check / null diagnosis / exploratory follow-up" pass.
- **Skipped session snapshot** — finished a task without calling `write_session_snapshot`, leaving a `status="running"` session behind.
- **Over-claimed execution** — described `plan_preflight` / `plan_create` / `pipeline_plan_validate` / `get_execution_recipe` as having executed an analysis.
- **Raw JSON dump** — pasted the full `log_research_event` or `write_session_snapshot` response into the user-facing final answer.
- **Contract drift** — agent followed an `AGENTS.brain-researcher.md` rule that names a tool the live server no longer exposes.

### What to include

1. **Where** — Claude Code / Codex / web; native session id if the client surfaces one.
2. **`session_id`** — from `log_research_event` or `write_session_snapshot`. This is the single most useful field.
3. **The user prompt** — verbatim (redacted if needed per [`REDACTION_POLICY.md`](REDACTION_POLICY.md)).
4. **Expected vs actual** — one line each.
5. **`contract_version`** — from `server_info` at the time of the run.
6. **Which template was active** — if the project's `AGENTS.md` includes `AGENTS.brain-researcher.md` from this kit, say which version (commit SHA).

Bug reports without a `session_id` are still welcome, but with one the maintainers can replay the trace.

---

## Tone

Critical feedback is welcome and useful. Personal attacks, dismissiveness, and bad-faith framing are not. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Recognition

Casual contributors show up in GitHub's contributors graph. Substantive design, KG, or example contributions are acknowledged in release notes when we cut a version.
