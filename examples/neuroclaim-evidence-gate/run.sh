#!/usr/bin/env bash
# Demo runner — neuroclaim_compile honesty gate: one claim per honesty branch.
set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -s "$demo_dir/expected_output/neuroclaim_report_1.json" ]]; then
  echo "expected_output fixtures are missing." >&2
  echo "  Re-capture with BR MCP: for each claim in input/claims.json call" >&2
  echo "  neuroclaim_compile(claim_text=..., population/modality/datasets/workflow_family" >&2
  echo "  from its scope, plan=... when present, extraction_confidence=...) and save each" >&2
  echo "  {\"ok\": true, ...NeuroClaimReportV1...} response as expected_output/neuroclaim_report_<i>.json." >&2
  echo "  See expected_output/_capture_notes.md for how the committed reference set was produced." >&2
  exit 2
fi

python -m evals.runner --demo neuroclaim-evidence-gate
