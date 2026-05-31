"""eval-cal-node consumer-side ForgeLineage emitter."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _ensure_sdk_on_path() -> None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[5] / "contracts" / "forge_lineage" / "sdk",
        Path.home() / "Forge" / "ecosystem" / "contracts" / "forge_lineage" / "sdk",
    ]
    for c in candidates:
        if c.exists() and str(c) not in sys.path:
            sys.path.insert(0, str(c))
            return


def _load_sdk():
    """Import the ForgeLineage SDK lazily.

    The SDK is a Forge-monorepo dependency that is not available when
    eval-cal-node is installed/checked out standalone. Importing it lazily
    keeps this module importable everywhere; the emit_* methods wrap calls in
    try/except so a missing SDK degrades to ``lineage_missing`` rather than
    breaking ingestion.
    """
    _ensure_sdk_on_path()
    from forge_lineage_sdk import LineageClient, LocalOutcome
    from forge_lineage_sdk.builders import build_edge, build_envelope, build_node
    return LineageClient, LocalOutcome, build_edge, build_envelope, build_node


@dataclass
class LineageEmissionStatus:
    record_node_id: str | None = None
    proposal_node_id: str | None = None
    gate_decision_node_id: str | None = None
    consumed_edge_id: str | None = None
    informed_edge_id: str | None = None
    reviewed_by_edge_id: str | None = None
    outcome: str = "lineage_missing"
    error: str | None = None


class EvalCalLineageEmitter:
    WRITER_IDENTITY = "eval-cal-node"
    SOURCE_SYSTEM = "eval-cal-node"

    def __init__(self, client: LineageClient) -> None:
        self._client = client

    @classmethod
    def from_env(
        cls,
        *,
        base_url: str = "http://127.0.0.1:8005",
        writer_token: str = "local-eval-cal-node",
    ) -> "EvalCalLineageEmitter":
        LineageClient = _load_sdk()[0]
        client = LineageClient(
            base_url=base_url,
            writer_identity=cls.WRITER_IDENTITY,
            writer_token=writer_token,
        )
        return cls(client)

    def emit_record_consumed(
        self,
        *,
        record_id: str,
        forge_eval_evidence_bundle_node_id: str,
        source_evidence_bundle_id: str,
        source_payload_hash: str | None = None,
        trace_id: str | None = None,
        ingested_at: str | None = None,
    ) -> LineageEmissionStatus:
        """Emit the eval_cal_record node + the consumed edge from the producer's
        evidence bundle. Non-blocking."""
        try:
            return self._emit_record_consumed(
                record_id=record_id,
                forge_eval_evidence_bundle_node_id=forge_eval_evidence_bundle_node_id,
                source_evidence_bundle_id=source_evidence_bundle_id,
                source_payload_hash=source_payload_hash,
                trace_id=trace_id,
                ingested_at=ingested_at,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "eval-cal-node lineage emission raised; raw ingestion continues",
                exc_info=exc,
            )
            return LineageEmissionStatus(
                outcome="lineage_missing", error=f"{type(exc).__name__}: {exc}"
            )

    def emit_proposal_and_gate_decision(
        self,
        *,
        record_node_id: str,
        proposal_id: str,
        gate: str,
        outcome: str,
        decided_at: str,
        block_reason_class: str | None = None,
        trace_id: str | None = None,
    ) -> LineageEmissionStatus:
        try:
            return self._emit_proposal_and_decision(
                record_node_id=record_node_id,
                proposal_id=proposal_id,
                gate=gate,
                outcome=outcome,
                decided_at=decided_at,
                block_reason_class=block_reason_class,
                trace_id=trace_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "eval-cal-node proposal/gate lineage emission raised", exc_info=exc
            )
            return LineageEmissionStatus(
                outcome="lineage_missing", error=f"{type(exc).__name__}: {exc}"
            )

    # ---- internals ----

    def _emit_record_consumed(
        self,
        *,
        record_id: str,
        forge_eval_evidence_bundle_node_id: str,
        source_evidence_bundle_id: str,
        source_payload_hash: str | None,
        trace_id: str | None,
        ingested_at: str | None,
    ) -> LineageEmissionStatus:
        _, LocalOutcome, build_edge, build_envelope, build_node = _load_sdk()
        trace = trace_id or f"trace:eval-cal-node:{record_id}"
        record_payload: dict[str, Any] = {
            "schema_version": "eval_cal_record.v1",
            "record_id": record_id,
            "ingested_at": ingested_at or "2026-05-04T15:00:00Z",
            "source_evidence_bundle_id": source_evidence_bundle_id,
        }
        if source_payload_hash:
            record_payload["source_payload_hash"] = source_payload_hash

        record_node = build_node(
            node_type="eval_cal_record",
            payload_schema_id="eval_cal_record",
            payload_schema_version="v1",
            payload=record_payload,
            source_system=self.SOURCE_SYSTEM,
            source_component="eval-cal-node/ingest",
            trace_id=trace,
            writer_identity=self.WRITER_IDENTITY,
            stable_source_id=f"eval-cal-node:record:{record_id}",
        )
        consumed_edge = build_edge(
            source_node_id=forge_eval_evidence_bundle_node_id,
            target_node_id=record_node["node_id"],
            edge_type="consumed",
            causality_class="deterministic",
            effect_class="calibration",
            trace_id=trace,
            writer_identity=self.WRITER_IDENTITY,
            created_by_system=self.SOURCE_SYSTEM,
            stable_source_id=f"{forge_eval_evidence_bundle_node_id}->{record_node['node_id']}",
        )
        envelope = build_envelope(
            writer_identity=self.WRITER_IDENTITY,
            trace_id=trace,
            nodes=[record_node],
            edges=[consumed_edge],
        )
        result = self._client.emit_envelope(envelope)

        if result.outcome in (LocalOutcome.accepted, LocalOutcome.accepted_duplicate):
            return LineageEmissionStatus(
                record_node_id=record_node["node_id"],
                consumed_edge_id=consumed_edge["edge_id"],
                outcome="lineage_available",
            )
        # If the producer's evidence-bundle node hasn't arrived yet, the edge
        # will be parked as pending — surface that as lineage_pending.
        if result.outcome == LocalOutcome.pending:
            return LineageEmissionStatus(
                record_node_id=record_node["node_id"],
                consumed_edge_id=consumed_edge["edge_id"],
                outcome="lineage_pending",
            )
        return LineageEmissionStatus(
            record_node_id=record_node["node_id"],
            consumed_edge_id=consumed_edge["edge_id"],
            outcome="lineage_degraded",
            error=(result.error.message if result.error else f"non-accept: {result.outcome}"),
        )

    def _emit_proposal_and_decision(
        self,
        *,
        record_node_id: str,
        proposal_id: str,
        gate: str,
        outcome: str,
        decided_at: str,
        block_reason_class: str | None,
        trace_id: str | None,
    ) -> LineageEmissionStatus:
        _, LocalOutcome, build_edge, build_envelope, build_node = _load_sdk()
        trace = trace_id or f"trace:eval-cal-node:{proposal_id}"

        proposal_node = build_node(
            node_type="eval_cal_proposal",
            payload_schema_id="eval_cal_proposal",
            payload_schema_version="v1",
            payload={
                "schema_version": "eval_cal_proposal.v1",
                "proposal_id": proposal_id,
                "record_id": record_node_id,
                "proposed_at": decided_at,
            },
            source_system=self.SOURCE_SYSTEM,
            source_component="eval-cal-node/proposal",
            trace_id=trace,
            writer_identity=self.WRITER_IDENTITY,
            stable_source_id=f"eval-cal-node:proposal:{proposal_id}",
        )

        decision_payload: dict[str, Any] = {
            "schema_version": "eval_cal_gate_decision.v1",
            "decision_id": f"decision:{proposal_id}:{gate}",
            "gate": gate,
            "outcome": outcome,
            "decided_at": decided_at,
        }
        if block_reason_class:
            decision_payload["block_reason_class"] = block_reason_class
        decision_node = build_node(
            node_type="eval_cal_gate_decision",
            payload_schema_id="eval_cal_gate_decision",
            payload_schema_version="v1",
            payload=decision_payload,
            source_system=self.SOURCE_SYSTEM,
            source_component=f"eval-cal-node/{gate}",
            trace_id=trace,
            writer_identity=self.WRITER_IDENTITY,
            stable_source_id=f"eval-cal-node:decision:{proposal_id}:{gate}",
        )

        informed_edge = build_edge(
            source_node_id=record_node_id,
            target_node_id=proposal_node["node_id"],
            edge_type="informed",
            causality_class="derived",
            effect_class="calibration",
            trace_id=trace,
            writer_identity=self.WRITER_IDENTITY,
            created_by_system=self.SOURCE_SYSTEM,
            stable_source_id=f"{record_node_id}->{proposal_node['node_id']}",
        )
        reviewed_by_edge = build_edge(
            source_node_id=proposal_node["node_id"],
            target_node_id=decision_node["node_id"],
            edge_type="reviewed_by",
            causality_class="operator_asserted" if gate == "gate_3" else "derived",
            effect_class="calibration",
            trace_id=trace,
            writer_identity=self.WRITER_IDENTITY,
            created_by_system=self.SOURCE_SYSTEM,
            stable_source_id=f"{proposal_node['node_id']}->{decision_node['node_id']}",
            decision_ref=(
                {
                    "schema_version": "DecisionRef.v1",
                    "decision_id": decision_payload["decision_id"],
                    "decided_by": "eval-cal-node",
                    "decided_at": decided_at,
                    "decision_kind": gate,
                }
                if gate == "gate_3"
                else None
            ),
        )

        envelope = build_envelope(
            writer_identity=self.WRITER_IDENTITY,
            trace_id=trace,
            nodes=[proposal_node, decision_node],
            edges=[informed_edge, reviewed_by_edge],
        )
        result = self._client.emit_envelope(envelope)

        if result.outcome in (LocalOutcome.accepted, LocalOutcome.accepted_duplicate):
            return LineageEmissionStatus(
                proposal_node_id=proposal_node["node_id"],
                gate_decision_node_id=decision_node["node_id"],
                informed_edge_id=informed_edge["edge_id"],
                reviewed_by_edge_id=reviewed_by_edge["edge_id"],
                outcome="lineage_available",
            )
        return LineageEmissionStatus(
            proposal_node_id=proposal_node["node_id"],
            gate_decision_node_id=decision_node["node_id"],
            outcome="lineage_degraded",
            error=(result.error.message if result.error else f"non-accept: {result.outcome}"),
        )


class NullLineageEmitter:
    def emit_record_consumed(self, **_kwargs: Any) -> LineageEmissionStatus:
        return LineageEmissionStatus(outcome="lineage_missing", error="emitter_disabled")

    def emit_proposal_and_gate_decision(self, **_kwargs: Any) -> LineageEmissionStatus:
        return LineageEmissionStatus(outcome="lineage_missing", error="emitter_disabled")
