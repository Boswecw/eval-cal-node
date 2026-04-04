"""Gate 1 — Sufficiency gate (fully autonomous)."""

from eval_cal_node.services.calibration_math import CalibrationCandidate
from eval_cal_node.services.pattern_extractor import PatternResult


def evaluate_gate1(
    candidate: CalibrationCandidate,
    pattern: PatternResult,
    config: dict,
) -> tuple[str, str]:
    """Evaluate Gate 1 sufficiency for a candidate.

    Returns (outcome, reason) where outcome is 'reject' | 'hold' | 'advance'.
    """
    min_sample_size = config["min_sample_size"]
    min_recurrence = config["min_recurrence"]
    effect_floor = config["effect_floor"]

    # Check minimum history depth
    if pattern.n_total < min_sample_size:
        return "hold", f"total records ({pattern.n_total}) < min_sample_size ({min_sample_size})"

    # Check minimum implicated count
    if pattern.n_total_implicated < min_sample_size:
        return "hold", f"n_total_implicated ({pattern.n_total_implicated}) < min_sample_size ({min_sample_size})"

    # Check recurrence
    if pattern.recurrence_count < min_recurrence:
        return "hold", f"recurrence_count ({pattern.recurrence_count}) < min_recurrence ({min_recurrence})"

    # Check effect floor
    if abs(candidate.net_direction) < effect_floor:
        return "reject", f"abs(net_direction) ({abs(candidate.net_direction):.6f}) below effect_floor ({effect_floor})"

    # Check conflicting signal
    if candidate.false_block_rate > 0.3 and candidate.missed_block_rate > 0.3:
        return "reject", "conflicting signal: both false_block_rate and missed_block_rate > 0.3"

    # Candidate already held by calibration math
    if candidate.status == "hold":
        return "hold", candidate.reason

    return "advance", "sufficiency conditions met"
