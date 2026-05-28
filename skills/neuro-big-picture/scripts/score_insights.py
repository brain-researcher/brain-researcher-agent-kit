#!/usr/bin/env python3
"""Deterministic insight scoring and ranking for neuro-big-picture."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - runtime dependency guard
    yaml = None

WEIGHTS = {
    "relevance": 0.25,
    "authority": 0.20,
    "freshness": 0.15,
    "signal_to_noise": 0.15,
    "capturability": 0.10,
    "novelty": 0.15,
}

ALLOWED_MODES = {"broad", "strict"}
GC_ID_RE = re.compile(r"^GC[0-9]+$")


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _freshness_from_date(date_text: str, recency_days: int) -> float:
    parsed = _parse_date(date_text)
    if parsed is None:
        return 0.5

    today = datetime.now(timezone.utc).date()
    delta_days = max(0, (today - parsed).days)
    if delta_days <= recency_days:
        # Keep in-window sources above 0.5 and recent ones near 1.0.
        ratio = delta_days / float(recency_days)
        return _clamp_01(1.0 - 0.5 * ratio)

    extra = delta_days - recency_days
    fade_window = max(recency_days, 1)
    return _clamp_01(0.5 - 0.5 * (extra / float(fade_window)))


def _capture_to_score(capture_method: str) -> float:
    mapping = {
        "api": 1.0,
        "rss": 0.9,
        "web": 0.8,
        "mirror": 0.6,
        "manual": 0.4,
    }
    return mapping.get(capture_method, 0.5)


def _default_grand_challenges_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "grand_challenges.yaml"


def _load_grand_challenge_catalog(path: Path | None) -> tuple[set[str], bool]:
    if path is None:
        path = _default_grand_challenges_path()

    if yaml is None or not path.exists():
        return set(), False

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return set(), False

    challenges = payload.get("grand_challenges")
    if not isinstance(challenges, dict):
        return set(), False

    ids = {key for key in challenges if isinstance(key, str) and GC_ID_RE.match(key)}
    return ids, True


def _source_from_payload(source_payload: dict[str, Any]) -> dict[str, Any]:
    source_id = source_payload.get("source_id") or source_payload.get("id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("Each source entry must contain source_id or id")

    return {
        "source_id": source_id,
        "name": source_payload.get("name", source_id),
        "tier": source_payload.get("tier", "C"),
        "channel": source_payload.get("channel", "social"),
        "capture_method": source_payload.get("capture_method", "manual"),
        "authority_score": float(source_payload.get("authority_score", 0.6)),
        "noise_risk": float(source_payload.get("noise_risk", 0.5)),
    }


def _exploration_bonus(mode: str, tier: str, novelty: float) -> float:
    if mode != "broad":
        return 0.0
    if tier not in {"B", "C"}:
        return 0.0
    if novelty <= 0.7:
        return 0.0
    return min(5.0, (novelty - 0.7) / 0.3 * 5.0)


def _noise_penalty(mode: str, noise_risk: float, evidence_count: int) -> float:
    noise_risk = _clamp_01(noise_risk)
    if mode == "broad":
        if noise_risk <= 0.5:
            penalty = 0.0
        else:
            penalty = 5.0 + ((noise_risk - 0.5) / 0.5) * 10.0
    else:
        if noise_risk <= 0.4:
            penalty = 0.0
        else:
            penalty = 10.0 + ((noise_risk - 0.4) / 0.6) * 15.0

    if evidence_count >= 2:
        penalty = max(0.0, penalty - 5.0)
    if evidence_count >= 3:
        penalty = max(0.0, penalty - 2.0)
    return min(25.0, penalty)


@dataclass
class ScoredInsight:
    payload: dict[str, Any]
    score: float


def score_payload(
    payload: dict[str, Any],
    mode: str,
    *,
    grand_challenge_ids: set[str] | None = None,
    grand_challenge_catalog_loaded: bool = False,
) -> dict[str, Any]:
    if mode not in ALLOWED_MODES:
        raise ValueError(f"mode must be one of {sorted(ALLOWED_MODES)}")

    query_profile = payload.get("query_profile", {})
    if not isinstance(query_profile, dict):
        query_profile = {}

    recency_days = int(query_profile.get("recency_days", 120))
    if recency_days <= 0:
        recency_days = 120

    source_payloads = payload.get("sources", [])
    insight_payloads = payload.get("insight_items", [])
    if not isinstance(source_payloads, list):
        raise ValueError("sources must be an array")
    if not isinstance(insight_payloads, list):
        raise ValueError("insight_items must be an array")

    source_index: dict[str, dict[str, Any]] = {}
    for raw_source in source_payloads:
        if not isinstance(raw_source, dict):
            continue
        source = _source_from_payload(raw_source)
        source["authority_score"] = _clamp_01(source["authority_score"])
        source["noise_risk"] = _clamp_01(source["noise_risk"])
        source_index[source["source_id"]] = source

    scored: list[ScoredInsight] = []
    source_item_scores: dict[str, list[float]] = {key: [] for key in source_index}
    recognized_grand_challenge_ids: set[str] = set()
    unknown_grand_challenge_ids: set[str] = set()
    invalid_grand_challenge_ids: set[str] = set()

    known_gc_ids = grand_challenge_ids or set()

    for idx, item in enumerate(insight_payloads):
        if not isinstance(item, dict):
            continue

        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            source_id = f"unknown_source_{idx}"

        source = source_index.get(source_id)
        if source is None:
            source = {
                "source_id": source_id,
                "name": source_id,
                "tier": "C",
                "channel": "social",
                "capture_method": "manual",
                "authority_score": 0.5,
                "noise_risk": 0.6,
            }
            source_index[source_id] = source
            source_item_scores.setdefault(source_id, [])

        noise_risk = float(item.get("noise_risk", source["noise_risk"]))
        relevance = _clamp_01(float(item.get("relevance", 0.6)))
        authority = _clamp_01(float(item.get("authority", source["authority_score"])))
        freshness = _clamp_01(
            float(item.get("freshness", _freshness_from_date(str(item.get("date", "")), recency_days)))
        )
        signal_to_noise = _clamp_01(float(item.get("signal_to_noise", 1.0 - noise_risk)))
        capturability = _clamp_01(
            float(item.get("capturability", _capture_to_score(str(source["capture_method"]))))
        )
        novelty = _clamp_01(float(item.get("novelty", 0.5)))
        evidence_count = int(item.get("evidence_count", 1))

        mapped_grand_challenges = item.get("mapped_grand_challenges", [])
        if not isinstance(mapped_grand_challenges, list):
            mapped_grand_challenges = []
        for gc_id in mapped_grand_challenges:
            if not isinstance(gc_id, str) or not GC_ID_RE.match(gc_id):
                invalid_grand_challenge_ids.add(str(gc_id))
                continue
            if known_gc_ids and gc_id not in known_gc_ids:
                unknown_grand_challenge_ids.add(gc_id)
            else:
                recognized_grand_challenge_ids.add(gc_id)

        base_score = (
            relevance * WEIGHTS["relevance"]
            + authority * WEIGHTS["authority"]
            + freshness * WEIGHTS["freshness"]
            + signal_to_noise * WEIGHTS["signal_to_noise"]
            + capturability * WEIGHTS["capturability"]
            + novelty * WEIGHTS["novelty"]
        ) * 100.0

        exploration_bonus = _exploration_bonus(mode=mode, tier=str(source["tier"]), novelty=novelty)
        noise_penalty = _noise_penalty(mode=mode, noise_risk=noise_risk, evidence_count=evidence_count)
        item_score = _clamp_100(base_score + exploration_bonus - noise_penalty)

        enriched = dict(item)
        enriched.setdefault("item_id", f"item_{idx + 1}")
        enriched.setdefault("source_id", source_id)
        enriched["item_score"] = round(item_score, 2)
        enriched["score_breakdown"] = {
            "relevance": round(relevance, 4),
            "authority": round(authority, 4),
            "freshness": round(freshness, 4),
            "signal_to_noise": round(signal_to_noise, 4),
            "capturability": round(capturability, 4),
            "novelty": round(novelty, 4),
            "exploration_bonus": round(exploration_bonus, 2),
            "noise_penalty": round(noise_penalty, 2),
        }

        source_item_scores.setdefault(source_id, []).append(item_score)
        scored.append(ScoredInsight(payload=enriched, score=item_score))

    scored.sort(key=lambda row: row.score, reverse=True)

    scored_sources: list[dict[str, Any]] = []
    for source_id, source in source_index.items():
        item_scores = source_item_scores.get(source_id, [])
        if item_scores:
            mean_item_score = sum(item_scores) / len(item_scores)
        else:
            mean_item_score = (
                _clamp_01(float(source["authority_score"])) * 70.0
                + (1.0 - _clamp_01(float(source["noise_risk"]))) * 30.0
            )

        source_score = _clamp_100(mean_item_score)
        scored_sources.append(
            {
                "source_id": source_id,
                "name": source.get("name", source_id),
                "tier": source.get("tier", "C"),
                "channel": source.get("channel", "social"),
                "capture_method": source.get("capture_method", "manual"),
                "source_score": round(source_score, 2),
                "noise_risk": round(_clamp_01(float(source.get("noise_risk", 0.5))), 4),
                "score_breakdown": {
                    "mean_item_score": round(mean_item_score, 2),
                    "item_count": len(item_scores),
                },
            }
        )

    scored_sources.sort(key=lambda row: row["source_score"], reverse=True)

    scored_items = [row.payload for row in scored]
    summary = {
        "mode": mode,
        "weights": WEIGHTS,
        "insight_count": len(scored_items),
        "source_count": len(scored_sources),
        "top_item_score": round(scored_items[0]["item_score"], 2) if scored_items else 0.0,
        "mean_item_score": round(
            sum(item["item_score"] for item in scored_items) / len(scored_items), 2
        )
        if scored_items
        else 0.0,
        "grand_challenge_catalog_loaded": grand_challenge_catalog_loaded,
        "recognized_grand_challenge_ids": sorted(recognized_grand_challenge_ids),
        "unknown_grand_challenge_ids": sorted(unknown_grand_challenge_ids),
        "invalid_grand_challenge_ids": sorted(invalid_grand_challenge_ids),
    }

    return {
        "query_profile": {
            "idea_text": str(query_profile.get("idea_text", "")),
            "mode": mode,
            "recency_days": recency_days,
            "perspectives": query_profile.get("perspectives", []),
        },
        "summary": summary,
        "sources": scored_sources,
        "insight_items": scored_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to input JSON payload.")
    parser.add_argument("--output", help="Optional output JSON path.")
    parser.add_argument("--mode", default="broad", choices=sorted(ALLOWED_MODES))
    parser.add_argument(
        "--grand-challenges",
        help="Optional path to grand_challenges.yaml for catalog validation.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    gc_path = Path(args.grand_challenges).expanduser().resolve() if args.grand_challenges else None
    gc_ids, gc_loaded = _load_grand_challenge_catalog(gc_path)
    result = score_payload(
        payload=payload,
        mode=args.mode,
        grand_challenge_ids=gc_ids,
        grand_challenge_catalog_loaded=gc_loaded,
    )

    serialized = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
