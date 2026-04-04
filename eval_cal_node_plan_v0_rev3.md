# Plan v0 — Eval Cal Node
**Revision:** 3
**Date:** 2026-03-06
**Owner:** Charlie
**Status:** Active — ready for implementation
**Scope:** Post-implementation calibration node that learns from the gap between Eval-verified behavior, SYSTEM.md-declared reality, and reconciliation findings. Produces bounded, reviewable calibration proposals. Never directly alters the current approved Eval parameter revision.

---

## 1. Plain-language intent

Eval Cal Node is a separate post-implementation node that studies the gap between what Eval verified, what SYSTEM.md later declares as implemented reality, and what reconciliation shows actually drifted or stayed aligned.

The system can then learn from repeated patterns instead of treating every slice as isolated history.

The node does not replace Eval math or change doctrine. It produces bounded, reviewable calibration proposals that can improve the quality of approved parameter revisions over time.

Expected gains:
- better-calibrated risk and hazard math
- stronger estimates for latent-defect and reviewer-capture behavior
- earlier recognition of repeat drift patterns
- fewer underweighted warning signals
- tighter internal control loop between implementation truth, documented truth, and governed evaluation

---

## 2. The three input surfaces

Eval Cal Node watches three surfaces per implementation slice:

### Surface 1 — What Eval said
The complete A-M artifact chain from a `forge-eval run` against the implementation slice:
- `config.resolved.json`
- `risk_heatmap.json`
- `context_slices.json`
- `review_findings.json`
- `telemetry_matrix.json`
- `occupancy_snapshot.json`
- `capture_estimate.json`
- `hazard_map.json`
- `merge_decision.json`
- `evidence_bundle.json`

Key signals extracted per run:
- `hazard_map.summary.hazard_score` and `hazard_tier`
- `merge_decision.decision` (`allow | caution | block`)
- `merge_decision.reason_codes`
- `capture_estimate.summary.selected_hidden` and `selected_method`
- `occupancy_snapshot.summary` — mean/max `psi_post`, null coverage
- `telemetry_matrix.summary.k_eff`
- `risk_heatmap` — top file risk scores
- Eval parameter revision used (from `config.resolved.json`)

### Surface 2 — What SYSTEM.md declared
The documented implemented state after the session completed. This is the human-authored truth claim about what was built.

Key signals extracted:
- which subsystems/stages were declared updated
- which components were declared newly implemented
- what the declared boundary was after the session

### Surface 3 — What reconciliation found
The structured outcome of comparing Eval's assessment against actual post-implementation reality.

Key signals extracted:
- drift type (overestimated risk, underestimated risk, missed defect class, false block, missed caution)
- severity of the gap
- which Eval parameters were most implicated
- whether drift recurred from prior slices
- final resolved disposition (confirmed drift, false alarm, accepted, deferred)

---

## 3. What the node computes from those surfaces

The calibration signal is the **gap** between Surface 1 and Surface 3, contextualized by Surface 2.

Concretely:

- Eval said `block` → reconciliation found no real risk → `hazard_blocking_threshold` may be too sensitive
- Eval said `allow` → reconciliation found latent defects post-merge → `hazard_hidden_uplift_strength` may be underweighted
- `psi_post` was high → defects were later confirmed real → occupancy prior calibration was appropriate
- `psi_post` was high → defects were later found to be false positives → `occupancy_prior_base` may be too aggressive
- `selected_hidden` was large → no latent defects found → capture estimate is overcautious for this subsystem class
- `k_eff` was low → reviewer coverage was actually adequate → telemetry conservatism may be miscalibrated

Over multiple slices, patterns in these gaps produce calibration candidates.

---

## 4. Hard rules — unchanged from Rev 2

1. Eval Cal Node does not change Eval stage order.
2. Eval Cal Node does not change artifact contracts.
3. Eval Cal Node does not change fail-closed doctrine.
4. Eval Cal Node does not directly rewrite the current approved Eval parameter revision.
5. Eval Cal Node only emits candidate proposals.
6. No learned output becomes part of an approved Eval parameter revision without threshold checks and explicit approval.
7. All outputs must be deterministic for a fixed input dataset and fixed node revision.
8. All proposals must be versioned, evidence-backed, and auditable.

---

## 5. Position in the sequence

```
implementation work occurs
        ↓
forge-eval run → A-M artifact chain emitted  [Surface 1]
        ↓
SYSTEM.md updated to current implemented reality  [Surface 2]
        ↓
reconciliation compares Eval output vs SYSTEM.md declared state
        ↓
reconciliation findings recorded  [Surface 3]
        ↓
Eval Cal Node ingests all three surfaces
        ↓
node runs deterministic calibration analysis
        ↓
Gate 1: sufficiency check (autonomous)
        ↓
Gate 2: control envelope check (autonomous)
        ↓
Gate 3: math-effect boundary (human approval required)
        ↓
accepted proposals may become new approved Eval parameter revision
```

Eval Cal Node is post-implementation and post-reconciliation. It never operates on in-flight implementation state.

---

## 6. Allowed calibration targets (v0)

### Allowed
- `hazard_hidden_uplift_strength`
- `hazard_structural_risk_strength`
- `hazard_occupancy_strength`
- `hazard_support_uplift_strength`
- `hazard_uncertainty_boost`
- `hazard_blocking_threshold`
- `merge_decision_caution_threshold`
- `merge_decision_block_threshold`
- `occupancy_prior_base`
- `occupancy_support_uplift`
- `occupancy_detection_assumption`
- `occupancy_miss_penalty_strength`
- `occupancy_null_uncertainty_boost`

### Deferred to later revision
- `ice_rare_threshold`
- `capture_round_digits`
- reviewer reliability priors
- subsystem-specific penalty multipliers

### Permanently forbidden
- stage sequence
- required artifact list
- schema shapes
- mandatory fail-closed conditions
- authority boundaries
- human approval requirements
- canonical evidence rules

---

## 7. Historical record schema

Each record fed to Eval Cal Node captures one implementation slice. A slice = one `forge-eval run` paired with its reconciliation outcome.

### Required fields per record

```json
{
  "record_id": "<deterministic hash of slice identity>",
  "slice_ref": {
    "repo": "<repo name>",
    "base_commit": "<sha>",
    "head_commit": "<sha>",
    "run_id": "<forge-eval run_id>"
  },
  "eval_parameter_revision": "<approved revision identifier>",
  "eval_signals": {
    "hazard_score": 0.0,
    "hazard_tier": "low|guarded|elevated|high|critical",
    "merge_decision": "allow|caution|block",
    "reason_codes": [],
    "selected_hidden": 0.0,
    "selected_method": "chao1|chao2|ice",
    "chao2_available": true,
    "mean_psi_post": 0.0,
    "max_psi_post": 0.0,
    "null_coverage_ratio": 0.0,
    "k_eff": 0,
    "defect_count": 0,
    "reviewer_count": 0
  },
  "system_md_signals": {
    "declared_subsystems_updated": [],
    "declared_boundary_after": "<text summary>"
  },
  "reconciliation_outcome": {
    "drift_found": true,
    "drift_types": [],
    "severity": "none|minor|moderate|significant",
    "implicated_parameters": [],
    "disposition": "confirmed_drift|false_alarm|accepted|deferred",
    "notes": ""
  },
  "record_version": "cal_record_v1",
  "recorded_at_revision": "<node revision>"
}
```

### Drift type vocabulary (locked v0)

- `false_block` — Eval blocked, reconciliation found no real risk
- `missed_block` — Eval allowed, latent defects found post-merge
- `false_caution` — Eval cautioned, reconciliation found clean
- `missed_caution` — Eval allowed cleanly, moderate drift found
- `overestimated_hidden` — capture estimate was too high vs outcome
- `underestimated_hidden` — capture estimate was too low vs outcome
- `occupancy_overcautious` — psi_post high, defects were false positives
- `occupancy_undercautious` — psi_post low, real defects were missed
- `risk_miscalibrated` — structural risk scores did not match actual change impact

---

## 8. Calibration math (v0 — deliberately simple)

### Principle
The v0 math is rules-based and statistically simple. No opaque model. No ML stack. Deterministic given fixed inputs.

### Step 1 — Pattern extraction
For each calibration target parameter, count across all records where that parameter is implicated:
- `n_false_block` — records where the parameter contributed to a false block
- `n_missed_block` — records where underweighting contributed to a missed block
- `n_total_implicated` — total records implicating this parameter
- `n_total` — total records in the dataset

### Step 2 — Directional signal
```
false_block_rate = n_false_block / n_total_implicated
missed_block_rate = n_missed_block / n_total_implicated
net_direction = missed_block_rate - false_block_rate
```

- `net_direction > 0` → parameter is underweighted → propose increase
- `net_direction < 0` → parameter is overweighted → propose decrease
- `abs(net_direction) < effect_floor` → no meaningful signal → hold

### Step 3 — Bounded delta
```
raw_delta = net_direction * sensitivity_factor
bounded_delta = clamp(raw_delta, -max_movement, +max_movement)
proposed_value = clamp(current_value + bounded_delta, param_min, param_max)
```

All bounds are policy-locked per parameter in the node config. No parameter can move beyond its policy ceiling in a single proposal.

### Step 4 — Evidence quality check
Proposal is eligible only if:
- `n_total_implicated >= min_sample_size` (default: 5)
- `recurrence_count >= min_recurrence` (default: 3 distinct slices)
- `abs(net_direction) >= effect_floor` (default: 0.15)
- no conflicting signal (both `false_block_rate` and `missed_block_rate` high simultaneously → hold, not propose)

---

## 9. Three-gate autonomy model

### Gate 1 — Sufficiency (fully autonomous)

Checks:
- required input completeness (all three surfaces present per record)
- minimum history depth met
- minimum recurrence count met
- deterministic computation succeeded
- effect-size floor cleared
- no conflicting signal

Outcomes:
- **Reject automatically** — weak, noisy, incomplete, or below floor
- **Hold automatically** — more history needed
- **Advance automatically** — sufficiency conditions met

Gate 1 never asks for approval.

### Gate 2 — Control envelope (fully autonomous)

Checks:
- proposed delta within policy-locked bounds per parameter
- no forbidden target implicated
- no doctrine boundary touched
- no contract or stage implication
- no fail-closed behavior implication
- proposed value within `[param_min, param_max]`
- no destabilizing combination across parameters in the same proposal

Outcomes:
- **Reject automatically** — policy violation
- **Hold automatically** — mixed or conflicting signals
- **Advance automatically** — within approved envelope

Gate 2 never asks for approval.

### Gate 3 — Math-effect boundary (human approval required)

Checks:
- current approved parameter value
- proposed value and exact delta
- affected Eval math surfaces
- expected bounded impact narrative
- evidence strength summary
- confirmation all prior gates passed

Outcomes:
- **Ask for approval** — candidate is strong and would change approved Eval math
- **Return to hold** — not yet strong enough
- **Reject automatically** — final blocking condition found

This is the only mandatory human approval boundary.

---

## 10. Output artifacts

### `eval_calibration_proposal.json`
What changes are recommended. Schema-locked. One proposal per eligible parameter.

### `eval_calibration_evidence.json`
Why the node believes the changes are justified. Full pattern extraction results, rates, effect sizes.

### `eval_param_delta.json`
Exact numeric movement being proposed per parameter. Current value, proposed value, bounded delta, policy bounds used.

### `eval_calibration_summary.md`
Human-readable explanation for review. Not schema-locked — derived view only.

### `eval_gate_decision.json`
Record of which gate each proposal reached and the outcome. Includes rejection reason for auto-rejected proposals.

### `eval_approval_request.json` (Gate 3 output only)
Compact approval request artifact containing:
- parameter name
- current approved value
- proposed value
- exact delta
- policy bounds
- net direction and rates
- evidence strength summary
- historical basis (slice count, recurrence count)
- affected Eval math surfaces
- recommendation: accept or decline

---

## 11. Rejection feedback loop

When Gate 3 asks for approval and the human declines:

- The proposal is stamped with `declined` status and archived in `eval_gate_decision.json`
- The same proposal cannot re-advance for `N` subsequent records (default: `hold_after_decline_cycles = 3`)
- Re-eligibility requires meaningfully different evidence — specifically a `recurrence_count` increase of at least `min_new_recurrence = 2` beyond what was present at time of decline
- Trivially similar proposals (same direction, nearly identical rates) are held, not re-escalated

---

## 12. Persistence posture (v0)

All Eval Cal Node records and outputs are **local structured JSON files**. No DataForge write contract required for v0.

Directory structure:
```
/home/charlie/Forge/ecosystem/eval-cal-node/
  records/
    <record_id>.json          # one historical record per slice
  proposals/
    <proposal_id>.json        # one proposal artifact set per gate cycle
  config/
    cal_node_config.json      # node config: bounds, floors, policy
    approved_param_revision.json  # current approved Eval parameter values
  reports/
    <date>_summary.md
```

Persistence is append-only for records. Proposals are immutable once written. Config is versioned.

DataForge integration deferred to a later revision if governance/persistence requirements expand.

---

## 13. Bootstrap and cold-start posture

On day one there are zero historical records. The node handles this explicitly:

- **Below `min_sample_size`:** all Gate 1 checks auto-hold. No proposals emitted. Node reports current record count and how many more are needed.
- **Zero records:** node reports `COLD_START` status and waits.
- **Synthetic seeding:** not supported in v0. All records must come from real implementation slices.
- **Retrospective seeding:** allowed. Prior implementation sessions can be manually recorded if the three surfaces are available in structured form. Use `--backfill` flag on the CLI.

The node is useful from record 5 onward for single-parameter signals. Multi-parameter proposals require more history. The node self-reports readiness.

---

## 14. Determinism requirements

For fixed dataset + node revision + config + policy bounds, Eval Cal Node must emit byte-stable outputs:
- canonical JSON ordering
- no random sampling
- no time-dependent fields in canonical artifacts
- explicit revision stamping on all outputs
- reproducible rounding policy (default: 6 decimal places)

---

## 15. Autonomy doctrine

**Autonomous analysis, autonomous filtering, autonomous evidence assembly, autonomous routing. Explicit approval only at the math-effect boundary.**

The node may autonomously:
- ingest and validate historical records
- run deterministic calibration analysis
- compute candidate parameter deltas
- apply bounds and policy checks
- reject weak proposals
- hold insufficient proposals
- assemble evidence artifacts
- classify proposal status
- route qualified proposals to Gate 3

The node may not autonomously:
- alter the current approved Eval parameter revision
- change numeric behavior on the approved Eval control surface
- rewrite doctrine, stage order, contracts, or fail-closed rules

---

## 16. Implementation slices

### Slice A — Record schema and ingestion CLI
Define and implement the `cal_record_v1` JSON schema. Implement `eval-cal-node record` CLI command that accepts the three input surfaces and writes a validated record to `records/`.

Deliverable: schema file + ingestion CLI + tests.

Prerequisite for all other slices.

### Slice B — Node config and policy bounds
Define `cal_node_config.json` schema and the per-parameter policy bounds for v0 allowed calibration targets. Implement config loading and validation.

Deliverable: config schema + loader + bounds for all 13 allowed parameters.

### Slice C — Pattern extraction and calibration math
Implement deterministic pattern extraction over the record dataset. Implement Step 1–4 calibration math from §8. Produce raw candidate deltas per parameter.

Deliverable: `services/pattern_extractor.py` + `services/calibration_math.py` + tests.

### Slice D — Gate 1 and Gate 2 logic
Implement sufficiency gate and control envelope gate. Implement autonomous reject, hold, and advance routing. Write gate decisions to `eval_gate_decision.json`.

Deliverable: `services/gate1.py` + `services/gate2.py` + gate decision artifact + tests.

### Slice E — Output artifact assembly
Implement deterministic assembly of all output artifacts: proposal, evidence, param delta, gate decision. Implement `eval_approval_request.json` for Gate 3 candidates.

Deliverable: all output artifact writers + schemas + tests.

### Slice F — Gate 3 CLI and approval workflow
Implement `eval-cal-node review` CLI that presents the approval request and captures accept/decline. Implement rejection feedback loop and hold stamping.

Deliverable: Gate 3 CLI + rejection record + tests.

### Slice G — Summary report and cold-start reporting
Implement `eval_calibration_summary.md` generation. Implement cold-start and readiness reporting. Implement `--backfill` flag for retrospective record seeding.

Deliverable: summary generator + cold-start output + backfill path + tests.

---

## 17. Success criteria for v0

Plan v0 Rev 3 is successful if it yields a node that can:

- ingest structured records from real implementation slices
- compute deterministic calibration candidates from three-surface gap analysis
- autonomously reject weak, noisy, or policy-violating candidates
- autonomously hold immature candidates without asking
- produce auditable proposal artifacts automatically
- stop only when adoption would change approved Eval math
- preserve deterministic internal control discipline
- self-report cold-start and readiness status honestly

---

## 18. What this is not

- Not a replacement for canonical Eval math
- Not an autonomous merge approver
- Not a SYSTEM.md rewriter
- Not an ML system in v0
- Not coupled to live implementation runs
- Not a silent self-tuner

---

# VS Code Claude Opus 4.6 — Implementation Prompt

## PREFLIGHT CONTEXT

### What Eval Cal Node is

A standalone post-implementation calibration node in the Forge Ecosystem. It reads three surfaces from completed implementation slices:

1. `forge-eval` A-M artifact chain outputs (what Eval said)
2. SYSTEM.md declared state after the session (what was documented)
3. Reconciliation findings (what actually drifted or aligned)

It computes deterministic calibration proposals for bounded Forge Eval parameters. It never changes the current approved Eval parameter revision directly.

### Repository location

```
/home/charlie/Forge/ecosystem/eval-cal-node/
```

This is a new standalone repository. Create it.

### Tech stack

- Python >= 3.12
- `jsonschema` (Draft 2020-12) for schema validation
- `PyYAML` for config loading
- stdlib only beyond those — no ML stack, no opaque dependencies
- `pytest` for tests
- Same install posture as forge-eval: `pip install -e .` / `pip install --no-build-isolation -e .`

### Doctrine — non-negotiable

1. Deterministic outputs for fixed dataset + config + node revision
2. Fail closed on invalid inputs, schema violations, policy breaches
3. Strict JSON schema contracts (`additionalProperties: false` at root)
4. No silent truncation or coercion
5. Autonomous operation everywhere except the math-effect boundary (Gate 3)
6. All proposals versioned, evidence-backed, auditable

---

## IMPLEMENTATION PROMPT — EXECUTE IN SLICE ORDER

You are implementing **Eval Cal Node**, a standalone post-implementation calibration node for the Forge Ecosystem.

Implement in strict slice order. Do not skip ahead. Each slice has a clear deliverable and exit criteria.

---

### Slice A — Record schema and ingestion CLI

**Objective:** Define the `cal_record_v1` schema and implement the record ingestion command.

**Step A1 — Create repository structure**

```
eval-cal-node/
  pyproject.toml
  README.md
  src/eval_cal_node/
    cli.py
    config.py
    errors.py
    schemas/
      cal_record_v1.schema.json
      cal_node_config.schema.json
    services/
    validation/
      schema_loader.py
      validate_record.py
  records/       # gitignored — runtime data
  proposals/     # gitignored — runtime data
  config/
    cal_node_config.json
  tests/
    test_cli.py
    test_record_schema.py
```

**Step A2 — Implement `cal_record_v1.schema.json`**

The schema must enforce:

```json
{
  "record_id": "string — sha256 of slice_ref fields",
  "slice_ref": {
    "repo": "string",
    "base_commit": "string",
    "head_commit": "string",
    "run_id": "string"
  },
  "eval_parameter_revision": "string",
  "eval_signals": {
    "hazard_score": "number [0,1]",
    "hazard_tier": "enum: low|guarded|elevated|high|critical",
    "merge_decision": "enum: allow|caution|block",
    "reason_codes": "array of strings",
    "selected_hidden": "number >= 0",
    "selected_method": "enum: chao1|chao2|ice",
    "chao2_available": "boolean",
    "mean_psi_post": "number [0,1]",
    "max_psi_post": "number [0,1]",
    "null_coverage_ratio": "number [0,1]",
    "k_eff": "integer >= 0",
    "defect_count": "integer >= 0",
    "reviewer_count": "integer >= 0"
  },
  "system_md_signals": {
    "declared_subsystems_updated": "array of strings",
    "declared_boundary_after": "string"
  },
  "reconciliation_outcome": {
    "drift_found": "boolean",
    "drift_types": "array of enum: false_block|missed_block|false_caution|missed_caution|overestimated_hidden|underestimated_hidden|occupancy_overcautious|occupancy_undercautious|risk_miscalibrated",
    "severity": "enum: none|minor|moderate|significant",
    "implicated_parameters": "array of strings",
    "disposition": "enum: confirmed_drift|false_alarm|accepted|deferred",
    "notes": "string"
  },
  "record_version": "const: cal_record_v1",
  "recorded_at_revision": "string"
}
```

All objects: `additionalProperties: false`. All required fields explicit.

**Step A3 — Implement ingestion CLI**

Command: `eval-cal-node record --input <record.json> [--backfill]`

Behavior:
- Load and validate input against `cal_record_v1` schema
- Compute deterministic `record_id = sha256(repo + base_commit + head_commit + run_id)`
- Verify `record_id` in input matches computed value — fail closed if mismatch
- Check for duplicate `record_id` in `records/` — fail closed if duplicate
- Write validated record to `records/<record_id>.json`
- Emit `RECORDED <record_id>` on success
- Emit structured error and exit non-zero on any failure

`--backfill` flag: allows records older than the current node revision. Without it, records from prior node revisions are rejected.

**Step A4 — Tests**

Required:
1. Valid record ingests correctly
2. Schema violation fails closed
3. `record_id` mismatch fails closed
4. Duplicate record fails closed
5. `--backfill` allows older revision records
6. Without `--backfill`, older revision records are rejected

**Exit criteria for Slice A:** CLI works, schema validates, records persist correctly, all tests pass.

---

### Slice B — Node config and policy bounds

**Objective:** Define the node config schema and load the per-parameter policy bounds for all 13 v0 allowed calibration targets.

**Step B1 — Implement `cal_node_config.schema.json`**

Config schema must enforce:

```json
{
  "node_revision": "string",
  "min_sample_size": "integer >= 1",
  "min_recurrence": "integer >= 1",
  "effect_floor": "number (0,1)",
  "sensitivity_factor": "number > 0",
  "hold_after_decline_cycles": "integer >= 1",
  "min_new_recurrence": "integer >= 1",
  "rounding_digits": "integer [0,12]",
  "parameters": {
    "<param_name>": {
      "current_value": "number",
      "param_min": "number",
      "param_max": "number",
      "max_movement": "number > 0",
      "allowed": "boolean"
    }
  }
}
```

**Step B2 — Implement `config/cal_node_config.json`**

Populate for all 13 allowed parameters with conservative initial bounds:

```json
{
  "node_revision": "cal_node_rev1",
  "min_sample_size": 5,
  "min_recurrence": 3,
  "effect_floor": 0.15,
  "sensitivity_factor": 0.5,
  "hold_after_decline_cycles": 3,
  "min_new_recurrence": 2,
  "rounding_digits": 6,
  "parameters": {
    "hazard_hidden_uplift_strength": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.1,
      "allowed": true
    },
    "hazard_structural_risk_strength": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.1,
      "allowed": true
    },
    "hazard_occupancy_strength": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.1,
      "allowed": true
    },
    "hazard_support_uplift_strength": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.1,
      "allowed": true
    },
    "hazard_uncertainty_boost": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.1,
      "allowed": true
    },
    "hazard_blocking_threshold": {
      "current_value": 0.75,
      "param_min": 0.5,
      "param_max": 0.95,
      "max_movement": 0.05,
      "allowed": true
    },
    "merge_decision_caution_threshold": {
      "current_value": 0.5,
      "param_min": 0.3,
      "param_max": 0.8,
      "max_movement": 0.05,
      "allowed": true
    },
    "merge_decision_block_threshold": {
      "current_value": 0.75,
      "param_min": 0.5,
      "param_max": 0.95,
      "max_movement": 0.05,
      "allowed": true
    },
    "occupancy_prior_base": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.05,
      "allowed": true
    },
    "occupancy_support_uplift": {
      "current_value": 0.2,
      "param_min": 0.0,
      "param_max": 0.5,
      "max_movement": 0.05,
      "allowed": true
    },
    "occupancy_detection_assumption": {
      "current_value": 0.7,
      "param_min": 0.3,
      "param_max": 0.95,
      "max_movement": 0.05,
      "allowed": true
    },
    "occupancy_miss_penalty_strength": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.1,
      "allowed": true
    },
    "occupancy_null_uncertainty_boost": {
      "current_value": 0.5,
      "param_min": 0.1,
      "param_max": 0.9,
      "max_movement": 0.1,
      "allowed": true
    }
  }
}
```

Update `current_value` fields to match the actual approved Eval parameter revision values from the running forge-eval config.

**Step B3 — Implement config loader**

`src/eval_cal_node/config.py`:
- Load and validate `cal_node_config.json` against schema
- Reject unknown parameters in the `parameters` block
- Reject `allowed: false` parameters from calibration targets
- Expose clean Python config object

**Step B4 — Tests**

Required:
1. Valid config loads correctly
2. Unknown parameter in `parameters` block fails closed
3. `allowed: false` parameter is excluded from calibration targets
4. Out-of-range `current_value` (outside `[param_min, param_max]`) fails closed

**Exit criteria for Slice B:** Config loads and validates. Policy bounds are explicit and enforced.

---

### Slice C — Pattern extraction and calibration math

**Objective:** Implement deterministic pattern extraction and the Step 1–4 calibration math.

**Step C1 — Implement `services/pattern_extractor.py`**

For each allowed parameter, scan all records in `records/` and compute:
- `n_false_block` — records where parameter is implicated and drift_type includes `false_block`
- `n_missed_block` — records where parameter is implicated and drift_type includes `missed_block`
- `n_false_caution` — analogous for caution signals
- `n_missed_caution` — analogous
- `n_total_implicated` — total records implicating this parameter
- `n_total` — total records in dataset
- `recurrence_count` — distinct `slice_ref.repo` values where parameter was implicated

Output: one `PatternResult` per parameter.

**Step C2 — Implement `services/calibration_math.py`**

Step 1: rates
```python
false_rate = n_false_block / n_total_implicated  # if > 0
missed_rate = n_missed_block / n_total_implicated
net_direction = missed_rate - false_rate
```

Step 2: effect check
```python
if abs(net_direction) < effect_floor:
    status = "hold"  # no meaningful signal
elif false_rate > 0.3 and missed_rate > 0.3:
    status = "hold"  # conflicting signal
else:
    status = "candidate"
```

Step 3: bounded delta
```python
raw_delta = net_direction * sensitivity_factor
bounded_delta = clamp(raw_delta, -max_movement, +max_movement)
proposed_value = clamp(current_value + bounded_delta, param_min, param_max)
proposed_value = round(proposed_value, rounding_digits)
```

Step 4: evidence quality
```python
if n_total_implicated < min_sample_size:
    status = "hold"
if recurrence_count < min_recurrence:
    status = "hold"
```

All math is deterministic. No random operations.

**Step C3 — Tests**

Required:
1. Pattern extraction produces correct counts from a synthetic record set
2. Net direction computed correctly for false_block-heavy record set
3. Net direction computed correctly for missed_block-heavy record set
4. Conflicting signal (both high) produces `hold`
5. Below `effect_floor` produces `hold`
6. Below `min_sample_size` produces `hold`
7. Below `min_recurrence` produces `hold`
8. Bounded delta does not exceed `max_movement`
9. Proposed value does not exceed `[param_min, param_max]`
10. Deterministic: same records + config → same output

**Exit criteria for Slice C:** Pattern extraction and math are correct, deterministic, and tested.

---

### Slice D — Gate 1 and Gate 2 logic

**Objective:** Implement the two autonomous gates and their routing logic.

**Step D1 — Implement `services/gate1.py`**

Gate 1 — sufficiency:
- Check all required surfaces present in each record
- Check `n_total >= min_sample_size`
- Check `recurrence_count >= min_recurrence`
- Check `abs(net_direction) >= effect_floor`
- Check no conflicting signal
- Route: `reject | hold | advance`

**Step D2 — Implement `services/gate2.py`**

Gate 2 — control envelope:
- Check proposed value within `[param_min, param_max]`
- Check `abs(bounded_delta) <= max_movement`
- Check parameter is in allowed list
- Check no forbidden target implicated
- Check no destabilizing combination (if multiple parameters in same proposal, verify they don't push in opposing directions on the same Eval math surface)
- Route: `reject | hold | advance`

**Step D3 — Write gate decision artifact**

Write `proposals/<proposal_id>_gate_decision.json` after each gate cycle:

```json
{
  "proposal_id": "<deterministic hash>",
  "node_revision": "cal_node_rev1",
  "evaluated_at_record_count": 0,
  "gate1_outcome": "reject|hold|advance",
  "gate1_reason": "string",
  "gate2_outcome": "reject|hold|advance|not_reached",
  "gate2_reason": "string",
  "final_routing": "rejected|held|gate3_ready",
  "parameters_evaluated": []
}
```

**Step D4 — Tests**

Required:
1. Gate 1 rejects when below `min_sample_size`
2. Gate 1 holds when below `min_recurrence`
3. Gate 1 advances when all sufficiency conditions met
4. Gate 2 rejects when proposed value outside policy bounds
5. Gate 2 rejects when parameter not in allowed list
6. Gate 2 advances when within envelope
7. Gate decision artifact written correctly
8. Gate 1 rejection does not reach Gate 2

**Exit criteria for Slice D:** Both gates work correctly. Autonomous routing is deterministic. Gate decision artifacts are written.

---

### Slice E — Output artifact assembly

**Objective:** Implement all output artifacts.

**Step E1 — Implement schemas**

Create schemas for:
- `eval_calibration_proposal.schema.json`
- `eval_calibration_evidence.schema.json`
- `eval_param_delta.schema.json`
- `eval_gate_decision.schema.json`
- `eval_approval_request.schema.json`

All strict (`additionalProperties: false`).

**Step E2 — Implement artifact writers**

One service per artifact type in `services/`:
- `proposal_writer.py`
- `evidence_writer.py`
- `param_delta_writer.py`
- `approval_request_writer.py`

All writers:
- produce deterministic JSON (`sort_keys=True`, compact separators)
- validate output against schema before writing
- fail closed on schema violation

**Step E3 — Tests**

Required:
1. Each artifact validates against its schema
2. Malformed artifact fails schema validation
3. Deterministic: same inputs → byte-identical artifact
4. Proposal artifact includes all required parameter deltas
5. Evidence artifact includes full pattern extraction results
6. Approval request artifact is compact and complete

**Exit criteria for Slice E:** All artifacts write correctly, validate, and are byte-stable.

---

### Slice F — Gate 3 CLI and approval workflow

**Objective:** Implement Gate 3 review CLI and rejection feedback loop.

**Step F1 — Implement `eval-cal-node review` CLI**

Command: `eval-cal-node review --proposal <proposal_id>`

Behavior:
- Load approval request artifact for the proposal
- Display compact summary to terminal
- Prompt: `Accept this proposal? [yes/no]:`
- On `yes`: stamp proposal as `accepted`, write accepted record
- On `no`: stamp proposal as `declined`, apply hold period, write decline record

**Step F2 — Implement rejection feedback loop**

On decline:
- Write decline record with timestamp and current record count
- Set re-eligibility threshold: `required_record_count = current_count + hold_after_decline_cycles`
- Set re-eligibility recurrence: `required_recurrence = decline_recurrence_count + min_new_recurrence`
- Block re-advance until both thresholds are met

**Step F3 — Tests**

Required:
1. Accept stamps proposal correctly
2. Decline stamps proposal correctly and sets hold thresholds
3. Declined proposal does not re-advance until hold thresholds met
4. Declined proposal re-advances when both thresholds met with new evidence

**Exit criteria for Slice F:** Gate 3 CLI works. Rejection loop is enforced.

---

### Slice G — Summary report and cold-start

**Objective:** Implement human-readable summary output and cold-start reporting.

**Step G1 — Implement `eval-cal-node status` CLI**

Reports current node state:
- Total records in dataset
- Records needed for first Gate 1 pass (if below threshold)
- `COLD_START` if zero records
- Per-parameter: current status (hold/candidate/gate3_ready/declined)
- Last proposal cycle results

**Step G2 — Implement summary report generator**

Write `reports/<date>_summary.md` with:
- Record count and date range
- Parameters with active candidates
- Gate outcomes summary
- Pending approval requests
- Recent decline history

**Step G3 — Implement `--backfill` validation**

When `--backfill` is passed to `record` command, allow records from prior node revisions with explicit warning logged per record.

**Step G4 — Tests**

Required:
1. `status` reports `COLD_START` with zero records
2. `status` reports correct counts and thresholds
3. Summary report writes correctly
4. `--backfill` allows older revision records with warning
5. Without `--backfill`, older revision records are rejected

**Exit criteria for Slice G:** Node is fully operational and self-reporting.

---

## Final acceptance criteria

The node is complete when:

- [ ] `eval-cal-node record` ingests and validates records correctly
- [ ] `eval-cal-node status` reports readiness honestly
- [ ] `eval-cal-node review` handles Gate 3 approval and decline
- [ ] Pattern extraction is correct and deterministic
- [ ] Calibration math produces bounded, policy-compliant candidates
- [ ] Gate 1 and Gate 2 route autonomously without human input
- [ ] All five output artifacts write, validate, and are byte-stable
- [ ] Rejection feedback loop enforces hold periods
- [ ] Cold-start and backfill paths work correctly
- [ ] All tests pass
- [ ] Write implementation report to `reports/eval_cal_node_v0_implementation_report.md`

---

## What NOT to do

- Do not touch forge-eval source code
- Do not build an ML stack or opaque model
- Do not add autonomous Gate 3 acceptance — human approval is mandatory there
- Do not write directly to forge-eval's approved parameter revision
- Do not add network dependencies or DataForge write contracts
- Do not use random, UUID without seed, or time-dependent fields in canonical artifacts
- Do not skip slices — implement in order A → G

Proceed now. Start with Slice A.
