"""Gate 3 lineage enforcement (Phase 06).

Gate 3 is the math-effect boundary in eval-cal-node — the human approval
point. Per ``08_PHASE_06_FORGE_EVAL_TO_EVAL_CAL_NODE.md``, Gate 3 must fail
closed if:

- no valid ``consumed`` edge exists from the forge-eval evidence bundle node
  to the eval-cal-node record node
- the edge is pending
- the edge is invalid
- the edge causality class is ``unknown``
- the source node hash does not match the record used for calibration
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


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


def _load_enforcement():
    """Import the ForgeLineage enforcement helpers lazily so this module is
    importable without the (monorepo-only) SDK present."""
    _ensure_sdk_on_path()
    from forge_lineage_sdk.enforcement import EdgeRequirement, enforce_edge_for_promotion
    return EdgeRequirement, enforce_edge_for_promotion


@dataclass
class LineageGate3Decision:
    allowed: bool
    availability: str
    reason_class: str | None
    reason_message: str | None
    edge: dict[str, Any] | None = None


def check_gate3_lineage(
    *,
    forge_eval_evidence_bundle_node_id: str,
    eval_cal_record_node_id: str,
    expected_source_payload_hash: str | None = None,
    base_url: str = "http://127.0.0.1:8005",
    http_client: "httpx.Client | None" = None,
) -> LineageGate3Decision:
    """Look up the source/target nodes and the ``consumed`` edge, then apply
    the SDK enforcement rule. Returns ``allowed=False`` if anything is wrong.

    On transport failure (DataForge unreachable), returns
    ``allowed=False, availability="lineage_missing"`` — Gate 3 must NOT
    approve when lineage cannot be verified.
    """
    try:
        import httpx

        EdgeRequirement, enforce_edge_for_promotion = _load_enforcement()
    except ImportError as exc:
        # Fail closed: if the enforcement SDK / transport is unavailable we
        # cannot verify lineage, so Gate 3 must not approve.
        return LineageGate3Decision(
            allowed=False,
            availability="lineage_missing",
            reason_class="enforcement_unavailable",
            reason_message=f"lineage dependencies not importable: {exc!r}",
        )

    client = http_client
    owns_client = False
    if client is None:
        client = httpx.Client(base_url=base_url, timeout=5.0)
        owns_client = True
    try:
        try:
            source_resp = client.get(f"/api/v1/lineage/nodes/{forge_eval_evidence_bundle_node_id}")
            target_resp = client.get(f"/api/v1/lineage/nodes/{eval_cal_record_node_id}")
        except httpx.HTTPError as exc:
            return LineageGate3Decision(
                allowed=False,
                availability="lineage_missing",
                reason_class="storage_error",
                reason_message=f"lineage transport failure: {exc!r}",
            )

        source = source_resp.json() if source_resp.status_code == 200 else None
        target = target_resp.json() if target_resp.status_code == 200 else None

        # Walk downstream from the source bundle to find the consumed edge.
        edge_record: dict[str, Any] | None = None
        if source is not None:
            try:
                down_resp = client.get(
                    f"/api/v1/lineage/nodes/{forge_eval_evidence_bundle_node_id}/downstream",
                    params={"max_depth": 1},
                )
                if down_resp.status_code == 200:
                    body = down_resp.json()
                    for e in body.get("edges", []):
                        if (
                            e.get("source_node_id") == forge_eval_evidence_bundle_node_id
                            and e.get("target_node_id") == eval_cal_record_node_id
                            and e.get("edge_type") == "consumed"
                        ):
                            edge_record = e
                            break
            except httpx.HTTPError as exc:
                return LineageGate3Decision(
                    allowed=False,
                    availability="lineage_missing",
                    reason_class="storage_error",
                    reason_message=f"lineage transport failure: {exc!r}",
                )

        result = enforce_edge_for_promotion(
            requirement=EdgeRequirement(
                source_node_id=forge_eval_evidence_bundle_node_id,
                target_node_id=eval_cal_record_node_id,
                edge_type="consumed",
                expected_source_payload_hash=expected_source_payload_hash,
                forbid_unknown_causality=True,
            ),
            source_node=source,
            target_node=target,
            edge=edge_record,
        )
        return LineageGate3Decision(
            allowed=result.allowed,
            availability=result.availability,
            reason_class=result.reason_class,
            reason_message=result.reason_message,
            edge=result.edge,
        )
    finally:
        if owns_client:
            client.close()
