# Eval Cal Node

Post-implementation calibration node for the Forge Ecosystem.

## Documentation Contract

- **Repo type:** Standalone CLI subsystem
- **Authority boundary:** Post-implementation calibration analysis and proposal emission; does not alter approved Eval parameter revisions directly
- **Deep reference:** `config/cal_node_config.json`, `../../docs/canonical/ecosystem_canonical.md`
- **README role:** CLI entrypoint overview
- **Truth note:** Calibration proposals are candidates only; no proposal becomes part of an approved Eval parameter revision without explicit Gate 3 human approval

## What it does

Eval Cal Node studies the gap between what `forge-eval` verified, what SYSTEM.md declared as implemented reality, and what reconciliation found actually drifted or aligned. It produces bounded, reviewable calibration proposals for Eval parameters.

## Hard rules

- Does not change Eval stage order, artifact contracts, or fail-closed doctrine
- Does not directly rewrite the current approved Eval parameter revision
- Only emits candidate proposals
- Deterministic outputs for fixed dataset + config + node revision
- All proposals versioned, evidence-backed, auditable

## Three-gate autonomy model

- **Gate 1 (Sufficiency):** Autonomous. Rejects weak/noisy/incomplete proposals.
- **Gate 2 (Control Envelope):** Autonomous. Rejects policy-violating proposals.
- **Gate 3 (Math-Effect Boundary):** Human approval required. The only mandatory approval boundary.

## Install

```bash
pip install -e .
```

## Commands

```bash
# Ingest a calibration record
eval-cal-node record --input <record.json> [--backfill]

# Check node status
eval-cal-node status

# Review a Gate 3 proposal
eval-cal-node review --proposal <proposal_id>
```

## Allowed calibration targets (v0)

13 parameters: hazard weights, merge thresholds, occupancy priors. See `config/cal_node_config.json` for bounds.

## Status

Eval Cal Node v0 — initial implementation.
