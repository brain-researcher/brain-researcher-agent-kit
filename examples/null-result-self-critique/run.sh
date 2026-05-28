#!/usr/bin/env bash
# Demo runner — null result → critique → exploratory follow-up → labeled report.
set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -s "$demo_dir/expected_output/report.md" ]]; then
  echo "TODO: expected_output not yet captured." >&2
  echo "  Wire BR MCP, then chain run_scientific_review on initial_findings.json," >&2
  echo "  follow up with a second pipeline_plan_validate against the proposed" >&2
  echo "  exploratory subgroup, and produce report.md with confirmatory/exploratory labels." >&2
  exit 2
fi

python -m evals.runner --demo null-result-self-critique
