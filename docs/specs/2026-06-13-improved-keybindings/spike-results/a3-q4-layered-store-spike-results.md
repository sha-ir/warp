[← Back to Spike Designs index](../README.md) · [Plan: A3-Q4 layered store](./a3-q4-layered-store-plan.md)

# A3-Q4 — per-layer-chained store · spike results

**Question.** Is variant (b) — per-layer-chained — structurally sufficient, can the shadow custom-action surface be folded coherently (A3-Q8), and does Tracked-invalidation identity / live-apply survive the refactor (A3-Q7)?

**Verdict.** ✅ **SUCCESS on all four criteria.** The `Keymap` was refactored into per-layer `LayerStore`s chained lazily in precedence order; the shadow custom-action collections were **removed** and replaced by a derived projection (Option A); live-apply invalidation is preserved (single re-render); and the **X13 golden stayed green (452/452 rows unchanged)** — the refactor is semantics-preserving.

**Branch.** `worktree-spike-a3-q4-layered-store` (X13 commit cherry-picked, then refactored on top). `matcher.rs` and all external consumers are **untouched** — every method signature was preserved.

---

## 1. Results

| Check | Outcome |
|---|---|
| Refactor compiles (`cargo check -p warpui_core --tests`) | ✅ |
| 18 existing `keymap` tests | ✅ no regression |
| `a3q4_shadow_coherence_derived` (A3-Q8) | ✅ menu/UI and dispatch surfaces agree on the winner, before/after/removal of an override |
| `a3q4_ordering_editable_beats_fixed_across_layers` | ✅ global editable>fixed survives layering (the within-split rule) |
| `a3q4_live_apply_invalidation_identity` (A3-Q7) | ✅ **count==2** — editing the override invalidates the render-subscribed view exactly once |
| **X13 resolution diff** (`cargo test -p warp -- --ignored x13_resolution_snapshot`) | ✅ **"snapshot matches golden (452 rows)"** — no unrelated winner moved |

## 2. What was built

- **`LayerStore`** — today's flat `Keymap` body scoped to one layer (`fixed`, `editable: Vec<Tracked<EditableBinding>>`, `editable_by_name`), with per-layer `register_*` / `editable_bindings()` / `fixed_bindings()` / `get_binding_by_name` / `update_custom_trigger`.
- **`Keymap = { default_layer, user_layer, modepack_layer }`** — `default_layer` = built-ins; `user_layer` = overrides/user bindings; `modepack_layer` = an **explicit empty stub** for Axis-4, chained at highest precedence so the N-layer chain shape is exercised.
- **`bindings()` / `editable_bindings()`** chain layers **within each split** (`editable across layers` then `fixed across layers`), preserving the historical global "all editable beat all fixed" ordering as a **nameable, zero-`Box`, fully-lazy** iterator type — no collect/sort.
- **`custom_action_bindings()` is now a derived filter of `bindings()`** (Option A): the two shadow `Vec`s and the dual-write are **gone**.

## 3. Findings

### 🟢 Structural leg — variant (b) is sufficient; laziness "kill" refuted

The per-layer chain over a fixed layer count is a statically-known, lazy iterator (`impl Iterator`, no `Vec`/`Box`). Variant (a) — a single globally `(layer,recency)`-ordered stream over the heterogeneous editable/fixed collections — is the one that *cannot* be emitted lazily (it needs a per-call collect + stable sort); a ~5-min attempt to write it lazily fails on the heterogeneous element types. So (b) wins on **structure**, exactly as hypothesized. The **ordering trap is real and now tested**: chaining whole layers (rather than within each split) would let a user-layer *fixed* binding beat a default-layer *editable* one — a silent precedence change the `a3q4_ordering_*` test guards against.

### 🟢 A3-Q8 fold — Option A removes the desync surface *and* fixes a latent bug

`custom_action_bindings() = bindings().filter(is_custom)` where `is_custom` tests **both** `trigger` and `original_trigger` for `Trigger::Custom` (matching `match_custom`'s dispatch filter). Because both the menu/UI surface and the dispatch surface now read **one** ordered source, they cannot disagree on the winner — coherence is **structural, not maintained by hand**. This also **fixes a latent bug** the old shadow had: a binding overridden *to* `Trigger::Custom` was found by dispatch but missing from the shadow (menu); the derived filter catches it via the current trigger. (Doesn't occur in production today — callers pass Keystrokes — but the fold neutralizes it.) The former macOS `menuNeedsUpdate` optimization is dropped; A3-Q20 showed the resolver scan is low-µs, so no cache was needed. If a future profile disagrees, re-add a **generation-invalidated** cache rebuilt from `bindings()` — never a second mutable copy.

### 🟢 A3-Q7 invalidation identity — preserved, and the precise condition is now pinned

Live-apply survives because the override stays on a **single `Tracked` instance**: `get_binding_by_name` resolves `default_layer.editable[idx]` and `update_custom_trigger` mutates that **same** instance in place, so the render-time `track_read(id)` edge and the event-time `track_update(id)` hit one `TrackedId` → the subscribed view is invalidated exactly once (`count==2`). **This is the design recommendation, not just an observation:** the override must remain single-instance. The spec's kill#2 — splitting base (default-layer) and override (a *cloned* user-layer `Tracked`) into two instances — would make `get_binding_by_name` read `id_D` while the edit mutates `id_U`, leaving the view never invalidated (`count==1`); that is the A3-Q7 escalation (layer-level revision counter / re-subscription). We kept the override single-instance, so we did **not** trip it.

> **Override-location nuance (honest).** The spec framed (b) as "move the override write *into* the user layer." We kept the override as an in-place field mutation on the layer that holds the binding (today: `default_layer`); the `user_layer` is present and chained (it carries user-*added* bindings and is exercised by the ordering test). Physically relocating an override into a separate user-layer `Tracked` is achievable only two ways without breaking A3-Q7: **move** the existing `Tracked` (preserving its id), or add a revision counter. Cloning breaks it. Since single-instance overrides satisfy every success criterion *and* avoid the kill, that is what we shipped; clean user-layer relocation is an A3-Q3 (layering-model) decision, not required by this layout spike.

### 🟢 Read-barrier off the hot path (criterion 4)

Established by **A3-Q20** (verified: `track_read` records edges only when `rendering_view == Some`, set only in `render_view`; `dispatch_keystroke → push_keystroke` is never render-wrapped). The refactor does **not** touch `track_read`/`render_view`/`push_keystroke`, so the premise holds unchanged — per-keystroke resolution is a plain O(n) scan (A3-Q20 bounded it at ~16µs p99).

## 4. Keep vs throw

- **KEEP (all of it — production-bound):** the `LayerStore` + layered `Keymap`, the within-split chained `bindings()`, the derived `custom_action_bindings()`, and the 3 tests (the live-apply / shadow / precedence regression net the axis lacked — *zero* tests previously exercised the Custom-trigger shadow or identity-through-render).
- **THROW:** nothing. The `modepack_layer` is an intentional empty stub.

## 5. Residual risks / scope

1. **Two real layers + empty stubs.** `user_layer` is populated only by the ordering test; `modepack_layer` is always empty. True 3-layer precedence (`default < user < modepack`) and "modepack rebinds an unbound key" need Axis-4 mode-packs.
2. **Unbound/suppression reserved, not built** (A3-Q5/Q9/Q11). The layout leaves room for a per-layer tombstone entry, but `Trigger::Unbound` and the 3 match-fn suppression edits are out of scope.
3. **Override relocation deferred** to A3-Q3 (see the nuance above); the layout supports it but the spike ships single-instance overrides.
4. **macOS menu perf** now filters the full `bindings()` rather than a pre-filtered shadow — bounded sub-µs by A3-Q20, but unmeasured on the exact menu path; re-add a derived cache if a profile flags it.

## 6. Unblocks

Settles **A3-Q4** with a structural pick (per-layer-chained) plus a proven shadow-fold (A3-Q8) and a preserved live-apply path (A3-Q7), all backed by the X13 golden showing production resolution is byte-identical. The layered store is the foundation X1 (the LayeredKeymap capstone) serves, and it reserves room for the Unbound primitive (A3-Q5/Q9/Q11).
