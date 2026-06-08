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

    The per-parameter sufficiency thresholds (min_sample_size on implicated
    count, min_recurrence, effect_floor, conflicting-signal) are evaluated once
    in ``compute_candidate`` and surfaced via ``candidate.reason_code``; Gate 1
    maps those codes to outcomes rather than re-deriving them. The only check
    unique to Gate 1 is total history depth, which the candidate math does not
    consider.
    """
    min_sample_size = config["min_sample_size"]

    # Check minimum total history depth (Gate 1-only; not seen by candidate math)
    if pattern.n_total < min_sample_size:
        return "hold", f"total records ({pattern.n_total}) < min_sample_size ({min_sample_size})"

    # Map the candidate's sufficiency classification to a Gate 1 outcome.
    hold_codes = {"insufficient_sample", "insufficient_recurrence"}
    reject_codes = {"below_effect_floor", "conflicting_signal"}
    if candidate.reason_code in hold_codes:
        return "hold", candidate.reason
    if candidate.reason_code in reject_codes:
        return "reject", candidate.reason

    return "advance", "sufficiency conditions met"
