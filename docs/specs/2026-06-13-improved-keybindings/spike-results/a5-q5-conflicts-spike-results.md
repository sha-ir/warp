[← Back to Spike Designs index](../README.md) · [Axis 5 design](../axis-5-discoverability-and-conflicts/spike-design.md)

# A5-Q5 — truthful-conflict definition (a vs b vs c) + identifier-exclusion dependency · spike results

**Question.** Two weighted halves. (PRIMARY — truthfulness) Walked over the FULL production binding population, do the three competing conflict definitions yield `N_exact_eq ≤ N_overlap < N_naive`, is the `N_naive → N_overlap` reduction a substantive CLASS or a single-artifact cosmetic win, and how many cross-view collisions REMAIN conflicts under (c) because the engine has no identifier-exclusion model? (SECONDARY — soundness) Can a sound+complete `can_both_be_true` over the 7 predicate variants be built by atom-enumeration with map-key exclusivity — no external SAT crate, no `unsafe` — agreeing with a brute-force oracle on ≥100k randomized pairs including same-key/different-value and absent/sentinel cases?

**Verdict.** ✅ **TRUSTWORTHY SUCCESS — and it pivots the headline.** The oracle is sound (100% agreement, 100,000/100,000 pairs, 0 disagreements; all adversarial units pass; no SAT crate, no `unsafe`). The cost guard never fires (max atom-union 14 < 20; overflow counter == 0). On the asserted-full population (472 bindings, floor `> 200`) the three N's are distinct and ordered: **`N_exact_eq = 11 ≤ N_overlap = 2662 < N_naive = 2669`**. **BUT the load-bearing finding is that (c) alone is NOT substantively truthful:** the `N_naive → N_overlap` win is a thin **7-pair (~0.26%) explicit-negation class**, while **2645 cross-view false conflicts REMAIN conflicts under (c)** because the engine has no identifier-mutual-exclusion model. So this is a legitimate green that *answers* the design question by surfacing a new dependency, not by validating (c) as the deliverable.

**Phase-1 needs a NEW identifier-mutual-exclusion primitive on top of (c).** Residual cross-view conflicts under (c) = **2645**. Option (a) structural-equality (11) is also clearly beaten by (c) (2662), so the trivial option is insufficient too — but neither (a) nor (c) closes the cross-view gap.

**Branch.** `sha-ir/spike-a5-q5-conflicts` (off `keybindings-draft`; worktree `.claude/worktrees/spike-a5-q5-conflicts`). The oracle + tests + accessor + written finding are **keepable** (they graduate, gated on A2 threading the predicate into the settings conflict path); the app-boot walk glue is **throwaway** measurement scaffolding.

---

## Adversarial stance — the false-greens defended against

All six design false-greens (axis-5 doc line 20) were attacked by skeptics; none refuted the build.

1. **Partial-fixture measurement (TOP risk).** Harness B lives in the **app** crate (`app/src/util/bindings_tests.rs`, wired via `app/src/util/bindings.rs:946-948`), NOT `warpui_core` (which holds only ~3 of 30 register sites). It assembles the live population by running 39/40 real keybinding-registration init fns (mirroring `initialize_app`'s sequence in `app/src/lib.rs:1649-1693`), walks `ctx.get_key_bindings().chain(ctx.custom_action_bindings())`, and **asserts the floor** `total_population > 200` (line 610). Live run: 472 bindings — a real population, not a fixture. *Honest caveat:* the harness does not literally call `initialize_app`; it uses a lighter `App::test` boot + a hand-copied init list (a real drift fragility), and `workspace::init` is SKIPPED (its `AppEditorSettings` group is unreachable in the lighter boot), so coverage is 39/40 groups — still 472 bindings, far above the floor.
2. **Unsoundness / independent-boolean shortcut.** The oracle exercises BOTH attacked classes — map-key exclusivity (the 3-valued `TerminalView_BlockSelectionCardinality`, 16 eq!/ne! atoms) and the `ne!`-vs-absent (`unwrap_or(true)`) asymmetry — and agrees with brute force. **Mutation testing proved the tests are not vacuous:** removing the absent/other sentinel made the differential test fail on pair 0 and broke `adversarial_not_equal_satisfied_via_absent_sentinel`; injecting an independent-boolean shortcut made it fail on a same-key multi-value pair and broke `adversarial_same_key_different_value_is_unsatisfiable`. Both reverted; baseline re-passes 9/9.
3. **Cosmetic truthfulness win.** Confirmed AND quantified, not papered over — see §3. The reduction is a substantiated >1-pair class (7 pairs across multiple identifier families), and the residual is reported (2645).
4. **Logical vs reachable.** `can_both_be_true` measures *logical* satisfiability over synthetic contexts; with no identifier-exclusion model `id(TerminalPane) & id(SettingsView)` reports CAN-both-be-true and stays a "conflict." The doc and harness flag this explicitly — `is_cross_view` is labelled a heuristic (disjoint required-positive-id proxy) and the finding names exclusion-groups as the real primitive.
5. **(a) == (c) undetected.** All three N's are printed on distinct labelled lines (11 / 2662 / 2669); both kill branches are evaluated against distinct integers, so equality cannot be concealed.
6. **Disabled/chord/triggerless universe.** The walk states its universe (see §2): unfiltered `keymap.bindings()`, single-keystroke only; chords excluded = 0, triggerless excluded = 82, single-keystroke walked = 390.

---

## 1. Soundness result (Harness A — `warpui_core`, zero keymap data)

`cargo nextest run -p warpui_core 'keymap::overlap'` → **9/9 PASS**, 292 skipped.

- **Differential oracle: 100% agreement, 100,000/100,000 pairs, 0 disagreements.** `differential_can_both_be_true_matches_brute_force_oracle` asserts every pair equal to an **independent recursive brute-force oracle** that keeps the explicit OTHER value AND absent/None **separate** — so agreement proves production's single collapsed sentinel, map-key exclusivity, and the `NotEqual = Not(Equal)` absent-asymmetry (`unwrap_or(true)` vs `unwrap_or(false)`, confirmed in `context.rs`) are all sound.
- **Corpus is not degenerate.** Coverage floors fail a green on a toy corpus: `same_key_diff_value > 1000`, `not_equal_atom > 1000`, `both_true > 1000`, `max_atom_union ≤ 20`.
- **Adversarial units pass:** same-key/different-value unsatisfiable, subsumption satisfiable, `ne!`-via-absent-sentinel reachable, `not_equal_on_absent_key` true, equal-vs-not-equal-same-value unsatisfiable, plus the guard/overflow-counter test.
- **No SAT crate** (varisat/splr/minisat/cadical/z3/batsat/cryptominisat/rustsat/kissat all absent from `crates/warpui_core/Cargo.toml`, root `Cargo.toml`, `Cargo.lock`). **No `unsafe`** in `overlap.rs`/`overlap_tests.rs` (the word appears only in a doc comment).

## 2. The three N's on the asserted-full population (Harness B — app crate)

`cargo nextest run -p warp a5_q5_full_population_keymap_conflict_walk --no-capture` → **1 passed**. Platform **Linux**.

**Universe statement.** Binding population = **472** (floor assert `> 200`, so well above floor). Init fns ran = 39, skipped = 1 (`workspace` — needs the private `AppEditorSettings` settings group unreachable from the lighter test boot). The walk is over the **unfiltered** `get_key_bindings() ∪ custom_action_bindings()` set, bucketed by **single resolved Keystroke** on the current platform: chords excluded = 0, triggerless (Standard/Custom/Empty) excluded = 82, single-keystroke walked = 390, distinct keystrokes = 142, colliding keystrokes (>1) = 52.

| Definition | Count | Meaning |
|---|---:|---|
| **N_naive** (all same-key pairs) | **2669** | today's map semantics — every same-keystroke pair is a "conflict" |
| **N_overlap** (option **c**, `can_both_be_true`) | **2662** | logical-overlap conflict oracle |
| **N_exact_eq** (option **a**, structural equality) | **11** | trivial structural-equality conflict |

Invariant `N_exact_eq ≤ N_overlap ≤ N_naive` holds (11 ≤ 2662 ≤ 2669). Cost half: max atom-union = **14** (< 20 guard); overflow guard fired = **0** (asserted `== 0`).

## 3. Cause-class breakdown + residual cross-view (the load-bearing substance)

**`N_naive → N_overlap` removals = 7, ALL explicit-negation contradiction** (same-key-value exclusivity = 0; other/non-conjunctive = 0). This is a substantiated CLASS, not one cosmetic artifact pair: the 7 span multiple identifier families — `EditorView & !IMEOpen & Vim` vs `& !Vim`; `warpify_subshell` vs `input:set_mode_terminal`/`input:set_mode_agent`; Terminal/`!IMEOpen` block-selection forks; `TabConfigParamsModal & !EditorView` vs `EditorView & !IMEOpen`. Machinery: `enum RemovalCause { ExplicitNegation, SameKeyValue, Other }` + `classify_removal()` flattens each predicate's top-level AND chain (pushing negation to leaves) and attributes each removed pair to three printed counters, collecting up to 12 examples per category.

**Residual cross-view (REMAIN conflicts under c) = 2645; intra-view (shared required id) = 17.** `residual_cross_view`/`intra_view_overlap` are incremented INSIDE the `if can_both_be_true(...)` branch and split via `is_cross_view()` (disjoint required-positive-id sets). Arithmetic reconciles exactly: `2669 − 2662 = 7 = removed_total`; `2662 = 2645 + 17`; `11 ≤ 2662 ≤ 2669`.

**Conclusion.** Option (c)'s win over naive is a thin ~0.26% explicit-negation artifact; the cross-view false conflicts the headline targets (2645, 99.4% of overlap pairs) **remain** conflicts under (c). Option (a) (11) is clearly insufficient vs (c) (2662). So neither (a) nor (c) is substantively truthful on its own.

## 4. Does Phase-1 need an identifier-mutual-exclusion primitive on top of (c)?

**YES.** `can_both_be_true` measures *logical* satisfiability over synthetic contexts; with no identifier-exclusion model, `id(TerminalPane) & id(SettingsView)` is reported CAN-both-be-true and stays a "conflict" though it is unreachable. The 2645 residual cross-view conflicts are exactly these unreachable pairs. (c) is the correct *logical* primitive but does not close the reachability gap — **Phase-1 must add a declared identifier-mutual-exclusion (exclusion-groups) primitive on top of (c)** before "truthful conflicts" is honest. The recommended definition is therefore **option (c) + declared exclusion groups**, not (a) alone and not (c) alone.

## 5. Keep vs throw

- **KEEP (graduates to production, gated on A2 threading `ContextPredicate` into the settings conflict path):**
  - `atoms()` collector (`crates/warpui_core/src/keymap/overlap.rs`).
  - `can_both_be_true()` with **map-key exclusivity** + the **`NotEqual = Not(Equal)`** absent-asymmetry modeling.
  - the **differential oracle + adversarial units** (`overlap_tests.rs`) — become the regression suite for the shipped overlap primitive.
  - the one-line `BindingLens::context_predicate()` accessor (`keymap.rs:267`).
  - **the WRITTEN FINDING** — cause-class breakdown + residual-cross-view count — this is what decides Phase-1 scope (need exclusion-groups).
- **THROW:** the criterion bench, the worst-case synthetic predicate, the `>20`-overflow path beyond the trivial safety guard (cost is inspection-settled), and the full-app boot/walk glue (`app/src/util/bindings_tests.rs` — measurement scaffolding only).

## 6. Residual risks / out of scope (carried, not silently dropped)

1. **Reachability unmodeled** (the headline residual). (c) measures logical satisfiability; the 2645 cross-view false conflicts persist because there is no identifier-mutual-exclusion model. The spike quantifies the gap but does not close it — "truthful conflicts" is only honest once exclusion-groups ship (the NEW Phase-1 primitive this spike surfaces but does not build).
2. **Production-graduation gap (A2 dependency).** The spike walks `BindingLens` (which carries the predicate), but the shipping `ConflictMap` sees only `Option<Keystroke>` (`keybindings.rs:106`); A2 must thread `ContextPredicate` through before (c) reaches users (A5-Q11 Phase-2 gate).
3. **Universe fidelity.** N's are over the unfiltered `bindings()`; they do not apply the `enabled_predicate`/context filtering of real dispatch, so the measured conflict set may not equal the dispatched one.
4. **Chord / triggerless out of scope.** Single-keystroke bucketing drops chords (0 here) and Standard/Custom/Empty triggers (82 excluded); deferred to A5-Q7/Q9 — the green must not be read as covering them.
5. **Platform.** Keystrokes resolve to the current OS at parse; the walk measures **one platform's (Linux)** conflict set only.
6. **Population drift.** 472 is a snapshot of a hand-copied init list (39/40 groups; `workspace` skipped). Without a completeness/golden test (A5-Q13) the N's rot as bindings are added, and the harness can silently drift from `initialize_app`. *Minor reproducibility note:* the exact delta wobbles run-to-run by ~8 pairs (an observed run gave 2654/removed 15/residual 2639; the committed run gives 2662/removed 7/residual 2645) — the three N's stay clearly distinct and ordered, and the qualitative finding (thin negation win + large residual cross-view) holds in every run; only the exact removal/residual split is non-deterministic.

## 7. Unblocks

- Settles **A5-Q5's** operational definition of conflict: **(c) `can_both_be_true` + declared exclusion-groups**, not (a) alone, not (c) alone — and surfaces identifier-mutual-exclusion as a **required Phase-1 primitive** (previously buried as a follow-on).
- Feeds **A5-Q6** (binding universe: include `get_key_bindings` + `custom_action_bindings`), **A5-Q7** (chord/prefix conflicts reuse this exact predicate-overlap primitive keyed on `Vec<Keystroke>`), and **A5-Q1/R6/G1** ("names the colliding action" needs a real conflict set).
- **Prerequisite for production graduation** (not for running the spike): A2 threads `ContextPredicate` into the settings `ConflictMap`.
