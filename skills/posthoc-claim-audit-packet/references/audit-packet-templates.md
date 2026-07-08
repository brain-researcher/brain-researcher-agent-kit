# Audit packet templates

Three files make the honest post-hoc packet. Shapes below mirror the worked
NeuroMark audit. Fill from the BR surface searches — never invent a sealed hash.

## claim_card.json

```json
{
  "claim_id": "<stable id>",
  "claim_text": "<the claim, scoped to what the evidence licenses>",
  "claim_mode": "exploratory",
  "commitment_card_ref": null,
  "commitment_hash": null,
  "status": "post_hoc",
  "scope": {"dataset": "<id>", "modality": "<e.g. fMRI>"},
  "evidence_tier": "<from verification>"
}
```

- `commitment_card_ref` / `commitment_hash` are `null` when no pre-run card was
  found. If a real card WAS found, put its actual hash here and set
  `status: "pre_registered"`.

## posthoc_registration.json

```json
{
  "run_id": "<id>",
  "pre_run_commitment_card_found": false,
  "searched_surfaces": ["run_get", "run_bundle_get", "artifact_list", "run_logs"],
  "registration_type": "post_hoc",
  "provenance_check": "<result from report_claim_provenance_check>",
  "registered_at": "<timestamp>"
}
```

## evidence_verdicts.json

```json
{
  "claim_id": "<same as claim_card>",
  "verdicts": [
    {"axis": "<e.g. association>", "status": "<supported|weakened|unresolved>", "tier": "<...>"}
  ],
  "binding_axis": "<the weakest axis = the ceiling>"
}
```

## May say / must not say

| Given | May say | Must NOT say |
|---|---|---|
| post_hoc, association evidence | "post-hoc analysis; association observed in <dataset>" | "pre-registered", "confirmatory", "causal", "biomarker" |
| pre_run card found + provenance match | "pre-registered (commitment <hash>)" | anything beyond the evidence tier |
| no card found | "no pre-run commitment card found on searched surfaces" | "pre-registered" |

The rule: a `null` commitment ref is an honest record. A fabricated one is
research misconduct — never synthesize a sealed card.
