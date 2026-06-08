# 00 — Overview

## Identity

**Eval Cal Node** is the post-implementation **calibration node** for the Forge
ecosystem. It is a standalone CLI subsystem under
`ecosystem/local-systems/eval-cal-node`, independent of any sibling repo's
runtime.

## Role

Eval Cal Node studies the gap between three sources of truth:

1. what **forge-eval** verified for a target repo,
2. what that repo's `SYSTEM.md` declared as implemented reality, and
3. what reconciliation found actually **drifted** or **aligned**.

From that gap it produces bounded, reviewable **calibration proposals** for Eval
parameters — never silent parameter changes.

## Authority boundary

Eval Cal Node's authority is **proposal emission only**. It does **not** alter
the approved Eval parameter revision directly. Every proposed change is a
*candidate*; nothing becomes part of an approved revision without explicit
**Gate 3** human approval (see `40-governance.md`).

## What it is not

- Not an Eval stage — it does not change stage order, artifact contracts, or the
  fail-closed doctrine of forge-eval.
- Not a rewriter — it never directly rewrites the current approved Eval parameter
  revision.
- Not autonomous at the math boundary — the only mandatory approval gate (Gate 3)
  is human.

## Boundary diagram

```
forge-eval (verification)  ─┐
SYSTEM.md (declared truth) ─┼─▶  Eval Cal Node  ──▶  candidate calibration proposals
reconciliation (drift)     ─┘     (Gate 1/2 auto,        (Gate 3 = human approval)
                                   Gate 3 human)
```

Deep references: `config/cal_node_config.json`,
`../../docs/canonical/ecosystem_canonical.md`.
