        # eval-cal-node - Compiled System Reference

        **Designation:** ECN
        **Document role:** Canonical compiled technical reference for eval-cal-node
        **Source:** `doc/system/`
        **Build command:** `bash doc/system/BUILD.sh`
        **Document version:** 2.0 (2026-06-22) - canonical compliance migration
        **Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

        > **Generated artifact warning:** `doc/ECNSYSTEM.md` is assembled output. Edit
        > the source modules under `doc/system/` and rebuild. Hand edits to the
        > compiled artifact are overwritten by the next build.

        Assembly contract:

        - Command: `bash doc/system/BUILD.sh`
        - Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
        - Primary output: `doc/ECNSYSTEM.md`

        This `doc/system/` tree is the canonical source of truth for eval-cal-node. It uses
        explicit **truth classes**: canonical facts define repo role, authority
        boundaries, contract behavior, runtime behavior, and verification doctrine;
        snapshot facts are dated, audit-derived counts and current implementation
        inventory that may drift between audits.

        | Part | File | Contents |
        | --- | --- | --- |
        | §1 | `00_overview/00-overview.md` | 00 — Overview |
| §2 | `00_overview/01-architecture.md` | 01 — Architecture |
| §3 | `10_service-contract/10-service-contract.md` | 10 — Service Contract |
| §4 | `20_runtime/20-runtime.md` | 20 — Runtime |
| §5 | `30_dependencies/30-dependencies.md` | 30 — Dependencies |
| §6 | `40_governance/40-governance.md` | 40 — Governance |
| §7 | `50_operations/50-operations.md` | 50 — Operations |
| §8 | `99_appendices/90-appendices.md` | 90 — Appendices |

        ## Quick Assembly

        ```bash
        bash doc/system/BUILD.sh
        ```
