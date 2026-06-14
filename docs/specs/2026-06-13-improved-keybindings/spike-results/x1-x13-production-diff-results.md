# X1 — X13 production-scale resolution diff, feature-ON · results addendum

> Addendum to `x1-layeredkeymap-spike-results.md` §4 ("X13 production-scale diff — `not-run`").
> That section honestly recorded the prod-scale diff as **not-run** at HEAD `3889f1c5` (the `warp` app build
> exceeded the time-box). This addendum **supersedes** that status: the diff has now been built, run, and
> adversarially proven. Capture commit: `db479a29`. Logs: `/tmp/x13_runA_diff.log` (clean),
> `/tmp/x13_runB_mutation.log` (perturbed RED), `/tmp/x13_runC_revert.log` (clean again).

## VERDICT: **CLEAN-CONFIRMED**

Feature-ON, the X13 resolution snapshot matches the frozen feature-OFF golden with **0 winner flips over
452 rows**, AND the capture is positively proven to resolve through `LayeredKeymap::bindings()` by BOTH a
routing hit-counter (fired) and a gold-standard mutation control (perturb → RED → revert → green). The
`LayeredKeymap` 4→1 collapse preserves full-population resolution within the harness's coverage. **Green
light** to build the non-feature-gated migration against the golden.

All three pre-registered skeptics attacked and **none substantiated its trap**: routing (silent old-matcher
fallback) — refuted; config-drift (apples-to-oranges population/flag/channel) — refuted; non-vacuity
(BLESS/rewrite mode or 0 rows compared) — refuted.

---

## 1. Rows compared / winner flips

| Metric | Value |
|---|---|
| Diff ran | **yes** (Run A and post-revert Run C) |
| Rows compared | **452** (full golden table; header + 452 data rows = 459 lines) |
| Comparison kind | byte-for-byte string equality of the whole golden file (`expected != content`), not a sampled subset |
| **Winner flips** | **0** |

Both clean runs reported `X13: snapshot matches golden (452 rows)`, `test result: ok. 1 passed`, exit 0.
There are **no flipped rows to fix** — the 4→1 collapse to a single indexed store reproduces every winner
cell (precedence, `index`, and `custom_index` tie-breaks all intact).

The only place flips appeared was the **mutation control** (Run B, deliberately broken — see §2), which is
the proof the harness *can* go red. Sample of the ~27 control-induced flips (NOT real bugs):

```
line 71:  code_editor_vim_normal  ctrl-d  editable:editor_view:delete  ->  editable:editor_view:vim_scroll_half_page_down
line 105: code_editor_vim_normal  down    fixed:Down                   ->  fixed:MoveDown
line 107: code_editor_vim_normal  enter   fixed:Enter                  ->  fixed:VimEnter
line 100: code_editor_vim_normal  ctrl-u  editable:editor_view:clear_and_copy_lines -> editable:editor_view:vim_scroll_half_page_up
```

## 2. The TWO routing proofs (both required, both satisfied)

**(A) Hit-counter — FIRED.** `record_bindings_walk_hit()` lives *inside* `LayeredKeymap::bindings()`
(`crates/warpui_core/src/keymap/layered_spike.rs`), feature-gated by the whole module being
`#[cfg(feature = "layered_spike")]`. The X13 test calls `reset_bindings_walk_hits()` before the 12-fixture
loop and asserts `bindings_walk_hits() > 0` after. All three runs printed
`X13 ROUTING-PROOF: LayeredKeymap bindings_walk_hits = 12` — exactly one `bindings()` walk per fixture. A
silent old-`Keymap` fallback (e.g. if only dispatch were repointed) would have left this at 0 and turned a
falsely-clean diff into a hard assertion failure. The counter prints to stderr and is **not** folded into the
captured `content`, so it cannot perturb the diff (confirmed: Run A is clean *with* it present).

**(B) Mutation control — DIVERGED, then reverted clean.** Inside the exact method the capture routes through —
`LayeredKeymap::bindings()` — `self.entries.iter()` was changed to `self.entries.iter().rev()`, inverting
precedence so the "first lens per trigger" winner becomes lowest-precedence. Re-running feature-ON (same debug
config) went **RED**: `X13 resolution snapshot drifted`, panic at
`keymap_resolution_snapshot_tests.rs:263`, `test result: FAILED. 0 passed; 1 failed`, exit 101, ~27 winner
rows flipped. The hit-counter still read 12 during the perturbed run, confirming the perturbed path is the one
the capture observes. The file was then reverted (`git checkout --`; confirmed clean vs HEAD — only the
legitimate `.rev()` in `From<Keymap>` registration remains, lines 280/285) and Run C was clean again. Because
A is clean and B (identical except the perturbation) is RED, the falsely-clean-diff hypothesis is ruled out.

## 3. Config-match check (apples-to-apples)

- **OS:** golden header `os = linux`; host is Linux and `OperatingSystem::get()` is compile-time → match.
- **Population/coverage:** golden header `rows = 452` and `coverage = FULL: view::tests::initialize_app
  (workspace cascade + experiments) + x13_register_keybinding_inits (production lib.rs:1649-1693 inits)`. The
  capture used that exact harness, byte-identical coverage constant, same fixtures, and produced 452 rows that
  match the golden **exactly** — which directly proves the `layered_spike` flag is **additive**: it repoints
  the matcher onto `LayeredKeymap` but does not change *which* bindings register.
- **Channel/build:** golden's frozen recipe is plain `cargo test -p warp -- --ignored` (DEBUG,
  `debug_assertions` on). The capture was run in DEBUG deliberately (NOT `--release`) to match the golden's
  freeze, and the mutation control was run in the SAME debug config so attribution is sound.
- **Feature additivity at the source:** `app/Cargo.toml` `layered_spike = ["warpui_core/layered_spike"]`;
  `crates/warpui_core/Cargo.toml` `layered_spike = []` (empty — pulls in no other feature, no channel/flag
  toggles). `matcher.rs:19-22` swaps only a `BackingKeymap` type alias (`Keymap` vs `LayeredKeymap`);
  `Matcher::new`/`set_keymap` take the same fully-populated `Keymap` and convert via `LayeredKeymap::from`.
- **Golden provenance:** committed at `375a2269` with 0 `layered_spike` refs in `matcher.rs` at that rev →
  golden was generated feature-OFF; feature-ON only adds the flag. The diff is apples-to-apples.

## 4. Wiring needed to route `bindings_for_context` through `LayeredKeymap`?

**No matcher-side wiring was needed.** The repoint is at the **type-alias level, not per-method**:
`type BackingKeymap = LayeredKeymap` (feature on) / `= Keymap` (off) in `matcher.rs:19-22`, and `Matcher` has
a single field `keymap: BackingKeymap` (`matcher.rs:27`). Every reader — `push_keystroke`, `match_standard`,
`match_custom`, AND `bindings_for_context` (`matcher.rs:320-324`) — calls the same `self.keymap.bindings()`.
So `bindings_for_context` (the read path the X13 catalog walk exercises) already resolves through
`LayeredKeymap::bindings()` feature-on; there is **no old-matcher path** for the catalog walk to silently
fall back to. `AppContext` holds one `keystroke_matcher: Matcher` (`core/app.rs:605`), so the X13 snapshot
entry shares that exact instance. (`wiringNeeded = false`, `wiringApplied = false`.)

Two **additive, feature-gated** edits were made to *enable and prove* the run (not to change resolution
behavior):
1. **`app/Cargo.toml`** — passthrough `layered_spike = ["warpui_core/layered_spike"]` so the `warp` app can
   source-`cfg` on the feature for the routing proof (neither `warp` nor `warpui` defined the feature; it
   lives only on `warpui_core`).
2. **`app/src/keymap_resolution_snapshot_tests.rs`** — the documented routing guard-rail: `reset` before the
   fixture loop + `assert bindings_walk_hits() > 0` after, gated on `#[cfg(feature = "layered_spike")]`, and
   explicitly NOT folded into the captured `content`.

The hit-counter itself (committed in `db479a29`) is the only change to
`crates/warpui_core/src/keymap/layered_spike.rs` (+47 lines, behavior-neutral; `keymap::` test suite 32
passed / 0 failed confirms parity).

## 5. What this DOES and DOES NOT cover

**Covers (within these bounds, resolution is preserved):**
- **Linux only** — `os = linux` golden, host Linux. Mac is not exercised.
- **Full registered population for the harness** — `initialize_app` workspace cascade + experiments +
  `x13_register_keybinding_inits` production inits, 452 winner rows.
- **In-memory resolution** — the `Matcher`/`LayeredKeymap` catalog walk via `bindings_for_context`.

**Does NOT cover (inherited X13 design boundaries, not introduced here):**
- **NOT macOS** — Linux-only capture; a Mac golden would need a separate feature-on run.
- **NOT live chord state** — the harness records per-completed-trigger winners; chord-pending / multi-key
  responder state is not modeled (chord-blind beyond the single completed-trigger snapshot).
- **NOT the live `Vec<Context>` responder chain** — fixtures are flattened single-`Context` rows, not the
  runtime responder cascade.
- **NOT the full ~472-binding aspiration** — the harness covers a ~266-binding subset of the full production
  population. This is a **completeness gap, not golden-vs-capture drift**: the subset is identical on both
  sides of the diff, so the comparison stays apples-to-apples; it simply does not yet exercise every
  production binding.
- **NOT the running app** — in-memory matcher only; no end-to-end keystroke dispatch through a live UI.

## 6. Next-step implication

**GREEN LIGHT.** With 0 winner flips, both routing proofs satisfied, config matched to the golden, and the
harness proven non-vacuous, the `LayeredKeymap` single-store backing preserves full-population resolution
within the characterized bounds. Proceed to build the **non-feature-gated** migration (collapse the four
parallel collections into the one indexed store) against this golden as the regression oracle.

Before treating parity as fully settled at production scale, close the carried gaps from §5 — extend the
golden/coverage toward the full ~472-binding population and add a macOS feature-on capture — but none of these
block starting the migration; they harden it.

## 7. Worktree state

- Perturbation: **reverted** (`layered_spike.rs` clean vs HEAD).
- Committed: hit-counter in `crates/warpui_core/src/keymap/layered_spike.rs` (`db479a29`).
- Uncommitted at capture time (now committed by this addendum): `app/Cargo.toml` passthrough feature +
  `app/src/keymap_resolution_snapshot_tests.rs` routing-proof reset/assert. These realize the routing
  guard-rail the `layered_spike.rs` module doc prescribes.
