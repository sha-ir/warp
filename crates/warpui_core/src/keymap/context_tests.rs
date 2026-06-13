use super::macros::*;
use super::*;

#[test]
fn test_context_predicate_eval() -> anyhow::Result<()> {
    let predicate = id!("a") & id!("b") | eq!("c", "d");

    let mut context = Context::default();
    context.set.insert("a");
    assert!(!predicate.eval(&context));

    context.set.insert("b");
    assert!(predicate.eval(&context));

    context.set.remove("b");
    context.map.insert("c", "x");
    assert!(!predicate.eval(&context));

    context.map.insert("c", "d");
    assert!(predicate.eval(&context));

    let predicate = !id!("a");
    assert!(predicate.eval(&Context::default()));

    Ok(())
}

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

    // always! does NOT subsume K2!=X, because the world K2=X is a counterexample.
    let always_true = always!();
    let not_none2 = ne!("K2", "X");
    assert!(
        !always_true.subsumes_reachable(&not_none2),
        "always! must NOT subsume K2!=X (world K2=X is a counterexample)"
    );

    // ABSENT-WORLD anchors (hand-computed, so they catch a "drop the absent choice" bug in
    // world selection regardless of domains()): the SOLE counterexample is the absent key.
    // always! does NOT subsume K2==X: when K2 is absent, Equal fails CLOSED (=> false).
    assert!(
        !always!().subsumes_reachable(&eq!("K2", "X")),
        "always! must NOT subsume K2==X (sole counterexample: K2 absent => Equal fails closed)"
    );
    // K2==X DOES subsume K2!=Y (X != Y), exercising present-mentioned vs the absent/other worlds.
    assert!(
        eq!("K2", "X").subsumes_reachable(&ne!("K2", "Y")),
        "K2==X must subsume K2!=Y"
    );
}

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
        // (iv) absent-key EQUAL (fail-CLOSED): sole counterexample is K2 absent. Guards the
        // candidate's absent world — a drop-absent bug makes implies_per_key say Some(true) here
        // while the independent oracle (which keeps absent) says false => bit-identity goes red.
        (always!(), eq!("K2", "X"), "always_vs_equal_absent"),
        // (v) complex pure-Identifier shapes. Production reaches 8 distinct idents + nested
        // Or-in-And (init.rs:312-323) and De-Morgan !(A&B) (input.rs:2071-2076, editor/view/mod.rs).
        // For pure-Identifier predicates the per-key model degenerates to a full 2^n truth table,
        // so it is exact regardless of Boolean nesting — demonstrated here rather than only argued.
        (
            id!("Terminal") & (id!("AltScreen") | id!("LongRunningCommand")) & !id!("IMEOpen"),
            id!("Terminal"),
            "complex_dnf_subsumes_terminal",
        ),
        (
            id!("CodeEditorView") & !(id!("AgentView") & id!("CtrlEnter")),
            id!("CodeEditorView"),
            "demorgan_subsumes_codeeditor",
        ),
    ]
}

/// Max number of distinct values mentioned for any single key in `p`.
fn max_values_per_key(p: &ContextPredicate) -> usize {
    let mut idents = BTreeSet::new();
    let mut kv = BTreeMap::new();
    p.collect_atoms(&mut idents, &mut kv);
    kv.values().map(|s| s.len()).max().unwrap_or(0)
}

/// Max distinct values for any single key UNIONED across both sides of a pair. (Per-side
/// `max_values_per_key` would miss the mutex shape, where each side holds exactly one value.)
fn union_max_values_per_key(l: &ContextPredicate, r: &ContextPredicate) -> usize {
    let mut idents = BTreeSet::new();
    let mut kv = BTreeMap::new();
    l.collect_atoms(&mut idents, &mut kv);
    r.collect_atoms(&mut idents, &mut kv);
    kv.values().map(|s| s.len()).max().unwrap_or(0)
}

/// Does `p` contain an `Equal` atom anywhere?
fn has_equal(p: &ContextPredicate) -> bool {
    match p {
        ContextPredicate::Equal(_, _) => true,
        ContextPredicate::Identifier(_)
        | ContextPredicate::NotEqual(_, _)
        | ContextPredicate::Just(_) => false,
        ContextPredicate::Not(c) => has_equal(c),
        ContextPredicate::And(a, b) | ContextPredicate::Or(a, b) => has_equal(a) || has_equal(b),
    }
}

/// Does `p` contain a `NotEqual` atom anywhere?
fn has_notequal(p: &ContextPredicate) -> bool {
    match p {
        ContextPredicate::NotEqual(_, _) => true,
        ContextPredicate::Identifier(_)
        | ContextPredicate::Equal(_, _)
        | ContextPredicate::Just(_) => false,
        ContextPredicate::Not(c) => has_notequal(c),
        ContextPredicate::And(a, b) | ContextPredicate::Or(a, b) => {
            has_notequal(a) || has_notequal(b)
        }
    }
}

#[test]
fn a2q4_fixture_set_provably_contains_required_shapes() {
    let fx = a2q4_fixtures();
    // (ii-a) the init.rs Or shape: a SINGLE predicate with >=2 values on one key.
    assert!(
        fx.iter()
            .any(|(l, r, _)| max_values_per_key(l) >= 2 || max_values_per_key(r) >= 2),
        "must contain the init.rs same-key multi-value Or shape"
    );
    // (ii-b) the DISCRIMINATING same-key mutual-exclusion shape (the foil's blind spot):
    // Equal(k,v1) on one side, NotEqual(k,v2) on the other, same key, >=2 values UNIONED across
    // the pair. The old per-side check scored these traps l=1,r=1 and was satisfied only by the
    // benign Or fixture the foil gets RIGHT — so it never enforced the discriminating shape.
    assert!(
        fx.iter().any(|(l, r, _)| {
            union_max_values_per_key(l, r) >= 2
                && ((has_equal(l) && has_notequal(r)) || (has_equal(r) && has_notequal(l)))
        }),
        "must contain the same-key Equal-vs-NotEqual mutual-exclusion shape"
    );
    // (iii) absent-key Equal (fail-CLOSED) shape, asserted STRUCTURALLY (not by label string):
    // Just(true) on one side, an Equal atom on the other => sole counterexample is the absent
    // world, which guards the candidate's absent choice.
    assert!(
        fx.iter().any(|(l, r, _)| {
            (matches!(l, ContextPredicate::Just(true)) && has_equal(r))
                || (matches!(r, ContextPredicate::Just(true)) && has_equal(l))
        }),
        "must contain an absent-key Equal (fail-closed) case"
    );
    // (iv) BOTH discriminating populations must be present, so neither can be silently dropped
    // (which would vacuously pass the foil test) while this guard stays green.
    assert!(
        fx.iter().filter(|(_, _, label)| label.ends_with("_trap")).count() >= 1,
        "must contain >=1 same-key trap fixture"
    );
    assert!(
        fx.iter().filter(|(_, _, label)| label.starts_with("vim_")).count() >= 1,
        "must contain >=1 pure-Identifier Vim mirage fixture"
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
    assert_eq!(
        disagreements, 0,
        "per-key candidate must equal the reachable-world oracle"
    );
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
    assert_eq!(
        many.implies_per_key(&always!()),
        None,
        "high-dimensional predicate must refuse"
    );

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

#[test]
fn a2q4_foil_2k_is_caught_on_same_key_and_mirages_on_vim() {
    let mut total_disagreements = 0;
    // vim fixtures the foil GOT RIGHT — incremented AFTER the agree-assert, so it is non-vacuous
    // (a disagreement panics first; it cannot silently stay 0 the way a post-assert `if disagrees`
    // counter would). This is what makes the mirage demonstration robust to fixture/label drift.
    let mut vim_agreed = 0;
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
            assert!(
                !disagrees,
                "[{label}] foil MUST agree on pure-Identifier Vim shape (mirage)"
            );
            vim_agreed += 1; // reached only when the foil agreed on a vim fixture
        }
        if label.ends_with("_trap") {
            assert!(
                disagrees,
                "[{label}] foil MUST disagree on the same-key mutual-exclusion shape"
            );
            trap_disagreements += 1;
        }
    }

    // The trap is real: the naive 2^k enumerator is unsound on >=1 same-key shape...
    assert!(
        total_disagreements > 0,
        "foil must disagree with the oracle somewhere"
    );
    assert!(
        trap_disagreements >= 1,
        "the same-key trap fixtures must be the disagreement source"
    );
    // ...and it would have shipped clean against a synthetic pure-Identifier population: require
    // that >=1 Vim fixture was actually exercised AND agreed.
    assert!(
        vim_agreed >= 1,
        "the Vim mirage population must be exercised (>=1 vim fixture the foil gets right)"
    );
}
