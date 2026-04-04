"""Test helpers for Eval Cal Node tests."""

import hashlib


def make_record(
    *,
    repo: str = "test-repo",
    base_commit: str = "aaa111",
    head_commit: str = "bbb222",
    run_id: str = "run-001",
    eval_parameter_revision: str = "rev1",
    hazard_score: float = 0.4,
    hazard_tier: str = "guarded",
    merge_decision: str = "caution",
    reason_codes: list[str] | None = None,
    selected_hidden: float = 1.5,
    selected_method: str = "chao1",
    chao2_available: bool = True,
    mean_psi_post: float = 0.3,
    max_psi_post: float = 0.6,
    null_coverage_ratio: float = 0.1,
    k_eff: int = 3,
    defect_count: int = 5,
    reviewer_count: int = 3,
    declared_subsystems_updated: list[str] | None = None,
    declared_boundary_after: str = "Pack J implemented",
    drift_found: bool = True,
    drift_types: list[str] | None = None,
    severity: str = "minor",
    implicated_parameters: list[str] | None = None,
    disposition: str = "confirmed_drift",
    notes: str = "",
    record_version: str = "cal_record_v1",
    recorded_at_revision: str = "cal_node_rev1",
) -> dict:
    """Build a valid calibration record with sensible defaults."""
    raw = repo + base_commit + head_commit + run_id
    record_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    return {
        "record_id": record_id,
        "slice_ref": {
            "repo": repo,
            "base_commit": base_commit,
            "head_commit": head_commit,
            "run_id": run_id,
        },
        "eval_parameter_revision": eval_parameter_revision,
        "eval_signals": {
            "hazard_score": hazard_score,
            "hazard_tier": hazard_tier,
            "merge_decision": merge_decision,
            "reason_codes": reason_codes or [],
            "selected_hidden": selected_hidden,
            "selected_method": selected_method,
            "chao2_available": chao2_available,
            "mean_psi_post": mean_psi_post,
            "max_psi_post": max_psi_post,
            "null_coverage_ratio": null_coverage_ratio,
            "k_eff": k_eff,
            "defect_count": defect_count,
            "reviewer_count": reviewer_count,
        },
        "system_md_signals": {
            "declared_subsystems_updated": declared_subsystems_updated or [],
            "declared_boundary_after": declared_boundary_after,
        },
        "reconciliation_outcome": {
            "drift_found": drift_found,
            "drift_types": drift_types or [],
            "severity": severity,
            "implicated_parameters": implicated_parameters or [],
            "disposition": disposition,
            "notes": notes,
        },
        "record_version": record_version,
        "recorded_at_revision": recorded_at_revision,
    }
