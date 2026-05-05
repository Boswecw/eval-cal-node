"""Phase 06 consumer-side + Gate 3 enforcement tests.

End-to-end Forge-Eval -> eval-cal-node integration:
- forge-eval emits run + evidence-bundle nodes + produced edge
- eval-cal-node emits record node + consumed edge
- Gate 3 lineage check passes
- Gate 3 lineage check fails closed when edge is missing / pending /
  unknown causality / source payload hash mismatched
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATAFORGE_LOCAL = _REPO_ROOT / "dataforge-Local"
_SDK_PATH = _REPO_ROOT / "contracts" / "forge_lineage" / "sdk"
_FORGE_EVAL = _REPO_ROOT / "local-systems" / "forge-eval" / "repo" / "src"
for p in (_SDK_PATH, _DATAFORGE_LOCAL, _FORGE_EVAL):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from forge_lineage_sdk import LineageClient  # noqa: E402
from eval_cal_node.lineage.emitter import EvalCalLineageEmitter  # noqa: E402
from eval_cal_node.lineage.gate3 import check_gate3_lineage  # noqa: E402
from forge_eval.lineage.emitter import ForgeEvalLineageEmitter  # noqa: E402


def _make_app() -> FastAPI:
    from app.lineage.router import router as lineage_router
    from app.lineage.service import LineageService

    fa = FastAPI()
    fa.include_router(lineage_router)
    fa.state.lineage_service = LineageService()
    return fa


@pytest.fixture
def app() -> FastAPI:
    return _make_app()


@pytest.fixture
def http(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def forge_eval_emitter(http: TestClient) -> ForgeEvalLineageEmitter:
    sdk = LineageClient(
        base_url="http://testserver",
        writer_identity="forge-eval",
        writer_token="local-forge-eval",
        http_client=http,
    )
    return ForgeEvalLineageEmitter(sdk)


@pytest.fixture
def eval_cal_emitter(app: FastAPI) -> EvalCalLineageEmitter:
    sdk = LineageClient(
        base_url="http://testserver",
        writer_identity="eval-cal-node",
        writer_token="local-eval-cal-node",
        http_client=TestClient(app),
    )
    return EvalCalLineageEmitter(sdk)


def _evidence_bundle(*, run_id: str = "fe-run-006") -> dict:
    return {
        "kind": "evidence_bundle",
        "bundle_id": f"bundle:{run_id}",
        "payload_hash": "b" * 64,
        "manifest": {"bundle_hash": "b" * 64, "artifacts": [{"kind": "merge_decision"}]},
    }


# ---------------------------------------------------------------- happy path


def test_forge_eval_to_eval_cal_node_happy_path(
    app: FastAPI, http: TestClient, forge_eval_emitter, eval_cal_emitter
):
    fe = forge_eval_emitter.emit_run_and_bundle(
        forge_eval_run_id="fe-run-006",
        repository_id="repo:demo",
        head_ref="abc",
        base_ref="def",
        evidence_bundle=_evidence_bundle(),
    )
    assert fe.outcome == "lineage_available"

    ec = eval_cal_emitter.emit_record_consumed(
        record_id="rec-006",
        forge_eval_evidence_bundle_node_id=fe.bundle_node_id,
        source_evidence_bundle_id="bundle:fe-run-006",
        source_payload_hash="b" * 64,
    )
    assert ec.outcome == "lineage_available"
    assert ec.consumed_edge_id is not None

    decision = check_gate3_lineage(
        forge_eval_evidence_bundle_node_id=fe.bundle_node_id,
        eval_cal_record_node_id=ec.record_node_id,
        http_client=http,
    )
    assert decision.allowed is True
    assert decision.availability == "lineage_available"


# ---------------------------------------------------------------- gate 3 negatives


def test_gate3_blocks_when_edge_missing(app: FastAPI, http: TestClient, forge_eval_emitter):
    fe = forge_eval_emitter.emit_run_and_bundle(
        forge_eval_run_id="missing-edge-run",
        repository_id="repo:demo",
        head_ref="abc",
        base_ref="def",
        evidence_bundle=_evidence_bundle(run_id="missing-edge-run"),
    )

    # eval-cal-node ingests the record but fails to emit the consumed edge.
    # We simulate that by writing the record node directly via the API.
    sdk = LineageClient(
        base_url="http://testserver",
        writer_identity="eval-cal-node",
        writer_token="local-eval-cal-node",
        http_client=http,
    )
    from forge_lineage_sdk.builders import build_node

    record_node = build_node(
        node_type="eval_cal_record",
        payload_schema_id="eval_cal_record",
        payload_schema_version="v1",
        payload={
            "schema_version": "eval_cal_record.v1",
            "record_id": "rec-missing-edge",
            "ingested_at": "2026-05-04T15:00:00Z",
        },
        source_system="eval-cal-node",
        source_component="eval-cal-node/ingest",
        trace_id="trace:eval-cal-node:rec-missing-edge",
        writer_identity="eval-cal-node",
        stable_source_id="eval-cal-node:record:rec-missing-edge",
    )
    sdk.emit_node(record_node)

    decision = check_gate3_lineage(
        forge_eval_evidence_bundle_node_id=fe.bundle_node_id,
        eval_cal_record_node_id=record_node["node_id"],
        http_client=http,
    )
    assert decision.allowed is False
    assert decision.availability == "lineage_missing"


def test_gate3_blocks_when_source_node_missing(http: TestClient):
    decision = check_gate3_lineage(
        forge_eval_evidence_bundle_node_id="node:does-not-exist",
        eval_cal_record_node_id="node:also-not-here",
        http_client=http,
    )
    assert decision.allowed is False
    assert decision.availability == "lineage_missing"
    assert decision.reason_class == "source_node_missing"


def test_gate3_blocks_when_causality_unknown(
    app: FastAPI, http: TestClient, forge_eval_emitter, eval_cal_emitter
):
    """Manually construct a consumed edge with causality_class=unknown."""
    fe = forge_eval_emitter.emit_run_and_bundle(
        forge_eval_run_id="unknown-causality-run",
        repository_id="repo:demo",
        head_ref="abc",
        base_ref="def",
        evidence_bundle=_evidence_bundle(run_id="unknown-causality-run"),
    )

    # Emit record node legitimately, then forge a manual edge with unknown causality.
    ec = eval_cal_emitter.emit_record_consumed(
        record_id="rec-unknown",
        forge_eval_evidence_bundle_node_id=fe.bundle_node_id,
        source_evidence_bundle_id="bundle:unknown-causality-run",
    )
    # The legitimate consumed edge already exists with deterministic causality.
    # Force a parallel "unknown" edge by directly inserting via the service —
    # which is the mode an attacker would use; enforcement must still see the
    # bad one if it exists. Since enforce_edge_for_promotion picks the first
    # matching edge from the downstream chain, we instead test the negative
    # path by directly using the SDK enforcement helper with a bad edge dict.
    from forge_lineage_sdk import EdgeRequirement, enforce_edge_for_promotion

    bad_edge = {
        "schema_version": "ImpactEdge.v1",
        "source_node_id": fe.bundle_node_id,
        "target_node_id": ec.record_node_id,
        "edge_type": "consumed",
        "causality_class": "unknown",
        "validation_status": "accepted",
    }
    src = app.state.lineage_service.get_node(fe.bundle_node_id)
    tgt = app.state.lineage_service.get_node(ec.record_node_id)
    decision = enforce_edge_for_promotion(
        requirement=EdgeRequirement(
            source_node_id=fe.bundle_node_id,
            target_node_id=ec.record_node_id,
            edge_type="consumed",
        ),
        source_node=src,
        target_node=tgt,
        edge=bad_edge,
    )
    assert decision.allowed is False
    assert decision.reason_class == "edge_invalid"


def test_gate3_blocks_on_payload_hash_mismatch(
    app: FastAPI, http: TestClient, forge_eval_emitter, eval_cal_emitter
):
    fe = forge_eval_emitter.emit_run_and_bundle(
        forge_eval_run_id="hash-mismatch-run",
        repository_id="repo:demo",
        head_ref="abc",
        base_ref="def",
        evidence_bundle=_evidence_bundle(run_id="hash-mismatch-run"),
    )
    ec = eval_cal_emitter.emit_record_consumed(
        record_id="rec-hash",
        forge_eval_evidence_bundle_node_id=fe.bundle_node_id,
        source_evidence_bundle_id="bundle:hash-mismatch-run",
        source_payload_hash="b" * 64,
    )

    # Gate 3 expects a hash that does not match the source.
    decision = check_gate3_lineage(
        forge_eval_evidence_bundle_node_id=fe.bundle_node_id,
        eval_cal_record_node_id=ec.record_node_id,
        expected_source_payload_hash="ff" * 32,
        http_client=http,
    )
    assert decision.allowed is False
    assert decision.availability == "lineage_stale"


def test_gate3_blocks_when_lineage_unreachable():
    """Transport failure must not silently allow Gate 3."""
    import httpx

    bad_client = httpx.Client(base_url="http://127.0.0.1:1", timeout=0.5)
    try:
        decision = check_gate3_lineage(
            forge_eval_evidence_bundle_node_id="any",
            eval_cal_record_node_id="any",
            http_client=bad_client,
        )
        assert decision.allowed is False
        assert decision.availability == "lineage_missing"
    finally:
        bad_client.close()


# ---------------------------------------------------------------- emitter non-blocking


def test_eval_cal_emitter_is_non_blocking_when_unreachable():
    sdk = LineageClient(
        base_url="http://127.0.0.1:1",
        writer_identity="eval-cal-node",
        writer_token="local-eval-cal-node",
    )
    em = EvalCalLineageEmitter(sdk)
    status = em.emit_record_consumed(
        record_id="r",
        forge_eval_evidence_bundle_node_id="bnode",
        source_evidence_bundle_id="bid",
    )
    assert status.outcome in ("lineage_missing", "lineage_degraded")
