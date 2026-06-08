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


def _propose_for_review(tmp_path):
    """Ingest + propose so a real gate3-ready proposal exists; return ids/dirs."""
    records_dir = tmp_path / "records"
    proposals_dir = tmp_path / "proposals"
    _ingest(records_dir, "hazard_blocking_threshold")
    _run(["propose", "--records-dir", str(records_dir),
          "--proposals-dir", str(proposals_dir)])
    proposal_id = json.load(
        open(list(proposals_dir.glob("*_gate_decision.json"))[0])
    )["proposal_id"]
    return proposal_id, proposals_dir


def _patch_lineage(monkeypatch, *, allowed):
    from eval_cal_node.lineage.gate3 import LineageGate3Decision

    def fake_check(**kwargs):
        return LineageGate3Decision(
            allowed=allowed,
            availability="lineage_available" if allowed else "lineage_missing",
            reason_class=None if allowed else "enforcement_unavailable",
            reason_message=None if allowed else "lineage could not be verified",
        )

    monkeypatch.setattr(
        "eval_cal_node.lineage.gate3.check_gate3_lineage", fake_check
    )


def test_review_fails_closed_when_lineage_unverified(tmp_path, monkeypatch, capsys):
    proposal_id, proposals_dir = _propose_for_review(tmp_path)
    _patch_lineage(monkeypatch, allowed=False)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "yes")

    rc = _run(["review", "--proposal", proposal_id, "--proposals-dir", str(proposals_dir),
               "--forge-eval-bundle-node-id", "node-bundle", "--record-node-id", "node-rec"])
    assert rc == 1
    assert "fail-closed" in capsys.readouterr().err
    # Must not have stamped an acceptance.
    assert not (proposals_dir / f"{proposal_id}_review.json").exists()


def test_review_proceeds_when_lineage_verified(tmp_path, monkeypatch, capsys):
    proposal_id, proposals_dir = _propose_for_review(tmp_path)
    _patch_lineage(monkeypatch, allowed=True)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "yes")

    rc = _run(["review", "--proposal", proposal_id, "--proposals-dir", str(proposals_dir),
               "--forge-eval-bundle-node-id", "node-bundle", "--record-node-id", "node-rec"])
    assert rc == 0
    assert "Lineage verified" in capsys.readouterr().out
    review = json.load(open(proposals_dir / f"{proposal_id}_review.json"))
    assert review["decision"] == "accepted"


def test_review_requires_both_lineage_ids(tmp_path, capsys):
    proposal_id, proposals_dir = _propose_for_review(tmp_path)
    rc = _run(["review", "--proposal", proposal_id, "--proposals-dir", str(proposals_dir),
               "--forge-eval-bundle-node-id", "node-bundle"])  # missing --record-node-id
    assert rc == 1
    assert "must be given together" in capsys.readouterr().err


def test_review_warns_when_lineage_not_supplied(tmp_path, monkeypatch, capsys):
    proposal_id, proposals_dir = _propose_for_review(tmp_path)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "yes")
    rc = _run(["review", "--proposal", proposal_id, "--proposals-dir", str(proposals_dir)])
    assert rc == 0
    assert "NOT verified" in capsys.readouterr().err


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
