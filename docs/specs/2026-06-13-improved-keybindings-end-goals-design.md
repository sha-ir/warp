# Improved Keybindings — Laddered End Goals

**Date:** 2026-06-13
**Status:** Approved (brainstorm output — goal decomposition, not a single implementation spec)
**Scope:** All three fronts — engine, settings UI, modal editing modes
**Optimized for:** Power users / config hackers
**Framing:** User-facing outcomes, organized by capability axis

## Context

This document decomposes the umbrella goal **"Improved keybindings"** into concrete,
user-facing end goals. It is the product of a brainstorming session and is grounded in the
adversarial architecture report at
[`.understand-anything/keybindings-architecture-report.md`](../../.understand-anything/keybindings-architecture-report.md)
(42 agents, 34/35 claims survived adversarial verification, 2026-06-12).

Each leaf goal is annotated with its report anchor (`R#` = recommendation, `L#` = engine
limitation, `G#` = UI gap, `Step X` = modal step) and a sequencing note tied to the report's
phased roadmap.

This is a **multi-project initiative**, not one spec. Each axis (or phase) below should get its
own brainstorm → spec → plan cycle rather than a single monolithic implementation plan.

### Key code anchors (from the report)

- **Engine:** `crates/warpui_core/src/keymap.rs` (`Keymap` = `fixed_bindings` + `editable_bindings`,
  `Trigger`, `Context`/`ContextPredicate`, linear first-match `Matcher`). Bindings are *code, not
  data*, registered imperatively at ~265 sites across ~109 files.
- **Config:** `app/src/keyboard.rs` — flat `keybindings.yaml` (`name → trigger`), loaded only at
  launch (`app/src/lib.rs:2557`); external edits need a restart, in-app edits apply live.
- **Settings UI:** `app/src/settings_view/keybindings.rs` (editor) +
  `app/src/resource_center/keybindings_page.rs` (read-only cheatsheet).
- **Modal:** `crates/vim` (pure FSA + reusable buffer algorithms) +
  `app/src/code/editor/view/vim_handler.rs`; gated by the boolean
  `text_editing.vim_mode_enabled` (`app/src/settings/editor.rs:202-210`).

## North Star

> A Warp power user can express their **entire keymap as portable, context-scoped data** —
> layering personal overrides over defaults, **truly unbinding** what they don't want, choosing
> their **modal scheme** — and trust that **what the UI shows is the truth**.

## The Capability Axes

### Axis 1 — Config as portable, live data

**End state:** the keymap is a hand-editable, shareable file that is the source of truth and
applies instantly.

- Edits to `keybindings.yaml` hot-reload with no restart — the current restart papercut is gone.
  *(R1; `app/src/user_config/native.rs` watcher) — Phase 1, independent*
- File schema is rich enough to express everything the GUI can — no capability gap between file
  and UI. *(R3b)*
- Export / import a keymap; drop in a colleague's config and it just works. *(R7)*
- Round-trip safe: file edits and in-app edits don't clobber each other; removed entries revert to
  default. *(R1 reset semantics — requires an "applied custom names" set)*

### Axis 2 — Scope & context control

**End state:** a power user binds a key differently per context (terminal vs code editor vs modal
submode) and the override hits *only* that scope.

- Overrides target **name + context**, not name-only — no more clobbering every same-name binding.
  *(L3, R3b; `keymap.rs:422`)*
- The config file expresses context predicates (`& | ! == !=`) parsed from text.
  *(R3a; `FromStr` for `ContextPredicate`) — Phase 2*
- New contexts/conditions are expressible from config, not Rust-only. *(L6)*

### Axis 3 — Layering, precedence & unbinding

**End state:** bindings resolve through explicit layers (default < user < mode-pack), and a user
can *truly disable* a default, not just shadow it.

- Explicit `(layer, recency)` precedence replaces the fixed-vs-editable LIFO.
  *(R2; `keymap.rs:454`) — Phase 2*
- A real `Unbound` state (not overloaded `Trigger::Empty`). *(R2)*
- Fixed bindings become auditable and, where appropriate, remappable — gated on first auditing how
  many user-facing shortcuts are actually Fixed. *(L9; open question §6 of the report)*
- Predictable chords: a short binding no longer silently shadows a longer chord sharing its prefix;
  explicit ambiguity policy / timeout. *(L5, R4)*

### Axis 4 — Modality as a first-class, pluggable choice

**End state:** vim / helix / kakoune are peer editing modes chosen by one setting, sharing one
engine and one executor.

- A single `editing_mode` enum setting replaces the `vim_mode` bool; surfaced as a dropdown.
  *(Step E)*
- Pluggable `ModalEngine` + mode-agnostic `EditorCommand` IR; **Helix (select-then-act) ships as
  the proof**. *(Steps A–D) — Phase 3*
- Per-mode keymaps are themselves scoped bindings the user can edit/override.
  *(depends on Axis 2 + Axis 3)*
- Modal modes reuse the generic buffer algorithms (text objects, word iterators, bracket matcher)
  as-is. *(`crates/vim`)*

### Axis 5 — Discoverability & truthful conflicts

**End state:** the user can find any bindable action, see its real binding + scope, and get honest,
actionable conflict feedback.

- Search by **action name / internal id**, not just description. *(G3, R7) — Phase 1*
- A real action catalog: `(id, description, group, context, default)`, including read-only fixed
  bindings. *(R9)*
- Context-aware conflict detection that **names the colliding action** and offers one-click
  rebind/swap; optional save-gate on hard conflicts. *(G1, R6) — Phase 2*
- Chord capture in the UI (multi-keystroke), not single-keystroke overwrite. *(G4, R8) — Phase 1*
- Validators (PTY-compliant, cross-platform) run on the edit path with inline warnings. *(R10)*

### Cross-cutting foundation (stretch)

- Platform-in-data-model so a single build can show/edit both mac and linux/windows bindings —
  prerequisite for a true cross-platform editor. *(R5; L7)* Kept as a stretch/foundation outcome:
  independent of the other axes, but a hard prerequisite for any cross-platform binding editor.

## Dependency Spine

- **Axes 1 & 5** are mostly Phase-1 quick wins — independently shippable, no schema/engine change.
- **Axes 2 & 3** are the engine core (Phase 2) and are the **prerequisite** that makes Axis 4's
  per-mode bindings actually editable.
- **Axis 4** is Phase 3 — highest risk, depends on the Phase-2 context model.

```
Phase 1 (quick wins) ──► Axis 1 (hot-reload, import/export)
                         Axis 5 (search-by-name, chord capture, validators, catalog v1)
                              │
                              ▼
Phase 2 (engine core) ──► Axis 2 (context-scoped overrides, predicate parser)
                          Axis 3 (layers, precedence, unbind, ambiguity policy)
                          Axis 5 (context-aware conflicts)
                              │
                              ▼
Phase 3 (modal) ───────► Axis 4 (ModalEngine, EditorCommand IR, Helix proof)
```

## Phase Cross-Reference (for build sequencing)

| Phase | Axes touched | Representative leaves |
|-------|--------------|------------------------|
| 1 — Quick wins | 1, 5 | Hot-reload YAML, search-by-name, chord capture, validators, action catalog v1, import/export |
| 2 — Engine core | 2, 3, 5 | Context-scoped overrides, `ContextPredicate` parser, binding layers + precedence, `Unbound` state, context-aware conflicts |
| 3 — Modal | 4 | `editing_mode` enum, `ModalEngine` trait, `EditorCommand` IR, Helix select-then-act proof |

## Open Questions (carry into per-axis specs)

- **Magnitude of `FixedBinding` usage** — audit how many user-facing shortcuts are actually Fixed
  before promising "make everything remappable." *(Axis 3)*
- **`ModelHandle<dyn ModalEngine>` feasibility** — report recommends an enum over `dyn`; verify
  against warpui `Entity`/`ModelHandle`. *(Axis 4)*
- **Trie correctness under context-dependent eligibility** — must rebuild/filter per active context
  and preserve `bindings()` precedence as tiebreaker. *(Axis 3)*
- **Hot-reload reset semantics** — reverting a removed entry to default needs a reliable
  "currently-applied custom names" set. *(Axis 1)*
- **Helix/Kakoune grammar depth** — multi-selection fit onto `ExtendSelection`/`ApplyOperator` is
  unproven beyond basic cases. *(Axis 4)*

## Next Step

Pick the first axis (recommended: **Axis 1 + the Phase-1 slice of Axis 5**, since they are
independently shippable and produce the action catalog that later phases depend on) and run it
through its own brainstorm → writing-plans cycle.
