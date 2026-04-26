from __future__ import annotations

from importlib import import_module
from typing import Any

EVAL_CAL_NODE_PRODUCER_REPO_ID = "eval-cal-node"
EVAL_CALIBRATION_REPORT_FAMILY = "eval_calibration_report"
EVAL_CALIBRATION_REPORT_VERSION = 1
EVAL_CALIBRATION_REPORT_SCHEMA_VERSION = "eval_cal_node.calibration_report.v1"

FORGE_EVAL_EVIDENCE_BUNDLE_FAMILY = "forge_eval_evidence_bundle"
FORGE_EVAL_EVIDENCE_BUNDLE_VERSION = 1


class EvaluationSpineContractError(RuntimeError):
    """Raised when Evaluation Spine contract admission fails closed."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def _load_contract_core() -> tuple[Any, Any]:
    try:
        families = import_module("forge_contract_core.validators.families")
        role_matrix = import_module("forge_contract_core.validators.role_matrix")
    except Exception as exc:  # pragma: no cover - only hit in misconfigured envs
        raise EvaluationSpineContractError(
            "forge-contract-core is required for Evaluation Spine contract validation",
            details={"error": str(exc)},
        ) from exc
    return families, role_matrix


def _check_producer_admitted(role_matrix: Any, repo_id: str, family: str) -> None:
    check = getattr(role_matrix, "check_producer_admitted", None)
    if check is None:
        return
    check(repo_id, family)


def _check_consumer_admitted(role_matrix: Any, repo_id: str, family: str) -> None:
    for name in (
        "check_consumer_admitted",
        "check_consumer_allowed",
        "check_consume_admitted",
    ):
        check = getattr(role_matrix, name, None)
        if check is not None:
            check(repo_id, family)
            return


def _validate_family_payload(families: Any, family: str, version: int, payload: dict[str, Any]) -> None:
    validate = getattr(families, "validate_family_payload", None)
    if validate is None:
        raise EvaluationSpineContractError(
            "forge-contract-core family validator is unavailable",
            details={"family": family, "version": version},
        )
    validate(family, version, payload)


def validate_forge_eval_evidence_bundle_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate eval-cal-node's admitted upstream forge-eval bundle.

    eval-cal-node consumes forge_eval_evidence_bundle artifacts but does not
    reinterpret forge-eval as math authority. This boundary check keeps Phase 04
    limited to calibration/report emission.
    """

    families, role_matrix = _load_contract_core()
    try:
        _check_consumer_admitted(role_matrix, EVAL_CAL_NODE_PRODUCER_REPO_ID, FORGE_EVAL_EVIDENCE_BUNDLE_FAMILY)
        _validate_family_payload(
            families,
            FORGE_EVAL_EVIDENCE_BUNDLE_FAMILY,
            FORGE_EVAL_EVIDENCE_BUNDLE_VERSION,
            payload,
        )
    except Exception as exc:
        raise EvaluationSpineContractError(
            "forge-eval evidence bundle payload failed eval-cal-node admission",
            details={
                "consumer_repo_id": EVAL_CAL_NODE_PRODUCER_REPO_ID,
                "artifact_family": FORGE_EVAL_EVIDENCE_BUNDLE_FAMILY,
                "artifact_version": FORGE_EVAL_EVIDENCE_BUNDLE_VERSION,
                "error": str(exc),
            },
        ) from exc

    return {
        "consumer_repo_id": EVAL_CAL_NODE_PRODUCER_REPO_ID,
        "artifact_family": FORGE_EVAL_EVIDENCE_BUNDLE_FAMILY,
        "artifact_version": FORGE_EVAL_EVIDENCE_BUNDLE_VERSION,
        "validation_state": "passed",
    }


def validate_eval_calibration_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate eval-cal-node's canonical Evaluation Spine output payload."""

    families, role_matrix = _load_contract_core()
    try:
        _check_producer_admitted(role_matrix, EVAL_CAL_NODE_PRODUCER_REPO_ID, EVAL_CALIBRATION_REPORT_FAMILY)
        _validate_family_payload(
            families,
            EVAL_CALIBRATION_REPORT_FAMILY,
            EVAL_CALIBRATION_REPORT_VERSION,
            payload,
        )
    except Exception as exc:
        raise EvaluationSpineContractError(
            "eval calibration report payload failed forge-contract-core validation",
            details={
                "producer_repo_id": EVAL_CAL_NODE_PRODUCER_REPO_ID,
                "artifact_family": EVAL_CALIBRATION_REPORT_FAMILY,
                "artifact_version": EVAL_CALIBRATION_REPORT_VERSION,
                "error": str(exc),
            },
        ) from exc

    return {
        "producer_repo_id": EVAL_CAL_NODE_PRODUCER_REPO_ID,
        "artifact_family": EVAL_CALIBRATION_REPORT_FAMILY,
        "artifact_version": EVAL_CALIBRATION_REPORT_VERSION,
        "validation_state": "passed",
    }
