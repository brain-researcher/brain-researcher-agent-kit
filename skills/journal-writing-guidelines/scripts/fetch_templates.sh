#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Fetch journal templates from a local manifest.

Usage:
  fetch_templates.sh --list
  fetch_templates.sh --journal JOURNAL_KEY_OR_ALIAS [--format latex|word|all] [--dry-run] [--force] [--output-dir PATH]
  fetch_templates.sh --journal imaging_neuroscience --format latex --dry-run

Options:
  --manifest PATH   Override manifest file path.
  --journal VALUE   Journal key or alias from templates_manifest.yaml.
  --format VALUE    latex|word|all (default: all).
  --output-dir PATH Download directory (default comes from manifest).
  --list            List available journals and template entries.
  --dry-run         Resolve and print actions without downloading.
  --force           Overwrite files if they already exist.
  -h, --help        Show this help.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_MANIFEST="${SCRIPT_DIR}/../references/templates_manifest.yaml"
REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null || pwd)"

MANIFEST="${DEFAULT_MANIFEST}"
JOURNAL=""
FORMAT="all"
OUTPUT_DIR=""
LIST_ONLY="0"
DRY_RUN="0"
FORCE="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      MANIFEST="$2"
      shift 2
      ;;
    --journal)
      JOURNAL="$2"
      shift 2
      ;;
    --format)
      FORMAT="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --list)
      LIST_ONLY="1"
      shift
      ;;
    --dry-run)
      DRY_RUN="1"
      shift
      ;;
    --force)
      FORCE="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "${LIST_ONLY}" != "1" && -z "${JOURNAL}" ]]; then
  echo "Error: --journal is required unless --list is used." >&2
  usage
  exit 2
fi

python3 - "$MANIFEST" "$JOURNAL" "$FORMAT" "$OUTPUT_DIR" "$LIST_ONLY" "$DRY_RUN" "$FORCE" "$REPO_ROOT" <<'PY'
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    print("Missing dependency: pyyaml. Install with `pip install pyyaml`.", file=sys.stderr)
    raise SystemExit(2)


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def resolve_path(path_text: str, repo_root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


manifest_path = Path(sys.argv[1]).resolve()
journal_query = sys.argv[2].strip()
format_query = sys.argv[3].strip().lower()
output_dir_arg = sys.argv[4].strip()
list_only = sys.argv[5] == "1"
dry_run = sys.argv[6] == "1"
force = sys.argv[7] == "1"
repo_root = Path(sys.argv[8]).resolve()

if format_query not in {"latex", "word", "all"}:
    print(f"Invalid --format value: {format_query}. Use latex|word|all.", file=sys.stderr)
    raise SystemExit(2)

if not manifest_path.exists():
    print(f"Manifest not found: {manifest_path}", file=sys.stderr)
    raise SystemExit(2)

with manifest_path.open("r", encoding="utf-8") as f:
    manifest = yaml.safe_load(f) or {}

journals = manifest.get("journals", {})
if not isinstance(journals, dict) or not journals:
    print("Manifest contains no journals.", file=sys.stderr)
    raise SystemExit(2)

if list_only:
    print("Available journals and template entries:")
    for key, value in sorted(journals.items()):
        display = value.get("display_name", key)
        aliases = value.get("aliases", [])
        templates = value.get("templates", [])
        formats = sorted({str(t.get("format", "")).lower() for t in templates if t.get("format")})
        print(f"- {key}: {display}")
        if aliases:
            print(f"  aliases: {', '.join(aliases)}")
        print(f"  formats: {', '.join(formats) if formats else 'none'}")
        print(f"  entries: {len(templates)}")
    raise SystemExit(0)

index: dict[str, str] = {}
for key, value in journals.items():
    index[norm(key)] = key
    for alias in value.get("aliases", []):
        index[norm(str(alias))] = key

resolved_key = index.get(norm(journal_query))
if resolved_key is None:
    print(f"Journal not found in manifest: {journal_query}", file=sys.stderr)
    print("Tip: run with --list to see valid keys/aliases.", file=sys.stderr)
    raise SystemExit(2)

journal = journals[resolved_key]
templates = journal.get("templates", [])
selected = [
    t for t in templates
    if format_query == "all" or str(t.get("format", "")).lower() == format_query
]

if not selected:
    print(f"No templates found for {resolved_key} with format={format_query}.", file=sys.stderr)
    raise SystemExit(1)

if output_dir_arg:
    output_root = resolve_path(output_dir_arg, repo_root)
else:
    output_root = resolve_path(
        str(manifest.get("default_output_dir", "skills/journal-writing-guidelines/assets/templates")),
        repo_root,
    )

display_name = journal.get("display_name", resolved_key)
print(f"Journal: {display_name} ({resolved_key})")
print(f"Output directory: {output_root}")

exit_code = 0

for entry in selected:
    template_id = str(entry.get("id", "unknown"))
    fmt = str(entry.get("format", "unknown")).lower()
    access = str(entry.get("access", "direct")).lower()
    url = str(entry.get("url", "")).strip()
    filename = str(entry.get("filename", "")).strip() or f"{template_id}.{fmt}"
    notes = str(entry.get("notes", "")).strip()

    target_path = output_root / resolved_key / fmt / filename

    if access != "direct":
        print(f"[manual] {template_id} ({fmt})")
        print(f"  url: {url}")
        if notes:
            print(f"  note: {notes}")
        continue

    if dry_run:
        print(f"[dry-run] {template_id} ({fmt}) -> {target_path}")
        print(f"  url: {url}")
        continue

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and not force:
        print(f"[skip] {template_id}: already exists ({target_path})")
        continue

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "brain-researcher-template-fetcher/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        with target_path.open("wb") as f:
            f.write(data)
        print(f"[ok] {template_id} -> {target_path} ({len(data)} bytes)")
    except urllib.error.HTTPError as err:
        print(f"[fail] {template_id}: HTTP {err.code} for {url}", file=sys.stderr)
        exit_code = 1
    except urllib.error.URLError as err:
        print(f"[fail] {template_id}: URL error for {url}: {err.reason}", file=sys.stderr)
        exit_code = 1
    except Exception as err:  # noqa: BLE001
        print(f"[fail] {template_id}: {err}", file=sys.stderr)
        exit_code = 1

raise SystemExit(exit_code)
PY
