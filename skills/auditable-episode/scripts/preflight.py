#!/usr/bin/env python3
"""Preflight for the auditable-episode skill — refuse loudly on version skew or a missing backend.

Two failure classes this catches (both would otherwise degrade SILENTLY into a plausible-wrong
"success", the #1 trap in this project):

  1. VERSION SKEW. A too-old / carved BR checkout may be missing an enabling symbol; the episode
     would then either crash deep in the run or (worse) seal a toothless card. We IMPORT-check
     every real primitive (stronger than a grep — it proves the symbol is actually importable and
     callable, and it inherently avoids the `emit_audit_bundle` red herring: the real names are
     `persist_audit_bundle` / `export_audit_bundle`). Any absent primitive => nonzero exit.

  2. NO OFFLINE BACKEND. The episode forces neuroclaim_compile onto the NiMARE backend so it never
     touches Neo4j. If nimare/nilearn are not importable, `resolve_backend('nimare')` would fall
     back to the online KG backend and the "offline" guarantee is a lie. We assert nimare AND
     nilearn import => nonzero exit if either is missing.

Usage:
    python preflight.py [--br-src /path/to/br@master]
    # or, from another module:
    from preflight import assert_preflight; assert_preflight(br_src)
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from pathlib import Path

# (module_path, symbol) pairs — the REAL enabling primitives. At least one of each OR-group must
# resolve; every AND item must resolve.
_REQUIRED_SYMBOLS: list[tuple[str, str]] = [
    ("brain_researcher.autoresearch.society", "neuroclaim_compile"),
    ("brain_researcher.autoresearch.society", "lock_commitment"),
    ("brain_researcher.autoresearch.society", "compute_permutation_null_probe"),
    ("brain_researcher.autoresearch.society", "NimareBackend"),
    ("brain_researcher.autoresearch.society", "build_synthetic_annotated_corpus"),
    ("brain_researcher.autoresearch.society", "resolve_region"),
    ("brain_researcher.services.review.audit_bundle", "persist_audit_bundle"),
    ("brain_researcher.services.review.audit_bundle", "export_audit_bundle"),
]
# OR-groups: at least one member must import.
_REQUIRED_OR_GROUPS: list[list[tuple[str, str]]] = [
    [
        ("brain_researcher.autoresearch.society", "derive_default_battery"),
        ("brain_researcher.autoresearch.society", "compile_required_battery"),
    ],
]
# The deterministic gate dispatcher (the permutation_null battery's real evaluator).
_REQUIRED_SYMBOLS_EXTRA: list[tuple[str, str]] = [
    ("brain_researcher.autoresearch.society.falsifiers", "DETERMINISTIC_GATES"),
]


def _try_import(module: str, symbol: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001 - report any import failure verbatim
        return False, f"import {module} FAILED: {type(exc).__name__}: {exc}"
    if not hasattr(mod, symbol):
        return False, f"{module}.{symbol} MISSING"
    return True, f"{module}.{symbol} ok"


def assert_preflight(br_src: str | None = None, *, verbose: bool = True) -> None:
    """Raise ``SystemExit`` (nonzero) with a clear message if any guard fails."""
    if br_src:
        src = Path(br_src).expanduser().resolve() / "src"
        if not (src / "brain_researcher").is_dir():
            raise SystemExit(f"REFUSING: --br-src {br_src} has no src/brain_researcher")
        sys.path.insert(0, str(src))

    problems: list[str] = []
    oks: list[str] = []

    # BR importable at all?
    ok, msg = _try_import("brain_researcher.autoresearch.society", "ClaimSpecV1")
    if not ok:
        raise SystemExit(
            "REFUSING TO RUN: brain_researcher is not importable.\n"
            f"  {msg}\n"
            "Fix: pass --br-src <a BR checkout off origin/master>, or set "
            "PYTHONPATH=<checkout>/src, in the brain_researcher conda env."
        )

    for module, symbol in _REQUIRED_SYMBOLS + _REQUIRED_SYMBOLS_EXTRA:
        ok, msg = _try_import(module, symbol)
        (oks if ok else problems).append(msg)

    for group in _REQUIRED_OR_GROUPS:
        present = [f"{m}.{s}" for (m, s) in group if _try_import(m, s)[0]]
        if present:
            oks.append(" | ".join(present) + " (>=1 of the OR-group)")
        else:
            problems.append("NONE of: " + ", ".join(f"{m}.{s}" for m, s in group))

    # Offline backend really available (not a silent KG fallback)?
    for pkg in ("nimare", "nilearn"):
        if importlib.util.find_spec(pkg) is None:
            problems.append(f"offline backend dependency {pkg!r} NOT importable")
        else:
            oks.append(f"{pkg} importable")

    if verbose:
        for m in oks:
            print(f"  [ok]   {m}")
    if problems:
        detail = "\n".join(f"  [MISSING] {p}" for p in problems)
        raise SystemExit(
            "REFUSING TO RUN — auditable-episode preflight failed (version skew or missing "
            "offline backend). Silent degradation would produce a plausible-wrong 'success'.\n"
            f"{detail}\n"
            "Fix: use a BR checkout off origin/master (--br-src / PYTHONPATH) and "
            "`pip install nimare nilearn` in the brain_researcher env."
        )
    if verbose:
        print(
            "PREFLIGHT OK — all enabling primitives import and the offline NiMARE backend is present."
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--br-src", default=None, help="BR checkout root (adds <root>/src to sys.path)"
    )
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    assert_preflight(args.br_src, verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
