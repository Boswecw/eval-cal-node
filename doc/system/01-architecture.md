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
