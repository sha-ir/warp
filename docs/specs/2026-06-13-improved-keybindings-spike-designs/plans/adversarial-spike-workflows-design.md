[← Back to Spike Designs index](../README.md)

# Adversarial spike workflows — execution design

**Date:** 2026-06-13
**Status:** Approved; executing (run-after-approval)
**Scope:** One adversarial Workflow per in-scope spike, each building in an isolated git worktree.

## In-scope spikes

| Source file | Spike(s) | Crate(s) | Harness |
|---|---|---|---|
| axis-4-modality-pluggable | **A4-Q16** Helix multi-selection keystroke bench | `crates/editor` | release criterion bench |
| axis-5-discoverability-and-conflicts | **A5-Q5** conflict oracle + full-keymap walk | `warpui_core/keymap` (NEW overlap.rs) + `app/` | nextest unit + app integration |
| axis-6-cross-cutting-foundation | **A6-Q3** (absorbs A6-Q14 + A6-Q16) portability build | `warpui_core/keymap.rs` + bench | cargo check + serde test + micro-bench |
| cross-axis-sequencing | **X7** leaf-Cow · **X9** tombstone kernel · **X12** (+A3-Q20) matcher perf · **X6** unified resolver · **X1** LayeredKeymap capstone | `warpui_core/keymap*` | check / nextest / release bench / criterion |

## The X13 gate (satisfied)

X13's irreversible `(context, trigger, OS) → winning action` golden is **already frozen** at commit `2899121c` in the `spike-x13-resolution-snapshot` worktree: `app/test_data/keymap/resolution_table.linux.txt` (459 rows, 12 contexts, Linux), plus the `#[ignore]` capture/diff harness in `app/src/keymap_resolution_snapshot_tests.rs` and the `AppContext::bindings_for_context_snapshot` accessor. The three `bindings()`-reordering spikes — **X9, X6, X1** — must `git cherry-pick 2899121c` into their worktree (Preconditions phase), then **re-run capture + diff after mutating**. A silent winner-flip = kill/false-green signal. No fresh X13 capture is needed.

## Per-spike workflow skeleton (5-phase pipeline)

```
Preconditions → Build → Run → Adversarial-verify → Synthesize
```

1. **Preconditions** — create/verify the worktree (`.claude/worktrees/spike-<id>`, branch `sha-ir/spike-<id>`, off `sha-ir/keybindings-draft`); assert upstream gates (X6 ⇐ X7 leaf-Cow branch + A3-Q5 paper decision; X9/X6/X1 ⇐ X13 golden cherry-picked). Unmet → halt with reason, never a hollow green.
2. **Build** — implementer agent implements *only* the throwaway harness from the spec's **The spike** + **Touch points**, inside the worktree. Returns `{filesChanged, buildOk, harnessReady, notes}`.
3. **Run** — runner agent executes the spec's exact **Harness** command(s); captures raw numbers vs the spec's **quantified** Success/Kill thresholds. Returns `{rawResults, prelimVerdict}`.
4. **Adversarial-verify** — **one skeptic agent per documented false-green trap** (extracted from the spec's ⚠️ False-green risk + Red-team), each with a distinct lens, prompted to **refute trustworthiness by default** (prove the build fell into *that* trap). A separate kill-checker confirms no kill condition was silently dodged. Each returns `{trap, refuted, evidence}`. Verdict downgrades to *False-green-caught* if **any** skeptic substantiates its trap.
5. **Synthesize** — fold raw results + skeptic verdicts → final verdict (**Trustworthy-Success / Kill / False-green-caught / Inconclusive**); write `plans/<id>-spike-results.md` (verdict, kept-vs-thrown, residual risk) mirroring the A1-Q6 / X13 results shape; commit in the worktree.

## Worktree & gating strategy

- Convention matches existing: worktree `.claude/worktrees/spike-<id>`, branch `sha-ir/spike-<id>`, base `sha-ir/keybindings-draft`.
- Isolation is the point: X7/X9/X12/X6/X1 collide on `warpui_core/keymap*`; separate worktrees let Wave-B run in parallel. X12 gets a clean pre-X9 baseline for free (X9's mutation is confined to its own worktree).
- **No auto-merge.** Each workflow builds/runs/verifies/commits *in its own worktree*; nothing returns to `keybindings-draft`. Keeps the X13 gate intact and everything reversible.
- Skeptics are read-only and share the spike's single worktree (no per-agent isolation); the Build agent is the only writer and runs before them.

## Launch order (honors the wave DAG)

1. **Gate:** X13 golden confirmed frozen (`2899121c`). ✔
2. **Wave A (canary):** **X7** — cheapest (cargo check), validates the build-in-worktree + adversarial mechanism and produces the leaf-Cow type X6/X9 consume. *(A6-Q16 is folded into A6-Q3 per the README merge.)*
3. **Wave B (parallel, separate worktrees):** **X9, X12, A4-Q16, A5-Q5, A6-Q3** — batched to actual machine capacity (decided from X7's measured build cost). → **checkpoint** before the capstone.
4. **Wave C:** **X6** (⇐ X7 + X9 + A3-Q5 paper decision).
5. **Wave D:** **X1** capstone (⇐ X9, X6, X12).

## Execution realism & guardrails

- Large Rust workspace ⇒ builds are slow and may not fully complete. Adopt the X13 philosophy: **incremental, time-boxed, commit maximal coverage achieved, document gaps as a labeled fact — never a silent truncation.**
- A *Success* verdict is never asserted without the adversarial phase clearing. *A false green is worse than no spike.*
- Per-worktree `target/` blowup is a real cost; Wave-B concurrency is sized from X7's observed build time, not assumed.
- Each workflow script is saved to `.claude/workflows/spike-<id>.js` for re-running a single spike by name.

## Grounding corrections (carried into the workflows)

- A4-Q16: real paths are under `crates/editor/src/content/` (`selection_model.rs`, `buffer.rs`, `anchor.rs`, `selection.rs`), not bare `crates/editor/src/selection_model.rs`.
- A5-Q5: harness B walk lives in the `app` crate (full `initialize_app` population), not `warpui_core` (which holds only ~3 register sites — a toy keymap).
- A6-Q3: `warpui_core` has no criterion dev-dep yet; the build adds `criterion = 0.5.1` + a `[[bench]]` block (mirrors editor).
- X12: timing is manual `Instant` p50/p99 over 50k samples (release), not criterion.
