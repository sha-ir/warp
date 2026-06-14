[← Back to Spike Designs index](../README.md) · [Spec: Axis 3 — A3-Q20](../axis-3-layering-precedence-unbinding.md)

# A3-Q20 (merged X12) — matcher-scan perf bench · execution plan

**Date:** 2026-06-13
**Status:** Plan, pending user approval before build
**Branch (to create):** `sha-ir/spike-a3-q20-matcher-perf` (worktree under `.claude/worktrees/`)
**Spike kind:** Throwaway `--release` microbench; settles a roadmap-scope question and leaves a CI perf baseline.
**Grounded by:** workflow `wcim8qp1p` (areas: matcher+keymap core, autotracking premise, context distribution, X12 merge delta, test harness scaffold).

---

## 1. Question

At the real binding scale (N ≈ 805–848; static call sites 384/397 fixed + 451 editable), is the **R4 per-context trie** required for Axis-3 **perf**, or does the linear `push_keystroke` scan stay far under the input-latency budget — making the trie a deferred-optional item? Decide via measured `--release` p50/p99/max, not a Fermi guess.

## 2. Grounded corrections that change the build

| Spec assumption | Reality (verified) | Consequence |
|---|---|---|
| Worst case = "most-shared **chord** leader … no single-key completion" | Production has **~1 multi-key chord** (`cmdorctrl-r w`, trivial predicate). Worst case is a **single-key** leader (`escape`=60 candidates) + the deepest predicate (`ctrl-g`, 11 combinators) — **which never coincide on one key** | Force the full no-early-return scan with X12's **synthetic held-pending vim-pack** (150–300 unmodified-letter chords); model fan-out as many single-key bindings sharing a leader, not a chord prefix tree |
| Predicate macros `and!`/`or!` | **No such macros.** AND/OR/NOT are operators `&`/`|`/`!`; leaves are `id!`/`eq!`/`ne!`/`always!` | Generator emits `&`/`|`/`!` |
| `EditableBinding::new(.., predicate)` | predicate attached via `.with_context_predicate(...)` builder | fixture builder shape |
| "bench through any binding vec" | A synthetic `Vec<FixedBinding>` skips the per-deref `with_cache` TLS tax (fixed bindings are untracked) — **false-greens autotracking cost to ~0** | build editable bindings through `register_editable_bindings` (`Tracked<EditableBinding>`) |
| "read-barrier may dominate" | **REFUTED**: `track_read` only inserts dep edges when `rendering_view==Some`, set only in `render_view`; `dispatch_keystroke→push_keystroke` is never render-wrapped → zero edge inserts on the hot path | do **NOT** wrap `push_keystroke` in `render_view`; that measures a config production never runs |

Depth distribution to reproduce (909 predicates): depth0 54%, depth1 35%, depth2 7.7%, tail to depth4, 3 outliers (6/7/11). Grep under-counts true depth (231 predicates are `let`-bound helpers), so the generator's deep tail should reach ~12 leaves.

## 3. Harness (one `#[ignore]` test in `crates/warpui_core/src/keymap/matcher_tests.rs`)

`cargo test -p warpui_core --release -- --ignored --nocapture bench_push_keystroke`. **No criterion** (absent from `warpui_core`; present only in the `editor` crate — do not touch), **no `benches/` dir**, no app-dump binary. Build the synthetic `Keymap` via the real `register_fixed_bindings`/`register_editable_bindings` paths; pre-parse the keystroke outside the timed loop; `std::hint::black_box` the `MatchResult`; compute p50/p99/max from a sorted `Vec<Duration>`; **assert the benched key actually runs the full scan** (instrument candidate-match count); import X12's named-min-spec-CPU + p99-gate discipline (max informational).

## 4. Merged probe list (A3-Q20 ∪ X12)

| # | Probe | Source | Measures |
|---|---|---|---|
| P1 | current early-return scan on worst-case **held-pending vim-pack** | A3-Q20 (a) + X12 cell B merged | the real predicate-eval tail (eval reachable only via the `&&` after the prefix gate) |
| P2 | plain-MISS baseline (cheap non-matching key) | **NEW (X12)** | `~n*D` bool compares; the linearity/cliff floor |
| P3 | **prebuilt** first-keystroke `HashMap<FirstKeystroke,Vec<idx>>` index | A3-Q20 (b) | >2× crossover after the per-keystroke context re-filter |
| P4 | worst-case **layered ENVELOPE** (collect+sort by (layer,recency)+Unbound scan, no early return) | A3-Q20 (c) | **synthetic upper bound** — `Unbound`/(layer,recency) do **not exist yet**; bounds every future A3-Q4 policy |
| P5 | variant-c per-binding platform-resolution String alloc | **NEW (X12)** | A6-Q4/R5 **guardrail** ("don't parse per-binding on the hot path"), **NOT** an R4 verdict |
| P6 | linear-vs-cliff slope | NEW (X12), near-free | analysis across the N sweep (read off P2) |

N sweep: {500, 835, 2000, 5000}; ≥200k iters (reconcile A3-Q20's 200k vs X12's 50k → use 200k).

## 5. Success / kill (from the spec)

- ✅ **Defer the trie** iff at N=835 on the worst-case key, `--release`: scan p99 ≤ ~50 µs **AND** prebuilt index shows no decisive >2× win **AND** the **worst-case envelope p99 ≤ ~100 µs** (the load-bearing clause — it upper-bounds whatever A3-Q4 resolution policy is later chosen).
- 🛑 **Build the index/trie** iff scan p99 > 1 ms at N≈835, **OR** the prebuilt index cuts p99 >2× and stays correct. **PARTIAL KILL** (watch this): if the **envelope** (not today's scan) blows past ~100 µs toward 1 ms, the flat-scan green is irrelevant and A3-Q4 must choose a policy that avoids a per-keystroke sort (or carries an index).

## 6. False-green guards

`register_editable_bindings` (TLS tax) · prebuilt-not-rebuilt index · worst-case key provably runs the full scan · p99/max not mean · `--release` only · envelope stays a **synthetic** upper bound (never wired to a non-existent primitive) · P5 verdict feeds Axis-6, not the R4 decision · scope-guard the green: confirms the trie is unnecessary **for perf only** — A3-Q4's ambiguity-policy implementability is out of scope.

## 7. Deliverable

`plans/a3-q20-matcher-perf-spike-results.md`: the measured table (3 resolvers × N sweep, p50/p99/max), the trie-defer-or-kill verdict, and keep (promote the percentile harness + N anchor to a CI perf guard, e.g. `push_keystroke p99 < 100µs at N=2000`) vs throw (the index + envelope prototypes — perf probes only, no chord/ambiguity/Unbound semantics).

## 8. Out of scope

A3-Q4's ambiguity/longest-match policy; the real `Unbound`/(layer,recency) primitive; chord-reset correctness (A3-Q7). This spike is **perf only**.
