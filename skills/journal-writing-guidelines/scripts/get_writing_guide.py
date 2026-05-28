#!/usr/bin/env python3
"""Return structured writing guidance for a target journal."""

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


def _default_guides_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_writing_guides.yaml"


def _default_examples_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_example_bank.yaml"


def _resolve_journal(journals: dict[str, Any], journal_arg: str) -> tuple[str, dict[str, Any]]:
    if journal_arg in journals:
        return journal_arg, journals[journal_arg]

    lookup = _norm(journal_arg)
    for journal_id, payload in journals.items():
        names = [journal_id, payload.get("name", ""), *payload.get("aliases", [])]
        if any(_norm(str(name)) == lookup for name in names):
            return journal_id, payload

    raise KeyError(f"Unknown journal '{journal_arg}'. Available: {', '.join(sorted(journals))}")


def _normalize_section(section: str | None) -> str | None:
    if not section:
        return None

    aliases = {
        "summary": "abstract",
        "background": "introduction",
        "method": "methods",
        "methodology": "methods",
        "findings": "results",
        "conclusion": "discussion",
    }
    key = section.strip().lower()
    return aliases.get(key, key)


def _safe_examples(payload: dict[str, Any], journal_id: str) -> dict[str, Any]:
    journals = payload.get("journals", {})
    journal_examples = journals.get(journal_id, {}) if isinstance(journals, dict) else {}
    if not isinstance(journal_examples, dict):
        journal_examples = {}

    return {
        "good_patterns": journal_examples.get("good_patterns", []),
        "weak_to_strong_rewrites": journal_examples.get("weak_to_strong_rewrites", []),
        "section_openers": journal_examples.get("section_openers", {}),
    }


def build_writing_guide(
    guides_payload: dict[str, Any],
    examples_payload: dict[str, Any],
    journal: str,
    section: str | None,
) -> dict[str, Any]:
    journals = guides_payload.get("journals", {})
    if not isinstance(journals, dict):
        raise ValueError("Invalid guides payload: journals must be an object.")

    journal_id, journal_cfg = _resolve_journal(journals, journal)
    examples = _safe_examples(examples_payload, journal_id)

    result: dict[str, Any] = {
        "journal_id": journal_id,
        "journal": journal_cfg.get("name", journal_id),
        "positioning": journal_cfg.get("positioning", ""),
        "core_message": journal_cfg.get("core_message", {}),
        "narrative_goals": journal_cfg.get("narrative_goals", {}),
        "claim_ladder": journal_cfg.get("claim_ladder", {}),
        "figure_strategy": journal_cfg.get("figure_strategy", {}),
        "style_rules": journal_cfg.get("style_rules", []),
        "dos": journal_cfg.get("dos", []),
        "donts": journal_cfg.get("donts", []),
        "reviewer_focus": journal_cfg.get("reviewer_focus", []),
        "common_reject_reasons": journal_cfg.get("common_reject_reasons", []),
        "examples": examples,
        "sources": journal_cfg.get("source_refs", []),
    }

    # Optional policy blocks for claim-evidence coherence and terminology control.
    optional_blocks = (
        "reader_translation_rules",
        "evidence_alignment_rules",
        "gate_reporting_rules",
        "figure_language_contract",
        "figure_drawing_workflow",
    )
    for key in optional_blocks:
        if key in journal_cfg:
            result[key] = journal_cfg.get(key)

    section_name = _normalize_section(section)
    if section_name:
        narrative = result["narrative_goals"].get(section_name, {})
        opener = examples.get("section_openers", {}).get(section_name, "")
        result["section_focus"] = {
            "section": section_name,
            "guidance": narrative,
            "example_opener": opener,
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, help="Journal id, name, or alias.")
    parser.add_argument(
        "--section",
        help="Optional section focus (abstract|introduction|methods|results|discussion).",
    )
    parser.add_argument(
        "--guides",
        default=str(_default_guides_path()),
        help="Path to journal_writing_guides.yaml.",
    )
    parser.add_argument(
        "--examples",
        default=str(_default_examples_path()),
        help="Path to journal_example_bank.yaml.",
    )
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()

    guides_path = Path(args.guides).expanduser().resolve()
    examples_path = Path(args.examples).expanduser().resolve()
    if not guides_path.exists():
        raise SystemExit(f"Guide file not found: {guides_path}")
    if not examples_path.exists():
        raise SystemExit(f"Example file not found: {examples_path}")

    guides_payload = yaml.safe_load(guides_path.read_text(encoding="utf-8")) or {}
    examples_payload = yaml.safe_load(examples_path.read_text(encoding="utf-8")) or {}
    result = build_writing_guide(
        guides_payload=guides_payload,
        examples_payload=examples_payload,
        journal=args.journal,
        section=args.section,
    )

    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
