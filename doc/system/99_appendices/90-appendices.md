# 90 — Appendices

## A. Glossary

| Term | Meaning |
| --- | --- |
| Calibration record | The `cal_record_v1` JSON input capturing verification, declared reality, and reconciliation drift for a target. |
| Calibration proposal | A bounded, evidence-backed candidate movement for one or more Eval parameters. |
| Node revision | The `node_revision` in `cal_node_config.json` that pins calibration math for reproducibility. |
| Control envelope | The per-parameter `allowed` / `param_min` / `param_max` / `max_movement` bounds enforced at Gate 2. |
| Gate 1 / 2 / 3 | Sufficiency (auto) / Control Envelope (auto) / Math-Effect Boundary (human approval). |
| `lineage_missing` | Deterministic outcome when DataForge-Local lineage is unreachable; calibration still completes. |

## B. Allowed calibration targets (v0)

13 parameters, each with `max_movement` 0.05 and `allowed=true` in v0.

| # | Parameter | Group | Range |
| --- | --- | --- | --- |
| 1 | `hazard_hidden_uplift_strength` | hazard | 0.05 – 0.50 |
| 2 | `hazard_structural_risk_strength` | hazard | 0.10 – 0.60 |
| 3 | `hazard_occupancy_strength` | hazard | 0.10 – 0.70 |
| 4 | `hazard_support_uplift_strength` | hazard | 0.05 – 0.40 |
| 5 | `hazard_uncertainty_boost` | hazard | 0.05 – 0.40 |
| 6 | `hazard_blocking_threshold` | hazard | 0.50 – 0.95 |
| 7 | `merge_decision_caution_threshold` | merge | 0.10 – 0.50 |
| 8 | `merge_decision_block_threshold` | merge | 0.30 – 0.90 |
| 9 | `occupancy_prior_base` | occupancy | 0.10 – 0.80 |
| 10 | `occupancy_support_uplift` | occupancy | 0.00 – 0.50 |
| 11 | `occupancy_detection_assumption` | occupancy | 0.30 – 0.95 |
| 12 | `occupancy_miss_penalty_strength` | occupancy | 0.10 – 0.70 |
| 13 | `occupancy_null_uncertainty_boost` | occupancy | 0.10 – 0.70 |

Authoritative bounds live in `config/cal_node_config.json`.

## C. Cross-references

- `config/cal_node_config.json` — node config + control envelope.
- `src/eval_cal_node/schemas/` — the `cal_record_v1` input schema.
- `src/eval_cal_node/services/` — pattern extraction, calibration math, gates.
- `src/eval_cal_node/lineage/` — DataForge-Local proposal + gate-decision emission.
- `../../docs/canonical/ecosystem_canonical.md` — ecosystem canonical reference.
- `eval_cal_node_plan_v0_rev3.md` — the originating implementation plan.
