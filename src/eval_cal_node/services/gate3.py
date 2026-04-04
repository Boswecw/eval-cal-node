"""Gate 3 — Math-effect boundary (human approval required)."""

import json
import sys
from pathlib import Path


def _load_approval_request(proposal_id: str, proposals_dir: Path) -> dict | None:
    """Load the approval request artifact for a proposal."""
    path = proposals_dir / f"{proposal_id}_approval_request.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _load_gate_decision(proposal_id: str, proposals_dir: Path) -> dict | None:
    """Load the gate decision artifact for a proposal."""
    path = proposals_dir / f"{proposal_id}_gate_decision.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _write_review_result(
    proposal_id: str,
    decision: str,
    proposals_dir: Path,
    gate_decision: dict,
    record_count: int,
    recurrence_counts: dict[str, int],
    config: dict | None = None,
) -> None:
    """Write the review result to the proposals directory."""
    result = {
        "proposal_id": proposal_id,
        "decision": decision,
        "reviewed_at_record_count": record_count,
    }
    if decision == "declined" and config:
        result["hold_until_record_count"] = record_count + config.get("hold_after_decline_cycles", 3)
        result["hold_until_recurrence"] = {
            name: count + config.get("min_new_recurrence", 2)
            for name, count in recurrence_counts.items()
        }

    path = proposals_dir / f"{proposal_id}_review.json"
    with open(path, "w") as f:
        json.dump(result, f, sort_keys=True, separators=(",", ":"))


def review_proposal(
    proposal_id: str,
    proposals_dir: Path,
    *,
    response: str | None = None,
    config: dict | None = None,
) -> int:
    """Review a Gate 3 proposal. Interactive if response is None.

    Returns exit code (0 = success).
    """
    approval = _load_approval_request(proposal_id, proposals_dir)
    if approval is None:
        print(f"ERROR: No approval request found for proposal {proposal_id}", file=sys.stderr)
        return 1

    gate_decision = _load_gate_decision(proposal_id, proposals_dir)
    if gate_decision is None:
        print(f"ERROR: No gate decision found for proposal {proposal_id}", file=sys.stderr)
        return 1

    # Display summary
    print(f"\n=== Gate 3 Review: {proposal_id} ===\n")
    for req in approval.get("requests", []):
        print(f"Parameter: {req['param_name']}")
        print(f"  Current value:  {req['current_value']}")
        print(f"  Proposed value: {req['proposed_value']}")
        print(f"  Delta:          {req['bounded_delta']:+.6f}")
        print(f"  Bounds:         [{req['param_min']}, {req['param_max']}]")
        print(f"  Net direction:  {req['net_direction']:.6f}")
        print(f"  Evidence:       {req['n_total_implicated']} records, {req['recurrence_count']} repos")
        print(f"  Surfaces:       {', '.join(req['affected_surfaces'])}")
        print(f"  Recommendation: {req['recommendation']}")
        print()

    # Get response
    if response is None:
        try:
            response = input("Accept this proposal? [yes/no]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nReview cancelled.")
            return 1

    record_count = gate_decision.get("evaluated_at_record_count", 0)
    recurrence_counts = {}
    for req in approval.get("requests", []):
        recurrence_counts[req["param_name"]] = req.get("recurrence_count", 0)

    if response in ("yes", "y"):
        _write_review_result(proposal_id, "accepted", proposals_dir, gate_decision, record_count, recurrence_counts)
        print(f"ACCEPTED {proposal_id}")
        return 0
    elif response in ("no", "n"):
        _write_review_result(proposal_id, "declined", proposals_dir, gate_decision, record_count, recurrence_counts, config)
        print(f"DECLINED {proposal_id}")
        return 0
    else:
        print(f"ERROR: Invalid response '{response}'. Expected 'yes' or 'no'.", file=sys.stderr)
        return 1


def is_proposal_held(proposal_id: str, proposals_dir: Path, current_record_count: int, current_recurrences: dict[str, int]) -> bool:
    """Check if a declined proposal is still in hold period."""
    review_path = proposals_dir / f"{proposal_id}_review.json"
    if not review_path.exists():
        return False
    with open(review_path) as f:
        review = json.load(f)
    if review.get("decision") != "declined":
        return False

    # Check record count threshold
    if current_record_count < review.get("hold_until_record_count", 0):
        return True

    # Check recurrence thresholds
    for param_name, required in review.get("hold_until_recurrence", {}).items():
        if current_recurrences.get(param_name, 0) < required:
            return True

    return False
