---
name: journal-writing-guidelines
description: End-to-end journal writing playbook for neuroscience, neuroimaging, and medical imaging papers. Use this skill to route ideas to target journals, retrieve journal-specific writing guidance, plan figure storylines, enforce hard manuscript constraints, rewrite sections in journal tone, and fetch venue templates.
---

# Journal Writing Guidelines

## Overview

Use this skill when you need more than venue routing. The default behavior is:
1. Route idea to candidate journals.
2. Pull journal-specific writing guidance.
3. Plan figure narrative and count budget.
4. Enforce hard formatting constraints.
5. Rewrite requested sections with target-journal tone.
6. Resolve templates (LaTeX/Word) from local manifest.

All outputs should be strict JSON and follow `references/output_schemas.json`.
For communication with collaborators, prefer plain wording:
1. "schema" -> "output format".
2. "audit" -> "logic consistency check".

## Core References

Load only what is needed:
1. `references/journal_profiles.yaml`: scope and audience fit signals.
2. `references/journal_constraints.yaml`: hard structure and count constraints.
3. `references/journal_writing_guides.yaml`: per-journal writing playbook.
4. `references/journal_example_bank.yaml`: paraphrased writing examples.
5. `references/few_shot_examples.md`: idea-fit reasoning calibration.
6. `references/output_schemas.json`: output contracts.
7. `references/templates_manifest.yaml`: local template registry.
8. `references/source_registry.yaml`: guideline provenance and confidence.
9. `references/failure_localization_templates.yaml`: conditional/failure-localization narrative templates.
10. `references/nomenclature_translation_bank.yaml`: code-term to reader-term translation bank.
11. `references/claim_strength_decision_table.yaml`: claim verb strength by evidence state.
12. `references/figure_drawing_workflow.yaml`: figure production workflow and QA checklist.

## Task A: Evaluate Idea Fit

Goal: return ranked journal fit and upgrade actions.

Output schema: `evaluate_idea_fit_result`.

Minimum output:
1. `analysis` over biological insight, method novelty, clinical relevance, open-science readiness, audience fit.
2. Ranked `journal_matches` with `gating_risks` and `priority_actions`.
3. `top_journal`, `gap_to_next_tier`, and short recommendation summary.

## Task B: Get Journal Writing Guide

Goal: return actionable writing guidance for a target journal.

Output schema: `get_journal_writing_guide_result`.

Includes:
1. Positioning and core message.
2. Section-level narrative goals.
3. Claim ladder (conservative -> strong).
4. Figure strategy and supplement priorities.
5. Style rules, dos/donts, reviewer focus, common reject triggers.
6. Paraphrased examples from local example bank.

Deterministic command:

```bash
python skills/journal-writing-guidelines/scripts/get_writing_guide.py \
  --journal imaging_neuroscience \
  --section abstract
```

## Task C: Plan Figure Strategy

Goal: turn journal expectations into a concrete figure storyline.

Output schema: `plan_figure_strategy_result`.

Deterministic command:

```bash
python skills/journal-writing-guidelines/scripts/plan_figure_strategy.py \
  --journal medical_image_analysis \
  --article-type research_article \
  --manuscript /absolute/path/to/draft.md
```

## Task D: Manuscript Format Check (Hard Rules)

Goal: check hard constraints before major rewriting.

Output schema: `enforce_journal_schema_result`.

Deterministic command:

```bash
python skills/journal-writing-guidelines/scripts/check_constraints.py \
  --manuscript /absolute/path/to/draft.md \
  --journal nature_neuroscience \
  --article-type research_article
```

## Task E: Rewrite for Target Journal

Goal: rewrite requested sections while preserving factual claims.

Output schema: `rewrite_for_journal_result`.

Rules:
1. Rewrite only requested sections unless full rewrite is explicitly requested.
2. Do not add unverifiable new claims.
3. Never suppress known violations from Task D.
4. Include explicit risk flags when claims outrun evidence.

## Task F: Route + Guide Combined Output

Use when user asks for one-shot planning.

Output schema: `route_and_guide_result`.

Deterministic command:

```bash
python skills/journal-writing-guidelines/scripts/route_and_guide.py \
  --idea "Cross-subject fMRI alignment with robust ablations and open-source release." \
  --section abstract \
  --top-k 5
```

## Task G: Template Fetch

List manifest:

```bash
bash skills/journal-writing-guidelines/scripts/fetch_templates.sh --list
```

Preview fetch:

```bash
bash skills/journal-writing-guidelines/scripts/fetch_templates.sh \
  --journal imaging_neuroscience \
  --format latex \
  --dry-run
```

Fetch direct entry:

```bash
bash skills/journal-writing-guidelines/scripts/fetch_templates.sh \
  --journal ieee_tmi \
  --format latex
```

## Task H: Story Logic Check (Pre-submission)

Goal: run a deterministic logic consistency check before submission-facing rewrites.

Output schema: `story_coherence_audit_result`.

Deterministic command:

```bash
python skills/journal-writing-guidelines/scripts/check_story_coherence.py \
  --manuscript /absolute/path/to/draft.md \
  --journal imaging_neuroscience
```

Checks include:
1. Claim-evidence alignment.
2. Terminology consistency (no internal labels in prose).
3. Separation of operational gate language from inferential language.
4. Figure caption/body wording consistency.
5. Main-text vs supplement caveat placement.

## Task I: Figure Production Workflow (NanoBanana)

Goal: produce publication-ready figures with consistent labels, low typo risk, and caption-text alignment.

Recommended two-pass workflow:
1. Structure pass: lock layout, panel order, axes, and visual hierarchy before adding dense text.
2. Text pass: add short labels, then legends/captions, then final number overlays.

Minimum process:
1. Draft one message sentence per figure panel.
2. Build a label dictionary (reader-facing terms only).
3. Generate prompt pack with shared style constraints.
4. Run generation and pick candidates.
5. Run figure QA checklist (term consistency, thresholds, sign, dataset naming).
6. Sync figure labels with caption and Results opening sentences.

Use references:
1. `references/figure_drawing_workflow.yaml`
2. `references/nomenclature_translation_bank.yaml`
3. `references/journal_writing_guides.yaml` -> `figure_language_contract`

## Validation and Maintenance

Validate cross-file consistency:

```bash
python skills/journal-writing-guidelines/scripts/validate_guides.py --fail-on-error
```

Check source health:

```bash
python skills/journal-writing-guidelines/scripts/check_sources.py
```

If source pages change, update:
1. `references/source_registry.yaml`
2. `references/journal_constraints.yaml`
3. `references/journal_writing_guides.yaml`
4. `references/templates_manifest.yaml`

## Reliability Rules

1. Keep output language in English unless user asks otherwise.
2. Treat high-confidence constraints as hard requirements.
3. Mark medium/low-confidence constraints as uncertain.
4. Prefer official guideline URLs over curated heuristics on conflicts.
5. Keep machine-readable fields complete; do not drop required keys.

## Scripts

1. `check_constraints.py`: deterministic manuscript checker.
2. `check_sources.py`: URL health and provenance checks.
3. `fetch_templates.sh`: list/fetch local manifest template entries.
4. `get_writing_guide.py`: fetch journal writing playbook JSON.
5. `plan_figure_strategy.py`: generate figure arc + count budget plan.
6. `route_and_guide.py`: one-shot idea fit + writing guide + figure plan output.
7. `validate_guides.py`: consistency checks across references.
8. `check_story_coherence.py`: deterministic claim/terminology/figure-consistency logic check.
