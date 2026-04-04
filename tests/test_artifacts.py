"""Tests for output artifact assembly (Slice E)."""

import json
import pytest

from eval_cal_node.errors import SchemaValidationError
from eval_cal_node.services.artifact_writers import (
    write_approval_request,
    write_evidence,
    write_param_delta,
    write_proposal,
)
from eval_cal_node.services.calibration_math import CalibrationCandidate, compute_candidate
from eval_cal_node.services.pattern_extractor import PatternResult
from eval_cal_node.validation.schema_loader import validate_against_schema


PARAM_CONFIG = {
    "current_value": 0.20,
    "param_min": 0.05,
    "param_max": 0.50,
    "max_movement": 0.05,
    "allowed": True,
}


def _make_test_data():
    """Create matching patterns/candidates for testing."""
    pr = PatternResult("hazard_hidden_uplift_strength")
    pr.n_total = 10
    pr.n_total_implicated = 8
    pr.n_false_block = 7
    pr.n_missed_block = 0
    pr.n_false_caution = 1
    pr.n_missed_caution = 0
    pr.recurrence_repos = {"r1", "r2", "r3", "r4"}

    candidate = compute_candidate(pr, PARAM_CONFIG,
        effect_floor=0.15, sensitivity_factor=0.5,
        min_sample_size=5, min_recurrence=3, rounding_digits=6)

    patterns = {"hazard_hidden_uplift_strength": pr}
    candidates = {"hazard_hidden_uplift_strength": candidate}
    allowed = {"hazard_hidden_uplift_strength": PARAM_CONFIG}
    return patterns, candidates, allowed


class TestArtifactValidation:
    """Slice E required tests."""

    def test_each_artifact_validates(self, tmp_path):
        """Test 1: Each artifact validates against its schema."""
        patterns, candidates, allowed = _make_test_data()
        pid = "test_proposal_001"
        nrev = "cal_node_rev1"

        p = write_proposal(pid, nrev, 10, candidates, tmp_path)
        validate_against_schema(p, "eval_calibration_proposal")

        e = write_evidence(pid, nrev, 10, patterns, candidates, tmp_path)
        validate_against_schema(e, "eval_calibration_evidence")

        d = write_param_delta(pid, nrev, candidates, allowed, tmp_path)
        validate_against_schema(d, "eval_param_delta")

        a = write_approval_request(pid, nrev, ["hazard_hidden_uplift_strength"],
                                   candidates, patterns, allowed, tmp_path)
        validate_against_schema(a, "eval_approval_request")

    def test_malformed_artifact_fails(self):
        """Test 2: Malformed artifact fails schema validation."""
        bad_proposal = {
            "proposal_id": "x",
            "node_revision": "r",
            # missing record_count and proposals
        }
        with pytest.raises(SchemaValidationError):
            validate_against_schema(bad_proposal, "eval_calibration_proposal")

    def test_deterministic_byte_identical(self, tmp_path):
        """Test 3: Deterministic — same inputs produce byte-identical artifacts."""
        patterns, candidates, allowed = _make_test_data()
        pid = "det_test"
        nrev = "cal_node_rev1"

        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"

        write_proposal(pid, nrev, 10, candidates, dir1)
        write_proposal(pid, nrev, 10, candidates, dir2)

        f1 = (dir1 / f"{pid}_proposal.json").read_bytes()
        f2 = (dir2 / f"{pid}_proposal.json").read_bytes()
        assert f1 == f2

    def test_proposal_includes_all_deltas(self, tmp_path):
        """Test 4: Proposal artifact includes all required parameter deltas."""
        patterns, candidates, allowed = _make_test_data()
        pid = "test_prop"
        p = write_proposal(pid, "cal_node_rev1", 10, candidates, tmp_path)
        assert len(p["proposals"]) == 1
        entry = p["proposals"][0]
        assert "param_name" in entry
        assert "bounded_delta" in entry
        assert "proposed_value" in entry

    def test_evidence_includes_pattern_results(self, tmp_path):
        """Test 5: Evidence artifact includes full pattern extraction results."""
        patterns, candidates, allowed = _make_test_data()
        pid = "test_ev"
        e = write_evidence(pid, "cal_node_rev1", 10, patterns, candidates, tmp_path)
        assert len(e["evidence"]) == 1
        ev = e["evidence"][0]
        assert ev["n_false_block"] == 7
        assert ev["n_total_implicated"] == 8
        assert ev["recurrence_count"] == 4

    def test_approval_request_complete(self, tmp_path):
        """Test 6: Approval request artifact is compact and complete."""
        patterns, candidates, allowed = _make_test_data()
        pid = "test_ar"
        a = write_approval_request(pid, "cal_node_rev1",
                                   ["hazard_hidden_uplift_strength"],
                                   candidates, patterns, allowed, tmp_path)
        assert len(a["requests"]) == 1
        req = a["requests"][0]
        assert req["param_name"] == "hazard_hidden_uplift_strength"
        assert "affected_surfaces" in req
        assert "hazard" in req["affected_surfaces"]
        assert req["recommendation"] == "accept"
