"""ForgeLineage integration for eval-cal-node (Phase 06).

Two surfaces:

- ``emitter.EvalCalLineageEmitter``: non-blocking producer of consumer-side
  lineage records (record + proposal + gate decision nodes; consumed/informed/
  reviewed_by edges).
- ``gate3.LineageGate3Decision``: fail-closed governance check used by Gate 3.

Doctrine:
- Emission is non-blocking — eval-cal-node can ingest a record into degraded
  posture if lineage is unavailable.
- Gate 3 promotion is fail-closed — if the required ``consumed`` edge from the
  forge-eval evidence bundle to the eval-cal-node record is missing, pending,
  or has unknown causality, Gate 3 must not approve.
"""

from eval_cal_node.lineage.emitter import (
    EvalCalLineageEmitter,
    LineageEmissionStatus,
    NullLineageEmitter,
)
from eval_cal_node.lineage.gate3 import (
    LineageGate3Decision,
    check_gate3_lineage,
)

__all__ = [
    "EvalCalLineageEmitter",
    "LineageEmissionStatus",
    "NullLineageEmitter",
    "LineageGate3Decision",
    "check_gate3_lineage",
]
