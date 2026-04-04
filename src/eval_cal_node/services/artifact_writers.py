"""Deterministic artifact writers for all output artifacts."""

import json
from pathlib import Path
from typing import Any

from eval_cal_node.services.calibration_math import CalibrationCandidate
from eval_cal_node.services.gate2 import SURFACE_GROUPS
from eval_cal_node.services.pattern_extractor import PatternResult
from eval_cal_node.validation.schema_loader import validate_against_schema


def _write_artifact(data: dict, path: Path, schema_name: str) -> None:
    """Validate against schema and write deterministic JSON."""
    validate_against_schema(data, schema_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, sort_keys=True, separators=(",", ":"))


def _get_affected_surfaces(param_name: str) -> list[str]:
    """Return which Eval math surfaces a parameter affects."""
    surfaces = []
    for surface_name, params in sorted(SURFACE_GROUPS.items()):
        if param_name in params:
            surfaces.append(surface_name)
    return surfaces


def write_proposal(
    proposal_id: str,
    node_revision: str,
    record_count: int,
    candidates: dict[str, CalibrationCandidate],
    proposals_dir: Path,
) -> dict:
    """Write eval_calibration_proposal.json."""
    proposals = []
    for name in sorted(candidates.keys()):
        c = candidates[name]
        direction = "none"
        if c.bounded_delta > 0:
            direction = "increase"
        elif c.bounded_delta < 0:
            direction = "decrease"
        proposals.append({
            "param_name": name,
            "current_value": c.current_value,
            "proposed_value": c.proposed_value,
            "bounded_delta": c.bounded_delta,
            "status": c.status if c.status in ("candidate", "hold") else "rejected",
            "direction": direction,
        })

    data = {
        "proposal_id": proposal_id,
        "node_revision": node_revision,
        "record_count": record_count,
        "proposals": proposals,
    }
    _write_artifact(data, proposals_dir / f"{proposal_id}_proposal.json", "eval_calibration_proposal")
    return data


def write_evidence(
    proposal_id: str,
    node_revision: str,
    record_count: int,
    patterns: dict[str, PatternResult],
    candidates: dict[str, CalibrationCandidate],
    proposals_dir: Path,
) -> dict:
    """Write eval_calibration_evidence.json."""
    evidence = []
    for name in sorted(patterns.keys()):
        pr = patterns[name]
        c = candidates.get(name)
        evidence.append({
            "param_name": name,
            "n_false_block": pr.n_false_block,
            "n_missed_block": pr.n_missed_block,
            "n_false_caution": pr.n_false_caution,
            "n_missed_caution": pr.n_missed_caution,
            "n_total_implicated": pr.n_total_implicated,
            "n_total": pr.n_total,
            "recurrence_count": pr.recurrence_count,
            "false_block_rate": c.false_block_rate if c else 0.0,
            "missed_block_rate": c.missed_block_rate if c else 0.0,
            "net_direction": c.net_direction if c else 0.0,
        })

    data = {
        "proposal_id": proposal_id,
        "node_revision": node_revision,
        "record_count": record_count,
        "evidence": evidence,
    }
    _write_artifact(data, proposals_dir / f"{proposal_id}_evidence.json", "eval_calibration_evidence")
    return data


def write_param_delta(
    proposal_id: str,
    node_revision: str,
    candidates: dict[str, CalibrationCandidate],
    allowed_params: dict[str, dict],
    proposals_dir: Path,
) -> dict:
    """Write eval_param_delta.json."""
    deltas = []
    for name in sorted(candidates.keys()):
        c = candidates[name]
        pc = allowed_params.get(name, {})
        deltas.append({
            "param_name": name,
            "current_value": c.current_value,
            "proposed_value": c.proposed_value,
            "bounded_delta": c.bounded_delta,
            "raw_delta": c.raw_delta,
            "param_min": pc.get("param_min", 0.0),
            "param_max": pc.get("param_max", 1.0),
            "max_movement": pc.get("max_movement", 0.1),
        })

    data = {
        "proposal_id": proposal_id,
        "node_revision": node_revision,
        "deltas": deltas,
    }
    _write_artifact(data, proposals_dir / f"{proposal_id}_param_delta.json", "eval_param_delta")
    return data


def write_approval_request(
    proposal_id: str,
    node_revision: str,
    gate3_params: list[str],
    candidates: dict[str, CalibrationCandidate],
    patterns: dict[str, PatternResult],
    allowed_params: dict[str, dict],
    proposals_dir: Path,
) -> dict:
    """Write eval_approval_request.json for Gate 3 candidates."""
    requests = []
    for name in sorted(gate3_params):
        c = candidates[name]
        pr = patterns[name]
        pc = allowed_params[name]
        requests.append({
            "param_name": name,
            "current_value": c.current_value,
            "proposed_value": c.proposed_value,
            "bounded_delta": c.bounded_delta,
            "param_min": pc["param_min"],
            "param_max": pc["param_max"],
            "net_direction": c.net_direction,
            "false_block_rate": c.false_block_rate,
            "missed_block_rate": c.missed_block_rate,
            "n_total_implicated": pr.n_total_implicated,
            "recurrence_count": pr.recurrence_count,
            "affected_surfaces": _get_affected_surfaces(name),
            "recommendation": "accept",
        })

    data = {
        "proposal_id": proposal_id,
        "node_revision": node_revision,
        "requests": requests,
    }
    _write_artifact(data, proposals_dir / f"{proposal_id}_approval_request.json", "eval_approval_request")
    return data
