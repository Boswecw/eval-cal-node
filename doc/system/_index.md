# Eval Cal Node — System Documentation

**Document version:** 1.0 (bootstrap)
**Protocol:** Forge Documentation Protocol v1
**Documentation structure class:** `service`
**Designation (proposed):** `ECN`

This `doc/system/` tree is the canonical source of truth for Eval Cal Node.
Chapters are assembled into a designation-bound canonical artifact.

Assembly contract:

- Command: `bash doc/system/BUILD.sh`
- Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
- Primary output: `doc/ECNSYSTEM.md`

| Part | File | Contents |
| --- | --- | --- |
| §1 | `00-overview.md` | System identity, role, and authority boundary within the Forge ecosystem. |
| §2 | `01-architecture.md` | Calibration pipeline, the three-gate autonomy model, and lineage posture. |
| §3 | `10-service-contract.md` | CLI service contract: commands, inputs, outputs, and the proposal contract. |
| §4 | `20-runtime.md` | Runtime flow from record ingest through gated proposal emission. |
| §5 | `30-dependencies.md` | Upstream (forge-eval), downstream (DataForge-Local lineage), and config dependencies. |
| §6 | `40-governance.md` | Authority boundary, the three gates, hard rules, and Gate-3 human approval. |
| §7 | `50-operations.md` | Install, commands, configuration, determinism, and audit/artifacts. |
| §8 | `90-appendices.md` | Glossary, the allowed calibration targets, and cross-references. |
