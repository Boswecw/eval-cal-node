"""Opt-in calibration lineage emission: default-off + upstream discovery by run_id.

Self-contained — no DataForge-Local, no SDK needed for these paths.
"""
from __future__ import annotations

from eval_cal_node.lineage.spine_emit import (
    EVAL_CAL_LINEAGE_URL_ENV,
    _discover_bundle,
    emit_calibration_lineage,
)


class _FakeClient:
    def __init__(self, nodes: list[dict]) -> None:
        self._nodes = nodes

    def list_nodes(self, *, node_type: str, limit: int = 50) -> list[dict]:
        assert node_type == "forge_eval_evidence_bundle"
        return self._nodes


def test_discover_bundle_matches_by_forge_eval_run_id():
    nodes = [
        {"node_id": "node:b:1", "payload": {"forge_eval_run_id": "other"}},
        {"node_id": "node:b:2", "payload": {"forge_eval_run_id": "run-x", "evidence_bundle_id": "bun-x"}},
    ]
    match = _discover_bundle(_FakeClient(nodes), "run-x")
    assert match is not None and match["node_id"] == "node:b:2"
    assert _discover_bundle(_FakeClient(nodes), "missing") is None
    assert _discover_bundle(_FakeClient(nodes), "") is None  # empty run_id never matches


def test_emit_is_default_off_when_url_unset(monkeypatch):
    monkeypatch.delenv(EVAL_CAL_LINEAGE_URL_ENV, raising=False)
    outcome = emit_calibration_lineage(
        source_payload={"forge_eval_run_id": "run-x"},
        report_payload={"calibration_report_id": "eval-calibration:run-x:v1"},
    )
    assert outcome == "lineage_missing"  # no network, no-op
