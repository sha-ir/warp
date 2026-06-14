[← Back to Spike Designs index](../README.md) · [Plan: A3-Q20 matcher perf](./a3-q20-matcher-perf-plan.md)

# A3-Q20 (merged X12) — matcher-scan perf bench · spike results

**Question.** At the real binding scale (N≈835), is the **R4 per-context trie** required for Axis-3 **perf**, or does the linear `push_keystroke` scan — and the worst-case post-Axis-3 layered resolver — stay far under the input-latency budget, making the trie premature?

**Verdict.** ✅ **DEFER THE TRIE for Axis-3 perf.** At N=835 the production scan p99 is **16.4 µs** and the worst-case layered **envelope** p99 is **10.8 µs** — both ~3 orders of magnitude under the ~100 µs / one-frame (16 ms) budget. A prebuilt index *does* shave microseconds, but the win is operationally irrelevant at this scale (see §3). The load-bearing kill clause (envelope ≤ ~100 µs) passes decisively.

**Branch.** `worktree-spike-a3-q20-matcher-perf` (off `origin/master`; code-identical to `keybindings-draft` for `crates/`). **No `warpui_core` mutation** — one `#[ignore]` bench appended to `matcher_tests.rs`. **No criterion, no `benches/`.**

---

## 1. Results (`--release`, worst-case held-pending vim-pack leader `g`, p99 over ≥200k iters)

| N | (a) prod scan (Tracked) | (a′) plain scan | (b) prebuilt index | (c) layered **ENVELOPE** | P2 plain-MISS | P5 variant-c +alloc |
|---:|---:|---:|---:|---:|---:|---:|
| 500 | 14.5 µs | 8.5 µs | 6.7 µs | 13.0 µs | 1.8 µs | 22.0 µs |
| **835** | **16.4 µs** | 8.5 µs | 5.9 µs | **10.8 µs** | 2.4 µs | 29.5 µs |
| 2000 | 28.9 µs | 14.2 µs | 6.2 µs | 17.2 µs | 7.3 µs | 69.3 µs |
| 5000 | 68.2 µs | 34.2 µs | 7.0 µs | 33.6 µs | 21.7 µs | 165.6 µs |

`max` is informational (tail jitter from OS preemption — a lone plain-scan `max` hit 1.06 ms at N=5000; p99 is the robust decision metric). The decision point is **N=835**; N=5000 is a margin stress (≈6× the real scale). **Stable across two runs** (N=835: scan p99 16–18 µs, envelope 11–14 µs, index 6–7 µs; N=2000: scan 29–33 µs, envelope 17 µs) — the verdict does not hinge on machine noise.

## 2. Verdict against the spec's criteria

- ✅ **scan p99 ≤ ~50 µs at N=835** → **16.4 µs**. (Holds to N=2000 = 28.9 µs; only the unrealistic N=5000 reaches 68 µs.)
- ✅ **worst-case ENVELOPE p99 ≤ ~100 µs at N=835** → **10.8 µs** (the load-bearing clause — it upper-bounds whatever A3-Q4 resolution policy is chosen). Holds to N=2000 = 17.2 µs (< 200 µs) and even N=5000 = 33.6 µs.
- ⚠️ **prebuilt index "no decisive >2× win"** → **needs honest handling** (§3). The apples-to-apples algorithmic win is **1.45×** (a′ vs b); the headline 2.8× (a vs b) is a Tracked-TLS-tax artifact.
- 🛑 **No KILL trigger:** scan p99 is ~60× under the 1 ms kill threshold; the **PARTIAL-KILL** (envelope blows past ~100 µs) does **not** fire — the envelope is 11–34 µs across the whole sweep.

## 3. The index "win" — honest treatment (the one subtle result)

Taken literally, (b) prebuilt index p99 (5.9 µs) vs (a) production scan p99 (16.4 µs) at N=835 is **2.8×** — which would *look* like the spec's ">2× → build the index" kill. It is not a real kill, for two grounded reasons:

1. **The 2.8× is mostly a TLS-tax asymmetry, not algorithm.** (b) runs over a plain `Vec` and pays **zero** `Tracked` derefs; the production scan (a) derefs all N `Tracked` editable bindings (the `with_cache` TLS tax, ≈ (a−a′)/N ≈ **9.4 ns/binding** at N=835). The fair, apples-to-apples comparison — plain scan (a′, 8.5 µs) vs plain index (b, 5.9 µs) — is only **1.45×**. A *real* index over the editable (`Tracked`) bindings would still pay the TLS tax for its candidates, landing ~2× vs the full scan — borderline, not decisive.
2. **Even at face value, the win is operationally irrelevant.** Halving a 16 µs scan to ~6–8 µs optimizes a path that is already **~0.1 % of a single 16 ms frame**. The spec's own PROXY red-team makes exactly this point: at the real ~300–835 binding scale the ratio "does not decide Q4." A trie buys microseconds you cannot perceive, at the cost of new complexity and correctness risk (chord-reset A3-Q7, the unsettled A3-Q4 ambiguity policy).

**SCOPE GUARD on the green:** this confirms the trie is unnecessary **for PERF only**. Whether A3-Q4's eventual ambiguity/longest-match policy is *easier to implement correctly* on a trie is **A3-Q4's** call, explicitly out of scope here.

## 4. Other findings

- **P5 variant-c (per-binding String alloc) is the one thing that scales toward budget:** 29.5 µs (835) → 69 µs (2000) → **165 µs (5000)**, crossing 100 µs. This is the **A6-Q4/R5 guardrail** it was built to be — *"do not parse/allocate per-binding on the keystroke hot path."* **Not** an R4/trie verdict; it's an Axis-6 constraint on per-binding platform resolution.
- **Cliff slope (P6) is linear, no cache cliff.** plain scan 8.5 → 14.2 → 34.2 µs for N = 835 → 2000 → 5000 tracks ~linearly with N; the index (b) is **flat** (5.9 → 6.2 → 7.0 µs) because its candidate set is fixed at the vim-pack size regardless of N — which is exactly why its relative win grows at unrealistically large N and is muted at the real N.
- **Read-barrier confirmed off the hot path:** the bench never wraps `push_keystroke` in `render_view`; the only residual autotracking cost is the per-deref `with_cache` TLS access, isolated as (a)−(a′) ≈ 9 ns/binding.
- **Worst case verified:** an in-test assert confirms the benched key prefix+context-matches the **full** vim-pack (250 evals), so the scan runs full length and retains pending — no early-return shortcut inflating the green.

## 5. Keep vs throw

- **KEEP:** the synthetic-keymap generator + the p50/p99/max percentile harness. Promote the production-scan assertion to a **CI perf guard** (e.g. `push_keystroke p99 < 100 µs at N=2000 on the worst-case key`) so any future index/layer work has a regression baseline. Keep the static-call-site **N anchor** and the three-cost decomposition (TLS tax / algorithm / envelope).
- **THROW:** the prebuilt-index and layered-envelope prototypes — perf probes only, with no chord-reset semantics (A3-Q7), no A3-Q4 ambiguity policy, and a *synthetic* Unbound/(layer,recency) that does not exist yet. If a future result flips to "build the index," the real store must be designed against A3-Q4 + A3-Q7, not these stubs.

## 6. Residual risks / scope

1. **Synthetic distribution.** The vim-pack fan-out is 250 (a large-fan-out stress); production's real worst leader is `escape`=60 (`grep`-derived). A smaller fan-out would *widen* the index's relative edge (fewer evals, more skipped derefs) but shrink absolute times further below budget — it strengthens "defer," not weakens it.
2. **Index modelled optimistically** (plain `Vec`, no candidate TLS tax). The real >2×-vs-scan question is therefore *bounded*, not exactly measured; §3 reconciles it to ~2× and argues irrelevance regardless.
3. **Perf-only verdict.** An all-green bench cannot prove A3-Q4's *eventual* ambiguity policy is implementable on the O(n) scan; the envelope is a guessed upper bound on the resolution shape. If that policy needs a per-context recency index the constant shifts (still very likely sub-ms at this N, but unmeasured).
4. **Grep under-counts predicate depth** (helpers built away from `::new`), so the deepest-tree tail is approximated; the N=5000 + deep-predicate cases stress it.

## 7. Unblocks

- Settles **A3-Q20**: the R4 trie is **not** an Axis-3 perf prerequisite — it stays the deferred-optional item the roadmap calls it.
- De-risks **A3-Q4**: its resolution policy may ride the O(n) scan (the worst-case envelope — full collect+sort+Unbound scan — is 11–17 µs at real N), and may even afford a per-keystroke collect+sort.
- De-risks **A3-Q7**: the chord-reset fix can target `push_keystroke`'s scan rather than blocking on a trie.
- Hands **Axis-6** a concrete guardrail (P5): no per-binding platform parse/alloc on the hot path.
