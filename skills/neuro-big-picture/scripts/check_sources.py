#!/usr/bin/env python3
"""Source registry validation and URL health checks for neuro-big-picture."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit(f"PyYAML is required to run this script: {exc}") from exc


ALLOWED_TIERS = {"A", "B", "C"}
ALLOWED_CHANNELS = {
    "blog",
    "newsletter",
    "podcast",
    "community",
    "social",
    "journal_editorial",
}
ALLOWED_CAPTURE_METHODS = {"rss", "api", "web", "mirror", "manual"}


def _default_registry_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "source_registry.yaml"


def _probe_url(url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "url": url,
        "reachable": False,
        "status_code": None,
        "final_url": None,
        "error": None,
        "latency_ms": None,
    }

    def _record_success(response: Any) -> dict[str, Any]:
        status = getattr(response, "status", None)
        final_url = getattr(response, "geturl", lambda: None)()
        latency = int((time.perf_counter() - started) * 1000)
        result.update(
            {
                "reachable": bool(status and 200 <= int(status) < 400),
                "status_code": int(status) if status is not None else None,
                "final_url": final_url,
                "latency_ms": latency,
            }
        )
        return result

    head_request = urllib.request.Request(url=url, method="HEAD")
    try:
        with urllib.request.urlopen(head_request, timeout=timeout) as response:
            return _record_success(response)
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 405):
            result["error"] = f"HTTPError: {exc.code}"
            result["status_code"] = exc.code
            result["latency_ms"] = int((time.perf_counter() - started) * 1000)
            return result
    except Exception as exc:  # pragma: no cover - network/path dependent
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    get_request = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(get_request, timeout=timeout) as response:
            return _record_success(response)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        result["error"] = f"HTTPError: {exc.code}"
        result["status_code"] = exc.code
    except Exception as exc:  # pragma: no cover - network dependent
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    return result


def _collect_urls(source_payload: dict[str, Any]) -> list[str]:
    urls_value = source_payload.get("urls", {})
    urls: list[str] = []
    if isinstance(urls_value, dict):
        for value in urls_value.values():
            if isinstance(value, str) and value.startswith("http"):
                urls.append(value)
    return urls


def _validate_source_fields(source_id: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "name",
        "tier",
        "channel",
        "capture_method",
        "urls",
        "authority_score",
        "noise_risk",
    }

    missing = sorted(key for key in required if key not in payload)
    if missing:
        errors.append(f"{source_id}: missing required fields: {', '.join(missing)}")
        return errors

    tier = payload.get("tier")
    if tier not in ALLOWED_TIERS:
        errors.append(f"{source_id}: invalid tier '{tier}'")

    channel = payload.get("channel")
    if channel not in ALLOWED_CHANNELS:
        errors.append(f"{source_id}: invalid channel '{channel}'")

    capture_method = payload.get("capture_method")
    if capture_method not in ALLOWED_CAPTURE_METHODS:
        errors.append(f"{source_id}: invalid capture_method '{capture_method}'")

    authority_score = payload.get("authority_score")
    if not isinstance(authority_score, (float, int)) or not 0 <= float(authority_score) <= 1:
        errors.append(f"{source_id}: authority_score must be a number in [0, 1]")

    noise_risk = payload.get("noise_risk")
    if not isinstance(noise_risk, (float, int)) or not 0 <= float(noise_risk) <= 1:
        errors.append(f"{source_id}: noise_risk must be a number in [0, 1]")

    urls = payload.get("urls")
    if not isinstance(urls, dict) or not urls:
        errors.append(f"{source_id}: urls must be a non-empty object")

    return errors


def check_registry(registry: dict[str, Any], timeout: float, skip_network: bool) -> dict[str, Any]:
    sources = registry.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError("Invalid source registry: 'sources' must be an object.")

    validation_errors: list[str] = []
    per_source: dict[str, Any] = {}
    total_urls = 0
    reachable_urls = 0

    for source_id, source_payload in sources.items():
        if not isinstance(source_payload, dict):
            validation_errors.append(f"{source_id}: source payload must be an object")
            continue

        validation_errors.extend(_validate_source_fields(source_id, source_payload))

        urls = _collect_urls(source_payload)
        checks: list[dict[str, Any]] = []
        for url in urls:
            total_urls += 1
            if skip_network:
                check = {
                    "url": url,
                    "reachable": None,
                    "status_code": None,
                    "final_url": None,
                    "error": "skipped_by_flag",
                    "latency_ms": None,
                }
            else:
                check = _probe_url(url, timeout=timeout)
                if check.get("reachable"):
                    reachable_urls += 1
            checks.append(check)

        per_source[source_id] = {
            "name": source_payload.get("name"),
            "tier": source_payload.get("tier"),
            "channel": source_payload.get("channel"),
            "checks": checks,
        }

    unreachable_urls = total_urls - reachable_urls if not skip_network else None
    summary = {
        "source_count": len(per_source),
        "total_urls": total_urls,
        "reachable_urls": reachable_urls if not skip_network else None,
        "unreachable_urls": unreachable_urls,
        "skip_network": skip_network,
        "valid_registry": len(validation_errors) == 0,
    }

    return {
        "summary": summary,
        "validation_errors": validation_errors,
        "sources": per_source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        default=str(_default_registry_path()),
        help="Path to source_registry.yaml.",
    )
    parser.add_argument("--timeout", type=float, default=8.0, help="Request timeout in seconds.")
    parser.add_argument("--output", help="Optional output JSON path.")
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Validate structure only without probing URLs.",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry).expanduser().resolve()
    if not registry_path.exists():
        raise SystemExit(f"Source registry not found: {registry_path}")

    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    result = check_registry(registry, timeout=args.timeout, skip_network=args.skip_network)

    payload = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(payload + "\n", encoding="utf-8")
    print(payload)

    return 0 if result["summary"]["valid_registry"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
