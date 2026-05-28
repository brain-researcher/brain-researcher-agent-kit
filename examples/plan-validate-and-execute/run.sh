#!/usr/bin/env bash
# Demo runner — preflight → validate → review → get-execution-recipe.
set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -s "$demo_dir/expected_output/validate.json" ]]; then
  echo "TODO: expected_output not yet captured." >&2
  echo "  Wire BR MCP, then call plan_preflight + pipeline_plan_validate + " >&2
  echo "  pipeline_plan_review + get_execution_recipe against input/plan.json." >&2
  exit 2
fi

python -m evals.runner --demo plan-validate-and-execute
