#!/usr/bin/env bash
set -euo pipefail

SUNET=""
PI_GROUP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sunet)
      SUNET="${2:-}"
      shift 2
      ;;
    --pi-group)
      PI_GROUP="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--sunet <sunetid>] [--pi-group <group>]" >&2
      exit 2
      ;;
  esac
done

check_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "[OK] $cmd"
  else
    echo "[MISSING] $cmd"
  fi
}

echo "Sherlock local preflight"
echo "========================"

check_cmd ssh
check_cmd rsync
check_cmd sftp
check_cmd sshfs

echo
echo "Recommended login command:"
if [[ -n "$SUNET" ]]; then
  echo "  ssh ${SUNET}@login.sherlock.stanford.edu"
else
  echo "  ssh <sunet>@login.sherlock.stanford.edu"
fi

echo
echo "Recommended filesystem routing:"
echo "  HOME: small code/config"
echo "  PI_HOME: shared non-purged project assets"
echo "  SCRATCH/PI_SCRATCH: temporary compute data (purgeable)"
echo "  OAK: durable datasets (preferred for long-term)"

echo
if [[ -n "$SUNET" ]]; then
  if [[ -n "$PI_GROUP" ]]; then
    echo "Optional rsync examples:"
    echo "  rsync -avP ./local_data/ ${SUNET}@login.sherlock.stanford.edu:\$OAK/data/"
    echo "  rsync -avP ${SUNET}@login.sherlock.stanford.edu:\$PI_HOME/project/ ./project_copy/"
    echo
    echo "Optional sshfs mount example:"
    echo "  sshfs ${SUNET}@login.sherlock.stanford.edu:/oak/stanford/groups/${PI_GROUP}/ ~/sherlock_oak"
  else
    echo "Tip: pass --pi-group <group> to render group-specific mount example."
  fi
fi

echo
echo "Next: run interactive shell safely (not on login node):"
echo "  srun --mem=32G --pty bash"
