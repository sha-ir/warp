[← Back to index](../README.md)

## Axis 1 — Config as portable, live data

**End state:** the keymap is a hand-editable, shareable file that is the source of truth and applies instantly.

> **Killer question:** Does Axis 1 ship over today's flat name-to-trigger HashMap -- a hot-reload watcher plus reset bookkeeping only (R1) -- and explicitly DEFER the rich context/platform-scoped schema (R3b: records of name, trigger, optional context, optional platform) to Axis 2, OR is R3b in scope for Axis 1? The end-goals doc lists R3b as an Axis-1 leaf (L52-53) while the report roadmap (section 7) and the dependency spine (L117: Axes 1 and 5 ... no schema/engine change) place R3b in Phase 2 -- an unresolved contradiction. This ruling determines whether round-trip of multi-context names (Q7), cross-platform import (Q14), unknown-name migration (Q10), and schema back-compat (Q17) are in scope, and whether Axis 1 is a one-week quick win or a multi-week schema project.

### Scope/requirements

**A1-Q1. Is the rich/context-scoped schema redesign (R3b: flat HashMap of name to PersistedTrigger becoming records of name, trigger, optional context, optional platform) in scope for Axis 1, or deferred to Axis 2 - i.e. does Axis 1 ship ONLY the watcher plus reset bookkeeping over today's flat map?** _(sharpened)_

- _Why it matters:_ Decides whether Axis 1 is a roughly one-week watcher+bookkeeping quick win (R1, Phase 1) or a multi-week schema+parser+migration project. Every downstream question (round-trip of context-scoped bindings Q7, cross-platform import Q14, unknown-name migration Q10, schema back-compat Q17) only exists if the schema changes. The end-goals doc lists R3b as an Axis-1 leaf (L52-53) but the report roadmap (section 7) and dependency spine (L117 no schema/engine change) put R3b in Phase 2 - a documented contradiction the spec must settle first.
- _How to answer:_ Reconcile the Axis-1 leaf list (end-goals L45-56) against the report phased roadmap (section 7: R1=Phase1, R3b=Phase2) and dependency spine (end-goals L117). Note today's file already supports chords (Vec1 of Keystroke, keyboard.rs:20-25,196-211) and unbind ('none', keyboard.rs:15) while the in-app UI captures only single keystrokes (G4) - so the file is currently RICHER than the UI, inverting the usual capability-gap framing. Then make an explicit scope ruling.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the naive assumption that 'Config as portable live data' is one coherent shippable unit; it staples a Phase-1 quick win to a Phase-2 engine refactor under one axis title.

**A1-Q2. Should keybindings hot-reload ship behind a runtime FeatureFlag with a clean disabled-path (falling back to launch-only load), the way settings hot-reload is itself gated on FeatureFlag::SettingsFile (native.rs:129)?** _(added-by-critic)_

- _Why it matters:_ A new live-reload plus reset path that can rebind or wipe keys on every external save is exactly the kind of change that needs a kill-switch for staged rollout and incident response. The analogous settings path retains that gate; shipping keybindings reload ungated removes that safety. Decides whether the watcher branch is flag-wrapped and whether disabling it cleanly reverts to today's launch-only behavior (lib.rs:2557) with no half-applied state.
- _How to answer:_ Follow the FeatureFlag::SettingsFile gate at native.rs:129-132 and use the add-feature-flag skill. Decide flag name, default rollout stage, and the disabled-path contract (launch-only load unchanged; watcher branch no-ops). Confirm the disabled path does not leave a partially-seeded applied-names set.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks 'low risk, copies a proven mechanism' - the proven mechanism it copies is itself feature-flagged; omitting the flag drops the kill-switch the precedent kept.

### Design decision

**A1-Q3. On each reload, do we diff (apply only deltas vs the last-applied set) or nuke-and-reapply (remove_custom_trigger every previously-applied name, then re-set the whole file)?**

- _Why it matters:_ Drives the shape of the applied-names bookkeeping and user-visible behavior: nuke-and-reapply momentarily reverts bindings to default within a single reload (flicker / dropped keystroke if a key is pressed mid-reload, since both set_custom_trigger and remove_custom_trigger clear the pending chord buffer at matcher.rs:138,150), while diffing needs reliable old-vs-new state tracking.
- _How to answer:_ Model both against matcher.rs:137-151 (set and remove both call pending.clear()). Decide whether an intra-reload revert window is acceptable; if not, require diff-based apply. Specify the last-applied data structure (name to applied trigger kind: Keystrokes / Empty / none), shared with Q2 and Q15.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that reset-then-reapply (report R1 wording) is free; it has an observable revert window and clears in-flight chord state on every keystroke-save.

### Edge case/failure mode

**A1-Q4. On hot-reload, how do we reconcile the three file states - name-present-with-keys, name-present-with-'none', and name-absent - given that the launch loader maps 'none' to set_custom_trigger(name, Trigger::Empty) (an explicit unbind, keyboard.rs:43-44) but the report reset story (R1) assumes remove_custom_trigger reverting to default (matcher.rs:146-151 then keymap.rs:422)? Does an ABSENT name revert to default while an explicit 'none' STAYS an unbind?** _(sharpened)_

- _Why it matters:_ This is the core of the 'removed entries revert to default' leaf. Trigger::Empty (unbind) and update_custom_trigger(name, None) (revert-to-default) are different live outcomes, and today's loader NEVER calls remove_custom_trigger - it only ever set_custom_triggers Empty or Keystrokes (keyboard.rs:42-48). The applied-names set must distinguish unbound vs reverted vs absent, or reloads will either fail to revert deleted entries or wrongly resurrect defaults the user deliberately unbound.
- _How to answer:_ Compare keyboard.rs:42-48 (load uses Trigger::Empty for Removed, never remove_custom_trigger) against matcher.rs:146-151 (remove_custom_trigger calls update_custom_trigger(None) = revert). Define a tri-state policy: absent maps to remove_custom_trigger (revert to default); 'none' maps to set_custom_trigger(Empty) (stay unbound); keys map to set_custom_trigger(Keystrokes). Specify the bookkeeping set (which names are applied, and the applied trigger kind for each).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the report hand-wave that removed entries revert via remove_custom_trigger - the existing code never calls it; it overloads Trigger::Empty, so revert and unbind are silently conflated today.

**A1-Q5. When a hand-edit leaves the file transiently malformed (syntax error mid-typing, or the watcher fires during a non-atomic truncating write), read_custom_keybindings returns None (keyboard.rs:128-138) - the SAME value as an absent/empty file. Should None mean 'keep current applied bindings' rather than 'empty file, revert ALL custom bindings to default'?**

- _Why it matters:_ A naive reload that treats None as empty will momentarily wipe every user override on any save that races a watcher event or any in-progress syntax error - a jarring, data-losing flicker. The save path uses fs::File::create (util/file.rs:143), which truncates in place (non-atomic), so a watcher event observing a half-written file is a real, not hypothetical, race.
- _How to answer:_ Confirm None semantics conflate absent-file and parse-failure (keyboard.rs:128-138) and the truncating write (util/file.rs:132-145). Decide a policy: distinguish File::open Err (absent) from serde_yaml Err (present-but-unparseable) by splitting read_custom_keybindings return; on parse error hold last-good applied state (and surface an error per Q11) instead of reverting; adopt atomic write (temp plus rename) for save_custom_keybindings to shrink the race window.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that parse failure equals no custom bindings; conflating absent-file with broken-file turns a typo into a full keymap reset.

**A1-Q6. In-app edits call write_custom_keybinding (read-modify-write of the whole map, keyboard.rs:64-75) which MUTATES the watched file, which then re-fires the watcher and triggers a reload. What is the echo-suppression strategy to avoid a write-back loop / self-clobber - and does that strategy wrongly suppress a legitimate concurrent external edit (or a second Warp process writing the same file)?** _(sharpened)_

- _Why it matters:_ settings.toml sidesteps this because its watcher only hot-reloads an EXTERNALLY-edited file and never writes back. keybindings' in-app writer mutates the same file the watcher watches, creating a feedback path settings never had. Without a guard, every in-app save races its own reload, and a reload landing mid-UI-edit can clobber the unsaved capture state - directly threatening the 'file edits and in-app edits do not clobber each other' leaf.
- _How to answer:_ Confirm write_custom_keybinding does a full read-modify-write of the file (keyboard.rs:71-74) and that no analogue exists in the settings loop. Prototype options: a self-write content-hash/dirty-flag dedup, an ignore-events window after self-write, or make the apply path idempotent and reload-safe so an echo is a no-op. Verify a content-hash approach still applies a genuine external edit that happens to follow a self-write. Spike the in-app-edit-then-watcher sequence.
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Attacks 'just add a watcher branch like settings does' - settings hot-reloads an externally-edited file and never writes back; keybindings' in-app writer mutates the same file, creating a feedback path settings never had.

**A1-Q7. Does the override survive bindings registered AFTER a reload? The Matcher stores no persistent name-to-trigger map (struct at matcher.rs:13-31); set_custom_trigger calls update_custom_trigger (keymap.rs:422-433) which mutates only bindings already in editable_bindings, and register_editable_bindings (keymap.rs:405-419 / matcher.rs:113-132) never re-applies a stored override. So any editable binding registered by a view/tab/view-type created after the reload (or after launch today) silently keeps its DEFAULT trigger. Must the hot-reload design add a persistent applied map plus a re-apply hook on registration?** _(added-by-critic)_

- _Why it matters:_ Reframes the applied-names set from a mere reset ledger into a required SOURCE OF TRUTH that the registration path must consult. If editable bindings are registered lazily per view-instance, a user who opens a new tab/editor after a reload gets defaults, not their overrides - a correctness bug the watcher would make newly visible (and possibly a latent bug at launch already, since load_custom_keybindings runs once at lib.rs:2557). Determines whether the engine needs a stored name-to-trigger map re-applied in register_editable_bindings, or whether we can prove all editable bindings register exactly once before any override is applied.
- _How to answer:_ Confirm the matcher has no custom-trigger storage (matcher.rs:13-31) and update_custom_trigger touches only existing bindings (keymap.rs:422-433). Determine whether register_editable_bindings is called once at app init or per view-instance/lazily (sample sites: root_view.rs:448 uses app, editor/view/mod.rs:518/908/928 use ctx). If any are per-instance/lazy, design a persistent map applied on registration and seeded from the launch load (lib.rs:2557).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that set_custom_trigger applies the override and it stays applied - there is no persistent store, so overrides evaporate for any binding registered after the apply call.

### Dependency/sequencing

**A1-Q8. Where does the reload handler live, and how does it obtain a mutable AppContext? set_custom_trigger/remove_custom_trigger are on AppContext (core/app.rs:1637,1656), but the watcher fires inside ModelContext of WarpConfig (native.rs:74). Do we mirror settings - emit a new WarpConfigUpdateEvent::Keybindings and handle it in an init-side subscriber that holds a mutable AppContext (init.rs:225) - and where does the applied-names set get OWNED?** _(sharpened)_

- _Why it matters:_ Determines the concrete plumbing and where the reset bookkeeping lives. handle_warp_managed_paths_event (native.rs:74-134) runs in ModelContext of WarpConfig and has no AppContext, so the keymap mutation must be hoisted via an event exactly as settings does. Picking the wrong host means the handler cannot mutate the keymap at all.
- _How to answer:_ Follow the settings pattern end-to-end: native.rs:129-132 emits WarpConfigUpdateEvent::Settings (gated on FeatureFlag::SettingsFile), then init.rs:225-256 handle_warp_config_change subscribes with a mutable AppContext and calls reload_all_public_settings. Decide whether keybindings reuses WarpConfig events plus an init.rs-style subscriber, and where the applied-names state is stored (on the global keystroke_matcher, a new singleton, or alongside keyboard.rs). Note the set must be SEEDED from the launch load (lib.rs:2557) or the first reload won't know prior state.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'add a branch to handle_warp_managed_paths_event and call set_custom_trigger' - that handler runs in ModelContext of WarpConfig with no AppContext, so the mutation must be hoisted via an event the way settings does.

**A1-Q9. Is 'round-trip safe' achievable in Axis 1 alone, given that one name maps to N context-scoped bindings (editable_bindings_by_name maps a name to a Vec of indices, keymap.rs:30) and update_custom_trigger rewrites ALL of them (keymap.rs:422-433)? Can a flat file (one PersistedTrigger per name, keyboard.rs:169) faithfully round-trip a per-context override without Axis 2 context records?**

- _Why it matters:_ If a name has multiple context-scoped bindings (e.g. the Vim vs non-Vim duplicate registrations the report cites at code/editor/view/actions.rs:51-60), the flat file can express only ONE trigger for the name and clobbers all contexts on apply (L3). A UI edit meant for one scope cannot be represented in the file and re-imported losslessly - making 'no capability gap between file and UI' and round-trip safe unreachable without R3b. This, with Q1, decides whether Axis 1 stands alone or hard-depends on Axis 2.
- _How to answer:_ Grep editable binding registrations for names registered under multiple contexts (Vim vs non-Vim at actions.rs:51-60); count how many names map to more than 1 binding via editable_bindings_by_name. If non-trivial, document that the flat-schema round-trip leaf is structurally gated on Axis 2 (R3b) and scope the Axis-1 leaf to single-context names.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the dependency-spine claim that Axis 1 is independently shippable; round-trip fidelity for multi-context names is structurally impossible in the flat schema, quietly coupling Axis 1 to Axis 2.

### Migration/back-compat

**A1-Q10. Unknown or renamed action names in the file silently no-op (update_custom_trigger filters by name, finds nothing - keymap.rs:423-432; only unparsable triggers warn - keyboard.rs:49-53). With roughly 437 inline static-str names that drift across releases, should an unknown name surface a warning/banner, and do we need a name-alias/migration map for renamed actions?** _(sharpened)_

- _Why it matters:_ Directly threatens the 'drop in a teammate's config and it just works' (import) leaf and back-compat: a colleague's or an older config silently loses bindings when a name was renamed, with zero feedback. This is the difference between import being trustworthy vs silently lossy.
- _How to answer:_ Confirm the silent no-op (keymap.rs:423-432) and the only warning path (keyboard.rs:49-53). Decide: (a) emit a warning/banner for names not found in the live keymap, (b) maintain an alias table for known renames, and (c) whether the action catalog (R9, Axis 5) becomes the validation source so unknown names can even be detected.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks 'import just works' - names are unstable string literals with no validation or alias layer, so a renamed action turns a shared config into a silent partial failure.

**A1-Q11. Does the import/export leaf require persisting a platform-agnostic cmdorctrl, or is import explicitly scoped to same-platform only? normalized() bakes literal cmd-/ctrl- (keymap.rs:970-993) - never cmdorctrl - and parse() resolves cmdorctrl only at load via OperatingSystem::get() (keymap.rs:914-919), so a macOS export of cmd-k imported on Linux is a literal cmd binding that Linux rarely emits.**

- _Why it matters:_ Decides whether 'drop in a teammate's config and it just works' is deliverable in Axis 1. If cross-platform import must work, the persisted form needs cmdorctrl (or a mac/other pair) - i.e. a slice of R5/L7 (platform-in-data-model) is pulled into Axis 1. If not, import must be explicitly documented as same-platform-only, narrowing the leaf.
- _How to answer:_ Confirm normalized() omits cmdorctrl (keymap.rs:970-993) and parse() resolves it at load (keymap.rs:914-919). Decide: (a) re-introduce cmdorctrl on export when the source binding came from a cmdorctrl/per-platform construction, (b) full mac/other representation (R5), or (c) scope import to same-platform and say so in the schema/docs.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks 'export/import a keymap and it just works' - the persisted keystroke form has already collapsed the platform modifier to a literal, so a shared file is silently platform-locked unless R5 is partly imported into Axis 1.

**A1-Q12. IF R3b lands in Axis 1 (per the Q1 ruling), must the new record schema still deserialize today's existing flat 'name: trigger' files on disk - and how? read_custom_keybindings returns None on any serde_yaml failure (keyboard.rs:132-138), which on a struct change would silently drop EVERY existing user's custom bindings on upgrade.** _(added-by-critic)_

- _Why it matters:_ Existing users already have flat HashMap-of-name-to-PersistedTrigger keybindings.yaml files (keyboard.rs:167-174). A naive struct redesign makes deserialization fail, and the None-on-failure path discards all of them with only a log warning - a silent keymap reset on upgrade. Even if R3b is deferred, recording this constraint is what Axis 2 inherits.
- _How to answer:_ Inspect the CustomKeybindings/PersistedTrigger serde derives (keyboard.rs:167-213). If the schema changes, design an untagged/duplex Deserialize that accepts both the legacy name-to-trigger map and the new record list, or add a version field plus one-time migration-on-load that rewrites the file. Verify the None-on-parse-failure path (keyboard.rs:132-138) cannot silently discard a legacy file - split absent vs parse-error first (shares Q3).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'we will just evolve CustomKeybindings to records' - a struct change without a back-compat deserializer turns every existing user's saved keymap into an unparseable file that read silently treats as no custom bindings.

### Testing/validation

**A1-Q13. How do we test hot-reload plus reset semantics deterministically when keyboard.rs load/read/write are cfg(not(test)) with no-op cfg(test) stubs (keyboard.rs:144-153), saving is suppressed via WARP_TEST_DISABLE_KEYBINDING_SAVE (keyboard.rs:14,67,85), and create_file deliberately errors under cfg(test) (util/file.rs:134-135)?**

- _Why it matters:_ The entire correctness story (tri-state reconciliation Q2, None-handling Q3, write-back loop Q4, late-registration persistence Q15) is testable only if a real file can be driven through the watcher in a test. Today's cfg gating means unit tests cannot exercise the file path at all, so the design must specify a seam (injected path/clock, or an integration harness) or the reset semantics ship untested.
- _How to answer:_ Review the test stubs (keyboard.rs:144-153), keyboard_tests.rs, and the integration framework (crates/integration; warp-integration-test skill). Decide whether to refactor keyboard.rs for path/IO injection (so cfg(test) can drive a temp file) or to add an integration test that writes a temp keybindings.yaml, fires the watcher, and asserts live keymap state via the matcher.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'copy the proven settings watcher pattern, it is low risk' - the keybindings file layer is deliberately stubbed out under cfg(test), so there is currently no way to assert reload behavior at all.

### UX/surface behavior

**A1-Q14. When a hot-reload hits a malformed keybindings.yaml, do we surface an error banner the way settings.toml does (WarpConfigUpdateEvent::SettingsErrors to workspace banner, init.rs:239-254 / workspace/view.rs:2670-2683), or silently log a warning (current keyboard.rs:50,135)?**

- _Why it matters:_ Defines the live-editing UX contract. Silent failure means a hand-editor sees nothing happen and cannot tell whether the reload worked or the file is broken - undermining 'the file is the source of truth that applies instantly.' Settings already set the precedent for surfaced parse errors with a dedicated event plus banner.
- _How to answer:_ Compare the settings error-surfacing path (init.rs:225-256 emitting SettingsErrors/SettingsErrorsCleared; workspace/view.rs:2670-2683 rendering the banner) with keybindings' silent logging (keyboard.rs:50-53,135). Decide on a parallel error event plus banner and its granularity (whole-file vs line/entry-level, leveraging the per-keystroke parse context already built at keyboard.rs:199-202).
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks 'applies instantly' - without error feedback, an instant no-op on a broken file is indistinguishable from success, so the user can't trust the live-data promise.

**A1-Q15. In-app edits read-modify-write an unordered HashMap serialized by serde_yaml (CustomKeybindings is a HashMap of name to PersistedTrigger, keyboard.rs:169; serde_yaml::to_writer, keyboard.rs:115), which loses comments and produces nondeterministic key ordering. For a config power users hand-edit and version-control, must writes preserve comments plus stable ordering (e.g. IndexMap / comment-preserving merge-in-place), or is clobbering formatting acceptable?**

- _Why it matters:_ The 'round-trip safe: file and in-app edits do not clobber each other' leaf is partly about FORMATTING, not just values. HashMap reserialization scrambles key order on every save (noisy git diffs) and drops user comments - a concrete clobber of the user's file even when binding values are preserved.
- _How to answer:_ Inspect CustomKeybindings (keyboard.rs:167-169) and save_custom_keybindings (keyboard.rs:100-122). Decide whether to switch to an order-preserving structure (IndexMap) and/or a comment-preserving YAML round-trip, or to explicitly scope the leaf to value-fidelity only and document that in-app saves rewrite file layout.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the assumption that round-trip safe is only about binding values; the HashMap plus serde_yaml read-modify-write silently rewrites the user's whole file layout on every in-app click.

### Performance/scale

**A1-Q16. Is per-reload cost acceptable? update_custom_trigger linearly scans editable_custom_action_bindings AND all editable_bindings per name (keymap.rs:423-432), ignoring the editable_bindings_by_name index (keymap.rs:30) that get_binding_by_name already uses (keymap.rs:380), so reapplying N file entries over roughly 437 editable bindings is O(N*437) on every 500ms-debounced save. Do we route the override path through the existing name index?**

- _Why it matters:_ A power user with a large keymap who hand-edits in a tight loop (or runs an import) triggers a full reapply repeatedly. Probably fine, but the spec should commit to a number and decide whether to fix the obvious O(N*M) by routing update_custom_trigger through editable_bindings_by_name - an index that already exists and is already used elsewhere but is bypassed by this exact function.
- _How to answer:_ Read keymap.rs:422-433 (linear filter) vs the index at keymap.rs:30, its population at keymap.rs:414-417, and its use at :380. Estimate M from the roughly 437 EditableBinding::new sites and a realistic N. Decide whether to index the override path now (low effort, the index exists) or accept the linear scan with a documented bound.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'reuse the existing apply path' - that path is quadratic and deliberately bypasses the very index built to avoid the scan, so naive reapply on every keystroke-save inherits a latent O(N*M).

<details><summary>Already settled by the report/code — pruned as non-questions (1)</summary>

- ~~Is keybindings.yaml actually delivered to handle_warp_managed_paths_event on all platforms - including when config_local_dir equals data_dir and on macOS?~~ — Answered by code: macOS has config_local_dir() equal to data_dir() (paths.rs:100-126), so the dedicated config watch is skipped but the recursive data_dir watch (warp_managed_paths_watcher.rs:255-261) with only a worktrees-exclusion filter (:254) covers keybindings.yaml at the config root (keyboard.rs:95-96). On Linux/Windows config_local_dir differs from data_dir so the accept_all config watch (:263-272) covers it. settings.toml lives in the same config_local_dir and already hot-reloads through this exact watcher (native.rs:130-132), proving the path is live on all platforms. Delivery is confirmed, not open.

</details>

---

