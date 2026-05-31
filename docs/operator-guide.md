# Operator Guide — Eval Cal Node

This guide covers the day-to-day workflow: feeding the node real records and
turning them into reviewable calibration proposals.

> **What it is, in one line:** Eval Cal Node studies the gap between what
> `forge-eval` verified, what `SYSTEM.md` later declared as implemented reality,
> and what reconciliation found drifted — and emits bounded, auditable proposals
> to adjust Eval parameters. It never changes approved Eval math on its own;
> every adoption passes through human **Gate 3**.

## Install

```bash
pip install -e .          # development
# or: pip install <built wheel>
```

This provides the `eval-cal-node` command.

## The loop

```
eval-cal-node record   --input <record.json>      # 1. ingest one slice record
eval-cal-node status                              # 2. check readiness
eval-cal-node propose                             # 3. run Gates 1 & 2, emit proposal artifacts
eval-cal-node review   --proposal <proposal_id>   # 4. human Gate 3: accept / decline
```

By default, records are read from / written to `./records/` and proposal
artifacts to `./proposals/` (override with `--records-dir` / `--proposals-dir`).
Run the commands from a stable working directory so the node accumulates
history across cycles.

### 1. `record` — ingest a slice

```bash
eval-cal-node record --input examples/records/01_forge-eval_run-2026-05-04-a.json
```

- The record is validated against the strict `cal_record_v1` schema.
- `record_id` must equal `sha256(repo + base_commit + head_commit + run_id)`;
  a mismatch is rejected (fail-closed).
- Duplicate records (same `record_id`) are rejected.
- Records whose `recorded_at_revision` differs from the node revision are
  rejected unless you pass `--backfill` (for importing history from a prior
  node revision).

### 2. `status` — honest readiness

```
COLD_START   no records yet
WARMING      have some records, fewer than min_sample_size (5)
OPERATIONAL  enough records; per-parameter candidate/hold status is shown
```

### 3. `propose` — run the autonomous gates

Runs Gate 1 (sufficiency) and Gate 2 (control envelope) over all records and
writes, keyed by a deterministic `proposal_id`:

| Artifact | Contents |
|---|---|
| `<id>_proposal.json` | per-parameter proposed value + direction |
| `<id>_evidence.json` | raw pattern counts behind each proposal |
| `<id>_param_delta.json` | current/proposed values, bounded vs raw delta, bounds |
| `<id>_gate_decision.json` | Gate 1/Gate 2 outcome + final routing per parameter |
| `<id>_approval_request.json` | the Gate 3 packet (only for `gate3_ready` params) |

Routing per parameter is one of `rejected`, `held`, or `gate3_ready`.
If nothing reaches Gate 3, no approval request is written and there is nothing
to review.

### 4. `review` — human Gate 3

```bash
eval-cal-node review --proposal <proposal_id>
```

Prints each proposed change with its evidence and prompts `yes`/`no`.

- **Accept** stamps `<id>_review.json` with `decision: accepted`.
- **Decline** stamps `decision: declined` and computes a *hold-after-decline*
  window: the same proposal will not re-advance until both
  `record_count + hold_after_decline_cycles` and a per-parameter
  `recurrence + min_new_recurrence` are reached. This prevents the node from
  re-pestering you with a proposal you already rejected until materially more
  evidence exists.

## Record format

Each record captures **three surfaces** for one implementation slice. All fields
are required; the schema is strict (`additionalProperties: false`).

| Block | Surface | Purpose |
|---|---|---|
| `slice_ref` | identity | `repo`, `base_commit`, `head_commit`, `run_id` |
| `eval_signals` | **Surface 1 — what Eval said** | hazard score/tier, merge decision, reason codes, estimator outputs |
| `system_md_signals` | **Surface 2 — what SYSTEM.md declared** | declared subsystems updated, declared boundary state |
| `reconciliation_outcome` | **Surface 3 — what actually drifted** | drift found?, drift types, severity, implicated parameters, disposition |

The node's signal comes from `reconciliation_outcome`:

- `implicated_parameters` — which of the 13 calibratable parameters this slice
  bears on. **A parameter only accrues evidence from records that implicate it.**
- `drift_types` — locked v0 vocabulary. The calibration math reacts to four of
  them: `false_block`, `missed_block`, `false_caution`, `missed_caution`. The
  net directional signal for a parameter is
  `missed_block_rate − false_block_rate`. (The remaining drift types —
  `overestimated_hidden`, `occupancy_overcautious`, etc. — are recorded for
  audit but do not, in v0, move a parameter on their own.)

> Note (v0 simplification): a record's `drift_types` are attributed to **every**
> parameter it implicates. If a slice implicates several parameters, give it the
> `drift_types` that genuinely apply to all of them, or split it into focused
> records — as the example set does.

See `src/eval_cal_node/schemas/cal_record_v1.schema.json` for the authoritative
field list and enums, and `examples/records/` for eight ready-to-ingest records.

## Worked example

The `examples/records/` set encodes a realistic early-life scenario: Eval has
been **over-blocking** — five slices across four repos where Eval said `block`
but reconciliation found a `false_block` on `hazard_blocking_threshold`, plus a
few unrelated occupancy/merge cautions that don't yet have enough evidence.

```bash
mkdir demo && cd demo
for f in ../examples/records/*.json; do eval-cal-node record --input "$f"; done
eval-cal-node status      # OPERATIONAL; hazard_blocking_threshold: candidate (5 implicated, 4 repos)
eval-cal-node propose     # gate3_ready: 1 (hazard_blocking_threshold), held: 12
```

`propose` recommends lowering `hazard_blocking_threshold` from **0.80 → 0.75**
(the move is clamped to the parameter's `max_movement` of 0.05), and routes it to
Gate 3. Everything else is held for insufficient evidence — the honest picture
after only eight records.

```bash
eval-cal-node review --proposal <printed id>   # accept or decline
```

## Determinism

For a fixed record set + config + node revision, every artifact is
byte-stable (sorted keys, compact separators, no timestamps or random fields).
Re-running `propose` over the same records yields identical files. This is what
makes proposals auditable.

## What the node will not do

It will not change approved Eval math, rewrite `SYSTEM.md`, approve merges, or
adopt a proposal without Gate 3. Proposals are candidates until a human accepts
them.
