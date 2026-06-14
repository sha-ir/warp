[← Back to Spike Designs index](../README.md) · [Spec: Axis 6 — A6-Q3](../axis-6-cross-cutting-foundation/spike-design.md#a6-q3--redesigned--time-box-1-2-days)

# A6-Q3 (merged A6-Q14 / A6-Q16) — platform-in-data-model canonical type · spike results

**Question.** Which canonical type can EXPRESS *and* SOURCE the asymmetric two-key platform pair (e.g. mac `cmd-[` ↔ non-mac `ctrl-shift-{`) given `Keystroke` has a single `key` field (keymap.rs:327): (a) a flat `cmd_or_ctrl:bool`, (b) a `Trigger`-level `{mac,other}` pair, or (c) a modifier-enum? The decisive open part is **not** the container's round-trip but whether `other` is mechanically **derivable** at the ~330 one-sided registration sites (esp. the 182 `cmd_or_ctrl_shift` sites, including the `bracket→brace` case where `cmd_or_ctrl_shift()` panics) or must be **hand-authored** — that, not latency, decides whether R5 "show both" is feasible incrementally. Plus (a-BREAK): does adding a field to the flat `Keystroke` ripple through the DERIVED `Serialize`/`Deserialize`/`Hash` cloud-sync consumers (NOT the invariant `SettingsValue` string file form)?

**Verdict.** ✅ **TRUSTWORTHY-SUCCESS — and KILL (A) fired as a legitimate DECISION.** All four probes RAN and PASSED (`cargo test -p warpui_core --features xplat_proto` → 3/3 probe tests pass; bench ran in `--release`). The `resolve(target_os)` seam materializes the inactive-OS `Keystroke` without `OperatingSystem::get()`; the sourcing probe returns a grounded, MIXED answer; the blast-radius count and the DERIVED-struct old-payload serde behavior are both recorded. The two decisive skeptics (wrong-serde-form, container-vs-sourcing) are **NOT refuted** — the green is not hollow.

**DECISION.** **Split R5: cmdorctrl-token-only Phase-1 (sourcing not fully derivable).** Per kill (A): on EXPRESSIVENESS, (b) `{mac,other}` remains the only viable canonical type (single `key` field rules out (a)/(c) by inspection — paper fact). But the sourcing probe is **MIXED** — the symmetric letter sites mechanically derive, the asymmetric `bracket→brace` site **panics and must be hand-authored** — so R5 "show both" **cannot** land in one incremental pass. The symmetric `cmdorctrl`-token sites become the **Phase-1 slice** (resolvable via `parse_for`); the non-derivable asymmetric pairs are **deferred to an Axis-2 record schema** (`ResolvedPair{mac,other}`). Kill (C) did **not** fire (blast-radius ≠ 0; old-payload deser breaks without `#[serde(default)]`), so option (a) is **not** resurrected as a cheap modifier-only slice.

**Branch / worktree.** `sha-ir/spike-a6-q3-portability` (worktree `/home/mhb/warp/.claude/worktrees/spike-a6-q3-portability`, off `sha-ir/keybindings-draft`). All throwaway source edits to `keymap.rs` reverted (`git diff` of `keymap.rs` empty); the worktree ends clean save the pre-existing `Cargo.lock` change. Probe artifacts: `crates/warpui_core/src/keymap_xplat_probe.rs` (tests), `crates/warpui_core/src/keymap.rs:1092-1219` (`xplat_proto` module), `crates/warpui_core/benches/xplat_resolve.rs` (bench). Throwaway-branch history: `973e3fe7` (seam) → `a31bbcea` (sourcing + serde) → `d19116fd` (micro-bench) → `66c79290` (blast-radius field, THROWAWAY) → `e2ed451a` (revert).

---

## 1. Expressiveness — DECIDED ON PAPER (no build, the type-level fact)

`Keystroke` carries a **single** `key` field (keymap.rs:327). Therefore:

- **(a) `cmd_or_ctrl:bool`** can flip a modifier but cannot hold **two distinct keys** — it cannot represent mac `[` vs non-mac `{`.
- **(c) modifier-enum** likewise varies only the modifier set, not the `key` — same failure.
- **(b) `Trigger`-level `{mac,other}` pair** is the only shape that stores two whole `Keystroke`s, hence two keys.

This is a structural fact read off the struct, **not** a green bench claimed as proof. It establishes that the *container* must be (b); §3 establishes whether (b) can be *populated* incrementally.

## 2. The `resolve(target_os)` seam — PASS (KEEP: the A6-Q14/Q15 injection seam)

Test `keymap_xplat_probe::seam_materializes_inactive_os_chord` passes. On the Linux host **both** platform chords materialize as real `Keystroke`s from the explicit target alone:

- `parse_for("cmdorctrl-p", Mac)` → `cmd=true, ctrl=false, key="p"`
- `parse_for("cmdorctrl-p", Linux)` → `ctrl=true, cmd=false, key="p"`

`ResolvedPair::resolve(target)` and `XplatSideTable::resolve(id, target)` take the target OS as a **PARAMETER** and **never** call `OperatingSystem::get()` (which is cfg-fixed at platform/mod.rs:669 with no native setter). `parse_for` rewrites the `cmdorctrl` token to `cmd`/`ctrl` per the explicit target **before** delegating to `Keystroke::parse`, so the inactive-OS side materializes without consulting the running OS. **`resolveMaterializesInactiveOs=TRUE`.** This is the production-needed seam reused identically by `displayed_for(target_os)` (A6-Q15) and the cross-platform test (A6-Q14) — it survives regardless of which option wins.

`ResolvedPair` is held **out-of-band** in `XplatSideTable { pairs: HashMap<BindingId, ResolvedPair> }` (keymap.rs:1157-1158), keyed by `BindingId`, **explicitly NOT inline** in the matcher's `Vec<Keystroke>` binding array — so the hot path is provably untouched for all three options (§6.1).

## 3. Sourcing probe — PASS, verdict MIXED (the decision-driving output)

Test `sourcing_probe_real_cmd_or_ctrl_shift_sites` ran the **real** `cmd_or_ctrl_shift` non-mac transform (a line-faithful replica — the production fn lives in `app/`, which depends on `warpui_core` and cannot be imported back; it still calls the **real** `is_valid_special_key`) over 4 real registration sites, wrapped in `catch_unwind`:

| site | mac side | derived `other` | result | source |
|---|---|---|---|---|
| CommandPalette | `cmd-p` | `ctrl-shift-P` | **DERIVABLE** (uppercase+shift) | bindings.rs:281 |
| Find | `cmd-f` | `ctrl-shift-F` | **DERIVABLE** | bindings.rs:283 |
| ClearBlocks | `cmd-k` | `ctrl-shift-K` | **DERIVABLE** | bindings.rs:350 |
| (bracket) | `cmd-[` | `ctrl-shift-{` | **PANIC → NOT-DERIVABLE, must hand-author** | bindings.rs:854-861 |

The 3 letter sites mechanically derive; the punctuation site **panics** because `cmd_or_ctrl_shift` has no keyboard-layout knowledge that `shift-[ = {` (`VALID_SPECIAL_KEYS`, keymap.rs:794-830, excludes `[`, so `is_valid_special_key('[')` is false and the panic branch is genuinely reached — matching the `## Panics` doc at bindings.rs:849-861 that *instructs authors to hand-author* separate mac/non-mac `Keystroke`s for exactly this case). **`bracketBraceCaseTested=TRUE`, `otherDerivable=mixed`.**

**Consequence for R5.** Because the asymmetric sites are not mechanically derivable, "show both" cannot be a single incremental rewrite. The symmetric `cmdorctrl`-token sites form the Phase-1 slice; the hand-authored asymmetric pairs require the Axis-2 `ResolvedPair{mac,other}` record schema — i.e. **R5 must split (A6-Q10).** (Sample is 4 of ~330 sites — provisional, see §9.)

## 4. Blast-radius + DERIVED-struct serde — PASS (the (a)-cost characterization)

**Blast-radius (count).** Re-adding `pub cmd_or_ctrl: bool` to `Keystroke` (throwaway commit `66c79290`) and counting with `grep -E '\.rs:[0-9]+:[0-9]+: error'` on `--message-format=short`:

- **Headline = 1 distinct file** — `crates/warpui_core/src/keymap.rs` (single `E0063` at :963, the `parse()` ctor). The ~40 derived `Serialize`/`Deserialize`/`Hash`/`Eq` impls auto-propagate and do **NOT** break; only explicit full-field `Keystroke { .. }` literals/patterns (no `..` rest) break. **`blastRadiusErrorCount=1`.**
- **Grep recipe correction:** with `--message-format=short`, per-site errors begin with the **file path**, so the spec's suggested `grep '^error'` matches only the trailing `error: could not compile` summary and **MISSES** the real sites; `\.rs:N:N: error` captures them.
- **HONEST CAVEAT — the lib-only "1" is a severe undercount of the true workspace surface.** `cargo` aborts a crate after its first errors (blocking downstream crates) and cfg-gated platform code never compiles on one host. After temp-fixing the lib ctor, `cargo check -p warpui_core --tests` adds `keymap_tests.rs` (6 sites); `cargo check --workspace --all-targets` then aborts at `warpui/.../key_events.rs:128`. Static enumeration of full-field literals/patterns without `..` spans **~14 distinct files** (incl. `warp_terminal/.../escape_sequences.rs` ~8 match arms that DO break, and several mac/wasm files that are platform-gated and never compile on Linux — so **no single-host build can enumerate them**). Note: throwaway commit `66c79290`'s claimed "`integration/step.rs:410,412` patterns with `..` → invariant" is a **FABRICATED citation** — that file does not exist; the real integration sites (`test.rs`, `keyboard_protocol.rs`) are full-field literals that WOULD break. The commit's qualitative finding (derived impls don't break; only literals/patterns do) holds, but its "distinct error FILES = 1" headline is an artifact of building the lib in isolation.

**DERIVED-struct serde (the correct wire form).** Test `serde_probe::derived_struct_old_payload_breaks_then_serde_default_neutralizes`:

1. ANCHOR: today's real `Keystroke` serializes to an object with **exactly 6 keys and no `cmd_or_ctrl`** (proving the test targets the derived struct wire form, **not** the `SettingsValue` `String(self.normalized())` form at keymap.rs:347-348, which it explicitly cites as invariant).
2. An OLD 6-field payload deserialized into the field-added struct **ERRORS** without `#[serde(default)]` (error string contains `"cmd_or_ctrl"`) — the cloud-sync break. **`serdeBreaksWithoutDefault=TRUE`.**
3. With `#[serde(default)]`, deser **SUCCEEDS** (field defaults `false`). **`serdeNeutralizedWithDefault=TRUE`.**

**Net cost of (a):** NOT a file round-trip break (the `SettingsValue`/TOML string form is invariant to adding a field). It is a **`Hash`/`PartialEq` + sync-schema** concern — and even the sync break is **neutralizable** with `#[serde(default)]`. Because the count is **1 (≠ 0)** AND old-payload deser **breaks** without `default`, **kill (C) does NOT fire** and (a) is not resurrected.

## 5. Micro-bench — RAN (optional A6-Q16 ns/op table; does NOT decide the type)

`cargo bench -p warpui_core --features xplat_proto --bench xplat_resolve` (RELEASE, criterion, host=Linux, `CARGO_BUILD_JOBS=6`). Median [low..high]:

| variant | what | ns/op |
|---|---|---|
| **V1** `pair_side_select` | option (b) — branch → `&Vec`, no alloc | **1.35** [1.333..1.376] |
| **V2b** `cmdorctrl_field_wise` | option (a) honest — bools+branch, `key:String` borrowed | **3.56** [3.523..3.604] |
| **V2** `cmdorctrl_alloc_construct` | do-NOT-do — `key:String` clone per compare | **9.70** [9.192..10.290] |

All single-digit ns; only the `String`-clone alloc variant (V2) regresses (~7× V1, ~2.7× V2b). Consistent with commit `d19116fd`'s ~1.2 / ~3.3 / ~8.1 ns. Confirms A6-Q16's "resolve inline, no cache": every realistic op is far below the per-binding floor; only the alloc-construct strawman is a regressor A6-Q3 must avoid. **The bench does NOT decide the canonical type** — latency is identical once resolved (a tautology). No 3-backend matcher clone / 2000-binding scaffolding built, per the bench's own do-not-build note.

## 6. Adversarial skeptic findings (all four CONFIRMED — none refuted)

1. **Latency-tautology — NOT refuted (high).** `ResolvedPair` is in the OUT-OF-BAND `XplatSideTable` keyed by `BindingId` (keymap.rs:1157-1158), explicitly NOT inline in the matcher's `Vec<Keystroke>`; the binding-array element still carries only the 6 flat fields. `push_keystroke` scans the same `Vec` for all of (a)/(b)/(c), so latency cannot discriminate the type. The decision is driven by expressiveness+sourcing+blast-radius, never latency; the bench commit and `xplat_resolve.rs` header both disclaim deciding power. **Both refutation conditions (inline `ResolvedPair`; bench as deciding evidence) are absent.**
2. **Wrong-serde-form — NOT refuted (high).** The serde test targets the DERIVED `#[derive(Serialize,Deserialize)]` struct (mirrors the real 6-field `Keystroke`, keymap.rs:320-328), anchoring on an object with exactly 6 keys and no `cmd_or_ctrl` — proving it is NOT the invariant `SettingsValue` `String(self.normalized())` path (keymap.rs:347-348). It builds an old missing-field payload, shows strict deser ERRORS (err contains `"cmd_or_ctrl"`), then `#[serde(default)]` SUCCEEDS. The decisive evidence is genuine, not the trivially-green string path. **This is one of the two skeptics whose refutation would have made the verdict False-green-caught; it held.**
3. **Container-vs-sourcing — NOT refuted (high).** `probe_site()` genuinely RUNS `derive_other_via_cmd_or_ctrl_shift()` (a line-faithful replica of the non-mac branch, calling the REAL `is_valid_special_key`) on `p/f/k/[` inside `catch_unwind`; it does not round-trip a hand-built pair. The hand-built `from_pair("cmd-[","ctrl-shift-{")` appears ONLY in the `NotDerivable` branch to exhibit the correct hand-authored value. `bracket→brace` was probed and genuinely panicked. **The sourcing was real; the second decisive skeptic held.**
4. **Noop-builder / zero-data — NOT refuted (high).** The spike does NOT claim "show both works" from a zero-data prototype; it explicitly rests the verdict on sourcing. `new_per_platform` (keymap.rs:497-508) selects one string and `Self::new` eagerly parses it; `with_mac`/`with_linux` (keymap.rs:688-713) noop on the inactive OS — both genuinely discard the inactive side. The skipped ~330-site re-plumb to RETAIN both sides is carried as residual risk (§9), not hidden.

## 7. Kill check — (A) FIRED as a decision; (B) and (C) did NOT fire

- **(A) FIRES (legitimate decision).** `otherDerivable=mixed`: `cmd-p/f/k` derive, `cmd-[` panics → must hand-author `ctrl-shift-{`. The asymmetric sites are NOT mechanically derivable, so a hand-authored `{mac,other}` record is the only path — forcing R5 "show both" to **split** into a Phase-1 `cmdorctrl`-token slice plus an Axis-2 record schema for the asymmetric sites. Per the spec, (A) firing is a DECISION, not a failure.
- **(B) does NOT fire.** The `{mac,other}` `ResolvedPair` lives in the out-of-band `XplatSideTable` keyed by `BindingId` (keymap.rs:1093) — the mechanism that AVOIDS editing all ~330 sites in lockstep; `blastRadius=1` corroborates. The seam threads `target_os` without an ambient `get()` override.
- **(C) does NOT fire.** Requires 0 build errors AND old-payload DERIVED-struct deser already holding. `blastRadius=1` (≠ 0) AND `serdeBreaksWithoutDefault=true` (only succeeds once `#[serde(default)]` is ADDED). The spike correctly probed the DERIVED cloud-sync form (which breaks), not the invariant `SettingsValue` string round-trip — so the kill-(C) string-green trap is avoided and (a) is NOT resurrected.

## 8. Keep vs throw

- **KEEP:** (1) the `resolve(target_os)` explicit-target-OS seam (`parse_for`/`XplatSideTable::resolve`) — the A6-Q14 test-injection seam and the basis for A6-Q15 `displayed_for(target_os)`, needed by production regardless of which option wins; (2) the SOURCING-PROBE finding (derivable for letter sites / hand-authored for punctuation) — the decision-driving output and the input to the A6-Q9/Q10 split; (3) the `ResolvedPair{mac,other}` type + its to-disk encoding **IF (b) wins** — it becomes the Axis-2 record shape for the asymmetric sites; (4) the per-representation ns/op table as the A6-Q16 input (inline, no cache).
- **THROW:** the `cmd_or_ctrl:bool` throwaway branch after its error count is recorded (already reverted, `66c79290`→`e2ed451a`); the 3-backend criterion matcher bench + 2000-binding prefix-colliding scaffolding (B2==B0 tautology — never built); the `SettingsValue`/`QuakeModeSettings` string round-trip test (wrong wire form, invariant — correctly never used as evidence).

## 9. Residual risks (carried, not dropped)

1. **Sourcing sample is 3-5 sites — provisional.** The probe sampled 4 of ~330 sites; a transform that derives for the sample may fail on an unsampled letter site (and vice versa). A "derivable" verdict for the symmetric slice must be confirmed by a **full audit** before committing R5's Phase-1 boundary as independent of Axis-2.
2. **Blast-radius count is a lower bound.** The lib-only "1" undercounts the true workspace surface (cross-crate consumers in `app/` synced-settings serializers, `warp_terminal` escape-sequence match arms, and platform-gated mac/wasm files that never compile on Linux). A real migration of (a) would surface ~14 distinct files across crates; no single-host build can enumerate them.
3. **The full ~330-site RETAIN-both re-plumb is NOT exercised.** The spike's noop `with_mac`/`with_linux`/`new_per_platform` still discard the inactive side; the genuinely hard re-plumb (102 `with_mac` + 57 `with_linux` + 14 `new_per_platform` + 182 `cmd_or_ctrl_shift`) to retain both sides is skipped.
4. **Lossy `cmd→ctrl`-only mapping.** The token rewrite never produces `meta`/`super`, so it is lossy for real Linux meta/super bindings (A6-Q7) — untouched here.
5. **Compile/ns ≠ runtime correctness.** The seam proves the data model materializes and round-trips on a Linux runner; it does NOT prove a real Mac delivers `cmd-[` vs `ctrl-shift-{` to `push_keystroke` at the OS input/modifier layer (below the keymap) — that needs real Mac CI or the X13 golden captured on Mac.

## 10. Unblocks

- **A6-Q3 (canonical type):** decided by expressiveness + sourcing + blast-radius — (b) `{mac,other}` is the type, but sourcing is MIXED so R5 splits; option (a) stays dead (kill C cold).
- **A6-Q9/Q10:** the SOURCING-PROBE result is the decisive new input — because `other` is hand-authored for asymmetric sites, R5 splits and **Phase-1 is `cmdorctrl`-token-only** on the flat `HashMap<String,PersistedTrigger>` file; the asymmetric pairs defer to the Axis-2 record schema.
- **A6-Q14:** the `resolve(target_os)`/`parse_for` seam exists (explicit target_os param, no ambient `get()` override); A6-Q14's permanent matcher/conflict/serde regression test is written against this chosen record, not a throwaway pair.
- **A6-Q15:** `displayed_for(target_os)` reuses the same explicit-target seam.
- **A6-Q16:** settled as "inline, no cache" — the ns/op table shows every realistic op is sub-floor; only the alloc-construct strawman regresses.
