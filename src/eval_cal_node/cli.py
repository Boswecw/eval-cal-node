"""CLI entrypoint for Eval Cal Node."""

import argparse
import json
import sys
from pathlib import Path

from eval_cal_node.errors import CalNodeError
from eval_cal_node.validation.validate_record import validate_and_ingest_record

DEFAULT_RECORDS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "records"


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
    except CalNodeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"RECORDED {record_id}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle the 'status' subcommand."""
    from eval_cal_node.services.status import report_status
    records_dir = Path(args.records_dir) if args.records_dir else DEFAULT_RECORDS_DIR
    config_path = Path(args.config) if args.config else None
    return report_status(records_dir, config_path)


def cmd_review(args: argparse.Namespace) -> int:
    """Handle the 'review' subcommand."""
    from eval_cal_node.services.gate3 import review_proposal
    proposals_dir = Path(args.proposals_dir) if args.proposals_dir else (
        Path(__file__).resolve().parent.parent.parent.parent / "proposals"
    )
    return review_proposal(args.proposal, proposals_dir)


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

    # status
    st = sub.add_parser("status", help="Report node status")
    st.add_argument("--records-dir", default=None, help="Override records directory")
    st.add_argument("--config", default=None, help="Override config path")

    # review
    rv = sub.add_parser("review", help="Review a Gate 3 proposal")
    rv.add_argument("--proposal", required=True, help="Proposal ID to review")
    rv.add_argument("--proposals-dir", default=None, help="Override proposals directory")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "record": cmd_record,
        "status": cmd_status,
        "review": cmd_review,
    }
    sys.exit(handlers[args.command](args))
