"""Gate 2 — Control envelope gate (fully autonomous)."""

from eval_cal_node.services.calibration_math import CalibrationCandidate

# Parameters that affect the same Eval math surface — opposing movements are
# destabilizing. This mapping is also the single in-module source of truth for
# which parameter names are legitimate calibration targets (see ALLOWED_PARAMETERS).
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

# Structural allow-list of calibratable parameter names, derived from the surface
# groups so the names are written exactly once. This is a control-envelope guard
# independent of the per-parameter ``allowed`` flag in config: a name that is not
# a recognized calibration target is rejected even if a caller marks it allowed.
# ``test_config`` keeps this set in sync with the production config.
ALLOWED_PARAMETERS = frozenset().union(*SURFACE_GROUPS.values())


def evaluate_gate2(
    candidate: CalibrationCandidate,
    param_config: dict,
) -> tuple[str, str]:
    """Evaluate Gate 2 control envelope for a single candidate.

    Returns (outcome, reason) where outcome is 'reject' | 'hold' | 'advance'.
    """
    param_name = candidate.param_name

    # Check allowed list (structural control-envelope guard)
    if param_name not in ALLOWED_PARAMETERS:
        return "reject", f"parameter '{param_name}' not in allowed calibration targets"

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
