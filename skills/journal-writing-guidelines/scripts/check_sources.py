#!/usr/bin/env python3
"""Semi-automatic source health checker for journal guideline links."""

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
        if exc.code in (403, 405):
            # Some sites block HEAD; retry with GET.
            pass
        else:
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


def _collect_urls(source_entry: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    primary = source_entry.get("primary_guideline_url")
    if isinstance(primary, str) and primary.strip():
        urls.append(primary.strip())
    secondary = source_entry.get("secondary_urls", [])
    if isinstance(secondary, list):
        for item in secondary:
            if isinstance(item, str) and item.strip():
                urls.append(item.strip())
    return urls


def check_registry(registry: dict[str, Any], timeout: float, skip_network: bool) -> dict[str, Any]:
    sources = registry.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError("Invalid source registry: 'sources' must be an object.")

    per_source: dict[str, Any] = {}
    total_urls = 0
    reachable_urls = 0

    for source_id, source_payload in sources.items():
        if not isinstance(source_payload, dict):
            continue
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
            "journal": source_payload.get("journal"),
            "last_verified_date": source_payload.get("last_verified_date"),
            "checks": checks,
        }

    unreachable_urls = total_urls - reachable_urls if not skip_network else None
    summary = {
        "source_count": len(per_source),
        "total_urls": total_urls,
        "reachable_urls": reachable_urls if not skip_network else None,
        "unreachable_urls": unreachable_urls,
        "skip_network": skip_network,
    }

    return {"summary": summary, "sources": per_source}


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
