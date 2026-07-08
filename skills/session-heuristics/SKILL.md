---
name: session-heuristics
description: Classify handoff risks and extract candidate lessons from a single Brain Researcher research-session digest using a deterministic, offline rule engine (open-risk taxonomy, session-hygiene checks, and lesson mapping). Use when triaging what a finished agent session left open, auditing a session's logging/handoff hygiene, or turning one session digest into risk labels plus policy-candidate lessons — after obtaining the digest from the Brain Researcher MCP tool research_session_digest.
---

# Session Heuristics

## Overview

Use this skill to turn one Brain Researcher **session digest** into two
deterministic read-outs:

1. **Risk classification** — task surfaces, detected validation evidence,
   canonical open-risk labels, and session-hygiene issues.
2. **Lesson extraction** — conservative, candidate lessons derived from the
   hygiene issues.

This is the offline, inspectable port of the MCP tools `session_risk_classify`
and `session_lesson_extract`. Both are pure functions over an injected digest —
they carry no server state — which is why they can run entirely as a local
skill. The rule kernel lives in `references/risk_taxonomy.json` (patterns,
labels, lesson text) and `references/classification_rules.md` (control flow), so
a reviewer can read exactly what the classifier does and re-run it bit-for-bit.

**Boundary (interpretation vs. certification).** This skill *interprets* a
digest. It never writes anything durable. Two adjacent steps stay on the MCP
server and must NOT be reimplemented here:

- **Obtaining the digest** (`research_session_digest`) is a read against the
  live, privacy-scoped run store — an MCP call.
- **Promoting a candidate lesson into durable policy** — writing it to the
  knowledge graph (`session_backfill_to_kg`) or accepted memory
  (`memory_write`) — is a certified, gated action. Candidate lessons from this
  skill are inputs to that decision, not the decision itself.

## When To Use

- A user asks "what did this session leave open / unfinished / risky?"
- Auditing whether a closed session recorded validation evidence and proper
  logging metadata (`source_client`, final snapshot).
- Converting a single session digest into risk labels and candidate lessons
  before deciding whether any belong in `AGENTS.md`, a skill, or the KG.

For multi-session aggregation, repeated-blocker mining, or writing lessons into
the graph, use the server-side tools (`session_learning_report_generate`,
`session_open_risks_query`, `session_backfill_to_kg`) — those scan the shared
run store and stay on the MCP.

## Inputs

A single research-session digest (the object under the `digest` key of a
`research_session_digest` response). See `references/digest_contract.md` for the
exact fields the heuristics read and how empty fields limit the output.

## Workflow

### Step 1 — Obtain the digest (MCP read)

Call the Brain Researcher MCP tool:

```text
research_session_digest(run_id="<run id>")     # or session_id="<stable session id>"
```

Save the response (or just its `digest` object) to a JSON file. If the MCP
server is unavailable, say so and stop — do not fabricate a digest.

### Step 2 — Sanity-check the digest (optional but recommended)

```bash
python scripts/validate_digest.py /absolute/path/to/digest.json
```

Read `input_limited` in the output. If it is `true`, the digest is empty or
near-empty and any "no risks" result is **input-limited, not a clean session** —
confirm you fetched the right run before trusting the classification.

### Step 3 — Run the heuristics

```bash
# both read-outs (default)
python scripts/session_heuristics.py /absolute/path/to/digest.json

# just risk classification (mirrors session_risk_classify)
python scripts/session_heuristics.py /absolute/path/to/digest.json --mode risk

# just lessons (mirrors session_lesson_extract)
python scripts/session_heuristics.py /absolute/path/to/digest.json --mode lessons
```

The script unwraps a top-level `digest` key automatically, so you can pass the
full MCP response. Output follows `references/output_schema.json`.

Smoke-test with the bundled example:

```bash
python scripts/session_heuristics.py examples/sample_digest.json
```

### Step 4 — Interpret and report

Read the structured output and summarize:

- **`task_surfaces`** — where the session worked (additive; `["other"]` when
  nothing matched).
- **`open_risks`** — each item's canonical label(s). A `pre-existing-debt` label
  with `matched_pattern: false` means "open item that matched no pattern", i.e.
  unclassified, not confidently debt.
- **`hygiene_issues`** — logging/handoff gaps, ordered, each with a severity.
- **`lessons`** — candidate lessons (one per mapped hygiene code).

Report in plain language; name the labels and severities. Do not paste raw JSON
into the final answer unless the user asks.

### Step 5 — Respect the certification boundary

Every lesson is a **candidate** derived from regex classifiers over one
session — not causal evidence. Before any lesson becomes durable policy:

- Confirm it recurs (use the server-side multi-session tools).
- Promote it via the certified path (`session_backfill_to_kg`,
  `memory_write`) — never by editing state locally.

## Reliability Rules

1. The scripts are pure and offline: same digest + same taxonomy → identical
   JSON, no network, no clock, no randomness.
2. Treat every open risk and lesson as heuristic. State that the read-out comes
   from regex classifiers over a session digest, not verified facts.
3. A "clean" result on a sparse digest is input-limited — always cross-check
   with `validate_digest.py`.
4. Do not claim a lesson was recorded, backfilled, or promoted unless a
   certified MCP tool actually did it.
5. Keep outputs in English unless the user asks otherwise.

## Resources

### references/

- `risk_taxonomy.json`: The auditable rule kernel — open-risk labels, all
  regex pattern tables, hygiene checks, and the lesson map. Edit a pattern here
  and the classifier changes deterministically.
- `classification_rules.md`: The deterministic control flow (surface inference,
  evidence dedup, open-risk fallback, hygiene conditions, lesson mapping, stable
  id scheme).
- `digest_contract.md`: The input contract — which digest fields are read and
  how to obtain a digest from `research_session_digest` (an MCP read).
- `output_schema.json`: The output contract for all three script modes.

### scripts/

- `session_heuristics.py`: Deterministic port of `classify_session` +
  `extract_session_lessons`. `python scripts/session_heuristics.py <digest.json>`.
- `validate_digest.py`: Checks a digest against the input contract and flags
  input-limited (near-empty) digests.

### examples/

- `sample_digest.json`: A runnable example digest (full MCP-response form).
