#!/usr/bin/env bash
# Demo runner — scores the captured literature-grounding fixture.

set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -s "$demo_dir/expected_output/answer.md" ]]; then
  echo "expected_output fixture is missing." >&2
  echo "  Re-capture with BR MCP, then call grounding_resolve + grounding_gate_evidence_basis" >&2
  echo "  against input/question.json and write sanitized outputs into $demo_dir/expected_output/." >&2
  exit 2
fi

python -m evals.runner --demo literature-grounding
