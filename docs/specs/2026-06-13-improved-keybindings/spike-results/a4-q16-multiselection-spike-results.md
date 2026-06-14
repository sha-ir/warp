[← Back to Spike Designs index](../README.md) · [Contract: Axis-4 modality (pluggable)](../axis-4-modality-pluggable/spike-design.md)

# A4-Q16 — multi-selection keystroke / overlap regime · spike results

**Question.** Under a REAL Helix steady state (`%` then `s\w+<CR>` producing N non-overlapping selections), when one `w`/`e` extend-all keystroke is applied: (U1, regime) does the realized `overlap_indices.len()` that `merge_overlapping_selections` sees stay **small/local** (k ≪ N, keeping merge effectively linear) or **chain to ~N** (the O(N²) `Vec::contains` path)? And (U2, constant factor) for whichever regime, at what N does p50 of one keystroke (merge + word-navigate + `set_selection_offsets` + full `to_rendered_selection_set` rebuild) cross 16.67 ms / the 8 ms input target, on a real markdown/code buffer, on a model pre-aged with dead anchors? **Explicitly out of scope:** GPUI layout + paint of N selection quads — a green here is necessary-not-sufficient for the frame.

**Verdict.** ⚠️ **INCONCLUSIVE (model layer is sound; the no-cap question is NOT cleared).** The bench is valid and the regime answer is real — but it is **density-dependent**, and the headline adversarial case lands in the regime that *fails* the success bar. The realistic spaced-multi-cursor regime (SPARSE, stride 5) is **local-k with k = 0** and stays under the 16.67 ms frame across the **entire** sweep (worst realized ≈ 13,688 selections at 12.8 ms p50). But the primary Helix-style "select every word then extend-all" regime (DENSE, stride 1) is **chained-N** — `overlap_indices.len() == N` (100 %) at every N ≥ 100, identical for rust and markdown — and its **~50k worst case is 42–48 ms p50 / 47–61 ms p99, NOT under 16.67 ms**. The spec's Trustworthy-Success bar requires *both* (a) k ≪ N AND (b) the 50k worst case under frame; the chained-N regime and the 50k overrun break both. No KILL fired (the chained-N collapse is genuinely-overlapping geometry, correct semantics, and the HashSet fix keeps it O(N), not O(N²)). Anchor-growth criterion (c) **PASSES**. All five adversarial skeptics confirm the bench is honest and correctly scoped. The model + selection-rebuild layer is therefore *viable* up to ~10k selections in either regime, but the **no-cap / no-incrementality decision for the whole feature stays OPEN** — both because dense extend-all blows the frame at extreme N at the model layer alone, and because paint of N quads remains unmeasured.

**Branch / worktree.** `sha-ir/spike-a4-q16-multiselection` (worktree `/home/mhb/warp/.claude/worktrees/spike-a4-q16-multiselection`, off `sha-ir/keybindings-draft`). The **HashSet fix** (`b856d43d`) is a real, mergeable PR; the **throwaway bench** (`5b9451b7`) is the regression-guard artifact. `cargo bench -p warp_editor --bench multi_selection_keystroke` exits 0. Logs: `/tmp/a4q16/bench2.log`.

---

## 1. Realized-overlap regime (the headline U1 answer)

REALIZED `overlap_indices.len()` vs N, measured on the post-`w`/`e` extend-all geometry — the exact count `merge_overlapping_selections` walks. Source: `/tmp/a4q16/bench2.log`.

**DENSE (stride 1 — a selection on EVERY word; the Helix `%` + `s\w+<CR>` analogue). rust AND markdown gave IDENTICAL counts.**

| N | selN | overlap_len | ovl/N | regime |
|---:|---:|---:|---:|:--|
| 1 | 1 | 0 | 0.0 % | — |
| 100 | 100 | 100 | **100.0 %** | chained-N |
| 1000 | 1000 | 1000 | **100.0 %** | chained-N |
| 5000 | 5000 | 5000 | **100.0 %** | chained-N |
| 10000 | 10000 | 10000 | **100.0 %** | chained-N |
| 50000 | 50000 | 50000 | **100.0 %** | chained-N |

→ `overlap_len == N` at every N ≥ 100 ⇒ **CHAINED-N**. One word-extend pushes each selection's head into its right neighbor, so the whole set collapses into a single chained overlap group. This is exactly the O(N²) `Vec::contains` trigger; the HashSet fix at `selection_model.rs:178` is **load-bearing** here.

**SPARSE (stride 5 — every 5th word; realistic multi-cursor spacing).**

| N | selN | overlap_len | ovl/N | regime |
|---:|---:|---:|---:|:--|
| 1 | 1 | 0 | 0.0 % | local k=0 |
| 100 | 100 | 0 | 0.0 % | local k=0 |
| 1000 | 1000 | 0 | 0.0 % | local k=0 |
| 5000 | 5000 | 0 | 0.0 % | local k=0 |
| 10000 | 10000 | 0 | 0.0 % | local k=0 |
| 50000 | 13688 (realized/tiled) | 0 | 0.0 % | local k=0 |

→ `overlap_len == 0` everywhere ⇒ **LOCAL (k = 0)**: a one-word extend never reaches the selected word 5 words away.

**Bottom line:** the regime is density-dependent. The primary/adversarial dense case is **chained-N**; spaced multi-cursor is **local-k with k = 0**. The answer is not a single regime — it depends on how tightly the selections are packed.

---

## 2. N-vs-latency (the U2 constant-factor answer)

Model + selection-rebuild + full `to_rendered_selection_set` per ONE keystroke. **PAINT / LAYOUT OUT OF SCOPE.** Budgets: 8 ms input target, 16.67 ms frame. Source: `/tmp/a4q16/bench2.log`.

| Fixture / regime | N | p50 (ms) | vs 8 ms | p99 (ms) | vs 16.67 ms | burst30 (ms) |
|:--|---:|---:|:--:|---:|:--:|---:|
| **DENSE rust** | 1 | 0.001 | OK | 0.001 | OK | 0.025 |
| | 100 | 0.056 | OK | 0.082 | OK | 0.086 |
| | 1000 | 0.638 | OK | 0.776 | OK | 0.674 |
| | 5000 | 3.667 | OK | 4.167 | OK | 3.685 |
| | 10000 | 7.748 | OK | 12.897 | OK | 8.173 |
| | 50000 | **48.444** | **OVER** | **60.861** | **OVER** | 49.491 |
| **DENSE markdown** | 100 | 0.058 | OK | 0.075 | OK | — |
| | 1000 | 0.604 | OK | 1.103 | OK | — |
| | 5000 | 3.309 | OK | 4.435 | OK | — |
| | 10000 | 6.745 | OK | 14.145 | OK | — |
| | 50000 | **42.424** | **OVER** | 47.247 | **OVER** | — |
| **SPARSE rust** | 100 | 0.054 | OK | 0.085 | OK | — |
| | 1000 | 0.699 | OK | 0.801 | OK | — |
| | 5000 | 4.531 | OK | 5.386 | OK | — |
| | 10000 | 9.277 | **OVER** | 9.878 | OK | — |
| | 50000 (realized 13688) | 12.797 | **OVER** | 14.490 | OK | — |

- **p50 < 16.67 ms (frame budget):** DENSE/chained holds up to **N = 10,000** (7.7 ms rust / 6.7 ms md); the crossover is between 10k and 50k (50k p50 = 42–48 ms). SPARSE/local holds across the **entire** sweep (worst realized ≈ 13,688 at 12.8 ms).
- **p50 < 8 ms (input target):** DENSE stays under up to ~10,000 (7.7 ms, just under). SPARSE crosses between 5k (4.5 ms) and 10k (9.3 ms).
- **~50k dense worst case: NOT under 16.67 ms** (42–48 ms p50). The dominant per-keystroke cost there is *not* the merge but the O(N) anchor resolves across 50k selections in `set_selection_offsets` + `to_rendered_selection_set`.

**Criterion `iter_custom` (rust dense, N=1000), supplementary timed bench:**
- `multi_selection_keystroke/rust_dense_n1000`: median **515 µs** [508.5 µs .. 522.2 µs].
- `…/rust_dense_burst30_n1000`: median **546 µs total** for 30 keystrokes (~18 µs/keystroke amortized; successive extends saturate at line ends).

Dense p50 scales ~linearly (N ×50 ⇒ time ×75.9 from 0.638 ms@1k to 48.444 ms@50k), **not ×2500** as a live quadratic would — direct evidence the HashSet fix holds.

---

## 3. Anchors growth (success criterion c) — PASS

```
[anchor-growth] N=100 applies=1000
anchors: before=202  bloated=200202  after_edit=201
resolve x200000: baseline=1.334ms  bloated=1.320ms  ratio=0.99 (O(1) => ~1)
```

All three assertions held:
1. The map **GREW** under 1000 no-edit `set_selection_offsets` applies (202 → 200,202 dead anchors).
2. Resolve stayed **O(1)** under ~1000× bloat (ratio 0.99 — no regression in locality).
3. The next edit's retain pass **RECLAIMED** the dead anchors (200,202 → 201).

`anchorsGrowthOk = true`.

> **Flagged (NOT a kill criterion):** the **retain-reclaim spike** — a single real edit on the dead-anchor-bloated map — costs ~10.8 ms (N=100) up to **~21–24 ms** at large N (dense N=50k / md N≥1000), itself over a frame. Separate from the keystroke path, but a real cost the no-cap decision must weigh.

---

## 4. Verdict against the spec's success criteria (model+rebuild layer ONLY)

- ⚠️ **(a) realized `overlap_indices` stays k ≪ N under real `w`/`e` extend-all** → **SPLIT.** TRUE for SPARSE (k = 0). FALSE for DENSE (k = N, 100 %). The criterion is not met in the headline adversarial regime.
- ⚠️ **(b) p50 < 16.67 ms to N=10k AND the ~50k worst case < 16.67 ms** → **PARTIAL.** p50 < 16.67 ms to N=10k holds (both regimes); the **50k dense worst case = 42–48 ms FAILS**. SPARSE 50k (realized 13,688) is fine.
- ✅ **(c) Anchors growth across 1000 no-edit applies does not regress resolve below O(1); the next edit reclaims** → **PASS** (§3).

Two of three success conditions are not cleanly met in the adversarial case, so the model layer is *not* cleared to "ship with no cap." It is *viable* up to ~10k selections; beyond that, dense extend-all blows the frame at the model layer alone.

---

## 5. Adversarial skeptic findings (all five confirm the bench is honest)

1. **model-only-scope — NOT refuted (scope correctly bounded), high confidence.** No artifact over-claims. The timed routine (`keystroke_timed`, bench lines 241–264) calls no GPUI layout/paint; `to_rendered_selection_set` (`buffer.rs:2081`) is a model-layer rebuild, not a quad paint. The bench header (lines 5, 18–20), the runtime print, the spike contract (`axis-4-modality-pluggable.md:18,20,23,24a`), and the downstream decision brief all keep paint UNMEASURED and the no-cap/no-incrementality decision OPEN. The over-read the trap warns of does not occur.
2. **wrong-geometry — REFUTED (geometry is genuinely real), high confidence.** Selections come from a REAL `\w+` regex split over real on-disk fixtures (`test_rust_file.rs` 283 KB, `multi_selection_fixture.md`); the extend is the REAL `word_ends_from_offset_exclusive` + `WordBoundariesPolicy::Default` primitive that production `extend_selection` uses; overlap is MEASURED on the post-extend geometry via a faithful re-impl of `Buffer::overlapping_ranges`. Stride only selects *which* real words become selections — overlap is realized, not stipulated. **This is the key skeptic for the regime question, and it confirms the regime answer is trustworthy** (so the verdict is NOT False-green-caught).
3. **warm-cache — NOT refuted (pre-aging + interleaved edit present), high confidence.** The bench pre-ages with up to 1000 no-edit applies (`PRE_AGE_ANCHOR_BUDGET`), interleaves a real retain-pass edit (`insert_one_char_update`), and reports explicit p99 (not amortized mean). It uses `iter_custom` rather than literal `iter_batched` (documented: `App::test` needs a `'static` future), with the same "pre-age, time only the routine" semantics. The "criterion-default-on-clean-model" trap is decisively false.
4. **single-keystroke — REFUTED, high confidence.** (Cross-checked against the A3-Q20 matcher bench, which times exactly one op per iteration with `pending.clear()` between samples.) Here the equivalent guard is the explicit **burst30** column (held-autorepeat ~30 keystrokes), so sustained input is reported, not a single op understatement.
5. **mis-attribution — NOT refuted (correct function fixed AND committed), high confidence.** Fix commit `b856d43d` touches ONLY `selection_model.rs` and modifies `merge_overlapping_selections`, NOT `overlapping_ranges` (which is itself O(N log N): one `sort_by_key` + one linear pass). The HashSet is inserted AFTER the `is_empty` early-return so both `.contains` calls become O(1); verified present in HEAD; the later bench commit did not revert it.

> None of the five found a defect. The only standing limitation is the model-only scope — an explicit, documented, honest caveat, not a false green. That is why this is **Inconclusive**, not **False-green-caught**.

---

## 6. KILL check — did NOT fire

- **KILL 1 (chained `overlap_indices` ~N AND O(N²) reached AND many selections WRONGLY collapse):** NOT FIRED. Chained-N appears only in DENSE, where every adjacent word is selected and each head extends into its right neighbor — the selections **genuinely overlap**, so merge collapsing them is **correct semantics, not a correctness bug** (the task explicitly excludes the synthetic all-colliding worst case as a standalone kill). And O(N²) is **not realized**: the HashSet fix holds and dense p50 scales ~linearly (§2).
- **KILL 2 (model+render p50 crosses 16.67 ms below N≈5k in the realistic non-overlapping regime):** NOT FIRED. Realistic = SPARSE: p50 at N=5000 is 4.531 ms and never crosses 16.67 ms anywhere (peak 12.797 ms at realized 13,688). The only sub-frame concern is the 8 ms *input target* crossing at N=10000 — above N≈5k and a different budget.
- **KILL 3 (anchors map grows UNBOUNDED across 1000 no-edit applies, degrading resolve locality):** NOT FIRED. Map is bounded/reclaimed by the next edit's retain (200,202 → 201); resolve ratio 0.99 (§3).

`killFired = false`.

---

## 7. Keep vs throw

- **KEEP — the HashSet fix (a real PR), `b856d43d`.** `crates/editor/src/content/selection_model.rs:178` — `let overlap_indices: HashSet<usize> = overlap_indices.into_iter().collect();` after the `is_empty` early-return, turning two `Vec::contains` scans into O(1) membership. **Mandatory-regardless** insurance: the dense chained-N regime is genuinely reachable from `%` + `s\w+` + `w`, and without this fix that path is the O(N²) catastrophe. This should land independent of the cap decision.
- **KEEP — both tables as a CI regression guard.** The realized-overlap regime table (§1) and the N-vs-latency p50/p99 sweep (§2). Promote a guard such as "dense p50 stays ~linear in N (no quadratic blow-up) and SPARSE p50 < 16.67 ms through N=10k" so any future merge/anchor/rebuild change has a baseline. The throwaway bench (`5b9451b7`) is the harness for it.
- **THROW — the throwaway instrumentation tied to the spike.** `BufferSelectionModel::anchor_count` (`selection_model.rs:69-75`, marked THROWAWAY) and the bench's `pub(crate)`/`#[cfg(test)]` work-arounds (drives the primitives rather than the `SelectionModel` wrapper; loads markdown as plain text — see bench header lines 22–49). The bench target is `harness = false`, so `cargo test` does NOT collect its `#[test]` (this is why `anchors_map_growth_does_not_regress_resolve` reports "0 tests / 426 filtered out"; the equivalent assertion runs via the bench's `run_headline_report` and PASSED).

---

## 8. Scope note — paint is UNMEASURED and does NOT license "ship no cap"

A green on the model + selection-rebuild layer is **NECESSARY-NOT-SUFFICIENT** for the 16.67 ms frame. **EXPLICITLY UNMEASURED here (no green clears these):** GPUI layout + paint of N selection quads, autoscroll, `SelectionChanged` subscriber fan-out. The "ship with no per-keystroke cap / no incrementality" decision for the whole feature stays **OPEN** and is gated on a **separate paint/layout spike**, independent of this bench. This is reinforced by the model layer itself failing the 50k dense worst case (42–48 ms) before paint is even added — so even at the model layer, the no-cap path is not clear at extreme N.

---

## 9. Residual risk (carried, not dropped)

1. **Fixture sensitivity.** The regime is density-dependent and depends on the test fixture's word density and the chosen motion. A pathological real document (dense adjacent words → chained overlaps) lands in the dense regime that the SPARSE fixture misses; the regime result should be re-run over 2–3 representative docs before any cap decision treats SPARSE as "the" answer. (DENSE rust+md already agree, which bounds one direction.)
2. **CI / lower-end hardware.** Criterion measures *this* machine's constants. CI or lower-end hardware shifts every crossover N **downward**, so the reported N (10k frame crossover, 5k–10k input-target crossing) is an **upper bound**, not a guarantee.
3. **Triple merge call sites.** `merge_overlapping_selections` is invoked from multiple paths (`buffer.rs:1637/1771`, `selection.rs:683`); the per-keystroke merge multiplier must be confirmed from the production dispatch path, not assumed to be exactly one — if a real keystroke runs merge more than once, the §2 numbers are an under-count.
4. **Retain-reclaim spike over frame.** A single edit on a dead-anchor-bloated map reaches ~21–24 ms at large N (§3) — separate from the keystroke path but a real per-edit cost the cap/incrementality decision must account for.
5. **Paint unmeasured (§8).** The plausible true frame bottleneck (paint of N quads) is deliberately not measured; the no-cap / no-incrementality decision could still flip toward mandatory incrementality after the render spike.

---

## 10. Unblocks

- **A4-Q16 itself** is split into (i) a **settled model-layer answer** — viable to ~10k selections in either regime; dense extend-all overruns the frame at ~50k at the model layer alone; SPARSE is fine through the sweep — and (ii) an **explicitly-deferred paint question** that still gates the whole-feature cap decision.
- **Lands the HashSet fix** as mandatory-regardless cheap insurance against the genuinely-reachable dense chained-N O(N²) path.
- **Keeps OPEN** (does NOT license) the selection-count-cap and incremental/dirty-region render decisions — gated on the separate paint/layout spike, and now additionally motivated by the 50k dense model-layer overrun.
- **Hands A4-Q6 / A4-Q3** a concrete input: a max-selections / incrementality contract is *not yet ruled out* and should be designed for, pending paint.
