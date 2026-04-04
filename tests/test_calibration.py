"""Tests for pattern extraction and calibration math (Slice C)."""

import pytest

from eval_cal_node.services.pattern_extractor import PatternResult, extract_patterns
from eval_cal_node.services.calibration_math import compute_candidate, compute_all_candidates
from helpers import make_record


PARAM_CONFIG = {
    "current_value": 0.20,
    "param_min": 0.05,
    "param_max": 0.50,
    "max_movement": 0.05,
    "allowed": True,
}

BASE_MATH_KWARGS = {
    "effect_floor": 0.15,
    "sensitivity_factor": 0.5,
    "min_sample_size": 5,
    "min_recurrence": 3,
    "rounding_digits": 6,
}


def _make_false_block_records(n: int, param: str = "hazard_hidden_uplift_strength"):
    """Create n records where param is implicated with false_block drift."""
    records = []
    for i in range(n):
        records.append(make_record(
            repo=f"repo-{i % 4}",
            run_id=f"run-fb-{i}",
            base_commit=f"base-fb-{i}",
            head_commit=f"head-fb-{i}",
            drift_found=True,
            drift_types=["false_block"],
            implicated_parameters=[param],
            disposition="confirmed_drift",
        ))
    return records


def _make_missed_block_records(n: int, param: str = "hazard_hidden_uplift_strength"):
    """Create n records where param is implicated with missed_block drift."""
    records = []
    for i in range(n):
        records.append(make_record(
            repo=f"repo-{i % 4}",
            run_id=f"run-mb-{i}",
            base_commit=f"base-mb-{i}",
            head_commit=f"head-mb-{i}",
            drift_found=True,
            drift_types=["missed_block"],
            implicated_parameters=[param],
            disposition="confirmed_drift",
        ))
    return records


class TestPatternExtraction:
    """Slice C required tests."""

    def test_correct_counts_from_synthetic_records(self):
        """Test 1: Pattern extraction produces correct counts."""
        param = "hazard_hidden_uplift_strength"
        records = _make_false_block_records(3, param) + _make_missed_block_records(2, param)
        allowed = {param: PARAM_CONFIG}
        patterns = extract_patterns(records, allowed)
        pr = patterns[param]
        assert pr.n_total == 5
        assert pr.n_total_implicated == 5
        assert pr.n_false_block == 3
        assert pr.n_missed_block == 2

    def test_net_direction_false_block_heavy(self):
        """Test 2: Net direction correct for false_block-heavy."""
        param = "hazard_hidden_uplift_strength"
        records = _make_false_block_records(6, param) + _make_missed_block_records(1, param)
        allowed = {param: PARAM_CONFIG}
        patterns = extract_patterns(records, allowed)
        pr = patterns[param]
        candidate = compute_candidate(pr, PARAM_CONFIG, **BASE_MATH_KWARGS)
        assert candidate.net_direction < 0  # overweighted → decrease

    def test_net_direction_missed_block_heavy(self):
        """Test 3: Net direction correct for missed_block-heavy."""
        param = "hazard_hidden_uplift_strength"
        records = _make_missed_block_records(6, param) + _make_false_block_records(1, param)
        allowed = {param: PARAM_CONFIG}
        patterns = extract_patterns(records, allowed)
        pr = patterns[param]
        candidate = compute_candidate(pr, PARAM_CONFIG, **BASE_MATH_KWARGS)
        assert candidate.net_direction > 0  # underweighted → increase

    def test_conflicting_signal_produces_hold(self):
        """Test 4: Conflicting signal (both high) produces hold."""
        pr = PatternResult("test_param")
        pr.n_total = 10
        pr.n_total_implicated = 10
        pr.n_false_block = 5
        pr.n_missed_block = 5
        pr.recurrence_repos = {"r1", "r2", "r3"}
        candidate = compute_candidate(pr, PARAM_CONFIG, **BASE_MATH_KWARGS)
        assert candidate.status == "hold"
        assert "conflicting" in candidate.reason

    def test_below_effect_floor_produces_hold(self):
        """Test 5: Below effect_floor produces hold."""
        pr = PatternResult("test_param")
        pr.n_total = 10
        pr.n_total_implicated = 10
        pr.n_false_block = 4  # 0.4
        pr.n_missed_block = 3  # 0.3 → net = -0.1 < 0.15 floor
        pr.recurrence_repos = {"r1", "r2", "r3"}
        candidate = compute_candidate(pr, PARAM_CONFIG, **BASE_MATH_KWARGS)
        assert candidate.status == "hold"
        assert "effect_floor" in candidate.reason

    def test_below_min_sample_size_produces_hold(self):
        """Test 6: Below min_sample_size produces hold."""
        pr = PatternResult("test_param")
        pr.n_total = 3
        pr.n_total_implicated = 3
        pr.n_false_block = 3
        pr.recurrence_repos = {"r1", "r2", "r3"}
        candidate = compute_candidate(pr, PARAM_CONFIG, **BASE_MATH_KWARGS)
        assert candidate.status == "hold"
        assert "min_sample_size" in candidate.reason

    def test_below_min_recurrence_produces_hold(self):
        """Test 7: Below min_recurrence produces hold."""
        pr = PatternResult("test_param")
        pr.n_total = 10
        pr.n_total_implicated = 10
        pr.n_false_block = 8
        pr.recurrence_repos = {"r1", "r2"}  # only 2 repos, need 3
        candidate = compute_candidate(pr, PARAM_CONFIG, **BASE_MATH_KWARGS)
        assert candidate.status == "hold"
        assert "min_recurrence" in candidate.reason

    def test_bounded_delta_does_not_exceed_max_movement(self):
        """Test 8: Bounded delta does not exceed max_movement."""
        pr = PatternResult("test_param")
        pr.n_total = 10
        pr.n_total_implicated = 10
        pr.n_false_block = 10  # 100% false block → net = -1.0, raw = -0.5
        pr.n_missed_block = 0
        pr.recurrence_repos = {"r1", "r2", "r3"}
        candidate = compute_candidate(pr, PARAM_CONFIG, **BASE_MATH_KWARGS)
        assert candidate.status == "candidate"
        assert abs(candidate.bounded_delta) <= PARAM_CONFIG["max_movement"]

    def test_proposed_value_within_bounds(self):
        """Test 9: Proposed value does not exceed [param_min, param_max]."""
        # Push strongly downward with a low current_value near param_min
        pc = {**PARAM_CONFIG, "current_value": 0.06}
        pr = PatternResult("test_param")
        pr.n_total = 10
        pr.n_total_implicated = 10
        pr.n_false_block = 10
        pr.n_missed_block = 0
        pr.recurrence_repos = {"r1", "r2", "r3"}
        candidate = compute_candidate(pr, pc, **BASE_MATH_KWARGS)
        assert candidate.proposed_value >= pc["param_min"]
        assert candidate.proposed_value <= pc["param_max"]

    def test_deterministic_same_inputs_same_output(self):
        """Test 10: Deterministic — same records + config → same output."""
        param = "hazard_hidden_uplift_strength"
        records = _make_false_block_records(6, param)
        allowed = {param: PARAM_CONFIG}

        patterns1 = extract_patterns(records, allowed)
        c1 = compute_candidate(patterns1[param], PARAM_CONFIG, **BASE_MATH_KWARGS)

        patterns2 = extract_patterns(records, allowed)
        c2 = compute_candidate(patterns2[param], PARAM_CONFIG, **BASE_MATH_KWARGS)

        assert c1.to_dict() == c2.to_dict()
