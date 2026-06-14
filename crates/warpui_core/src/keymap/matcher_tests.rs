use super::*;
use crate::keymap::macros::*;

#[test]
fn test_matcher() -> anyhow::Result<()> {
    #[derive(Debug, PartialEq)]
    enum Action {
        A(String),
        B,
        AB,
    }

    let keymap = Keymap::new(vec![
        FixedBinding::new("a", Action::A("b".into()), id!("a")),
        FixedBinding::new("b", Action::B, id!("a")),
        FixedBinding::new("a b", Action::AB, id!("a") | id!("b")),
    ]);

    let mut ctx_a = Context::default();
    ctx_a.set.insert("a");

    let mut ctx_b = Context::default();
    ctx_b.set.insert("b");

    let mut matcher = Matcher::new(keymap);

    let view_id = EntityId::new();

    // Basic match
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b".into())
    );

    // Multi-keystroke match
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AB
    );

    // Failed matches don't interfere with matching subsequent keys
    assert!(matcher.test_keystroke("x", view_id, &ctx_a).is_none());
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b".into())
    );

    // Pending keystrokes are cleared when the context changes
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::B
    );

    let mut ctx_c = Context::default();
    ctx_c.set.insert("c");

    // Pending keystrokes are maintained per-view
    let view_id1 = EntityId::new();
    let view_id2 = EntityId::new();
    assert_ne!(view_id1, view_id2);
    assert!(matcher.test_keystroke("a", view_id1, &ctx_b).is_none());
    assert!(matcher.test_keystroke("a", view_id2, &ctx_c).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id1, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AB
    );

    Ok(())
}

#[test]
fn test_editable_binding_matching() {
    #[derive(Debug, PartialEq)]
    enum Action {
        A(&'static str),
        B,
        AOrB,
    }

    let mut keymap = Keymap::default();
    use crate::keymap::macros::*;
    keymap.register_editable_bindings([
        EditableBinding::new("a", "Action for A", Action::A("b"))
            .with_key_binding("a")
            .with_context_predicate(id!("a")),
        EditableBinding::new("b", "Action for B", Action::B)
            .with_key_binding("b")
            .with_context_predicate(id!("a")),
        EditableBinding::new("a_or_b", "Action for A or B", Action::AOrB)
            .with_key_binding("a b")
            .with_context_predicate(id!("a") | id!("b")),
    ]);

    let mut ctx_a = Context::default();
    ctx_a.set.insert("a");

    let mut ctx_b = Context::default();
    ctx_b.set.insert("b");

    let mut matcher = Matcher::new(keymap);

    let view_id = EntityId::new();

    // Basic match
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b"),
    );

    // Multi-keystroke match
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AOrB
    );

    // Failed matches don't interfere with matching subsequent keys
    assert!(matcher.test_keystroke("x", view_id, &ctx_a).is_none());
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b")
    );

    // Pending keystrokes are cleared when the context changes
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::B
    );

    let mut ctx_c = Context::default();
    ctx_c.set.insert("c");

    // Pending keystrokes are maintained per-view
    let view_id1 = EntityId::new();
    let view_id2 = EntityId::new();
    assert_ne!(view_id1, view_id2);
    assert!(matcher.test_keystroke("a", view_id1, &ctx_b).is_none());
    assert!(matcher.test_keystroke("a", view_id2, &ctx_c).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id1, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AOrB
    );
}

#[test]
fn test_bindings_for_context() {
    #[derive(Debug)]
    enum Action {
        A,
        B,
        C,
    }
    let keymap = Keymap::new(vec![
        FixedBinding::new("a", Action::A, id!("a")),
        FixedBinding::new("b", Action::B, id!("b")),
        FixedBinding::new("c", Action::C, id!("b")),
    ]);
    let matcher = Matcher::new(keymap);

    let mut ctx_a = Context::default();
    ctx_a.set.insert("a");

    let mut ctx_b = Context::default();
    ctx_b.set.insert("b");

    // Getting bindings for the 'a' context returns a single result
    let ctx_a_bindings = matcher
        .bindings_for_context(ctx_a)
        .filter_map(|bind| match bind.trigger {
            Trigger::Keystrokes(keys) => {
                assert_eq!(keys.len(), 1);
                Some(keys[0].normalized())
            }
            _ => None,
        })
        .collect::<Vec<_>>();

    assert_eq!(ctx_a_bindings.len(), 1);
    assert_eq!(ctx_a_bindings, vec!["a"]);

    // Getting bindings for the 'b' context returns two results, in the reverse order they
    // added, so the "c" binding first followed by the "b" binding
    let ctx_b_bindings = matcher
        .bindings_for_context(ctx_b)
        .filter_map(|bind| match bind.trigger {
            Trigger::Keystrokes(keys) => {
                assert_eq!(keys.len(), 1);
                Some(keys[0].normalized())
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(ctx_b_bindings, vec!["c", "b"]);
}

impl Matcher {
    fn test_keystroke(
        &mut self,
        keystroke: &str,
        view_id: EntityId,
        ctx: &Context,
    ) -> Option<Arc<dyn Action>> {
        match self.push_keystroke(Keystroke::parse(keystroke).unwrap(), view_id, ctx) {
            MatchResult::Action(action) => Some(action),
            _ => None,
        }
    }
}

trait AsAction {
    fn as_action<A: Action>(&self) -> &A;
}

impl AsAction for Arc<dyn Action> {
    fn as_action<A: Action>(&self) -> &A {
        self.as_ref().as_any().downcast_ref::<A>().unwrap()
    }
}

/// A3-Q20 (merged X12) — matcher-scan perf bench. Throwaway `--release` microbench that
/// settles whether the R4 per-context trie is needed for Axis-3 PERF, or stays deferred.
///
/// Separates the two costs the spec conflates:
///   (a)  PRODUCTION scan  — real `push_keystroke` over `Tracked` editable bindings,
///        so the per-deref `with_cache` TLS tax is counted (a `Vec<FixedBinding>` would
///        false-green it to ~0).
///   (a') PLAIN scan       — identical logic over a plain `Vec`, isolating the algorithm
///        from the TLS tax so (b)/(c) compare apples-to-apples.
///   (b)  PREBUILT index   — `HashMap<FirstKeystroke, Vec<idx>>` built once; per-keystroke
///        evals only candidates. The >2x-crossover question.
///   (c)  layered ENVELOPE — collect ALL prefix+context matches, sort by (layer,recency),
///        scan an Unbound layer, NO early return. SYNTHETIC upper bound (the real
///        Unbound/(layer,recency) primitives do not exist yet); load-bearing kill clause.
///   P2   plain-MISS floor — a key matching nothing (cheap n*starts_with, 0 evals).
///   P5   variant-c        — per-binding platform-resolution String alloc; an A6-Q4/R5
///        guardrail ("don't parse per-binding on the hot path"), NOT an R4 verdict.
///
/// Worst case (forces the full no-early-return scan): a 2-key vim-pack of chords sharing
/// leader `g`; pressing `g` (len 1) never exact-matches a len-2 chord, so the scan runs
/// full and retains pending while evaluating every prefix-matching predicate.
///
/// Run: cargo test -p warpui_core --release -- --ignored --nocapture bench_push_keystroke
#[test]
#[ignore = "A3-Q20 (merged X12) matcher-scan perf bench; --release only, run explicitly"]
fn bench_push_keystroke() {
    use std::collections::{HashMap, HashSet};
    use std::hint::black_box;
    use std::time::{Duration, Instant};

    use crate::keymap::ContextPredicate;

    #[derive(Debug)]
    struct BenchAction(#[allow(dead_code)] u32);

    struct Synth {
        keys: Vec<Keystroke>,
        pred: ContextPredicate,
        layer: u8,
        recency: u32,
    }

    fn id_p(s: &'static str) -> ContextPredicate {
        ContextPredicate::Identifier(s)
    }

    // Deep "ctrl-g"-shaped predicate (11 combinators / 12 leaves); evaluates true in the bench ctx.
    fn deep_predicate() -> ContextPredicate {
        (id_p("Terminal") & !id_p("IMEOpen") & (id_p("LRC") | id_p("Alt")) & id_p("F1") & id_p("F2"))
            | (id_p("EditorView") & !id_p("IMEOpen") & id_p("F3"))
            | (id_p("Terminal") & !id_p("IMEOpen") & id_p("F3"))
    }

    // Reproduce the real predicate-depth histogram (depth0 ~54%, depth1 ~35%, tail to ~4,
    // ~1% deep). All evaluate TRUE in the bench ctx so the worst-case scan does full work.
    fn make_predicate(i: usize) -> ContextPredicate {
        const POS: [&str; 8] = ["Terminal", "EditorView", "LRC", "Alt", "F1", "F2", "F3", "ViewTag"];
        let p = POS[i % POS.len()];
        let q = POS[(i / POS.len()) % POS.len()];
        match i % 100 {
            0..=53 => id_p(p),
            54..=88 => id_p(p) & !id_p("IMEOpen"),
            89..=96 => id_p(p) & !id_p("IMEOpen") & id_p(q),
            97..=98 => id_p(p) & !id_p("IMEOpen") & id_p(q) & id_p("F1") & id_p("F2"),
            _ => deep_predicate(),
        }
    }

    fn build(n: usize, vim: usize) -> (Matcher, Vec<Synth>, Keystroke, Context) {
        const FILLER: [&str; 9] = ["a", "b", "c", "d", "e", "f", "h", "i", "j"]; // single keys, never "g"
        let mut editables = Vec::with_capacity(n);
        let mut synth = Vec::with_capacity(n);
        for i in 0..n {
            let pred = make_predicate(i);
            let (chord, keys) = if i < vim {
                (
                    "g a".to_string(),
                    vec![Keystroke::parse("g").unwrap(), Keystroke::parse("a").unwrap()],
                )
            } else {
                let k = FILLER[i % FILLER.len()];
                (k.to_string(), vec![Keystroke::parse(k).unwrap()])
            };
            let name: &'static str = Box::leak(format!("b{i}").into_boxed_str());
            editables.push(
                EditableBinding::new(name, "bench", BenchAction(i as u32))
                    .with_key_binding(&chord)
                    .with_context_predicate(pred.clone()),
            );
            synth.push(Synth { keys, pred, layer: (i % 2) as u8, recency: i as u32 });
        }
        let mut keymap = Keymap::default();
        keymap.register_editable_bindings(editables);
        let matcher = Matcher::new(keymap);

        let leader = Keystroke::parse("g").unwrap();
        let mut ctx = Context::default();
        for tag in ["Terminal", "EditorView", "LRC", "Alt", "F1", "F2", "F3", "ViewTag"] {
            ctx.set.insert(tag);
        }
        (matcher, synth, leader, ctx)
    }

    fn pct(sorted: &[Duration], q: f64) -> Duration {
        let idx = (((sorted.len() as f64) * q) as usize).min(sorted.len() - 1);
        sorted[idx]
    }
    fn report(label: &str, n: usize, mut s: Vec<Duration>) {
        s.sort_unstable();
        println!(
            "  N={n:<5} {label:<22} p50={:.2?}  p99={:.2?}  max={:.2?}",
            pct(&s, 0.50),
            pct(&s, 0.99),
            *s.last().unwrap(),
        );
    }

    assert!(
        !cfg!(debug_assertions),
        "bench_push_keystroke MUST run in --release (debug autotracking/HashMap is 10-50x slower and inverts the result)"
    );

    let leader_miss = Keystroke::parse("z").unwrap(); // prefix-matches nothing

    println!("\nbench_push_keystroke (release) — worst case: leader 'g' shared by a held-pending vim-pack");
    for &n in &[500usize, 835, 2000, 5000] {
        let vim = (n / 2).min(250).max(1);
        let (mut matcher, synth, leader, ctx) = build(n, vim);
        let view = EntityId::new();
        let iters: usize = if n >= 5000 { 50_000 } else { 200_000 };

        // Sanity: the worst-case key must prefix+context-match the full vim-pack (full eval).
        let cand = synth
            .iter()
            .filter(|s| s.keys.starts_with(std::slice::from_ref(&leader)) && s.pred.eval(&ctx))
            .count();
        assert_eq!(cand, vim, "worst-case key must prefix+context-match the whole vim-pack");

        println!("--- N={n} (vim-pack={vim}, iters={iters}) ---");

        // (a) PRODUCTION SCAN — real push_keystroke over Tracked bindings (counts TLS tax).
        {
            let mut t = Vec::with_capacity(iters);
            for _ in 0..iters {
                matcher.pending.clear();
                let start = Instant::now();
                let r = matcher.push_keystroke(leader.clone(), view, &ctx);
                t.push(start.elapsed());
                black_box(matches!(r, MatchResult::Pending));
            }
            report("a: prod scan (Tracked)", n, t);
        }

        // (a') PLAIN SCAN — same logic over a plain Vec (no Tracked) — isolates the algorithm.
        {
            let mut t = Vec::with_capacity(iters);
            for _ in 0..iters {
                let start = Instant::now();
                let mut retain = false;
                for sb in &synth {
                    if sb.keys.starts_with(std::slice::from_ref(&leader)) && sb.pred.eval(&ctx) {
                        if sb.keys.len() == 1 {
                            retain = false;
                            break;
                        }
                        retain = true;
                    }
                }
                t.push(start.elapsed());
                black_box(retain);
            }
            report("a': plain scan", n, t);
        }

        // P2 PLAIN-MISS floor — a key that prefix-matches nothing (0 evals).
        {
            let mut t = Vec::with_capacity(iters);
            for _ in 0..iters {
                let start = Instant::now();
                let mut hit = false;
                for sb in &synth {
                    if sb.keys.starts_with(std::slice::from_ref(&leader_miss)) && sb.pred.eval(&ctx) {
                        hit = true;
                    }
                }
                t.push(start.elapsed());
                black_box(hit);
            }
            report("P2: plain-MISS floor", n, t);
        }

        // (b) PREBUILT first-keystroke index — built once; per-keystroke evals only candidates.
        {
            let mut index: HashMap<Keystroke, Vec<usize>> = HashMap::new();
            for (i, sb) in synth.iter().enumerate() {
                index.entry(sb.keys[0].clone()).or_default().push(i);
            }
            let mut t = Vec::with_capacity(iters);
            for _ in 0..iters {
                let start = Instant::now();
                let mut retain = false;
                if let Some(cands) = index.get(&leader) {
                    for &i in cands {
                        let sb = &synth[i];
                        if sb.pred.eval(&ctx) {
                            if sb.keys.len() == 1 {
                                retain = false;
                                break;
                            }
                            retain = true;
                        }
                    }
                }
                t.push(start.elapsed());
                black_box(retain);
            }
            report("b: prebuilt index", n, t);
        }

        // (c) WORST-CASE LAYERED ENVELOPE — collect ALL matches, sort by (layer,recency),
        // scan an Unbound layer, NO early return. Synthetic upper bound.
        {
            let unbound: HashSet<usize> = HashSet::new();
            let mut t = Vec::with_capacity(iters);
            for _ in 0..iters {
                let start = Instant::now();
                let mut matches: Vec<(u8, std::cmp::Reverse<u32>, usize)> = Vec::new();
                for (i, sb) in synth.iter().enumerate() {
                    if sb.keys.starts_with(std::slice::from_ref(&leader)) && sb.pred.eval(&ctx) {
                        matches.push((sb.layer, std::cmp::Reverse(sb.recency), i));
                    }
                }
                matches.sort_unstable();
                let winner = matches
                    .iter()
                    .find(|&&(_, _, i)| !unbound.contains(&i))
                    .map(|&(_, _, i)| i);
                t.push(start.elapsed());
                black_box(winner);
            }
            report("c: layered ENVELOPE", n, t);
        }

        // P5 VARIANT-C guardrail (A6-Q4/R5, NOT an R4 verdict) — per-binding String alloc.
        {
            let mut t = Vec::with_capacity(iters);
            for _ in 0..iters {
                let start = Instant::now();
                let mut retain = false;
                for sb in &synth {
                    let _resolved = black_box(format!("{}", sb.keys[0].key));
                    if sb.keys.starts_with(std::slice::from_ref(&leader)) && sb.pred.eval(&ctx) {
                        retain = true;
                    }
                }
                t.push(start.elapsed());
                black_box(retain);
            }
            report("P5: variant-c +alloc", n, t);
        }
    }
}
