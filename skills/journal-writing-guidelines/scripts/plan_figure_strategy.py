#!/usr/bin/env python3
"""Generate a journal-specific figure storyline and count budget."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit(f"PyYAML is required to run this script: {exc}") from exc


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _default_constraints_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_constraints.yaml"


def _default_guides_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_writing_guides.yaml"


def _resolve_journal_from_guides(guides: dict[str, Any], journal_arg: str) -> tuple[str, dict[str, Any]]:
    if journal_arg in guides:
        return journal_arg, guides[journal_arg]

    lookup = _norm(journal_arg)
    for journal_id, payload in guides.items():
        names = [journal_id, payload.get("name", ""), *payload.get("aliases", [])]
        if any(_norm(str(name)) == lookup for name in names):
            return journal_id, payload

    raise KeyError(f"Unknown journal '{journal_arg}'. Available: {', '.join(sorted(guides))}")


def _resolve_journal_from_constraints(
    constraints: dict[str, Any], journal_arg: str
) -> tuple[str, dict[str, Any]]:
    journals = constraints.get("journals", {})
    if not isinstance(journals, dict):
        raise ValueError("Invalid constraints payload: journals must be an object.")

    if journal_arg in journals:
        return journal_arg, journals[journal_arg]

    lookup = _norm(journal_arg)
    for journal_id, payload in journals.items():
        names = [
            journal_id,
            payload.get("canonical_name", ""),
            *payload.get("aliases", []),
        ]
        if any(_norm(str(name)) == lookup for name in names):
            return journal_id, payload

    raise KeyError(f"Unknown journal '{journal_arg}'. Available: {', '.join(sorted(journals))}")


def _count_display_items(markdown: str, patterns: list[str]) -> int:
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, markdown))
    return total


def build_figure_plan(
    guides_payload: dict[str, Any],
    constraints_payload: dict[str, Any],
    journal: str,
    article_type: str,
    manuscript_text: str | None,
) -> dict[str, Any]:
    guides = guides_payload.get("journals", {})
    if not isinstance(guides, dict):
        raise ValueError("Invalid guides payload: journals must be an object.")

    journal_id, guide_cfg = _resolve_journal_from_guides(guides, journal)
    _, constraint_cfg = _resolve_journal_from_constraints(constraints_payload, journal_id)

    article_cfg = constraint_cfg.get("article_types", {}).get(article_type)
    if not isinstance(article_cfg, dict):
        raise KeyError(f"Unknown article type '{article_type}' for journal '{journal_id}'.")

    figure_strategy = guide_cfg.get("figure_strategy", {})
    main_figures = figure_strategy.get("main_figures", {})
    story_arc = figure_strategy.get("figure_story_arc", [])
    supplement_priority = figure_strategy.get("supplement_priority", [])
    figure_language_contract = guide_cfg.get("figure_language_contract", {})
    reader_translation_rules = guide_cfg.get("reader_translation_rules", {})
    figure_drawing_workflow = guide_cfg.get("figure_drawing_workflow", {})

    recommended_main_figures = {
        "min": int(main_figures.get("min", 4)),
        "target": int(main_figures.get("target", 6)),
        "max": int(main_figures.get("max", 8)),
    }

    target_slots = recommended_main_figures["target"]
    recommended_slots = story_arc[:target_slots] if isinstance(story_arc, list) else []

    display_rule = article_cfg.get("display_items_max")
    journal_limit = None
    if isinstance(display_rule, dict) and isinstance(display_rule.get("value"), int):
        journal_limit = int(display_rule["value"])

    detected_count = None
    if manuscript_text is not None:
        detection_cfg = constraints_payload.get("global_detection", {})
        patterns = detection_cfg.get("figure_patterns", [])
        if not isinstance(patterns, list) or not patterns:
            patterns = [r"(?im)^\s*(figure|fig\.?|table)\s+[0-9ivxlcdm]+\b"]
        detected_count = _count_display_items(manuscript_text, patterns)

    if journal_limit is None:
        compliance = {
            "status": "no_limit",
            "journal_limit": None,
            "detected_count": detected_count,
            "suggestion": "No explicit hard figure cap in constraints; follow target count from guide.",
        }
    elif detected_count is None:
        compliance = {
            "status": "unknown",
            "journal_limit": journal_limit,
            "detected_count": None,
            "suggestion": "Provide --manuscript to compare current draft against journal limit.",
        }
    elif detected_count <= journal_limit:
        compliance = {
            "status": "within_limit",
            "journal_limit": journal_limit,
            "detected_count": detected_count,
            "suggestion": "Current draft is within journal figure limit.",
        }
    else:
        overflow = detected_count - journal_limit
        compliance = {
            "status": "exceeds_limit",
            "journal_limit": journal_limit,
            "detected_count": detected_count,
            "suggestion": f"Reduce at least {overflow} display item(s) from the main manuscript.",
        }

    panel_label_dictionary = {}
    if isinstance(figure_language_contract, dict):
        canonical_terms = figure_language_contract.get("canonical_terms", {})
        if isinstance(canonical_terms, dict):
            panel_label_dictionary = canonical_terms

    forbidden_terms: list[str] = []
    if isinstance(reader_translation_rules, dict):
        raw_forbidden = reader_translation_rules.get("forbidden_terms", [])
        if isinstance(raw_forbidden, list):
            forbidden_terms = [str(x) for x in raw_forbidden if isinstance(x, str)]

    legend_alignment_notes: list[str] = []
    if isinstance(figure_language_contract, dict):
        notes = figure_language_contract.get("legend_alignment_notes", [])
        if isinstance(notes, list):
            legend_alignment_notes = [str(x) for x in notes if isinstance(x, str)]

    main_text_anchor_sentence: list[str] = []
    for slot in recommended_slots:
        if not isinstance(slot, dict):
            continue
        slot_id = slot.get("slot")
        purpose = str(slot.get("purpose", "")).strip()
        title = str(slot.get("title", "")).strip()
        if not purpose:
            continue
        label = f"Figure {slot_id}" if isinstance(slot_id, int) else "This figure"
        if title:
            main_text_anchor_sentence.append(
                f"{label} ({title}) addresses: {purpose}"
            )
        else:
            main_text_anchor_sentence.append(f"{label} addresses: {purpose}")

    return {
        "journal_id": journal_id,
        "article_type": article_type,
        "recommended_main_figures": recommended_main_figures,
        "recommended_figure_slots": recommended_slots,
        "supplement_suggestions": supplement_priority,
        "panel_label_dictionary": panel_label_dictionary,
        "forbidden_terms": forbidden_terms,
        "legend_alignment_notes": legend_alignment_notes,
        "main_text_anchor_sentence": main_text_anchor_sentence,
        "figure_drawing_workflow": figure_drawing_workflow,
        "compliance_check": compliance,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, help="Journal id, canonical name, or alias.")
    parser.add_argument(
        "--article-type",
        default="research_article",
        help="Article type from journal_constraints.yaml.",
    )
    parser.add_argument("--manuscript", help="Optional manuscript markdown path to evaluate current figure count.")
    parser.add_argument(
        "--guides",
        default=str(_default_guides_path()),
        help="Path to journal_writing_guides.yaml.",
    )
    parser.add_argument(
        "--constraints",
        default=str(_default_constraints_path()),
        help="Path to journal_constraints.yaml.",
    )
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()

    guides_path = Path(args.guides).expanduser().resolve()
    constraints_path = Path(args.constraints).expanduser().resolve()
    if not guides_path.exists():
        raise SystemExit(f"Guide file not found: {guides_path}")
    if not constraints_path.exists():
        raise SystemExit(f"Constraints file not found: {constraints_path}")

    manuscript_text = None
    if args.manuscript:
        manuscript_path = Path(args.manuscript).expanduser().resolve()
        if not manuscript_path.exists():
            raise SystemExit(f"Manuscript file not found: {manuscript_path}")
        manuscript_text = manuscript_path.read_text(encoding="utf-8")

    guides_payload = yaml.safe_load(guides_path.read_text(encoding="utf-8")) or {}
    constraints_payload = yaml.safe_load(constraints_path.read_text(encoding="utf-8")) or {}

    result = build_figure_plan(
        guides_payload=guides_payload,
        constraints_payload=constraints_payload,
        journal=args.journal,
        article_type=args.article_type,
        manuscript_text=manuscript_text,
    )

    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
