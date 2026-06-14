[← Back to Spike Designs index](../README.md) · [Spec: Cross-axis — X1](../cross-axis-sequencing/spike-design.md) · [Builds on: X9 tombstone](./x9-tombstone-spike-results.md) · [Unified resolver: X6 resolve()](./x6-resolve-spike-results.md) · [Perf sibling: A3-Q20](./a3-q20-matcher-perf-spike-results.md) · [Gate: X13 snapshot](./x13-resolution-snapshot-spike-results.md)

# X1 — `LayeredKeymap` engine capstone (single store + indexed-Unbound suppression + write-fan-out) · spike results

**Question.** Can the four-plus parallel binding vectors (`editable_bindings`, `editable_custom_action_bindings`, fixed bindings, the macOS-menu custom cache) collapse to **ONE** owned `LayeredKeymap` store (`Vec<LayerEntry>` tagged `Base` / `UserOverride` / `ModePack`, with the X6 single-walk indexed-`Unbound` suppression primitive and a *derived* `custom_index`) such that — on its three load-bearing legs — **(a) PARITY:** the verbatim `matcher_tests.rs` passes against the `LayeredKeymap`-backed `Matcher` with **zero parallel owned binding vecs** and the derived `custom_index` stays correct *after* layer mutation (reset-all clear+replay, mode-pack push/pop); **(b) LATENCY:** `push_keystroke` p99 stays under the input budget at N=2000 and within ~1.5× of the flat scan, with the layered/flat ratio **not** growing with the Unbound count U (i.e. suppression is an O(1)-per-binding indexed lookup, not an O(N×U) scan); and **(c) AUTOTRACKING:** a *single shared* `Tracked<u64>` layer-revision counter's write-side invalidation fan-out — on one override edit and on a 5-keypress override-preview burst — is bounded or an explicitly-documented-and-accepted number, measured through the **real** `render_view` begin/end + `track_update` path (the load-bearing leg the redesign exists for)?

**Verdict.** ✅ **TRUSTWORTHY-SUCCESS (write-fan-out is an explicit, accepted, bounded-escapable whole-list number; the override-preview debounce is a carried residual).** No KILL fired on any of the three kill clauses, and no skeptic's evidence substantiated its trap — most importantly the **autotracking false-green skeptic refuted itself**: the trivially-true *"matcher walk yields 0 settings-list invalidations"* assertion was genuinely **DELETED** (it survives only in the probe's docstring explaining why), the probe drives a **real** `render_view` begin/end around N=300 `Tracked`-backed reads, and a decisive mutation (replacing `render_view(window,row,||read_dep(i))` with a bare `read_dep(i)`) flips **all 5** probe tests to `left:0 vs right:300` — so the green is load-bearing, not hollow. All gates hold: (a) the verbatim `matcher_tests.rs` (untouched by the X1 commit) passes feature-ON with the `LayeredKeymap` holding ONE owned `Vec<LayerEntry>` and INDEX-only side structures, and `custom_index` is correct after reset-all AND mode-pack; (b) `push_keystroke` p99 ≈ 5.1 µs layered / 5.2 µs flat at N=2000 (~40× under the 200 µs budget), layered/flat p50 ≈ 1.0, and the production indexed suppression is **flat in U** (indexed/flat U1→U50 +4.5%) while the deliberately-rejected naive O(N×U) anti-pattern grows ×11.7 — proving the bench *can* detect O(N×U) and the chosen path does not exhibit it; (c) one override write invalidates the **whole 300-row list** — an EXPLICIT, asserted, documented, **accepted** number (not silent), against which the bench also measures the bounded escape hatches it regresses from (per-row Tracked = 1 row; per-bucket(10) = 30 rows), and the 5-write preview burst **dedups within a frame to 300, not 5×300=1500**. The verdict considered and rejected **Partial-kill**: the Trustworthy clause explicitly permits *"an explicitly documented + accepted whole-list number"* for the single override write, and the within-frame preview burst meets its no-per-write-full-list condition — what remains (cross-frame, each drained keypress re-invalidates the whole list ⇒ the preview path **must be debounced**, and the fan-out threshold is a judgment call) is carried as a **mandatory residual**, not a blocking decision.

**Branch / worktree.** `sha-ir/spike-x1-layeredkeymap` (worktree `/home/mhb/warp/.claude/worktrees/spike-x1-layeredkeymap`, off `sha-ir/keybindings-draft`). HEAD `3889f1c5` (`spike(keybindings): X1 LayeredKeymap engine slice + redesigned write-fan-out probe`) on top of the X9 tombstone + X6 resolve work. In-memory only, throwaway, feature-gated (`feature="layered_spike"`). New artifacts: `crates/warpui_core/src/keymap/layered_spike.rs` (the store + bench fixtures + index-sync tests), `crates/warpui_core/src/core/autotracking/layered_probe.rs` (the redesigned write-fan-out probe), `crates/warpui_core/benches/keymap_layered.rs` (the N×U bench), `+36` lines in `autotracking/mod.rs` (the raw `FANOUT_LOG` counter), `+5` in `keymap.rs`, `26` changed in `matcher.rs` (the feature-gated repoint). **`matcher_tests.rs` is NOT in the X1 commit's file diff** — reused verbatim as the parity harness.

**Run.**
- **(a) PARITY + (c) AUTOTRACKING:** `cargo nextest run -p warpui_core --features layered_spike` → **17 passed / 0 failed** = 8 `keymap::matcher::tests::*` (the verbatim `matcher_tests.rs`) + 4 `keymap::layered_spike::tests::*` (index-sync) + 5 `core::autotracking::layered_probe::*` (write-fan-out).
- **(b) LATENCY:** `cargo bench --features layered_spike --bench keymap_layered` → exit 0, all **30** criterion cells (12 `push_keystroke` + 18 `catalog_walk`) over N{200,2000} × U{0,1,50}.
- **(d) X13 production-scale diff:** **not-run** (honest, not fabricated) — the `warp` app build exceeded the time-box (see §4).

---

## 1. PARITY — verbatim `matcher_tests` green, ONE owned store, index correct *after mutation*

`parityPass = true` · `zeroParallelOwnedVecs = true` · `customIndexCorrectAfterResetAll = true` · `customIndexCorrectAfterModePack = true`.

### 1a. The 4→1 collapse holds with no re-introduced parallel owned vec

`LayeredKeymap` (`layered_spike.rs:206-227`) holds exactly **one** owned source-of-truth: `entries: Vec<LayerEntry>` (`:211`). A `LayerEntry` is `LayerTag{Base, UserOverride, ModePack}` + `ContextPredicate` + `Trigger` + `Arc<Action>` + an `Unbound` flag. Everything else is an **index into `entries`, not an owned binding**:

| Side structure | Type | Holds |
|---|---|---|
| `custom_index` | `HashMap<CustomTag, Vec<usize>>` | indices into `entries` |
| `suppression_index` | `HashMap<Trigger, Vec<usize>>` (keyed on **resolved** trigger) | indices into `entries` |
| `unbound_indices` | `Vec<usize>` | indices into `entries` |

The macOS custom-action surface `custom_action_bindings()` (`layered_spike.rs:361-368`) — the menu list that was a separately-owned `editable_custom_action_bindings` vec in production — is now served **ONLY** by `custom_index` materialized on the fly. `matcher.rs` routes the menu path straight to it. So the four-vec collapse is real: no parallel *owned* binding vector is reintroduced; `rebuild_indices()` (`:267-287`) runs per structural **mutation** only (register / inject / override / reset-all / mode-pack push+pop), **never per keystroke** — the hot path never rebuilds.

### 1b. Verbatim `matcher_tests.rs` passes against the layered backing (feature-ON parity)

All **8** `keymap::matcher::tests::*` pass feature-ON against the `LayeredKeymap`-backed `Matcher`: `test_matcher`, `test_editable_binding_matching`, `test_bindings_for_context`, the four X9 `test_tombstone_suppresses_{keystroke,standard,custom_primary_and_second_surface,custom_via_original_trigger_dual_check}`, and `test_inject_override_consistency_gate`. The file is included via `#[path]` in `matcher.rs:451`, was last modified by X9, and is **untouched by the X1 commit** (confirmed: absent from the `3889f1c5` file diff). Because the *same* behavioral suite is the gate against *both* backings, a feature-ON green is genuine parity, not a re-skinned assertion.

> **Honest caveat on feature-OFF.** The load-bearing direction — the layered backing reproducing the golden matcher behavior — is fully confirmed (feature-ON 17/17). The complementary feature-OFF run (baseline `Keymap`) was launched but stayed blocked behind the same heavy `cargo` build lock that blocked X13 within the time-box, so the feature-OFF green is asserted **structurally** (the parity harness is verbatim/unmodified, so feature-OFF is the unchanged production path) rather than re-executed in this run. The X9 results doc independently records the baseline `Keymap` suite green.

### 1c. `custom_index` stays correct *after* layer mutation (the real guard, not post-build only)

The "zero parallel owned vecs" claim *would* pass trivially if sync were only checked post-build — so the two **mutation** tests assert `custom_index` AFTER mutation, reading the real `custom_index` field (via `custom_index_for`, cloned, **not** recomputed from `entries`):

- **`custom_index_correct_after_reset_all`** — register base `TAG_A` (index len 1) → `inject_binding` a `UserOverride` for `TAG_A` (index grows to 2, override at idx 0, `layer_revision` bumped) → `reset_all()` (retain non-`UserOverride` + replay) → asserts `custom_index_for(TAG_A).len() == 1` AND the surviving entry replays the **base** action (`Act::A`), not the dropped override.
- **`custom_index_correct_after_mode_pack_push_then_pop`** — `push_mode_pack` contributes pack `TAG_A`+`TAG_B` (asserts counts, precedence ordering, and an explicit in-bounds `i < entries_len()` no-stale-index check) → `pop_mode_pack` removes exactly the pack (`TAG_A` back to 1, `TAG_B` key removed) → surviving `TAG_A` is the **base** `Act::B`, not the popped pack `Act::C`.

`suppression_index_keys_on_resolved_trigger` and `custom_index_correct_after_build` also pass (4/4). **Decisive mutation (skeptic):** deleting `self.rebuild_indices()` from `reset_all` and `pop_mode_pack` makes **both** mutation tests FAIL (`left:2 right:1`) — i.e. the tests genuinely detect the stale-parallel-index bug; reverted, diff empty.

---

## 2. LATENCY — p99 ≈ 5 µs at N=2000, layered/flat ≈ 1.0, suppression is indexed O(1)-per-binding (flat in U)

`latencyP99AtN2000`: `push_keystroke` p99 ≈ **5.1 µs layered** (U0 5.12 / U1 4.82 / U50 5.11) and ≈ **5.2 µs flat** — ~**40× under** the 200 µs input budget and ~100× under the 500 µs kill threshold. `layeredFlatRatio`: p50 ≈ **0.997** across U0/U1/U50 (criterion 100-sample per-call distribution).

Medians @ N=2000 (`target/criterion/*/estimates.json`):

| U | push_keystroke layered | push_keystroke flat | layered/flat |
|---:|---:|---:|---:|
| 0 | 4816.9 ns | 4830.6 ns | 0.997 |
| 1 | 4766.3 ns | 4774.7 ns | 0.998 |
| 50 | 5006.7 ns | 5031.7 ns | 0.995 |

`ratioGrowsWithU = false` · `suppressionIndexedO1 = true`. The catalog walk isolates the only net-new cost — Unbound suppression as U grows — by comparing the **indexed** path (`is_suppressed_indexed`, `layered_spike.rs:439`, a resolved-trigger hash-bucket lookup, O(1)-per-binding) against the deliberately-rejected **naive** O(N×U) scan (`is_suppressed_naive`, `:456`), both vs flat, at N=2000:

| path / flat | U0 | U1 | U50 | U1→U50 growth |
|---|---:|---:|---:|---:|
| **indexed** / flat | 1.00 | 3.31 | 3.46 | **×1.07 (+4.5%)** — flat in U |
| naive / flat | 1.01 | 1.33 | 15.26 | **×11.72 (+1047%)** — linear in U |

The naive path is the control that proves the bench *can* see O(N×U) (its U50 absolute ≈ 301 µs, near budget); the chosen indexed path is ~68 µs at U50 and **does not** scale in U. So `push_keystroke` is flat in U and the suppression index is the cheap O(1)-per-binding fix, not a nested scan with no fix.

> **Honest caveat (the U0→U1 step-up).** indexed/flat steps once from ~1.0 (U0) to ~3.3 (U1) and then stays flat. This is the **constant** per-binding hash-lookup cost that activates the moment the suppression map is non-empty (hashbrown skips hashing on an empty map at U0). It is **constant in U, not U-proportional**, so it does not contradict O(1)-per-binding — it is a one-time activation cost, not the O(N×U) growth the kill clause targets.
>
> **Caveat on predicate realism.** The bench builds every cell with **production-shallow** `shallow_predicate(i)` (`layered_spike.rs:555-564`) cycling `Identifier("View")` / `And(Identifier("A"), Identifier("B"))` / `Just(true)` — max depth 2. It does **not** synthesize deep And/Or/Not trees (corroborated: production has only ~5–7 `ContextPredicate::And` sites). The original design's deep-predicate fear was a misdirection; the bench correctly tests the real cost (U-scaling) instead.

---

## 3. AUTOTRACKING write-side fan-out — the load-bearing leg (trivially-true assertion DROPPED)

This is the leg the whole spike was **redesigned** around. The probe (`core/autotracking/layered_probe.rs`, `N_ROWS=300`) drives a **real** render and measures write-side fan-out through the production `render_view` + `track_update` path; all **5** probe tests pass.

### 3a. The trivially-true matcher-walk assertion was genuinely DELETED

The original probe asserted *"a matcher walk yields 0 settings-list invalidations"* — which is **true for ANY store** because `track_read` no-ops when `rendering_view` is `None`, and `push_keystroke` runs outside a render (`rendering_view = None`). A design that catastrophically over-invalidates would have passed it. That assertion is **gone**: grep over `autotracking/` finds *"matcher walk"* ONLY in the probe docstring (`layered_probe.rs:5,9`) explaining *why* it was deleted (*"settled by reading code (a grep), not measured — so it is DELETED"*). No test asserts 0 invalidations from a matcher walk; no push_keystroke-during-non-render leg exists.

### 3b. A real render is driven, and write fan-out is measured with a real counter

`render_rows` (`layered_probe.rs:52-56`) calls the **production** `super::render_view(window, row, ||read_dep(i))` for each of the 300 rows. `render_view` (`mod.rs:183-201`) sets `cache.rendering_view = Some(view)` before the callback (`:193`) and resets to `None` after (`:197`) — the real begin/end. `read_dep` does a real `Tracked` `Deref` → `track_read`, registering a dep **only because** `rendering_view` is `Some`. Write-side fan-out is counted two ways: the deduped re-render **set** (`take_invalidations_for_window`, a `HashSet`) AND the raw `track_update` event count (`take_fanout_log`, the `FANOUT_LOG` counter incremented inside `track_update` at `mod.rs:307-312`).

### 3c. Override fan-out number + bounded escape hatches + preview burst

`overrideFanOutBounded = true` (with an explicit number). The **chosen** design is a single shared `Tracked<u64>` revision counter:

| Granularity design | Override fan-out (re-render set) | Note |
|---|---:|---|
| **Single shared `Tracked<u64>` (chosen)** | **300 (= N_ROWS, the WHOLE list)** | EXPLICIT, asserted, documented, **accepted** — raw `track_update` fan-out also == 300 |
| per-row `Tracked` | 1 row | bounded escape hatch, measured |
| per-bucket (10 buckets / 300 rows) | 30 rows | bounded escape hatch, measured |

So one override write invalidates the whole list — but the number is **explicit and asserted** (`single_revision_counter`, `:66-95`: asserts deduped invalidations == 300 AND raw fan-out == 300), and the bench *also* measures the tighter alternatives it regresses from (per-row = 1, per-bucket = 30), proving fan-out **is** bounded under per-layer/per-name granularity. This is over-rendering (it re-renders the affected row plus the rest), not a *failure to re-render* — so it is not silent and is not the kill trigger.

`previewBurstNoFullListPerWrite = true`. The 5-write override-preview burst (`:159-194`) **dedups within a frame to N=300** (asserts == 300 AND < 1500 = 5×N): the raw `track_update` fan-out is 5×300 = 1500 events, but the re-render **set** is bounded to 300 by the invalidations `HashSet`. So the preview burst avoids per-write full-list invalidation **within a frame**.

**Decisive mutation (skeptic):** replacing `render_view(window,row,||read_dep(i))` with a bare `read_dep(i)` (no begin/end) flips **all 5** tests to `left:0 vs right:300/1/etc` (no deps registered ⇒ 0 fan-out ⇒ 0 invalidations). Reverted, diff empty. The green is load-bearing on the render actually driving dependency registration.

> **Documented residual (the 5th test).** `override_preview_per_drained_frame_reinvalidates_whole_list` (`:201-225`): across **drained** frames, each keypress re-invalidates the whole list (5×300 total). The within-frame dedup does **not** carry across frames — so the override-preview path **must be debounced** before rollout. This is flagged, **not decided**, and is the mandatory residual in §6.
>
> **Honest scoping note.** The probe models the three granularity designs with hand-built `Tracked<u64>` counters (single / per-row / per-bucket) rather than wiring the real `LayeredKeymap.layer_revision`. It uses the **real** production `Tracked` type and `render_view`, which is the correct experimental isolation of the granularity variable (the "simulated render" framing), but the real store's counter is not yet wired to the probe.

---

## 4. X13 production-scale diff — `not-run` (honest, not fabricated)

`x13DiffStatus = not-run`. The best-effort production-scale parity diff was launched (`cargo test -p warp --features warpui_core/layered_spike --lib x13_resolution_snapshot -- --ignored`) but the `warp` app build exceeded the time-box — the dependency tree was still compiling and the `warp` crate had not started after several minutes. It is recorded as **not-run, not fabricated**. Two facts make this a deferred-but-ready gap rather than a hole:

1. The `warp` app crate has **no native `layered_spike` feature** — the run had to thread it via the `warpui_core/layered_spike` dependency-feature CLI syntax, which pulls the whole heavy app build.
2. The frozen golden is **present and OS-matched**: `app/test_data/keymap/resolution_table.linux.txt` (459 lines, linux), ready for a future run.

Production-scale parity instead rests, for now, on the **verbatim `matcher_tests` passing feature-ON** (§1b) and the X13 clean-diff already recorded by the X9 results (the X1 store does not change the dormant tombstone semantics X9 froze). The X13 diff against the layered backing should be re-run before any production migration.

---

## 5. KEEP vs THROW

**KEEP (seed for the Phase-2 engine + X6 unified resolver):**
- The **`LayerTag` / `LayerEntry` / `LayeredKeymap` sketch** — ONE owned `Vec<LayerEntry>` tagged `Base` / `UserOverride` / `ModePack` + predicate + trigger + `Arc<Action>` + `Unbound`, as the single store all later axes resolve against (no re-forking into parallel vecs).
- The **single-walk indexed-`Unbound` suppression** (`suppression_index` keyed on resolved trigger, O(1)-per-binding) — this **is** the X6 unified-resolver primitive made concrete and shown flat in U; promote it as the suppression mechanism in the real resolver.
- The **derived `custom_index`** serving the macOS custom-action surface from indices into the single store (the X9 second-surface predicate generalizes onto it).
- The **redesigned multi-row write-fan-out probe** (`layered_probe.rs`: real `render_view` begin/end over N=300 + the `FANOUT_LOG` raw counter + the deduped invalidations `HashSet` + the single/per-row/per-bucket granularity comparison + the 5-write preview burst) — graduate it into the reactive-invalidation regression suite; it is the only instrument that catches over-invalidation.
- The **index-sync assertions** (`custom_index_correct_after_{build,reset_all,mode_pack_push_then_pop}`, `suppression_index_keys_on_resolved_trigger`) and the **four axis-operation tests** (register/inject-override, reset-all clear+replay, mode-pack push, mode-pack pop) as the **seed acceptance suite** for the production store.

**THROW:**
- The **cfg-gated `Matcher` repoint** (`matcher.rs` `feature="layered_spike"` field swap) — production lands the store unconditionally, not behind a throwaway feature flag.
- The **synthetic bench predicate/keymap scaffolding** (`layered_spike.rs:551-617` `bench_build` + the `shallow_predicate` generator + the disjoint `k{i}`/`t{i}` key scheme). Note it is production-**shallow** by design — there is **no** deep-predicate scaffolding to keep or discard (the original deep-And/Or/Not fear was a corrected misdirection); the perf signal it produced (flat-in-U indexed suppression) is the keeper, the generator is not.
- The throwaway **`layered_spike.rs` module** as a whole (the parallel `cfg`-gated store) — its *design* is the keeper; the spike file is scaffolding.
- The **original 1-row probe** (already replaced by the multi-row `render_view`-driven probe) — do not resurrect the trivially-true matcher-walk assertion.

---

## 6. Residual risk (carried, not dropped)

1. **ModePack-vs-UserOverride precedence is an Axis-4 product decision.** The `LayerTag` ordering the spike bakes in (does a vim mode-pack override a user's custom binding, or vice-versa?) passes the spike either way — but it is a product call X1 does **not** pin. A wrong choice ships wrong behavior with a green spike. Pin it in Axis-4 before the store is authoritative.
2. **The write-fan-out threshold is a judgment call, and the override-preview path MUST be debounced.** Whole-list invalidation per override is acceptable IFF the team accepts it for a rarely-edited settings page (the bench shows per-row=1 / per-bucket=30 escape hatches exist if not). But the override-**preview** per-keypress path re-invalidates the whole list on every drained frame (§3, 5th test) — this is **not** optional; the preview must debounce or the settings list thrashes on every keystroke during a live preview. The spike flags, it does not decide.
3. **macOS `menuNeedsUpdate` equivalence is validated only in isolation.** The `custom_index`-served menu surface's `BindingLens` equivalence is validated on Linux CI by the index-sync tests, **not** under live Cocoa. A Cocoa-specific ordering/identity assumption in the real menu builder (`[WarpDelegate menuNeedsUpdate]`) could still regress on mac. The non-risk reasoning (index maintained incrementally at registration, READ-not-rebuilt per menu open) is corroborated by code but the read-path equivalence is isolated, not live.
4. **N realism.** The bench grid is N{200,2000}; the actual registration count may be closer to ~60-files-worth than the design's ~397. If true, latency is even safer; but a future mode-pack explosion pushing N or U far past the grid would need the indexed-suppression assumption re-validated.
5. **X13 production-scale diff is not yet run against the layered backing (§4).** Re-run it (golden is ready) before any production migration treats parity as fully settled at scale.

---

## 7. Adversarial skeptic findings (4 attacked; none substantiated its trap)

1. **Autotracking false-green** (the load-bearing one) — trap **NOT confirmed**, high confidence. The trivially-true matcher-walk assertion was **deleted** (survives only in the docstring explaining why); the probe drives a real `render_view` begin/end over 300 `Tracked` reads and measures write-side fan-out via a real `track_update` counter; the decisive bare-`read_dep` mutation flips all 5 tests to `left:0`. The green is load-bearing, not hollow → **not** False-green-caught.
2. **Predicate misdirection** — trap **NOT confirmed**, high confidence. The bench uses production-shallow predicates (max depth 2) and the N×U grid; it measures the layered/flat ratio's growth in U (the real net-new cost), not deep-predicate eval. The naive control proves the bench can detect O(N×U); the indexed path does not exhibit it.
3. **Gameable unification** — trap **NOT confirmed**, high confidence. Both mutation tests assert `custom_index` *after* reset-all and after mode-pack push/pop (reading the real parallel structure, not recomputed); deleting `rebuild_indices()` makes both FAIL. The stale-index bug is genuinely exercised.
4. **Platform / Cocoa** — trap **NOT confirmed**, high confidence. No artifact claims mac menu correctness from a Linux test; the Cocoa read-path-equivalence-in-isolation residual is recorded (cross-axis False-green #4 / Residual-risk #3 and §6.3 here). Minor caveat: the commit-message results summary omits the Cocoa residual (without overclaiming it); this doc carries it.

---

## 8. KILL & verdict mapping (the pre-registered rules)

- **Autotracking false-green skeptic** substantiates the probe relied on the trivially-true matcher-walk assertion / never drove a real render? **No** — the assertion was deleted, a real render is driven, mutation proves load-bearing → **not** False-green-caught.
- **KILL fired?** **No.** (a) custom-action collapse + index correctness: ONE owned `entries` + derived `custom_index`, correct after mutation → not fired. (b) push_keystroke latency / U-growth: p99 ≈ 5 µs (~100× under the 500 µs kill threshold), flat in U, indexed O(1)-per-binding → not fired. (c) single `Tracked<u64>` write fan-out: whole-list 300 is over-render (not a failure-to-re-render) AND per-layer/per-name granularity (per-row=1, per-bucket=30) restores bounded fan-out, so the (whole-list **AND** no-granularity-fix) conjunction is false → not fired.
- **All hold for Trustworthy-Success?** Parity passes with zero parallel owned vecs + `custom_index` correct after reset-all AND mode-pack (§1); `push_keystroke` p99 < 200 µs at N=2000 AND ≤ 1.5× flat AND the layered/flat ratio does NOT grow with U (indexed O(1)-per-binding suppression) (§2); one override write invalidates an **explicitly documented + accepted whole-list number** (300, with bounded escape hatches measured) AND the 5-write preview burst avoids per-write full-list invalidation within a frame (§3). **Yes.**
- **Partial-kill considered:** the perf+parity legs pass and the write-fan-out is a documented (not silent) whole-list regression — but it is the **accepted whole-list number** the Trustworthy clause explicitly permits, with the within-frame preview condition met. The team-must-decide remainder (cross-frame preview debounce + fan-out threshold) is carried as a **mandatory residual** (§6.2), not a blocking partial-kill of the engine slice.

**→ TRUSTWORTHY-SUCCESS** (write-fan-out is explicit/accepted/bounded-escapable; override-preview debounce + X13-at-scale carried as residuals).

**buildDecision:** *commit the single `LayeredKeymap` store + indexed-`Unbound` suppression + derived `custom_index` as the Phase-2 engine base (the X6 unified resolver hosts it); ship the single shared `layer_revision` counter accepting whole-list settings-invalidation per override BUT debounce the override-preview path (mandatory); pin ModePack-vs-UserOverride precedence in Axis-4; re-run the X13 snapshot against the layered backing before migration.*
