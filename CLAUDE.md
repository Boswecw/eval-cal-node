# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Eval Cal Node is a standalone CLI subsystem within the Forge ecosystem (`ecosystem/local-systems`). It is a post-implementation calibration node: it studies drift between `forge-eval` verification results, declared SYSTEM.md reality, and reconciliation output, then emits bounded, reviewable calibration proposals for Eval parameters. It never silently changes parameters — proposals are candidates only.

## Common Commands

- Install: `pip install -e .`
- Run tests: `pytest` (testpaths = `tests`, configured in `pyproject.toml`)
- CLI entrypoint (installed as `eval-cal-node`):
  - `eval-cal-node record --input <record.json> [--backfill]` — ingest a calibration record
  - `eval-cal-node propose` — run Gate 1 + Gate 2 over ingested records and emit a proposal
  - `eval-cal-node status` — check node status
  - `eval-cal-node report` — write a markdown status summary to the reports directory
  - `eval-cal-node review --proposal <proposal_id>` — review a Gate 3 proposal

## Architecture

- `src/eval_cal_node/cli.py` — CLI entrypoint
- `src/eval_cal_node/config.py`, `src/eval_cal_node/data/cal_node_config.json` — calibration target definitions and bounds (v0 has 13 allowed parameters: hazard weights, merge thresholds, occupancy priors)
- `src/eval_cal_node/contracts/`, `src/eval_cal_node/schemas/` — data contracts and JSON schemas
- `src/eval_cal_node/services/`, `src/eval_cal_node/validation/` — core logic and validation
- `src/eval_cal_node/lineage/` — optional ForgeLineage Gate 3 transport checks (requires the `lineage` extra; `forge_lineage_sdk`/`forge_contract_core` are Forge-monorepo-only and resolved at runtime, not via pip)
- `docs/operator-guide.md` — full record -> propose -> review workflow and record format
- `examples/records/` — sample records ready to ingest

**Three-gate autonomy model:**
- Gate 1 (Sufficiency) — autonomous, rejects weak/noisy/incomplete proposals
- Gate 2 (Control Envelope) — autonomous, rejects policy-violating proposals
- Gate 3 (Math-Effect Boundary) — human approval required; the only mandatory approval boundary

## Notes

- This node does not change Eval stage order, artifact contracts, or fail-closed doctrine, and never directly rewrites the current approved Eval parameter revision — it only emits candidate proposals.
- Outputs must be deterministic for a fixed dataset + config + node revision. All proposals are versioned, evidence-backed, and auditable.
- Deep reference for the ecosystem this node lives in: `../../docs/canonical/ecosystem_canonical.md` (path relative to this repo's location within the Forge ecosystem checkout).
