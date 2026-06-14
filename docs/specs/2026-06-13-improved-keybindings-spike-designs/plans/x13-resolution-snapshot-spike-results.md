[← Back to Spike Designs index](../README.md) · [Plan: X13 resolution snapshot](./x13-resolution-snapshot-plan.md)

# X13 — Resolution-snapshot freeze · spike results

**Question.** Can we freeze an irreversible `(context, trigger, OS) → winning action` golden through the **real** matcher — before any `bindings()` reorder — cheaply enough to be worth doing now, and does the resulting net actually catch a winner change?

**Verdict.** ✅ **SUCCESS, and cheaper than the brief assumed.** A full-coverage golden (452 winner rows, all 40 production inits, 12 curated contexts) was captured headless in **<0.11 s with zero singleton panic-chase**. It re-runs deterministically and a deliberately perturbed winner makes the diff test go **RED**. The net is real.

**Branch.** `worktree-spike-x13-resolution-snapshot` (off `origin/master`; code-identical to `sha-ir/keybindings-draft` for `crates/`+`app/`). Build is **keepable** (it is the regression net), not throwaway.

---

## Decoupling correction (the premise that sent us here)

The run portfolio (`README.md:58-59`) said *"A3-Q20 needs X13 capture first — regression-net gate."* **That is a mislabel.** A3-Q20 is the perf/trie microbench; it produces no winner table to diff. The X13 golden's real consumers are **A3-Q17** (snapshot harness), **A3-Q16** (golden fixtures), and **A3-Q4** (the layer-store refactor that reorders `bindings()`). X13 and A3-Q20 are **independent**. We did X13 first only because it is the *irreversible* piece and the pre-reorder window is open — not because it gates the bench. *(Grounded by workflow `wcim8qp1p`, area "X13 capture recipe".)*

---

## Adversarial stance — the false-greens defended against

1. **Config-relative matcher reads as absolute.** The same matcher differs by OS / channel / feature-flag / cargo-feature. Defense: the golden header **records** the capture config (`os = linux`, coverage string); the OS is in the filename (`resolution_table.linux.txt`).
2. **A synthetic `Vec<FixedBinding>` capture that never boots the real registration tree.** Defense: capture drives the **production assembly** — `view::tests::initialize_app` (89 mock singletons + `workspace::init` cascade + `experiments::init`) **plus the real `lib.rs:1649-1693` init list**, replayed verbatim from a crate-root helper so every `module::init` path resolves exactly as production.
3. **Nondeterministic golden that flaps.** Defense: `Context.set`/`map` (HashSet/HashMap) are sorted into a `BTreeMap` keyed by trigger, rows are `sort()`ed; the winner cell uses the editable **name** (stable) or fixed **action Debug** (verified stable across two runs). The volatile per-run `BindingId` is **excluded**.
4. **A golden that can't fail (theater).** Defense: a perturbed winner was injected and the diff went RED, naming the exact line, before re-bless restored green.

---

## What was built (keep)

| File | Change | Keep rationale |
|---|---|---|
| `crates/warpui_core/src/core/app.rs` | `+11` — `#[cfg(feature="test-util")] AppContext::bindings_for_context_snapshot(Context) -> Vec<BindingLens>` | Mirrors the per-context half of `key_bindings_for_view` without a live window; the only new engine surface, test-gated. |
| `app/src/lib.rs` | `+56` — `#[cfg(test)] x13_register_keybinding_inits(ctx)` + a `mod` decl | Replays the production init block from the crate root so paths resolve as production; the load-bearing "boot the full matcher headless" primitive. |
| `app/src/keymap_resolution_snapshot_tests.rs` | new — the `#[ignore]` capture/diff test + 12 fixtures + BLESS rewrite | The harness A3-Q4/Q16/Q17 re-run; promotes to a CI gate later. |
| `app/test_data/keymap/resolution_table.linux.txt` | new — **452-row frozen golden** | The actual irreversible baseline. |

**Run / regenerate:**
```
# verify (diff vs golden):
cargo test -p warp -- --ignored --nocapture x13_resolution_snapshot
# regenerate (bless):
BLESS=1 cargo test -p warp -- --ignored --nocapture x13_resolution_snapshot
```

---

## Findings

### 🟢 Finding 1 — bootability is CHEAP in practice, not the brief's "MODERATE / ~½-day panic-chase"

The pre-build probe (`w2nddu90y`) rated full-coverage capture **MODERATE** — "call all 42 inits after wiring the *union* of mock singletons they need (~half-day, panic-by-panic plumbing)." **Refuted by the build:** layering the entire `lib.rs:1649-1693` init list on top of `view::tests::initialize_app`'s **existing 89 singletons** ran to completion on the **first try, zero added singletons, zero panics**, in 0.11 s. The 89 singletons the workspace harness already wires are a superset of what the other 38 top-level inits read. Net: a full headless keymap snapshot is a ~1-hour build, not ~half a day. *(This also de-risks A3-Q16/A3-Q17, which reuse the same harness.)*

### 🟢 Finding 2 — full coverage, all 12 contexts populated

452 winner rows; per-context: `code_editor_vim_normal` 97, `drive_index` 60, `workspace_multi_tab_pane_drag` 58, `terminal_block_selected` 38, `agent_input` 36, `terminal_alt_screen` 33, `terminal_long_running` 32, `flagged_terminal` 30, `terminal_idle_empty` 30, `richtext_notebook_editing` 19, `input_focused_ime_open` 17, `bare_root` 2. Editable winners carry stable names (`editable:editor_view:left`); fixed winners use action Debug (`fixed:VimBackspace`, `fixed:SelectAll`); Standard/Custom triggers are captured too (`Standard(Paste) → fixed:Paste`, `Custom(17) → editable:terminal:copy`).

### 🟢 Finding 3 — deterministic + the net bites

- Two consecutive diff runs both reported "snapshot matches golden (452 rows)" — **no flap**.
- Perturbing one winner cell produced `X13 resolution snapshot drifted … line 8`, test **FAILED**, then `BLESS=1` restored it and the re-verify is green. A winner change is caught.

---

## Residual risks / out of scope (carried, not silently dropped)

1. **Flattened-context approximation.** The live matcher resolves over a `Vec<Context>` chain (focused view → root, `app.rs:1767`) with cross-view precedence; each fixture flattens that chain into one `Context`. Consistent for *before/after* characterization (both sides captured identically) but can mask cross-view precedence effects. Faithful chain modeling is A3-Q17's job.
2. **Chord-blindness, but negligible here.** `bindings_for_context` records per-*completed*-trigger winners, not the pending/short-shadows-chord state. Production has **~1 real multi-key chord** (`cmdorctrl-r w`), and its completed trigger is captured like any other; the gap is the intermediate pending state only. A `push_keystroke` keystroke-space walk is deferred to the R2 boundary per the brief.
3. **Config-relative & Linux-only.** The golden reflects this build's OS + the test default flag/channel config (recorded in the header). `OperatingSystem::get()` is compile-time fixed, so a Mac golden needs a Mac runner (or the A6-Q14 OS-injection seam). Both deferred.
4. **Fixed-winner key = action Debug.** Stable across runs (verified) and sufficient for reorder-diffing, but an action whose `Debug` derivation changes for unrelated reasons would show as a (reviewable) diff. Editable winners use the stable `name`.
5. **Not yet a CI gate.** The test is `#[ignore]` (boots the full app). Promotion to a pre-merge gate is the reversible half of X13, deferred to the R2 boundary per the brief; a named owner must mandate it before A3-Q4 merges.

---

## Keep vs throw

- **KEEP (all of it):** the `bindings_for_context_snapshot` test-util accessor, the `x13_register_keybinding_inits` crate-root helper, the capture/diff harness, and the 452-row golden. This *is* the live-apply/resolution regression net for the whole engine axis.
- **Salvage note for production:** extract `x13_register_keybinding_inits` to sit beside the real init block so it cannot drift from `lib.rs:1649-1693` as inits are added/removed; promote the `#[ignore]` test to a CI gate at the R2 boundary; add a Mac golden when a Mac runner or the OS-injection seam exists.
- **THROW:** nothing. (The brief's feared "two-live-Matcher fallback" and per-axis-fixtures retreat were not needed — full capture worked.)

---

## Unblocks

- **A3-Q4** can now refactor `keymap.rs` to per-layer stores and diff the re-captured table against this frozen golden to prove no *unrelated* binding's winner moved.
- **A3-Q16/A3-Q17** reuse the same harness + fixtures (and inherit Finding 1: the boot is cheap).
- The irreversible Wave-1 gate the README demanded ("capture before any `bindings()` reorder") is **satisfied** for the Linux build.
