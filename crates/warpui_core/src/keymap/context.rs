use std::collections::{HashMap, HashSet};

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Context {
    pub set: HashSet<&'static str>,
    pub map: HashMap<&'static str, &'static str>,
}

#[derive(Debug, Clone, Eq, PartialEq)]
pub enum ContextPredicate {
    Identifier(&'static str),
    Equal(&'static str, &'static str),
    NotEqual(&'static str, &'static str),
    Not(Box<ContextPredicate>),
    And(Box<ContextPredicate>, Box<ContextPredicate>),
    Or(Box<ContextPredicate>, Box<ContextPredicate>),
    Just(bool),
}

pub mod macros {
    /// Returns a context predicate identifier.
    #[macro_export]
    macro_rules! id {
        ($val:literal) => {
            $crate::keymap::ContextPredicate::Identifier($val)
        };
        ($val:expr) => {
            $crate::keymap::ContextPredicate::Identifier($val)
        };
    }
    pub use id;

    /// Returns a context predicate which checks whether the given context
    /// key has a particular value.
    #[macro_export]
    macro_rules! eq {
        ($a:literal, $b:literal) => {
            $crate::keymap::ContextPredicate::Equal($a, $b)
        };
    }
    pub use eq;

    /// Returns a context predicate which checks whether the given context
    /// key does _not_ have a particular value.
    #[macro_export]
    macro_rules! ne {
        ($a:literal, $b:literal) => {
            $crate::keymap::ContextPredicate::NotEqual($a, $b)
        };
    }
    pub use ne;

    impl std::ops::Not for ContextPredicate {
        type Output = ContextPredicate;

        fn not(self) -> Self::Output {
            ContextPredicate::Not(Box::new(self))
        }
    }

    impl std::ops::BitAnd for ContextPredicate {
        type Output = ContextPredicate;

        fn bitand(self, rhs: Self) -> Self::Output {
            ContextPredicate::And(Box::new(self), Box::new(rhs))
        }
    }

    impl std::ops::BitOr for ContextPredicate {
        type Output = ContextPredicate;

        fn bitor(self, rhs: Self) -> Self::Output {
            ContextPredicate::Or(Box::new(self), Box::new(rhs))
        }
    }

    /// Returns a context predicate which is always matched.
    #[macro_export]
    macro_rules! always {
        () => {
            $crate::keymap::ContextPredicate::Just(true)
        };
    }
    pub use always;

    use super::ContextPredicate;
}

impl Context {
    pub fn extend(&mut self, other: Context) {
        for v in other.set {
            self.set.insert(v);
        }
        for (k, v) in other.map {
            self.map.insert(k, v);
        }
    }
}

impl ContextPredicate {
    pub fn eval(&self, ctx: &Context) -> bool {
        match self {
            Self::Identifier(name) => ctx.set.contains(*name),
            Self::Equal(left, right) => ctx
                .map
                .get(left)
                .map(|value| value == right)
                .unwrap_or(false),
            Self::NotEqual(left, right) => ctx
                .map
                .get(left)
                .map(|value| value != right)
                .unwrap_or(true),
            Self::Not(pred) => !pred.eval(ctx),
            Self::And(left, right) => left.eval(ctx) && right.eval(ctx),
            Self::Or(left, right) => left.eval(ctx) || right.eval(ctx),
            Self::Just(val) => *val,
        }
    }
}

// ───────────────────────── THROWAWAY A2-Q4 spike ─────────────────────────
// Targeting-relation subsumption-fidelity probe. NOT production code — remove
// with the matching test block in context_tests.rs once A2-Q4-spike-results.md
// captures the evidence. See docs/superpowers/plans/2026-06-13-a2-q4-targeting-relation-spike.md.
use std::collections::{BTreeMap, BTreeSet};

/// A value guaranteed NOT mentioned by any predicate. Used ONLY by the oracle so its
/// per-key world universe includes a present-but-unmentioned value — actively testing
/// the candidate's "absent ≡ present-with-unmentioned-value" lemma instead of sharing it.
const ORACLE_UNMENTIONED_SENTINEL: &str = "\u{1}__a2q4_unmentioned_sentinel__";

#[allow(dead_code)] // throwaway probe: methods are exercised only by the #[cfg(test)] block
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

    /// Oracle-only world universe, built INDEPENDENTLY of the candidate's `domains()`
    /// (it re-decides world selection from scratch), and each key additionally carries a
    /// never-mentioned sentinel present-value. This is what makes `candidate == oracle`
    /// test world SELECTION, not merely enumeration order: if the candidate dropped the
    /// absent world, or if the "absent ≡ present-with-unmentioned-value" lemma were false,
    /// the oracle would diverge and `a2q4_candidate_is_bit_identical_to_oracle` would fail.
    fn oracle_domains(
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
                let mut choices: Vec<Option<&'static str>> = Vec::with_capacity(vs.len() + 2);
                choices.push(None); // absent
                choices.extend(vs.into_iter().map(Some)); // mentioned values
                choices.push(Some(ORACLE_UNMENTIONED_SENTINEL)); // a present-but-unmentioned value
                (k, choices)
            })
            .collect();
        (idents.into_iter().collect(), keys)
    }

    /// ORACLE: does every *reachable* Context world satisfying `self` also satisfy
    /// `other`? Plain recursive enumeration over an INDEPENDENT world universe
    /// (`oracle_domains`) — the ground truth the candidate and foil are scored against.
    fn subsumes_reachable(&self, other: &ContextPredicate) -> bool {
        let (idents, keys) = self.oracle_domains(other);
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
            ctx.set.remove(name);
            if !self.subsumes_rec(other, idents, keys, ident_i + 1, key_i, ctx) {
                return false;
            }
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
                        ctx.map.remove(*k);
                    }
                    Some(v) => {
                        ctx.map.insert(*k, *v);
                    }
                }
                if !self.subsumes_rec(other, idents, keys, ident_i, key_i + 1, ctx) {
                    ctx.map.remove(*k);
                    return false;
                }
            }
            ctx.map.remove(*k);
            return true;
        }
        // leaf world: self ⇒ other
        !self.eval(ctx) || other.eval(ctx)
    }

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
}

#[cfg(test)]
#[path = "context_tests.rs"]
mod tests;
