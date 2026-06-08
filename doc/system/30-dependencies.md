# 30 — Dependencies

## Upstream (sources)

- **forge-eval** — the evaluation framework whose verification results, together
  with a target repo's declared `SYSTEM.md` reality and reconciliation drift,
  form the calibration record Eval Cal Node consumes. Eval Cal Node is a
  *consumer of Eval outcomes*, not part of the Eval stage pipeline.
- **Calibration record (`cal_record_v1`)** — the JSON contract at the ingest
  boundary (`src/eval_cal_node/schemas/`).

## Downstream (sinks)

- **DataForge-Local lineage** (`http://127.0.0.1:8005`, `/api/v1/lineage/*`) —
  `lineage/emitter.py` and `lineage/gate3.py` emit proposal and gate-decision
  provenance nodes. This is **best-effort**: an unreachable or unmounted lineage
  surface yields `lineage_missing` and does not block calibration.
  > Operational note: the lineage surface must be mounted on DataForge-Local for
  > emission to land; absent it, provenance is silently skipped.
- **Eval parameter revision (indirect)** — proposals are *candidates* for the
  approved Eval parameter set. Eval Cal Node never writes that revision; approval
  flows through the Gate-3 human boundary and the owning Eval authority.

## Configuration

- `config/cal_node_config.json` — node revision, sufficiency thresholds
  (`min_sample_size`, `min_recurrence`, `min_new_recurrence`,
  `hold_after_decline_cycles`), math controls (`effect_floor`,
  `sensitivity_factor`, `rounding_digits`), and the per-parameter bound table.

## Runtime / packaging

- Python, packaged via `pyproject.toml` (`pip install -e .`), exposing the
  `eval-cal-node` console entrypoint. Offline-first: no network dependency is
  required for a calibration run to succeed (lineage is optional).
