"""Record validation and ingestion for Eval Cal Node."""

import hashlib
import json
from pathlib import Path

from eval_cal_node.errors import (
    DuplicateRecordError,
    RecordIdMismatchError,
    RevisionError,
    SchemaValidationError,
)
from eval_cal_node.validation.schema_loader import validate_against_schema

NODE_REVISION = "cal_node_rev1"


def compute_record_id(slice_ref: dict) -> str:
    """Compute deterministic record_id from slice_ref fields."""
    raw = slice_ref["repo"] + slice_ref["base_commit"] + slice_ref["head_commit"] + slice_ref["run_id"]
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_and_ingest_record(
    record_data: dict,
    records_dir: Path,
    *,
    backfill: bool = False,
) -> str:
    """Validate a record and write it to the records directory.

    Returns the record_id on success.
    """
    validate_against_schema(record_data, "cal_record_v1")

    expected_id = compute_record_id(record_data["slice_ref"])
    if record_data["record_id"] != expected_id:
        raise RecordIdMismatchError(
            f"record_id mismatch: input has '{record_data['record_id']}', "
            f"computed '{expected_id}'"
        )

    if not backfill:
        if record_data["recorded_at_revision"] != NODE_REVISION:
            raise RevisionError(
                f"Record revision '{record_data['recorded_at_revision']}' does not match "
                f"node revision '{NODE_REVISION}'. Use --backfill to allow older revisions."
            )

    records_dir.mkdir(parents=True, exist_ok=True)
    dest = records_dir / f"{expected_id}.json"
    if dest.exists():
        raise DuplicateRecordError(f"Record {expected_id} already exists at {dest}")

    with open(dest, "w") as f:
        json.dump(record_data, f, sort_keys=True, separators=(",", ":"))

    return expected_id
