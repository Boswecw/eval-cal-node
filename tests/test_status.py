"""Tests for status CLI and summary report (Slice G)."""

import json
import pytest
from pathlib import Path

from eval_cal_node.services.status import report_status, generate_summary_report
from eval_cal_node.validation.validate_record import validate_and_ingest_record
from eval_cal_node.errors import RevisionError
from helpers import make_record


def _write_test_config(tmp_path):
    """Write a minimal config for testing."""
    config = {
        "node_revision": "cal_node_rev1",
        "min_sample_size": 5,
        "min_recurrence": 3,
        "effect_floor": 0.15,
        "sensitivity_factor": 0.5,
        "hold_after_decline_cycles": 3,
        "min_new_recurrence": 2,
        "rounding_digits": 6,
        "parameters": {
            "hazard_hidden_uplift_strength": {
                "current_value": 0.20,
                "param_min": 0.05,
                "param_max": 0.50,
                "max_movement": 0.05,
                "allowed": True,
            }
        },
    }
    path = tmp_path / "config.json"
    with open(path, "w") as f:
        json.dump(config, f)
    return path


class TestStatus:
    """Slice G required tests."""

    def test_status_cold_start_zero_records(self, tmp_path, capsys):
        """Test 1: status reports COLD_START with zero records."""
        records_dir = tmp_path / "records"
        records_dir.mkdir()
        config_path = _write_test_config(tmp_path)
        rc = report_status(records_dir, config_path)
        assert rc == 0
        output = capsys.readouterr().out
        assert "COLD_START" in output

    def test_status_correct_counts(self, tmp_path, capsys):
        """Test 2: status reports correct counts and thresholds."""
        records_dir = tmp_path / "records"
        records_dir.mkdir()
        config_path = _write_test_config(tmp_path)

        # Ingest 3 records (below min_sample_size of 5)
        for i in range(3):
            record = make_record(run_id=f"run-{i}", base_commit=f"base-{i}", head_commit=f"head-{i}")
            validate_and_ingest_record(record, records_dir)

        rc = report_status(records_dir, config_path)
        assert rc == 0
        output = capsys.readouterr().out
        assert "Total records: 3" in output
        assert "WARMING" in output

    def test_summary_report_writes(self, tmp_path):
        """Test 3: Summary report writes correctly."""
        records_dir = tmp_path / "records"
        records_dir.mkdir()
        reports_dir = tmp_path / "reports"
        config_path = _write_test_config(tmp_path)

        report_path = generate_summary_report(records_dir, reports_dir, config_path)
        assert report_path.exists()
        content = report_path.read_text()
        assert "Eval Cal Node Summary" in content
        assert "COLD_START" in content

    def test_backfill_allows_older_with_warning(self, tmp_path):
        """Test 4: --backfill allows older revision records."""
        records_dir = tmp_path / "records"
        records_dir.mkdir()
        record = make_record(recorded_at_revision="cal_node_rev0")
        record_id = validate_and_ingest_record(record, records_dir, backfill=True)
        assert (records_dir / f"{record_id}.json").exists()

    def test_without_backfill_older_rejected(self, tmp_path):
        """Test 5: Without --backfill, older revision records are rejected."""
        records_dir = tmp_path / "records"
        records_dir.mkdir()
        record = make_record(recorded_at_revision="cal_node_rev0")
        with pytest.raises(RevisionError):
            validate_and_ingest_record(record, records_dir, backfill=False)
