from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from eval_cal_node.services.evaluation_spine_calibrator import calibrate_forge_eval_bundle_file_or_raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval_cal_node.evaluation_spine_cli",
        description="Emit an Evaluation Spine eval_calibration_report from a forge-eval evidence bundle contract payload.",
    )
    parser.add_argument(
        "--forge-eval-bundle",
        required=True,
        help="Path to forge_eval_evidence_bundle contract JSON emitted by forge-eval.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory where eval_calibration_report.contract.json will be written.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = calibrate_forge_eval_bundle_file_or_raise(
        Path(args.forge_eval_bundle),
        Path(args.out_dir),
    )
    summary = {key: value for key, value in result.items() if key != "payload"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
