"""Gate 2 — Control envelope gate (fully autonomous)."""

from eval_cal_node.services.calibration_math import CalibrationCandidate

ALLOWED_PARAMETERS = {
    "hazard_hidden_uplift_strength",
    "hazard_structural_risk_strength",
    "hazard_occupancy_strength",
    "hazard_support_uplift_strength",
    "hazard_uncertainty_boost",
    "hazard_blocking_threshold",
    "merge_decision_caution_threshold",
    "merge_decision_block_threshold",
    "occupancy_prior_base",
    "occupancy_support_uplift",
    "occupancy_detection_assumption",
    "occupancy_miss_penalty_strength",
    "occupancy_null_uncertainty_boost",
}

FORBIDDEN_TARGETS = {
    "stage_sequence",
    "required_artifact_list",
    "schema_shapes",
    "mandatory_fail_closed_conditions",
    "authority_boundaries",
    "human_approval_requirements",
    "canonical_evidence_rules",
}

# Parameters that affect the same Eval math surface — opposing movements are destabilizing
SURFACE_GROUPS = {
    "hazard": {
        "hazard_hidden_uplift_strength",
        "hazard_structural_risk_strength",
        "hazard_occupancy_strength",
        "hazard_support_uplift_strength",
        "hazard_uncertainty_boost",
        "hazard_blocking_threshold",
    },
    "merge": {
        "merge_decision_caution_threshold",
        "merge_decision_block_threshold",
    },
    "occupancy": {
        "occupancy_prior_base",
        "occupancy_support_uplift",
        "occupancy_detection_assumption",
        "occupancy_miss_penalty_strength",
        "occupancy_null_uncertainty_boost",
    },
}


def evaluate_gate2(
    candidate: CalibrationCandidate,
    param_config: dict,
) -> tuple[str, str]:
    """Evaluate Gate 2 control envelope for a single candidate.

    Returns (outcome, reason) where outcome is 'reject' | 'hold' | 'advance'.
    """
    param_name = candidate.param_name

    # Check allowed list
    if param_name not in ALLOWED_PARAMETERS:
        return "reject", f"parameter '{param_name}' not in allowed calibration targets"

    # Check forbidden target
    if param_name in FORBIDDEN_TARGETS:
        return "reject", f"parameter '{param_name}' is a forbidden target"

    # Check proposed value within bounds
    if candidate.proposed_value < param_config["param_min"]:
        return "reject", (
            f"proposed_value ({candidate.proposed_value}) < param_min ({param_config['param_min']})"
        )
    if candidate.proposed_value > param_config["param_max"]:
        return "reject", (
            f"proposed_value ({candidate.proposed_value}) > param_max ({param_config['param_max']})"
        )

    # Check delta within max_movement
    if abs(candidate.bounded_delta) > param_config["max_movement"] + 1e-9:
        return "reject", (
            f"abs(bounded_delta) ({abs(candidate.bounded_delta)}) > max_movement ({param_config['max_movement']})"
        )

    # Check parameter is allowed
    if not param_config.get("allowed", False):
        return "reject", f"parameter '{param_name}' has allowed=false in config"

    return "advance", "within control envelope"


def check_destabilizing_combination(
    candidates: dict[str, CalibrationCandidate],
) -> list[str]:
    """Check for destabilizing combinations across candidates in the same surface group.

    Returns list of warning strings (empty if no issues).
    """
    warnings = []
    for surface_name, group_params in SURFACE_GROUPS.items():
        active = [
            c for name, c in candidates.items()
            if name in group_params and c.status == "candidate"
        ]
        if len(active) < 2:
            continue

        directions = {c.param_name: c.net_direction for c in active}
        has_positive = any(d > 0 for d in directions.values())
        has_negative = any(d < 0 for d in directions.values())
        if has_positive and has_negative:
            warnings.append(
                f"destabilizing combination in '{surface_name}' surface: "
                f"opposing directions among {list(directions.keys())}"
            )
    return warnings
