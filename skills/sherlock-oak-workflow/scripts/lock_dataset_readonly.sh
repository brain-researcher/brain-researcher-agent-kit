#!/usr/bin/env bash
set -euo pipefail

DIR=""
APPLY=0

usage() {
  cat <<'USAGE'
Usage:
  lock_dataset_readonly.sh --dir <dataset_root> [--apply]

Description:
  Set finalized dataset permissions to read-only:
    directories -> 550
    files       -> 440

Safety:
  Dry-run by default. Use --apply to execute chmod.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      DIR="${2:-}"
      shift 2
      ;;
    --apply)
      APPLY=1
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

if [[ -z "$DIR" ]]; then
  echo "Error: --dir is required." >&2
  usage >&2
  exit 2
fi

if [[ ! -d "$DIR" ]]; then
  echo "Error: directory does not exist: $DIR" >&2
  exit 1
fi

if [[ "$APPLY" -eq 0 ]]; then
  echo "Dry-run mode. Commands that would run:"
  echo "find '$DIR' -type d -exec chmod 550 {} +"
  echo "find '$DIR' -type f -exec chmod 440 {} +"
  exit 0
fi

find "$DIR" -type d -exec chmod 550 {} +
find "$DIR" -type f -exec chmod 440 {} +

echo "Permissions updated for $DIR"
