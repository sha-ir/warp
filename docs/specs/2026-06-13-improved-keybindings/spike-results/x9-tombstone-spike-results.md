[← Back to Spike Designs index](../README.md) · [Spec: Cross-axis — X9](../cross-axis-sequencing.md) · [Gate: X13 resolution snapshot](./x13-resolution-snapshot-spike-results.md)

# X9 — First-class `Unbound` tombstone short-circuit · spike results

**Question.** Can a first-class `Unbound` *tombstone* binding — a higher-precedence entry that SUPPRESSES a separate, present, lower-precedence binding on the same key/action and SHORT-CIRCUITS the scan — be expressed through **ONE shared helper** across **all three** matcher `MatchResult` paths (`push_keystroke`, `match_standard`, `match_custom` incl. its `original_trigger` dual-check) without any path special-casing the tombstone decision; does a reader-**consistency gate** (matcher vs `get_binding_by_name` vs the macOS-menu `binding_for_custom_action_in_context`) agree after an inject override; and does the engine mutation leave **production resolution unchanged** against the frozen X13 golden?

**Verdict.** 🟡 **PARTIAL-KILL (second-surface-only).** The three primary `MatchResult` paths unify cleanly: every one routes the tombstone decision through the single helper `Matcher::resolve_matched_binding` (`matcher.rs:344-350`), which returns `MatchResult::Unbound` iff `binding.is_tombstone()`. `match_custom`'s `original_trigger` dual-check does **not** fork — both arms call the same helper. The full kill (a "primary path special-cased the decision") did **not** fire; nor did the consistency-gate kill (b) or the subsumption kill (c). **What fired is the pre-registered partial-kill clause:** the macOS-menu **fourth surface** `binding_for_custom_action_in_context` (`matcher.rs:251-279`) returns `Option<BindingLens>`, **cannot** return `MatchResult::Unbound`, and therefore **cannot** call the `MatchResult`-returning helper — it carries its **own** short-circuit site (`.filter(|b| !b.is_tombstone())`, `matcher.rs:278`). It reuses the **same** `is_tombstone()` predicate (`keymap.rs:267`), so the tombstone *decision* is shared; the *short-circuit shape* (Option vs MatchResult) is not. A clean single-helper unification was structurally impossible for this Option-returning surface. Per the framework's pre-registered rule — *"A second-surface-only special-case is a Partial-kill, not a full Kill"* — this is a Partial-kill: keep the per-surface unbind for the menu path, document the divergence. The consistency gate **passes** and the X13 regression diff is **clean**.

**Branch / worktree.** `sha-ir/spike-x9-tombstone` (worktree `/home/mhb/warp/.claude/worktrees/spike-x9-tombstone`, off `sha-ir/keybindings-draft`). HEAD `df7386d3` (`spike(keybindings): X9 Unbound tombstone kernel + consistency gate`) on top of `375a2269` (X13 net cherry-picked for the regression diff). Worktree clean.

---

## 1. The kernel result — ONE shared helper across all three paths (which special-cased?)

`suppressesAllThreePaths = true`. `pathThatSpecialCased` (among the three primary `MatchResult` paths) = **None**.

| Path | Call site | Tombstone decision | Special-cased? |
|---|---|---|---|
| `push_keystroke` (keystroke) | `matcher.rs:376` | `Self::resolve_matched_binding(&binding)` | No — shared helper |
| `match_standard` (standard action) | `matcher.rs:399` | `Self::resolve_matched_binding(&binding)` | No — shared helper |
| `match_custom` — primary `Trigger::Custom` arm | `matcher.rs:412` | `Self::resolve_matched_binding(&binding)` | No — shared helper |
| `match_custom` — `original_trigger` dual-check arm | `matcher.rs:420` | `Self::resolve_matched_binding(&binding)` | No — same helper, no fork |

The helper is the single point that maps the predicate to the variant:

```rust
fn resolve_matched_binding(binding: &BindingLens) -> MatchResult {
    if binding.is_tombstone() {
        MatchResult::Unbound          // suppress any lower-precedence binding on this key/action
    } else {
        MatchResult::Action(binding.action.clone())
    }
}
```

`MatchResult::Unbound` is a **new** enum variant that pure LIFO of normal bindings can never produce (LIFO yields only `Action(..)` or `None`). The per-path match-keys differ (keystrokes / standard action / custom tag), but the tombstone decision is key-independent, so no path is forced into per-path unbind logic. Iteration order is corroborated in `keymap.rs`: `editable_bindings()` walks `.rev()` (LIFO) and precedes fixed bindings; `inject_binding` appends last, so an injected tombstone is the highest-precedence match — it would otherwise win as an `Action`, which is exactly why the short-circuit is load-bearing. Confirmed by 4 passing tombstone tests (one per path + the second-surface coverage).

### The divergence that DID fire — the macOS-menu fourth surface (partial-kill)

`binding_for_custom_action_in_context` (`matcher.rs:251-279`) is **not** one of the three `MatchResult` paths. It returns `Option<BindingLens>` for the macOS menu lookup, reads a *different* source (`custom_action_bindings()`), and honors tombstones via its own short-circuit:

```rust
    .find(move |binding| binding.context_predicate.eval(context))
    // ... if the highest-precedence match is an Unbound tombstone, return None ...
    .filter(|binding| !binding.is_tombstone())   // matcher.rs:278 — distinct short-circuit SITE
```

It shares the ONE `is_tombstone()` predicate (so the *decision* is unified), but because it returns `Option` it cannot call `resolve_matched_binding`. This is a divergence in short-circuit **shape**, not a hidden special-case of the tombstone **decision** — and it is documented in-code (`matcher.rs:268-278`). The kill framework deliberately counts this surface: the kill (a) headline is about unifying through *"ONE shared HELPER"*, and this surface provably does not use that helper, so the **partial**-kill clause fires while the three primary paths stay unified.

---

## 2. Consistency-gate result — PASS (no name-reader half-override)

`consistencyGatePass = true`. `test_inject_override_consistency_gate` (matcher_tests.rs) registers `copy → Copy::Original`, asserts a baseline where all **three** readers return `Original`, then injects `Copy::Override` at highest precedence and asserts all **three** now return `Override`:

- **matcher** `match_custom` → `Override`;
- **`get_binding_by_name`** → `Override` (no name-reader half-override);
- **macOS-menu** `binding_for_custom_action_in_context` → `Override`.

The gate is **not** matcher-only — it explicitly covers both name-readers the trap named. The pass is real plumbing, not a faked green:

- `get_binding_by_name` now iterates `indices.iter().rev()` (latest-wins, `keymap.rs:407-414`) so it agrees with the matcher's LIFO precedence;
- `inject_binding` **dual-appends** — to `editable_custom_action_bindings` when `Trigger::Custom` AND to `editable_bindings` (`keymap.rs:426-438`) — keeping the separate macOS-menu vector in sync;
- `editable_custom_action_bindings()` iterates `.rev()` (`keymap.rs:518-524`), so the menu surface also reads latest-wins.

Load-bearing check (skeptic mutation): reverting `get_binding_by_name` to forward/earliest ordering makes the gate FAIL with `left: Original, right: Override` — precisely the half-override the trap describes. The trap's premise (earliest-ordering + a separate custom-action vector) was true of the *original* code; X9 closed both surfaces and the gate guards them. **As the kill (b) prediction warned, override-via-inject is NOT free** — it required exactly this reader plumbing (the code comment states verbatim *"override via inject is NOT free"*) — but the divergence was fixed, so the gate passes.

---

## 3. X13 REGRESSION DIFF — CLEAN (the engine-mutation gate)

`x13DiffClean = true`. This is the gate that proves the hot-loop mutation did not move any production winner.

- **Command (no BLESS):** `CARGO_BUILD_JOBS=6 cargo test -p warp --release x13_resolution_snapshot -- --ignored --nocapture`
- **Output:** `X13: snapshot matches golden (452 rows)` · `test result: ok. 1 passed; 0 failed` · `EXIT_CODE=0`
- **No winner flipped** vs the committed golden `app/test_data/keymap/resolution_table.linux.txt` (452 rows). Production resolution is **unchanged**, reproduced stable.
- **Not theater:** perturbing a winner cell (line 8, the `agent_input` `Custom(17)` editable:terminal:copy row) drove the diff **RED** (exit 101, naming the drifted winner); restoring returned green.

> Identifier correction: the package is **`warp`** (`app/Cargo.toml` name = `"warp"`, default-run `warp-oss`), **not** `app`; the test fn is **`x13_resolution_snapshot`** in `app/src/keymap_resolution_snapshot_tests.rs`. The task's command named `-p app`; the corrected `-p warp` was used (the file's own header documents `-p warp`).

**Why clean is the EXPECTED, structurally-grounded result (static corroboration).** The tombstone mechanism is **inert in production**: `as_tombstone()` has **zero** non-test call sites; every production registration path sets `tombstone: false` (`FixedBinding` @ `keymap.rs:693-694`, `EditableBinding::new` @ `keymap.rs:717`). So `is_tombstone()` is false for every production binding → `resolve_matched_binding` always takes the `Action` branch (`Action(clone)`, byte-identical to pre-X9) and the second-surface `!is_tombstone()` filter is a no-op that passes all production bindings. The helper can only fire `Unbound` for `inject_binding(... .as_tombstone())`, which is test-only. The X13 diff therefore confirms what the static read predicts: the kernel adds a dormant capability, not a live behavior change.

---

## 4. Pre-registered code-read finding — mutate is RETAINED; inject does NOT subsume mutate

`update_custom_trigger` is **left untouched** (verified: it is absent from the `df7386d3` diff; only `get_binding_by_name` switched to `.rev()`). The spike records **mutate retained** as a *code-read* finding, not a build outcome, and **no keystroke/matching test claims subsumption**:

- **Why a green match test proves nothing about subsumption:** `track_read` is rendering-view-gated and `track_update` fires only for views that read that exact `TrackedId` during a render (`autotracking/mod.rs:272-296`); the entire reactive-invalidation graph is **dormant** in `#[cfg(test)]` unit tests. A passing match/keystroke test exercises resolution, not invalidation.
- **Why subsumption is settled NO by identity:** `inject` mints a **new** `TrackedId`; readers of the *original* id (settings rows, hint badges, the macOS menu via `as_lens`) go **stale**. `inject` is a full *override* of resolution, not a substitute for `update_custom_trigger`'s reactive `Tracked` invalidation.
- The spike design pre-empted this trap and **cut** the offending success signal (`cross-axis-sequencing.md:86,91`): *"success_signal #4 (\"test_custom_triggers passes re-expressed as inject ⇒ inject subsumes mutate\") is structurally false … the whole invalidation graph is dormant — green proves nothing about the reactive path."* Kill (c) does **not** fire — the keystroke test only shows an injected tombstone suppresses a separate lower-precedence binding via the shared helper.

---

## 5. Tests (what was run)

**KERNEL** (`cargo nextest run -p warpui_core keymap::`): 23 run, **23 passed**, 274 skipped. The 5 X9 tombstone/gate tests all PASS:

| Test | Surface exercised |
|---|---|
| `test_tombstone_suppresses_keystroke_via_shared_helper` | `push_keystroke` |
| `test_tombstone_suppresses_standard_via_shared_helper` | `match_standard` |
| `test_tombstone_suppresses_custom_primary_and_second_surface` | `match_custom` primary arm + macOS-menu second surface |
| `test_tombstone_suppresses_custom_via_original_trigger_dual_check` | `match_custom` `original_trigger` dual-check + second surface |
| `test_inject_override_consistency_gate` | matcher vs `get_binding_by_name` vs `binding_for_custom_action_in_context` agree on `Copy::Override` |

Each tombstone test (1) seeds a SEPARATE lower-precedence binding, (2) asserts baseline `MatchResult::Action`, (3) injects a higher-precedence `.as_tombstone()`, (4) asserts `MatchResult::Unbound`. Two targeted skeptic mutations confirm dependence on the novel mechanism: neutering `resolve_matched_binding` to ignore `is_tombstone` → all 4 tombstone tests FAIL (each gets `Action` instead of `Unbound`); making `match_standard` SKIP tombstones and continue the scan → it falls through to the separate lower-precedence fixed `Close` binding (`Action(Close)`) instead of `Unbound` — directly proving suppression of a SEPARATE binding is what is asserted.

**X13** (release, no BLESS): 1 passed, 0 failed; `X13: snapshot matches golden (452 rows)`; exit 0 (see §3).

---

## 6. Adversarial skeptic findings (5 attacked; none defeated the build)

1. **Subsumption (`inject` subsumes `mutate`?)** — trap AVOIDED. The build never claims subsumption from a match test; `update_custom_trigger` is untouched; mutate retained as a code-read note (§4). High confidence.
2. **Proxy (a green test merely re-confirms LIFO + `context_predicate.eval`?)** — trap AVOIDED. `MatchResult::Unbound` is unreachable by LIFO; the tombstone even carries its own action, so without the short-circuit LIFO would return `Action`. Mutation tests bite. High confidence.
3. **Name-reader (matcher-only half-override?)** — REFUTED. The gate asserts both name-readers agree post-inject; the half-override fails only if the `.rev()` plumbing is reverted (§2). High confidence.
4. **Faked-modal (dynamic Modal vocabulary papered over?)** — trap AVOIDED. The dynamic mode-pack vocabulary residual is recorded honestly (it lives in X7's results / Axis-5/X10); production `Context.set`/`map` stay static, so FSA dynamic submode strings do not flow end-to-end here. Carried as residual #1 below. High confidence.
5. **X13-regression (clean diff asserted without running, or stale binary?)** — trap AVOIDED. The diff was re-run at HEAD `df7386d3` against the frozen golden, green and reproduced, with a RED-on-perturb counter-check (§3). High confidence.

---

## 7. KEEP vs THROW

**KEEP (seed A3-Q13 / A3-Q5 / X6):**
- The first-class **`MatchResult::Unbound` tombstone variant** + the `is_tombstone()` predicate + `as_tombstone()` constructor — the genuine novelty (suppress-and-short-circuit, not LIFO).
- The **shared short-circuit helper** `resolve_matched_binding` unifying the three primary `MatchResult` paths, **plus the documented per-surface divergence** for the Option-returning macOS-menu path (`binding_for_custom_action_in_context` filters on the same predicate; keep its per-surface unbind, do not force a fake unification).
- The **reader-consistency assertions** (`test_inject_override_consistency_gate`) + the `get_binding_by_name` `.rev()` latest-wins fix + `inject_binding` dual-append — the proof that inject is a FULL override across matcher and both name-readers (seeds the live-apply/override path for A3-Q13/A3-Q5 and X6's unified resolver).

**THROW:**
- A `BindingLayer` enum / explicit `(layer, recency)` precedence rewrite — not needed; LIFO + tombstone short-circuit suffices for the override semantics tested here.
- The in-test `Modal` predicate scaffolding (no production mode-pack registration was built).
- `mutate → inject` migration: do **not** replace `update_custom_trigger` with inject — subsumption is settled NO by `TrackedId` identity (§4); keep mutate for reactive invalidation.

---

## 8. Residual risk (carried, not dropped)

1. **Dynamic Modal vocabulary is faked / unbuilt.** Production `Context.set`/`map` remain static `&'static str` (the X7 leaf-`Cow` change is what would carry runtime atoms, and even that is leaf-only). FSA-emitted submode strings do not flow end-to-end; the dynamic `Modal:{engine}:{submode}` vocabulary is an Axis-5/X10 + A4-Q1 design item, **not** validated by this spike.
2. **The real ~109-site clobber needs the X13 golden — which we diffed.** Production has no tombstone injector today, so the kernel is dormant; the moment a live override path injects tombstones at scale (the ~109 custom-action override sites), the resolution table can move. The X13 golden is the gate for that change, and the clean diff here only proves the *dormant kernel* is inert — re-diff against the golden when a live injector lands.
3. **X12 frame budget.** The tombstone scan rides the existing `bindings()` LIFO walk (no extra pass), so it adds no per-dispatch allocation today; but resident `Cow::Owned` runtime atoms (X7 residual) and a populated override layer are the X12 interned-id / frame-budget kill-branch trigger — out of scope here, must be re-measured before a hot-path rollout.
4. **Second-surface shape divergence is permanent by type.** The macOS-menu path will keep its own `!is_tombstone()` filter because it returns `Option`; this is a documented, tested divergence, not a bug — but any future refactor unifying the surfaces must preserve the second short-circuit site or the menu silently shows a tombstoned binding.

---

## 9. Verdict mapping (the pre-registered rules)

- X13-regression skeptic refuted (diff not run / winners flipped)? **No** → not False-green-caught on the engine gate.
- Name-reader/consistency skeptic refuted OR consistency gate failed? **No** (`consistencyGatePass = true`) → not False-green-caught on half-override.
- Tombstone short-circuits all three paths via ONE helper AND gate passes AND `x13DiffClean`, with **no** surface diverging? Three primary paths yes — **but** the second surface (`binding_for_custom_action_in_context`) special-cases in shape → drops out of clean Trustworthy-Success.
- Only the SECOND surface special-cases while the three primary paths unify → **PARTIAL-KILL** (keep per-surface unbind for the menu path; document). ✅ This is the firing clause.
- No primary path special-cased → not a full Kill.

**→ PARTIAL-KILL.**
