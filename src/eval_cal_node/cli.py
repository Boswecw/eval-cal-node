"""CLI entrypoint for Eval Cal Node."""

import argparse
import json
import sys
from pathlib import Path

from eval_cal_node.errors import CalNodeError
from eval_cal_node.validation.validate_record import validate_and_ingest_record

# Records and proposals are written relative to the current working directory
# so the tool behaves correctly whether run from a source checkout or installed
# as a wheel. Override with --records-dir / --proposals-dir.
DEFAULT_RECORDS_DIR = Path("records")
DEFAULT_PROPOSALS_DIR = Path("proposals")
DEFAULT_REPORTS_DIR = Path("reports")


def cmd_record(args: argparse.Namespace) -> int:
    """Handle the 'record' subcommand."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        with open(input_path) as f:
            record_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {input_path}: {e}", file=sys.stderr)
        return 1

    records_dir = Path(args.records_dir) if args.records_dir else DEFAULT_RECORDS_DIR

    try:
        record_id = validate_and_ingest_record(
            record_data,
            records_dir,
            backfill=args.backfill,
        )
    except (CalNodeError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"RECORDED {record_id}")
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    """Handle the 'propose' subcommand.

    Runs Gate 1 and Gate 2 over the ingested records and emits the proposal,
    evidence, param-delta, gate-decision, and (for any Gate 3-ready parameter)
    approval-request artifacts. Gate 3 itself remains a human review step
    (see the 'review' subcommand).
    """
    from eval_cal_node.config import load_config, get_allowed_parameters
    from eval_cal_node.services.pattern_extractor import extract_patterns, load_all_records
    from eval_cal_node.services.calibration_math import compute_all_candidates
    from eval_cal_node.services.gate_runner import run_gates
    from eval_cal_node.services.artifact_writers import (
        write_approval_request,
        write_evidence,
        write_param_delta,
        write_proposal,
    )

    records_dir = Path(args.records_dir) if args.records_dir else DEFAULT_RECORDS_DIR
    proposals_dir = Path(args.proposals_dir) if args.proposals_dir else DEFAULT_PROPOSALS_DIR
    config_path = Path(args.config) if args.config else None

    try:
        config = load_config(config_path)
    except (CalNodeError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    records = load_all_records(records_dir)
    n_total = len(records)
    min_sample_size = config["min_sample_size"]
    if n_total < min_sample_size:
        print(f"Not enough records to propose: {n_total}/{min_sample_size}. No proposal emitted.")
        return 0

    allowed = get_allowed_parameters(config)
    patterns = extract_patterns(records, allowed)
    candidates = compute_all_candidates(patterns, allowed, config)

    gate_decision = run_gates(candidates, patterns, allowed, config, proposals_dir)
    proposal_id = gate_decision["proposal_id"]
    node_revision = config["node_revision"]

    write_proposal(proposal_id, node_revision, n_total, candidates, proposals_dir)
    write_evidence(proposal_id, node_revision, n_total, patterns, candidates, proposals_dir)
    write_param_delta(proposal_id, node_revision, candidates, allowed, proposals_dir)

    gate3_params = [
        e["param_name"]
        for e in gate_decision["parameters_evaluated"]
        if e["final_routing"] == "gate3_ready"
    ]
    if gate3_params:
        write_approval_request(
            proposal_id, node_revision, gate3_params,
            candidates, patterns, allowed, proposals_dir,
        )

    routing_counts: dict[str, int] = {}
    for e in gate_decision["parameters_evaluated"]:
        routing_counts[e["final_routing"]] = routing_counts.get(e["final_routing"], 0) + 1

    print(f"PROPOSED {proposal_id}")
    print(f"  Records evaluated: {n_total}")
    for routing in sorted(routing_counts):
        print(f"  {routing}: {routing_counts[routing]}")
    if gate3_params:
        print(f"  Gate 3 review required for: {', '.join(gate3_params)}")
        print(f"  Run: eval-cal-node review --proposal {proposal_id}")
    else:
        print("  No parameters reached Gate 3; nothing to review.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle the 'status' subcommand."""
    from eval_cal_node.services.status import report_status
    records_dir = Path(args.records_dir) if args.records_dir else DEFAULT_RECORDS_DIR
    config_path = Path(args.config) if args.config else None
    return report_status(records_dir, config_path)


def cmd_report(args: argparse.Namespace) -> int:
    """Handle the 'report' subcommand — write a markdown status summary."""
    from eval_cal_node.services.status import generate_summary_report

    records_dir = Path(args.records_dir) if args.records_dir else DEFAULT_RECORDS_DIR
    reports_dir = Path(args.reports_dir) if args.reports_dir else DEFAULT_REPORTS_DIR
    config_path = Path(args.config) if args.config else None

    try:
        report_path = generate_summary_report(records_dir, reports_dir, config_path)
    except (CalNodeError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"REPORT {report_path}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Handle the 'review' subcommand."""
    from eval_cal_node.config import load_config
    from eval_cal_node.services.gate3 import review_proposal
    proposals_dir = Path(args.proposals_dir) if args.proposals_dir else DEFAULT_PROPOSALS_DIR

    # Config is needed so a 'declined' decision can compute its hold-after-decline
    # thresholds; without it that doctrine is silently unenforced.
    try:
        config = load_config(Path(args.config) if args.config else None)
    except (CalNodeError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    return review_proposal(args.proposal, proposals_dir, config=config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval-cal-node",
        description="Eval Cal Node — post-implementation calibration for Forge Eval",
    )
    sub = parser.add_subparsers(dest="command")

    # record
    rec = sub.add_parser("record", help="Ingest a calibration record")
    rec.add_argument("--input", required=True, help="Path to record JSON file")
    rec.add_argument("--backfill", action="store_true", help="Allow records from prior node revisions")
    rec.add_argument("--records-dir", default=None, help="Override records directory")

    # propose
    pp = sub.add_parser("propose", help="Run the gates over records and emit a proposal")
    pp.add_argument("--records-dir", default=None, help="Override records directory")
    pp.add_argument("--proposals-dir", default=None, help="Override proposals directory")
    pp.add_argument("--config", default=None, help="Override config path")

    # status
    st = sub.add_parser("status", help="Report node status")
    st.add_argument("--records-dir", default=None, help="Override records directory")
    st.add_argument("--config", default=None, help="Override config path")

    # report
    rp = sub.add_parser("report", help="Write a markdown status summary")
    rp.add_argument("--records-dir", default=None, help="Override records directory")
    rp.add_argument("--reports-dir", default=None, help="Override reports directory")
    rp.add_argument("--config", default=None, help="Override config path")

    # review
    rv = sub.add_parser("review", help="Review a Gate 3 proposal")
    rv.add_argument("--proposal", required=True, help="Proposal ID to review")
    rv.add_argument("--proposals-dir", default=None, help="Override proposals directory")
    rv.add_argument("--config", default=None, help="Override config path")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "record": cmd_record,
        "propose": cmd_propose,
        "status": cmd_status,
        "report": cmd_report,
        "review": cmd_review,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
