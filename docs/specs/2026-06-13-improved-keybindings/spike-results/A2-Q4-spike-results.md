[← Back to Spike Designs index](./README.md) · [Spec: Axis 2 — A2-Q4](./axis-2-scope-and-context-control.md)

# A2-Q4 — Adversarial spike results

**Question.** What relation targets an override onto the right binding when a user rebinds a same-name fork — `Exact` predicate equality, `BindingId`, name+predicate-hash, or `Subsumes` (per-key value-domain implication)? And is a subsumption primitive faithfully implementable against `ContextPredicate::eval`?

**Verdict to earn (not assert).** *"The override-targeting key must be an author-assigned stable id field — `Exact`, `BindingId`, and name+predicate-hash are all disqualified — AND a per-key value-domain `implies()` can be made bit-identical to `eval`, so subsumption is faithfully implementable, but any shipped subsumption primitive must carry an explicit `undecidable/too-large ⇒ refuse and warn, never silently mis-target` guard."* The spec already recommends author-assigned id. This spike's job is to **try to break that argument** and to fix the spec where its supporting claims are wrong — not to restate the conclusion.

**Branch.** `sha-ir/spike-a2-q4-targeting-relation` (off `sha-ir/keybindings-draft`). Evidence branch — the `implies_per_key`/`implies_2k`/`subsumes_reachable` probes are **throwaway** `context.rs` functions, stripped in the final commit; the reproducible evidence stays in the commit history.

---

## Adversarial stance — the false-greens we are defending against

From the spec's own False-green section:

1. **Fidelity mirage (dominant).** The original 1–2 day design modelled the flagship forks as pure-`Identifier` predicates (`text_entry & id!("Vim")` vs `& !id!("Vim")`), where every atom is an independent boolean. There a naive `2^k`-over-atoms enumerator agrees with the truth, so the `implies()`-vs-`eval` disagreement counter is **structurally 0** — falsely certifying subsumption fidelity. Meanwhile the only awkward production shape (terminal block-selection `eq!(k,"One") | eq!(k,"None")`, one key two mutually-exclusive values) is exactly where `2^k`-over-atoms is **unsound** and never gets fed in. *Defense:* the fidelity test enumerates **per-key value-domains**, the fixture set **provably contains** the same-key multi-value shape, and we **re-run with a `2^k` enumerator and require it to go red** — otherwise the green is fake.
2. **Tautology-as-measurement.** The original "orphan rate" is definitionally 100% for any override targeting an edited fork (hash of mutable input), so a synthetic number masks nothing. *Defense:* the stable-handle conclusion is mandated by reasoning, not by any number; no orphan harness is built.
3. **Phantom population.** The `{0,1,≥2}` histogram runs on forks that do not exist (A2-Q5 option-D migration unbuilt), with guessed predicate spellings and a non-existent natural-predicate parser. *Defense:* no histogram; the recommendation is made robust to unknown future spellings, not validated against them.

---

## Gate status — A2-Q5 is effectively settled, and it keeps this test on the critical path

The cross-axis sequencing analysis pre-registers the load-bearing code-read conclusion (`cross-axis-sequencing.md:75,88`):

> *"mutate is NOT subsumed by inject: TrackedId-keyed invalidation means `update_custom_trigger` (touching the existing Tracked) and inject (minting a new Tracked) are not interchangeable for the reactive reader graph, so `update_custom_trigger` SURVIVES in parallel."*

So A2-Q5 is a **split answer**: layer + unbind + mode-pack go the inject route, but the **mutate path is retained**. Mutate means targeting an existing binding, so the targeting relation **matters** — the spec's "kill if A2-Q5 = inject" branch does **not** fire. The remaining gate (editable same-name forks don't exist yet; they would come from A2-Q5 option D migrating the ~19 Vim Fixed forks to named `EditableBinding`s) is precisely why this spike proves the primitive **implementable-but-fragile** rather than running a population histogram.

---

## Deliverable A — the three relations settled on paper (from code already read)

Verified against code on 2026-06-13. The relation that targets a user override onto a binding must survive (a) being authored from natural input, (b) a predicate edit, and (c) a process restart. Three of the four candidates fail on reading alone:

| Candidate targeting key | Verdict | Why (from code) | Citation |
|---|---|---|---|
| **`Exact`** (structural `ContextPredicate` equality) | ❌ unusable from natural input | `#[derive(Debug, Clone, Eq, PartialEq)]` is **structural**; `BitAnd`/`BitOr` build `And(Box(self), Box(rhs))` in **author order** so `a & b ≠ b & a` (no commutative canonicalization); and there is **zero** `FromStr`/`Display` ⇒ a predicate cannot be constructed from a user-facing string, and matching by structural equality leaks internal predicate spelling and is order-sensitive. | `context.rs:9` (derive), `context.rs:61-75` (order-preserving `BitAnd`/`BitOr`), repo-wide grep: no `FromStr`/`Display` for `ContextPredicate` |
| **`BindingId`** | ❌ not persistable | `BindingId(pub usize)` is minted from a per-run `static NEXT_BINDING_ID: AtomicUsize` via `fetch_add` ⇒ a fresh, run-dependent value every process start; nothing serializes or restores it. | `crates/warpui_core/src/keymap.rs:257-273` |
| **name + predicate-hash** | ❌ drifts by definition | Hashing a mutable predicate changes the key the instant the predicate is edited. | definitional (hash of mutable input) |
| **(name, canonical-predicate)** | ⚠️ viable but **deferred** (cycle 2) | A distinct candidate the hash row conceals: the predicate is **not user-mutable** (users rebind the keystroke via `set_custom_trigger`; the predicate is code-fixed), so a *canonical* predicate is stable across every user action. Blocked because no `FromStr`/canonical form exists yet (→ A2-Q6/A2-Q15), it leaks internal spelling, and it drifts on *author* release edits. Its advantage: **zero migration**. | `keymap.rs:422` (trigger-only setter), A2-Q6/A2-Q15 |
| **author-assigned stable id field** | ✅ **recommended target** (decisive with A2-Q5 = mutate, which holds) | The handle stable across edits *and* restarts — but **not an existing handle**: the Vim forks are anonymous `FixedBinding`s (`name: Default::default()`), `EditableBinding`s default to `Just(true)`, and same-name forks are deliberately unified by name (`update_custom_trigger` updates *all* matches). Requires a new per-fork-unique field + the unbuilt A2-Q5-D migration. | `keymap.rs:633` (anonymous fork), `keymap.rs:657`, `keymap.rs:426-431` |

**Conclusion (paper):** the A2-Q3 schema override key should be an **author-assigned stable id field** (its only real cost vs `(name, canonical-predicate)` is a one-time mint-unique-ids migration, traded against author-discipline-on-predicate-edit). It must not be a verbatim predicate string, an interned predicate, or a derived hash. `Subsumes` is the only remaining candidate that needs code to adjudicate — covered by Deliverable B.

---

## Deliverable B — subsumption fidelity (test result)

The claim under test: a per-key value-domain `implies()` can be made **bit-identical** to `ContextPredicate::eval` over the awkward production shapes, and the obvious `2^k`-over-atoms enumerator **cannot**.

**Direction pinned (per the spec's red-team).** `implies(a, b)` ≡ *a ⊨ b* ≡ every reachable `Context` world that satisfies `a` also satisfies `b` (so `a` is the **stronger/narrower** predicate, `b` the **weaker/broader**). The success criterion is stated as "subsumption answer ≠ the oracle's" (catching both over- and under-matching), never the spec's ambiguous `override⊆binding` phrasing.

**Probe.** Three throwaway fns in `crates/warpui_core/src/keymap/context.rs` (stripped in the final commit): `subsumes_reachable` (the oracle — a recursive enumerator over its **own** world universe, `oracle_domains`, built independently of the candidate and carrying a never-mentioned **sentinel** present-value per key — see *Adversarial cycle 2* for why), `implies_per_key` (candidate: mixed-radix per-key-domain enumeration + budget), `implies_2k` (deliberately-unsound `2^(#distinct atoms)` foil — it dedups atoms via derived `PartialEq`, so a shared identifier shares one bit). Tests in `context_tests.rs`. Run: `cargo nextest run -p warpui_core a2q4_`.

```
        PASS  warpui_core keymap::context::tests::a2q4_oracle_matches_hand_computed_truth
        PASS  warpui_core keymap::context::tests::a2q4_candidate_is_bit_identical_to_oracle
        PASS  warpui_core keymap::context::tests::a2q4_candidate_refuses_high_dimensional_predicate
        PASS  warpui_core keymap::context::tests::a2q4_fixture_set_provably_contains_required_shapes
[terminal_mutex_trap] FOIL DISAGREES foil=Some(false) oracle=true
[bare_mutex_trap]     FOIL DISAGREES foil=Some(false) oracle=true
        PASS  warpui_core keymap::context::tests::a2q4_foil_2k_is_caught_on_same_key_and_mirages_on_vim
     Summary  5 tests run: 5 passed, 292 skipped
```
Full crate regression check after the additions: `cargo nextest run -p warpui_core` → **290 passed, 7 skipped, 0 failures, 0 warnings**.

- ✅ **Fidelity assertion:** candidate `implies_per_key` == the **independent** oracle on **every** fixture (disagreement count **0**), over a set the test *structurally* proves contains the pure-Identifier Vim fork, the real terminal same-key multi-value shape (`init.rs:457-461`), the discriminating Equal-vs-NotEqual mutex shape, and absent-key Equal/NotEqual cases. The oracle's world universe is genuinely independent of the candidate's (own `oracle_domains` + sentinel), so this asserts world **selection**, not just enumeration order (hardened in cycle 2). **Subsumption is faithfully implementable.**
- ✅ **Trap demonstration:** the `2^k`-over-atoms foil disagrees with the oracle on **exactly** the two same-key mutual-exclusion fixtures (`foil=Some(false)` vs `oracle=true`) and **agrees on every pure-Identifier Vim fixture** (asserted via a non-vacuous `vim_agreed ≥ 1` counter — cycle 2 replaced a tautological `vim_disagreements == 0`). This is the **false-green made visible**: a subsumption primitive validated only on the synthetic Vim population would ship silently unsound on the real terminal predicate. The disagreement is genuine impossible-world admission, not a planted bug (verified by skeptic 2).
- ✅ **Refuse guard:** a 17-identifier predicate ⇒ `implies_per_key` returns **`None`** (2¹⁷ > budget); a wide single-key value domain (12 values) stays tractable. *Precisely:* the budget bounds the **product** of per-key/per-identifier domains — identifiers contribute a factor of 2 each (exponential ⇒ trips at ~17 atoms), a single key contributes (n+1) linearly (trips only at ~100 000 distinct values). The real-world maximum is ~8 distinct identifiers (`init.rs:312-323`), so production sits far under the refuse threshold — the guard is a safety net, not a routine path.

---

## Adversarial cycle 1 — refutation pass

Three independent skeptics, each mandated to **refute** one load-bearing claim by reading the real code (default-to-refuted). All three **SURVIVED** at high confidence; one produced a refinement folded in below. (A second, broader cycle — *Adversarial cycle 2* — follows.)

### 1. Candidate fidelity — **SURVIVED** (high)

Claim: `implies_per_key` is bit-identical to the true implication relation defined by `eval` over reachable worlds. All five attack vectors PASS:
- **absent ≡ unmentioned-value** — only `Equal`/`NotEqual` read `map`, and both compare solely against *mentioned* values, so an absent key and a key present-with-an-unmentioned-value are eval-indistinguishable in every arm and under every `Not`/`And`/`Or` composition. The lemma is airtight.
- **asymmetric keys** — `domains()` unions `collect_atoms` from **both** predicates, so a key/identifier in only one side is still enumerated.
- **identifier/key name collision** — `set` and `map` are independent `Context` fields; `collect_atoms` routes `Identifier`→idents and `Equal`/`NotEqual`→keys, and `eval` reads them independently. No cross-talk.
- **nested Not/And/Or + Just** — the candidate delegates composition to the real `eval`; constant/empty worlds are still enumerated (product ≥ 1).
- **mixed-radix decode + budget** — `product = 2^|idents| × Π|choices|`, the decode is a correct bijection over `[0, product)` (each world once, none skipped; every `choices.len() ≥ 2`), and `None` is returned iff `product > BUDGET`, never masking a wrong bool.

No `(a, b, world)` counterexample exists: the enumerated worlds are a complete set of eval-equivalence-class representatives over **all** possible `Context` values.

### 2. Foil realism — **SURVIVED** (high), both parts

- **(A) fair strawman** — `implies_2k` is the honest textbook truth-table method: `collect` gathers distinct leaf atoms, the loop enumerates `2^(#atoms)` assignments, and `truth` composes `Not`/`And`/`Or`/`Just` **identically** to `eval`. The only unsoundness is the foundational "atoms are independent" modeling choice — the obvious first instinct — with no planted bug in collect/truth/indexing/budget.
- **(B) genuine unsoundness** — the wrong `Some(false)` on `terminal_mutex_trap` comes from the impossible world `bits = 0b011` (`Terminal=true, Equal(BSC,"One")=true, NotEqual(BSC,"None")=false`). No real `Context` can produce it: `map[BSC]=="One"` (required to make `Equal(BSC,"One")` true) forces `"One" ≠ "None"`, i.e. `NotEqual(BSC,"None")=true`. Impossible-world admission, not a Boolean-composition bug.
- **Refinement (folded into Deliverable B):** the foil enumerates `2^(#DISTINCT atoms)` — it dedups via derived `PartialEq`, so the shared `Identifier("Terminal")` occupies **one** bit ⇒ 2³ = 8 worlds here, and the budget/`None` path is uninvolved (8 ≤ 100 000).

### 3. Disqualifications — **SURVIVED** (high), both claims

- **BindingId non-persistable** — no `Serialize`/`Deserialize` on `BindingId`; the only `BindingId(value)` reconstruction (`app/src/search/action/data_source.rs:237`) is an in-process search-index round-trip rebuilt every run from freshly-minted ids. Custom keybindings persist **by name** (`util/bindings.rs:491` → `set_custom_trigger(name, …)`; comment at `settings_view/keybindings.rs:771`: *"bindings are saved/loaded by name"*). No path restores a `BindingId` across runs.
- **Exact uninstantiable + order-sensitive** — repo-wide, the only trait impls for `ContextPredicate` are `Not`/`BitAnd`/`BitOr`; **zero** `FromStr`/`Display`/`Deserialize`/`Serialize` across 92 references. `bitand`/`bitor` preserve author order; no `canonical`/`normalize`/`sort` touches `And`/`Or`. Both halves confirmed.

---

## Adversarial cycle 2 — hardening (find → fix → re-verify)

A second, fresh cycle ran **5** independent adversaries over the live tree (the 3 refutation skeptics above, re-run, plus a *completeness* critic — "what did this spike miss?" — and a *test-adequacy* critic — "is the green gameable?"). Each blocker/major finding was then **independently verified** by a default-to-not-real skeptic. **candidate-fidelity** and **foil-realism** SURVIVED again (0 confirmed). The two new critics confirmed **5 test-rigor gaps** — all **minor** (no production bug; the per-key model and the verdict are independently backstopped by the sound *absent ≡ unmentioned-value* lemma). Each was fixed and the fix was **proven by mutation testing**.

| Gap the cycle found | Fix | Re-verify (mutation → now caught) |
|---|---|---|
| The oracle **shared `domains()`** with the candidate, so `candidate == oracle` could only test enumeration *order*, never world *selection*. A "drop the absent world" bug passed the **entire** suite. | Gave the oracle its **own** `oracle_domains` + a never-mentioned **sentinel** present-value per key, so it actively tests the absent≡unmentioned lemma. Added hand-computed absent-world anchors and an `always! ⊭ K2==X` fixture. | Delete `choices.push(None)` from the candidate's `domains()` ⇒ `a2q4_candidate_is_bit_identical_to_oracle` **RED** (`candidate=Some(true) oracle=false`). |
| The structural guard's per-side `max_values_per_key ≥ 2` was satisfied only by the **benign Or** fixture; the discriminating Equal-vs-NotEqual mutex traps scored 1/1 and were never required. | Replaced with a **union-across-both-sides** mutex check + explicit "≥1 `_trap` and ≥1 `vim_` fixture" requirements; made the absent-key check structural (not label-string). | Delete both `_trap` fixtures ⇒ structural guard + foil test **RED**. |
| `assert_eq!(vim_disagreements, 0)` was **tautological** — the counter was incremented only inside an `if disagrees` block that sat after `assert!(!disagrees)`, so it was provably 0 regardless of foil behavior; nothing required vim fixtures to exist. | Replaced with a non-vacuous `vim_agreed` counter incremented **after** the agree-assert, asserted `≥ 1`. | Delete both `vim_` fixtures ⇒ structural guard + foil test **RED**. |
| Fidelity was demonstrated only on ≤3-identifier toys; production reaches **8 distinct identifiers** + De-Morgan `!(A&B)` (`init.rs:312-323`, `terminal/input.rs:2071-2076`). | Added complex pure-Identifier fixtures (Or-in-And, De-Morgan) + stated the monotone "pure-Identifier ⇒ 2ⁿ truth table ⇒ exact" argument explicitly. | — (these pass; they close the *empirical* gap behind the generalization claim). |
| The "blowup is dimensionality, **not** cardinality" phrasing over-stated — a single key with ≥~100 000 values *does* trip the budget (linearly). | Reworded to the precise product-based statement (identifiers exponential at ~17; single-key linear at ~100 000; production max ~8). | — (documentation). |

All five `a2q4_*` tests are green after the fixes; the full crate suite is **290 passed / 0 failed / 0 warnings**. The three mutations above each previously passed the whole suite and now go red — the find→fix→re-verify loop is closed.

**Two framing critiques (raised, auto-verifier marked *not a blocking bug*, but folded in for honesty):**
- **A 4th candidate — `(name, canonical-predicate)`** — collapsed by the memo into "name+hash drifts." But the predicate is *not user-mutable* (users rebind the **keystroke** via `set_custom_trigger`; the predicate is code-fixed), so a canonical predicate is stable across every *user* action — the A2-Q4 scenario. Its real weaknesses are: it needs the A2-Q6/A2-Q15 canonical form (which does not exist yet), it leaks internal predicate spelling, and it drifts on *author* release edits. It is a legitimate **zero-migration** point on the tradeoff curve, recorded in the relation table below.
- **"author-assigned stable id" is not yet an existing handle** — the flagship Vim forks are anonymous `FixedBinding`s (`name: Default::default()`, only a per-run `BindingId`), `EditableBinding`s default to `Just(true)`, and where names exist they are deliberately **non-unique** (`update_custom_trigger` updates *all* same-name matches). So the recommendation is the right *target* but presupposes a new per-fork-unique field + the unbuilt A2-Q5-D migration to back-fill the ~19 forks — not a property of any handle that exists today. The relation table and Unblocks now say so.

---

## Corrections to the spec (`axis-2-scope-and-context-control.md`)

Spec left intact per the A1-Q6 precedent; corrections recorded here. (Seeded from citation verification; extended by the refutation pass in Task 5.)

| # | Spec said | Reality | Evidence |
|---|---|---|---|
| 1 | Vim forks at `actions.rs:51-70` | The flagship Vim forks live at `app/src/code/editor/view/actions.rs:50-79` (there is no top-level `actions.rs` registering them). Pattern confirmed: `text_entry & id!("Vim")` vs `& !id!("Vim")`, where `text_entry = id!("CodeEditorView") & !id!("IMEOpen")` — pure `Identifier` atoms. | `app/src/code/editor/view/actions.rs:47-69` |
| 2 | `BindingId` per-run `AtomicUsize` at `keymap.rs:264-272` | Correct mechanism, stale lines: doc 257-260, `struct BindingId(pub usize)` at 261-262, `static NEXT_BINDING_ID` at 264, `new()` at 266-273 — in `crates/warpui_core/src/keymap.rs`, not `keymap/keymap.rs`. | `crates/warpui_core/src/keymap.rs:257-273` |
| 3 | terminal same-key shape at `init.rs:459-460` | The predicate spans `app/src/terminal/view/init.rs:457-461`; the key is `"TerminalView_BlockSelectionCardinality"` with values `"One"`/`"None"`. | `app/src/terminal/view/init.rs:457-461` |
| 4 | (pin requested) "Equal/NotEqual fail OPEN" | The spec body is already correct; pinned here from code: `Equal` fails **CLOSED** (`.unwrap_or(false)`), only `NotEqual` fails **OPEN** (`.unwrap_or(true)`). | `context.rs:104-113` |
| 5 | (pin requested) `override⊆binding` direction contradicts the prose example | Pinned: `implies(a,b)` = *a ⊨ b* (a stronger ⇒ b); the criterion is "answer ≠ oracle", over **or** under. | this doc, Deliverable B |
| 6 | `ContextPredicate` "derive(PartialEq)" | Full derive is `#[derive(Debug, Clone, Eq, PartialEq)]` — `Eq` is also present (total equality), relevant to any future HashMap-key use but not to A2-Q4. | `context.rs:9` |

---

## Final verdict

**A2-Q4 resolves to: the override-targeting key must be an author-assigned stable id field; subsumption is faithfully implementable but implementable-but-fragile.** Earned, not asserted — all three refutation skeptics SURVIVED at high confidence:

1. **Exact / BindingId / hash are disqualified by code already read** (refutation pass, skeptic 3, SURVIVED). `Exact` cannot be built from natural input (no `FromStr`/`Display`) and is order-sensitive (author-ordered `And`/`Or`, no canonicalization); `BindingId` is a per-run `AtomicUsize` with no persistence path (custom keybindings save by **name**); name+predicate-hash drifts on edit by definition. ⇒ the A2-Q3 schema override key must be an **author-assigned stable id field**. No histogram or orphan harness was needed (or built) to reach this — it is forced by reasoning.
2. **`Subsumes` is faithfully implementable** (Deliverable B, skeptic 1, SURVIVED). A per-key value-domain `implies()` is bit-identical to `eval` over reachable worlds (disagreement 0 on a fixture set provably containing the awkward shapes), and the obvious `2^k`-over-atoms enumerator is **provably unsound** on the real terminal same-key shape while mirage-clean on the synthetic Vim forks — so the spec's dominant false-green is real and is caught.
3. **…but fragile, and must carry a refuse guard.** Any shipped subsumption primitive must carry an explicit `undecidable/too-large ⇒ refuse and warn, never silently mis-target` guard. The guard fires on **dimensionality** (product of many keys/identifiers), since a wide single-key value domain is linear (cheap) — this **refines the spec's residual-risk (b)**, which framed the danger as a large same-key value domain.

**Decisive in conjunction with A2-Q5 = mutate**, which holds (mutate is retained — `cross-axis-sequencing.md:75,88`). If A2-Q5 had selected inject, A2-Q4 would collapse to "store `{name, trigger, predicate}` as a higher-precedence binding; dispatch `eval` (`matcher.rs:262`) selects by precedence, no relation needed" — but it does not.

**Net:** make the A2-Q3 override key an author-assigned stable id. Treat `Subsumes` as **available but not shipped by default** — it is faithfully implementable today, but is fragile to high-dimensional or config-authored/interned predicates (X7/R3a) and must never ship without the refuse-and-warn guard. The fidelity probe is throwaway; its reproducible evidence lives in this branch's history (`git show` the `oracle`/`candidate`/`foil` commits) and the production functions are stripped in the final commit.

---

## Unblocks / residual risk

- **Feeds A2-Q3:** the override key becomes an author-assigned stable id field. **And (if A2-Q5 = mutate and id wins, both of which hold):** activates `get_binding_by_name` becoming **id-aware** (today `fn get_binding_by_name(&self, name: &str)`, `keymap.rs:379`) and A3-Q6, and Axis-5 R9 (the catalog must surface a stable per-binding handle). The original Unblocks listing only "Feeds A2-Q3" was incomplete (cycle 2).
- **Gated by / conditional on:** A2-Q5 = mutate (holds — see Gate status); the editable same-name-fork population still does not exist (A2-Q5 option-D migration unbuilt), so the recommendation is made **robust to unknown future predicate spellings**, not validated against them. Any future same-name-fork test folds into the **A2-Q17** harness, not a parallel one.
- **Residual risk (refined, cycle 2):** the budget bounds the **product** of per-key/per-identifier domains. A single key contributes (n+1) **linearly** — so a wide single-key value domain is cheap but a key with ≥~100 000 distinct values *does* trip the refuse path; identifiers contribute ×2 each (**exponential**, trips at ~17). Production's real maximum is ~8 distinct identifiers (`init.rs:312-323`), comfortably under threshold. So any shipped subsumption primitive must carry the `undecidable/too-large ⇒ refuse and warn` guard for high-**dimensional** predicates. This **refines the spec's residual-risk (b)** (which framed the danger as a large same-key value domain) and corrects an over-statement in this memo's own first draft.
- **Representation hazard (cycle 2):** the whole fidelity model assumes `&'static str` **content** equality (`Context.set`/`map`, `collect_atoms` dedup by content `Ord`). If X7/R3a interning moves `eval` to **id-based** (pointer/`u32`) equality, the candidate's content-based dedup could diverge from `eval` — a distinct hazard from the budget concern, only partially captured by the spec's X7/R3a residual.
- **Explicitly not built** (scope discipline): no `canonical_id`/commutative canonicalization (→ A2-Q6/A2-Q15), no `update_custom_trigger_scoped` (→ A2-Q5), no `{0,1,≥2}` histogram, no orphan-rate harness.
