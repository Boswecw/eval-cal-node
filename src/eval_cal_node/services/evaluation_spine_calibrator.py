from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from eval_cal_node.contracts.evaluation_spine import (
    EVAL_CALIBRATION_REPORT_SCHEMA_VERSION,
    EvaluationSpineContractError,
    validate_eval_calibration_report_payload,
    validate_forge_eval_evidence_bundle_payload,
)

SCORE_NORMALIZATION_VERSION = "eval-cal-node.phase04.weighted-evidence.v1"
OUTPUT_FILENAME = "eval_calibration_report.contract.json"


class CalibrationInputError(ValueError):
    """Raised when a forge-eval handoff is malformed for calibration."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def _stable_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CalibrationInputError(
            "failed to read forge-eval evidence bundle JSON",
            details={"path": str(path), "error": str(exc)},
        ) from exc
    if not isinstance(loaded, dict):
        raise CalibrationInputError(
            "forge-eval evidence bundle JSON must be an object",
            details={"path": str(path), "actual_type": type(loaded).__name__},
        )
    return loaded


def _canonical_source_uuid(run_id: str) -> str:
    try:
        return str(UUID(run_id))
    except ValueError:
        return str(uuid5(NAMESPACE_URL, f"forge-eval:evidence-bundle:{run_id}"))


def _source_bundle_ref(source_payload: dict[str, Any]) -> str:
    run_id = source_payload.get("forge_eval_run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise CalibrationInputError("forge-eval evidence bundle is missing forge_eval_run_id")
    return f"forge_eval_evidence_bundle:{_canonical_source_uuid(run_id.strip())}:v1"


def _source_artifact_hash(source_payload: dict[str, Any]) -> str:
    artifact_refs = source_payload.get("artifact_refs")
    if not isinstance(artifact_refs, list):
        raise CalibrationInputError("forge-eval evidence bundle artifact_refs must be a list")

    for ref in artifact_refs:
        if isinstance(ref, dict) and ref.get("artifact_kind") == "forge_eval_evidence_bundle":
            value = ref.get("artifact_hash")
            if isinstance(value, str) and value.startswith("sha256:"):
                return value
            break

    raise CalibrationInputError(
        "forge-eval evidence bundle artifact_refs must include its own sha256 hash",
        details={"required_artifact_kind": "forge_eval_evidence_bundle"},
    )


def _repository_id(source_payload: dict[str, Any]) -> str:
    value = source_payload.get("repository_id")
    if not isinstance(value, str) or not value.strip():
        raise CalibrationInputError("forge-eval evidence bundle is missing repository_id")
    return value.strip()


def _score_artifact_coverage(source_payload: dict[str, Any]) -> float:
    artifact_refs = source_payload.get("artifact_refs")
    if not isinstance(artifact_refs, list):
        return 0.0
    required_kinds = {
        "config_resolved",
        "risk_heatmap",
        "context_slices",
        "forge_eval_evidence_bundle",
    }
    observed = {
        ref.get("artifact_kind")
        for ref in artifact_refs
        if isinstance(ref, dict) and isinstance(ref.get("artifact_kind"), str)
    }
    return round(len(required_kinds.intersection(observed)) / len(required_kinds), 6)


# forge-eval records each validation it ran on a bundle as a namespaced
# "<check>:<state>" ref (e.g. "forge_contract_core.family_payload:passed").
# This metric measures coverage over two validation dimensions; each maps onto
# the real check forge-eval emits for it. A dimension only counts as covered
# when its check is present AND passed. Source of these strings:
# forge-eval/repo/src/forge_eval/centipede_runner.py.
_VALIDATION_REF_DIMENSIONS = {
    "schema_validation": "forge_contract_core.family_payload",
    "contract_core_validation": "forge_contract_core.role_matrix",
}


def _score_validation_refs(source_payload: dict[str, Any]) -> float:
    refs = source_payload.get("validation_refs")
    if not isinstance(refs, list):
        return 0.0
    passed_checks = {
        ref.split(":", 1)[0].strip()
        for ref in refs
        if isinstance(ref, str) and ref.strip().endswith(":passed")
    }
    covered = sum(
        1 for check in _VALIDATION_REF_DIMENSIONS.values() if check in passed_checks
    )
    return round(covered / len(_VALIDATION_REF_DIMENSIONS), 6)


def _score_validation_state(source_payload: dict[str, Any]) -> float:
    return 1.0 if source_payload.get("validation_state") == "passed" else 0.0


def _weighted_confidence_score(source_payload: dict[str, Any]) -> float:
    scores = {
        "source_validation_state": _score_validation_state(source_payload),
        "artifact_coverage": _score_artifact_coverage(source_payload),
        "validation_reference_coverage": _score_validation_refs(source_payload),
    }
    weights = {
        "source_validation_state": 0.5,
        "artifact_coverage": 0.3,
        "validation_reference_coverage": 0.2,
    }
    return round(sum(scores[name] * weights[name] for name in scores), 6)


def _confidence_band(score: float) -> str:
    if score >= 0.85:
        return "high_confidence"
    if score >= 0.6:
        return "medium_confidence"
    if score > 0:
        return "low_confidence"
    return "unknown"


def _direction(score: float, threshold: float) -> str:
    if score == threshold:
        return "equal"
    if score > threshold:
        return "above"
    return "below"


def build_eval_calibration_report_payload(source_payload: dict[str, Any]) -> dict[str, Any]:
    """Build the contract-core eval_calibration_report payload.

    Phase 04 deliberately performs bounded calibration only: it validates the
    upstream forge-eval contract payload, derives deterministic score candidates,
    and emits a report for downstream ForgeMath authority. It does not make final
    math-authority decisions.
    """

    validate_forge_eval_evidence_bundle_payload(source_payload)

    if source_payload.get("validation_state") != "passed":
        raise CalibrationInputError(
            "eval-cal-node only calibrates passed forge-eval evidence bundles",
            details={"validation_state": source_payload.get("validation_state")},
        )

    if source_payload.get("deterministic") is not True:
        raise CalibrationInputError("forge-eval evidence bundle must be deterministic")

    source_ref = _source_bundle_ref(source_payload)
    source_uuid = source_ref.split(":", 2)[1]
    source_hash = _source_artifact_hash(source_payload)
    confidence_score = _weighted_confidence_score(source_payload)

    calibrated_scores = [
        {
            "metric_name": "source_validation_state",
            "raw_score": _score_validation_state(source_payload),
            "calibrated_score": _score_validation_state(source_payload),
            "weight": 0.5,
        },
        {
            "metric_name": "artifact_coverage",
            "raw_score": _score_artifact_coverage(source_payload),
            "calibrated_score": _score_artifact_coverage(source_payload),
            "weight": 0.3,
        },
        {
            "metric_name": "validation_reference_coverage",
            "raw_score": _score_validation_refs(source_payload),
            "calibrated_score": _score_validation_refs(source_payload),
            "weight": 0.2,
        },
        {
            "metric_name": "weighted_confidence_candidate",
            "raw_score": confidence_score,
            "calibrated_score": confidence_score,
            "weight": 1.0,
        },
    ]

    payload = {
        "schema_version": EVAL_CALIBRATION_REPORT_SCHEMA_VERSION,
        "calibration_report_id": f"eval-calibration:{source_uuid}:v1",
        "source_forge_eval_evidence_bundle_ref": source_ref,
        "source_artifact_hash": source_hash,
        "repository_id": _repository_id(source_payload),
        "score_normalization_version": SCORE_NORMALIZATION_VERSION,
        "calibrated_scores": calibrated_scores,
        "confidence_band_candidate": _confidence_band(confidence_score),
        "threshold_crossings": [
            {
                "threshold_id": "minimum_high_confidence_candidate",
                "crossed": confidence_score >= 0.85,
                "direction": _direction(confidence_score, 0.85),
            },
            {
                "threshold_id": "minimum_medium_confidence_candidate",
                "crossed": confidence_score >= 0.6,
                "direction": _direction(confidence_score, 0.6),
            },
            {
                "threshold_id": "complete_artifact_coverage",
                "crossed": _score_artifact_coverage(source_payload) >= 1.0,
                "direction": _direction(_score_artifact_coverage(source_payload), 1.0),
            },
            {
                "threshold_id": "contract_validation_refs_present",
                "crossed": _score_validation_refs(source_payload) >= 1.0,
                "direction": _direction(_score_validation_refs(source_payload), 1.0),
            },
        ],
        "validation_state": "passed",
        "normalization_notes": [
            "Phase 04 calibration uses deterministic bounded score candidates only.",
            "ForgeMath remains the downstream math authority; eval-cal-node does not issue final lane decisions.",
        ],
    }

    validate_eval_calibration_report_payload(payload)
    return payload


def write_eval_calibration_report_payload(payload: dict[str, Any], output_dir: Path) -> Path:
    validate_eval_calibration_report_payload(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_FILENAME
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def payload_sha256(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def calibrate_forge_eval_bundle_file(input_path: Path, output_dir: Path) -> dict[str, Any]:
    source_payload = _read_json_object(input_path)
    report_payload = build_eval_calibration_report_payload(source_payload)
    report_path = write_eval_calibration_report_payload(report_payload, output_dir)
    # Opt-in, non-blocking lineage emission (default off; the calibration above is transport-free).
    from eval_cal_node.lineage.spine_emit import emit_calibration_lineage

    lineage_outcome = emit_calibration_lineage(
        source_payload=source_payload, report_payload=report_payload
    )
    return {
        "artifact_family": "eval_calibration_report",
        "artifact_version": 1,
        "output_path": str(report_path),
        "output_hash": payload_sha256(report_payload),
        "validation_state": "passed",
        "payload": report_payload,
        "lineage": lineage_outcome,
    }


def calibrate_forge_eval_bundle_file_or_raise(input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    try:
        return calibrate_forge_eval_bundle_file(Path(input_path), Path(output_dir))
    except (CalibrationInputError, EvaluationSpineContractError):
        raise
    except Exception as exc:
        raise CalibrationInputError(
            "unexpected calibration failure",
            details={"input_path": str(input_path), "output_dir": str(output_dir), "error": str(exc)},
        ) from exc
