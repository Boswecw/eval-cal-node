# 10 — Service Contract

Eval Cal Node exposes a single CLI entrypoint, `eval-cal-node`, installed via
`pip install -e .`.

## Commands

| Command | Purpose |
| --- | --- |
| `eval-cal-node record --input <record.json> [--backfill]` | Ingest a calibration record, run the pipeline, and emit any resulting candidate proposals. |
| `eval-cal-node status` | Report node status: revision, recent proposals, and gate posture. |
| `eval-cal-node review --proposal <proposal_id>` | Review a specific Gate-3 proposal awaiting human approval. |

## Inputs

- **Calibration record** — a JSON document conforming to the
  `cal_record_v1` schema (`src/eval_cal_node/schemas/`). Validated at ingest by
  `validation/validate_record.py`; invalid records are rejected fail-closed.
- **Node config** — `config/cal_node_config.json`, which declares the node
  revision, sufficiency thresholds, and the per-parameter bounds (`param_min`,
  `param_max`, `max_movement`, `allowed`).

## Outputs

- **Candidate calibration proposals** — versioned, evidence-backed proposals for
  one or more allowed Eval parameters. Each carries the signals that motivated
  it, the proposed bounded movement, and its gate decisions.
- **Gate decisions** — the Gate 1/2/3 outcome record for each proposal.
- **Lineage** — proposal and decision nodes emitted to DataForge-Local (best
  effort; see `30-dependencies.md`).

## Contract guarantees

- Proposals are **candidates only** — emission never mutates an approved Eval
  parameter revision.
- Outputs are **deterministic** for a fixed record set + config + node revision.
- Every proposal is **versioned and auditable**, with its evidence retained.
- Movement is **bounded** — no proposal can exceed a parameter's configured
  `max_movement` or step outside `[param_min, param_max]`.
