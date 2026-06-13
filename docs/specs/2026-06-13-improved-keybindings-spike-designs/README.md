# Improved Keybindings — Spike Designs (adversarial)

**Date:** 2026-06-13
**Status:** Throwaway-build designs for the 14 `prototype-spike` design-readiness questions
**Companion to:** the [questions](../2026-06-13-improved-keybindings-design-readiness-questions/README.md), the [verified code answers](../2026-06-13-improved-keybindings-code-investigation-answers/README.md), and the [decision briefs](../2026-06-13-improved-keybindings-decision-briefs/README.md)

## Method

Each empirical unknown got a spike design (minimal throwaway build with named touch-points, a **quantified** success signal and kill signal, a time-box, and a *false-green* analysis), then a **red-team** whose first job was to construct the scenario where the spike passes but the real thing still fails — and to ask whether a cheaper non-build experiment (a grep, a type-check, a paper exercise) gets the same signal. A final pass sequenced them into a run portfolio.

Verdicts: **2** DESCOPED · **5** REDESIGNED · **6** SHARPENED · **1** MERGE/CUT

> A spike that gives a false green is worse than no spike. Each design states exactly what observation to trust — and what would make that observation a lie.

---

## Run portfolio

Front-load the four near-free settles (X7 cargo-check, A6-Q16 micro-bench, A1-Q6 settings read, A2-Q4 memo): they cost hours, outright cut two 1-2d frameworks (A1-Q6, A2-Q4), and hand the bigger builds their inputs — X7's leaf-Cow type and A6-Q16's ns/op table. Then run the de-risking builds in parallel across worktrees, because the only Axis-0 mutator among them is X9; the rest (A4-Q16 Helix selection, A5-Q5 conflict oracle, the merged A6-Q3/Q14/Q16 portability build, and the merged X12+A3-Q20 matcher-scan perf bench) share no state. X9 is the linchpin: its tombstone-short-circuit kernel tells you whether the expensive X1 needs a full LayeredKeymap store at all and fixes the match_custom leak (A3-Q5), while the perf bench adjudicates whether the R4 trie is a Phase-2 prerequisite or stays the deferred-optional item the roadmap promises. Only after X9/X6/X12 prove the pieces do you commit the 3-5d X1 integration capstone, now scoped to its two genuine legs (write-side invalidation fan-out + Unbound U-scaling) with the matcher-coupling leg cut to a grep. One hard gate the lead must enforce: capture X13's irreversible resolution snapshot in Wave 1 before X9 or any spike reorders bindings(), so every engine refactor diffs against a frozen golden. Net: most expensive build entered last and already de-risked, critical path X9->X6->X1, everything else parallelized around it, ~14 engineer-days, ~6.5-8 days wall-clock.

**Total time-box (run optimally):** ~14 engineer-days of actual work (down from ~25+ implied by the un-descoped designs, after the X12+A3-Q20 and A6-Q3/14/16 merges and the A1-Q6/A2-Q4/X7 cuts). Optimal wall-clock with 2-3 engineers is ~6.5-8 working days: Wave A ~0.5d (parallel hours-spikes), Wave B ~2d (parallel 1-2d builds across worktrees), Wave C ~1.5d (X6 ~1d + A3-Q4 ~0.5d), Wave D ~3-5d (X1 capstone). The critical path is X9 -> X6 -> X1 (~6.5d); A4-Q16/A5-Q5/A6-Q3/perf-bench all finish inside Wave B alongside it and never gate the path."

### Run first (best de-risk per hour)

- **X7** — Hours, not a build: grep + derive-read settle everything except two cargo-check runs (transitive-compile confirm + error-file count). It produces the leaf-Cow ContextPredicate type that BOTH X6 (unified resolver) and X9 (mode-pack predicate) build on, and directly unblocks A2-Q6 config runtime predicate atoms. Highest unblock-per-hour in the set; the fork-reconciliation arm is replaced by a half-page storage-vs-catalog memo.
- **X9** — Descoped to the single tombstone-short-circuit kernel (1-2d), it is the highest-leverage probe against the most expensive build: it proves whether X1 needs a full LayeredKeymap store at all (it does not — inject's new TrackedId cannot subsume mutate's invalidation, settled by reading tracked.rs), settles the match_custom original_trigger leak (A3-Q5), and IS the shared short-circuit X6 hooks. Run before committing X1's 3-5d build.
- **X12** — Merge target with A3-Q20. A paper Fermi baseline (double short-circuit at matcher.rs:326-327 => ~n*D cheap bool compares, low microseconds at N~=835, 2-3 orders under the 4ms budget) plus a ~1hr release micro-bench settles the single biggest roadmap-scope question: is the R4 trie a Phase-2 shared prerequisite or the deferred-optional item the report (L258/L144) calls it. Bounds X1's single-store viability and caps X9's per-context injection budget. Near-free, gates a deep refactor.
- **A6-Q16** — Hours: an isolated micro-bench of the 3 resolution ops plus a paper composition argument. Supplies the ns/op number A6-Q3 hard-depends on and settles inline-vs-cache as 'inline, no cache' on a correctness argument (cache adds an invalidation surface across every mutation path). Cheap precursor that unblocks the entire Axis-6 portability build and removes its only perf objection.
- **A1-Q6** — Effectively a cut: reading the settings write-free idempotent reload pattern (manager.rs:327, lib.rs:500-515) proves an in-app writer already mutates its own watched file without a content-hash loop. Frees a 1-2d echo-suppression framework for a free code-read; the only empirical residue (torn-read wipe) is a ~30-line repro that belongs to A1-Q5. Cut-per-hour is maximal.

### Run order

- **Wave A — settle-by-inspection + type/number prerequisites (hours; fully parallel; mostly non-build):** X7, A6-Q16, A1-Q6, A2-Q4
  - Cheapest, highest-fan-out, and they feed or cut the larger builds. X7 cargo-check produces the leaf-Cow ContextPredicate type X6/X9 consume; A6-Q16 micro-bench produces the ns/op table A6-Q3 needs; A1-Q6 collapses to a settings-pattern read (its 1-2d framework is cut); A2-Q4 collapses to a paper memo settling 2.5/3 override-targeting relations. None mutate shared engine files, so run them concurrently before scheduling any build.
- **Wave B — cross-axis de-risking builds (1-2d each; run concurrently in separate worktrees):** X9, X12, A3-Q20, A4-Q16, A5-Q5, A6-Q3
  - The independent-axis builds with no shared state: A4-Q16 (Helix selection_model.rs — land the HashSet fix now, slimmed build only for the U1 overlap regime + U2 constant factor), A5-Q5 (conflict oracle + full-keymap walk — soundness oracle uses ZERO keymap data, walk is the one real-data build), A6-Q3 (absorbs A6-Q14/A6-Q16 — representation, `other`-sourcing probe, serde blast-radius). Plus the lone Axis-0 mutator X9 (tombstone kernel) and the merged X12+A3-Q20 matcher-scan perf bench, which should snapshot the baseline off master before X9's mutation. X9 is the only one touching matcher.rs/keymap.rs, so it parallels these but NOT X6/X1.
- **Wave C — Axis-0 unification + layered structure (sequential after Wave B kernel; ~1.5d):** X6, A3-Q4
  - X6 unifies the three trigger walks + the second custom-action surface into one scope-tagged loop hosting the suppression primitive — it needs X7's leaf-Cow type, X9's proven tombstone short-circuit, and the A3-Q5 unbind-representation decision settled on paper first. A3-Q4 picks the per-layer-chained structure and proves the shadow-collection fold + Tracked-invalidation identity; it needs the X12/A3-Q20 perf bound to know whether a per-keystroke collect+sort is affordable. Both feed the X1 store.
- **Wave D — integration capstone (after Wave C; 3-5d, in-memory only):** X1
  - The ONE LayeredKeymap store with the redesigned write-side invalidation fan-out probe + Unbound U-scaling bench — entered LAST and already de-risked: X9 showed no full store is forced, X6 proved the unified resolver walk, X12/A3-Q20 proved a single linearly-scanned store stays viable. Scope the build to its two genuine legs (write-fan-out multi-row render probe + N*U suppression bench); the matcher-walk-coupling leg is cut to a grep (track_read no-ops when rendering_view=None) and the 4->1 parity leg rides existing matcher_tests.rs. In-memory only, so NOT gated by the X2 file-format decision.

**Can run in parallel:** X7, A6-Q16, A1-Q6, A2-Q4, A4-Q16, A5-Q5, A6-Q3, X12, A3-Q20, X9

### Prerequisites

- **X6** needs **X7** first — type prerequisite — the unified scope-tagged resolver is built on the leaf-Cow ContextPredicate type X7 produces
- **X6** needs **A3-Q5 decision (unbind/tombstone representation)** first — design decision — settle the tombstone model on paper FIRST; if it dictates per-path vs unified, X6's control-flow merge may be redundant
- **X6** needs **X9** first — de-risk — X9's tombstone short-circuit IS X6's suppression hook; X6 hosts it in one loop
- **X9** needs **X7** first — type (loose) — X9 exercises ContextPredicate for the mode-pack predicate, the shared-vocabulary fork X7 settles
- **X1** needs **X9** first — de-risk / re-scope — X9 proves the tombstone needs no full LayeredKeymap store, so X1 may ship narrower
- **X1** needs **X6** first — de-risk — the single layer+context+indexed-Unbound walk X6 proves IS the unified resolver X1's store serves
- **X1** needs **X12 / A3-Q20** first — de-risk — the perf bench proves a single linearly-scanned store stays viable before the migration
- **A3-Q4** needs **X12 / A3-Q20** first — de-risk — the worst-case layered-envelope number decides whether A3-Q4's resolution policy may do a per-keystroke collect+sort or must avoid it
- **A6-Q3** needs **A6-Q16** first — input — A6-Q16's ns/op table removes the perf objection to the {mac,other} pair A6-Q3's recommendation depends on
- **A6-Q14** needs **A6-Q3** first — decision — A6-Q14's permanent matcher/conflict/serde regression test is blocked on A6-Q3 picking the unresolved representation; write it as part of A6-Q3's impl, not standalone
- **A2-Q4** needs **A2-Q5 decision (mutate vs inject)** first — gate — A2-Q4's implies()==eval fidelity test is only on the critical path if A2-Q5=mutate AND editable same-name forks actually exist; otherwise inject moots targeting
- **A1-Q6** needs **A1-Q5** first — couple — A1-Q6's only empirical residue (non-atomic torn-read wipe) is owned by A1-Q5's atomic temp+rename + absent-vs-parse-error split
- **X9** needs **X13 capture** first — regression-net gate — X13's irreversible (context,keystroke,OS)->winning-action snapshot must be captured in Wave 1 before X9 (and any engine spike) reorders bindings(); X9/A3-Q20 reuse the same fixtures
- **A3-Q20** needs **X13 capture** first — regression-net gate — same frozen golden; A3-Q20's reusable CI baseline diffs against it

### Merge or cut

- **X12 + A3-Q20** — MERGE into one --release matcher-scan perf build at the real N~=835 (384 fixed + 451 editable call sites). Both adjudicate the identical roadmap question — is the R4 trie a Phase-2 shared prerequisite or deferred-optional (report L258/L144). One #[ignore] Instant bench in the existing matcher_tests.rs covers: plain-MISS baseline (also settleable on paper), worst-case layered envelope (collect+sort by (layer,recency)+Unbound, no early return), the prebuilt first-keystroke-index >2x crossover at real shared-leader fan-out, variant-c per-binding platform-resolution String alloc, the vim-pack+pending predicate-eval tail, and the linear-vs-cliff working-set slope. Drop the criterion subproject and the app-dump binary (use a multiline grep of the predicate macros for N).
- **A6-Q3 + A6-Q14 + A6-Q16** — MERGE into one ~1-1.5d Axis-6 portability build. A6-Q16's 3-op ns/op micro-bench + paper composition feeds A6-Q3's representation choice; A6-Q14's seam decision (explicit target_os param, unresolved retention required) is already settled by two confirmed investigation answers, and its only build residue — the permanent matcher/conflict/serde regression test — is blocked on A6-Q3's representation pick, so it ships AS A6-Q3's implementation test, not a separate decision spike. The 3-backend criterion matcher bench is not needed; A6-Q16's 'inline, no cache' answer holds regardless.
- **A1-Q6** — CUT the 1-2d echo-suppression/content-hash framework. The loop-prevention question is settled by reading the settings write-free idempotent reload (manager.rs:315-327) + semantic skip-if-unchanged (lib.rs:500-515) — an in-app writer already mutates its own watched file without a hash. The only thing a grep can't settle (torn/empty read wiping overrides) is a ~30-line repro that belongs under A1-Q5's atomic write, not here.
- **A2-Q4** — CUT to a half-day memo + a gated 2hr test. The memo settles 2.5/3 relations from code already read (Exact = derive(PartialEq) + non-commutative And + no FromStr => unusable; BindingId = per-run AtomicUsize => not persistable; name+predicate-hash => drifts on edit). The only code-needing piece is a ~2hr implies()==eval fidelity test over the init.rs:459-460 same-key multi-value shape — fold it into A2-Q17's harness, and only run it if A2-Q5=mutate AND editable forks exist.
- **X7** — DESCOPE — not a build. grep + derive-read insulate ~965 sites behind 3 macros and confirm no Copy/Hash/HashMap-key hazard; the only irreducible work is two cargo-check runs (transitive-compile confirm + error-file count for the Context-set Cow increment). Replace the fork-reconciliation arm entirely with a half-page storage-vs-catalog written argument; hand the catalog-key-format question to X10/Axis-5.

## Contents

Spike designs, grouped by axis:

- [Axis 1 — Config as portable, live data](./axis-1-config-portable-live-data.md) — A1-Q6
- [Axis 2 — Scope & context control](./axis-2-scope-and-context-control.md) — A2-Q4
- [Axis 3 — Layering, precedence & unbinding](./axis-3-layering-precedence-unbinding.md) — A3-Q4, A3-Q20
- [Axis 4 — Modality as a first-class, pluggable choice](./axis-4-modality-pluggable.md) — A4-Q16
- [Axis 5 — Discoverability & truthful conflicts](./axis-5-discoverability-and-conflicts.md) — A5-Q5
- [Axis 6 — Cross-cutting foundation (platform-in-data-model)](./axis-6-cross-cutting-foundation.md) — A6-Q3, A6-Q14, A6-Q16
- [Cross-axis — Cross-axis / sequencing](./cross-axis-sequencing.md) — X1, X6, X7, X9, X12
