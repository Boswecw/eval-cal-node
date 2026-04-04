"""Tests for Gate 3 CLI and rejection feedback loop (Slice F)."""

import json
import pytest

from eval_cal_node.services.gate3 import review_proposal, is_proposal_held


def _write_artifacts(proposals_dir, proposal_id="test_proposal"):
    """Write minimal approval request and gate decision artifacts."""
    approval = {
        "proposal_id": proposal_id,
        "node_revision": "cal_node_rev1",
        "requests": [{
            "param_name": "hazard_hidden_uplift_strength",
            "current_value": 0.20,
            "proposed_value": 0.15,
            "bounded_delta": -0.05,
            "param_min": 0.05,
            "param_max": 0.50,
            "net_direction": -0.875,
            "false_block_rate": 0.875,
            "missed_block_rate": 0.0,
            "n_total_implicated": 8,
            "recurrence_count": 4,
            "affected_surfaces": ["hazard"],
            "recommendation": "accept",
        }],
    }
    gate_decision = {
        "proposal_id": proposal_id,
        "node_revision": "cal_node_rev1",
        "evaluated_at_record_count": 10,
        "parameters_evaluated": [{
            "param_name": "hazard_hidden_uplift_strength",
            "candidate_status": "candidate",
            "gate1_outcome": "advance",
            "gate1_reason": "sufficiency conditions met",
            "gate2_outcome": "advance",
            "gate2_reason": "within control envelope",
            "final_routing": "gate3_ready",
        }],
    }

    proposals_dir.mkdir(parents=True, exist_ok=True)
    with open(proposals_dir / f"{proposal_id}_approval_request.json", "w") as f:
        json.dump(approval, f)
    with open(proposals_dir / f"{proposal_id}_gate_decision.json", "w") as f:
        json.dump(gate_decision, f)


CONFIG = {
    "hold_after_decline_cycles": 3,
    "min_new_recurrence": 2,
}


class TestGate3:
    """Slice F required tests."""

    def test_accept_stamps_correctly(self, tmp_path):
        """Test 1: Accept stamps proposal correctly."""
        proposals_dir = tmp_path / "proposals"
        _write_artifacts(proposals_dir)
        rc = review_proposal("test_proposal", proposals_dir, response="yes")
        assert rc == 0
        review_path = proposals_dir / "test_proposal_review.json"
        assert review_path.exists()
        with open(review_path) as f:
            review = json.load(f)
        assert review["decision"] == "accepted"

    def test_decline_stamps_and_sets_thresholds(self, tmp_path):
        """Test 2: Decline stamps proposal correctly and sets hold thresholds."""
        proposals_dir = tmp_path / "proposals"
        _write_artifacts(proposals_dir)
        rc = review_proposal("test_proposal", proposals_dir, response="no", config=CONFIG)
        assert rc == 0
        review_path = proposals_dir / "test_proposal_review.json"
        with open(review_path) as f:
            review = json.load(f)
        assert review["decision"] == "declined"
        assert review["hold_until_record_count"] == 13  # 10 + 3
        assert review["hold_until_recurrence"]["hazard_hidden_uplift_strength"] == 6  # 4 + 2

    def test_declined_does_not_re_advance_until_thresholds(self, tmp_path):
        """Test 3: Declined proposal does not re-advance until hold thresholds met."""
        proposals_dir = tmp_path / "proposals"
        _write_artifacts(proposals_dir)
        review_proposal("test_proposal", proposals_dir, response="no", config=CONFIG)

        # Still held at 11 records and 4 recurrences
        assert is_proposal_held("test_proposal", proposals_dir, 11, {"hazard_hidden_uplift_strength": 4})

        # Still held at 13 records but only 5 recurrences (need 6)
        assert is_proposal_held("test_proposal", proposals_dir, 13, {"hazard_hidden_uplift_strength": 5})

    def test_declined_re_advances_when_thresholds_met(self, tmp_path):
        """Test 4: Declined proposal re-advances when both thresholds met."""
        proposals_dir = tmp_path / "proposals"
        _write_artifacts(proposals_dir)
        review_proposal("test_proposal", proposals_dir, response="no", config=CONFIG)

        # Both thresholds met: 13 records and 6 recurrences
        assert not is_proposal_held("test_proposal", proposals_dir, 13, {"hazard_hidden_uplift_strength": 6})
