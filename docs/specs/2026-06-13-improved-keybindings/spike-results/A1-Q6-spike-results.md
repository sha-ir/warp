[← Back to Spike Designs index](./README.md) · [Spec: Axis 1 — A1-Q6](../axis-1-config-portable-live-data/spike-design.md)

# A1-Q6 — Adversarial spike results

**Question.** After adopting the settings-proven write-free reload pattern, is echo-SUPPRESSION (content-hash) required for keybindings, or is echo-TOLERANCE sufficient?

**Verdict to earn (not assert).** "Echo-TOLERANCE via a write-free idempotent reload; suppression NOT required." The spec already recommends this. This spike's job is to *try to break it* and to fix the spec where its supporting argument is wrong — not to re-state the conclusion.

**Branch.** `sha-ir/spike-a1-q6-echo-tolerance` (off `sha-ir/keybindings-draft`). Evidence branch — **no production wiring** (no `native.rs` keybindings branch, no visibility changes to `keyboard.rs`).

---

## Adversarial stance — the false-greens we are defending against

From the spec's own False-green section, plus what this build adds:

1. **Inverted false-green (dominant):** "proving" suppression is needed by greening a content-hash design against a baseline that never needed it. Defense: we build **no** suppression; we test the recommended design against its *kill* criteria instead.
2. **Write-then-read-at-rest (false-green #1/#3):** a serialized harness can never observe a torn read. Defense: the repro is genuinely **concurrent** (separate writer/reader threads, tight loops).
3. **Replica drift:** a hand-copied save/read that hides or invents the bug. Defense: the **writer drives the real `save_custom_keybindings`** via the public `write_custom_keybinding`; the reader is a byte-faithful replica of the private `read_custom_keybindings` (see fidelity caveat in Step B).
4. **Self-clobber measured on the wrong state (proxy mismatch):** the spec's UI risk is about the *capture buffer*, not the applied keymap. Defense: Step C traces where `unsaved_binding` lives vs. where `set_custom_trigger` applies.

---

## Pre-build findings — two cracks in the spec's argument

Established by reading the current code before building (evidence cited inline). Both are recorded as **corrections to the spec** below; neither changes the headline verdict, but each changes *why* it holds.

### 🔴 Crack #1 — settings does NOT "hold last-good on parse error"

The spec leans on a claimed differentiator: settings holds last-good on parse error, keybindings (`None`) doesn't. **False.**

- On parse failure, `read_from_preferences` returns `None` (`crates/settings/src/lib.rs:430–432, 447–449`).
- `reload_all_public_settings` treats `None` as **use-default**, not last-good (`crates/settings/src/manager.rs:358–361`: `Some(v) => (v, true), None => (entry.serialized_default, false)`).
- Settings survives only because it then calls `inhibit_writes_for_key()` (`manager.rs:366`) so the transient default never overwrites the user's broken-but-fixable file.

**Consequence.** The transferable mechanism is *write-free reload + write-inhibit-on-parse-error*, **not** *last-good-hold*. The in-memory wipe-to-default on a torn/partial read is **not keybindings-specific** — settings has the same in-memory behavior. This *strengthens* the case that the real work is A1-Q5 (split `None` into absent-vs-parse-error + hold-last-good + atomic write), and removes a false sense that keybindings is uniquely exposed.

### 🔴 Crack #2 — "write-free reload" is true only with a precise function choice

The spec says the reload "calls only `set_custom_trigger`/`remove_custom_trigger` (write-free)." There are **two namespaces** with the same verbs:

| Symbol | Location | Disk write? |
|---|---|---|
| `set_custom_trigger` (on `AppContext`) | warpui / `core/app.rs:1637` | **No** — in-memory matcher only |
| matcher-level `remove_custom_trigger` | `matcher.rs:146` (`update_custom_trigger(None)` = revert) | **No** — in-memory |
| `keyboard.rs::write_custom_keybinding` | `app/src/keyboard.rs:64–75` | **Yes** — read → insert → `save_custom_keybindings` |
| `keyboard.rs::remove_custom_keybinding` | `app/src/keyboard.rs:79–93` | **Yes** — read → remove → `save_custom_keybindings` |

**Consequence.** The loop is "pre-killed" *only* if the reload path calls the matcher-level (in-memory) functions and **never** the `keyboard.rs` disk-writing ones. If a future implementer wires the reload to `keyboard.rs::remove_custom_keybinding` (an easy mistake given the near-identical names), it re-persists and re-fires the watcher → the exact loop the spec calls impossible. The corrected finding states this as a **hard design constraint**, not an assumption.

---

## Step A — Corrected precedent-transfer finding (paper/grep)

**Method.** Re-derive the settings→keybindings transfer from the actual code, correcting Cracks #1 and #2. Falsification target: find any path where a *write-free* reload re-persists to disk (Crack #2 already supplies one — so the finding ships the constraint, not a bare claim).

**Result.**
- _Loop-safety transfers:_ ✅ `config_local_dir` is watched **recursively** (`app/src/warp_managed_paths_watcher.rs:263–271`, `RecursiveMode::Recursive`), so `keybindings.yaml` (`keyboard.rs:95–97`) is already in scope; settings already mutates its own watched file via a write-free reload and does not loop (`manager.rs:321–327`, comment: "avoiding write-back loops with the file watcher"). A keybindings reload built to call only the in-memory `set_custom_trigger` / matcher-level revert is loop-safe **by construction**, subject to the Crack #2 constraint.
- _Torn-read safety does NOT transfer for free:_ ✅→A1-Q5. Settings wipes in-memory to default on parse error too (Crack #1); its protection is write-inhibit, which keybindings lacks. So the wipe residue is handed to A1-Q5 (split `None`, hold-last-good, atomic write).
- _No keybindings reload exists today:_ confirmed — `handle_warp_managed_paths_event` (`app/src/user_config/native.rs:74–134`) has branches for themes/workflows/launch_configs/tab_configs/settings, **none** for `keybindings.yaml`. There is no echo loop today; the spike is designing a reload to be loop-safe before it exists.

_Verified against code on 2026-06-13:_ write-back-loop comment at `manager.rs:70` and `:322–327` (`reload_all_public_settings` at `:327`); `None => (entry.serialized_default, false)` at `manager.rs:360` (Crack #1); `inhibit_writes_for_key` at `:370`; `RecursiveMode::Recursive` at `warp_managed_paths_watcher.rs:269`.

## Step B — Torn-read repro (`app/examples/keybindings_torn_read.rs`)

**Why an example, not a unit test.** Under `#[cfg(test)]`, `save/read/write_custom_keybinding` are stubbed to no-ops (`keyboard.rs:144–153`) and `create_file` returns an error (`app/src/util/file.rs`). Only a `cfg(not(test))` target with `--features local_fs` exercises the real truncating write. Examples are the right target.

**Mechanism.**
1. At `main` start, set `XDG_CONFIG_HOME` to a fresh temp dir (Linux `config_local_dir()` resolves through `directories::ProjectDirs`, which honors it — `paths.rs:114→257`).
2. **Assert** `keyboard::keybinding_file_path()` resolves *under* the temp dir before any write — abort otherwise, so we can never clobber the user's real `keybindings.yaml`.
3. **Writer thread:** tight loop calling the real public `write_custom_keybinding(name, UserDefinedKeybinding::keystroke(..))`, which internally runs the real `read_custom_keybindings` + the real truncating `save_custom_keybindings`. Use a fat map (many entries) to widen the truncate→flush window.
4. **Reader threads:** tight loop performing a byte-faithful replica of `read_custom_keybindings`. To avoid a TOCTOU between "is it empty" and "does it parse," each read does a single `std::fs::read` then `serde_yaml::from_slice::<HashMap<String,String>>` on those exact bytes, classifying by what `read_custom_keybindings` would return (`None` ⟺ open-error or serde-error). _(Refined from the originally-planned `from_reader` + separate raw read during execution.)_
5. Run for a fixed duration; report counts: `clean` (full map), `short_map` (`Some`, partial), `some_empty` (0 bytes but serde `Ok`), `none_empty` (0 bytes, serde `Err`), `none_partial` (>0 bytes, serde `Err`), `absent` (open `Err`). `NONE-total = none_empty + none_partial + absent`.

**Fidelity caveat (stated honestly).** The reader cannot call the private `read_custom_keybindings` directly (private + `cfg(test)`-stubbed; calling it for real needs production changes this branch forbids). The replica is byte-identical in behavior: `PersistedTrigger(String)` is a serde-transparent newtype, so `CustomKeybindings` serializes as a YAML `map<string,string>`, which the replica deserializes identically. The property under measurement — whether a concurrent reader observes a torn/empty/partial file — is a filesystem property, not a logic property, so the replica is faithful for this purpose.

**Verdict rule.** ≥1 torn/empty/partial/parse-`None` read across N trials ⇒ atomic temp+rename is **REQUIRED** (hand to A1-Q5). 0 across many trials ⇒ atomic write is **defensive-only** (still recommended, but the wipe is not empirically reachable on this OS/filesystem).

**Result.** Built `app/examples/keybindings_torn_read.rs`, run via `cargo run --release -p warp --example keybindings_torn_read --features local_fs`. Verdict is **unambiguous, reproducible across two filesystems and two parameter sets, and far beyond the ≥1 threshold.**

- _Platform:_ Linux 7.0.3-arch1-2 x86_64.
- _Harness fidelity:_ writer thread drives the **real** `save_custom_keybindings` via the public `write_custom_keybinding` (truncating `create_file` → `serde_yaml::to_writer` over the fat map). Reader threads classify each read by what `read_custom_keybindings` **would actually return**, judged from the same bytes in one read (no TOCTOU): `read()==None` ⟺ open-error **or** serde-error. Genuinely concurrent (4–8 reader threads + 1 writer, atomic counters).
- _Empty-file semantics settled empirically:_ `some_empty = 0` in every run ⇒ `serde_yaml` returns **`Err`** on a 0-byte file, so an empty (truncated) file → `read_custom_keybindings == None` → revert-all. (This confirms — rather than assumes — that empty reads belong in the wipe class.)

| Run | FS | seed / readers / secs | reader reads | NONE-total | clean | %NONE |
|---|---|---|---|---|---|---|
| 1 | tmpfs (`/tmp`) | 1500 / 4 / 10 | 1,498,936 | 1,453,350 | 37,655 | 96.9% |
| 2 | tmpfs | 2000 / 8 / 20 | 2,301,604 | 2,187,213 | 98,996 | 95.0% |
| 3 | **btrfs** (`$HOME`) | 1500 / 4 / 10 | 1,296,309 | 1,250,332 | 38,544 | 96.5% |

NONE-total = `none_empty` (0 bytes, serde Err) + `none_partial` (>0 bytes, serde Err) + `absent`. Across all runs `absent = 0` (the file always exists once created; it is only ever truncated, never removed), and the overwhelming majority of `None` reads are `none_empty` — i.e., the truncating `File::create` leaves the file at **0 bytes for the majority of each write's duration**.

- **Verdict:** a torn read **can** return `read()==None`, which a nuke-and-reapply reload would turn into a revert-all wipe of every custom binding. That hazard is **reachable** (proven: `none_partial` alone is thousands of reads per run, independent of the empty-file case). **Atomic temp+rename is REQUIRED** — hand to A1-Q5 — and the requirement rests on **reachability**, not on the proportion. The btrfs run rules out a tmpfs artifact; if anything tmpfs (fast) understates the disk-backed window.
- **The ~95–97% is a stress/conditional figure, NOT a production failure rate** (refutation pass, finding #2). It measures window-width × the harness's near-100%-duty-cycle writer + an artificially fat 1500-entry seed (multi-flush BufWriter), *conditioned on a read overlapping a write*. In production, writes are rare user events, so the unconditional fraction of reloads that see `None` is ~0. Read it as "when a read coincides with a write, `None` is overwhelmingly likely," i.e. evidence the window is **wide and reachable** — not as a steady-state failure rate.
- _Scope honesty (what the repro does NOT measure):_ it measures the **width** of the torn window (reachability), not the **production probability** that a watcher-triggered reload read lands inside it. That probability depends on which inotify event the watcher fires on (IN_MODIFY mid-write vs IN_CLOSE_WRITE after close) and any debounce — a separate question. The conservative, correct conclusion stands regardless: the window is wide and reachable, so atomic temp+rename is the structural fix that makes the reload **never** observe a torn state, independent of event timing.

## Step C — UI-capture-clobber trace (code investigation)

**Method.** Trace where the in-app key-capture pending buffer lives vs. where an echo reload applies, to confirm a reload cannot clobber an uncommitted capture (or name the clobber path).

**Result.**
- _Capture buffer:_ `KeybindingsView.modifying_row: Option<KeyBindingModifyingState>` (`app/src/settings_view/keybindings.rs:154`), in-flight keystroke in `KeyBindingModifyingState.unsaved_binding: Option<Keystroke>` (`:88`), populated at `:710`.
- _Where a reload applies:_ via `set_custom_trigger` on the **global matcher** — a different object. A reload **never writes `unsaved_binding`** ⇒ ✅ no direct self-clobber of an uncommitted capture. (Confirms the spec's hypothesis; corrects the spec's worry that this needed a content-hash.)
- _Adversarial addition:_ the UI commit is a two-step `set_custom_trigger`(in-mem, `:592`) → `write_custom_keybinding`(disk, `:600`); also `util/bindings.rs:491–506`. A reload landing **between** those two steps desyncs the matcher from disk for one window. This is minor, is **not** fixed by content-hash, and belongs to A1-Q3 (diff vs nuke-and-reapply) / the apply-ordering discussion — recorded, not solved here.

_Verified against code on 2026-06-13:_ `KeyBindingModifyingState.unsaved_binding: Option<Keystroke>` at `settings_view/keybindings.rs:88`; `KeybindingsView.modifying_row` at `:154`; capture populated at `:710`; two-step commit `ctx.set_custom_trigger` at `:592` → `write_custom_keybinding` at `:600`.

---

## Adversarial verification pass

Three independent skeptics, each mandated to **refute** one finding (default to "refuted" if uncertain), reading the real code. Outcomes:

### 1. Loop-impossibility — **SURVIVED** (high confidence)

Full apply chain traced: `AppContext::set_custom_trigger` (app.rs:1637) → `matcher::set_custom_trigger` (matcher.rs:137, clears `pending`) → `keymap::update_custom_trigger` (keymap.rs:422) = **pure in-memory field mutation** (`binding.custom_trigger = trigger.clone()`), no fs call, no serde write, no event emission. All disk persistence lives **only** in `write_custom_keybinding`/`remove_custom_keybinding` → `save_custom_keybindings` → `create_file` → `fs::File::create`, called **only** from UI handlers (keybindings.rs:600, bindings.rs:496/513), never from an apply path. The existing `load_custom_keybindings` (keyboard.rs:37) **already is** the write-free apply pattern the design proposes. `reload_all_public_settings` (manager.rs:327) is genuinely write-free; `inhibit_writes_for_key` only inserts into an in-memory suppress-set.

- **New finding (non-fatal, feeds A1-Q8/A1-Q3):** an apply-only reload calling just `set_custom_trigger` will **not** emit `KeybindingChangedEvent` (only the UI wrappers `set_custom_keybinding`/`reset_keybinding_to_default` in `util/bindings.rs` emit it). That is a **UI-staleness** concern — after an external file edit, the settings panel may not re-render to reflect the new binding — **not** a write-back loop. The reload design should decide whether to emit a change event for the UI.

### 2. Torn-read verdict — **PARTIAL** (high confidence): "atomic REQUIRED" survives; the 95–97% framing must be relabeled

The harness was confirmed faithful on **every** axis: (a) writer drives the **real** `save_custom_keybindings` (example is a non-test build so the real `#[cfg(not(test))]` fns compile; `DISABLE_SAVE_ENV_VAR` removed; `--features local_fs` selects the `create_file` branch; nonzero `clean`/`short_map` are only coherent with `local_fs` on); (b) reader classification matches the `None` contract exactly, and `HashMap<String,String>` is structurally identical to `CustomKeybindings(HashMap<String,PersistedTrigger>)` because `PersistedTrigger` is a serde-transparent newtype over `String`; (c) `some_empty` is **measured** (split from `none_empty`), so `some_empty=0` is sound empirical proof that a 0-byte file errs→`None`; (d) concurrency is real (spawned threads vs main-thread writer); (e) single writer + read-only readers ⇒ `save` always fully returns before the next write, so the writer's own RMW never collapses the map — the empty/partial files readers see are genuine `File::create` truncate-to-0 + incremental-BufWriter artifacts, **not** fabricated.

- **Conclusion stands on reachability:** a torn read **can** return `None` and wipe all custom bindings → **atomic temp+rename REQUIRED**.
- **Correction applied (see Step B / Final verdict):** the `~95–97%` is a **stress/conditional** figure (near-100%-duty-cycle writer + fat 1500-entry seed spanning multiple BufWriter flushes) = window-width relative to total time, *conditioned on overlapping a write*. It is **not** the production probability that a watcher-triggered reload lands in a write window — in production writes are rare, so the unconditional rate is ~0. "REQUIRED" rests on **reachability**, not on the proportion.

### 3. UI-capture-clobber — **SURVIVED** (high confidence)

`set_custom_trigger` writes only `keystroke_matcher` (app.rs:1638), distinct from the view-local `modifying_row`/`unsaved_binding`. The capture buffer's sole writer is `set_temporary_keystroke_state` (keybindings.rs:710, user keydown); the edit row displays its own `binding.trigger` (render at :265), never the matcher. `KeybindingsView` subscribes to nothing config-related (only the search editor at :502), and the watcher handler (native.rs:74–134) has no keybindings branch.

- **New finding (feeds A1-Q8/A1-Q3):** a real reset-and-rebuild path **does** exist — `on_page_selected` (keybindings.rs:750/754) sets `modifying_row = None` **and** rebuilds rows from `ctx.editable_bindings()` — but it fires only on **settings-page navigation** (mod.rs:2059), never on a reload/config-change event, so it does not falsify the claim. **Caveat:** if a future live reload is wired to rebuild rows the way `on_page_selected` does, it *would* clobber an in-flight capture — the reload must avoid the reset-and-rebuild-from-matcher shape, or interlock while a capture is open.

## Final verdict

**A1-Q6 resolves to: echo-TOLERANCE via a write-free idempotent reload; echo-SUPPRESSION (content-hash) is NOT required.** Earned, not asserted:

1. **Loop-impossibility — confirmed (refutation SURVIVED, high).** Applying a loaded map via the in-memory `set_custom_trigger` / matcher-level revert touches no disk and emits no event, so the echo reload cannot re-fire the watcher. The pattern already runs in production (`load_custom_keybindings` at launch; `reload_all_public_settings` for settings). No content-hash guard is needed.
2. **Torn-read wipe — real and reachable; atomic write REQUIRED (refutation PARTIAL → "REQUIRED" survives on reachability).** The real non-atomic truncating `save_custom_keybindings` exposes an empty/partial file that makes `read_custom_keybindings == None` reachable (and `None` would wipe all bindings under a nuke-and-reapply reload). Fix is **atomic temp+rename + split `None` into absent-vs-parse-error + hold-last-good** — this belongs to **A1-Q5**, not A1-Q6. The repro's `~95–97%` is a stress/conditional figure, not a production rate.
3. **No UI-capture self-clobber — confirmed (refutation SURVIVED, high).** A reload mutates the global matcher, not the view-local `unsaved_binding`. No interlock needed for the apply itself.

**Both spec corrections stand.** Crack #1 (settings resets to default in-memory on parse error, surviving via write-inhibit — not last-good-hold) is confirmed by `manager.rs:360`. Crack #2 (write-freedom requires the matcher-level functions, never the disk-writing `keyboard.rs` ones) is confirmed by the loop refuter's full trace.

**Two new findings surfaced by the refutation pass (both feed A1-Q8 / A1-Q3, neither reopens A1-Q6):**
- An apply-only reload won't emit `KeybindingChangedEvent` → the settings panel may show stale bindings after an external edit. The reload design should decide whether to emit a change event.
- `on_page_selected` (keybindings.rs:750/754) is a real reset-`modifying_row`-and-rebuild-from-matcher path, but page-nav-triggered only. A future live reload must avoid that shape (or interlock while a capture is open) to stay clobber-free.

**Net:** ship the "naive watcher-only over the flat map" option as a small, correct, **write-free** branch in `handle_warp_managed_paths_event` (calling matcher-level `set_custom_trigger`/revert only). Build **no** content-hash subsystem. The only real residue (torn-read wipe) is A1-Q5's atomic write.

---

## Corrections to the original spec (`axis-1-config-portable-live-data.md`)

Spec left intact per decision; corrections recorded here.

| # | Spec said | Reality | Evidence |
|---|---|---|---|
| 1 | "settings' reload_from_disk may hold last-good on parse error, whereas keybindings returns None… the wipe gap is keybindings-specific" (Residual risk #1; Hypothesis) | Settings resets to **default** in-memory on parse error too; it survives via `inhibit_writes_for_key`, not last-good-hold. The in-memory wipe is **not** keybindings-specific. | `crates/settings/src/lib.rs:430–449`; `crates/settings/src/manager.rs:358–366` |
| 2 | "reload designed to call only set_custom_trigger… write-free… by construction" treats write-freedom as automatic | Write-freedom holds **only** if the reload calls matcher-level (in-memory) `set_custom_trigger`/revert, never `keyboard.rs::write_custom_keybinding`/`remove_custom_keybinding`, which write to disk. Must be stated as a hard constraint. | `app/src/keyboard.rs:64–93` vs. `matcher.rs:146`, `core/app.rs:1637` |

## Keep vs. throw (confirmed)

- **KEEP:** write-free idempotent reload design (matcher-level apply only); the torn-read repro + scenario → promote into A1-Q5 as atomic-write justification; optional write-time semantic skip-if-unchanged (mirror `lib.rs:500`) *iff* a perf/flicker need appears.
- **THROW:** all content-hash / `last_written_canonical_hash` machinery, the time-window/dirty-flag guard, standalone notify-debouncer scaffolding, the BulkFilesystemWatcher pass, and the 100-trial coalescing framework — they solve echo-SUPPRESSION, which echo-TOLERANCE does not have.

## Unblocks / hands-off

- A1-Q6 → "echo-tolerance via write-free idempotent reload, not suppression."
- Hard-couples the only empirical residue (torn-read wipe) to **A1-Q5** (atomic temp+rename + split `None`).
- Constrains **A1-Q4** (the write-free reload must distinguish set / unbind / revert to be idempotent).
- Confirms **A1-Q8** (reload host needs a mutable AppContext to call `set_custom_trigger`; must be write-free, must call matcher-level functions per Crack #2).
- New for **A1-Q8 / A1-Q3** (from the refutation pass): (a) the reload must decide whether to emit `KeybindingChangedEvent` so the settings panel reflects external edits — `set_custom_trigger` alone does not; (b) the reload must **not** use the `on_page_selected` reset-`modifying_row`-and-rebuild-from-matcher shape (keybindings.rs:750/754), or it must interlock while a key-capture is open, to stay clobber-free.
- Unblocks Axis-4 Step-D (live-aliasing), gated on A1-Q6.
