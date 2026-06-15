from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

# Phase 04 exercises the Evaluation Spine contract-admission layer, which is
# backed by the internal forge-contract-core package. When eval-cal-node is
# checked out standalone that package is unavailable and the contract layer
# fails closed by design, so skip these tests cleanly rather than fail.
pytest.importorskip("forge_contract_core.validators.families")
pytest.importorskip("forge_contract_core.validators.role_matrix")

from eval_cal_node.contracts.evaluation_spine import (
    EvaluationSpineContractError,
    validate_eval_calibration_report_payload,
    validate_forge_eval_evidence_bundle_payload,
)
from eval_cal_node.services.evaluation_spine_calibrator import (
    CalibrationInputError,
    _score_validation_refs,
    build_eval_calibration_report_payload,
    calibrate_forge_eval_bundle_file,
    payload_sha256,
)

HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64
HASH_D = "sha256:" + "d" * 64


def forge_eval_bundle_payload() -> dict:
    return {
        "schema_version": "forge_eval.evidence_bundle.v1",
        "forge_eval_run_id": "550e8400-e29b-41d4-a716-446655440000",
        "source_projection_id": "centipede-projection:550e8400-e29b-41d4-a716-446655440000",
        "source_fused_bundle_id": "centipede-fused-bundle:550e8400-e29b-41d4-a716-446655440000",
        "repository_id": "forge-eval",
        "base_ref": "HEAD~1",
        "head_ref": "HEAD",
        "artifact_refs": [
            {
                "artifact_kind": "config_resolved",
                "artifact_path": "config_resolved.json",
                "artifact_hash": HASH_A,
            },
            {
                "artifact_kind": "risk_heatmap",
                "artifact_path": "risk_heatmap.json",
                "artifact_hash": HASH_B,
            },
            {
                "artifact_kind": "context_slices",
                "artifact_path": "context_slices.json",
                "artifact_hash": HASH_C,
            },
            {
                "artifact_kind": "forge_eval_evidence_bundle",
                "artifact_path": "forge_eval_evidence_bundle.contract.json",
                "artifact_hash": HASH_D,
            },
        ],
        "deterministic": True,
        "validation_state": "passed",
        # Real forge-eval centipede vocabulary (see centipede_runner.py); the
        # calibrator maps these onto the schema/contract-core coverage dimensions.
        "validation_refs": [
            "forge_eval.local_artifact_validation:passed",
            "forge_contract_core.role_matrix:passed",
            "forge_contract_core.family_payload:passed",
        ],
    }


def test_phase04_validates_upstream_forge_eval_bundle_contract() -> None:
    payload = forge_eval_bundle_payload()

    result = validate_forge_eval_evidence_bundle_payload(payload)

    assert result["consumer_repo_id"] == "eval-cal-node"
    assert result["artifact_family"] == "forge_eval_evidence_bundle"
    assert result["validation_state"] == "passed"


def test_phase04_builds_contract_core_eval_calibration_report_payload() -> None:
    payload = build_eval_calibration_report_payload(forge_eval_bundle_payload())

    assert payload["schema_version"] == "eval_cal_node.calibration_report.v1"
    assert payload["calibration_report_id"] == "eval-calibration:550e8400-e29b-41d4-a716-446655440000:v1"
    assert payload["source_forge_eval_evidence_bundle_ref"] == "forge_eval_evidence_bundle:550e8400-e29b-41d4-a716-446655440000:v1"
    assert payload["source_artifact_hash"] == HASH_D
    assert payload["repository_id"] == "forge-eval"
    assert payload["confidence_band_candidate"] == "high_confidence"
    assert payload["validation_state"] == "passed"
    assert validate_eval_calibration_report_payload(payload)["validation_state"] == "passed"


def test_phase04_calibration_is_deterministic_for_same_input() -> None:
    source = forge_eval_bundle_payload()

    first = build_eval_calibration_report_payload(source)
    second = build_eval_calibration_report_payload(copy.deepcopy(source))

    assert first == second
    assert payload_sha256(first) == payload_sha256(second)


def test_phase04_generates_stable_source_ref_for_non_uuid_run_id() -> None:
    source = forge_eval_bundle_payload()
    source["forge_eval_run_id"] = "phase-03-contract-core-bridge-proof"

    payload = build_eval_calibration_report_payload(source)

    assert re.match(
        r"^forge_eval_evidence_bundle:[0-9a-f-]{36}:v1$",
        payload["source_forge_eval_evidence_bundle_ref"],
    )
    assert payload["calibration_report_id"].startswith("eval-calibration:")
    assert validate_eval_calibration_report_payload(payload)["validation_state"] == "passed"


def test_phase04_file_runner_writes_valid_report(tmp_path: Path) -> None:
    input_path = tmp_path / "forge_eval_evidence_bundle.contract.json"
    input_path.write_text(json.dumps(forge_eval_bundle_payload()), encoding="utf-8")

    result = calibrate_forge_eval_bundle_file(input_path, tmp_path / "out")
    output_path = Path(result["output_path"])

    assert output_path.name == "eval_calibration_report.contract.json"
    assert output_path.exists()
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted == result["payload"]
    assert validate_eval_calibration_report_payload(persisted)["validation_state"] == "passed"


def test_phase04_fails_closed_when_source_contract_is_invalid() -> None:
    source = forge_eval_bundle_payload()
    source["deterministic"] = False

    with pytest.raises(EvaluationSpineContractError):
        build_eval_calibration_report_payload(source)


def test_phase04_fails_closed_without_source_bundle_hash() -> None:
    source = forge_eval_bundle_payload()
    source["artifact_refs"] = [
        ref for ref in source["artifact_refs"] if ref["artifact_kind"] != "forge_eval_evidence_bundle"
    ]

    with pytest.raises(CalibrationInputError):
        build_eval_calibration_report_payload(source)


# --- Regression guard: validation_refs vocabulary must match forge-eval's real
# output. The scorer previously required the literals
# {"schema_validation", "contract_core_validation"}, which forge-eval never
# emits, so validation_reference_coverage was pinned at 0.0 and the downstream
# ForgeMath gate (score >= 0.85) could never be reached for any changeset.


def test_validation_refs_score_matches_real_forge_eval_vocabulary() -> None:
    # Exactly what forge-eval/repo/src/forge_eval/centipede_runner.py emits.
    refs = [
        "forge_eval.local_artifact_validation:passed",
        "forge_contract_core.role_matrix:passed",
        "forge_contract_core.family_payload:passed",
    ]
    assert _score_validation_refs({"validation_refs": refs}) == 1.0


def test_validation_refs_score_is_partial_when_one_dimension_missing() -> None:
    refs = ["forge_contract_core.family_payload:passed"]  # schema dim only
    assert _score_validation_refs({"validation_refs": refs}) == 0.5


def test_validation_refs_score_ignores_old_phantom_literals() -> None:
    # The pre-fix assumed vocabulary must NOT be treated as coverage.
    refs = ["schema_validation", "contract_core_validation"]
    assert _score_validation_refs({"validation_refs": refs}) == 0.0


def test_validation_refs_score_excludes_unpassed_checks() -> None:
    # A check that ran but did not pass must not count toward coverage.
    refs = [
        "forge_contract_core.family_payload:failed",
        "forge_contract_core.role_matrix:passed",
    ]
    assert _score_validation_refs({"validation_refs": refs}) == 0.5
