# A2-Q4 — Targeting-Relation Subsumption Fidelity Spike — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Earn (not assert) the A2-Q4 verdict — the override-targeting key must be an author-assigned stable id, and a per-key value-domain `implies()` *can* be made bit-identical to `ContextPredicate::eval` over the awkward production predicate shapes, but only with an explicit `undecidable/too-large ⇒ refuse` guard — by building a throwaway adversarial fidelity test that proves the per-key enumerator sound *and* proves the obvious 2^k-over-atoms enumerator unsound on the real same-key multi-value shape.

**Architecture:** Three throwaway functions added to `crates/warpui_core/src/keymap/context.rs` (clearly marked, stripped in the final task): a candidate `implies_per_key` (mixed-radix enumeration over per-key value-domains + budget guard), a deliberately-unsound foil `implies_2k` (atoms as independent booleans), and an independent recursive oracle `subsumes_reachable`. A `#[cfg(test)]` fixture set in `context_tests.rs` that *structurally* contains the real Vim-fork shape, the real terminal same-key multi-value shape (`init.rs:457-461`), an absent-key `NotEqual` case, and a high-dimensionality budget-overflow case — and asserts the candidate equals the oracle everywhere (0 disagreements) while the foil disagrees on the same-key shape (>0) and *agrees* on the pure-Identifier Vim shape (the false-green it would have shipped). A paper decision-memo (`A2-Q4-spike-results.md`) settles the other 2.5 relations from already-read code and records corrections to the spec.

**Tech Stack:** Rust, `cargo nextest`, the existing `ContextPredicate`/`Context` types and `id!`/`eq!`/`ne!`/`always!` macros in `crates/warpui_core/src/keymap/context.rs`.

---

## Pre-registered verdict to earn (not assert)

> *The override-targeting key must be an author-assigned stable id field — Exact, BindingId, and name+predicate-hash are all disqualified — AND a per-key value-domain `implies()` can be made bit-identical to `eval` (so subsumption is faithfully implementable), but any shipped subsumption primitive must carry an explicit `undecidable/too-large ⇒ refuse and warn, never silently mis-target` guard.*

The spec already states this. Every task below either tries to **break** it or **corrects the spec's supporting argument** where the code disagrees. A green that comes only from pure-Identifier fixtures is the false-green the spec names; the test is built to fail in that case.

## Gate status (resolved during brainstorming — do not re-litigate)

- **A2-Q5 is effectively settled as a split answer:** `cross-axis-sequencing.md:75,88` pre-registers *"mutate is NOT subsumed by inject … update_custom_trigger SURVIVES in parallel"* (TrackedId-keyed reactive invalidation). So the mutate path is retained, targeting **matters**, and the spec's "kill if A2-Q5=inject" branch does **not** fire. The remaining gate (editable same-name forks don't exist yet — they would come from A2-Q5 option D migrating the ~19 Vim Fixed forks) is exactly why this spike proves the primitive *implementable-but-fragile* rather than running a population histogram.

## Verified facts (from code, 2026-06-13 — citations the memo will cite)

- `ContextPredicate` is `#[derive(Debug, Clone, Eq, PartialEq)]` — structural equality (`context.rs:9`). Variants: `Identifier(&'static str)`, `Equal(&'static str,&'static str)`, `NotEqual(&'static str,&'static str)`, `Not`, `And`, `Or`, `Just(bool)`.
- `eval(&self, ctx: &Context) -> bool` (`context.rs:101-119`): `Equal` → `.unwrap_or(false)` (fails **closed**), `NotEqual` → `.unwrap_or(true)` (fails **open**). `Context { set: HashSet<&'static str>, map: HashMap<&'static str,&'static str> }` — **one** value per key.
- **No** `FromStr`/`Display`/parser for `ContextPredicate` anywhere in the repo.
- Real same-key multi-value shape (`app/src/terminal/view/init.rs:457-461`): `id!("Terminal") & (eq!("TerminalView_BlockSelectionCardinality","One") | eq!("TerminalView_BlockSelectionCardinality","None"))`.
- Real Vim forks (`app/src/code/editor/view/actions.rs:50-79`, **not** the spec's stale `actions.rs:51-70`): `text_entry & id!("Vim")` vs `text_entry & !id!("Vim")`, where `text_entry = id!("CodeEditorView") & !id!("IMEOpen")` — pure `Identifier` atoms.
- `BindingId(pub usize)` minted from a per-run `static NEXT_BINDING_ID: AtomicUsize` (`crates/warpui_core/src/keymap.rs:257-273`, **not** the spec's `keymap.rs:264-272`) ⇒ not persistable across runs.
- `update_custom_trigger` dual-writes `editable_custom_action_bindings` then `editable_bindings` (`keymap.rs:421-433`); `get_binding_by_name(name: &str)` is name-only, not id-aware (`keymap.rs:378-386`); `EditableBinding::new` defaults `context_predicate: ContextPredicate::Just(true)` (`keymap.rs:657`).

---

## Task 0: Create the spike worktree and land the plan on its branch

**Files:**
- Create: git worktree on branch `sha-ir/spike-a2-q4-targeting-relation` off `sha-ir/keybindings-draft`
- Move into branch: `docs/superpowers/plans/2026-06-13-a2-q4-targeting-relation-spike.md` (this file — same location as the A1-Q6 plan)

- [ ] **Step 1: Create the isolated worktree**

REQUIRED SUB-SKILL: use `superpowers:using-git-worktrees` to create the worktree. Target branch `sha-ir/spike-a2-q4-targeting-relation`, base `sha-ir/keybindings-draft`. All remaining tasks run **inside** that worktree.

- [ ] **Step 2: Materialize this plan inside the worktree and commit it**

Ensure this plan file exists at the path above inside the worktree (copy it in if it was authored in the main working tree), then:

```bash
git add docs/superpowers/plans/2026-06-13-a2-q4-targeting-relation-spike.md
git commit -m "spike(keybindings): A2-Q4 plan — targeting-relation subsumption fidelity

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

Expected: clean commit on `sha-ir/spike-a2-q4-targeting-relation`.

---

## Task 1: Draft the paper decision-memo (the 2.5 code-settled relations)

**Files:**
- Create: `docs/specs/2026-06-13-improved-keybindings/spike-results/A2-Q4-spike-results.md`

This is **Deliverable A**. Draft now; the verdict + refutation outcomes + final test output are folded in by Tasks 6–7. The paper relations are settled from already-read code and do **not** depend on the test.

- [ ] **Step 1: Write the memo skeleton with the three relation findings**

Create `A2-Q4-spike-results.md` with these sections (fill the verified facts above into each):

1. **Header** — link back to `./README.md` and `./axis-2-scope-and-context-control.md`; date 2026-06-13; "Branch: `sha-ir/spike-a2-q4-targeting-relation` (evidence branch — throwaway `context.rs` fns, stripped in the final commit)".
2. **Verdict to earn (not assert)** — paste the pre-registered verdict above verbatim, with the note that the spike's job is to break it / correct its argument.
3. **Gate status** — the A2-Q5 split-answer finding above (mutate retained ⇒ targeting matters ⇒ test on the critical path).
4. **Paper relation table** — three rows, each with a verified citation:
   | Candidate targeting key | Verdict | Why (from code) | Citation |
   |---|---|---|---|
   | `Exact` (structural `ContextPredicate` equality) | ❌ unusable | `#[derive(…PartialEq)]` is structural + `And`/`Or` non-commutative (no canonicalization) + **zero** `FromStr` ⇒ uninstantiable from natural input, leaks internal predicate spelling | `context.rs:9`, `context.rs:61-75` (BitAnd/BitOr build nested boxes in author order), no-FromStr grep |
   | `BindingId` | ❌ not persistable | minted from per-run `static AtomicUsize` ⇒ a fresh value every process start | `crates/warpui_core/src/keymap.rs:257-273` |
   | name + predicate-hash | ❌ drifts | hashing a mutable predicate changes the key by definition whenever the predicate is edited | n/a (definitional) |
   | **author-assigned stable id field** | ✅ recommended (conditional on A2-Q5=mutate, which holds) | the only handle stable across edits and process restarts | — |
5. **Placeholders for** (filled later): "Subsumption fidelity (test result)", "Adversarial verification pass", "Corrections to spec", "Final verdict".

- [ ] **Step 2: Commit the memo draft**

```bash
git add docs/specs/2026-06-13-improved-keybindings/spike-results/A2-Q4-spike-results.md
git commit -m "spike(keybindings): A2-Q4 memo draft — 2.5 relations settled on paper

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Build the independent oracle + the fixture set (TDD anchor)

**Files:**
- Modify: `crates/warpui_core/src/keymap/context.rs` (add a throwaway `impl ContextPredicate` block after the existing one, ~line 120)
- Test: `crates/warpui_core/src/keymap/context_tests.rs`

The oracle `subsumes_reachable` is the ground truth: it enumerates the **reachable** Context worlds (per-key value-domains + per-identifier present/absent) by plain recursion — structurally different from the candidate's mixed-radix loop, so their agreement has real teeth. Build it first and anchor it with hand-computed cases.

- [ ] **Step 1: Write the failing oracle test with hand-computed answers**

Append to `crates/warpui_core/src/keymap/context_tests.rs`:

```rust
// ───────────────────────── THROWAWAY A2-Q4 spike ─────────────────────────
// Subsumption-fidelity probe. Remove with the throwaway `context.rs` fns once
// the evidence in A2-Q4-spike-results.md is captured.

/// Real terminal same-key multi-value shape (app/src/terminal/view/init.rs:457-461).
fn terminal_cardinality_or() -> ContextPredicate {
    id!("Terminal")
        & (eq!("TerminalView_BlockSelectionCardinality", "One")
            | eq!("TerminalView_BlockSelectionCardinality", "None"))
}

/// Real editor-core text-entry guard (app/src/code/editor/view/actions.rs:47).
fn text_entry() -> ContextPredicate {
    id!("CodeEditorView") & !id!("IMEOpen")
}

#[test]
fn a2q4_oracle_matches_hand_computed_truth() {
    // Vim fork A = text_entry & Vim ; B = text_entry & !Vim. A cannot imply B (Vim vs !Vim).
    let vim_a = text_entry() & id!("Vim");
    let vim_b = text_entry() & !id!("Vim");
    assert!(!vim_a.subsumes_reachable(&vim_b), "Vim fork: A must NOT subsume B");
    // A = text_entry & Vim implies the weaker text_entry.
    assert!(vim_a.subsumes_reachable(&text_entry()), "A must subsume text_entry");

    // Mutual exclusion: BSC=One implies BSC!=None (a key holds one value).
    let one = eq!("TerminalView_BlockSelectionCardinality", "One");
    let not_none = ne!("TerminalView_BlockSelectionCardinality", "None");
    assert!(one.subsumes_reachable(&not_none), "BSC=One must subsume BSC!=None");

    // always! does NOT subsume BSC!=None, because the world BSC=None is a counterexample.
    let always_true = always!();
    let not_none2 = ne!("K2", "X");
    assert!(
        !always_true.subsumes_reachable(&not_none2),
        "always! must NOT subsume K2!=X (world K2=X is a counterexample)"
    );
}
```

- [ ] **Step 2: Run to verify it fails (method missing)**

Run: `cargo nextest run -p warpui_core a2q4_oracle_matches_hand_computed_truth`
Expected: FAIL — `no method named subsumes_reachable found for enum ContextPredicate` (compile error).

- [ ] **Step 3: Implement the oracle + atom-collection helper**

Append to `crates/warpui_core/src/keymap/context.rs` (after the existing `impl ContextPredicate { … }` block, before `#[cfg(test)]`):

```rust
// ───────────────────────── THROWAWAY A2-Q4 spike ─────────────────────────
// Targeting-relation subsumption-fidelity probe. NOT production code — remove
// with the matching test in context_tests.rs once A2-Q4-spike-results.md
// captures the evidence. See docs/superpowers/plans/2026-06-13-a2-q4-targeting-relation-spike.md.
use std::collections::{BTreeMap, BTreeSet};

impl ContextPredicate {
    /// Collect every `Identifier` name into `idents`, and for every `Equal`/`NotEqual`
    /// key the set of values mentioned into `key_values`. (BTree* for deterministic order.)
    fn collect_atoms(
        &self,
        idents: &mut BTreeSet<&'static str>,
        key_values: &mut BTreeMap<&'static str, BTreeSet<&'static str>>,
    ) {
        match self {
            Self::Identifier(name) => {
                idents.insert(*name);
            }
            Self::Equal(k, v) | Self::NotEqual(k, v) => {
                key_values.entry(*k).or_default().insert(*v);
            }
            Self::Not(p) => p.collect_atoms(idents, key_values),
            Self::And(l, r) | Self::Or(l, r) => {
                l.collect_atoms(idents, key_values);
                r.collect_atoms(idents, key_values);
            }
            Self::Just(_) => {}
        }
    }

    /// Build the reachable per-key/per-identifier domains for `self` ∪ `other`.
    /// Each key's choices: index 0 = absent, then one entry per mentioned value.
    /// (Absent is eval-equivalent to "present with an unmentioned value": both make
    /// every Equal false and every NotEqual true, so no extra sentinel is needed.)
    fn domains(
        &self,
        other: &ContextPredicate,
    ) -> (Vec<&'static str>, Vec<(&'static str, Vec<Option<&'static str>>)>) {
        let mut idents = BTreeSet::new();
        let mut key_values = BTreeMap::new();
        self.collect_atoms(&mut idents, &mut key_values);
        other.collect_atoms(&mut idents, &mut key_values);
        let keys = key_values
            .into_iter()
            .map(|(k, vs)| {
                let mut choices: Vec<Option<&'static str>> = Vec::with_capacity(vs.len() + 1);
                choices.push(None);
                choices.extend(vs.into_iter().map(Some));
                (k, choices)
            })
            .collect();
        (idents.into_iter().collect(), keys)
    }

    /// ORACLE: does every *reachable* Context world satisfying `self` also satisfy
    /// `other`? Plain recursive enumeration over the per-key domains — the
    /// independent ground truth the candidate and foil are scored against. No
    /// budget guard (test fixtures are small); panics nowhere.
    fn subsumes_reachable(&self, other: &ContextPredicate) -> bool {
        let (idents, keys) = self.domains(other);
        let mut ctx = Context::default();
        self.subsumes_rec(other, &idents, &keys, 0, 0, &mut ctx)
    }

    fn subsumes_rec(
        &self,
        other: &ContextPredicate,
        idents: &[&'static str],
        keys: &[(&'static str, Vec<Option<&'static str>>)],
        ident_i: usize,
        key_i: usize,
        ctx: &mut Context,
    ) -> bool {
        if ident_i < idents.len() {
            let name = idents[ident_i];
            // absent
            ctx.set.remove(name);
            if !self.subsumes_rec(other, idents, keys, ident_i + 1, key_i, ctx) {
                return false;
            }
            // present
            ctx.set.insert(name);
            let ok = self.subsumes_rec(other, idents, keys, ident_i + 1, key_i, ctx);
            ctx.set.remove(name);
            return ok;
        }
        if key_i < keys.len() {
            let (k, choices) = &keys[key_i];
            for choice in choices {
                match choice {
                    None => {
                        ctx.map.remove(k);
                    }
                    Some(v) => {
                        ctx.map.insert(k, v);
                    }
                }
                if !self.subsumes_rec(other, idents, keys, ident_i, key_i + 1, ctx) {
                    ctx.map.remove(k);
                    return false;
                }
            }
            ctx.map.remove(k);
            return true;
        }
        // leaf world: a ⇒ b
        !self.eval(ctx) || other.eval(ctx)
    }
}
```

- [ ] **Step 4: Run to verify the oracle test passes**

Run: `cargo nextest run -p warpui_core a2q4_oracle_matches_hand_computed_truth`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/warpui_core/src/keymap/context.rs crates/warpui_core/src/keymap/context_tests.rs
git commit -m "spike(keybindings): A2-Q4 reachable-world oracle + hand-computed anchors

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Implement the candidate `implies_per_key` + budget guard (must equal the oracle)

**Files:**
- Modify: `crates/warpui_core/src/keymap/context.rs` (throwaway impl block from Task 2)
- Test: `crates/warpui_core/src/keymap/context_tests.rs`

- [ ] **Step 1: Write the failing candidate test**

Append to `context_tests.rs`:

```rust
/// The full A2-Q4 fixture set, each pair PROVABLY exercising a required shape.
/// (left, right, label)
fn a2q4_fixtures() -> Vec<(ContextPredicate, ContextPredicate, &'static str)> {
    // NOTE: eq!/ne! are LITERAL-ONLY macros (($a:literal,$b:literal)). For a key held
    // in a `const`/variable we must construct ContextPredicate::Equal/NotEqual directly.
    const BSC: &str = "TerminalView_BlockSelectionCardinality";
    vec![
        // (i) pure-Identifier Vim fork — the synthetic population that false-greens 2^k.
        (text_entry() & id!("Vim"), text_entry() & !id!("Vim"), "vim_fork_AB"),
        (text_entry() & id!("Vim"), text_entry(), "vim_A_subsumes_textentry"),
        // (ii) real terminal same-key multi-value Or shape (init.rs:457-461) present verbatim.
        (terminal_cardinality_or(), id!("Terminal"), "terminal_or_subsumes_terminal"),
        // (ii-trap) same-key mutual exclusion tied to the terminal key — the foil's blind spot.
        (
            id!("Terminal") & ContextPredicate::Equal(BSC, "One"),
            id!("Terminal") & ContextPredicate::NotEqual(BSC, "None"),
            "terminal_mutex_trap",
        ),
        (
            ContextPredicate::Equal(BSC, "One"),
            ContextPredicate::NotEqual(BSC, "None"),
            "bare_mutex_trap",
        ),
        // (iii) absent-key NotEqual — exercises NotEqual fail-open and value-domain from NotEqual.
        (always!(), ne!("K2", "X"), "always_vs_notequal"),
        (ne!("K2", "X"), always!(), "notequal_vs_always"),
    ]
}

/// Max number of distinct values mentioned for any single key in `p`.
fn max_values_per_key(p: &ContextPredicate) -> usize {
    let mut idents = BTreeSet::new();
    let mut kv = BTreeMap::new();
    p.collect_atoms(&mut idents, &mut kv);
    kv.values().map(|s| s.len()).max().unwrap_or(0)
}

#[test]
fn a2q4_fixture_set_provably_contains_required_shapes() {
    let fx = a2q4_fixtures();
    // (ii) at least one fixture predicate is the same-key multi-value shape (>=2 values on one key).
    assert!(
        fx.iter().any(|(l, r, _)| max_values_per_key(l) >= 2 || max_values_per_key(r) >= 2),
        "fixture set must contain the init.rs same-key multi-value shape"
    );
    // (iii) at least one fixture contains a NotEqual atom on a key absent from the other side.
    assert!(
        fx.iter().any(|(_, _, label)| *label == "always_vs_notequal"),
        "fixture set must contain an absent-key NotEqual case"
    );
}

#[test]
fn a2q4_candidate_is_bit_identical_to_oracle() {
    let mut disagreements = 0;
    for (l, r, label) in a2q4_fixtures() {
        let oracle = l.subsumes_reachable(&r);
        let candidate = l.implies_per_key(&r);
        if candidate != Some(oracle) {
            eprintln!("[{label}] candidate={candidate:?} oracle={oracle}");
            disagreements += 1;
        }
    }
    assert_eq!(disagreements, 0, "per-key candidate must equal the reachable-world oracle");
}

#[test]
fn a2q4_candidate_refuses_high_dimensional_predicate() {
    // 17 distinct identifiers => 2^17 = 131072 > BUDGET (100_000) => refuse (None), never guess.
    // Refined finding (corrects spec residual-risk (b)): the budget fires on DIMENSIONALITY
    // (product of many keys/idents), NOT on single-key value cardinality, which stays linear.
    const IDENT_POOL: [&str; 17] = [
        "I0", "I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9", "I10", "I11", "I12", "I13",
        "I14", "I15", "I16",
    ];
    let many = (0..IDENT_POOL.len())
        .map(|i| id!(IDENT_POOL[i]))
        .reduce(|a, b| a & b)
        .unwrap();
    assert_eq!(many.implies_per_key(&always!()), None, "high-dimensional predicate must refuse");

    // A single key with a WIDE value domain does NOT overflow (product = n+1, linear).
    const VALUE_POOL: [&str; 12] =
        ["w0", "w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8", "w9", "w10", "w11"];
    let mut wide = ContextPredicate::Equal("WideKey", VALUE_POOL[0]);
    for i in 1..VALUE_POOL.len() {
        wide = wide | ContextPredicate::Equal("WideKey", VALUE_POOL[i]);
    }
    assert!(
        wide.implies_per_key(&always!()).is_some(),
        "single wide-domain key stays tractable (linear, not exponential)"
    );
}
```

- [ ] **Step 2: Run to verify it fails (candidate missing)**

Run: `cargo nextest run -p warpui_core a2q4_candidate`
Expected: FAIL — `no method named implies_per_key found` (compile error).

- [ ] **Step 3: Implement the candidate (mixed-radix + budget guard)**

Inside the throwaway `impl ContextPredicate` block in `context.rs`, add:

```rust
    /// CANDIDATE: per-key value-domain implication, bit-faithful to `eval` over
    /// reachable worlds. `Some(true)` if every reachable world satisfying `self`
    /// satisfies `other`; `Some(false)` on a reachable counterexample; `None` if the
    /// reachable-world product exceeds BUDGET (refuse — never silently mis-target).
    fn implies_per_key(&self, other: &ContextPredicate) -> Option<bool> {
        const BUDGET: u64 = 100_000;
        let (idents, keys) = self.domains(other);

        let mut product: u64 = 1;
        for _ in &idents {
            product = product.saturating_mul(2);
            if product > BUDGET {
                return None;
            }
        }
        for (_, choices) in &keys {
            product = product.saturating_mul(choices.len() as u64);
            if product > BUDGET {
                return None;
            }
        }

        for n in 0..product {
            let mut rem = n;
            let mut ctx = Context::default();
            for ident in &idents {
                let bit = rem % 2;
                rem /= 2;
                if bit == 1 {
                    ctx.set.insert(*ident);
                }
            }
            for (k, choices) in &keys {
                let idx = (rem % choices.len() as u64) as usize;
                rem /= choices.len() as u64;
                if let Some(v) = choices[idx] {
                    ctx.map.insert(*k, v);
                }
            }
            if self.eval(&ctx) && !other.eval(&ctx) {
                return Some(false);
            }
        }
        Some(true)
    }
```

- [ ] **Step 4: Run to verify all three candidate tests pass**

Run: `cargo nextest run -p warpui_core a2q4_`
Expected: PASS for `a2q4_fixture_set_provably_contains_required_shapes`, `a2q4_candidate_is_bit_identical_to_oracle`, `a2q4_candidate_refuses_high_dimensional_predicate` (and the Task-2 oracle test). This proves: subsumption is faithfully implementable AND the refuse guard fires on dimensionality, not single-key cardinality.

- [ ] **Step 5: Commit**

```bash
git add crates/warpui_core/src/keymap/context.rs crates/warpui_core/src/keymap/context_tests.rs
git commit -m "spike(keybindings): A2-Q4 candidate implies_per_key == oracle + refuse guard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Implement the unsound foil `implies_2k` — prove the trap is real and caught

**Files:**
- Modify: `crates/warpui_core/src/keymap/context.rs` (throwaway impl block)
- Test: `crates/warpui_core/src/keymap/context_tests.rs`

This is the load-bearing adversarial assertion: the obvious 2^k-over-atoms enumerator (the one a reasonable engineer writes first) is unsound on the real terminal shape, and the fixture set catches it — while it *agrees* on the pure-Identifier Vim fixtures, which is the false-green the spec warns about.

- [ ] **Step 1: Write the failing foil test**

Append to `context_tests.rs`:

```rust
#[test]
fn a2q4_foil_2k_is_caught_on_same_key_and_mirages_on_vim() {
    let mut total_disagreements = 0;
    let mut vim_disagreements = 0;
    let mut trap_disagreements = 0;

    for (l, r, label) in a2q4_fixtures() {
        let oracle = l.subsumes_reachable(&r);
        let foil = l.implies_2k(&r);
        let disagrees = foil != Some(oracle);
        if disagrees {
            total_disagreements += 1;
            eprintln!("[{label}] FOIL DISAGREES foil={foil:?} oracle={oracle}");
        }
        if label.starts_with("vim_") {
            assert!(!disagrees, "[{label}] foil MUST agree on pure-Identifier Vim shape (mirage)");
            if disagrees {
                vim_disagreements += 1;
            }
        }
        if label.ends_with("_trap") {
            assert!(disagrees, "[{label}] foil MUST disagree on the same-key mutual-exclusion shape");
            trap_disagreements += 1;
        }
    }

    // The trap is real: the naive enumerator is unsound on >=1 same-key shape...
    assert!(total_disagreements > 0, "foil must disagree with the oracle somewhere");
    assert!(trap_disagreements >= 1, "the same-key trap fixtures must be the disagreement source");
    // ...and it would have shipped clean against a synthetic pure-Identifier population.
    assert_eq!(vim_disagreements, 0, "foil is a false-green on the Vim-only population");
}
```

- [ ] **Step 2: Run to verify it fails (foil missing)**

Run: `cargo nextest run -p warpui_core a2q4_foil_2k_is_caught_on_same_key_and_mirages_on_vim`
Expected: FAIL — `no method named implies_2k found` (compile error).

- [ ] **Step 3: Implement the foil (atoms as independent booleans)**

Inside the throwaway `impl ContextPredicate` block in `context.rs`, add:

```rust
    /// DELIBERATELY UNSOUND foil: every distinct atom (`Identifier`/`Equal`/`NotEqual`)
    /// is an INDEPENDENT boolean, enumerated over 2^(#atoms) — admitting impossible
    /// worlds such as `Equal(k,"One") && Equal(k,"None")`. Exists only to prove the
    /// trap is real and the per-key model is the fix. Same `Some/None` contract.
    fn implies_2k(&self, other: &ContextPredicate) -> Option<bool> {
        const BUDGET: u64 = 100_000;
        fn collect(p: &ContextPredicate, atoms: &mut Vec<ContextPredicate>) {
            match p {
                ContextPredicate::Identifier(_)
                | ContextPredicate::Equal(_, _)
                | ContextPredicate::NotEqual(_, _) => {
                    if !atoms.contains(p) {
                        atoms.push(p.clone());
                    }
                }
                ContextPredicate::Not(c) => collect(c, atoms),
                ContextPredicate::And(l, r) | ContextPredicate::Or(l, r) => {
                    collect(l, atoms);
                    collect(r, atoms);
                }
                ContextPredicate::Just(_) => {}
            }
        }
        fn truth(p: &ContextPredicate, atoms: &[ContextPredicate], bits: u64) -> bool {
            match p {
                ContextPredicate::Identifier(_)
                | ContextPredicate::Equal(_, _)
                | ContextPredicate::NotEqual(_, _) => {
                    let idx = atoms.iter().position(|a| a == p).expect("atom indexed");
                    (bits >> idx) & 1 == 1
                }
                ContextPredicate::Not(c) => !truth(c, atoms, bits),
                ContextPredicate::And(l, r) => truth(l, atoms, bits) && truth(r, atoms, bits),
                ContextPredicate::Or(l, r) => truth(l, atoms, bits) || truth(r, atoms, bits),
                ContextPredicate::Just(v) => *v,
            }
        }

        let mut atoms = Vec::new();
        collect(self, &mut atoms);
        collect(other, &mut atoms);
        if atoms.len() >= 17 || (1u64 << atoms.len()) > BUDGET {
            return None;
        }
        for bits in 0..(1u64 << atoms.len()) {
            if truth(self, &atoms, bits) && !truth(other, &atoms, bits) {
                return Some(false);
            }
        }
        Some(true)
    }
```

- [ ] **Step 4: Run to verify the foil test passes (trap caught, mirage confirmed)**

Run: `cargo nextest run -p warpui_core a2q4_foil_2k_is_caught_on_same_key_and_mirages_on_vim`
Expected: PASS — `terminal_mutex_trap` and `bare_mutex_trap` disagree with the oracle (foil says `Some(false)`, oracle says `true`); the Vim fixtures agree (`vim_disagreements == 0`).

- [ ] **Step 5: Run the entire A2-Q4 suite and capture real output for the memo**

Run: `cargo nextest run -p warpui_core a2q4_ --no-capture`
Expected: all `a2q4_*` tests PASS. Copy the exact summary line + the `eprintln!` foil-disagreement lines verbatim — they are the evidence pasted into the memo in Task 6.

- [ ] **Step 6: Commit**

```bash
git add crates/warpui_core/src/keymap/context.rs crates/warpui_core/src/keymap/context_tests.rs
git commit -m "spike(keybindings): A2-Q4 unsound 2^k foil — trap caught on same-key, mirage on Vim

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Adversarial verification pass (3 independent refutation skeptics)

**Files:**
- Modify: `docs/specs/2026-06-13-improved-keybindings/spike-results/A2-Q4-spike-results.md` (Adversarial verification + Corrections sections)

Dispatch three independent subagents, each mandated to **refute** one load-bearing claim by reading the real code (default to "refuted" if uncertain). Run them concurrently (this is the ultracode fan-out step — use the Workflow tool or three parallel `Agent` calls).

- [ ] **Step 1: Dispatch the three refuters concurrently**

Skeptic prompts (each reads real code, returns CONFIRMED/REFUTED + evidence + any spec correction):

1. **"Refute candidate fidelity."** Claim under attack: *`implies_per_key` is bit-identical to `eval` over all reachable Context worlds.* Find a `ContextPredicate` pair (using only `Identifier`/`Equal`/`NotEqual`/`Not`/`And`/`Or`/`Just`) and a real `Context` that `eval` could produce, where `implies_per_key` disagrees with the true `∀ctx: eval(a)⇒eval(b)`. Specifically probe: a value present in `Context.map` that is mentioned in *neither* predicate (does the "absent ≡ unmentioned-value" collapse hold?); nested `Not` over `Or`; a key appearing only in one predicate. Read `context.rs:101-119`.

2. **"Refute the foil's realism."** Claim under attack: *`implies_2k` is the enumerator an engineer would actually write, not a strawman, and its disagreement is genuine unsoundness (not a bug we planted).* Confirm the foil's `Some(false)` on `terminal_mutex_trap` is because it visits the impossible world `Equal(BSC,"One") ∧ NotEqual(BSC,"None")=false` — a world `Context.map` (one value per key) can never produce. Verify against `context.rs` `Context` definition (`:3-7`).

3. **"Refute the disqualifications."** Claims under attack: *BindingId is non-persistable* and *Exact is uninstantiable from natural input*. Re-read `crates/warpui_core/src/keymap.rs:257-273` (is the `AtomicUsize` really per-process, or is there any persistence/serde?) and grep the whole repo for any `FromStr`/`Deserialize`/parser that could construct a `ContextPredicate` from a string, and for any commutative canonicalization of `And`/`Or`.

- [ ] **Step 2: Fold outcomes into the memo**

In `A2-Q4-spike-results.md`, write an **Adversarial verification pass** section: for each skeptic, SURVIVED/PARTIAL/REFUTED + the evidence. Any refutation that lands becomes a correction (e.g., if skeptic 1 finds a world the candidate misses, the verdict downgrades to "subsumption is NOT faithfully implementable as written — author-assigned id is forced"). Record every confirmed spec inaccuracy in the **Corrections to spec** table (seed it with: stale `actions.rs:51-70` → `app/src/code/editor/view/actions.rs:50-79`; `keymap.rs:264-272` → `keymap.rs:257-273`; "Equal/NotEqual fail open" → Equal fails **closed**; pin the `override⊆binding` direction).

- [ ] **Step 3: Commit**

```bash
git add docs/specs/2026-06-13-improved-keybindings/spike-results/A2-Q4-spike-results.md
git commit -m "spike(keybindings): A2-Q4 adversarial verification pass + spec corrections

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Finalize the memo verdict with captured evidence

**Files:**
- Modify: `docs/specs/2026-06-13-improved-keybindings/spike-results/A2-Q4-spike-results.md`

- [ ] **Step 1: Paste the real test output and write the final verdict**

Fill the memo's remaining sections:
- **Subsumption fidelity (test result):** paste the verbatim `cargo nextest` summary + the foil-disagreement `eprintln!` lines from Task 4 Step 5. State plainly: candidate == oracle (0 disagreements over a fixture set provably containing the Vim, terminal same-key, and absent-key NotEqual shapes); foil disagrees on the same-key trap and mirages clean on Vim; refuse guard fires on dimensionality (17 idents → `None`) while a wide single-key value domain stays tractable (linear).
- **Final verdict:** the pre-registered verdict, marked earned (or amended per any landed refutation), with the explicit residual: any shipped subsumption primitive must carry the `undecidable/too-large ⇒ refuse and warn` guard; the per-key model makes large single-key value domains cheap (linear), so the guard is about dimensionality. Note the recommendation is decisive in conjunction with A2-Q5=mutate (which holds).
- **Unblocks/residual:** feeds A2-Q3 (override key = author-assigned stable id field); the same-name-fork population still doesn't exist (A2-Q5 option D unbuilt), so the recommendation is made robust to unknown future spellings, not validated against them; fold any future fork test into A2-Q17.

- [ ] **Step 2: Run the full crate test suite to confirm nothing else broke**

Run: `cargo nextest run -p warpui_core`
Expected: PASS (no regressions from the throwaway additions).

- [ ] **Step 3: Commit**

```bash
git add docs/specs/2026-06-13-improved-keybindings/spike-results/A2-Q4-spike-results.md
git commit -m "spike(keybindings): A2-Q4 final verdict — author-assigned id; subsumption implementable-but-fragile

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Strip the throwaway code (evidence preserved in history)

**Files:**
- Modify: `crates/warpui_core/src/keymap/context.rs` (remove the throwaway `impl` block + the `use BTreeMap/BTreeSet` it added)
- Modify: `crates/warpui_core/src/keymap/context_tests.rs` (remove the `THROWAWAY A2-Q4` block)

The evidence stays reproducible in the prior commits; the branch HEAD leaves production clean, matching the user's "remove after we gather the evidence" intent.

- [ ] **Step 1: Remove the throwaway functions and their test block**

Delete the entire `// ── THROWAWAY A2-Q4 spike ──` `impl ContextPredicate { … }` block (and the `use std::collections::{BTreeMap, BTreeSet};` it introduced) from `context.rs`, and the matching `// ── THROWAWAY A2-Q4 spike ──` block from `context_tests.rs`. Leave the original `test_context_predicate_eval` intact.

- [ ] **Step 2: Confirm the tree builds clean and the original test still passes**

Run: `cargo nextest run -p warpui_core context`
Expected: PASS — only `test_context_predicate_eval` remains; no `a2q4_*` tests; no unused-import or dead-code warnings from the spike.

Run: `cargo build -p warpui_core`
Expected: clean build.

- [ ] **Step 3: Commit the strip**

```bash
git add crates/warpui_core/src/keymap/context.rs crates/warpui_core/src/keymap/context_tests.rs
git commit -m "spike(keybindings): A2-Q4 strip throwaway probe (evidence in HEAD~N + results doc)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 4: Report the branch state**

Summarize: branch `sha-ir/spike-a2-q4-targeting-relation`, the commit range holding the reproducible probe, the results doc path, and the one-line verdict. Offer the finishing-a-development-branch options (land onto `keybindings-draft`, open a PR, or leave the worktree for review).

---

## Self-review (run before handing off for execution)

- **Spec coverage:** Deliverable A (memo, 2.5 relations) → Task 1/5/6. Deliverable B (gated fidelity test) → Tasks 2–4. False-green defense (foil must disagree on same-key, agree on Vim) → Task 4. Refuse guard → Task 3. Adversarial verification + spec corrections → Task 5. Scope discipline (no canonical_id / update_custom_trigger_scoped / histogram / orphan harness) → none added. ✅
- **Placeholder scan:** every code step shows complete code; the only deferred content is the *captured test output* and *refutation outcomes*, which are runtime evidence by design, not placeholders. ✅
- **Type consistency:** `collect_atoms`, `domains`, `subsumes_reachable`/`subsumes_rec`, `implies_per_key`, `implies_2k` signatures match between `context.rs` and every call site in `context_tests.rs`; fixtures use only `id!`/`eq!`/`ne!`/`always!` + `&`/`|`/`!`, all confirmed present. ✅
