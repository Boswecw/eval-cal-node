"""Calibration math — deterministic candidate delta computation."""

from typing import Any

from eval_cal_node.services.pattern_extractor import PatternResult


class CalibrationCandidate:
    """Calibration candidate for one parameter."""

    def __init__(
        self,
        param_name: str,
        *,
        status: str,
        false_block_rate: float,
        missed_block_rate: float,
        net_direction: float,
        raw_delta: float,
        bounded_delta: float,
        proposed_value: float,
        current_value: float,
        reason: str = "",
    ) -> None:
        self.param_name = param_name
        self.status = status
        self.false_block_rate = false_block_rate
        self.missed_block_rate = missed_block_rate
        self.net_direction = net_direction
        self.raw_delta = raw_delta
        self.bounded_delta = bounded_delta
        self.proposed_value = proposed_value
        self.current_value = current_value
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "param_name": self.param_name,
            "status": self.status,
            "false_block_rate": self.false_block_rate,
            "missed_block_rate": self.missed_block_rate,
            "net_direction": self.net_direction,
            "raw_delta": self.raw_delta,
            "bounded_delta": self.bounded_delta,
            "proposed_value": self.proposed_value,
            "current_value": self.current_value,
            "reason": self.reason,
        }


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_candidate(
    pattern: PatternResult,
    param_config: dict,
    *,
    effect_floor: float,
    sensitivity_factor: float,
    min_sample_size: int,
    min_recurrence: int,
    rounding_digits: int,
) -> CalibrationCandidate:
    """Compute a calibration candidate for one parameter from its pattern result."""
    current_value = param_config["current_value"]
    param_min = param_config["param_min"]
    param_max = param_config["param_max"]
    max_movement = param_config["max_movement"]

    # Defaults for when we can't compute rates
    false_block_rate = 0.0
    missed_block_rate = 0.0
    net_direction = 0.0
    raw_delta = 0.0
    bounded_delta = 0.0
    proposed_value = current_value

    # Step 4 first: evidence quality check (sample size and recurrence)
    if pattern.n_total_implicated < min_sample_size:
        return CalibrationCandidate(
            pattern.param_name,
            status="hold",
            false_block_rate=false_block_rate,
            missed_block_rate=missed_block_rate,
            net_direction=net_direction,
            raw_delta=raw_delta,
            bounded_delta=bounded_delta,
            proposed_value=proposed_value,
            current_value=current_value,
            reason=f"n_total_implicated ({pattern.n_total_implicated}) < min_sample_size ({min_sample_size})",
        )

    if pattern.recurrence_count < min_recurrence:
        return CalibrationCandidate(
            pattern.param_name,
            status="hold",
            false_block_rate=false_block_rate,
            missed_block_rate=missed_block_rate,
            net_direction=net_direction,
            raw_delta=raw_delta,
            bounded_delta=bounded_delta,
            proposed_value=proposed_value,
            current_value=current_value,
            reason=f"recurrence_count ({pattern.recurrence_count}) < min_recurrence ({min_recurrence})",
        )

    # Step 1: rates
    false_block_rate = pattern.n_false_block / pattern.n_total_implicated
    missed_block_rate = pattern.n_missed_block / pattern.n_total_implicated
    net_direction = missed_block_rate - false_block_rate

    # Step 2: effect check — conflicting signal check first
    if false_block_rate > 0.3 and missed_block_rate > 0.3:
        return CalibrationCandidate(
            pattern.param_name,
            status="hold",
            false_block_rate=false_block_rate,
            missed_block_rate=missed_block_rate,
            net_direction=net_direction,
            raw_delta=raw_delta,
            bounded_delta=bounded_delta,
            proposed_value=proposed_value,
            current_value=current_value,
            reason="conflicting signal: both false_block_rate and missed_block_rate > 0.3",
        )

    if abs(net_direction) < effect_floor:
        return CalibrationCandidate(
            pattern.param_name,
            status="hold",
            false_block_rate=false_block_rate,
            missed_block_rate=missed_block_rate,
            net_direction=net_direction,
            raw_delta=raw_delta,
            bounded_delta=bounded_delta,
            proposed_value=proposed_value,
            current_value=current_value,
            reason=f"abs(net_direction) ({abs(net_direction):.6f}) < effect_floor ({effect_floor})",
        )

    # Step 3: bounded delta
    raw_delta = net_direction * sensitivity_factor
    bounded_delta = _clamp(raw_delta, -max_movement, max_movement)
    proposed_value = _clamp(current_value + bounded_delta, param_min, param_max)
    proposed_value = round(proposed_value, rounding_digits)

    return CalibrationCandidate(
        pattern.param_name,
        status="candidate",
        false_block_rate=round(false_block_rate, rounding_digits),
        missed_block_rate=round(missed_block_rate, rounding_digits),
        net_direction=round(net_direction, rounding_digits),
        raw_delta=round(raw_delta, rounding_digits),
        bounded_delta=round(bounded_delta, rounding_digits),
        proposed_value=proposed_value,
        current_value=current_value,
        reason="candidate: meaningful directional signal with sufficient evidence",
    )


def compute_all_candidates(
    patterns: dict[str, PatternResult],
    allowed_params: dict[str, dict],
    config: dict,
) -> dict[str, CalibrationCandidate]:
    """Compute candidates for all allowed parameters."""
    candidates = {}
    for param_name in sorted(patterns.keys()):
        if param_name not in allowed_params:
            continue
        candidates[param_name] = compute_candidate(
            patterns[param_name],
            allowed_params[param_name],
            effect_floor=config["effect_floor"],
            sensitivity_factor=config["sensitivity_factor"],
            min_sample_size=config["min_sample_size"],
            min_recurrence=config["min_recurrence"],
            rounding_digits=config["rounding_digits"],
        )
    return candidates
