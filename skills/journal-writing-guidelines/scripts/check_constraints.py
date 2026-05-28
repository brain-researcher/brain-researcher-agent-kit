#!/usr/bin/env python3
"""Deterministic manuscript constraint checker for journal-writing-guidelines."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit(f"PyYAML is required to run this script: {exc}") from exc


WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?")
HEADER_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

SECTION_ALIASES = {
    "abstract": ["summary"],
    "introduction": ["background"],
    "methods": ["materials and methods", "methodology", "experimental procedures"],
    "results": ["findings"],
    "discussion": ["conclusion", "discussion and conclusion"],
    "references": ["bibliography", "works cited"],
    "related work": ["prior work", "literature review"],
}

DEFAULT_FORBIDDEN_INTERNAL_TERMS = [
    "abs_voxel",
    "residual_voxel",
    "residual_lowrank32",
    "drop_unresolved",
    "keep",
    "b_raw_signed_plus_filteredkg",
]

DEFAULT_FILESYSTEM_PATH_PATTERNS = [
    r"/(?:home|Users|mnt|var|tmp)/[^\s)]+",
    r"[A-Za-z]:\\(?:[^\\\s]+\\)+[^\\\s]*",
]


@dataclass(frozen=True)
class Heading:
    title: str
    norm: str
    level: int
    line: int


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def _parse_markdown(markdown: str) -> tuple[list[Heading], dict[str, list[str]]]:
    lines = markdown.splitlines()
    headings: list[Heading] = []
    sections: dict[str, list[str]] = {}

    for i, line in enumerate(lines):
        match = HEADER_RE.match(line)
        if not match:
            continue
        title = match.group(2).strip()
        headings.append(
            Heading(title=title, norm=_normalize(title), level=len(match.group(1)), line=i)
        )

    if not headings:
        sections["__full_document__"] = [markdown]
        return headings, sections

    for idx, heading in enumerate(headings):
        start = heading.line + 1
        end = len(lines)
        for next_heading in headings[idx + 1 :]:
            # Keep nested subsections inside the parent section.
            if next_heading.level <= heading.level:
                end = next_heading.line
                break
        chunk = "\n".join(lines[start:end]).strip()
        sections.setdefault(heading.norm, []).append(chunk)

    return headings, sections


def _aliases_for(section_name: str) -> list[str]:
    base = _normalize(section_name)
    out = {base}
    for alias in SECTION_ALIASES.get(base, []):
        out.add(_normalize(alias))
    return sorted(out)


def _find_heading_index(headings: list[Heading], section_name: str) -> int | None:
    aliases = set(_aliases_for(section_name))
    for idx, heading in enumerate(headings):
        if heading.norm in aliases:
            return idx
    return None


def _section_text(sections: dict[str, list[str]], section_name: str) -> str:
    aliases = _aliases_for(section_name)
    chunks: list[str] = []
    for alias in aliases:
        chunks.extend(sections.get(alias, []))
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _count_display_items(markdown: str, patterns: list[str]) -> int:
    matches = 0
    for pattern in patterns:
        matches += len(re.findall(pattern, markdown))
    return matches


def _count_references(reference_text: str) -> int:
    if not reference_text.strip():
        return 0
    lines = [line.strip() for line in reference_text.splitlines() if line.strip()]
    if not lines:
        return 0

    matched = 0
    for line in lines:
        if (
            re.match(r"^\[[0-9]+\]\s+", line)
            or re.match(r"^[0-9]+\.\s+", line)
            or re.match(r"^[-*]\s+", line)
        ):
            matched += 1
    if matched > 0:
        return matched

    blocks = [block for block in re.split(r"\n\s*\n", reference_text) if block.strip()]
    return len(blocks)


def _resolve_journal(journals: dict[str, Any], journal_arg: str) -> tuple[str, dict[str, Any]]:
    key = journal_arg.strip()
    if key in journals:
        return key, journals[key]

    lookup = _normalize(journal_arg)
    for journal_id, payload in journals.items():
        names = [payload.get("canonical_name", ""), *payload.get("aliases", [])]
        if any(_normalize(name) == lookup for name in names if isinstance(name, str)):
            return journal_id, payload
    raise KeyError(f"Unknown journal '{journal_arg}'. Available: {', '.join(sorted(journals))}")


def _add_violation(
    violations: list[dict[str, Any]],
    *,
    violation_id: str,
    severity: str,
    field: str,
    message: str,
    found: Any = None,
    expected: Any = None,
    suggestion: str | None = None,
) -> None:
    entry = {
        "id": violation_id,
        "severity": severity,
        "field": field,
        "message": message,
    }
    if found is not None:
        entry["found"] = found
    if expected is not None:
        entry["expected"] = expected
    if suggestion:
        entry["suggestion"] = suggestion
    violations.append(entry)


def _check_range(
    violations: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    *,
    violation_id: str,
    field: str,
    value: int,
    rule: dict[str, Any] | None,
) -> None:
    if not rule:
        return

    minimum = rule.get("min")
    maximum = rule.get("max")
    strict = bool(rule.get("strict", False))

    status = "pass"
    expected: dict[str, int] = {}
    if isinstance(minimum, int):
        expected["min"] = minimum
        if value < minimum:
            status = "fail" if strict else "warning"
            _add_violation(
                violations,
                violation_id=violation_id,
                severity="error" if strict else "warning",
                field=field,
                message=f"{field} is below minimum threshold.",
                found=value,
                expected=expected,
                suggestion=f"Increase {field} content to at least {minimum} words.",
            )
    if isinstance(maximum, int):
        expected["max"] = maximum
        if value > maximum:
            status = "fail" if strict else "warning"
            _add_violation(
                violations,
                violation_id=violation_id,
                severity="error" if strict else "warning",
                field=field,
                message=f"{field} exceeds maximum threshold.",
                found=value,
                expected=expected,
                suggestion=f"Reduce {field} content to at most {maximum} words.",
            )

    checks.append(
        {
            "check": violation_id,
            "status": status,
            "found": value,
            "expected": expected if expected else None,
        }
    )


def evaluate_constraints(
    manuscript_text: str,
    constraints_payload: dict[str, Any],
    journal: str,
    article_type: str,
) -> dict[str, Any]:
    journals = constraints_payload.get("journals", {})
    if not isinstance(journals, dict):
        raise ValueError("Invalid constraints payload: journals must be an object.")

    journal_id, journal_cfg = _resolve_journal(journals, journal)
    article_cfg = (
        journal_cfg.get("article_types", {}).get(article_type)
        if isinstance(journal_cfg.get("article_types"), dict)
        else None
    )
    if not isinstance(article_cfg, dict):
        raise KeyError(f"Unknown article type '{article_type}' for journal '{journal_id}'.")

    headings, sections = _parse_markdown(manuscript_text)
    full_word_count = _count_words(manuscript_text)
    abstract_text = _section_text(sections, "Abstract")
    methods_text = _section_text(sections, "Methods")
    references_text = _section_text(sections, "References")
    abstract_words = _count_words(abstract_text)
    methods_words = _count_words(methods_text)
    references_count = _count_references(references_text)
    main_text_words = max(full_word_count - abstract_words - methods_words, 0)

    detection_cfg = constraints_payload.get("global_detection", {})
    display_patterns = detection_cfg.get("figure_patterns", [])
    if not isinstance(display_patterns, list) or not display_patterns:
        display_patterns = [r"(?im)^\s*(figure|fig\.?|table)\s+[0-9ivxlcdm]+\b"]
    display_items = _count_display_items(manuscript_text, display_patterns)

    violations: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []

    required_sections = article_cfg.get("required_sections", [])
    if not isinstance(required_sections, list):
        required_sections = []
    for section_name in required_sections:
        if not isinstance(section_name, str):
            continue
        idx = _find_heading_index(headings, section_name)
        status = "pass" if idx is not None else "fail"
        checks.append({"check": f"required_section_{_normalize(section_name)}", "status": status})
        if idx is None:
            _add_violation(
                violations,
                violation_id="required_section_missing",
                severity="error",
                field="section_structure",
                message=f"Missing required section: {section_name}.",
                expected=section_name,
                suggestion=f"Add a top-level '{section_name}' section.",
            )

    section_order = article_cfg.get("section_order", [])
    if isinstance(section_order, list) and section_order:
        previous_idx = -1
        order_ok = True
        for section_name in section_order:
            if not isinstance(section_name, str):
                continue
            idx = _find_heading_index(headings, section_name)
            if idx is None:
                continue
            if idx < previous_idx:
                order_ok = False
                _add_violation(
                    violations,
                    violation_id="section_order",
                    severity="error",
                    field="section_order",
                    message=f"Section order violation around '{section_name}'.",
                    expected=section_order,
                    suggestion="Reorder top-level sections to match journal expectations.",
                )
                break
            previous_idx = idx
        checks.append(
            {
                "check": "section_order",
                "status": "pass" if order_ok else "fail",
                "expected": section_order,
            }
        )

    methods_position = article_cfg.get("methods_position")
    methods_idx = _find_heading_index(headings, "Methods")
    results_idx = _find_heading_index(headings, "Results")
    if methods_position in {"before_results", "after_results"} and methods_idx is not None and results_idx is not None:
        ok = methods_idx < results_idx if methods_position == "before_results" else methods_idx > results_idx
        checks.append(
            {
                "check": "methods_position",
                "status": "pass" if ok else "fail",
                "found": {"methods_index": methods_idx, "results_index": results_idx},
                "expected": methods_position,
            }
        )
        if not ok:
            _add_violation(
                violations,
                violation_id="methods_position",
                severity="error",
                field="section_order",
                message="Methods section position does not satisfy journal requirement.",
                found=methods_position,
                expected=methods_position,
                suggestion="Move the Methods section to the required location.",
            )

    _check_range(
        violations,
        checks,
        violation_id="abstract_word_limit",
        field="abstract_word_count",
        value=abstract_words,
        rule=article_cfg.get("abstract_word_limit"),
    )
    _check_range(
        violations,
        checks,
        violation_id="main_text_word_limit",
        field="main_text_word_count",
        value=main_text_words,
        rule=article_cfg.get("main_text_word_limit"),
    )
    _check_range(
        violations,
        checks,
        violation_id="methods_word_limit",
        field="methods_word_count",
        value=methods_words,
        rule=article_cfg.get("methods_word_limit"),
    )

    display_rule = article_cfg.get("display_items_max")
    if isinstance(display_rule, dict) and isinstance(display_rule.get("value"), int):
        max_items = int(display_rule["value"])
        strict = bool(display_rule.get("strict", False))
        status = "pass"
        if display_items > max_items:
            status = "fail" if strict else "warning"
            _add_violation(
                violations,
                violation_id="display_items_max",
                severity="error" if strict else "warning",
                field="display_items",
                message="Display items exceed journal threshold.",
                found=display_items,
                expected={"max": max_items},
                suggestion=f"Reduce main figures/tables to at most {max_items}.",
            )
        checks.append(
            {
                "check": "display_items_max",
                "status": status,
                "found": display_items,
                "expected": {"max": max_items},
            }
        )

    references_rule = article_cfg.get("references_max")
    if isinstance(references_rule, dict) and isinstance(references_rule.get("value"), int):
        max_refs = int(references_rule["value"])
        strict = bool(references_rule.get("strict", False))
        status = "pass"
        if references_count > max_refs:
            status = "fail" if strict else "warning"
            _add_violation(
                violations,
                violation_id="references_max",
                severity="error" if strict else "warning",
                field="reference_count",
                message="Reference count exceeds journal threshold.",
                found=references_count,
                expected={"max": max_refs},
                suggestion=f"Reduce references to at most {max_refs} in the main list.",
            )
        checks.append(
            {
                "check": "references_max",
                "status": status,
                "found": references_count,
                "expected": {"max": max_refs},
            }
        )

    required_subsections = article_cfg.get("required_subsections_in_methods", [])
    if isinstance(required_subsections, list):
        for subsection in required_subsections:
            if not isinstance(subsection, str):
                continue
            present = _normalize(subsection) in _normalize(methods_text)
            checks.append(
                {
                    "check": f"methods_subsection_{_normalize(subsection)}",
                    "status": "pass" if present else "fail",
                }
            )
            if not present:
                _add_violation(
                    violations,
                    violation_id="methods_required_subsection",
                    severity="error",
                    field="methods",
                    message=f"Methods section missing required subsection: {subsection}.",
                    expected=subsection,
                    suggestion=f"Add a clear '{subsection}' subsection in Methods.",
                )

    keyword_requirements = article_cfg.get("required_sections_or_keywords", [])
    if isinstance(keyword_requirements, list):
        for keyword in keyword_requirements:
            if not isinstance(keyword, str):
                continue
            present = _normalize(keyword) in _normalize(manuscript_text)
            checks.append(
                {
                    "check": f"required_keyword_{_normalize(keyword)}",
                    "status": "pass" if present else "warning",
                }
            )
            if not present:
                warnings.append(f"Recommended keyword/section not found: {keyword}.")

    if article_cfg.get("architecture_figure_required"):
        if not re.search(r"(?i)architecture|pipeline", manuscript_text):
            warnings.append("No explicit architecture/pipeline mention found.")
            checks.append(
                {"check": "architecture_figure_required", "status": "warning"}
            )
        else:
            checks.append({"check": "architecture_figure_required", "status": "pass"})

    normalized_doc = _normalize(manuscript_text)

    forbidden_internal = detection_cfg.get("forbidden_internal_terms", DEFAULT_FORBIDDEN_INTERNAL_TERMS)
    if not isinstance(forbidden_internal, list):
        forbidden_internal = DEFAULT_FORBIDDEN_INTERNAL_TERMS
    internal_hits = sorted(
        {
            term
            for term in forbidden_internal
            if isinstance(term, str) and term and _normalize(term) in normalized_doc
        }
    )
    if internal_hits:
        checks.append(
            {
                "check": "no_internal_labels_in_main_text",
                "status": "warning",
                "found": internal_hits,
            }
        )
        _add_violation(
            violations,
            violation_id="internal_label_leak",
            severity="warning",
            field="terminology",
            message="Detected internal/code-like labels in manuscript text.",
            found=internal_hits,
            suggestion="Replace internal labels with reader-facing scientific terms.",
        )
    else:
        checks.append({"check": "no_internal_labels_in_main_text", "status": "pass"})

    path_patterns = detection_cfg.get("filesystem_path_patterns", DEFAULT_FILESYSTEM_PATH_PATTERNS)
    if not isinstance(path_patterns, list):
        path_patterns = DEFAULT_FILESYSTEM_PATH_PATTERNS
    path_hits: list[str] = []
    for pattern in path_patterns:
        if not isinstance(pattern, str) or not pattern:
            continue
        for match in re.finditer(pattern, manuscript_text):
            token = match.group(0)
            path_hits.append(token)
            if len(path_hits) >= 5:
                break
        if len(path_hits) >= 5:
            break
    if path_hits:
        checks.append(
            {
                "check": "no_filesystem_paths_in_main_text",
                "status": "warning",
                "found": path_hits,
            }
        )
        _add_violation(
            violations,
            violation_id="filesystem_path_leak",
            severity="warning",
            field="manuscript_text",
            message="Filesystem paths detected in manuscript body text.",
            found=path_hits,
            suggestion="Move engineering paths to reproducibility notes or remove from main narrative.",
        )
    else:
        checks.append({"check": "no_filesystem_paths_in_main_text", "status": "pass"})

    has_loto = bool(re.search(r"(?i)\bLOTO\b|leave[- ]one[- ]task[- ]out", manuscript_text))
    has_lotfo = bool(re.search(r"(?i)leave[- ]one[- ]task[- ]family[- ]out", manuscript_text))
    if has_loto and has_lotfo:
        clarifier = bool(re.search(r"(?i)folds?\s+are\s+defined\s+by\s+.*task[- ]family", manuscript_text))
        status = "pass" if clarifier else "warning"
        checks.append(
            {
                "check": "fold_term_consistency",
                "status": status,
                "found": ["LOTO", "leave-one-task-family-out"],
            }
        )
        if not clarifier:
            _add_violation(
                violations,
                violation_id="fold_term_consistency",
                severity="warning",
                field="evaluation_definition",
                message="Both LOTO and leave-one-task-family-out appear without explicit reconciliation.",
                suggestion="Add one sentence that defines folds unambiguously and keep naming consistent.",
            )
    else:
        checks.append({"check": "fold_term_consistency", "status": "pass"})

    definition_warnings: list[str] = []
    if re.search(r"(?i)\bcombo(s)?\b", manuscript_text):
        if not re.search(
            r"(?i)combo\s*(=|:|is|means)|\(\s*task_raw\s*,\s*contrast",
            manuscript_text,
        ):
            definition_warnings.append("combo")
    if re.search(r"(?i)ontology[- ]mapped|ontology[- ]unmapped", manuscript_text):
        if not re.search(r"(?i)ontology[- ]mapped.*(if|when|defined|means)", manuscript_text):
            definition_warnings.append("ontology-mapped status")
    if re.search(r"(?i)\bgate\b", manuscript_text):
        if not re.search(r"(?i)not a null[- ]hypothesis test|not.*significance", manuscript_text):
            definition_warnings.append("gate interpretation")

    if definition_warnings:
        checks.append(
            {
                "check": "mandatory_definitions_present",
                "status": "warning",
                "found": definition_warnings,
            }
        )
        _add_violation(
            violations,
            violation_id="mandatory_definitions_missing",
            severity="warning",
            field="definitions",
            message="Some high-impact terms appear without explicit definitions.",
            found=definition_warnings,
            suggestion="Add a Definitions paragraph with reproducible term definitions.",
        )
    else:
        checks.append({"check": "mandatory_definitions_present", "status": "pass"})

    has_split = bool(
        re.search(r"(?i)ontology[- ]mapped", manuscript_text)
        and re.search(r"(?i)ontology[- ]unmapped", manuscript_text)
    )
    has_adjusted = bool(re.search(r"(?i)composition[- ]adjusted|adjusted model|cluster-robust", manuscript_text))
    has_attenuation_disclosure = bool(
        re.search(r"(?i)attenuat|bounded interpretation|associational|cannot establish causal", manuscript_text)
    )
    if has_split:
        if not has_adjusted:
            checks.append(
                {
                    "check": "raw_adjusted_conflict_disclosure_required",
                    "status": "warning",
                }
            )
            _add_violation(
                violations,
                violation_id="raw_adjusted_conflict_disclosure",
                severity="warning",
                field="results_discussion",
                message="Mapped-vs-unmapped split is reported without an adjusted/composition-aware disclosure.",
                suggestion="Add adjusted-model results or explicitly justify why adjustment is not available.",
            )
        elif not has_attenuation_disclosure:
            checks.append(
                {
                    "check": "raw_adjusted_conflict_disclosure_required",
                    "status": "warning",
                }
            )
            _add_violation(
                violations,
                violation_id="raw_adjusted_conflict_disclosure",
                severity="warning",
                field="results_discussion",
                message="Adjusted analysis appears but attenuation/bounded-claim disclosure is missing.",
                suggestion="Explicitly state whether adjusted estimates attenuate and bound claim strength accordingly.",
            )
        else:
            checks.append(
                {
                    "check": "raw_adjusted_conflict_disclosure_required",
                    "status": "pass",
                }
            )
    else:
        checks.append(
            {
                "check": "raw_adjusted_conflict_disclosure_required",
                "status": "pass",
            }
        )

    auto_fix_suggestions = sorted(
        {
            item["suggestion"]
            for item in violations
            if item.get("suggestion") and isinstance(item.get("suggestion"), str)
        }
    )
    manual_required = []
    if not references_text.strip():
        manual_required.append("Reference section parsing needs manual verification.")
    if not headings:
        manual_required.append("No markdown headings found; structure checks are weak.")

    pass_fail = "fail" if any(v["severity"] == "error" for v in violations) else "pass"

    return {
        "journal_id": journal_id,
        "article_type": article_type,
        "pass_fail": pass_fail,
        "summary": {
            "full_word_count": full_word_count,
            "abstract_word_count": abstract_words,
            "methods_word_count": methods_words,
            "main_text_word_count": main_text_words,
            "display_item_count": display_items,
            "reference_count": references_count,
        },
        "violations": violations,
        "warnings": warnings,
        "checks": checks,
        "auto_fix_suggestions": auto_fix_suggestions,
        "manual_required": manual_required,
    }


def _default_constraints_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_constraints.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", required=True, help="Path to markdown manuscript.")
    parser.add_argument("--journal", required=True, help="Journal id or canonical name.")
    parser.add_argument(
        "--article-type", default="research_article", help="Article type in constraints file."
    )
    parser.add_argument(
        "--constraints",
        default=str(_default_constraints_path()),
        help="Path to journal_constraints.yaml.",
    )
    parser.add_argument("--output", help="Optional output JSON path.")
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="Exit with non-zero status when pass_fail is fail.",
    )
    args = parser.parse_args()

    manuscript_path = Path(args.manuscript).expanduser().resolve()
    constraints_path = Path(args.constraints).expanduser().resolve()
    if not manuscript_path.exists():
        raise SystemExit(f"Manuscript file not found: {manuscript_path}")
    if not constraints_path.exists():
        raise SystemExit(f"Constraints file not found: {constraints_path}")

    manuscript_text = manuscript_path.read_text(encoding="utf-8")
    constraints_payload = yaml.safe_load(constraints_path.read_text(encoding="utf-8")) or {}
    result = evaluate_constraints(
        manuscript_text=manuscript_text,
        constraints_payload=constraints_payload,
        journal=args.journal,
        article_type=args.article_type,
    )

    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

    if args.fail_on_violations and result["pass_fail"] == "fail":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
