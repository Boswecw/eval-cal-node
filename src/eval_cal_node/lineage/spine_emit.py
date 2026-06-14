"""Opt-in, non-blocking lineage emission for the Evaluation Spine calibration flow.

Lives in the lineage layer (the transport boundary) so the calibrator service stays
transport-free. When ``EVAL_CAL_LINEAGE_URL`` is set, after a calibration report is produced
this emits the ``eval_cal_record`` node + the ``consumed`` edge from the upstream forge-eval
evidence-bundle node — the cross-producer link a downstream consumer (ForgeCommand's gate-walk)
traverses. Default-OFF and fail-soft: any failure is logged and calibration still completes.

Discovery: eval-cal consumes the bundle *contract* (which carries ``forge_eval_run_id``), not the
bundle's lineage node_id, so the bundle node is found by matching ``forge_eval_run_id`` over
``list_nodes("forge_eval_evidence_bundle")``. The emitted record's ``record_id`` is set to the
``calibration_report_id`` so ForgeMath can later discover *this* node by that id.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

EVAL_CAL_LINEAGE_URL_ENV = "EVAL_CAL_LINEAGE_URL"
EVAL_CAL_LINEAGE_TOKEN_ENV = "EVAL_CAL_LINEAGE_TOKEN"
FORGE_EVAL_BUNDLE_NODE_TYPE = "forge_eval_evidence_bundle"


def _discover_bundle(client: Any, run_id: str) -> dict[str, Any] | None:
    """Find the forge-eval evidence-bundle lineage node for ``run_id`` (newest first)."""
    if not run_id:
        return None
    for node in client.list_nodes(node_type=FORGE_EVAL_BUNDLE_NODE_TYPE, limit=50):
        payload = node.get("payload") or {}
        if str(payload.get("forge_eval_run_id") or "") == run_id:
            return node
    return None


def emit_calibration_lineage(
    *, source_payload: dict[str, Any], report_payload: dict[str, Any]
) -> str:
    """Emit eval_cal_record + consumed edge. Returns the lineage outcome string.

    Default-OFF (``EVAL_CAL_LINEAGE_URL`` unset → ``"lineage_missing"``, no network). Never raises.
    """
    base_url = os.environ.get(EVAL_CAL_LINEAGE_URL_ENV, "").strip()
    if not base_url:
        return "lineage_missing"
    try:
        from eval_cal_node.lineage.emitter import EvalCalLineageEmitter, _load_sdk

        LineageClient = _load_sdk()[0]
        token = os.environ.get(EVAL_CAL_LINEAGE_TOKEN_ENV, "").strip() or "local-eval-cal-node"
        client = LineageClient(
            base_url=base_url,
            writer_identity=EvalCalLineageEmitter.WRITER_IDENTITY,
            writer_token=token,
        )
        run_id = str(source_payload.get("forge_eval_run_id") or "")
        bundle = _discover_bundle(client, run_id)
        if bundle is None:
            logger.warning(
                "eval-cal lineage: no forge-eval bundle node for run_id=%r; skipping consumed edge",
                run_id,
            )
            return "lineage_missing"
        bundle_payload = bundle.get("payload") or {}
        status = EvalCalLineageEmitter(client).emit_record_consumed(
            record_id=str(report_payload.get("calibration_report_id") or ""),
            forge_eval_evidence_bundle_node_id=str(bundle.get("node_id") or ""),
            source_evidence_bundle_id=str(bundle_payload.get("evidence_bundle_id") or ""),
            source_payload_hash=str(bundle_payload.get("payload_hash") or "") or None,
        )
        return status.outcome
    except Exception as exc:  # noqa: BLE001
        logger.warning("eval-cal lineage emission skipped; calibration continues", exc_info=exc)
        return "lineage_missing"
