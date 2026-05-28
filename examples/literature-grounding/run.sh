#!/usr/bin/env bash
# Demo runner — captures BR MCP responses for the literature-grounding intent chain.
# Currently exits 2 (fixture not captured); flip to a real run once BR MCP credentials
# and a live server are wired into the kit environment.

set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -s "$demo_dir/expected_output/answer.md" ]]; then
  echo "TODO: expected_output not yet captured." >&2
  echo "  Wire BR MCP server, then call grounding_resolve + grounding_gate_evidence_basis" >&2
  echo "  against input/question.json and write outputs into $demo_dir/expected_output/." >&2
  exit 2
fi

python -m evals.runner --demo literature-grounding
