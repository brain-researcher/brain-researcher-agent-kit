#!/usr/bin/env bash
set -euo pipefail

DIR=""
USER_NAME=""
GROUP_NAME=""  # e.g. oak_<pi_group> — supply via --group
RECURSIVE=1
APPLY=0

usage() {
  cat <<'USAGE'
Usage:
  restrict_acl.sh --dir <path> --user <sunetid> [--group <group>] [--no-recursive] [--apply]

Description:
  Restrict ACLs on a dataset directory by granting rwx to one user and removing group access.

Safety:
  Dry-run by default. Use --apply to execute setfacl commands.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      DIR="${2:-}"
      shift 2
      ;;
    --user)
      USER_NAME="${2:-}"
      shift 2
      ;;
    --group)
      GROUP_NAME="${2:-}"
      shift 2
      ;;
    --no-recursive)
      RECURSIVE=0
      shift
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

if [[ -z "$DIR" || -z "$USER_NAME" ]]; then
  echo "Error: --dir and --user are required." >&2
  usage >&2
  exit 2
fi

if [[ ! -d "$DIR" ]]; then
  echo "Error: directory does not exist: $DIR" >&2
  exit 1
fi

if [[ "$APPLY" -eq 1 ]] && ! command -v setfacl >/dev/null 2>&1; then
  echo "Error: setfacl is not installed or not in PATH." >&2
  exit 1
fi

run() {
  echo "+ $*"
  if [[ "$APPLY" -eq 1 ]]; then
    "$@"
  fi
}

echo "Applying ACL policy"
echo "  dir:   $DIR"
echo "  user:  $USER_NAME"
echo "  group: $GROUP_NAME"
echo "  recursive: $RECURSIVE"
if [[ "$APPLY" -eq 0 ]]; then
  echo "Mode: dry-run (use --apply to execute)"
else
  echo "Mode: apply"
fi

if [[ "$RECURSIVE" -eq 1 ]]; then
  run setfacl -R -m "u:${USER_NAME}:rwx" "$DIR"
  run setfacl -R -d -m "u:${USER_NAME}:rwx" "$DIR"
  run setfacl -R -m "g:${GROUP_NAME}:---" "$DIR"
  run setfacl -R -d -m "g:${GROUP_NAME}:---" "$DIR"
else
  run setfacl -m "u:${USER_NAME}:rwx" "$DIR"
  run setfacl -d -m "u:${USER_NAME}:rwx" "$DIR"
  run setfacl -m "g:${GROUP_NAME}:---" "$DIR"
  run setfacl -d -m "g:${GROUP_NAME}:---" "$DIR"
fi

echo "Done."
