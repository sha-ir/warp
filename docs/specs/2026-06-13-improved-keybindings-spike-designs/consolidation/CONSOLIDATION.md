# Keybindings Spikes — Consolidation Manifest

**Status:** UNSTAGED handoff. Nothing here is merged yet. Do NOT `git add` or commit this file.
**Target branch:** `sha-ir/keybindings-draft`
**Date:** 2026-06-14
**Scope:** Single source of truth for the merge agent. Land ONLY the KEEP production artifacts of the keybindings spikes; drop all plans and throwaway/cfg-gated spike code.

---

## 1. Purpose + Ground Rules

This manifest tells a downstream merge agent exactly **what production code to extract** from the per-spike branches into `sha-ir/keybindings-draft`, and what to **leave behind**.

**Ground rules (apply to every decision below):**

1. **KEEP production artifacts only.** A "KEEP" artifact is real production code (or a real regression test) that is wanted on `keybindings-draft` as-is or after minor de-spiking. If something only exists to measure or prove a spike, it is THROW.
2. **DROP all plans.** Every file under `../plans/*-plan.md`, the `*-spike-results.md` copies that ride along on branches, `adversarial-spike-workflows-design.md`, `adversarial-spike-workflows-rollup.md`, and `HANDOFF.md` are NOT merge payload. The canonical record we keep lives in `consolidation/results/` (see §8).
3. **DROP throwaway / cfg-gated spike code.** `layered_spike.rs`, `resolve_spike.rs`, `keymap_xplat_probe.rs`, the cfg-gated `Matcher` repoints, criterion benches (unless a regression guard is explicitly wanted), the full-app-boot population walks, and all `#[cfg(feature = "...spike...")]` modules do NOT merge. Their **designs and findings graduate as decisions** (§5, §7), not as code.
4. **This is an unstaged handoff.** Nothing is merged yet. The merge agent performs the lands in the recommended order (§6).
5. **The X13 gate must stay GREEN.** Land the X13 resolution-snapshot net ONCE and early; **re-diff after every engine change** (A3-Q4, X9). A green 452/452 is the proof that an engine reshape did not silently move any binding's winner.
6. **Exactly ONE engine refactor lands.** A3-Q4's `LayerStore` is canonical; X1's `LayeredKeymap` graduates as design only (§5).

---

## 2. Current State

| Item | State |
| --- | --- |
| Main tree `sha-ir/keybindings-draft` | Clean. Only untracked: `.claude/workflows/`, `consolidation/` (this dir), `plans/HANDOFF.md`. No spike code is on this branch. |
| All spike code | Isolated on per-spike branches / worktrees (enumerated in §3). |
| Results docs | Gathered (unstaged) in `consolidation/results/` — 11 docs (§8). |
| Committed plans | `../plans/*.md` are tracked on this branch and are to be DROPPED from the consolidation. |
| X13 golden baseline | Linux-only, default-layer-only, config-relative; established GREEN at 452 rows. |

---

## 3. KEEP-Artifact Extraction Table

Grouped by target crate. "PR?" = production-ready (✅) or needs de-spiking (🛠). Source is `branch @ commit`.

### 3a. `crates/warpui_core` — keymap engine (the conflict-prone core)

| Unit | Source | File | Symbols / Hunks | PR? | Why keep |
| --- | --- | --- | --- | --- | --- |
| **X7 leaf-Cow** | `sha-ir/spike-x7-leaf-cow @ 7cb3a0b0` | `crates/warpui_core/src/keymap/context.rs` | FOUR coordinated edits in this one file: (1) add `use std::borrow::Cow;`; (2) 3 leaf variants of `enum ContextPredicate` → `Cow<'static, str>` (`Identifier`, `Equal`, `NotEqual`); non-leaf variants unchanged; (3) `id!`/`eq!`/`ne!` macro bodies wrap args in `.into()`, PLUS new `($a:expr,$b:expr)` arms on `eq!`/`ne!`; (4) the 3 leaf `eval` arms deref via `&**`. Net ~+19/-12 in a 131-line file. | ✅ | Load-bearing shared prerequisite. X6/X9 (predicate construction) and A2-Q6 (config-authored runtime atoms) consume owned/expr atoms. `cargo check -p warpui_core --lib` = EXIT 0 (forced recompile verified). Every `.into()` at today's `&'static str` call sites is a free `Cow::Borrowed` (zero heap alloc). Land **first** so downstream units build on the new leaf type. **Doc note:** the branch is GREEN, not RED — the results doc's "committed deliverable is RED / needs `.as_ref()` follow-up" prose is STALE; the `&**` fix is already in-file. |
| **A3-Q4 LayerStore** (CANONICAL engine) | `worktree-spike-a3-q4-layered-store @ f5f638fd` | `crates/warpui_core/src/keymap.rs` | NEW `struct LayerStore { fixed, editable: Vec<Tracked<EditableBinding>>, editable_by_name }` + impl (`register_fixed`, `register_editable`, `editable_bindings()`, `fixed_bindings()`, `update_custom_trigger`, `get_binding_by_name`). REWRITTEN `struct Keymap { default_layer, user_layer, modepack_layer: LayerStore }`. `layers_high_to_low() -> [&LayerStore;3]`. `bindings()` chains **all-editable-across-layers THEN all-fixed-across-layers** (within-split layering). `custom_action_bindings()` = DERIVED filter of `bindings()` (Option A). DELETES the 4 flat collections + `editable_custom_action_bindings()` helper. ~205 lines changed (~120 net new). | ✅ | THE production engine refactor. Variant (b) per-layer-chained store; within-split precedence preserved (X13 452/452 byte-identical); Option-A derived projection FIXES a latent override→Custom shadow desync and deletes the hand-maintained dual-write surface. Single `Tracked` per binding preserves live-apply identity. **Un-gated, matcher.rs untouched.** Note: `modepack_layer`/`user_layer` are forward-looking Axis-4 scaffolding (empty in prod today). |
| **A3-Q4 tests** | `worktree-spike-a3-q4-layered-store @ f5f638fd` | `crates/warpui_core/src/keymap_tests.rs` | Two new `#[test]` fns appended after L527: `a3q4_shadow_coherence_derived` and `a3q4_ordering_editable_beats_fixed_across_layers`. (+74) | ✅ | Regression net the axis lacked: guards the Custom-trigger shadow surface and the within-split editable-beats-fixed ordering trap (whole-layer chaining would let a user-layer fixed binding beat a default-layer editable one). |
| **A3-Q4 identity test** | `worktree-spike-a3-q4-layered-store @ f5f638fd` | `crates/warpui_core/src/core/autotracking/autotracking_tests.rs` | NEW `a3q4_live_apply_invalidation_identity` after L289 + supporting `BindingView` entity/View/TypedActionView impls. (+81) | ✅ | A3-Q7 identity witness: render counter == 2 proves the override stays on one `TrackedId` (read-edge + edit-edge hit the same instance). A split base/override design would leave count at 1; this catches that regression. |
| **X9 tombstone kernel** (COMPOSE onto A3-Q4) | `sha-ir/spike-x1-layeredkeymap @ 6391c43f` (linear stack) | `crates/warpui_core/src/keymap.rs` | Tombstone FIELDS: `tombstone:bool` on `BindingLens`/`EditableBinding`/`EditableBindingLens`; `BindingLens::is_tombstone()`; `EditableBinding::as_tombstone()`; propagation (`FixedBinding::as_lens`=false, `EditableBinding::new`=false, `EditableBinding::as_lens`, `EditableBindingLens::as_binding`). READER-consistency: fold `.rev()` (latest-wins) into `LayerStore::get_binding_by_name`; re-express `inject_binding` to write `user_layer` via `register_editable`. ~45 lines. | 🛠 | Genuine engine novelty: first-class suppress-and-short-circuit a pure-LIFO store cannot produce. Dormant in prod (no non-test `as_tombstone` callers). **De-spike:** strip "X9 spike" doc wording; **re-express `inject_binding` against `user_layer`** (X9's version writes the flat fields A3-Q4 deleted); **DROP X9's `editable_custom_action_bindings` dual-append** — A3-Q4's derived projection makes it obsolete. |
| **X9 matcher kernel** | `sha-ir/spike-x1-layeredkeymap @ 6391c43f` | `crates/warpui_core/src/keymap/matcher.rs` | `MatchResult::Unbound` variant; `Matcher::resolve_matched_binding` single shared short-circuit helper + its 4 call sites (`push_keystroke`, `match_standard`, `match_custom` primary + `original_trigger` dual-check); the second-surface `.filter(|b| !b.is_tombstone())` in `binding_for_custom_action_in_context`; `Matcher::inject_binding` wrapper. ~45 of the 82-line diff. | 🛠 | Unifies the tombstone decision across all 3 primary `MatchResult` paths via ONE helper; macOS-menu second surface keeps its own `Option`-shaped filter by type necessity (X9 partial-kill, intentional). Mutation-tested. **De-spike:** DROP the entire cfg(`layered_spike`) `BackingKeymap` repoint (lines 11, 18-22, 27, 79, 95) — that is X1's throwaway store. |
| **X9 tests** | `sha-ir/spike-x1-layeredkeymap @ 6391c43f` | `crates/warpui_core/src/keymap/matcher_tests.rs` | ONLY the X9-appended block, lines 227-488 (pure append; top 226 lines already on draft): helpers `assert_unbound`/`assert_is_action`/`expect_action`; the 4 tombstone tests; `test_inject_override_consistency_gate`. (~262) | ✅ | The real keepable "golden matcher_tests" for the stack — extends the actual production test file and is the acceptance suite for the X9 kernel. (The X6 `ported_test_*` golden ports live inside throwaway `resolve_spike.rs` — those are THROW.) |
| **A5-Q5 overlap oracle** | `sha-ir/spike-a5-q5-conflicts @ 9584cbba` | `crates/warpui_core/src/keymap/overlap.rs` | ENTIRE new file (239 lines): `struct AtomSet { ids: BTreeSet<&'static str>, map_values: BTreeMap<...> }` + `collect`/`add`/`union_with`/`atom_count`; `fn atoms(pred)`; `fn can_both_be_true(a,b)` (atom-enumeration oracle, reuses `ContextPredicate::eval`); `MAX_ATOMS=20`; `MAX_ASSIGNMENTS=1<<21`; `OVERFLOW_COUNT` + `overlap_overflow_count()`; `#[cfg(test)] reset_overlap_overflow_count()`; trailing `#[cfg(test)] #[path="overlap_tests.rs"] mod tests`. | ✅ | THE sound+complete logical-overlap conflict primitive (100% agreement vs brute-force over 100k pairs). Models map-key exclusivity and the NotEqual=Not(Equal) absent-true asymmetry. **No feature gate, no unsafe, no SAT crate.** |
| **A5-Q5 oracle tests** | `sha-ir/spike-a5-q5-conflicts @ 9584cbba` | `crates/warpui_core/src/keymap/overlap_tests.rs` | ENTIRE new file (340 lines): independent brute-force oracle + random generator + the 100k-pair differential property test + 8 adversarial unit tests. Uses `rand` (already a `[dependencies]` entry — no Cargo change). | ✅ | Permanent regression suite. The differential oracle is structurally independent (recursion + separate OTHER/absent sentinels vs production's iterative collapse), so it proves soundness rather than re-asserting it. Mutation-tested non-vacuous. |
| **A5-Q5 wiring** | `sha-ir/spike-a5-q5-conflicts @ 9584cbba` | `crates/warpui_core/src/keymap.rs` | Two additive hunks (~15 lines): (1) `pub mod overlap;` + `pub use overlap::{atoms, can_both_be_true, overlap_overflow_count, AtomSet};` in the module/re-export block; (2) new `impl<'a> BindingLens<'a> { pub fn context_predicate(&self) -> &ContextPredicate { self.context_predicate } }`. | ✅ | Minimal plumbing to expose the module and read each binding's gating predicate (the `BindingLens.context_predicate` field is private). Land LAST so it rebases onto the post-A3-Q4+X9 module block. **SEMANTIC reconcile with X7:** `AtomSet` is built on `&'static str` leaves — if X7's Cow leaves land first (they do), PORT `AtomSet` to the Cow leaf type and PRESERVE `context.rs`'s NotEqual-on-absent `unwrap_or(true)` (the oracle's soundness proof depends on it). |

### 3b. `crates/editor` — selection model (fully isolated, no keymap contention)

| Unit | Source | File | Symbols / Hunks | PR? | Why keep |
| --- | --- | --- | --- | --- | --- |
| **A4-Q16 HashSet fix** | `sha-ir/spike-a4-q16-multiselection @ b856d43d` (isolated commit; branch tip 7dd68a99, merge-base d5b2a4cf) | `crates/editor/src/content/selection_model.rs` | Inside `fn merge_overlapping_selections` (branch L165-203): add `use std::collections::HashSet;` (L1); insert `let overlap_indices: HashSet<usize> = overlap_indices.into_iter().collect();` (L178) + its 4-line comment (L174-177), immediately AFTER the `if overlap_indices.is_empty() { return; }` early-return. The two pre-existing `.contains(...)` call sites are unchanged. 6 net lines (commit = 7 insertions). **DO NOT pull `anchor_count` (L66-75 / L73).** | ✅ | Mandatory production correctness/perf insurance. Dense chained-N regime is reachable from real Helix `%` + `s\w+<CR>` + extend; without it the path is O(N²). Spike proved dense p50 scales ~linearly. Cleanest land: cherry-pick commit `b856d43d` (auto-excludes the throwaway `anchor_count` probe). Lands independent of the cap decision. |

### 3c. `app` crate + `core/app.rs` — the X13 regression net (LAND ONCE, from the canonical source)

Canonical source: `worktree-spike-x13-resolution-snapshot @ 2899121c` (payload = exactly 4 files / +770, all KEEP). The a3-q4/x1/x9/x6 branches each carry a **cherry-picked duplicate** of these 4 paths — do NOT re-add from them.

| File | Symbols / Hunks | PR? | Why keep |
| --- | --- | --- | --- |
| `crates/warpui_core/src/core/app.rs` | The single +11 hunk after `AppContext::get_bindings` (~L1707): `#[cfg(feature = "test-util")] pub fn bindings_for_context_snapshot(&self, context: Context) -> Vec<BindingLens<'_>>` (body wraps the existing `Matcher::bindings_for_context`). | ✅ | Load-bearing capture entrypoint: headless per-context resolution mirroring the per-context half of `key_bindings_for_view`. `test-util` already a feature (`warpui_core/Cargo.toml:19`); calls the EXISTING matcher fn (unchanged). |
| `app/src/lib.rs` | (1) `#[cfg(test)] mod keymap_resolution_snapshot_tests;`; (2) `#[cfg(test)] pub(crate) fn x13_register_keybinding_inits(ctx)` replaying the production keybinding-init block headless (excludes `workspace::init`). (+56) | 🛠 | "Boot the full matcher headless" primitive. **De-spike:** it is a hand-copied DUPLICATE of the real init list at `lib.rs:1649-1693` and will drift — extract it to sit beside the real init block (single source of truth). Functionally correct today. |
| `app/src/keymap_resolution_snapshot_tests.rs` | ENTIRE new 244-line file: `#[test] #[ignore] fn x13_resolution_snapshot()` (BLESS/diff harness), the 12-entry `FIXTURES`, `Fixture` struct, `build_context`, `fmt_*`, `golden_path`, `print_diff`. **STRIP the two `#[cfg(feature="layered_spike")]` routing-proof blocks (~L196-197, L225-228).** | 🛠 | The capture/diff harness A3-Q4/A3-Q16/A3-Q17 diff against; verified to bite. **De-spike:** reword the module doc's "throwaway spike harness" → "permanent resolution-snapshot regression net"; an owner must promote the `#[ignore]` test to a pre-merge CI gate before any A3-Q4-class reorder. Known gap: flattened-context approximation (faithful chain modeling is A3-Q17). |
| `app/test_data/keymap/resolution_table.linux.txt` | ENTIRE new 459-line golden: 7-line header (os=linux, rows=452) + 452 TAB-separated `context<TAB>trigger<TAB>winner` rows. | ✅ | The frozen pre-reorder baseline the whole engine axis diffs against. Deterministic across runs. Linux-only + config-relative; a Mac golden waits on the A6-Q14 OS-injection seam (additive, not a blocker). |

> **`core/app.rs` receives TWO independent hunks across the whole consolidation:** the X13 `test-util` accessor (~L1707, from the X13 net) and X9's `MatchResult::Unbound => false` dispatch arm (~L2050, from X9). Both land, in different regions, no conflict.

### 3d. App-crate dispatch arm (mechanically required by X9)

| Unit | Source | File | Symbols / Hunks | PR? | Why keep |
| --- | --- | --- | --- | --- | --- |
| **X9 dispatch arm** | `sha-ir/spike-x1-layeredkeymap @ 6391c43f` | `crates/warpui_core/src/core/app.rs` | `MatchResult::Unbound => false` in the keystroke-dispatch match (~L2050). | 🛠 | Required to compile once `MatchResult::Unbound` exists. **It is a placeholder** — whether an unbound key is CONSUMED (stop the responder chain) or FALLS THROUGH to a parent is an unresolved product decision (see §7). Land the arm, flag the policy. |

---

## 4. Explicit THROW List

Nothing in this section merges. Designs/findings survive only in `consolidation/results/` (§8) and the decisions table (§7).

### 4a. ALL plans / process docs (DROP — never merge)

`../plans/a3-q20-matcher-perf-plan.md`, `a3-q20-matcher-perf-spike-results.md`, `a3-q4-layered-store-plan.md`, `a3-q4-layered-store-spike-results.md`, `adversarial-spike-workflows-design.md`, `adversarial-spike-workflows-rollup.md`, `x13-resolution-snapshot-plan.md`, `x13-resolution-snapshot-spike-results.md`, and untracked `HANDOFF.md`. Also every `*-spike-results.md` copy that rides along inside a spike branch's diff (the canonical copies live in `consolidation/results/`).

### 4b. Throwaway / cfg-gated spike modules (DROP-AS-CODE; designs graduate)

| Artifact | Source unit | Note |
| --- | --- | --- |
| `crates/warpui_core/src/keymap/layered_spike.rs` (877 lines, `#[cfg(feature="layered_spike")]`) | X1 | The entire `LayeredKeymap`, `LayerTag`, indices, `rebuild_indices`, `layer_revision`, `bench_build`, index-sync tests. The DESIGN graduates (§5); the file does not merge. |
| `crates/warpui_core/src/keymap/resolve_spike.rs` (803 lines, `#[cfg(test)]`) | X6 | The parallel `resolve(TriggerQuery, view_id, ctx)` walk, `Suppress`/`SuppressKind`, `resolve_custom_menu`, and the `ported_test_*` golden ports. Unified scope-tagged resolve DESIGN graduates; module does not. |
| `crates/warpui_core/src/keymap_xplat_probe.rs` (246 lines, `#[cfg(all(test, feature="xplat_proto"))]`) | A6-Q3 | Seam-sanity + sourcing replica + serde mirror structs. DECISION graduates (§7); module does not. |
| The `xplat_proto`-gated `pub mod xplat_proto` block appended to `keymap.rs` (`parse_for`, `parse_sequence_for`, `ResolvedPair`, `XplatSideTable`) | A6-Q3 | Conditional keep only IF the A6-Q9/Q10 Phase-1 cmdorctrl slice starts immediately. **Default: DEFER — land the DECISION only.** Verified to be a pure append after `impl Keystroke` (~L1068), so it creates ZERO keymap.rs conflict in this pass. |
| matcher.rs cfg(`layered_spike`) `BackingKeymap` repoint (lines 11, 18-22, 27, 79, 95) | X1 | Production lands the store un-gated, not behind a throwaway feature. |
| `keymap.rs` module decls `pub mod layered_spike` (~L21), `mod resolve_spike` (~L26) | X1/X6 | Only mount throwaway modules. |
| `app/src/lib.rs` X1 passthrough feature; the X13 `cfg(feature="layered_spike")` routing-proof blocks | X1/X13 | Strip when landing the X13 net. |

### 4c. Benches + measurement glue (DROP unless a guard is explicitly wanted)

| Artifact | Source unit | Note |
| --- | --- | --- |
| `crates/warpui_core/benches/xplat_resolve.rs` + Cargo `[[bench]]`/`criterion`/`xplat_proto` feature | A6-Q3 | ns/op micro-bench; latency is non-deciding. FINDINGS (~1.35/3.56/9.70 ns) survive in the decision. |
| `crates/warpui_core/benches/keymap_layered.rs` (84 lines) + Cargo `[[bench]]`/`criterion`/`layered_spike` feature | X1 | N×U bench; flat-in-U FINDING survives in the results doc. |
| `crates/editor/benches/multi_selection_keystroke.rs` (579 lines) + fixture `multi_selection_fixture.md` (78 lines) + `crates/editor/Cargo.toml` `[[bench]]` + `regex` dev-dep + Cargo.lock edge | A4-Q16 | Harness=false scaffolding. **FLAG:** keep ONLY if a CI regression guard is explicitly wanted (results doc §7 suggests it; the strict rule says THROW). |
| The whole `#[ignore]` `bench_push_keystroke` fn (+263 in `matcher_tests.rs`) — synth generator, `pct`/`report`, variants a/a'/b/c/P2/P5, `struct Synth` | A3-Q20 | Self-labeled "Throwaway". DECISION = DEFER-TRIE (§7). **No code lands** unless a CI perf guard is explicitly built from the named symbols (de-spike recipe in the results doc). |
| `crates/warpui_core/src/keymap/{overlap}` cost-bench / >20-overflow exploration | A5-Q5 | Cost is inspection-settled; only the `MAX_ATOMS` guard (already in `overlap.rs`) graduates. |

### 4d. App-boot population walks + probes (DROP)

| Artifact | Source unit | Note |
| --- | --- | --- |
| `app/src/util/bindings_tests.rs` branch-appended L117-640 (the `a5_q5_full_population_keymap_conflict_walk` + helpers) | A5-Q5 | Full-app-boot measurement scaffolding (run-to-run non-deterministic ~8 pairs). **Restore the file to its 116-line merge-base form**; do NOT touch the pre-existing test or `bindings.rs:947` wiring. |
| `selection_model.rs:66-75` `anchor_count()` + `anchor.rs:201-210` `Anchors::anchor_count()` | A4-Q16 | Explicitly THROWAWAY spike instrumentation. Cherry-picking `b856d43d` auto-excludes them. |
| A6-Q3 `keymap_xplat_probe.rs` + its `lib.rs` gated decl; the reverted `pub cmd_or_ctrl: bool` field | A6-Q3 | Test scaffolding + a reverted blast-radius probe (already absent from the payload). |
| X1 `autotracking/layered_probe.rs` (225 lines) + `autotracking/mod.rs` `FANOUT_LOG` | X1 | The ONE structurally-mergeable X1 instrument, BUT it currently tests SIMULATED hand-built `Tracked<u64>` counters. **OPTIONAL later (§6 step 8):** rewire to the real revision counter once A3-Q4's store grows one, then graduate. Not part of the minimal KEEP. |

### 4e. Duplicated X13 nets (DROP all but the canonical)

The X13 4-file net is cherry-picked into `spike-x1-layeredkeymap`, `spike-x1-x13-prod-diff`, `spike-x9-tombstone`, `spike-x6-resolve`, and `worktree-spike-a3-q4-layered-store` (via commit `05429b67`). **Land it ONCE from `worktree-spike-x13-resolution-snapshot @ 2899121c`.** When landing A3-Q4, take ONLY its 3 `warpui_core` files and EXCLUDE its X13 cherry-pick files.

---

## 5. Engine Reconciliation — THE central decision

**CANONICAL = A3-Q4's `LayerStore` (un-gated), with X9's tombstone kernel COMPOSED onto it. X1's `LayeredKeymap` graduates as DESIGN + perf decisions only (not code).**

### 5a. Why A3-Q4 over X1

| Axis | A3-Q4 `LayerStore` | X1 `LayeredKeymap` |
| --- | --- | --- |
| Gating | **Un-feature-gated** (production-bound) | Entirely inside `layered_spike.rs` (877-line `#[cfg(feature="layered_spike")]` throwaway) |
| matcher.rs | **Untouched** | Repoints the Matcher behind the throwaway feature |
| X13 re-diff | **GREEN 452/452 byte-identical** | Clean feature-ON at 452 rows (but on the throwaway store) |
| Shadow surface | Option-A **derived** `custom_action_bindings()` — FIXES a latent override→Custom desync, deletes the dual-write | Still WRITES `editable_custom_action_bindings` (its inject dual-appends) |
| Verdict under keep-only rule | **KEEP (production)** | **THROW-AS-CODE** (design graduates) |

`HANDOFF.md` confirms intent: A3-Q4 "reserves a per-layer tombstone slot" for X9 — they were designed to compose. **Do NOT attempt to merge both keymap.rs rewrites; they hard-conflict line-for-line on the `Keymap` struct + `bindings()` + `custom_action_bindings()`.**

### 5b. Shape difference (for the merge agent)

- **A3-Q4:** THREE separate `LayerStore` structs (default/user/modepack), each `{fixed, editable: Vec<Tracked<EditableBinding>>, editable_by_name}`. Whole-keymap precedence is built lazily by chaining layers high-to-low **within each split**: `bindings()` = `modepack.editable().chain(user.editable()).chain(default.editable())` THEN the same for `.fixed()`. A nameable, zero-Box iterator preserving the historical global editable>fixed ordering. `custom_action_bindings()` = `matches!(trigger, Custom) || matches!(original_trigger, Some(Custom))`.
- **X1:** ONE flat `Vec<LayerEntry>` tagged `Base/UserOverride/ModePack`, plus DERIVED side-indices rebuilt on mutation (`custom_index`, `suppression_index`/`unbound_indices`, one shared `layer_revision`).

### 5c. Where X9's tombstone fits

- **On A3-Q4:** tombstone is a **per-binding `bool`** (the "reserved slot"); the matcher short-circuits on the chained `bindings()` walk. LIFO + tombstone short-circuit is sufficient — **NO suppression index needed** (A3-Q20 proved the linear scan is ~3 orders under frame budget). X9's `inject_binding` is **re-expressed to inject into `user_layer`** via `register_editable`; X9's `editable_custom_action_bindings` dual-append is **DROPPED** (A3-Q4's derived projection makes it obsolete and auto-satisfies the menu/dispatch consistency it guarded). `.rev()` folds into `LayerStore::get_binding_by_name` for same-layer matcher-LIFO consistency.
- **X1's suppression INDEX** (`suppression_index`/`unbound_indices`, proven flat-in-U) is a **deferred-optional optimization** (DEFER, same posture as DEFER-TRIE) — only revisit if a profile flags the linear suppression scan. It lives in the throwaway store and does not land.

### 5d. What graduates from X1 as DESIGN (Phase 2, re-implemented un-gated, validated against the X13 golden)

- The 4→1 flat-`Vec<LayerEntry>` collapse tagged Base/UserOverride/ModePack.
- Indexed-`Unbound` suppression proven **flat in U** (indexed +4.5% U1→U50 vs naive +1047%).
- Derived `custom_index` for the menu surface; a single shared `layer_revision` counter accepting whole-list settings-invalidation per override (bounded escape hatches per-row=1 / per-bucket=30 measured) **WITH a MANDATORY override-preview debounce residual**.
- X6's unified scope-tagged `resolve()` over `bindings()` (matcher unifies, but the 3 app.rs dispatch wrappers do NOT collapse — matcher-unify ≠ dispatch-unify).

> **RISK:** X1's perf/write-fan-out numbers were validated against the THROWAWAY `LayeredKeymap`, NOT A3-Q4's `LayerStore` (which chains 3 stores lazily, no suppression index, no revision counter). Those numbers **do not transfer** — re-validate when Phase-2 grafts them on; the override-preview-debounce residual carries forward unproven.

### 5e. X13-net land-once

Land the 4-file X13 net EXACTLY ONCE from `worktree-spike-x13-resolution-snapshot` as the FIRST engine-gate step (before A3-Q4). Take ONLY A3-Q4's 3 `warpui_core` files and EXCLUDE its X13 cherry-pick. After landing X13, run the snapshot to confirm GREEN; re-run after A3-Q4 and again after X9 to prove 452/452 holds across the reshape.

---

## 6. Recommended Merge Order (with verification)

Conflict files to watch throughout: `crates/warpui_core/src/keymap.rs`, `crates/warpui_core/src/keymap/matcher.rs`, `Cargo.toml`, `Cargo.lock`.

| Step | Land | Source | Exclude | Verify |
| --- | --- | --- | --- | --- |
| **1** | X7 leaf-Cow `context.rs` (verbatim) | `sha-ir/spike-x7-leaf-cow @ 7cb3a0b0` | the 6 ride-along `.md` files | `cargo check -p warpui_core --lib` = EXIT 0 |
| **2** | A4-Q16 HashSet fix (cherry-pick commit) | `sha-ir/spike-a4-q16-multiselection @ b856d43d` | the 2 `anchor_count` probes, the 579-line bench, fixture, Cargo/Cargo.lock bench wiring, 6 `.md` | `cargo check -p editor`; confirm `overlap_indices` is `HashSet` at both `.contains` sites and `anchor_count` did NOT come along. Can land in parallel (no keymap contention). |
| **3** | X13 net — all 4 files ONCE | `worktree-spike-x13-resolution-snapshot @ 2899121c` | the `layered_spike` routing blocks in the harness; all `.md` | `cargo test -p warp -- --ignored --nocapture x13_resolution_snapshot` → **GREEN baseline** |
| **4** | A3-Q4 — ONLY the 3 `warpui_core` files | `worktree-spike-a3-q4-layered-store @ f5f638fd` | its X13 cherry-pick (`app/.../snapshot_tests.rs`, golden, `lib.rs`, `core/app.rs` accessor — already in step 3); all `.md` | `cargo test -p warpui_core a3q4`; re-run `x13_resolution_snapshot` → must stay **452/452 GREEN** |
| **5** | X9 tombstone COMPOSED onto A3-Q4 | `sha-ir/spike-x1-layeredkeymap @ 6391c43f` | the cfg(`layered_spike`) repoint in matcher.rs; the 2 throwaway module decls in keymap.rs; the duplicated X13 net | `cargo test -p warpui_core` (the 5 tombstone/consistency tests incl. `test_inject_override_consistency_gate`); re-run `x13_resolution_snapshot` → 452/452 |
| **6** | A5-Q5 — `overlap.rs` + `overlap_tests.rs` (verbatim) + 2 keymap.rs hunks | `sha-ir/spike-a5-q5-conflicts @ 9584cbba` | the `bindings_tests.rs` walk (restore to 116-line base); the 6 `.md`; the cost-bench | PORT `AtomSet` `&'static str` → X7 Cow leaf (preserve `NotEqual`-on-absent `unwrap_or(true)`). `cargo nextest run -p warpui_core 'keymap::overlap'` = **9/9** |
| **7** | DECISIONS-ONLY into this manifest / results docs — **NO code** | — | — | A6-Q3 portability, A3-Q20 DEFER-TRIE, X1 LayeredKeymap design + perf, A5-Q5 finding, A4-Q16 cap OPEN (see §5d, §7) |
| **8** | OPTIONAL later: X1 `layered_probe.rs` write-fan-out instrument | `sha-ir/spike-x1-layeredkeymap` | — | Defer until A3-Q4's store grows a real revision counter; rewire from the simulated `Tracked<u64>` counters, then graduate into the reactive-invalidation suite. |

### 6a. keymap.rs composition notes (steps 4-6, hand-surgery)

THREE KEEP units touch `keymap.rs`: A3-Q4 (canonical rewrite ~205 lines), X9 (tombstone fields + inject + `.rev()`), A5-Q5 (+15 additive). **A6-Q3 does NOT land** (decision-only), so its append-at-EOF `xplat_proto` module creates ZERO keymap.rs conflict — the feared A6-Q3-vs-X9 struct-field collision **does not occur** in this pass.

- **Tombstone FIELDS** (X9): regions UNTOUCHED by A3-Q4 → compose cleanly, no textual conflict.
- **`get_binding_by_name`:** BOTH edit it. Keep A3-Q4's `layers_high_to_low().find_map(...)` AND fold X9's `.rev()` into `LayerStore::get_binding_by_name`.
- **`inject_binding`:** RE-EXPRESS to inject into A3-Q4's `user_layer` via `register_editable`; DROP the `editable_custom_action_bindings` dual-append.
- **matcher.rs (X9):** independent of A3-Q4 (which never touches matcher.rs) → lands as-is. DROP the cfg(`layered_spike`) repoint.
- **A5-Q5 lands LAST:** rebase the `pub mod overlap` + re-export block onto the post-A3-Q4+X9 module block (additive); the `context_predicate()` accessor is independent.

### 6b. Cargo.toml / Cargo.lock — NET RESULT: no manifest change for the KEEP set

Verified on `sha-ir/keybindings-draft`: `test-util` is already a feature (`warpui_core/Cargo.toml:19`); `rand` is already a `[dependencies]` entry (~:59); `criterion` is NOT present. Both A6-Q3 and X1 add `criterion` + a `[[bench]]` + a feature gate (`xplat_proto`, `layered_spike`); A4-Q16 adds `criterion` + `regex` to `crates/editor/Cargo.toml`. **All of these are attached to THROW benches → DROP them all; add no `criterion`, drop both `[[bench]]` stanzas + both features, and regenerate Cargo.lock to remove those edges.** The A4-Q16 KEEP needs only `std::collections::HashSet` (no manifest change).

---

## 7. Open Product Decisions to flag to humans

These are product/integration decisions, NOT de-spike work. They do not block landing the KEEP set, but the code below ships DORMANT until they are resolved.

| Decision | Owner question | Where it bites |
| --- | --- | --- |
| **Identifier-exclusion-groups (A5-Q5)** | A NEW declared identifier-mutual-exclusion primitive is a **REQUIRED Phase-1** primitive on top of `can_both_be_true`. Without it, cross-view false conflicts REMAIN (residual cross-view = 2645, 99.4% of overlap pairs; e.g. `id(TerminalPane) & id(SettingsView)` reported CAN-both though unreachable). | The oracle is correct but cross-view false-positives persist until exclusion-groups land. Also: A2 must thread `ContextPredicate` into the settings `ConflictMap` (`keybindings.rs:106` sees only `Option<Keystroke>`) before the oracle reaches users. |
| **Write-fan-out granularity + cross-frame preview debounce (X1)** | What is the write-fan-out threshold? The single `layer_revision` invalidates the whole settings list per override; the override-preview path re-invalidates per drained frame and **MUST be debounced**. | Phase-2 store. The debounce residual is MANDATORY and currently unproven against A3-Q4's store. |
| **R5 "show both" split (A6-Q3)** | Confirmed split: Phase-1 = symmetric `cmdorctrl`-token sites (mechanically derivable); asymmetric punctuation pairs (e.g. `cmd-[` vs `ctrl-shift-{`) DEFER to an Axis-2 `ResolvedPair{mac,other}` schema. Canonical type = option (b) trigger-level `{mac, other}`; option (a) `cmd_or_ctrl:bool` stays DEAD. | No code lands now. The seam (`parse_for`) + `ResolvedPair` graduate only when A6-Q9/Q10 Phase-1 starts. Residual: sourcing verdict rests on a 4-of-~330-site sample — full audit required before treating the symmetric slice as Axis-2-independent. |
| **Unbound-key consume-vs-fall-through (X9)** | `MatchResult::Unbound => false` is a placeholder. Should an unbound key be CONSUMED (stop the responder chain) or FALL THROUGH to a parent link? | `core/app.rs` ~L2050 dispatch arm. Unresolved by the spike. |
| **Dense multi-selection cap / incrementality + GPUI paint (A4-Q16)** | "Ship with no per-keystroke cap / no incrementality" stays OPEN. Model viable to ~10k both regimes, but 50k dense p50 = 42-48ms (OVER 16.67ms). **GPUI layout/paint of N quads is EXPLICITLY UNMEASURED** and gates the whole-feature cap decision (separate paint/layout spike). | The HashSet fix lands regardless; the cap/incrementality contract should be designed for (feeds A4-Q6 / A4-Q3). |
| **Trie deferred (A3-Q20)** | DEFER-TRIE: the R4 per-context trie is NOT an Axis-3 perf prerequisite (prod-scan p99 = 16.4µs at N=835; worst-case envelope p99 = 10.8µs — ~3 orders under budget). | No code. Side guardrail handed to Axis-6: do NOT parse/allocate per-binding on the keystroke hot path (per-binding `String` alloc crosses 100µs at N=5000). |

---

## 8. Index of Results Docs (`consolidation/results/`)

11 docs. "Committed in ../plans/?" marks the 3 that are ALSO tracked in `../plans/` (those committed plan copies are DROPPED; the `consolidation/results/` copy is the record we keep).

| # | Doc (`consolidation/results/`) | One-line verdict | Also committed in `../plans/`? |
| --- | --- | --- | --- |
| 1 | `x7-leaf-cow-spike-results.md` | TRUSTWORTHY-SUCCESS — KEEP single file `context.rs` (leaf→Cow); compiles clean, production-ready; doc's "RED" prose is stale. | No |
| 2 | `a3-q4-layered-store-spike-results.md` | KEEP — `LayerStore` refactor (CANONICAL engine) + 3 tests; X13 452/452; Option-A derived projection fixes shadow desync. | **Yes** |
| 3 | `x9-tombstone-spike-results.md` | PARTIAL-KILL (menu second-surface keeps its own short-circuit) — KEEP the Unbound-tombstone kernel + consistency plumbing + tests. | No |
| 4 | `x6-resolve-spike-results.md` | TRUSTWORTHY-SUCCESS as DESIGN — matcher unifies but dispatch wrappers don't collapse; resolve walk lives in throwaway `resolve_spike.rs` → graduates as design. | No |
| 5 | `x1-layeredkeymap-spike-results.md` | TRUSTWORTHY-SUCCESS as DESIGN — 4→1 collapse, indexed-Unbound flat-in-U, layer_revision; lives in throwaway `layered_spike.rs` → graduates as design, not code. | No |
| 6 | `x1-x13-production-diff-results.md` | CLEAN-CONFIRMED — LayeredKeymap feature-ON X13 diff at 452 prod rows; proves the design preserves resolution (design evidence only). | No |
| 7 | `x13-resolution-snapshot-spike-results.md` | KEEP all 4 files — the (context,trigger,OS)→winner regression net; canonical source, LAND ONCE. | **Yes** |
| 8 | `a5-q5-conflicts-spike-results.md` | TRUSTWORTHY-SUCCESS — KEEP `overlap.rs`+`overlap_tests.rs`+wiring; finding: conflict = `can_both_be_true` PLUS a required identifier-exclusion-groups primitive. | No |
| 9 | `a6-q3-portability-spike-results.md` | DECISION not code — canonical type = option (b) trigger-level {mac,other}; seam (`parse_for`) defers; all branch code is `xplat_proto`-gated throwaway. | No |
| 10 | `a4-q16-multiselection-spike-results.md` | INCONCLUSIVE at feature level (cap OPEN, paint unmeasured) — KEEP exactly one artifact: the HashSet fix in `merge_overlapping_selections`. | No |
| 11 | `a3-q20-matcher-perf-spike-results.md` | DEFER-TRIE — linear scan ~3 orders under budget; whole branch is a throwaway microbench; NO code lands (optional CI guard only). | **Yes** |

---

### Appendix — Source branches / commits referenced

| Unit | Branch / worktree | Commit | merge-base |
| --- | --- | --- | --- |
| X7 leaf-Cow | `sha-ir/spike-x7-leaf-cow` | `7cb3a0b0` | (current keybindings-draft) |
| A4-Q16 | `sha-ir/spike-a4-q16-multiselection` (tip `7dd68a99`) | fix commit `b856d43d` | `d5b2a4cf` |
| A5-Q5 | `sha-ir/spike-a5-q5-conflicts` | `9584cbba` | `d5b2a4cf` |
| X1-stack (X9+X6+X1) | `sha-ir/spike-x1-layeredkeymap` | `6391c43f` | `d5b2a4cf` |
| A3-Q4 LayerStore | `worktree-spike-a3-q4-layered-store` | `f5f638fd` (X13 cherry-pick `05429b67`) | `d7ecfac5` |
| A3-Q20 | `worktree-spike-a3-q20-matcher-perf` | `28126681` | `d7ecfac5` |
| X13 net (canonical) | `worktree-spike-x13-resolution-snapshot` | `2899121c` | — |
| A6-Q3 (decision-only) | `sha-ir/spike-a6-q3-portability` | `a4bc729b` | — |
