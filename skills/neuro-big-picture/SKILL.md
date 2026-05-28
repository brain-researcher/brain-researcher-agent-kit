---
name: neuro-big-picture
description: Assess neuroscience and NeuroAI research ideas against field-level grand challenges, recent high-signal trends, and expert commentary; then return evidence-backed scoring and next-step recommendations. Use when brainstorming a new idea, checking novelty against recent discourse, validating assumptions with expert/community views, or contextualizing a project in the broader neuroimaging and NeuroAI landscape.
---

# Neuro Big Picture

## Overview

Use this skill to stress-test a neuroscience or NeuroAI idea before committing to a
full experiment or manuscript direction.

Combine:
1. Static worldview constraints from `references/field_manifesto.md`.
2. Dynamic, source-ranked insight gathering from `references/source_registry.yaml`.
3. Deterministic scoring from `scripts/score_insights.py`.

Always return JSON following `references/output_schemas.json`.

## Workflow Decision Tree

1. If user asks for big-picture framing, run worldview-first:
   - Load `references/field_manifesto.md`.
   - Map idea to `references/grand_challenges.yaml`.
2. If user asks for "what people are saying recently", run evidence-first:
   - Load `references/source_registry.yaml` and `references/expert_registry.yaml`.
   - Gather candidate items from Tier A/B/C sources.
3. If user asks for both, run hybrid:
   - Retrieve recent items.
   - Score and rank with `scripts/score_insights.py`.
   - Re-anchor output to grand challenges.

## Step 1: Parse Intent

Extract:
1. Core problem (for example, cross-subject decoding, alignment, interpretability).
2. Method class (for example, contrastive learning, diffusion, foundation model pretraining).
3. Evaluation target (for example, benchmark gain, mechanistic insight, translational use).
4. Preferred perspective if provided:
   - `neuroai_alignment`
   - `method_rigor`
   - `causal_interpretation`
   - `clinical_translation`
   - `open_science`

Use query patterns from `references/query_templates.yaml`.

## Step 2: Select Sources

1. Start with Tier A and Tier B.
2. Add Tier C only in broad mode or when user asks for social signal coverage.
3. Treat social and closed-platform summaries as high-noise unless cross-source support exists.
4. For claims that could change project direction, require at least two independent links.

Use deterministic checks with:

```bash
python skills/neuro-big-picture/scripts/check_sources.py --skip-network
```

## Step 3: Build Candidate Insights

For each candidate item, normalize into:
1. `source_id`, `title`, `url`, `date`.
2. `stance`: `supports`, `questions`, or `mixed`.
3. `mapped_topics` and `mapped_grand_challenges`.
   - Use extensible challenge IDs (`GC1`, `GC2`, ...).
   - Keep IDs aligned with `references/grand_challenges.yaml` when possible.
4. Metric priors in `[0, 1]`:
   - `relevance`
   - `authority`
   - `freshness`
   - `signal_to_noise`
   - `capturability`
   - `novelty`
5. `noise_risk` and `evidence_count`.

## Step 4: Score and Rank

Run:

```bash
python skills/neuro-big-picture/scripts/score_insights.py \
  --input /absolute/path/to/insights.json \
  --mode broad
```

Scoring rules:
1. Base weighted score over six dimensions.
2. Broad mode can add exploration bonus for novel Tier B/C items.
3. High noise risk incurs strong penalties.
4. Cross-source evidence can partially offset noise penalties.
5. Validate `mapped_grand_challenges` in dual-track mode:
   - Regex validation (`^GC[0-9]+$`).
   - Catalog validation against `references/grand_challenges.yaml`.

## Step 5: Produce Output Contract

Return strict JSON matching `consult_neuro_insights_result` in
`references/output_schemas.json`.

Minimum output obligations:
1. Include scored sources and scored insight items.
2. Include `why_it_matters`, `missing_link`, and `next_actions`.
3. Include explicit assumptions when evidence is weak or source quality is mixed.
4. Include grand-challenge diagnostics in summary:
   - `recognized_grand_challenge_ids`
   - `unknown_grand_challenge_ids`
   - `invalid_grand_challenge_ids`

## Reliability Rules

1. Keep all outputs in English unless user explicitly asks another language.
2. Never present source summaries as facts without URL evidence.
3. Mark social-only conclusions with elevated uncertainty.
4. If no relevant recent evidence is found in 120 days, expand to 365 days and disclose fallback.
5. If evidence conflicts, keep both sides and recommend a discriminative experiment.

## Hand-off to Other Skills

After finishing `consult_neuro_insights_result`:
1. Pass ranked grand challenge mapping into `$journal-writing-guidelines` for venue positioning.
2. Reuse `missing_link` as the gap-analysis paragraph for introductions or proposals.

## Resources

### references/

- `field_manifesto.md`: Static worldview and framing constraints.
- `grand_challenges.yaml`: Canonical challenge taxonomy and matching keywords.
- `source_registry.yaml`: Tiered source allowlist and risk metadata.
- `expert_registry.yaml`: Expert profiles and perspective routing.
- `query_templates.yaml`: Query templates by lane and perspective.
- `output_schemas.json`: Required JSON output contract.

### scripts/

- `check_sources.py`: Registry structure and URL health checking.
- `score_insights.py`: Deterministic weighted scoring and ranking.
  - Supports `--grand-challenges` for explicit catalog validation path override.
