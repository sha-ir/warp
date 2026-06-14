[← Back to Spike Designs index](../README.md)

# X13 — Resolution-snapshot freeze · execution plan

**Date:** 2026-06-13
**Status:** Plan, pending user approval before build
**Branch (to create):** `sha-ir/spike-x13-resolution-snapshot` (worktree under `.claude/worktrees/`)
**Spike kind:** Throwaway build that settles the *bootability* unknown and leaves a **keepable** frozen golden + diff harness.
**Companion docs:** [README run portfolio](../README.md) · [decision brief X13](../../2026-06-13-improved-keybindings-decision-briefs.md) (cross-axis-sequencing §X13, L254-290) · grounded by two verification workflows (`wcim8qp1p`, `w2nddu90y`).

---

## 1. Goal

Capture an **irreversible** frozen golden of `(context, trigger, OS) → winning action`, resolved through the **real** matcher, **before any `bindings()` reorder lands**. This is the regression net the Phase-2 engine refactors diff against — most directly **A3-Q4**, which reorders `bindings()` by `(layer, recency)` and can silently flip the winner for any of ~266 registrations. Once R2/A3-Q4 lands, the clean pre-refactor winner table can no longer be re-derived, so the capture window is open *now*.

## 2. Decoupling note (why this is its own branch)

Grounding refuted the README's "A3-Q20 needs X13 first — regression-net gate" line: **A3-Q20 is the perf/trie microbench and produces no winner table to diff** (the gate was a mislabel of A3-Q17). X13's real consumers are **A3-Q4 / A3-Q16 / A3-Q17**. X13 and A3-Q20 are therefore independent; we run X13 first purely because it is the *irreversible* piece and the window is open.

## 3. Grounded findings that shape the build

| Finding | Evidence | Consequence for the build |
|---|---|---|
| **Bootability = MODERATE** (not "cheap ~1d") | Central entrypoint `app/src/lib.rs:1649-1703` (~42 `module::init(ctx)`); headless `App::test` exists (`crates/warpui_core/src/core/app.rs:74-99`, no GUI/GPU/winit, used by 30+ test files); but full `initialize_app()` is fused to secure-storage/settings/network/SQLite/GPU and is **un-callable** in a test | Capture lives as a `#[cfg(test)]` helper **in the `app` crate**, modeled on `app/src/workspace/view_tests.rs::initialize_app` (already wires ~70 mock singletons + `experiments::init` + `workspace::init`). Reaching all ~266 bindings = call all 42 inits after wiring the *union* of mock singletons → **~half-day panic-by-panic plumbing**, slow first build |
| Capture entrypoint | `Matcher::bindings_for_context(context)` → first `BindingLens` per distinct registered `Trigger` = winner (`matcher.rs:282`) | Iterate registered triggers, project the first match per fixture. **Does not model chord/pending** |
| Only ~1 real multi-key chord | `cmdorctrl-r w` (`app/src/code/view.rs:116`, trivial predicate); all other space-separated triggers are tests | Seed that one chord row explicitly via `push_keystroke`; the chord-blindness gap is otherwise negligible |
| Winner cell stability | Actions are `Arc<dyn Action>`, `Debug`-only, no stable `BindingId`; `BindingLens.name` is the stable handle | Cell = editable `name` / fixed `action` Debug fallback; **prefer name/description** (action payloads can have nondeterministic Debug) |
| No snapshot framework anywhere | No insta/expect-test/.snap; repo convention = plain files under `<crate>/test_data/` + `#[test]` + `assert_eq!` | Plain deterministically-sorted **text** golden + `BLESS=1` env rewrite. **Zero new deps** (do not add insta) |
| Matcher is **config-relative** | ~34 flag-reading files, 94 `.with_enabled`, per-platform keystrokes, `#[cfg]`-gated inits | **Pin and record** OS + channel/debug + feature-flag + cargo-feature state in the golden header; a golden is one config variant |
| OS is compile-time fixed | `OperatingSystem::get()` cfg_if (`platform/mod.rs:668-683`); `new_per_platform` resolves-and-discards the inactive OS at registration (`keymap.rs:497`) | One golden **per build OS**. This build = **Linux**. Label it `resolution_table.linux.txt`; cross-OS needs a Mac runner or the A6-Q14 OS-injection seam (out of scope) |
| `Context` is `HashSet`/`HashMap` | `context.rs:3-7` | Sort set ids + map entries + table rows, or the golden flaps every run |

## 4. Deliverables

1. **Capture harness (throwaway):** `#[cfg(test)]` code in the `app` crate that stands up a headless `App::test`, wires mock singletons, runs the 42 inits, and dumps the resolution table.
2. **Golden artifact (keep):** `app/test_data/keymap/resolution_table.linux.txt` — deterministically sorted, with a config header recording OS / channel / flag set / cargo features / coverage.
3. **Diff test (keep — the actual regression net):** a `#[cfg(test)]` test that re-captures and asserts equality with the golden; `BLESS=1` rewrites it; on mismatch it prints a unified diff. This is what A3-Q4 will run post-refactor.
4. **Results doc (keep):** `plans/x13-resolution-snapshot-spike-results.md` — the bootability verdict, coverage achieved, keep-vs-throw, residual gaps.

## 5. Curated context fixtures (~10–12, flattened responder-chain unions)

Harvested from the real `id!()` vocabulary (top tags: IMEOpen 207, Workspace 168, EditorView 118, Terminal 110, RichTextEditorView 31, Input 24, Vim 20, PaneGroup 19, LongRunningCommand 14, …). Each built via `Context::default()` + `set.insert(...)` / `map.insert(...)`:

1. `terminal_idle_empty` — {Terminal, TerminalView_EmptyBlockList}
2. `terminal_long_running` — {Terminal, TerminalView_NonEmptyBlockList, LongRunningCommand} · map{BlockSelectionCardinality: None}
3. `terminal_alt_screen` — {Terminal, TerminalView_NonEmptyBlockList, AltScreen, ActiveAltScreenSelection}
4. `terminal_block_selected` — {Terminal, TerminalView_NonEmptyBlockList, ActiveBlockTextSelection} · map{BlockSelectionCardinality: One}
5. `input_focused_ime_open` — {Terminal, Input, EditorFocused, TerminalView_EmptyBlockList, **IMEOpen**} — the critical `!id!("IMEOpen")` suppression-path fixture
6. `agent_input` — {Terminal, Input, AIInput, VoltronActive, UniversalDeveloperInput}
7. `workspace_multi_tab_pane_drag` — {Workspace, Workspace_MultipleTabs, PaneGroup, PaneGroup_PaneDragging, PaneGroup_MultiplePanes}
8. `code_editor_vim_normal` — {EditorView, CodeEditorView, Vim, VimNormalMode, FindBarAvailable} — modal-mode branch (directly relevant to the vim/helix/kakoune initiative)
9. `richtext_notebook_editing` — {RichTextEditorView, NotebookView, NotebookEditing, EditorIsEditable, BlockInsertionMenu, HasCommandSelection}
10. `drive_index` — {Workspace, DriveIndex, WarpDrive_BelongsToTeam}
11. *(opt)* `flagged_terminal` — {Terminal, TerminalView_EmptyBlockList, Vim_Mode_Enabled, Notifications_Enabled, Copy_On_Select}
12. *(opt)* `bare_root` — `Context::default()` / {RootView} — unconditional `always!()` globals + no-view baseline

*Exact id strings verified against each module before freezing (a few are symbolic consts).*

## 6. Build strategy (incremental, time-boxed ~half-day)

1. **Pipeline proof first:** reuse `view_tests::initialize_app` to capture the **workspace-subtree** subset end-to-end (~10 lines) — proves dump → sort → serialize → diff works before investing in full coverage.
2. **Extend init-by-init:** add the remaining inits (terminal/editor/input/pane_group/ai/menu/…) in `lib.rs` order, chasing missing-singleton panics until all 42 run.
3. **Commit maximal coverage achieved.** If a particular init's singleton web explodes past the time-box, commit the maximal-coverage golden and **document the missing inits** in the header + results. Coverage is a labeled fact, never a silent truncation.

## 7. False-green guards (this spike's whole point)

- Seed the one real chord (`cmdorctrl-r w`) explicitly — `bindings_for_context` is chord-blind.
- **Pin + record** config; a config-relative matcher silently differs otherwise.
- Sort set ids / map entries / rows (HashSet/HashMap nondeterminism).
- Winner cell = `name`, not action Debug (payload nondeterminism).
- **Prove the net bites:** flip one binding deliberately and confirm the diff test goes red — a golden that can't fail is theater.
- Document the **flattened-Context approximation**: the live matcher resolves over a `Vec<Context>` chain (`app.rs:1767`) with cross-view precedence; a flattened single Context can mask chain-ordering effects. Acceptable for *before/after* characterization (both sides captured identically); flagged as residual, full chain modeling is A3-Q17's job.

## 8. Success / kill

- ✅ **Success:** a committed, deterministic golden that re-runs green twice (no flap); all 42 inits called **or** the gap documented; the ~10–12 fixtures + the 1 chord row present; the diff test demonstrably **fails** on a deliberate winner change.
- 🛑 **Kill / fallback:** if full headless assembly proves infeasible within the time-box (singleton plumbing explodes), fall back to the brief's pre-agreed option — commit the **workspace-subtree partial golden** + an in-process **two-live-Matcher** comparison under a flag — and document the coverage gap. Do **not** block on 100% coverage.

## 9. Out of scope (deferred per brief)

- The `push_keystroke` full keystroke-space **chord walk** (deferred to the R2 boundary).
- Wiring the diff as a **CI pre-merge gate** (reversible; build just-in-time at R2).
- **Cross-OS** goldens (need a Mac runner or the A6-Q14 OS-injection seam).
- A3-Q20 (separate branch, next).
