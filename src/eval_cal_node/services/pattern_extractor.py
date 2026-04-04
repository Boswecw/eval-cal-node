"""Pattern extraction over calibration records."""

import json
from pathlib import Path
from typing import Any


class PatternResult:
    """Pattern extraction result for one parameter."""

    def __init__(self, param_name: str) -> None:
        self.param_name = param_name
        self.n_false_block = 0
        self.n_missed_block = 0
        self.n_false_caution = 0
        self.n_missed_caution = 0
        self.n_total_implicated = 0
        self.n_total = 0
        self.recurrence_repos: set[str] = set()

    @property
    def recurrence_count(self) -> int:
        return len(self.recurrence_repos)

    def to_dict(self) -> dict[str, Any]:
        return {
            "param_name": self.param_name,
            "n_false_block": self.n_false_block,
            "n_missed_block": self.n_missed_block,
            "n_false_caution": self.n_false_caution,
            "n_missed_caution": self.n_missed_caution,
            "n_total_implicated": self.n_total_implicated,
            "n_total": self.n_total,
            "recurrence_count": self.recurrence_count,
        }


def load_all_records(records_dir: Path) -> list[dict]:
    """Load all record JSON files from the records directory, sorted by filename for determinism."""
    if not records_dir.exists():
        return []
    paths = sorted(records_dir.glob("*.json"))
    records = []
    for p in paths:
        with open(p) as f:
            records.append(json.load(f))
    return records


def extract_patterns(
    records: list[dict],
    allowed_params: dict[str, dict],
) -> dict[str, PatternResult]:
    """Extract pattern results for each allowed parameter from the record set."""
    results: dict[str, PatternResult] = {}
    for param_name in sorted(allowed_params.keys()):
        results[param_name] = PatternResult(param_name)

    n_total = len(records)
    for pr in results.values():
        pr.n_total = n_total

    for record in records:
        outcome = record["reconciliation_outcome"]
        drift_types = set(outcome.get("drift_types", []))
        implicated = set(outcome.get("implicated_parameters", []))
        repo = record["slice_ref"]["repo"]

        for param_name, pr in results.items():
            if param_name not in implicated:
                continue

            pr.n_total_implicated += 1
            pr.recurrence_repos.add(repo)

            if "false_block" in drift_types:
                pr.n_false_block += 1
            if "missed_block" in drift_types:
                pr.n_missed_block += 1
            if "false_caution" in drift_types:
                pr.n_false_caution += 1
            if "missed_caution" in drift_types:
                pr.n_missed_caution += 1

    return results
