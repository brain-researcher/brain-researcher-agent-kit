#!/usr/bin/env bash
set -euo pipefail

DATASET_NAME=""
OWNERS=""
DESCRIPTION=""
PROVENANCE=""
ACCESS=""
OUT="README.md"
FORCE=0

usage() {
  cat <<'USAGE'
Usage:
  init_dataset_readme.sh --dataset <name> --owners <owners> --description <text> \
    --provenance <text> --access <text> [--out <path>] [--force]

Description:
  Create a dataset README.md with required provenance and access metadata.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset)
      DATASET_NAME="${2:-}"
      shift 2
      ;;
    --owners)
      OWNERS="${2:-}"
      shift 2
      ;;
    --description)
      DESCRIPTION="${2:-}"
      shift 2
      ;;
    --provenance)
      PROVENANCE="${2:-}"
      shift 2
      ;;
    --access)
      ACCESS="${2:-}"
      shift 2
      ;;
    --out)
      OUT="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$DATASET_NAME" || -z "$OWNERS" || -z "$DESCRIPTION" || -z "$PROVENANCE" || -z "$ACCESS" ]]; then
  echo "Error: required fields are missing." >&2
  usage >&2
  exit 2
fi

OUT_DIR="$(dirname "$OUT")"
mkdir -p "$OUT_DIR"

if [[ -f "$OUT" && "$FORCE" -ne 1 ]]; then
  echo "Error: output exists ($OUT). Use --force to overwrite." >&2
  exit 1
fi

cat > "$OUT" <<EOF2
# ${DATASET_NAME}

## Owner(s)
${OWNERS}

## Description
${DESCRIPTION}

## Provenance
${PROVENANCE}

## Access restrictions
${ACCESS}
EOF2

echo "Wrote $OUT"
