[← Back to Spike Designs index](../README.md) · [Execution design](./adversarial-spike-workflows-design.md)

# Adversarial spike workflows — final portfolio rollup

**Date:** 2026-06-13 → 2026-06-14
**Status:** COMPLETE — all 8 in-scope spikes executed in isolated worktrees with adversarial verification.
**Method:** one Workflow per spike, 5-phase pipeline (preconditions → build → run → adversarial-verify → synthesize), with **one skeptic per documented false-green trap** pulled from each spec's *⚠️ False-green risk* + *Red-team* sections. A verdict is downgraded only when a skeptic's **evidence positively substantiates** its trap; verdicts anchor on the run-level signals, not skeptic booleans.

## Verdicts

| Spike | Verdict | Branch @ results commit | Results doc |
|---|---|---|---|
| **X7** ContextPredicate leaf→`Cow` | ✅ **Trustworthy-Success** | `sha-ir/spike-x7-leaf-cow` @ `7cb3a0b0` | `x7-leaf-cow-spike-results.md` |
| **A6-Q3** xplat canonical type (absorbs A6-Q14/A6-Q16) | ✅ **Trustworthy-Success** | `sha-ir/spike-a6-q3-portability` @ `a4bc729b` | `a6-q3-portability-spike-results.md` |
| **A4-Q16** Helix multi-selection bench | ⚠️ **Inconclusive (honest)** | `sha-ir/spike-a4-q16-multiselection` @ `7dd68a99` | `a4-q16-multiselection-spike-results.md` |
| **X9** Unbound tombstone kernel | ⚠️ **Partial-kill (predicted)** | `sha-ir/spike-x9-tombstone` @ `0dfb825f` | `x9-tombstone-spike-results.md` |
| **A5-Q5** truthful-conflict oracle + walk | ✅ **Trustworthy-Success** | `sha-ir/spike-a5-q5-conflicts` @ `9584cbba` | `a5-q5-conflicts-spike-results.md` |
| **X6** unified scope-tagged resolver | ✅ **Trustworthy-Success** | `sha-ir/spike-x6-resolve` @ `f35d3d1d` | `x6-resolve-spike-results.md` |
| **X1** LayeredKeymap capstone | ✅ **Trustworthy-Success** | `sha-ir/spike-x1-layeredkeymap` @ `2bf4f4b3` | `x1-layeredkeymap-spike-results.md` |
| **X12** matcher-scan perf | ✅ **Done (pre-existing, merged with A3-Q20)** | `worktree-spike-a3-q20-matcher-perf` @ `28126681` | `a3-q20-matcher-perf-spike-results.md` |
| *(gate)* **X13** resolution snapshot | ✅ **Frozen (gate satisfied)** | `worktree-spike-x13-resolution-snapshot` @ `2899121c` | `x13-resolution-snapshot-spike-results.md` |

Results docs live on each spike's branch (downstream branches inherit upstream docs: X6/X1 carry X9; everyone carries X13/A3-Q20). Each worktree under `.claude/worktrees/spike-*`.

## Quantified findings

- **X7:** leaf→`Cow` is a genuine **~1-file** change (after the `&**` deref fix for the `Borrow<Q>` ambiguity); `warpui_core` clean. Probe-2 (full `Context`-set Cow) = 3 error files (≤30 band, lower bound). All 4 skeptics confirmed safe/in-scope.
- **A6-Q3:** only `(b){mac,other}` can express `cmd-[`/`ctrl-shift-{` (single key field rules out a/c). Sourcing **mixed** — `cmd-p/f/k`→`ctrl-shift-P/F/K` derive, but `cmd-[`→`{` panics (hand-authored). `resolve(target_os)` seam materializes the inactive OS without `get()`. Derived-struct serde breaks without `#[serde(default)]` → true cost is Hash/sync-schema, not a file break. **Decision: R5 splits** (cmdorctrl-token Phase-1 + Axis-2 record schema).
- **A4-Q16:** bench verified honest (real `\w+` split + real `w`/`e` extend, measured overlap). **Density-dependent:** sparse multi-cursor `local-k` stays under frame; **dense select-all-words-then-extend is `chained-N`, 50k worst = 42–48 ms p50** (overruns 16.67 ms at the model layer). Anchor-growth fine (resolve ratio 0.99). **Mandatory HashSet fix landed** (`b856d43d`). Paint UNMEASURED → no-cap/incrementality stays open.
- **X9:** all **3 primary** match paths route the tombstone through one `is_tombstone` helper; **consistency gate passes** (matcher + `get_binding_by_name` + macOS-menu agree post-inject, mutation-tested); **X13 diff CLEAN** (452 rows, zero flips — production resolution unchanged). The Option-returning 2nd surface shares the predicate but keeps its own short-circuit shape (pre-registered split). `mutate` retained (TrackedId identity).
- **A5-Q5:** oracle **sound** (100k/100k pairs, 0 disagreements, map-key-exclusivity + `ne!`-vs-absent units pass, no SAT/unsafe, mutation-tested). Full 472-binding pop: N_exact_eq=**11** ≤ N_overlap=**2662** < N_naive=**2669**. **(c) is cosmetic** (thin 7-pair negation class; 2645/2662 cross-view conflicts remain) → **Phase-1 needs an identifier-mutual-exclusion (exclusion-groups) primitive**.
- **X6:** the unified `resolve()` walks `bindings()` in **one loop** hosting retain_pending + first-match + scope-tagged suppression early-stop, no separate `resolve_keystroke`; suppression is one primitive dispatched by binding metadata; leak returns `None`; walk-once invariant holds. **matcher-unify ≠ dispatch-unify** (the three `app.rs` wrappers stay distinct).
- **X1:** parity holds (verbatim `matcher_tests` against one `Vec<LayerEntry>`, custom_index correct after reset-all + mode-pack); push_keystroke p99 **~5.1µs @ N=2000 (~40× under budget)**, layered/flat ~1.0, **indexed suppression flat in U** (+4.5%) vs naive O(N×U) ×11.7; the load-bearing write-fan-out probe is real (false-green skeptic self-refuted). Single `Tracked<u64>` ⇒ **whole-list 300-row fan-out** on one override (explicit/accepted; per-row=1, per-bucket=30 escape hatches measured); preview burst dedups within-frame.
- **X12 (A3-Q20):** **defer the trie** — scan p99 16.4µs, envelope 10.8µs, ~3 orders under budget; the "index win" is a TLS-tax artifact (real 1.45×, irrelevant at N=835). Variant-c per-binding alloc = the A6-Q4/R5 guardrail.

## Cross-cutting decisions for the initiative

1. **R5 portability must split** — a Phase-1 cmdorctrl-token slice on the flat string, with the full asymmetric `{mac,other}` pair deferred to an Axis-2 record schema (asymmetric sites aren't mechanically derivable).
2. **Truthful conflicts needs a new primitive** — `can_both_be_true` satisfiability (option c) is cosmetic; the real Phase-1 deliverable is an **identifier-mutual-exclusion (exclusion-groups)** declaration. Option (a) structural-equality (11) is also insufficient.
3. **The unified resolver is viable shared Phase-2 infra** — X6's one scope-tagged `resolve()` + X9's indexed Unbound tombstone + X1's single `Vec<LayerEntry>` LayeredKeymap compose, at ~1.0× latency and flat-in-U suppression. The matcher unifies; the three dispatch *wrappers* do not (Axis-2 scoped-match lands there).
4. **The trie stays deferred** (X12) — not an Axis-3 perf prerequisite.
5. **Two things stay OPEN, by design:** (a) dense multi-selection paint/incrementality (A4-Q16 measured only the model layer; the 50k dense overrun *adds* motivation); (b) the LayeredKeymap **write-side fan-out granularity** (whole-list vs per-bucket vs per-row) + a **cross-frame override-preview debounce** — a product/judgment call X1 surfaced but cannot decide.

## KEEP artifacts → graduate to real PRs

- **A4-Q16 HashSet fix** in `merge_overlapping_selections` (`b856d43d`) — mandatory-regardless; cheap insurance proven by arithmetic.
- **X7 leaf-`Cow`** `context.rs` diff — the production shape of R3a-for-Axis-2 (unblocks config runtime predicate atoms).
- **A5-Q5** `can_both_be_true` oracle + differential/adversarial test suite + `BindingLens::context_predicate()` accessor.
- **A6-Q3** `resolve(target_os)` seam (the A6-Q14/Q15 injection/display seam) + the sourcing finding.
- **X9** Unbound tombstone variant + shared `is_tombstone` short-circuit helper + reader-consistency assertions.
- **X6/X1** the unified `resolve()` signature + scope-tagged suppression + LayerTag/LayerEntry sketch + the redesigned multi-row write-fan-out invalidation probe + the N×U suppression bench + index-sync tests (CI regression guards).
- **A3-Q20** synthetic-keymap generator + percentile harness → CI matcher perf guard.

## Residuals / NOT settled

- A4-Q16 paint of N quads (unmeasured); regime is fixture-sensitive; CI hardware shifts the crossover N.
- X9/X6 second macOS-menu surface keeps its own Option-shaped short-circuit (predicate shared, shape diverges); dynamic Modal vocabulary is faked (no FromStr/interning — see X7).
- A5-Q5 reachability unmodeled (logical overlap ≠ reachable); production graduation needs Axis-2 to thread `ContextPredicate` into the settings `ConflictMap`.
- X1: ModePack-vs-UserOverride precedence (Axis-4 product call). The **X13 production-scale diff with `--features layered_spike` is now RUN → ✅ Clean-confirmed** (`6391c43f`): 0 winner flips over all 452 golden rows (BLESS off, feature-ON vs feature-OFF golden), with routing PROVEN both ways — a cfg-feature hit-counter (fired 12×, one LayeredKeymap walk per fixture) and a mutation control (`entries.iter().rev()` → ~27 flips/RED, then revert → green). No matcher wiring needed (the repoint is at the `BackingKeymap` type-alias shared by `bindings_for_context`; no old-matcher fallback). **Residual = coverage breadth**: the golden covers a ~266-binding subset (winners over the 12 curated contexts), not the full ~472 registration population; still Linux-only, chord-blind (except `cmdorctrl-r w`), flattened single-Context, in-memory — so macOS / live chords / responder cascade / running app remain separate, pre-existing X13 limits.
- Nothing has been merged to `sha-ir/keybindings-draft`; every spike is isolated and reversible. The X13 gate remains intact.

## Recommended next steps

1. Land the two no-brainer PRs: the **A4-Q16 HashSet fix** and the **X7 leaf-`Cow`** type.
2. ~~Run the deferred X1 feature-on X13 production diff~~ — **DONE, Clean-confirmed** (`6391c43f`). Resolution preservation holds for the covered population → **green light to build the non-feature-gated LayeredKeymap migration** against the golden. Later hardening: widen the golden toward the full ~472-binding population + add a macOS capture (Mac runner or the A6-Q14 OS-injection seam).
3. Take the two product decisions: **exclusion-groups** primitive (A5-Q5) and the **write-fan-out granularity + preview debounce** (X1).
4. Sequence the engine unification (X6 resolver + X9 tombstone + X1 store) as shared Phase-2 infra; keep R5 on the split path; keep the trie deferred.
