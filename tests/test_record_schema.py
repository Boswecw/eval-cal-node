"""Tests for cal_record_v1 schema validation and record ingestion (Slice A)."""

import json
import pytest
from pathlib import Path

from eval_cal_node.errors import (
    DuplicateRecordError,
    RecordIdMismatchError,
    RevisionError,
    SchemaValidationError,
)
from eval_cal_node.validation.validate_record import (
    compute_record_id,
    validate_and_ingest_record,
)
from helpers import make_record


@pytest.fixture
def tmp_records(tmp_path):
    d = tmp_path / "records"
    d.mkdir()
    return d


class TestRecordIngestion:
    """Slice A required tests."""

    def test_valid_record_ingests_correctly(self, tmp_records):
        """Test 1: Valid record ingests correctly."""
        record = make_record()
        record_id = validate_and_ingest_record(record, tmp_records)
        assert record_id == record["record_id"]
        dest = tmp_records / f"{record_id}.json"
        assert dest.exists()
        with open(dest) as f:
            stored = json.load(f)
        assert stored["slice_ref"]["repo"] == "test-repo"

    def test_schema_violation_fails_closed(self, tmp_records):
        """Test 2: Schema violation fails closed."""
        record = make_record()
        del record["eval_signals"]
        with pytest.raises(SchemaValidationError):
            validate_and_ingest_record(record, tmp_records)

    def test_record_id_mismatch_fails_closed(self, tmp_records):
        """Test 3: record_id mismatch fails closed."""
        record = make_record()
        record["record_id"] = "wrong_id_value"
        with pytest.raises(RecordIdMismatchError):
            validate_and_ingest_record(record, tmp_records)

    def test_duplicate_record_fails_closed(self, tmp_records):
        """Test 4: Duplicate record fails closed."""
        record = make_record()
        validate_and_ingest_record(record, tmp_records)
        with pytest.raises(DuplicateRecordError):
            validate_and_ingest_record(record, tmp_records)

    def test_backfill_allows_older_revision(self, tmp_records):
        """Test 5: --backfill allows older revision records."""
        record = make_record(recorded_at_revision="cal_node_rev0")
        record_id = validate_and_ingest_record(record, tmp_records, backfill=True)
        assert record_id == record["record_id"]
        assert (tmp_records / f"{record_id}.json").exists()

    def test_without_backfill_older_revision_rejected(self, tmp_records):
        """Test 6: Without --backfill, older revision records are rejected."""
        record = make_record(recorded_at_revision="cal_node_rev0")
        with pytest.raises(RevisionError):
            validate_and_ingest_record(record, tmp_records, backfill=False)


class TestRecordId:
    def test_compute_record_id_deterministic(self):
        """record_id is deterministic for same inputs."""
        ref = {"repo": "r", "base_commit": "a", "head_commit": "b", "run_id": "x"}
        id1 = compute_record_id(ref)
        id2 = compute_record_id(ref)
        assert id1 == id2
        assert len(id1) == 64  # sha256 hex

    def test_compute_record_id_varies_with_input(self):
        """Different inputs produce different record_ids."""
        ref1 = {"repo": "r1", "base_commit": "a", "head_commit": "b", "run_id": "x"}
        ref2 = {"repo": "r2", "base_commit": "a", "head_commit": "b", "run_id": "x"}
        assert compute_record_id(ref1) != compute_record_id(ref2)


class TestSchemaEdgeCases:
    def test_invalid_hazard_tier_rejected(self, tmp_records):
        record = make_record(hazard_tier="unknown")
        with pytest.raises(SchemaValidationError):
            validate_and_ingest_record(record, tmp_records)

    def test_invalid_drift_type_rejected(self, tmp_records):
        record = make_record(drift_types=["not_a_real_drift"])
        with pytest.raises(SchemaValidationError):
            validate_and_ingest_record(record, tmp_records)

    def test_additional_properties_rejected(self, tmp_records):
        record = make_record()
        record["extra_field"] = "not allowed"
        with pytest.raises(SchemaValidationError):
            validate_and_ingest_record(record, tmp_records)

    def test_negative_hazard_score_rejected(self, tmp_records):
        record = make_record(hazard_score=-0.1)
        with pytest.raises(SchemaValidationError):
            validate_and_ingest_record(record, tmp_records)
