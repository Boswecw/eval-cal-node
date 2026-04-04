"""Gate runner — orchestrates Gate 1 and Gate 2 evaluation and writes gate decision artifacts."""

import hashlib
import json
from pathlib import Path
from typing import Any

from eval_cal_node.services.calibration_math import CalibrationCandidate
from eval_cal_node.services.gate1 import evaluate_gate1
from eval_cal_node.services.gate2 import evaluate_gate2, check_destabilizing_combination
from eval_cal_node.services.pattern_extractor import PatternResult


def _compute_proposal_id(node_revision: str, record_count: int, param_names: list[str]) -> str:
    raw = node_revision + str(record_count) + "|".join(sorted(param_names))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_gates(
    candidates: dict[str, CalibrationCandidate],
    patterns: dict[str, PatternResult],
    allowed_params: dict[str, dict],
    config: dict,
    proposals_dir: Path,
) -> dict[str, Any]:
    """Run Gate 1 and Gate 2 on all candidates. Write gate decision artifact.

    Returns the gate decision dict.
    """
    record_count = next(iter(patterns.values())).n_total if patterns else 0
    node_revision = config["node_revision"]
    param_names = sorted(candidates.keys())
    proposal_id = _compute_proposal_id(node_revision, record_count, param_names)

    parameters_evaluated = []

    for param_name in param_names:
        candidate = candidates[param_name]
        pattern = patterns[param_name]
        param_config = allowed_params[param_name]

        entry: dict[str, Any] = {
            "param_name": param_name,
            "candidate_status": candidate.status,
        }

        # Gate 1
        g1_outcome, g1_reason = evaluate_gate1(candidate, pattern, config)
        entry["gate1_outcome"] = g1_outcome
        entry["gate1_reason"] = g1_reason

        # Gate 2 only if Gate 1 advances
        if g1_outcome == "advance":
            g2_outcome, g2_reason = evaluate_gate2(candidate, param_config)
            entry["gate2_outcome"] = g2_outcome
            entry["gate2_reason"] = g2_reason
        else:
            entry["gate2_outcome"] = "not_reached"
            entry["gate2_reason"] = "gate1 did not advance"

        # Final routing
        if g1_outcome == "reject":
            entry["final_routing"] = "rejected"
        elif g1_outcome == "hold":
            entry["final_routing"] = "held"
        elif entry["gate2_outcome"] == "reject":
            entry["final_routing"] = "rejected"
        elif entry["gate2_outcome"] == "hold":
            entry["final_routing"] = "held"
        else:
            entry["final_routing"] = "gate3_ready"

        parameters_evaluated.append(entry)

    # Check destabilizing combinations among gate3_ready candidates
    gate3_candidates = {
        e["param_name"]: candidates[e["param_name"]]
        for e in parameters_evaluated
        if e["final_routing"] == "gate3_ready"
    }
    destab_warnings = check_destabilizing_combination(gate3_candidates)
    if destab_warnings:
        for entry in parameters_evaluated:
            if entry["final_routing"] == "gate3_ready":
                entry["final_routing"] = "held"
                entry["gate2_reason"] += f" | destabilizing: {'; '.join(destab_warnings)}"

    gate_decision = {
        "proposal_id": proposal_id,
        "node_revision": node_revision,
        "evaluated_at_record_count": record_count,
        "parameters_evaluated": parameters_evaluated,
    }

    # Write artifact
    proposals_dir.mkdir(parents=True, exist_ok=True)
    dest = proposals_dir / f"{proposal_id}_gate_decision.json"
    with open(dest, "w") as f:
        json.dump(gate_decision, f, sort_keys=True, separators=(",", ":"))

    return gate_decision
