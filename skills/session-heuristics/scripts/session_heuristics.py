#!/usr/bin/env python3
"""Deterministic session risk classification and lesson extraction.

Offline, stdlib-only port of the two Brain Researcher pure functions
``classify_session`` and ``extract_session_lessons`` (originally in
``brain_researcher/services/shared/session_lessons.py``). It operates on a single
research-session *digest* dict — the same object returned under the ``digest``
key by the MCP tool ``research_session_digest`` — and prints JSON findings.

It does NOT talk to any server. Obtaining the digest is an MCP read; feeding it in
and interpreting the result is this local skill.

Usage:
    python scripts/session_heuristics.py <digest.json>
    python scripts/session_heuristics.py <digest.json> --mode risk
    python scripts/session_heuristics.py <digest.json> --mode lessons
    python scripts/session_heuristics.py <digest.json> --mode both --output out.json

The input file may be either a raw digest object, or the full
``research_session_digest`` response ``{"ok": true, "digest": {...}}`` — the
``digest`` key is unwrapped automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Rule kernel loading (the auditable taxonomy lives in references/)            #
# --------------------------------------------------------------------------- #


def _default_taxonomy_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "risk_taxonomy.json"


def load_taxonomy(path: Path | None = None) -> dict[str, Any]:
    """Load and compile the risk taxonomy rule kernel."""
    taxonomy_path = path or _default_taxonomy_path()
    if not taxonomy_path.exists():
        raise SystemExit(f"Taxonomy file not found: {taxonomy_path}")
    raw = json.loads(taxonomy_path.read_text(encoding="utf-8"))

    compiled: dict[str, Any] = {
        "risk_labels": list(raw.get("risk_labels") or []),
        "open_risk_patterns": [
            (str(row["label"]), re.compile(str(row["pattern"]), re.IGNORECASE))
            for row in raw.get("open_risk_patterns") or []
        ],
        "open_risk_fallback_label": str(
            raw.get("open_risk_fallback_label") or "pre-existing-debt"
        ),
        "task_surface_patterns": [
            (str(row["name"]), re.compile(str(row["pattern"]), re.IGNORECASE))
            for row in raw.get("task_surface_patterns") or []
        ],
        "task_surface_fallback": str(raw.get("task_surface_fallback") or "other"),
        "validation_evidence_patterns": [
            (str(row["evidence_type"]), re.compile(str(row["pattern"]), re.IGNORECASE))
            for row in raw.get("validation_evidence_patterns") or []
        ],
        "prod_task_re": re.compile(
            str(raw.get("prod_task_regex") or ""), re.IGNORECASE
        ),
        "prod_evidence_re": re.compile(
            str(raw.get("prod_evidence_regex") or ""), re.IGNORECASE
        ),
        "vague_open_values": {
            str(v).lower() for v in raw.get("vague_open_values") or []
        },
        "hygiene_checks": {
            str(row["code"]): row for row in raw.get("hygiene_checks") or []
        },
        "lesson_map": dict(raw.get("lesson_map") or {}),
    }
    return compiled


# --------------------------------------------------------------------------- #
# Digest field helpers (ported verbatim)                                       #
# --------------------------------------------------------------------------- #


def _items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _snapshot(digest: dict[str, Any]) -> dict[str, Any]:
    snap = digest.get("snapshot")
    return snap if isinstance(snap, dict) else {}


def _text_parts(digest: dict[str, Any]) -> list[str]:
    snapshot = _snapshot(digest)
    return [
        str(digest.get("session_id") or ""),
        str(digest.get("run_id") or ""),
        str(snapshot.get("goal") or ""),
        str(snapshot.get("next_command") or ""),
        " ".join(_items(digest.get("event_tags"))),
        " ".join(_items(digest.get("done_items"))),
        " ".join(_items(digest.get("open_items"))),
    ]


def _digest_text(digest: dict[str, Any]) -> str:
    return " ".join(_text_parts(digest)).lower()


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


# --------------------------------------------------------------------------- #
# Classifiers (ported verbatim from classify_session's helpers)               #
# --------------------------------------------------------------------------- #


def infer_task_surfaces(digest: dict[str, Any], tax: dict[str, Any]) -> list[str]:
    text = _digest_text(digest)
    surfaces = [
        surface
        for surface, pattern in tax["task_surface_patterns"]
        if pattern.search(text)
    ]
    return surfaces or [tax["task_surface_fallback"]]


def extract_validation_evidence(
    digest: dict[str, Any], tax: dict[str, Any]
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source_field in ("done_items", "open_items"):
        for item in _items(digest.get(source_field)):
            for evidence_type, pattern in tax["validation_evidence_patterns"]:
                if not pattern.search(item):
                    continue
                key = (evidence_type, item)
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(
                    {
                        "id": _stable_id("validation_evidence", evidence_type, item),
                        "evidence_type": evidence_type,
                        "source_field": source_field,
                        "text": item,
                    }
                )
    return evidence


def classify_open_risks(
    digest: dict[str, Any], tax: dict[str, Any]
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    session_key = digest.get("session_id") or digest.get("run_id")
    for item in _items(digest.get("open_items")):
        labels = [
            label
            for label, pattern in tax["open_risk_patterns"]
            if pattern.search(item)
        ]
        matched = bool(labels)
        if not labels:
            labels = [tax["open_risk_fallback_label"]]
        for label in labels:
            risks.append(
                {
                    "id": _stable_id("open_risk", session_key, label, item),
                    "label": label,
                    "text": item,
                    "matched_pattern": matched,
                }
            )
    return risks


def classify_session_hygiene(
    digest: dict[str, Any], tax: dict[str, Any]
) -> list[dict[str, Any]]:
    checks = tax["hygiene_checks"]
    issues: list[dict[str, Any]] = []
    session_id = str(digest.get("session_id") or "")

    def _emit(code: str, evidence: list[str]) -> None:
        meta = checks.get(code, {})
        issues.append(
            {
                "code": code,
                "severity": str(meta.get("severity") or "unknown"),
                "message": str(meta.get("message") or ""),
                "evidence": evidence,
            }
        )

    if not str(digest.get("source_client") or "").strip():
        _emit("missing_source_client", [session_id])
    if not bool(digest.get("has_snapshot")):
        _emit("missing_final_snapshot", [session_id])
    vague_open = [
        item
        for item in _items(digest.get("open_items"))
        if item.lower() in tax["vague_open_values"]
    ]
    if vague_open:
        _emit("vague_open_none", vague_open)
    if (
        str(digest.get("status") or "").lower() == "succeeded"
        and bool(digest.get("has_snapshot"))
        and not extract_validation_evidence(digest, tax)
    ):
        _emit(
            "succeeded_without_validation_evidence",
            _items(digest.get("done_items"))[:3],
        )
    text = _digest_text(digest)
    evidence_text = " ".join(
        _items(digest.get("done_items")) + _items(digest.get("open_items"))
    )
    if tax["prod_task_re"].search(text) and not tax["prod_evidence_re"].search(
        evidence_text
    ):
        _emit("prod_without_rollout_health_evidence", _text_parts(digest)[:4])
    return issues


def classify_session(digest: dict[str, Any], tax: dict[str, Any]) -> dict[str, Any]:
    """Return session surfaces, evidence, open risks, and hygiene issues."""
    return {
        "session_id": digest.get("session_id"),
        "run_id": digest.get("run_id"),
        "status": digest.get("status"),
        "source_client": digest.get("source_client"),
        "has_snapshot": bool(digest.get("has_snapshot")),
        "task_surfaces": infer_task_surfaces(digest, tax),
        "validation_evidence": extract_validation_evidence(digest, tax),
        "open_risks": classify_open_risks(digest, tax),
        "hygiene_issues": classify_session_hygiene(digest, tax),
    }


def extract_session_lessons(
    digest: dict[str, Any], tax: dict[str, Any]
) -> dict[str, Any]:
    """Build a conservative, fact-first lesson extraction payload."""
    classification = classify_session(digest, tax)
    lesson_map = tax["lesson_map"]
    lessons: list[dict[str, Any]] = []
    for issue in classification["hygiene_issues"]:
        code = str(issue.get("code") or "")
        lesson = lesson_map.get(code)
        if not lesson:
            continue
        lessons.append(
            {
                "id": _stable_id("lesson", digest.get("session_id"), code, lesson),
                "issue_code": code,
                "text": lesson,
                "status": "candidate",
            }
        )
    return {
        "session_id": digest.get("session_id"),
        "run_id": digest.get("run_id"),
        "classification": classification,
        "lessons": lessons,
    }


# --------------------------------------------------------------------------- #
# Tool wrappers — mirror the MCP tool output contracts                         #
# --------------------------------------------------------------------------- #


def session_risk_classify(
    digest: dict[str, Any], tax: dict[str, Any]
) -> dict[str, Any]:
    classification = classify_session(digest, tax)
    return {
        "ok": True,
        "session_id": classification.get("session_id"),
        "run_id": classification.get("run_id"),
        "classification": classification,
        "risk_labels": list(tax["risk_labels"]),
    }


def session_lesson_extract(
    digest: dict[str, Any], tax: dict[str, Any]
) -> dict[str, Any]:
    payload = extract_session_lessons(digest, tax)
    return {"ok": True, **payload}


# --------------------------------------------------------------------------- #
# I/O                                                                          #
# --------------------------------------------------------------------------- #


def _unwrap_digest(payload: Any) -> dict[str, Any]:
    """Accept a raw digest or a research_session_digest response envelope."""
    if not isinstance(payload, dict):
        raise SystemExit("Input JSON must be an object (a digest or {digest: {...}}).")
    inner = payload.get("digest")
    if isinstance(inner, dict) and inner:
        return inner
    return payload


def run(digest: dict[str, Any], mode: str, tax: dict[str, Any]) -> dict[str, Any]:
    if mode == "risk":
        return session_risk_classify(digest, tax)
    if mode == "lessons":
        return session_lesson_extract(digest, tax)
    # both: merge the two contracts (classification is shared/identical)
    lessons = session_lesson_extract(digest, tax)
    return {
        "ok": True,
        "session_id": lessons.get("session_id"),
        "run_id": lessons.get("run_id"),
        "classification": lessons["classification"],
        "lessons": lessons["lessons"],
        "risk_labels": list(tax["risk_labels"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to a digest JSON (or {digest: {...}}).")
    parser.add_argument(
        "--mode",
        default="both",
        choices=["risk", "lessons", "both"],
        help="risk = session_risk_classify, lessons = session_lesson_extract, both = merged.",
    )
    parser.add_argument("--taxonomy", help="Override path to risk_taxonomy.json.")
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    tax_path = Path(args.taxonomy).expanduser().resolve() if args.taxonomy else None
    tax = load_taxonomy(tax_path)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    digest = _unwrap_digest(payload)
    result = run(digest, args.mode, tax)

    serialized = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(
            serialized + "\n", encoding="utf-8"
        )
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
