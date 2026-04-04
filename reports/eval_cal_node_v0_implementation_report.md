# Eval Cal Node v0 Implementation Report

## 1. Executive verdict

Implemented.

All 7 slices (A-G) are complete. 51 tests pass. All acceptance criteria from the plan are met.

## 2. Repository

```
/home/charlie/Forge/ecosystem/eval-cal-node/
```

New standalone repository. Python >= 3.12, jsonschema, PyYAML. No ML stack.

## 3. Implementation summary by slice

### Slice A — Record schema and ingestion CLI

- `src/eval_cal_node/schemas/cal_record_v1.schema.json` — Draft 2020-12, strict `additionalProperties: false`
- `src/eval_cal_node/validation/validate_record.py` — SHA-256 record_id computation, schema validation, duplicate detection, revision enforcement
- `src/eval_cal_node/cli.py` — `eval-cal-node record --input <file> [--backfill]`
- `src/eval_cal_node/errors.py` — CalNodeError hierarchy
- 12 tests (6 required + 6 edge cases)

### Slice B — Node config and policy bounds

- `src/eval_cal_node/schemas/cal_node_config.schema.json` — config schema
- `config/cal_node_config.json` — all 13 allowed parameters with actual forge-eval production values
- `src/eval_cal_node/config.py` — config loader with out-of-range validation
- 6 tests (4 required + 2 extra)

Actual parameter values sourced from `forge-eval/repo/src/forge_eval/config.py`:

| Parameter | Current Value |
|-----------|--------------|
| hazard_hidden_uplift_strength | 0.20 |
| hazard_structural_risk_strength | 0.30 |
| hazard_occupancy_strength | 0.35 |
| hazard_support_uplift_strength | 0.15 |
| hazard_uncertainty_boost | 0.12 |
| hazard_blocking_threshold | 0.80 |
| merge_decision_caution_threshold | 0.20 |
| merge_decision_block_threshold | 0.60 |
| occupancy_prior_base | 0.45 |
| occupancy_support_uplift | 0.20 |
| occupancy_detection_assumption | 0.70 |
| occupancy_miss_penalty_strength | 0.35 |
| occupancy_null_uncertainty_boost | 0.30 |

### Slice C — Pattern extraction and calibration math

- `src/eval_cal_node/services/pattern_extractor.py` — deterministic pattern extraction, sorted record loading
- `src/eval_cal_node/services/calibration_math.py` — Step 1-4 calibration math, bounded deltas, conflict detection
- 10 tests (all 10 required)

### Slice D — Gate 1 and Gate 2 logic

- `src/eval_cal_node/services/gate1.py` — sufficiency gate (fully autonomous)
- `src/eval_cal_node/services/gate2.py` — control envelope gate with allowed/forbidden target lists, surface group destabilization check
- `src/eval_cal_node/services/gate_runner.py` — gate orchestrator, writes `_gate_decision.json`
- 8 tests (all 8 required)

### Slice E — Output artifact assembly

- 5 JSON schemas: `eval_calibration_proposal`, `eval_calibration_evidence`, `eval_param_delta`, `eval_gate_decision`, `eval_approval_request`
- `src/eval_cal_node/services/artifact_writers.py` — 4 deterministic writers (proposal, evidence, param_delta, approval_request)
- All writers validate against schema before writing
- All output is `sort_keys=True, separators=(",", ":")`
- 6 tests (all 6 required)

### Slice F — Gate 3 CLI and approval workflow

- `src/eval_cal_node/services/gate3.py` — `eval-cal-node review --proposal <id>`, accept/decline, hold thresholds
- Rejection feedback loop: `hold_after_decline_cycles` + `min_new_recurrence` thresholds
- `is_proposal_held()` for re-eligibility checking
- 4 tests (all 4 required)

### Slice G — Summary report and cold-start

- `src/eval_cal_node/services/status.py` — `eval-cal-node status`, COLD_START/WARMING/OPERATIONAL reporting
- `generate_summary_report()` — markdown summary with per-parameter status
- 5 tests (all 5 required)

## 4. Test results

```bash
.venv/bin/python -m pytest tests/ -v
```

51 passed, 0 failed, 0 skipped.

| Test file | Count |
|-----------|-------|
| test_record_schema.py | 12 |
| test_config.py | 6 |
| test_calibration.py | 10 |
| test_gates.py | 8 |
| test_artifacts.py | 6 |
| test_gate3.py | 4 |
| test_status.py | 5 |
| **Total** | **51** |

## 5. Doctrine compliance

| Requirement | Status |
|-------------|--------|
| Deterministic outputs for fixed dataset + config | Met — sorted keys, compact JSON, no random/time fields |
| Fail closed on invalid inputs | Met — schema validation, record_id mismatch, duplicate, revision |
| Strict JSON schema contracts | Met — additionalProperties: false on all schemas |
| No silent truncation | Met — explicit errors on all violations |
| Autonomous except Gate 3 | Met — Gates 1-2 fully autonomous, Gate 3 requires human |
| All proposals versioned and auditable | Met — proposal_id, node_revision, record_count in all artifacts |
| Does not touch forge-eval | Met — standalone repo, no forge-eval imports |
| No ML stack | Met — stdlib + jsonschema + PyYAML only |

## 6. File inventory

### Source files

```
src/eval_cal_node/
  __init__.py
  cli.py
  config.py
  errors.py
  schemas/
    __init__.py
    cal_record_v1.schema.json
    cal_node_config.schema.json
    eval_calibration_proposal.schema.json
    eval_calibration_evidence.schema.json
    eval_param_delta.schema.json
    eval_gate_decision.schema.json
    eval_approval_request.schema.json
  services/
    __init__.py
    artifact_writers.py
    calibration_math.py
    gate1.py
    gate2.py
    gate3.py
    gate_runner.py
    pattern_extractor.py
    status.py
  validation/
    __init__.py
    schema_loader.py
    validate_record.py
```

### Config and test files

```
config/cal_node_config.json
tests/
  __init__.py
  helpers.py
  test_record_schema.py
  test_config.py
  test_calibration.py
  test_gates.py
  test_artifacts.py
  test_gate3.py
  test_status.py
```

## 7. Remaining open items

None. All acceptance criteria are met.

## 8. Recommended next actions

- Ingest first real implementation slice records from completed forge-eval runs
- After 5+ records, run calibration analysis and verify Gate 1/2 routing
- Consider retrospective backfill from prior Pack A-M implementation sessions
