# Improved Keybindings — Design-Readiness Questions (Adversarial)

**Date:** 2026-06-13
**Status:** Question-set (input to per-axis brainstorm -> spec -> plan cycles)
**Companion to:** [`2026-06-13-improved-keybindings-end-goals-design.md`](../2026-06-13-improved-keybindings-end-goals-design.md) and the architecture report at [`.understand-anything/keybindings-architecture-report.md`](../../../.understand-anything/keybindings-architecture-report.md)

## Purpose

For each capability axis, the **questions that must be answered before a dev design doc can be written**. These are not the design — they are the interrogation that de-risks it. Each was generated adversarially (attack the naive implementation), then critiqued (prune what the report/code already answers, sharpen the rest, add what a skeptic would catch). Every question carries _why it matters_, _how to answer it_, and _who/what can answer it_ (`code-investigation` = go read/measure; `user-product-decision` = a product call; `prototype-spike` = build a throwaway; `external-research` = study Helix/Kakoune etc.; `cross-team-decision` = needs another owner).

## How to use this

1. Take one axis (the end-goals doc recommends starting with **Axis 1 + the Phase-1 slice of Axis 5**).
2. Answer its **killer question** first — it gates the rest.
3. Walk the `code-investigation` questions (cheap, unblock facts), then force the `user-product-decision` / `prototype-spike` ones.
4. Carry the **cross-axis questions** into whichever axis you start, since they constrain the schema/abstraction choices that are expensive to reverse later.

---

## Contents

- [Initiative-wide — Cross-axis & sequencing questions](./initiative-wide-cross-axis.md)
- [Axis 1 — Config as portable, live data](./axis-1-config-portable-live-data.md)
- [Axis 2 — Scope & context control](./axis-2-scope-and-context-control.md)
- [Axis 3 — Layering, precedence & unbinding](./axis-3-layering-precedence-unbinding.md)
- [Axis 4 — Modality as a first-class, pluggable choice](./axis-4-modality-pluggable.md)
- [Axis 5 — Discoverability & truthful conflicts](./axis-5-discoverability-and-conflicts.md)
- [Axis 6 — Cross-cutting foundation](./axis-6-cross-cutting-foundation.md)

## Summary of effort

- Axes interrogated: **6/6**
- Per-axis design-readiness questions: **102**
- Cross-axis / sequencing questions: **13**
- Method: 6 adversarial generators -> 6 adversarial critics (prune/sharpen/fill) -> 1 cross-axis synthesis, all grounded in the architecture report + live code.
