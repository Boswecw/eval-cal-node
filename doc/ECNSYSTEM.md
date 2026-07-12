        # eval-cal-node - Compiled System Reference

        **Designation:** ECN
        **Document role:** Canonical compiled technical reference for eval-cal-node
        **Source:** `doc/system/`
        **Build command:** `bash doc/system/BUILD.sh`
        **Document version:** 2.0 (2026-06-22) - canonical compliance migration
        **Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

        > **Generated artifact warning:** `doc/ECNSYSTEM.md` is assembled output. Edit
        > the source modules under `doc/system/` and rebuild. Hand edits to the
        > compiled artifact are overwritten by the next build.

        Assembly contract:

        - Command: `bash doc/system/BUILD.sh`
        - Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
        - Primary output: `doc/ECNSYSTEM.md`

        This `doc/system/` tree is the canonical source of truth for eval-cal-node. It uses
        explicit **truth classes**: canonical facts define repo role, authority
        boundaries, contract behavior, runtime behavior, and verification doctrine;
        snapshot facts are dated, audit-derived counts and current implementation
        inventory that may drift between audits.

        | Part | File | Contents |
        | --- | --- | --- |
        | §1 | `00_overview/00-overview.md` | 00 — Overview |
| §2 | `00_overview/01-architecture.md` | 01 — Architecture |
| §3 | `10_service-contract/10-service-contract.md` | 10 — Service Contract |
| §4 | `20_runtime/20-runtime.md` | 20 — Runtime |
| §5 | `30_dependencies/30-dependencies.md` | 30 — Dependencies |
| §6 | `40_governance/40-governance.md` | 40 — Governance |
| §7 | `50_operations/50-operations.md` | 50 — Operations |
| §8 | `99_appendices/90-appendices.md` | 90 — Appendices |

        ## Quick Assembly

        ```bash
        bash doc/system/BUILD.sh
        ```

---

# 00 — Overview

> **System identity — bds family (Boswell Digital Solutions business system, local-systems tier).** Eval Cal Node is the post-implementation calibration node for the Forge ecosystem, operating as a standalone CLI subsystem in `ecosystem/local-systems`.

## Identity

**Eval Cal Node** is the post-implementation **calibration node** for the Forge
ecosystem. It is a standalone CLI subsystem under
`ecosystem/local-systems/eval-cal-node`, independent of any sibling repo's
runtime.

## Role

Eval Cal Node studies the gap between three sources of truth:

1. what **forge-eval** verified for a target repo,
2. what that repo's `SYSTEM.md` declared as implemented reality, and
3. what reconciliation found actually **drifted** or **aligned**.

From that gap it produces bounded, reviewable **calibration proposals** for Eval
parameters — never silent parameter changes.

## Authority boundary

Eval Cal Node's authority is **proposal emission only**. It does **not** alter
the approved Eval parameter revision directly. Every proposed change is a
*candidate*; nothing becomes part of an approved revision without explicit
**Gate 3** human approval (see `40-governance.md`).

## What it is not

- Not an Eval stage — it does not change stage order, artifact contracts, or the
  fail-closed doctrine of forge-eval.
- Not a rewriter — it never directly rewrites the current approved Eval parameter
  revision.
- Not autonomous at the math boundary — the only mandatory approval gate (Gate 3)
  is human.

## Boundary diagram

```
forge-eval (verification)  ─┐
SYSTEM.md (declared truth) ─┼─▶  Eval Cal Node  ──▶  candidate calibration proposals
reconciliation (drift)     ─┘     (Gate 1/2 auto,        (Gate 3 = human approval)
                                   Gate 3 human)
```

Deep references: `config/cal_node_config.json`,
`../../docs/canonical/ecosystem_canonical.md`.

---

# 01 — Architecture

## High-level shape

Eval Cal Node is a deterministic pipeline that turns calibration **records** into
gated calibration **proposals**. It is organised as a thin CLI over a service
layer, with validation at the edge and lineage emission at the tail.

```
CLI (cli.py)
  └─ validation/        schema-load + validate the inbound calibration record
  └─ services/
        pattern_extractor      detect recurring drift/alignment signals
        calibration_math       compute bounded parameter movement candidates
        evaluation_spine_calibrator   map signals → spine parameters
        gate_runner ─ gate1 → gate2 → gate3   the three-gate evaluation
        artifact_writers       write versioned proposal + decision artifacts
        status                 node status / proposal review read model
  └─ lineage/
        emitter, gate3         emit proposal + gate-decision lineage to DataForge-Local
  └─ contracts/           evaluation_spine contract surface
  └─ config.py            load + bound-check cal_node_config.json
```

## Determinism

For a fixed (dataset + config + node revision) the outputs are deterministic:
the same records and `cal_node_config.json` (with the same `node_revision`)
always yield the same proposals and decisions. This is a hard contract — it makes
proposals reproducible and auditable.

## The three-gate model (authority spine)

Every candidate proposal passes through three gates in order:

| Gate | Name | Mode | Rejects |
| --- | --- | --- | --- |
| Gate 1 | Sufficiency | autonomous | weak / noisy / incomplete proposals |
| Gate 2 | Control Envelope | autonomous | policy- or bound-violating proposals |
| Gate 3 | Math-Effect Boundary | **human approval** | anything not explicitly approved |

Gates 1–2 are fail-closed filters. Gate 3 is the single mandatory human boundary:
no proposal crosses into an approved Eval parameter revision without it.

## Lineage posture

The node emits its proposal and gate-decision provenance to DataForge-Local via
`lineage/emitter.py` and `lineage/gate3.py` (base URL `http://127.0.0.1:8005`).
Lineage is **best-effort and non-blocking**: when DataForge-Local is unreachable
the emitter returns `lineage_missing` deterministically rather than failing the
calibration run.

---

# 10 — Service Contract

Eval Cal Node exposes a single CLI entrypoint, `eval-cal-node`, installed via
`pip install -e .`.

## Commands

| Command | Purpose |
| --- | --- |
| `eval-cal-node record --input <record.json> [--backfill]` | Ingest a calibration record, run the pipeline, and emit any resulting candidate proposals. |
| `eval-cal-node status` | Report node status: revision, recent proposals, and gate posture. |
| `eval-cal-node review --proposal <proposal_id>` | Review a specific Gate-3 proposal awaiting human approval. |

## Inputs

- **Calibration record** — a JSON document conforming to the
  `cal_record_v1` schema (`src/eval_cal_node/schemas/`). Validated at ingest by
  `validation/validate_record.py`; invalid records are rejected fail-closed.
- **Node config** — `config/cal_node_config.json`, which declares the node
  revision, sufficiency thresholds, and the per-parameter bounds (`param_min`,
  `param_max`, `max_movement`, `allowed`).

## Outputs

- **Candidate calibration proposals** — versioned, evidence-backed proposals for
  one or more allowed Eval parameters. Each carries the signals that motivated
  it, the proposed bounded movement, and its gate decisions.
- **Gate decisions** — the Gate 1/2/3 outcome record for each proposal.
- **Lineage** — proposal and decision nodes emitted to DataForge-Local (best
  effort; see `30-dependencies.md`).

## Contract guarantees

- Proposals are **candidates only** — emission never mutates an approved Eval
  parameter revision.
- Outputs are **deterministic** for a fixed record set + config + node revision.
- Every proposal is **versioned and auditable**, with its evidence retained.
- Movement is **bounded** — no proposal can exceed a parameter's configured
  `max_movement` or step outside `[param_min, param_max]`.

---

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

### Evaluation Spine calibration lineage (opt-in)

The Evaluation Spine calibrator (`services/evaluation_spine_calibrator.py`,
`calibrate_forge_eval_bundle_file`) optionally emits cross-producer lineage after writing an
`eval_calibration_report`, via `lineage/spine_emit.py` (`emit_calibration_lineage`). It emits an
`eval_cal_record` node plus a `consumed` edge from the upstream forge-eval evidence-bundle node —
the link a downstream consumer (ForgeCommand's self-healing gate-walk) traverses. It discovers the
bundle node by matching `forge_eval_run_id` over `list_nodes("forge_eval_evidence_bundle")`, and
sets the record's `record_id` to the `calibration_report_id` so ForgeMath can later find this node.
**Default-OFF + fail-soft:** emits only when `EVAL_CAL_LINEAGE_URL` is set; any failure is logged
and calibration still completes (the calibrator itself stays transport-free).

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

---

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

---

# 40 — Governance

## Authority boundary

Eval Cal Node's authority is **bounded to candidate emission**. It analyses
post-implementation calibration signals and proposes parameter movements; it has
**no authority to change an approved Eval parameter revision**. That authority
remains with the human approver at Gate 3 and the owning Eval authority.

## The three-gate autonomy model

| Gate | Boundary | Autonomy | Rule |
| --- | --- | --- | --- |
| Gate 1 | Sufficiency | autonomous | Reject weak, noisy, or incomplete proposals. |
| Gate 2 | Control Envelope | autonomous | Reject proposals that violate policy or configured bounds. |
| Gate 3 | Math-Effect Boundary | **human** | **Mandatory** approval; nothing crosses into an approved revision without it. |

Gates 1–2 narrow the candidate set deterministically. Gate 3 is the single,
non-negotiable human approval boundary — the point at which a candidate could
affect Eval math.

## Hard rules (invariants)

- Does **not** change Eval stage order, artifact contracts, or fail-closed
  doctrine.
- Does **not** directly rewrite the current approved Eval parameter revision.
- Emits **candidate proposals only**.
- Outputs are **deterministic** for a fixed dataset + config + node revision.
- Every proposal is **versioned, evidence-backed, and auditable**.

## Change control

- Calibration behaviour is governed by `config/cal_node_config.json`; changing
  the `node_revision` is the explicit, auditable way to evolve calibration math.
- Per-parameter `allowed`, `param_min`, `param_max`, and `max_movement` form the
  control envelope enforced at Gate 2.
- Proposal and gate-decision provenance is emitted to DataForge-Local lineage for
  audit (best effort).

## Ownership

Owner: Charlie (Forge ecosystem). Registry posture: a governed local-systems
subsystem (proposed designation `ECN`).

---

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

---

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
