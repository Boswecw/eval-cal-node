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
