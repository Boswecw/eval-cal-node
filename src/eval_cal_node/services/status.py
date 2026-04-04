"""Status reporting and summary generation for Eval Cal Node."""

import json
import sys
from datetime import date
from pathlib import Path

from eval_cal_node.config import load_config, get_allowed_parameters
from eval_cal_node.services.calibration_math import compute_all_candidates
from eval_cal_node.services.pattern_extractor import extract_patterns, load_all_records


def report_status(records_dir: Path, config_path: Path | None = None) -> int:
    """Report current node status to stdout. Returns exit code."""
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
        return 1

    records = load_all_records(records_dir)
    n_total = len(records)
    min_sample_size = config["min_sample_size"]
    node_revision = config["node_revision"]

    print(f"=== Eval Cal Node Status ===")
    print(f"Node revision: {node_revision}")
    print(f"Total records: {n_total}")

    if n_total == 0:
        print(f"Status: COLD_START")
        print(f"Records needed for first Gate 1 pass: {min_sample_size}")
        return 0

    if n_total < min_sample_size:
        print(f"Status: WARMING ({n_total}/{min_sample_size} records)")
        print(f"Records needed: {min_sample_size - n_total} more")
        return 0

    print(f"Status: OPERATIONAL")

    allowed = get_allowed_parameters(config)
    patterns = extract_patterns(records, allowed)
    candidates = compute_all_candidates(patterns, allowed, config)

    print(f"\nPer-parameter status:")
    for name in sorted(candidates.keys()):
        c = candidates[name]
        p = patterns[name]
        print(f"  {name}: {c.status} (implicated={p.n_total_implicated}, recurrence={p.recurrence_count})")

    return 0


def generate_summary_report(
    records_dir: Path,
    reports_dir: Path,
    config_path: Path | None = None,
) -> Path:
    """Generate a markdown summary report. Returns the path to the written file."""
    config = load_config(config_path)
    records = load_all_records(records_dir)
    n_total = len(records)
    allowed = get_allowed_parameters(config)

    today = date.today().isoformat()
    report_path = reports_dir / f"{today}_summary.md"
    reports_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Eval Cal Node Summary — {today}",
        "",
        f"Node revision: {config['node_revision']}",
        f"Record count: {n_total}",
        "",
    ]

    if n_total == 0:
        lines.append("Status: COLD_START — no records ingested yet.")
        lines.append(f"Records needed for first analysis: {config['min_sample_size']}")
    elif n_total < config["min_sample_size"]:
        lines.append(f"Status: WARMING — {n_total}/{config['min_sample_size']} records.")
        lines.append(f"Records needed: {config['min_sample_size'] - n_total} more.")
    else:
        lines.append("Status: OPERATIONAL")
        lines.append("")

        patterns = extract_patterns(records, allowed)
        candidates = compute_all_candidates(patterns, allowed, config)

        # Active candidates
        active = {n: c for n, c in candidates.items() if c.status == "candidate"}
        held = {n: c for n, c in candidates.items() if c.status == "hold"}

        lines.append("## Parameters with active candidates")
        lines.append("")
        if active:
            for name, c in sorted(active.items()):
                lines.append(f"- **{name}**: {c.current_value} -> {c.proposed_value} (delta: {c.bounded_delta:+.6f})")
        else:
            lines.append("None.")
        lines.append("")

        lines.append("## Parameters on hold")
        lines.append("")
        if held:
            for name, c in sorted(held.items()):
                lines.append(f"- **{name}**: {c.reason}")
        else:
            lines.append("None.")

    lines.append("")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    return report_path
