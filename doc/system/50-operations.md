# 50 — Operations

## Install

```bash
pip install -e .
```

Exposes the `eval-cal-node` console entrypoint.

## Commands

```bash
# Ingest a calibration record (optionally backfilling from prior records)
eval-cal-node record --input <record.json> [--backfill]

# Node status: revision, recent proposals, gate posture
eval-cal-node status

# Review a Gate-3 proposal awaiting human approval
eval-cal-node review --proposal <proposal_id>
```

## Configuration

All operational tuning lives in `config/cal_node_config.json`:

- `node_revision` — calibration math revision (change = explicit, auditable evolution).
- `min_sample_size`, `min_recurrence`, `min_new_recurrence` — sufficiency thresholds.
- `effect_floor`, `sensitivity_factor`, `rounding_digits` — bounded-movement math.
- `hold_after_decline_cycles` — anti-churn hold after a declined proposal.
- `parameters.*` — per-target control envelope (`current_value`, `param_min`,
  `param_max`, `max_movement`, `allowed`).

## Determinism + audit

- A run is reproducible: fixed record set + config + `node_revision` ⇒ identical
  proposals and decisions (same proposal ids).
- Proposals and decisions are written as versioned artifacts; provenance is
  emitted to DataForge-Local lineage when reachable.

## Documentation assembly

This `doc/system/` tree assembles into the canonical artifact:

```bash
bash doc/system/BUILD.sh          # -> doc/ECNSYSTEM.md (validated during assembly)
bash doc/system/validate_snapshots.sh
```

## Health / degraded modes

- DataForge-Local unreachable → lineage `lineage_missing`; calibration still
  completes and proposals are still written.
- Invalid record or config → fail-closed; no proposal emitted, non-zero exit.
