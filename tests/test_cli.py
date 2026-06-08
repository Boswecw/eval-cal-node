"""Tests for the CLI workflow wiring (record -> propose -> review)."""

import json

from eval_cal_node import cli
from helpers import make_record


def _ingest(records_dir, param, n=8, repos=4):
    records_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        rec = make_record(
            repo=f"repo-{i % repos}",
            run_id=f"run-{i}",
            base_commit=f"b{i}",
            head_commit=f"h{i}",
            drift_found=True,
            drift_types=["false_block"],
            implicated_parameters=[param],
        )
        with open(records_dir / f"{rec['record_id']}.json", "w") as f:
            json.dump(rec, f)


def _run(argv):
    args = cli.build_parser().parse_args(argv)
    handler = {
        "record": cli.cmd_record,
        "propose": cli.cmd_propose,
        "status": cli.cmd_status,
        "report": cli.cmd_report,
        "review": cli.cmd_review,
    }[args.command]
    return handler(args)


def test_propose_insufficient_records(tmp_path, capsys):
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    rc = _run(["propose", "--records-dir", str(records_dir),
               "--proposals-dir", str(tmp_path / "proposals")])
    assert rc == 0
    assert "Not enough records" in capsys.readouterr().out


def test_propose_emits_artifacts(tmp_path, capsys):
    records_dir = tmp_path / "records"
    proposals_dir = tmp_path / "proposals"
    param = "hazard_blocking_threshold"
    _ingest(records_dir, param)

    rc = _run(["propose", "--records-dir", str(records_dir),
               "--proposals-dir", str(proposals_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PROPOSED" in out
    assert "Gate 3 review required" in out

    gd = list(proposals_dir.glob("*_gate_decision.json"))
    assert len(gd) == 1
    proposal_id = json.load(open(gd[0]))["proposal_id"]
    for suffix in ("proposal", "evidence", "param_delta", "approval_request"):
        assert (proposals_dir / f"{proposal_id}_{suffix}.json").exists(), suffix


def test_report_writes_summary(tmp_path, capsys):
    records_dir = tmp_path / "records"
    reports_dir = tmp_path / "reports"
    param = "hazard_blocking_threshold"
    _ingest(records_dir, param)

    rc = _run(["report", "--records-dir", str(records_dir),
               "--reports-dir", str(reports_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("REPORT ")
    written = list(reports_dir.glob("*_summary.md"))
    assert len(written) == 1
    assert "Eval Cal Node Summary" in written[0].read_text()


def test_review_rejects_path_traversal_id(tmp_path, capsys):
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    rc = _run(["review", "--proposal", "../../etc/passwd",
               "--proposals-dir", str(proposals_dir)])
    assert rc == 1
    assert "Invalid proposal id" in capsys.readouterr().err


def test_propose_then_review_decline_sets_hold(tmp_path, monkeypatch):
    """A CLI decline must compute hold-after-decline thresholds, which only
    happens when cmd_review passes config into review_proposal."""
    records_dir = tmp_path / "records"
    proposals_dir = tmp_path / "proposals"
    param = "hazard_blocking_threshold"
    _ingest(records_dir, param)

    _run(["propose", "--records-dir", str(records_dir),
          "--proposals-dir", str(proposals_dir)])
    proposal_id = json.load(
        open(list(proposals_dir.glob("*_gate_decision.json"))[0])
    )["proposal_id"]

    monkeypatch.setattr("builtins.input", lambda *a, **k: "no")
    rc = _run(["review", "--proposal", proposal_id, "--proposals-dir", str(proposals_dir)])
    assert rc == 0

    review = json.load(open(proposals_dir / f"{proposal_id}_review.json"))
    assert review["decision"] == "declined"
    # 8 records + hold_after_decline_cycles (3); 4 repos + min_new_recurrence (2).
    assert review["hold_until_record_count"] == 11
    assert review["hold_until_recurrence"][param] == 6
