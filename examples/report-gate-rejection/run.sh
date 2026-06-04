#!/usr/bin/env bash
# Demo runner — weak evidence → gate downgrades → report blocked.
set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -s "$demo_dir/expected_output/gate_result.json" ]]; then
  echo "expected_output fixture is missing." >&2
  echo "  Re-capture with BR MCP, then call grounding_gate_evidence_basis with" >&2
  echo "  input/weak_evidence_basis.json and then call scientific_report_generate" >&2
  echo "  with halt_on_review_block=True. Capture sanitized gate_result.json, the report-attempt" >&2
  echo "  log, and the kit's degraded-mode handoff." >&2
  exit 2
fi

python -m evals.runner --demo report-gate-rejection
