#!/usr/bin/env bash
# Demo runner — multi-tool handoff with explicit provenance chain.
set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -s "$demo_dir/expected_output/handoff_chain.json" ]]; then
  echo "TODO: expected_output not yet captured." >&2
  echo "  Wire BR MCP, then execute the chain documented in input/cross_tool_request.json" >&2
  echo "  and record per-step output_artifact_sha256 into handoff_chain.json." >&2
  exit 2
fi

python -m evals.runner --demo cross-tool-handoff
