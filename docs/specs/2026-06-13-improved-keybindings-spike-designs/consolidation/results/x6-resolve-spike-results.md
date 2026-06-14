[← Back to Spike Designs index](../README.md) · [Spec: Cross-axis — X6](../cross-axis-sequencing.md) · [Builds on: X9 tombstone](./x9-tombstone-spike-results.md) · [Leaf type: X7 leaf-Cow](./x7-leaf-cow-spike-results.md)

# X6 — Unified scope-tagged `resolve()` walk over `keymap.bindings()` · spike results

**Question.** Can ONE loop over the single shared source `keymap.bindings()` host BOTH (a) the keystroke path's keep-scanning-after-partial-match (`retain_pending`) AND (b) Standard/Custom first-match-wins, with suppression expressed as ONE primitive carrying a binding-side **SCOPE TAG** (key-scoped vs action-identity-scoped) dispatched by **binding metadata** rather than by **query kind** — such that a tombstone suppresses across Keystroke/Standard/Custom through one suppression check, WITHOUT re-introducing a separate `resolve_keystroke` special-case; does the A3-Q5 custom-unbind leak return `None` through that unified `resolve()`; AND does the same suppression/leak decision generalize to the SECOND resolution surface `binding_for_custom_action_in_context` (the macOS-menu `original_trigger` path)?

**Verdict.** ✅ **TRUSTWORTHY-SUCCESS (second surface shape-diverges, recorded).** All five `cfg(test)` tests pass on a forced clean rebuild and again under nextest. The WALK genuinely unifies: ONE loop over `keymap.bindings()` (`resolve_spike.rs:243`) hosts the keystroke `retain_pending` keep-scanning leg AND Standard/Custom first-match-wins AND the scope-tagged suppression early-stop, with **no** separate `resolve_keystroke` (grep confirms the symbol exists only in doc comments asserting its deliberate absence). Suppression is ONE scope-tagged primitive — `suppression_for` → `scope_of` → `apply` — that decides purely from **binding-side** metadata (`is_tombstone()`; `Trigger::Empty && original_trigger.is_some()`) and derives the scope tag from the **matched** trigger, never the query kind; the tri-kind test exercises this across **distinct** keys/actions (`ctrl-k`, `StandardAction::Close`, `Custom(7)`), never a single shared key. The A3-Q5 leak fixture (`custom_trigger=Empty`, `original_trigger=Some(Custom(TAG))`) returns `MatchResult::None` through `resolve()` (not resurrected by the dual-check). The kill did NOT fire: (a) one-loop holds, (b) one-primitive holds, (d) walk-once holds. The ONLY divergence is the pre-registered second-surface split (X9's partial-kill residual): the `is_tombstone`/`menu_is_unbound` **predicate** generalizes to the Option-returning macOS-menu surface (the spike's generalized replica `resolve_custom_menu` returns `None`), but the REAL `binding_for_custom_action_in_context` keeps its own `Option::filter` short-circuit **shape** and X9's `!is_tombstone()`-only filter still leaks the `Empty` representation (`real_menu.is_some()`). Per the framework's pre-registered rule, **predicate-generalizes + shape-diverges is a recorded split, NOT a Partial-kill** (a Partial-kill would require the predicate itself failing to generalize; it does not).

**Branch / worktree.** `sha-ir/spike-x6-resolve` (worktree `/home/mhb/warp/.claude/worktrees/spike-x6-resolve`, branched off the X9 tombstone work on `sha-ir/keybindings-draft`). HEAD `86681f52` (`spike(keybindings): X6 unified scope-tagged resolve() walk over bindings()`) on top of `0dfb825f` (X9 results) / `df7386d3` (X9 kernel). Real APIs confirmed present (not fictional green): `keymap.rs` `is_tombstone`/`original_trigger`/`bindings()`/`custom_action_bindings()`, `matcher.rs:251` `binding_for_custom_action_in_context`. Worktree clean.

**Run.** From the worktree: `cargo test -p warpui_core --lib keymap::resolve_spike -- --nocapture` → `5 passed; 0 failed` (touched source, recompiled clean); re-run under `cargo nextest run` → `5 tests run: 5 passed, 297 skipped`.

---

## 1. The four test outcomes (what `resolve()` proved)

| # | Test | Axis probed | Outcome |
|---|---|---|---|
| 1 | `ported_test_matcher_fixed` + `ported_test_editable_binding_matching` | **Ported golden parity** | ✅ PASS — both run side-by-side with the REAL `Matcher`, asserting parity at every step |
| 2 | `prefix_chord_after_tombstone_one_loop` | **One-loop control-flow merge** | ✅ PASS — `retain_pending` coexists with suppression early-stop in ONE loop |
| 3 | `scope_tagged_tri_kind_distinct` | **One scope-tagged primitive** | ✅ PASS — distinct keys/actions; scope tag derived from binding side |
| 4 | `both_surface_custom_unbind_leak` | **Leak `None` + second surface** | ✅ PASS — `resolve()` returns `None`; second surface shares-predicate-diverges-shape |

### Test 1 — ported golden parity (`portedTestsPass = true`)

Two core `matcher_tests` cases are ported **line-for-line** and run against the real `Matcher` in lockstep, with `assert_parity` (downcast action-value equality for `Action`/`Action`, variant-string equality otherwise):

- `ported_test_matcher_fixed` (ports `matcher_tests::test_matcher`, fixed bindings),
- `ported_test_editable_binding_matching` (ports `test_editable_binding_matching`).

Both exercise basic match, the `'a b'` chord, failed-key non-interference, context-change pending clear, and per-view pending — i.e. **chord / pending / per-view state all compose into the single unified `resolve(query, view_id, ctx)` signature**, producing results identical to `push_keystroke`.

> **Honest caveat on "ALL".** `matcher_tests.rs` has 8 test fns; only the **two** state-machine tests were ported verbatim. The other six (`test_bindings_for_context` — a different read surface; the four X9 `test_tombstone_suppresses_*`; `test_inject_override_consistency_gate`) were NOT ported line-for-line, but the tombstone-suppression behavior they cover is independently re-exercised by the spike's own scope/leak tests (Tests 3 and 4) and by the X9 suite.

### Test 2 — one loop, no `resolve_keystroke` (`prefixChordResolvesOneLoop = true`)

`prefix_chord_after_tombstone_one_loop`: pressing `"a"` exactly matches a `KeyScoped` tombstone → `MatchResult::Unbound` (defined policy = suppressed) in ONE loop, **even though** chord `"a b"` shares the prefix; pending is cleared so a stray `"b"` → `None`; a NON-tombstoned chord `"c d"` still retains pending (`"c"` → `Pending`, `"d"` → `Action::Cd`) in the SAME loop. This proves `retain_pending` (the partial-match keep-scanning leg, `resolve_spike.rs:264`) coexists with the suppression early-stop `break` (`:254-257`) inside the single `for binding in self.keymap.bindings()` loop. **Verified there is NO separate `resolve_keystroke` anywhere in `keymap/`** — grep finds the symbol only in doc comments stating its deliberate absence. The keystroke match arm is inline in `resolve()`.

### Test 3 — one scope-tagged primitive, distinct keys/actions (`scopeTagOnePrimitive = true`)

`scope_tagged_tri_kind_distinct` uses **DISTINCT** keys/actions (`ctrl-k`, `StandardAction::Close`, `Custom` tag 7 — never one shared key) with one tombstone per kind:

- `KeyScoped` tombstone suppresses the **Keystroke** query → `last_suppress = KeyScoped([ctrl-k])`;
- `ActionScoped` tombstone suppresses BOTH the **Standard** query (`ActionScoped(Standard(Close))`) AND the **Custom** query (`ActionScoped(Custom(7))`).

All three flow through ONE primitive: `apply()` → `suppression_for()` → `scope_of(matched)`, where the scope tag is derived from the **binding-side matched trigger**, NOT from a match-on-query-kind. The suppression primitive contains **zero** references to `query` — it keys on `binding.is_tombstone()` / `Trigger::Empty + original_trigger`, and the four call sites pass `binding.trigger` (or `orig`), never the query (`:253/272/286/300`). This refutes the scope-category trap (single-shared-key artifact / query-kind dispatch).

### Test 4 — leak returns `None`, both surfaces accounted (`leakReturnsNoneThroughResolve = true`; `secondSurface = shares-predicate-diverges-shape`)

`both_surface_custom_unbind_leak`:

- The A3-Q5 leak fixture (`custom_trigger=Empty`, `original_trigger=Some(Custom(TAG))`) returns `MatchResult::None` through `resolve()` — **not** resurrected via the `original_trigger` dual-check — and the `Empty`-unbind still flows through the scope-tagged primitive (`last_suppress = ActionScoped(Custom(TAG))`).
- **Second surface = `shares-predicate-diverges-shape`:** the spike's GENERALIZED replica `resolve_custom_menu` (predicate = tombstone OR `Empty`-unbind, via `menu_is_unbound`) returns `None`, proving the scope-tagged decision CAN port to the Option-returning surface. BUT the REAL `Matcher::binding_for_custom_action_in_context` shares only the `is_tombstone()` predicate (X9 added `.filter(|b| !b.is_tombstone())`) and keeps its own `Option::filter` short-circuit **shape**, so it STILL leaks the `Empty` representation (`real_menu.is_some()`) while correctly honoring a real `as_tombstone()` tombstone (`is_none()`).

This is exactly X9's PARTIAL-KILL residual carried forward: **same predicate, divergent short-circuit shape, `Empty` case uncovered on the real surface.** Because the predicate generalizes, this is a recorded split, not a new Partial-kill.

---

## 2. The walk-once invariant (the perf gate's honest substitute)

`walkOncePerCall = true`. The tautological criterion ratio (~1.0x by construction — same single walk) was **dropped** and replaced by a walk-count invariant:

- `resolve()` calls `self.keymap.bindings()` at **exactly one** site (`resolve_spike.rs:243`), with `walk_count` incremented exactly once immediately before it (`:238`); no other `bindings()` iteration occurs in `resolve()` (pending bookkeeping uses `self.pending`).
- Every test asserts `walk_count() == number of resolve() calls` (10, 10, 4, 3, 1 respectively).
- The second surface `resolve_custom_menu` walks a **different** source (`custom_action_bindings()`) and does **not** touch `walk_count`, so it cannot perturb the invariant.

> **Honest caveat (the walk-count trap).** The instrument is a **per-call** counter (`walk_count += 1` once per `resolve()`), not a counter wired **onto the iterator**. So `walk_count == calls` is sound **only because** manual inspection + grep confirm there is exactly ONE `self.keymap.bindings()` call site in `resolve()` (`:243`) guarded by the adjacent increment. A future second walk added inside `resolve()` would NOT bump this counter and the assertion would still pass — the proxy guards against double-walking only as long as the single-call-site structure is preserved. This is the one place the spike substituted a per-call counter for an on-iterator counter; it is sound today, but the invariant rides on the single verified call site, not on the instrument itself.

---

## 3. THE residual: matcher-unify ≠ dispatch-unify (the three app.rs wrappers stay distinct)

`secondSurfaceGeneralizes = shares-predicate-diverges-shape`; `walkOncePerCall = true` — **but a green unified `resolve()` over `bindings()` does NOT prove the three dispatch CALLERS collapse.** This is the load-bearing scoping boundary, recorded in the X6 design doc (`cross-axis-sequencing.md:46`, residual risk):

> *"Even a fully green unified resolve() over bindings() does NOT prove the three dispatch wrappers (app.rs:1866/1981/2005) collapse — they share .rev() context-chain iteration but diverge in pending/view_id threading, early-return policy, and the Paste special-case, so Axes 2/3/4 still touch three callers; X6 answers 'can the MATCHER unify,' not 'can the DISPATCH unify.'"*

Read-only confirmation in `crates/warpui_core/src/core/app.rs`: all three iterate `.iter_mut().enumerate().rev()` **identically**, but they diverge in shape:

| Wrapper | Divergence |
|---|---|
| `dispatch_standard_action` (~1877-1901) | NO early-return + the **Paste** special-case (~1894-1898) |
| `dispatch_custom_action_internal` (~1992-2014) | early-returns (~2009-2011), no Paste |
| `dispatch_keystroke` (~2016+) | threads per-view `responder_chain[i]` + `pending` (~2024, ~2035-2037) |

The spike code (`resolve_spike.rs`) and commit `86681f52` never claim/imply caller unification: the module is scoped to `keymap.bindings()` (*"the shared source of the three dispatch matchers"*) and explicitly *"does NOT refactor the real Matcher."* **CAVEAT:** the caller-fragmentation residual is recorded in the **design doc**, not in the executed-spike artifact; the residual documented *inside* `resolve_spike.rs` (Test 4) is a DIFFERENT one (the second-surface `Empty`-unbind leak). A reader of only the code/commit would not see the dispatch-caller distinction — it lives unambiguously in this worktree's design doc and is repeated here so it is not lost. **X6 answers "can the MATCHER unify," not "can the DISPATCH unify"; Axis-2 scoped-match lands in the latter.**

---

## 4. Adversarial skeptic findings (4 attacked; none defeated the build)

1. **Second-surface (macOS-menu cmd-p path leaks undocumented?)** — trap NOT confirmed, high confidence. The trap's premise is real (`matcher.rs:251-279` walks `custom_action_bindings()`, carries its own `original_trigger` dual-check, filters only `!is_tombstone()`, blind to the `Empty`-unbind) — **but the leak test EXPLICITLY covers it.** Test 4 calls the REAL surface twice: asserts `real_menu.is_some()` and documents it as a RESIDUAL leak, and asserts `is_none()` for an `as_tombstone()` tombstone; the generalized replica returns `None`. The headline is not hollow — the spike never claims a green `resolve()` fixes the menu path; it tests and discloses the residual on that exact surface.
2. **Caller-fragmentation (green matcher mistaken for collapsed dispatch wrappers?)** — trap NOT confirmed, high confidence. The matcher-unify ≠ dispatch-unify distinction is explicitly recorded in the design doc (`cross-axis-sequencing.md:31/37/46/47`) and read-only-confirmed in `app.rs` (all three `.rev()`, divergent pending/early-return/Paste). Caveat carried in §3: the distinction lives in the design doc, not the executed artifact.
3. **Scope-category (single shared key artifact / query-kind dispatch?)** — trap NOT confirmed, high confidence. `scope_tagged_tri_kind_distinct` uses DISTINCT triggers (`ctrl-k`, `Close`, tag 7); `suppression_for`/`scope_of`/`apply` reference `query` **zero** times and key on binding-side metadata. Residual (not the trap): the matching loop forces binding-trigger-kind == query-kind, so the test cannot fully *isolate* binding-derived from query-derived scope, though the code is structurally binding-derived.
4. **Walk-count (tautological per-call counter, not on-iterator?)** — trap flagged `true` by the skeptic, but its evidence was empty ("see above") and did not positively substantiate untrustworthiness. Anchoring on the run-level field (`walkOncePerCall = true`) and on the verified single `bindings()` call site (`:243`), the invariant **holds**; the per-call-vs-on-iterator weakness is recorded honestly as a residual in §2. It does not flip the verdict.

---

## 5. KEEP vs THROW

**KEEP (seed for A3-Q5 / A3-Q13 / Phase-2 resolver):**
- The **`resolve(TriggerQuery, view_id, ctx)` signature shape** + the **`TriggerQuery`** enum (one enum, one per-kind match arm inside ONE loop, never a separate `resolve_keystroke`).
- The **scope-tagged `Suppress` primitive** design (`KeyScoped(keystrokes)` vs `ActionScoped(Standard|Custom)`), dispatched by **binding-side metadata** — `suppression_for` → `scope_of` → `apply` — not by query kind.
- The **ported golden tests** (graduate into the A3-Q16/Q17 resolution-snapshot regression suite once production lands a real unified resolver).
- The **both-surface finding**: the leak fix must reach `binding_for_custom_action_in_context` too, not just `match_custom`; the predicate (`is_tombstone` OR `Empty`-unbind) generalizes, but the Option-returning surface keeps its own short-circuit shape — feeds A3-Q5's leak-fix scope.
- The **caller-fragmentation note** (all three `app.rs` wrappers `.rev()` but diverge in pending/view_id threading, early-return, and Paste) — the input to whether Axis-2 scoped-match touches one or three dispatchers.

**THROW:**
- The **cfg-gated parallel suppression/`Trigger` copy** — production lands suppression as a real layer/`Trigger` variant (the X9 `MatchResult::Unbound` + `is_tombstone()`), not the throwaway spike `Suppress`/`SuppressKind` scaffolding.
- **Any criterion bench** + the synthetic 435+400 generator — the perf ratio is ~1.0x by construction (same single walk); the walk-count invariant replaces it.
- The **Vim-fork `{default,user}` truth table** — that fixture is **A3-Q2's** N-layer harness, not X6's unify question; it was never built here.

---

## 6. Residual risk (carried, not dropped)

1. **Dispatch wrappers are NOT collapsed.** X6 proves the MATCHER unifies over `bindings()`; it does NOT prove the three `app.rs` dispatch wrappers (`1866/1981/2005`) collapse — they diverge in pending/view_id threading, early-return policy, and the Paste special-case. Axes 2/3/4 still touch three callers; caller unification is the downstream question where Axis-2 scoped-match actually lands (§3).
2. **Dynamic Modal vocabulary is faked / unbuilt.** The spike uses static fixtures; the dynamic `Modal:{engine}:{submode}` mode-pack vocabulary (FSA-emitted submode strings flowing end-to-end) is an Axis-5/X10 + A4-Q1 design item, NOT validated here. Production `Context.set`/`map` remain static; even X7's leaf-`Cow` change is leaf-only.
3. **Menu `original_trigger` coupling.** The second-surface leak fix's reach into `binding_for_custom_action_in_context` may surface a deeper coupling — the macOS menu resolution depends on `original_trigger` by design, so removing the fallback could break cmd-p. The spike flags this (Test 4 shows the real surface still leaks the `Empty` rep and must keep a per-surface short-circuit) but does not resolve it; any future refactor unifying the surfaces must preserve the second short-circuit site or the menu silently shows an unbound action's keybinding.
4. **Walk-count proxy is structural, not instrumented.** The once-per-call counter is sound only while `resolve()` keeps its single `bindings()` call site (§2); it is not wired onto the iterator, so it would not catch a future second walk.
5. **Compile/green ≠ production resolution.** The spike is a parallel `cfg(test)` resolver; it does not mutate the real `Matcher`. Any production unification must still cross the X13 resolution-snapshot golden before `bindings()`-touching work treats it as settled.

---

## 7. Verdict mapping (the pre-registered rules)

- Second-surface skeptic substantiates the cmd-p leak is **live and undocumented**? **No** — the leak test explicitly covers `binding_for_custom_action_in_context` and discloses the residual → not False-green-caught.
- Scope-category skeptic substantiates a **single-shared-key artifact**? **No** — distinct keys/actions, binding-metadata dispatch → not False-green-caught.
- KILL (a) one-loop OR (b) one-primitive fired (must split `resolve_keystroke` / suppression needs query-kind branching)? **No** — both refuted → not Kill (do NOT pre-unify on a false claim, but the unify claim is true).
- All hold: ported tests pass through `resolve()`; prefix-chord resolves in ONE loop; suppression is ONE scope-tagged primitive (distinct keys/actions); leak returns `None` through `resolve()` AND the second surface is accounted (shares-predicate-diverges-shape per X9 = acceptable documented split); walk-once invariant holds.
- Only the second surface shape-diverges (predicate **generalizes**) → **Trustworthy-Success with the split recorded**, NOT Partial-kill.

**→ TRUSTWORTHY-SUCCESS.**

**unifyDecision:** *unify the three primary walkers + scope-tagged suppression as shared pre-Phase-2 infra; the second (Option-returning) surface shares the `is_tombstone` predicate but keeps its own short-circuit shape; the three dispatch WRAPPERS stay distinct (matcher-unify ≠ dispatch-unify).*
