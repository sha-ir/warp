//! Sound + complete predicate-overlap oracle for the keymap conflict model.
//!
//! Two bindings registered on the same resolved [`Keystroke`] only *truly*
//! conflict if their [`ContextPredicate`]s can be simultaneously satisfied by
//! some reachable context. Today's conflict map keys purely on the keystroke
//! (see `app/src/settings_view/keybindings.rs`), which over-counts: e.g. the
//! Vim forks `... & id!("Vim")` vs `... & !id!("Vim")` share a keystroke but
//! can never both be active.
//!
//! [`can_both_be_true`] answers "is there an assignment of contexts under which
//! both predicates evaluate true?" by **atom enumeration** — no external SAT
//! crate, no `unsafe`. It reuses [`ContextPredicate::eval`] as the per-assignment
//! oracle, so the satisfiability answer is, by construction, consistent with the
//! semantics the matcher actually runs.
//!
//! ## The atom model
//!
//! The leaves of a [`ContextPredicate`] are three kinds of *atom*:
//!
//! * `Identifier(name)` — a membership test against `Context::set`. Modeled as
//!   an **independent boolean**: a context either contains `name` or not, and
//!   distinct identifiers are unconstrained relative to each other.
//! * `Equal(key, value)` / `NotEqual(key, value)` — tests against
//!   `Context::map`, which maps each `key` to *at most one* `value`. These are
//!   modeled **per key**: a key takes exactly one of the values referenced by
//!   either predicate, **or** an `other/absent` sentinel.
//!
//! Grouping map atoms per key is what makes the enumeration sound:
//!
//! 1. **Map-key exclusivity.** Because a key holds one value at a time,
//!    `Equal(k, "x")` and `Equal(k, "y")` can never both be true. An
//!    independent-boolean shortcut would wrongly allow it. Enumerating one value
//!    per key models the exclusion correctly.
//! 2. **The `NotEqual = Not(Equal)` absent-true asymmetry.** `eval` resolves an
//!    absent key with `unwrap_or(true)` for `NotEqual` (see
//!    `context.rs`): `NotEqual(k, v)` is *true* when `k` is absent. The sentinel
//!    state (key left out of the map) reproduces this: every `Equal(k, *)`
//!    evaluates false and every `NotEqual(k, *)` evaluates true, which is exactly
//!    the behavior of both an absent key *and* a key holding some unreferenced
//!    value. Those two cases are logically indistinguishable to any predicate
//!    built from the referenced atoms, so a single sentinel suffices.
//!
//! ## Safety guard
//!
//! Enumeration is `2^(#id atoms) * Π(#values_per_key + 1)`. On the real keymap
//! this is tiny (predicates are identifier-dominated plus a single 3-valued map
//! key), so it never blows up. A guard nonetheless caps the work: if the atom
//! union exceeds [`MAX_ATOMS`] (or the assignment count exceeds
//! [`MAX_ASSIGNMENTS`]) the function conservatively returns `true` (treat as a
//! potential conflict) and bumps [`overlap_overflow_count`]. This is a safety
//! valve, *not* a measured finding: it cannot fire on data the current model can
//! produce, and the walk harness asserts the counter stays zero.

use std::borrow::Cow;
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::sync::atomic::{AtomicU64, Ordering};

use super::{Context, ContextPredicate};

/// Maximum size of the atom union before [`can_both_be_true`] gives up and
/// returns a conservative `true`. Real predicates are identifier-dominated with
/// a single low-cardinality map key, so the union sits around ~10; 20 leaves
/// generous headroom while still bounding the worst case.
pub const MAX_ATOMS: usize = 20;

/// Hard ceiling on the number of enumerated assignments. Belt-and-suspenders
/// alongside [`MAX_ATOMS`]: a key referencing many values could in principle
/// push the product up even with few distinct atoms. `1 << 21` keeps a single
/// call comfortably sub-millisecond.
const MAX_ASSIGNMENTS: u64 = 1 << 21;

/// Number of times the [`MAX_ATOMS`]/[`MAX_ASSIGNMENTS`] guard fired and forced
/// a conservative `true`. Must remain `0` on the real keymap.
static OVERFLOW_COUNT: AtomicU64 = AtomicU64::new(0);

/// Reads the guard's overflow counter. The walk harness asserts this is `0`
/// after sweeping the real population.
pub fn overlap_overflow_count() -> u64 {
    OVERFLOW_COUNT.load(Ordering::Relaxed)
}

fn as_static(atom: &Cow<'static, str>) -> &'static str {
    match atom {
        Cow::Borrowed(value) => value,
        Cow::Owned(value) => Box::leak(value.clone().into_boxed_str()),
    }
}

/// Resets the overflow counter. Test-only.
#[cfg(test)]
pub fn reset_overlap_overflow_count() {
    OVERFLOW_COUNT.store(0, Ordering::Relaxed);
}

/// The set of atoms referenced by one or more predicates.
///
/// * `ids` — identifier atoms, each an independent boolean.
/// * `map_values` — for each map key, the set of values referenced by an
///   `Equal`/`NotEqual` atom. Enumeration assigns each key one of these values
///   or the `other/absent` sentinel.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct AtomSet {
    pub ids: BTreeSet<Cow<'static, str>>,
    pub map_values: BTreeMap<Cow<'static, str>, BTreeSet<Cow<'static, str>>>,
}

impl AtomSet {
    /// Collects the atoms referenced by a single predicate.
    pub fn collect(pred: &ContextPredicate) -> Self {
        let mut set = Self::default();
        set.add(pred);
        set
    }

    fn add(&mut self, pred: &ContextPredicate) {
        match pred {
            ContextPredicate::Identifier(name) => {
                self.ids.insert(name.clone());
            }
            ContextPredicate::Equal(key, value) | ContextPredicate::NotEqual(key, value) => {
                self.map_values
                    .entry(key.clone())
                    .or_default()
                    .insert(value.clone());
            }
            ContextPredicate::Not(inner) => self.add(inner),
            ContextPredicate::And(left, right) | ContextPredicate::Or(left, right) => {
                self.add(left);
                self.add(right);
            }
            ContextPredicate::Just(_) => {}
        }
    }

    /// Merges another atom set into this one.
    pub fn union_with(&mut self, other: &AtomSet) {
        for id in &other.ids {
            self.ids.insert(id.clone());
        }
        for (key, values) in &other.map_values {
            let entry = self.map_values.entry(key.clone()).or_default();
            for value in values {
                entry.insert(value.clone());
            }
        }
    }

    /// The number of distinct atoms: identifier atoms plus the total number of
    /// referenced `(key, value)` pairs. This is the quantity the [`MAX_ATOMS`]
    /// guard bounds.
    pub fn atom_count(&self) -> usize {
        self.ids.len()
            + self
                .map_values
                .values()
                .map(|values| values.len())
                .sum::<usize>()
    }
}

/// Collects the atoms referenced by a single predicate. Convenience wrapper over
/// [`AtomSet::collect`].
pub fn atoms(pred: &ContextPredicate) -> AtomSet {
    AtomSet::collect(pred)
}

/// Returns `true` iff there exists a [`Context`] under which **both** predicates
/// evaluate true — i.e. the two bindings can be simultaneously active and so
/// genuinely conflict on a shared keystroke.
///
/// Sound and complete over the [`ContextPredicate`] grammar by enumerating every
/// distinguishable assignment of the atom union (identifier booleans × one value
/// or the absent sentinel per map key) and testing it with
/// [`ContextPredicate::eval`]. See the module docs for the atom model and the
/// exclusivity / absent-asymmetry guarantees.
///
/// Returns a conservative `true` (and bumps [`overlap_overflow_count`]) if the
/// atom union exceeds the safety guard; this cannot happen on the real keymap.
pub fn can_both_be_true(a: &ContextPredicate, b: &ContextPredicate) -> bool {
    let mut atom_set = AtomSet::collect(a);
    atom_set.union_with(&AtomSet::collect(b));

    let ids: Vec<Cow<'static, str>> = atom_set.ids.iter().cloned().collect();
    let keys: Vec<(Cow<'static, str>, Vec<Cow<'static, str>>)> = atom_set
        .map_values
        .iter()
        .map(|(key, values)| (key.clone(), values.iter().cloned().collect()))
        .collect();

    let n_id = ids.len();

    // Per-key radix: one slot per referenced value plus the `other/absent`
    // sentinel.
    let map_combos: u64 = keys
        .iter()
        .map(|(_, values)| values.len() as u64 + 1)
        .product();
    let id_combos: u64 = if n_id >= 64 { u64::MAX } else { 1u64 << n_id };
    let total = id_combos.saturating_mul(map_combos);

    // Safety guard. Cannot fire on real data.
    if atom_set.atom_count() > MAX_ATOMS || n_id >= 64 || total > MAX_ASSIGNMENTS {
        OVERFLOW_COUNT.fetch_add(1, Ordering::Relaxed);
        return true;
    }

    let radices: Vec<u64> = keys
        .iter()
        .map(|(_, values)| values.len() as u64 + 1)
        .collect();

    // Enumerate every (map assignment) × (identifier assignment).
    for map_combo in 0..map_combos {
        let mut map: HashMap<&'static str, &'static str> = HashMap::with_capacity(keys.len());
        let mut remainder = map_combo;
        for (index, (key, values)) in keys.iter().enumerate() {
            let radix = radices[index];
            let digit = (remainder % radix) as usize;
            remainder /= radix;
            if digit < values.len() {
                map.insert(as_static(key), as_static(&values[digit]));
            }
            // digit == values.len() => the `other/absent` sentinel: leave the
            // key out of the map so `Equal` reads false and `NotEqual` reads
            // true via `unwrap_or(true)`.
        }

        for id_mask in 0..id_combos {
            let mut active: HashSet<&'static str> = HashSet::with_capacity(n_id);
            for (bit, name) in ids.iter().enumerate() {
                if id_mask & (1u64 << bit) != 0 {
                    active.insert(as_static(name));
                }
            }
            let ctx = Context {
                set: active,
                map: map.clone(),
            };
            if a.eval(&ctx) && b.eval(&ctx) {
                return true;
            }
        }
    }

    false
}

#[cfg(test)]
#[path = "overlap_tests.rs"]
mod tests;
