#!/usr/bin/env python3
"""Validate consistency across journal writing guideline reference files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit(f"PyYAML is required to run this script: {exc}") from exc


REQUIRED_GUIDE_FIELDS = {
    "name",
    "aliases",
    "source_refs",
    "positioning",
    "core_message",
    "narrative_goals",
    "claim_ladder",
    "figure_strategy",
    "style_rules",
    "dos",
    "donts",
    "reviewer_focus",
    "common_reject_reasons",
}

REQUIRED_NARRATIVE_SECTIONS = {"abstract", "introduction", "methods", "results", "discussion"}


def _default_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[1] / "references" / filename


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _collect_ids(payload: dict[str, Any], key: str = "journals") -> set[str]:
    container = payload.get(key, {})
    if not isinstance(container, dict):
        return set()
    return set(container.keys())


def validate(
    guides_payload: dict[str, Any],
    profiles_payload: dict[str, Any],
    constraints_payload: dict[str, Any],
    examples_payload: dict[str, Any],
    sources_payload: dict[str, Any],
    templates_payload: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    guides = guides_payload.get("journals", {})
    profiles = profiles_payload.get("journals", {})
    constraints = constraints_payload.get("journals", {})
    examples = examples_payload.get("journals", {})
    sources = sources_payload.get("sources", {})
    templates = templates_payload.get("journals", {})

    if not isinstance(guides, dict):
        raise ValueError("journal_writing_guides.yaml: journals must be an object")
    if not isinstance(profiles, dict):
        raise ValueError("journal_profiles.yaml: journals must be an object")
    if not isinstance(constraints, dict):
        raise ValueError("journal_constraints.yaml: journals must be an object")
    if not isinstance(examples, dict):
        raise ValueError("journal_example_bank.yaml: journals must be an object")
    if not isinstance(sources, dict):
        raise ValueError("source_registry.yaml: sources must be an object")
    if not isinstance(templates, dict):
        raise ValueError("templates_manifest.yaml: journals must be an object")

    guide_ids = set(guides)
    profile_ids = set(profiles)
    constraint_ids = set(constraints)
    example_ids = set(examples)
    template_ids = set(templates)
    source_ids = set(sources)

    for label, ids in (
        ("profiles", profile_ids),
        ("constraints", constraint_ids),
        ("examples", example_ids),
    ):
        missing = sorted(guide_ids - ids)
        extra = sorted(ids - guide_ids)
        if missing:
            errors.append(f"{label} missing journal ids: {', '.join(missing)}")
        if extra:
            errors.append(f"{label} has unknown journal ids: {', '.join(extra)}")

    unknown_template_ids = sorted(template_ids - guide_ids)
    if unknown_template_ids:
        errors.append(
            "templates manifest has journal ids not present in guides: "
            + ", ".join(unknown_template_ids)
        )

    for journal_id, guide in guides.items():
        if not isinstance(guide, dict):
            errors.append(f"{journal_id}: guide entry must be an object")
            continue

        missing_fields = sorted(REQUIRED_GUIDE_FIELDS - set(guide.keys()))
        if missing_fields:
            errors.append(f"{journal_id}: missing required fields: {', '.join(missing_fields)}")

        narrative = guide.get("narrative_goals", {})
        if not isinstance(narrative, dict):
            errors.append(f"{journal_id}: narrative_goals must be an object")
        else:
            missing_sections = sorted(REQUIRED_NARRATIVE_SECTIONS - set(narrative.keys()))
            if missing_sections:
                errors.append(
                    f"{journal_id}: narrative_goals missing sections: {', '.join(missing_sections)}"
                )

        refs = guide.get("source_refs", [])
        if not isinstance(refs, list):
            errors.append(f"{journal_id}: source_refs must be a list")
        else:
            bad_refs = [ref for ref in refs if ref not in source_ids]
            if bad_refs:
                errors.append(
                    f"{journal_id}: source_refs not in source_registry: {', '.join(sorted(bad_refs))}"
                )

        figure_strategy = guide.get("figure_strategy", {})
        main_figures = figure_strategy.get("main_figures", {}) if isinstance(figure_strategy, dict) else {}
        if not isinstance(main_figures, dict):
            errors.append(f"{journal_id}: figure_strategy.main_figures must be an object")
            continue

        try:
            fig_min = int(main_figures.get("min"))
            fig_target = int(main_figures.get("target"))
            fig_max = int(main_figures.get("max"))
        except Exception:
            errors.append(f"{journal_id}: main_figures must provide integer min/target/max")
            continue

        if not (fig_min <= fig_target <= fig_max):
            errors.append(
                f"{journal_id}: main_figures must satisfy min <= target <= max (got {fig_min}, {fig_target}, {fig_max})"
            )

        arc = figure_strategy.get("figure_story_arc", []) if isinstance(figure_strategy, dict) else []
        if not isinstance(arc, list):
            errors.append(f"{journal_id}: figure_story_arc must be a list")
        else:
            if len(arc) < fig_target:
                warnings.append(
                    f"{journal_id}: figure_story_arc has {len(arc)} slots, less than target={fig_target}"
                )
            slots: list[int] = []
            for idx, slot in enumerate(arc):
                if not isinstance(slot, dict):
                    errors.append(f"{journal_id}: figure_story_arc[{idx}] must be an object")
                    continue
                for key in ("slot", "title", "purpose", "must_include"):
                    if key not in slot:
                        errors.append(f"{journal_id}: figure_story_arc[{idx}] missing '{key}'")
                if isinstance(slot.get("slot"), int):
                    slots.append(int(slot["slot"]))
            if slots and slots != sorted(slots):
                warnings.append(f"{journal_id}: figure_story_arc slots are not sorted ascending")

        constraint_cfg = constraints.get(journal_id, {})
        article_cfg = (
            constraint_cfg.get("article_types", {}).get("research_article")
            if isinstance(constraint_cfg, dict)
            else None
        )
        if isinstance(article_cfg, dict):
            display = article_cfg.get("display_items_max")
            if isinstance(display, dict) and isinstance(display.get("value"), int):
                limit = int(display["value"])
                if fig_target > limit or fig_max > limit:
                    errors.append(
                        f"{journal_id}: figure target/max exceed display_items_max ({fig_target}/{fig_max} > {limit})"
                    )

    pass_fail = "fail" if errors else "pass"
    return {
        "pass_fail": pass_fail,
        "summary": {
            "guide_journal_count": len(guide_ids),
            "profile_journal_count": len(profile_ids),
            "constraint_journal_count": len(constraint_ids),
            "example_journal_count": len(example_ids),
            "template_journal_count": len(template_ids),
            "source_count": len(source_ids),
        },
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--guides",
        default=str(_default_path("journal_writing_guides.yaml")),
        help="Path to journal_writing_guides.yaml.",
    )
    parser.add_argument(
        "--profiles",
        default=str(_default_path("journal_profiles.yaml")),
        help="Path to journal_profiles.yaml.",
    )
    parser.add_argument(
        "--constraints",
        default=str(_default_path("journal_constraints.yaml")),
        help="Path to journal_constraints.yaml.",
    )
    parser.add_argument(
        "--examples",
        default=str(_default_path("journal_example_bank.yaml")),
        help="Path to journal_example_bank.yaml.",
    )
    parser.add_argument(
        "--sources",
        default=str(_default_path("source_registry.yaml")),
        help="Path to source_registry.yaml.",
    )
    parser.add_argument(
        "--templates",
        default=str(_default_path("templates_manifest.yaml")),
        help="Path to templates_manifest.yaml.",
    )
    parser.add_argument("--output", help="Optional output JSON path.")
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit non-zero when validation fails.",
    )
    args = parser.parse_args()

    guides_payload = _load_yaml(Path(args.guides).expanduser().resolve())
    profiles_payload = _load_yaml(Path(args.profiles).expanduser().resolve())
    constraints_payload = _load_yaml(Path(args.constraints).expanduser().resolve())
    examples_payload = _load_yaml(Path(args.examples).expanduser().resolve())
    sources_payload = _load_yaml(Path(args.sources).expanduser().resolve())
    templates_payload = _load_yaml(Path(args.templates).expanduser().resolve())

    result = validate(
        guides_payload=guides_payload,
        profiles_payload=profiles_payload,
        constraints_payload=constraints_payload,
        examples_payload=examples_payload,
        sources_payload=sources_payload,
        templates_payload=templates_payload,
    )

    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

    if args.fail_on_error and result["pass_fail"] == "fail":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
