# Improved Keybindings — Initiative

A multi-project initiative decomposing **"Improved keybindings"** across three fronts
(engine, settings UI, modal modes) into per-axis design work. Grounded in the adversarial
architecture report at
[`.understand-anything/keybindings-architecture-report.md`](../../../.understand-anything/keybindings-architecture-report.md)
(42 agents, 34/35 claims survived adversarial verification, 2026-06-12).

**Date:** 2026-06-13 · **Optimized for:** power users / config hackers.

**Start here:** [`end-goals.md`](end-goals.md) — the north-star laddered end goals.

## How this directory is organized

Navigate **by axis**: each `axis-*/` folder holds one capability axis's entire journey
through every phase, as one file per phase. `cross-axis-sequencing/` holds the cutting work
that spans all axes. Empirical spike outcomes live in `spike-results/`, keyed by spike ID
(they are cross-cutting, so they are not split per axis).

## Reading order

1. [`end-goals.md`](end-goals.md) — what we're building and why (initiative-wide north star).
2. **Readiness questions** (`*/readiness-questions.md`) — the questions that must be answered
   before a dev design doc can be written, per axis. Generated adversarially, each carries
   *why it matters / how to answer / who can answer*.
3. **Code answers** (`*/code-answers.md`) — adversarially-verified, code-grounded answers to the
   `code-investigation` questions (each CONFIRMED or CORRECTED under independent re-check).
4. **Decision briefs** (`*/decision-brief.md`) — the resulting design decisions for the non-code
   questions (named options, steelman + what-breaks, effort/reversibility; red-teamed —
   33 HARDENED · 5 FLIPPED).
5. **Spike designs** (`*/spike-design.md`) — throwaway-build designs that de-risk the empirical
   unknowns (quantified success/kill signals, false-green analysis).
6. [`spike-results/`](spike-results/README.md) — empirical outcomes, keyed by spike ID.

For the cross-cutting sequencing / spike run-portfolio across all axes, see
[`cross-axis-sequencing/spike-design.md`](cross-axis-sequencing/spike-design.md).

## Phase × axis matrix

Each row is one axis's whole journey; columns are the four per-axis phases.

| Axis | Readiness questions | Code answers | Decision brief | Spike design |
|------|---------------------|--------------|----------------|--------------|
| 1 · config-portable-live-data | [q](axis-1-config-portable-live-data/readiness-questions.md) | [a](axis-1-config-portable-live-data/code-answers.md) | [b](axis-1-config-portable-live-data/decision-brief.md) | [s](axis-1-config-portable-live-data/spike-design.md) |
| 2 · scope-and-context-control | [q](axis-2-scope-and-context-control/readiness-questions.md) | [a](axis-2-scope-and-context-control/code-answers.md) | [b](axis-2-scope-and-context-control/decision-brief.md) | [s](axis-2-scope-and-context-control/spike-design.md) |
| 3 · layering-precedence-unbinding | [q](axis-3-layering-precedence-unbinding/readiness-questions.md) | [a](axis-3-layering-precedence-unbinding/code-answers.md) | [b](axis-3-layering-precedence-unbinding/decision-brief.md) | [s](axis-3-layering-precedence-unbinding/spike-design.md) |
| 4 · modality-pluggable | [q](axis-4-modality-pluggable/readiness-questions.md) | [a](axis-4-modality-pluggable/code-answers.md) | [b](axis-4-modality-pluggable/decision-brief.md) | [s](axis-4-modality-pluggable/spike-design.md) |
| 5 · discoverability-and-conflicts | [q](axis-5-discoverability-and-conflicts/readiness-questions.md) | [a](axis-5-discoverability-and-conflicts/code-answers.md) | [b](axis-5-discoverability-and-conflicts/decision-brief.md) | [s](axis-5-discoverability-and-conflicts/spike-design.md) |
| 6 · cross-cutting-foundation | [q](axis-6-cross-cutting-foundation/readiness-questions.md) | [a](axis-6-cross-cutting-foundation/code-answers.md) | [b](axis-6-cross-cutting-foundation/decision-brief.md) | [s](axis-6-cross-cutting-foundation/spike-design.md) |
| cross-axis-sequencing | [q](cross-axis-sequencing/readiness-questions.md) | [a](cross-axis-sequencing/code-answers.md) | [b](cross-axis-sequencing/decision-brief.md) | [s](cross-axis-sequencing/spike-design.md) |

## Empirical results

Spike results are keyed by spike ID (cross-cutting), not by axis — see
[`spike-results/`](spike-results/README.md).
