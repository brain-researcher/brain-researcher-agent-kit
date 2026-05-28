#!/usr/bin/env python3
"""Audit manuscript story coherence for claim, terminology, and figure-text alignment."""

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


def _default_guides_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_writing_guides.yaml"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _resolve_journal(guides: dict[str, Any], journal_arg: str) -> tuple[str, dict[str, Any]]:
    if journal_arg in guides:
        return journal_arg, guides[journal_arg]

    lookup = _norm(journal_arg)
    for journal_id, payload in guides.items():
        names = [journal_id, payload.get("name", ""), *payload.get("aliases", [])]
        if any(_norm(str(name)) == lookup for name in names):
            return journal_id, payload
    raise KeyError(f"Unknown journal '{journal_arg}'. Available: {', '.join(sorted(guides))}")


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [c.strip() for c in chunks if c.strip()]


def _append_violation(
    violations: list[dict[str, Any]],
    *,
    violation_id: str,
    severity: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    violations.append(
        {
            "id": violation_id,
            "severity": severity,
            "message": message,
            "details": details,
        }
    )


def _extract_figure_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if re.search(r"(?i)^\s*(figure|fig\.?)\s*[0-9ivxlcdm]+", line):
            out.append(line.strip())
    return out


def _load_fig_map(fig_map_path: Path | None) -> dict[str, Any]:
    if fig_map_path is None:
        return {}
    if not fig_map_path.exists():
        raise FileNotFoundError(f"Figure term map not found: {fig_map_path}")
    payload = yaml.safe_load(fig_map_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Figure term map must be a YAML object.")
    return payload


def audit_story_coherence(
    manuscript_text: str,
    journal_id: str,
    journal_cfg: dict[str, Any],
    fig_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fig_map = fig_map or {}
    normalized_doc = _normalize(manuscript_text)
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []
    risk_flags: set[str] = set()

    reader_rules = journal_cfg.get("reader_translation_rules", {})
    figure_contract = journal_cfg.get("figure_language_contract", {})

    forbidden_terms = []
    if isinstance(reader_rules, dict):
        forbidden_terms = [str(x) for x in reader_rules.get("forbidden_terms", []) if isinstance(x, str)]

    disallowed_aliases = []
    if isinstance(figure_contract, dict):
        disallowed_aliases = [
            str(x) for x in figure_contract.get("disallowed_aliases", []) if isinstance(x, str)
        ]

    canonical_terms: list[str] = []
    if isinstance(figure_contract, dict):
        raw_terms = figure_contract.get("canonical_terms", {})
        if isinstance(raw_terms, dict):
            for value in raw_terms.values():
                if isinstance(value, str):
                    canonical_terms.append(value)
                elif isinstance(value, dict):
                    canonical_terms.extend(
                        [str(v) for v in value.values() if isinstance(v, str)]
                    )
                elif isinstance(value, list):
                    canonical_terms.extend([str(v) for v in value if isinstance(v, str)])
    if isinstance(fig_map.get("canonical_terms"), list):
        canonical_terms.extend([str(v) for v in fig_map["canonical_terms"] if isinstance(v, str)])
    canonical_terms = sorted(set(canonical_terms))

    # 1) Claim-evidence alignment.
    strong_claim_patterns = [
        r"(?i)\bwe prove\b",
        r"(?i)\bproves?\b",
        r"(?i)\bestablish(es|ed)\b",
        r"(?i)\bcausal effect\b",
        r"(?i)\bcauses?\b",
    ]
    caveat_patterns = [
        r"(?i)\bobservational\b",
        r"(?i)\bassociational\b",
        r"(?i)\bcannot establish causal\b",
        r"(?i)\bbounded interpretation\b",
        r"(?i)\bconditional\b",
    ]
    strong_hits = [p for p in strong_claim_patterns if re.search(p, manuscript_text)]
    has_caveat = any(re.search(p, manuscript_text) for p in caveat_patterns)

    claim_evidence_alignment = "pass"
    if strong_hits and not has_caveat:
        claim_evidence_alignment = "fail"
        risk_flags.add("claim_evidence_mismatch_risk")
        _append_violation(
            violations,
            violation_id="claim_evidence_mismatch",
            severity="error",
            message="Strong causal/establishing language appears without bounded-observational caveats.",
            details={"matched_patterns": strong_hits},
        )
    elif strong_hits and has_caveat:
        claim_evidence_alignment = "warning"
        risk_flags.add("claim_evidence_mismatch_risk")
        _append_violation(
            violations,
            violation_id="claim_strength_tension",
            severity="warning",
            message="Strong claim words appear; ensure all key claims remain conditional/associational.",
            details={"matched_patterns": strong_hits},
        )
    checks.append(
        {"check": "claim_evidence_alignment", "status": claim_evidence_alignment, "details": None}
    )

    # 2) Terminology consistency.
    jargon_hits = sorted({term for term in forbidden_terms if _normalize(term) in normalized_doc})
    alias_hits = sorted({alias for alias in disallowed_aliases if _normalize(alias) in normalized_doc})
    terminology_consistency = "pass"
    if jargon_hits or alias_hits:
        terminology_consistency = "warning"
        risk_flags.add("jargon_leak_risk")
        risk_flags.add("figure_label_drift_risk")
        _append_violation(
            violations,
            violation_id="terminology_drift",
            severity="warning",
            message="Detected internal labels or disallowed aliases in manuscript text.",
            details={"forbidden_term_hits": jargon_hits, "disallowed_alias_hits": alias_hits},
        )
    checks.append(
        {
            "check": "terminology_consistency",
            "status": terminology_consistency,
            "details": {"forbidden_term_hits": jargon_hits, "alias_hits": alias_hits},
        }
    )

    # 3) Gate vs inferential separation.
    gate_inference_separation = "pass"
    gate_sentences = []
    for sentence in _split_sentences(manuscript_text):
        if re.search(r"(?i)\bgate\b", sentence):
            gate_sentences.append(sentence)
            if re.search(r"(?i)\bp\s*[=<>]|p-value|significant", sentence):
                gate_inference_separation = "fail"
                break
    if gate_inference_separation == "fail":
        risk_flags.add("gate_inference_conflation_risk")
        _append_violation(
            violations,
            violation_id="gate_inference_conflation",
            severity="error",
            message="Gate language is conflated with inferential statistics in the same sentence.",
            details={"examples": gate_sentences[:3]},
        )
    elif gate_sentences and not re.search(
        r"(?i)not a null[- ]hypothesis test|not.*significance", manuscript_text
    ):
        gate_inference_separation = "warning"
        risk_flags.add("gate_inference_conflation_risk")
        _append_violation(
            violations,
            violation_id="gate_definition_missing",
            severity="warning",
            message="Gate is used but not explicitly defined as operational (non-NHST).",
            details={"examples": gate_sentences[:3]},
        )
    checks.append(
        {
            "check": "gate_inference_separation",
            "status": gate_inference_separation,
            "details": {"gate_sentence_count": len(gate_sentences)},
        }
    )

    # 4) Figure-caption vs text consistency.
    figure_lines = _extract_figure_lines(manuscript_text)
    figure_text = "\n".join(figure_lines)
    normalized_figure_text = _normalize(figure_text)
    figure_caption_text_consistency = "pass"
    missing_from_body = []
    for term in canonical_terms:
        nt = _normalize(term)
        if nt and nt in normalized_figure_text and nt not in normalized_doc:
            missing_from_body.append(term)
    if missing_from_body:
        figure_caption_text_consistency = "warning"
        risk_flags.add("figure_label_drift_risk")
        _append_violation(
            violations,
            violation_id="figure_text_alignment",
            severity="warning",
            message="Terms in figure captions/labels are not reflected in manuscript body text.",
            details={"missing_from_body": missing_from_body},
        )
    checks.append(
        {
            "check": "figure_caption_text_consistency",
            "status": figure_caption_text_consistency,
            "details": {"figure_line_count": len(figure_lines)},
        }
    )

    # 5) Main-vs-supp placement for caveats.
    main_vs_supp_placement = "pass"
    lines = manuscript_text.splitlines()
    supp_idx = None
    for i, line in enumerate(lines):
        if re.search(r"(?i)^\s*#{1,6}\s+supplement|^\s*supplementary", line):
            supp_idx = i
            break

    caveat_pattern = re.compile(
        r"(?i)\blimitation|confound|attenuat|failure mode|boundary condition|cannot establish causal"
    )
    caveat_positions = [i for i, line in enumerate(lines) if caveat_pattern.search(line)]
    if supp_idx is not None and caveat_positions:
        if all(pos >= supp_idx for pos in caveat_positions):
            main_vs_supp_placement = "warning"
            risk_flags.add("confounding_underreported_risk")
            _append_violation(
                violations,
                violation_id="caveat_supp_only",
                severity="warning",
                message="Key caveat language appears only after Supplementary section begins.",
                details={"supplement_start_line": supp_idx + 1},
            )
    checks.append(
        {
            "check": "main_vs_supp_placement",
            "status": main_vs_supp_placement,
            "details": {"supplement_present": supp_idx is not None},
        }
    )

    # Aggregate warnings as flat strings for quick scanning.
    for item in violations:
        if item["severity"] == "warning":
            warnings.append(item["message"])

    pass_fail = "fail" if any(v["severity"] == "error" for v in violations) else "pass"
    summary = {
        "forbidden_term_hits": len(jargon_hits),
        "disallowed_alias_hits": len(alias_hits),
        "figure_lines_detected": len(figure_lines),
        "risk_flag_count": len(risk_flags),
    }

    return {
        "journal_id": journal_id,
        "pass_fail": pass_fail,
        "claim_evidence_alignment": claim_evidence_alignment,
        "terminology_consistency": terminology_consistency,
        "gate_inference_separation": gate_inference_separation,
        "figure_caption_text_consistency": figure_caption_text_consistency,
        "main_vs_supp_placement": main_vs_supp_placement,
        "risk_flags": sorted(risk_flags),
        "violations": violations,
        "warnings": warnings,
        "checks": checks,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", required=True, help="Path to manuscript markdown/tex.")
    parser.add_argument("--journal", default="imaging_neuroscience", help="Journal id, name, or alias.")
    parser.add_argument(
        "--guides",
        default=str(_default_guides_path()),
        help="Path to journal_writing_guides.yaml.",
    )
    parser.add_argument(
        "--fig-map",
        help="Optional YAML mapping of canonical/disallowed figure terms.",
    )
    parser.add_argument("--output", help="Optional output JSON path.")
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="Exit non-zero when the audit pass_fail is fail.",
    )
    args = parser.parse_args()

    manuscript_path = Path(args.manuscript).expanduser().resolve()
    guides_path = Path(args.guides).expanduser().resolve()
    if not manuscript_path.exists():
        raise SystemExit(f"Manuscript file not found: {manuscript_path}")
    if not guides_path.exists():
        raise SystemExit(f"Guide file not found: {guides_path}")

    fig_map_path = Path(args.fig_map).expanduser().resolve() if args.fig_map else None
    fig_map = _load_fig_map(fig_map_path) if fig_map_path else {}

    guides_payload = yaml.safe_load(guides_path.read_text(encoding="utf-8")) or {}
    journals = guides_payload.get("journals", {})
    if not isinstance(journals, dict):
        raise SystemExit("Invalid guide payload: journals must be an object.")

    journal_id, journal_cfg = _resolve_journal(journals, args.journal)
    manuscript_text = manuscript_path.read_text(encoding="utf-8")

    result = audit_story_coherence(
        manuscript_text=manuscript_text,
        journal_id=journal_id,
        journal_cfg=journal_cfg,
        fig_map=fig_map,
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
