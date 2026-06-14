//! Differential + adversarial tests for the [`can_both_be_true`] overlap oracle.
//!
//! These use **zero keymap data** — they exercise the pure predicate logic. The
//! property test pits the production atom-enumeration against an *independently
//! written* brute-force truth-table oracle. The two implementations differ on
//! purpose:
//!
//! * production enumerates with an iterative mixed-radix counter and collapses
//!   "key absent" and "key holds an unreferenced value" into one sentinel;
//! * the oracle recurses over keys and represents those two cases **separately**
//!   (an explicit `OTHER` value *and* `None`/absent), so agreement proves the
//!   production collapse is sound and that map-key exclusivity is honored.

use std::borrow::Cow;
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

use super::{
    atoms, can_both_be_true, overlap_overflow_count, reset_overlap_overflow_count, AtomSet,
    MAX_ATOMS,
};
use crate::keymap::macros::*;
use crate::keymap::{Context, ContextPredicate};

// ---------------------------------------------------------------------------
// Independent brute-force oracle
// ---------------------------------------------------------------------------

/// A value distinct from any value the random generator can reference. Used by
/// the oracle to represent "key holds some unreferenced value", kept separate
/// from the absent (`None`) case so we verify production's collapse of the two.
const ORACLE_OTHER: &str = "__oracle_other_sentinel__";

fn collect_atoms(
    pred: &ContextPredicate,
    ids: &mut BTreeSet<Cow<'static, str>>,
    keys: &mut BTreeMap<Cow<'static, str>, BTreeSet<Cow<'static, str>>>,
) {
    match pred {
        ContextPredicate::Identifier(name) => {
            ids.insert(name.clone());
        }
        ContextPredicate::Equal(key, value) | ContextPredicate::NotEqual(key, value) => {
            keys.entry(key.clone()).or_default().insert(value.clone());
        }
        ContextPredicate::Not(inner) => collect_atoms(inner, ids, keys),
        ContextPredicate::And(left, right) | ContextPredicate::Or(left, right) => {
            collect_atoms(left, ids, keys);
            collect_atoms(right, ids, keys);
        }
        ContextPredicate::Just(_) => {}
    }
}

/// Independent ground-truth: does some context satisfy both predicates?
///
/// Enumerates identifier booleans against, per key, every referenced value plus
/// an explicit unreferenced `OTHER` value plus absent (`None`). Recursion +
/// dual sentinels make this structurally independent from the production code.
fn oracle_can_both(a: &ContextPredicate, b: &ContextPredicate) -> bool {
    let mut id_set: BTreeSet<Cow<'static, str>> = BTreeSet::new();
    let mut key_map: BTreeMap<Cow<'static, str>, BTreeSet<Cow<'static, str>>> = BTreeMap::new();
    collect_atoms(a, &mut id_set, &mut key_map);
    collect_atoms(b, &mut id_set, &mut key_map);

    let ids: Vec<Cow<'static, str>> = id_set.into_iter().collect();
    let keys: Vec<(Cow<'static, str>, Vec<Option<Cow<'static, str>>>)> = key_map
        .iter()
        .map(|(key, values)| {
            let mut candidates: Vec<Option<Cow<'static, str>>> =
                values.iter().map(|value| Some(value.clone())).collect();
            candidates.push(Some(ORACLE_OTHER.into())); // an unreferenced value
            candidates.push(None); // absent
            (key.clone(), candidates)
        })
        .collect();

    fn recurse(
        keys: &[(Cow<'static, str>, Vec<Option<Cow<'static, str>>>)],
        index: usize,
        map: &mut HashMap<&'static str, &'static str>,
        ids: &[Cow<'static, str>],
        a: &ContextPredicate,
        b: &ContextPredicate,
    ) -> bool {
        if index == keys.len() {
            for mask in 0..(1usize << ids.len()) {
                let mut set: HashSet<&'static str> = HashSet::new();
                for (bit, name) in ids.iter().enumerate() {
                    if mask & (1 << bit) != 0 {
                        set.insert(as_static(name));
                    }
                }
                let ctx = Context {
                    set,
                    map: map.clone(),
                };
                if a.eval(&ctx) && b.eval(&ctx) {
                    return true;
                }
            }
            return false;
        }

        let (key, candidates) = &keys[index];
        for candidate in candidates {
            match candidate {
                Some(value) => {
                    map.insert(as_static(key), as_static(value));
                }
                None => {
                    map.remove(as_static(key));
                }
            }
            if recurse(keys, index + 1, map, ids, a, b) {
                return true;
            }
        }
        map.remove(as_static(key));
        false
    }

    let mut map: HashMap<&'static str, &'static str> = HashMap::new();
    recurse(&keys, 0, &mut map, &ids, a, b)
}

// ---------------------------------------------------------------------------
// Random predicate generator over a small alphabet
// ---------------------------------------------------------------------------

const ID_NAMES: [&str; 3] = ["A", "B", "C"];
const MAP_KEYS: [&str; 2] = ["k", "m"];
// Three values per key mirrors the only multi-valued context key in production
// (the 3-valued block-selection cardinality), exercising same-key/different
// value exclusivity and the "all referenced values excluded" sentinel path.
const MAP_VALUES: [&str; 3] = ["x", "y", "z"];

fn as_static(atom: &Cow<'static, str>) -> &'static str {
    match atom {
        Cow::Borrowed(value) => value,
        Cow::Owned(value) => Box::leak(value.clone().into_boxed_str()),
    }
}

fn random_predicate(rng: &mut StdRng, depth: u32) -> ContextPredicate {
    if depth == 0 || rng.gen_bool(0.45) {
        match rng.gen_range(0..5) {
            0 => ContextPredicate::Identifier(ID_NAMES[rng.gen_range(0..ID_NAMES.len())].into()),
            1 => ContextPredicate::Equal(
                MAP_KEYS[rng.gen_range(0..MAP_KEYS.len())].into(),
                MAP_VALUES[rng.gen_range(0..MAP_VALUES.len())].into(),
            ),
            2 => ContextPredicate::NotEqual(
                MAP_KEYS[rng.gen_range(0..MAP_KEYS.len())].into(),
                MAP_VALUES[rng.gen_range(0..MAP_VALUES.len())].into(),
            ),
            3 => ContextPredicate::Just(true),
            _ => ContextPredicate::Just(false),
        }
    } else {
        match rng.gen_range(0..3) {
            0 => ContextPredicate::Not(Box::new(random_predicate(rng, depth - 1))),
            1 => ContextPredicate::And(
                Box::new(random_predicate(rng, depth - 1)),
                Box::new(random_predicate(rng, depth - 1)),
            ),
            _ => ContextPredicate::Or(
                Box::new(random_predicate(rng, depth - 1)),
                Box::new(random_predicate(rng, depth - 1)),
            ),
        }
    }
}

// ---------------------------------------------------------------------------
// Differential property test
// ---------------------------------------------------------------------------

#[test]
fn differential_can_both_be_true_matches_brute_force_oracle() {
    const NUM_PAIRS: usize = 100_000;
    let mut rng = StdRng::seed_from_u64(0x5A5F_C0FF_EE12_3456);

    // Coverage bookkeeping so a green can't hide a degenerate corpus.
    let mut same_key_diff_value_pairs = 0u64;
    let mut not_equal_atom_pairs = 0u64;
    let mut both_true_results = 0u64;
    let mut max_atom_union = 0usize;

    for i in 0..NUM_PAIRS {
        let a = random_predicate(&mut rng, 3);
        let b = random_predicate(&mut rng, 3);

        let got = can_both_be_true(&a, &b);
        let want = oracle_can_both(&a, &b);
        assert_eq!(
            got, want,
            "can_both_be_true disagreed with oracle on pair {i}: a={a:?} b={b:?} (got {got}, want {want})",
        );

        if got {
            both_true_results += 1;
        }

        let mut union = atoms(&a);
        union.union_with(&atoms(&b));
        max_atom_union = max_atom_union.max(union.atom_count());
        if union.map_values.values().any(|values| values.len() >= 2) {
            same_key_diff_value_pairs += 1;
        }
        if contains_not_equal(&a) || contains_not_equal(&b) {
            not_equal_atom_pairs += 1;
        }
    }

    // The corpus must actually exercise the hard cases the oracle exists for.
    assert!(
        same_key_diff_value_pairs > 1_000,
        "corpus did not exercise same-key/different-value exclusivity (only {same_key_diff_value_pairs})",
    );
    assert!(
        not_equal_atom_pairs > 1_000,
        "corpus did not exercise NotEqual / absent-asymmetry atoms (only {not_equal_atom_pairs})",
    );
    assert!(
        both_true_results > 1_000,
        "corpus produced too few satisfiable pairs ({both_true_results}); generator may be degenerate",
    );
    // The safety guard must be unreachable for these small predicates.
    assert!(
        max_atom_union <= MAX_ATOMS,
        "max atom union {max_atom_union} exceeded guard {MAX_ATOMS}; corpus would trip the overflow path",
    );
}

fn contains_not_equal(pred: &ContextPredicate) -> bool {
    match pred {
        ContextPredicate::NotEqual(_, _) => true,
        ContextPredicate::Identifier(_)
        | ContextPredicate::Equal(_, _)
        | ContextPredicate::Just(_) => false,
        ContextPredicate::Not(inner) => contains_not_equal(inner),
        ContextPredicate::And(left, right) | ContextPredicate::Or(left, right) => {
            contains_not_equal(left) || contains_not_equal(right)
        }
    }
}

// ---------------------------------------------------------------------------
// Hand-written adversarial units
// ---------------------------------------------------------------------------

#[test]
fn adversarial_explicit_negation_is_unsatisfiable() {
    // id(A) vs !id(A): an identifier cannot be both present and absent.
    assert!(!can_both_be_true(&id!("A"), &!id!("A")));
}

#[test]
fn adversarial_subsumption_is_satisfiable() {
    // id(A) vs id(A) & id(B): satisfied by a context with both A and B.
    assert!(can_both_be_true(&id!("A"), &(id!("A") & id!("B"))));
}

#[test]
fn adversarial_same_key_different_value_is_unsatisfiable() {
    // eq(k,x) vs eq(k,y): map-key exclusivity — k holds at most one value.
    assert!(!can_both_be_true(&eq!("k", "x"), &eq!("k", "y")));
}

#[test]
fn adversarial_equal_vs_not_equal_same_value_is_unsatisfiable() {
    // eq(k,x) vs ne(k,x): NotEqual is exactly Not(Equal).
    assert!(!can_both_be_true(&eq!("k", "x"), &ne!("k", "x")));
}

#[test]
fn adversarial_not_equal_satisfied_via_absent_sentinel() {
    // ne(k,'None') paired with anything trivially-true is satisfiable because an
    // absent key makes NotEqual true (the unwrap_or(true) asymmetry).
    assert!(can_both_be_true(&ne!("k", "None"), &always!()));
    // Two distinct NotEquals are jointly satisfiable via the absent sentinel.
    assert!(can_both_be_true(&ne!("k", "x"), &ne!("k", "y")));
    // Excluding every referenced value is still satisfiable — only the
    // absent/other sentinel works, proving the sentinel is reachable.
    assert!(can_both_be_true(
        &(ne!("k", "x") & ne!("k", "y") & ne!("k", "z")),
        &always!(),
    ));
}

#[test]
fn not_equal_on_absent_key_evaluates_true() {
    // Anchors the asymmetry the absent sentinel reproduces: against an empty
    // context, NotEqual is true and Equal is false (context.rs unwrap_or).
    let empty = Context::default();
    assert!(ne!("k", "None").eval(&empty));
    assert!(!eq!("k", "None").eval(&empty));
}

// ---------------------------------------------------------------------------
// Atom collector + safety guard
// ---------------------------------------------------------------------------

#[test]
fn atom_set_collects_and_unions() {
    let a = id!("A") & eq!("k", "x");
    let b = ne!("k", "y") | id!("B");

    let mut union: AtomSet = atoms(&a);
    assert_eq!(
        union.ids.iter().map(|id| &**id).collect::<Vec<_>>(),
        vec!["A"]
    );
    assert_eq!(union.map_values.get("k").unwrap().len(), 1); // x

    union.union_with(&atoms(&b));
    assert_eq!(union.ids.len(), 2); // A, B
    assert_eq!(union.map_values.get("k").unwrap().len(), 2); // x, y
    assert_eq!(union.atom_count(), 4); // A, B, (k,x), (k,y)
}

#[test]
fn guard_returns_conservative_true_and_counts_overflow() {
    // This is the ONLY test that touches the global overflow counter, so the
    // reset/assert pair below is race-free under parallel execution.
    reset_overlap_overflow_count();

    // 21 distinct identifier atoms exceeds MAX_ATOMS (20).
    const NAMES: [&str; 21] = [
        "a00", "a01", "a02", "a03", "a04", "a05", "a06", "a07", "a08", "a09", "a10", "a11", "a12",
        "a13", "a14", "a15", "a16", "a17", "a18", "a19", "a20",
    ];
    let mut pred = id!(NAMES[0]);
    for name in &NAMES[1..] {
        pred = pred & id!(*name);
    }

    // Two satisfiable copies; an exact enumeration would return true anyway, so
    // we assert the *counter* moved to prove the guard (not enumeration) fired.
    assert!(can_both_be_true(&pred, &pred));
    assert_eq!(overlap_overflow_count(), 1);

    reset_overlap_overflow_count();
}
