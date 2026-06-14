# Keybindings — Architecture Diagrams

Component & data-flow diagrams for the **improved-keybindings** initiative: one map of the system
as it exists today, and one **proposed delta per build phase** toward the
[end goals](../end-goals.md).

## Charts

| Chart | Scope |
|---|---|
| [`current-state.md`](current-state.md) | The keybindings subsystem **as it is on `master`** (`d7ecfac5`) — engine, config load, settings UI, modal. The baseline every proposal builds on. |
| [`proposal-phase1-quickwins.md`](proposal-phase1-quickwins.md) | **Phase 1 — quick wins** (Axis 1 + Axis 5 slice): hot-reload over the flat map, action catalog v1, name search, chord capture, validators. No schema/engine change. |
| [`proposal-phase2-engine-core.md`](proposal-phase2-engine-core.md) | **Phase 2 — engine core** (Axes 2 + 3 + 5): name+context overrides, `ContextPredicate` parser, `(layer, recency)` precedence, real `Unbound`, context-aware conflicts. |
| [`proposal-phase3-modal.md`](proposal-phase3-modal.md) | **Phase 3 — modal** (Axis 4): `editing_mode` enum, pluggable `ModalEngine` + `EditorCommand` IR, the two `VimHandler` impls collapsed into one `ModalEditExecutor`, Helix as the proof. |

The phase split follows the [end-goals dependency spine](../end-goals.md#dependency-spine):
Phase 1 is independently shippable; Phase 2 is the engine prerequisite that makes Phase 3's
per-mode bindings editable; Phase 3 is the highest-risk modal work.

**Delta key (proposal charts):** 🟩 `new` — added this phase · 🟧 `changed` — reworked ·
🟥 `removed` — papercut deleted · ⬜ `base` — unchanged, shown for context ·
⬛ `stretch` — optional / foundation. Colours are applied via mermaid `classDef`.

## How these were produced

Two adversarial multi-agent workflows, authored as senior-software-architect agent panels:

1. **`keybindings-current-state-chart`** (23 agents) — 7 architects each extracted one subsystem
   slice **read only from a pinned `origin/master` worktree** (so unmerged spike code on this
   branch could not contaminate the baseline); **2 independent red-teamers re-verified every node,
   edge, and claim against master code**; a lead architect synthesized confirmed-only elements into
   one flowchart; a mermaid validator passed it.
2. **`keybindings-proposal-charts`** (15 agents) — per phase: one architect designed the delta
   **grounded in the team's `✅ recommended` decisions** (the per-axis `decision-brief.md` +
   `spike-results/`); a **grounding skeptic** cut any node adopting a rejected option or inventing a
   component (e.g. editable per-mode keymaps in Phase 3, which `A4-Q1` explicitly cut); a
   **feasibility skeptic** re-read master to confirm each changed construct is real; the synthesizer
   dropped/flagged the rest; a mermaid validator passed each chart.

Every chart ends with an **adversarial-review section** recording what was dropped, corrected, or
flagged — the edits are auditable, not asserted.

## Caveats

- The proposal charts render the **recommended options** in the decision-briefs as of 2026-06-14.
  They are *design intent*, not committed implementation — open questions in each brief
  (`_Residual risk_`, `_What would settle it_`) still apply.
- `current-state.md` is pinned to `master` @ `d7ecfac5`; re-verify against `master` before relying
  on specific line numbers, as the subsystem is under active change on feature branches.

## Regenerating

Both workflows are re-runnable scripts (one architect/adversary panel per run). Re-run the
current-state workflow first (it produces the verified baseline the proposals consume), then the
proposals workflow with that baseline as input.
