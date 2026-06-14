[← Back to Spike Designs index](../README.md) · [Spec: Axis 3 — A3-Q4](../axis-3-layering-precedence-unbinding.md)

# A3-Q4 — per-layer-chained store · execution plan

**Date:** 2026-06-13
**Status:** Plan, pending user approval before refactoring the engine
**Branch (to create):** `sha-ir/spike-a3-q4-layered-store`, **cherry-picking the X13 commit** so the refactor diffs against the frozen golden.
**Spike kind:** Engine refactor of `keymap.rs` (variant **b** only) + 3 targeted tests + the X13 resolution diff.
**Grounded by:** workflow `wm8c8c6ve` (layer-store shape, shadow dual-write / A3-Q8, Tracked invalidation identity / A3-Q7).

---

## 1. Goal

Pick the **per-layer-chained** store layout and prove two things a compile is genuinely needed for: (A3-Q8) the shadow custom-action collections can be **folded** so `custom_action_bindings()` and `bindings()` never disagree on the winner; and (A3-Q7) **Tracked-invalidation identity** survives the override moving into a user layer, so the settings view's live-apply still fires. Win on **structure**, not a perf ratio (A3-Q20 already bounded perf).

## 2. Grounded reality that shapes the build

| Fact (verified) | Consequence |
|---|---|
| `Keymap` = exactly 5 fields: `fixed_bindings`(26), `editable_bindings`(27, `Vec<Tracked<EditableBinding>>`), `editable_bindings_by_name`(30), `fixed_custom_action_bindings`(36), `editable_custom_action_bindings`(37) | Refactor target is a `LayerStore` holding those 5, with `Keymap = { default_layer, user_layer, modepack_stub }` |
| **Precedence today = ALL editable (rev) THEN ALL fixed (rev), globally** — no layer/recency field exists | ⚠️ **Ordering trap:** must layer **within each split** (`editable = user.editable ++ default.editable`, then `fixed = user.fixed ++ default.fixed`), NOT chain whole layers — else user-layer *fixed* would beat default-layer *editable*, a silent precedence change |
| Laziness "kill" is **refuted** | Explicit `.chain()` over a fixed layer count is a nameable, zero-`Box`, fully-lazy type; dynamic-N (Axis-4) uses `flat_map` over homogeneous per-layer iterators, still lazy. Only **variant (a)** (one global (layer,recency) stream) forces collect+sort — recorded as a ~30-min type/alloc fact, not built |
| `update_custom_trigger` (422-433) **dual-writes** the override into `editable_custom_action_bindings` (separate `Tracked` clones, L412) AND `editable_bindings` (canonical). `custom_action_bindings()`(474) reads the **shadow**; `bindings()`(454) reads the **canonical** | The two surfaces agree *only* via the hand-written dual-write — the A3-Q8 desync surface |
| `match_custom`(matcher 363, dispatch) uses `bindings()`; `binding_for_custom_action_in_context`(matcher 246, menu/UI) uses `custom_action_bindings()` | Same query, two stores — divergence = menu shows one shortcut, dispatch runs another |
| `get_binding_by_name`(379-385) and `update_custom_trigger` loop-2 (430-432) touch the **same** `editable_bindings[idx]` `Tracked` → identity holds **today**; `TrackedId` is **per-value** (per `Tracked::new`), `Deref→track_read(id)`, `DerefMut→track_update(id)` | A split base/override into two `Tracked` instances breaks live-apply (A3-Q7 kill) |
| 🔴 `render_view`/`take_invalidations_for_window` are **`pub(super)`-to-`core`**; `keymap` is crate-root; `TrackedId` has **no accessor** | The invalidation test **cannot** live in `keymap_tests.rs`. It runs at the **`App::test`/AppContext** level (mirroring `core/.../autotracking_tests.rs::test_update_view_dependency_rerenders`); identity witness = **exactly one re-render (count==1)**, since `count==1` ⇒ same id (split ⇒ `count==0`) |
| 🔴 **Zero** existing tests use `with_custom_action`/`Trigger::Custom`/`custom_action_bindings()` — the shadow path is untested; `test_custom_triggers` uses Keystroke triggers and never populates the shadow | The shadow-coherence kill test **must** register a Custom-triggered editable binding, or it's a built-in false-green |

## 3. The refactor (variant b)

```
struct LayerStore { fixed, editable: Vec<Tracked<EditableBinding>>, editable_by_name, /* custom surface: see §4 */ }
pub struct Keymap { default_layer: LayerStore, user_layer: LayerStore /*, modepack_layer: stub */ }

fn editable_bindings(&self) -> impl Iterator =  user.editable_bindings().chain(default.editable_bindings())
fn bindings(&self)          -> impl Iterator =  self.editable_bindings().map(as_binding)
                                                  .chain(user.fixed_bindings().chain(default.fixed_bindings()))
```
- `register_fixed_bindings`/`register_editable_bindings` keep their exact bodies but target `default_layer` (built-ins).
- `update_custom_trigger` routes the override into `user_layer`.
- `get_binding_by_name` resolves through the layers to the **same** `Tracked` the user-layer override mutates (the A3-Q7 invariant).

## 4. The one real design fork — shadow-fold approach

**Option A — derive (recommended).** Make the Custom surface a **pure projection**: `custom_action_bindings() = resolve_bindings().filter(is_custom)`, where `is_custom` tests **both** `trigger` and `original_trigger` (matching `match_custom`). The shadow `Vec`s and the dual-write **disappear** → A3-Q8 desync impossible by construction, and it **fixes the latent live-apply bug** (today the shadow's separate `Tracked` clones mean a menu subscription isn't invalidated by a canonical edit). If the macOS `menuNeedsUpdate` perf intent (the comment at keymap.rs:32-35) still needs a materialized index, make it a **generation-invalidated cache** rebuilt from `resolve_bindings()`, never mutated directly. *Trade-off: touches `custom_action_bindings()` + the macOS path; the custom subset is small and A3-Q20 showed the scan is µs, so a cache is likely unnecessary.*

**Option B — per-layer shadow (fallback).** Keep per-layer shadow `Vec`s in `LayerStore`; `update_custom_trigger` does a per-layer dual-write into `user_layer.{editable, shadow}`. Preserves the macOS optimization verbatim; the dual-write persists (per-layer) and A3-Q8 coherence is *tested*, not *structural*.

**Plan:** attempt **A**; if the derived surface can't preserve the menu winner or regresses perceptibly (it shouldn't), fall back to **B** and record it as the spec's kill#1 escalation.

## 5. Tests + the X13 diff

1. **Shadow-coherence** (`keymap_tests.rs`): register a **Custom-triggered editable** binding (`.with_custom_action(tag)` — populates the shadow), `update_custom_trigger(name, Some(Keystrokes))` into the user layer (and `None` for removal); assert `bindings()`-resolution and `custom_action_bindings()`-resolution return the **same winner** (BindingId + resolved `trigger` + `original_trigger`), **before and after**, in a matching and a non-matching context.
2. **Invalidation-IDENTITY** (`core/…autotracking`-level via `App::test`, **not** keymap_tests): a `View` whose `render()` calls `app.get_binding_by_name(NAME).trigger` (records the dep edge through `AppContext::render_view`); register the binding + `set_custom_trigger(NAME, t1)` to establish the user-layer override **and subscribe**; force first render; **outside render** `set_custom_trigger(NAME, t2)`; assert the render counter incremented by **exactly 1**. (`count==1` is the identity proof; a split base/override design yields `count==0`.)
3. **Read-barrier-off-hot-path** (`keymap`/`matcher` test): `push_keystroke` **outside** `render_view` inserts **zero** dep edges (`rendering_view==None` gates `track_read`) — documents that per-keystroke perf is a plain O(n) scan (A3-Q20).
4. **X13 resolution diff** (the regression net): after the refactor, re-run the cherry-picked X13 capture in diff mode (`cargo test -p warp -- --ignored x13_resolution_snapshot`). The refactor is **semantics-preserving**, so the 452-row golden must stay **green**; a RED row = an unintended winner flip (e.g. the ordering trap). *(X13's capture exercises only the default layer — empty user layer — so the user-layer ordering trap is covered by Test 1's sibling assertion below, not X13.)*

   **Ordering-trap assertion** (in Test 1's file): register a **default-layer editable** and a **user-layer fixed** binding on the same trigger; assert `bindings()` yields the **editable** first (global editable>fixed survives layering).

## 6. Success / kill

- ✅ **Success:** (1) `bindings()` compiles as a lazy chain across layers with **no** Vec collect/sort (variant-a's loss recorded as a type fact); precedence == chain order with editable>fixed preserved globally. (2) Shadow-coherence green (custom surfaces agree post-override). (3) Invalidation-identity green (`count==1` single re-render). (4) Read-barrier-off-hot-path green. (5) **X13 golden stays green** (no unrelated winner moved). Only 2 real layers + a stub modepack are exercised — labelled as such.
- 🛑 **Kill:** (1) the fold can't keep the custom surfaces coherent without per-layer shadow duplication, or desyncs → STOP, escalate to A3-Q8 (adopt Option B, document). (2) Invalidation identity breaks (split `Tracked` → `count==0`) → STOP, escalate to A3-Q7 (layer-level revision counter / re-subscription); do **not** ship the split layout.

## 7. Out of scope (explicitly deferred)

`Trigger::Unbound` + the first-match suppression edits across the 3 match fns are **A3-Q5/Q9/Q11** — *not* built here, but the layout must **reserve room** for a per-layer Unbound/tombstone entry. No criterion, no perf bench (A3-Q20 owns perf). Cross-OS, true 3-layer precedence (needs Axis-4 modepacks), and nameless fixed-binding disables (A3-Q15/Q2) remain follow-ons.
