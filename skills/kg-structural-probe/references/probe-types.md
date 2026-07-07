# KG probe types & when to use which tool

All three tools *explore structure*; none *accepts a claim*. Pick by the question.

## `kg_probe(probe_type=...)`

| probe_type | Finds | Reach for it when |
|---|---|---|
| `structural_leverage` | nodes/edges whose position gives them outsized influence | "what's the high-leverage place to intervene / study?" |
| `contradiction_motifs` | recurring shapes where evidence conflicts | "where does the evidence disagree with itself?" |
| `contradiction_frontiers` | the active edge between supported and contested | "what's the current frontier of disagreement?" |
| `assumption_cracks` | load-bearing assumptions that are thinly supported | "what is everyone assuming that isn't well established?" |
| `analogy_transfers` | structurally similar subgraphs in another domain | "is there an analogy from domain A to B?" |

Pass `seed_kg_ids` / `start_kg_ids` (seed-ground them first). Optionally `claim` /
`hypothesis` to focus the probe.

## `kg_multihop_qa`

Use for a **traversal question** spanning multiple hops ("what path connects X to
Y?", "which regions link this task to that disorder?"). Report `degraded` / timeout
verbatim — a truncated traversal is not evidence of absence.

## `refuted_landscape_summary`

Use over a set of structured findings to summarize **supported / refuted /
inconclusive** directions at a glance. `inconclusive` is its own state — never
collapse it into supported or refuted.

## The discipline

Everything here surfaces **leads and structure**. A lead becomes a claim only after
`kg-hypothesis-discovery-and-verification` + a verification verdict. Keep the probe's
output labeled as questions.
