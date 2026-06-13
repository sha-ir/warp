# Improved Keybindings — Code-Investigation Answers (adversarially verified)

**Date:** 2026-06-13
**Status:** Phase-1 answers to the 63 `code-investigation` design-readiness questions
**Companion to:** [`2026-06-13-improved-keybindings-design-readiness-questions.md`](../2026-06-13-improved-keybindings-design-readiness-questions/README.md) (the questions) and [`.understand-anything/keybindings-architecture-report.md`](../../../.understand-anything/keybindings-architecture-report.md)

## Method

Each question was answered by a hybrid investigator using the `/understand-chat` knowledge-graph method (grep the graph, follow edges/layers, cite code) **plus** direct reads of `app/` — which the graph does not cover (it spans only `warpui_core`, `editor`, `vim`). Every answer was then handed to an independent **adversarial verifier** that re-opened the cited code and tried to refute it, producing a verdict:

- **CONFIRMED** — the answer held under independent code re-check.
- **CORRECTED** — mostly right; the verifier fixed specifics (line refs, scope, counts).
- **REFUTED** — materially wrong; the final answer is the verifier’s.
- **UNVERIFIABLE** — could not be confirmed from code alone.

Confidence is the verifier’s final call. `residual_unknowns` flags any decision/product residue that code cannot settle (those route back to the question doc’s `user-product-decision` / `cross-team-decision` / `prototype-spike` items).

## Summary

- Questions answered + verified: **63 / 63**
- Verdicts: **49** confirmed · **14** corrected
- Final confidence: **63** high

---

## Contents

- [Axis 1 — Config as portable, live data](./axis-1-config-portable-live-data.md)
- [Axis 2 — Scope & context control](./axis-2-scope-and-context-control.md)
- [Axis 3 — Layering, precedence & unbinding](./axis-3-layering-precedence-unbinding.md)
- [Axis 4 — Modality as a first-class, pluggable choice](./axis-4-modality-pluggable.md)
- [Axis 5 — Discoverability & truthful conflicts](./axis-5-discoverability-and-conflicts.md)
- [Axis 6 — Cross-cutting foundation](./axis-6-cross-cutting-foundation.md)
- [Cross-axis / sequencing](./cross-axis-sequencing.md)
