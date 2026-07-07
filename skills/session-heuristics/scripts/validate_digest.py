#!/usr/bin/env python3
"""Validate a caller-supplied session digest against the heuristics input contract.

The risk classifier and lesson extractor only read a handful of digest fields. A
sparse digest silently under-reports (for example, an empty ``open_items`` yields
zero open risks, which is *input-limited*, not a clean bill of health). This
script checks which load-bearing fields are present/populated and prints JSON
findings so the agent can flag input limits before trusting the output.

It is offline and stdlib-only, and does not classify anything itself.

Usage:
    python scripts/validate_digest.py <digest.json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Fields the heuristics actually read, and what an empty value costs.
IDENTITY_FIELDS = ("session_id", "run_id")
SIGNAL_FIELDS: dict[str, str] = {
    "status": "hygiene check 'succeeded_without_validation_evidence' cannot fire",
    "source_client": "hygiene check 'missing_source_client' fires by default (absence is itself a finding)",
    "has_snapshot": "hygiene check 'missing_final_snapshot' fires by default; validation/prod checks are gated on it",
    "open_items": "no open risks and no vague-open hygiene finding can be inferred (input-limited, not risk-free)",
    "done_items": "validation evidence and success-pattern signal are reduced",
    "event_tags": "task-surface inference loses signal",
    "snapshot": "goal/next_command text is unavailable to surface inference",
}


def _unwrap_digest(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SystemExit("Input JSON must be an object (a digest or {digest: {...}}).")
    inner = payload.get("digest")
    if isinstance(inner, dict) and inner:
        return inner
    return payload


def _is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    if isinstance(value, bool):
        return True
    return True


def validate(digest: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    identity_present = [f for f in IDENTITY_FIELDS if _is_populated(digest.get(f))]
    if not identity_present:
        findings.append(
            {
                "level": "error",
                "field": "session_id|run_id",
                "detail": "No identity key present; stable ids will hash on empty strings.",
            }
        )

    populated: list[str] = []
    empty: list[str] = []
    for field, cost in SIGNAL_FIELDS.items():
        if _is_populated(digest.get(field)):
            populated.append(field)
        else:
            empty.append(field)
            findings.append(
                {
                    "level": "warning",
                    "field": field,
                    "detail": f"absent/empty -> {cost}",
                }
            )

    snapshot = digest.get("snapshot")
    if isinstance(snapshot, dict):
        for sub in ("goal", "next_command"):
            if not _is_populated(snapshot.get(sub)):
                findings.append(
                    {
                        "level": "info",
                        "field": f"snapshot.{sub}",
                        "detail": "absent/empty -> reduced surface-inference text",
                    }
                )

    # A digest that reads as clean only because it is nearly empty.
    input_limited = not _is_populated(digest.get("open_items")) and not _is_populated(
        digest.get("done_items")
    )

    return {
        "ok": True,
        "session_id": digest.get("session_id"),
        "run_id": digest.get("run_id"),
        "identity_ok": bool(identity_present),
        "populated_signal_fields": populated,
        "empty_signal_fields": empty,
        "input_limited": input_limited,
        "findings": findings,
        "guidance": (
            "input_limited=true means an empty/near-empty digest will report no risks "
            "because there is nothing to classify, not because the session was clean. "
            "Confirm the digest came from research_session_digest for the intended run."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to a digest JSON (or {digest: {...}}).")
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    digest = _unwrap_digest(payload)
    result = validate(digest)

    serialized = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(
            serialized + "\n", encoding="utf-8"
        )
    print(serialized)
    # Non-zero only on a hard identity error, so CI can gate on it.
    return 0 if result["identity_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
