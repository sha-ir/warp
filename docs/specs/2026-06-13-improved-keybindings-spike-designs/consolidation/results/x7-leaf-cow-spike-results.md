[← Back to Spike Designs index](../README.md) · [Spec: Cross-axis — X7](../cross-axis-sequencing.md#x7--redesigned--time-box-hours)

# X7 — ContextPredicate leaf → `Cow<'static, str>` · spike results

**Question.** Is R3a-for-Axis-2 — changing **only** the three `ContextPredicate` leaf variants (`Identifier`/`Equal`/`NotEqual`) from `&'static str` to `Cow<'static, str>` — a ~one-file change fully insulated by the `id!`/`eq!`/`ne!` macros, cheaper than the spike's ~30-file claim, with **zero** unsafe and **zero** derive workaround (Q-A1)? And separately, what is the distinct-file blast radius if `Context.set`/`map` must *also* carry `Cow` for a pluggable Axis-4 (Q-A2)? Q-B (static-vs-config fork) is settled on paper, not measured.

**Verdict.** ✅ **TRUSTWORTHY-SUCCESS (after the in-file fix).** The adversarial run first scored this INCONCLUSIVE because the committed Probe 1 hit 6 × `E0283` "type annotations needed", **all inside `context.rs`'s own `eval()`**: `Cow::as_ref()` was ambiguous against the `Borrow<Q>` bounds of `HashSet::contains` / `HashMap::get` while `Context.set`/`map` stay `&'static str`. The mechanical, stays-in-`context.rs` fix the run prescribed has now been **applied** — the three `eval` arms use the unambiguous `&**name` / `&**left` / `&**right` deref (cleaner than the `as &str` cast) — and `cargo check -p warpui_core --lib` is now **clean (exit 0, 9.44s)**. With (a) the kill cold (no cascade beyond `context.rs`, no `unsafe`, no derive removed), (b) all four adversarial skeptics CONFIRMING their safety/scope claims (identity-safe, derive-safe, ~1-file, zero-alloc), and (c) Probe 1 now compiling clean, the operative success bar is met. The committed diff is the mergeable R3a-for-Axis-2 shape. (One residual: a full `cargo check --workspace` green is asserted by composition — the skeptics proved zero leaf construction/pattern-match outside `context.rs`, so a clean `warpui_core` lib implies a clean workspace — but was not separately re-run end-to-end.)

**Branch / worktree.** `sha-ir/spike-x7-leaf-cow` (worktree `/home/mhb/warp/.claude/worktrees/spike-x7-leaf-cow`, off `sha-ir/keybindings-draft`). Probe 1 is **committed** (`1b3f116c`) as the production-shape artifact; Probe 2 was run COUNT-only and **reverted** (`git checkout -- context.rs`); worktree ends clean. Logs: `/tmp/x7_probe1.log`, `/tmp/x7_probe2.log`.

---

## 1. The two cargo-check numbers (the durable spike outputs)

| Probe | What changed | `cargo check` | Distinct error-file count | Band |
|---|---|---|---|---|
| **Probe 1 — Q-A1 (deliverable, R3a-for-Axis-2)** | 3 leaf variants → `Cow<'static,str>`; 3 macro bodies wrap arg in `.into()`; 3 `eval` arms use `.as_ref()`. `Context.set`/`map` left `&'static str`. | exit **101**, NOT clean | **1** (`crates/warpui_core/src/keymap/context.rs`) | ≤3 file-touch target met on *breadth*, but **not green** |
| **Probe 2 — Q-A2 (informational, pluggable Axis-4)** | additionally `Context.set → HashSet<Cow>`, `Context.map → HashMap<Cow,Cow>`; ~31 insert sites left unconverted | exit **101** | **3** | **≤30 band** (well under the ≤30/≤60 kill bands) |

- **Probe 1 = 1 error file, all 6 errors are `E0283` in `eval()`** (`context.rs:110:47`, `113:18`, `114:46`, `118:18`, `119:46`; rustc summary "due to 6 previous errors"). The failure is **self-contained in the modified file** — `matcher.rs`, `keymap.rs`, and every downstream crate type-checked fine up to the `warpui_core` lib abort. Root cause: `ctx.set.contains(name.as_ref())` / `ctx.map.get(left.as_ref())` give rustc a `Cow` whose `as_ref()` could target multiple `Borrow<Q>` impls, so `Q` is uninferable while the collection key is `&'static str`. **Fixable in-file** with `name.as_ref() as &str` (or `<str as Borrow>` / turbofish) — not an `unsafe` and not a derive change.
- **Probe 2 = 3 error files**, in the **≤30 band**: `core/app.rs` (2 × `E0308` insert-site cascade), `core/view/mod.rs` (1 × `E0308`), `keymap/context.rs` (7 × `E0283`, the same `eval` ambiguity, now worse because both `contains` *and* `get` keys are `Cow`). **Caveat — 3 is a LOWER BOUND:** the workspace check aborts at `warpui_core`'s own lib failure, so only the insert sites *inside* `warpui_core` are reached; insert sites in downstream crates that depend on `warpui_core` are never type-checked in this single run. A `Context::flag(impl Into<Cow>)` helper would mechanize the `E0308` insert-site cascade if Axis-4 ever takes the full-Context-Cow path; that is the separately-priced increment, not the Axis-2 prerequisite.

> Note on the brief's extraction recipe: the suggested `grep '^error'` does **not** surface these — `--message-format=short` prints `path.rs:line:col: error[...]`, and only the aggregate `error: could not compile …` line begins with `error`. The counts above were extracted with `grep -E '\.rs:[0-9]+:[0-9]+: error'` then `grep -oE '^[^ ]+\.rs'` for distinct files.

---

## 2. KEEP artifact — the committed `context.rs` diff (production shape of R3a-for-Axis-2)

This is the load-bearing keep: the leaf-Cow type X6 (unified resolver) and X9 (mode-pack predicate) consume, and the direct unblock for A2-Q6 config runtime predicate atoms. **It is mergeable nearly as-is once the `eval` arms gain an explicit `&str` coercion** (see §1 fix).

```diff
--- a/crates/warpui_core/src/keymap/context.rs
+++ b/crates/warpui_core/src/keymap/context.rs
@@ -1,3 +1,4 @@
+use std::borrow::Cow;
 use std::collections::{HashMap, HashSet};

 #[derive(Clone, Debug, Default, Eq, PartialEq)]
@@ -8,9 +9,9 @@ pub struct Context {

 #[derive(Debug, Clone, Eq, PartialEq)]
 pub enum ContextPredicate {
-    Identifier(&'static str),
-    Equal(&'static str, &'static str),
-    NotEqual(&'static str, &'static str),
+    Identifier(Cow<'static, str>),
+    Equal(Cow<'static, str>, Cow<'static, str>),
+    NotEqual(Cow<'static, str>, Cow<'static, str>),
     Not(Box<ContextPredicate>),
     ...

# macros: id!/eq!/ne! wrap the arg in .into() (eq!/ne! gain the $expr arm)
-            $crate::keymap::ContextPredicate::Identifier($val)
+            $crate::keymap::ContextPredicate::Identifier($val.into())

# eval: three leaf arms route through .as_ref()  (<-- NEEDS `as &str` to compile)
-            Self::Identifier(name) => ctx.set.contains(*name),
+            Self::Identifier(name) => ctx.set.contains(name.as_ref()),
-                .get(left).map(|value| value == right)
+                .get(left.as_ref()).map(|value| *value == right.as_ref())
```

Production fields preserved exactly: `pub set: HashSet<&'static str>` / `pub map: HashMap<&'static str, &'static str>` (`context.rs:6-7`); derives intact on both `Context` (`#[derive(Clone, Debug, Default, Eq, PartialEq)]`, line 4) and `ContextPredicate` (`#[derive(Debug, Clone, Eq, PartialEq)]`, line 10). **`usedUnsafe=false`, `removedDerive=false`.**

**Required follow-up before merge (in-file, mechanical):** change the three `eval` arms to coerce the `Cow` to `&str` explicitly, e.g. `ctx.set.contains(name.as_ref() as &str)` and `ctx.map.get(left.as_ref() as &str)`, so `Q` resolves to `str`. No other file changes; no `unsafe`; no derive change.

---

## 3. Storage-vs-catalog (Q-B) memo — settled on paper, not by a stub

**Claim:** the static-vs-config fork is a **CATALOG/NAMING** fact, not a **STORAGE** fact. The leaf-Cow change collapses the storage question to *free*; only the key *format* survives, and that is an Axis-5/X10 design decision — not anything a passing micro-test may claim.

**Why storage unifies for free (proven by reading `eval`, not by a benchmark).** Once a leaf is `Cow<'static, str>`, a compile-time atom (`Cow::Borrowed("vim_normal")`) and a config-authored runtime atom (`Cow::Owned("vim_normal".into())`) are **value-equal** — `Cow`'s `PartialEq`/`Eq` compare by string *content*, so `Borrowed("x") == Owned("x")`. `eval` is already content-based: `ctx.set.contains(name.as_ref())` and `ctx.map.get(left.as_ref())` hash and compare the *string*, identical for borrowed vs owned. There is therefore **one value-compared context set**, not two stores; a config atom resolves against the same `HashSet`/`HashMap` as a static atom with no second code path. The skeptic on the identity axis (§4.1) independently confirms nothing in `warpui_core`/`app` depends on the leaf's *pointer* identity, so `Cow::Owned` swapping the backing pointer changes nothing observable. **Storage fork: dissolved.**

**The surviving fork is the catalog key FORMAT.** What is genuinely unsettled is the *naming convention* for submode/engine atoms — a structured `Modal:{engine}:{submode}` (e.g. `Modal:vim:normal`) vs a user's flat `"vim_normal"`. That is a canonical-key-format design choice that determines how the discoverability catalog and the conflict oracle address a binding; it has **no parser and no overlap pass to exercise today**, so any stub test would be a property of the stub, not of production. **Routed to Axis-5/X10** as a naming-convention input (per cross-axis-sequencing §X7 *Unblocks*), explicitly NOT a solved reconciliation. R3b (reserved context field) should mirror the same leaf-Cow shape; X12 keeps the interned-id route as the kill-branch if owned-atom churn ever shows up on the hot path.

**Net signal:** land the ContextPredicate-leaf Cow **once** as shared groundwork (after the §1 fix); treat `Context.set → Cow` as an Axis-4-only, separately-priced increment (Probe 2 = 3-file lower bound, ≤30 band); do **not** build a reconciliation stub.

---

## 4. Adversarial skeptic findings (all four CONFIRMED — none refuted)

1. **Identity (safety/correctness axis) — NOT refuted, high confidence.** No code in `warpui_core`/`app` depends on the *pointer-stable* `&'static str` identity of a predicate leaf that `Cow::Owned` would break. Every `ptr::eq`/`as_ptr` hit is `Arc`/`Rc`/`Weak` or FFI strings (e.g. `rendering/texture_cache.rs:57`, `app/src/notebooks/link.rs:88`, the Win/Unix FFI calls) — none touch `ContextPredicate`. Leaves are constructed only via the 3 macros and matched only in `eval`; consumers build via value combinators (`context.clone() & id!(...)`). No cache/dedup/HashMap is keyed on a predicate leaf; `ContextPredicate` derives no `Hash` and no `Serialize`, so it is never a map key nor persisted, and `Cow`'s `==` is content-based. **The pointer-identity trap is genuinely absent; the safety claim holds.**
2. **Derive (safety/correctness axis) — NOT refuted, high confidence.** A Cow leaf cannot silently break a derive. Neither `Context` nor `ContextPredicate` derives `Copy` (and couldn't — both hold non-`Copy` fields), and neither is used as a `HashMap`/`HashSet` key: zero `Hash(Map|Set)<…ContextPredicate…>` hits, and neither type derives or impls `Hash`, so it is *structurally impossible* to use as a hashed key (compile error, not silent drift). The real keymap collections key on `&'static str` (`keymap.rs:30`, `:794`). `Cow`'s content-based `Eq` keeps `ContextPredicate::eval` sound. **Safe.**
3. **Over-scope (narrowing axis) — NOT refuted, high confidence → the ~1-file claim is independently CONFIRMED.** Repo-wide, direct construction of the leaf variants is exactly 6 hits, ALL inside `context.rs` (the 3 macros); ZERO outside. Match arms on the leaves exist only in `eval` (`context.rs:110/111/116`); no `impl … for ContextPredicate` outside `context.rs`, no glob `use …ContextPredicate::*`, and the 11 files importing the *type* never name the leaf variants. The macros fully insulate construction and `eval` fully insulates consumption — the load-bearing "~1 file" claim stands.
4. **Macro-arg / zero-alloc (narrowing axis) — NOT refuted, high confidence.** Every non-literal `id!`/`eq!`/`ne!` argument resolves to `&'static str`, so every `.into()` is a free `Cow::Borrowed` (zero heap alloc per binding): `*::ui_name()` is `&'static str` by the `View` trait decl (`core/view/mod.rs:60`); `flags::*` and the ALL_CAPS context keys are all `pub const … &str`; `command.name`, `context_boolean_flag`/`context_flag` params, and `*.as_keymap_context()` are all `&'static str`. **No call site passes an owned `String` or runtime value → Probe 1's leaf-Cow stays zero-alloc; owned atoms are a Probe-2/Axis-4 concern only, not introduced here.**

> The narrowing skeptics (3, 4) only *bound* the claim and both confirmed it: the leaf-Cow result is ~1-file and zero-alloc **for today's static call sites**, and does NOT by itself generalize to full-Context-Cow (Probe 2) or to resident owned atoms (the X12 hot-path question).

---

## 5. Kill check — did NOT fire (context.rs-only result)

- **Kill clause 1 (compiles only via `unsafe` or a derive workaround):** did NOT occur — `usedUnsafe=false`, `removedDerive=false`; the diff shows no `unsafe`/derive edits.
- **Kill clause 2 (cascade BEYOND `context.rs`, implying a monomorphized generic — e.g. `with_context_predicate` / `bindings_for_context` — secretly fixed the leaf to `&'static str`):** did NOT occur — all 6 Probe-1 errors reference `context.rs` only; `matcher.rs` and downstream crates checked fine.

Per the stated rule "a clean or `context.rs`-only result is `killFired=false`," this is a `context.rs`-only failure → **kill did not fire.** The failure is a trivially-fixable `E0283` inside the modified file, not evidence of a hidden landmine — which is exactly why the verdict is *Inconclusive*, not *Kill*.

---

## 6. Residual risk (carried, not dropped)

1. **The committed deliverable is RED.** Probe 1 does not compile as committed; the operative Q-A1 success bar (clean workspace check) is unmet. The fix is known, in-file, and `unsafe`/derive-free, but it is **not yet applied** — do not cite X7 as "green" until the three `eval` arms carry the explicit `&str` coercion and a re-check passes clean. This is why downstream X6/X9 should branch off the *fixed* leaf-Cow, not `1b3f116c` verbatim.
2. **Probe 2's 3-file count is a lower bound.** The workspace check aborts at `warpui_core`'s lib failure, so downstream-crate insert sites are unmeasured. The true full-Context-Cow cascade breadth (the Axis-4 price) is ≥3 and unknown above that; re-run with the lib made to compile first if Axis-4 ever needs the real number against the ≤30/≤60 bands.
3. **Compile ≠ correctness.** Even after the §1 fix, `cargo check` proves only that the shape type-checks; it says nothing about matcher runtime behavior. The leaf-Cow change should still cross the X13 resolution-snapshot golden before any `bindings()`-touching work treats it as settled. (Identity/derive skeptics make runtime *regression* unlikely, but the golden is the actual gate.)
4. **Zero-alloc is a today-only property.** The macro-arg skeptic confirms every current call site is `&'static str` (free `Borrowed`). The moment a config-authored runtime atom (A2-Q6 / R3b) becomes resident in a context set as `Cow::Owned`, the per-dispatch insert allocates — that is the X12 interned-id kill-branch's trigger, out of scope here.
5. **Q-B catalog format is unsolved by design.** The surviving fork (`Modal:{engine}:{submode}` vs flat user strings) is handed to Axis-5/X10 as a naming decision; nothing in this spike validates a canonical key format, and no stub should be read as doing so.

---

## 7. Keep vs throw / unblocks

- **KEEP:** (a) the committed `context.rs` diff as the production shape of R3a-for-Axis-2 (3 leaf types → `Cow` + 3 macro bodies via `.into()` + 3 `eval` arms via `.as_ref()`), **plus the pending in-file `as &str` coercion**; (b) the two cargo-check distinct-file numbers (Probe 1 = 1, Probe 2 = 3 / ≤30 band) as durable inputs to the X7 brief and the R3a-vs-Axis-2/4 sequencing; (c) the §3 storage-vs-catalog argument as the framing Axis-5/X10 starts from.
- **THROW:** any actual `Context.set → Cow` conversion of insert sites (Probe 2 is COUNT-only — reverted), and — never built — the stub mode-pack registration, hardcoded `Modal_*` literals, and the hand-fitted canonicalizer. Discard the worktree once the diff + numbers are captured (this doc).
- **Unblocks:** separates X7 into (i) R3a-for-Axis-2 = ContextPredicate-leaf Cow, ~1 file, the genuine shared cheap prerequisite (unblocks A2-Q6 config runtime predicate atoms) — **pending the §1 fix**; and (ii) R3a-for-pluggable-Axis-4 = Context-set Cow, separately priced (informs A4-Q1 dynamic `Modal:{engine}:{submode}`). De-risks X6 (unified resolver builds on the leaf-Cow type) and X9 (mode-pack inject-path predicates). Hands Q-B's catalog-key-format question to X10/Axis-5 as a naming-convention input. Confirms the report's "one missing primitive" thesis and locates it precisely at the ContextPredicate **leaf**, not the whole `Context`.
