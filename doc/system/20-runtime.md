# 20 — Runtime

## End-to-end flow

A `eval-cal-node record` invocation runs the following deterministic pipeline:

1. **Load + validate** — `config.py` loads `cal_node_config.json` and
   bound-checks it; `validation/` loads the `cal_record_v1` schema and validates
   the inbound record. Failure here is fail-closed (no proposal emitted).
2. **Pattern extraction** — `services/pattern_extractor.py` scans the record (and,
   with `--backfill`, prior records) for recurring drift/alignment signals,
   filtering by `min_sample_size`, `min_recurrence`, and `min_new_recurrence`.
3. **Calibration math** — `services/calibration_math.py` and
   `services/evaluation_spine_calibrator.py` translate qualifying signals into
   candidate parameter movements, applying `sensitivity_factor`, `effect_floor`,
   `max_movement`, and `rounding_digits` so movement stays bounded and rounded.
4. **Gate run** — `services/gate_runner.py` drives `gate1 → gate2 → gate3`:
   - **Gate 1 (Sufficiency)** rejects weak/noisy/incomplete candidates.
   - **Gate 2 (Control Envelope)** rejects candidates that violate policy or the
     configured parameter bounds.
   - **Gate 3 (Math-Effect Boundary)** marks the candidate as **awaiting human
     approval** — it is never auto-approved.
5. **Persist + emit** — `services/artifact_writers.py` writes the versioned
   proposal + decision artifacts; `lineage/emitter.py` emits proposal and
   gate-decision lineage to DataForge-Local (best effort).

## State and idempotency

- `hold_after_decline_cycles` suppresses re-proposing a parameter for a number of
  cycles after a decline, preventing churn.
- Determinism (fixed dataset + config + revision ⇒ identical output) makes a
  re-run idempotent: re-ingesting the same record yields the same proposal id and
  decisions.

## Failure posture

- Schema/config validation failure → fail-closed, no emission.
- DataForge-Local lineage unreachable → `lineage_missing`, the calibration run
  still completes and proposals are still written locally.
