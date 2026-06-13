[← Back to index](./README.md)

## Axis 4 — Modality as a first-class, pluggable choice

**End state:** vim / helix / kakoune are peer editing modes chosen by one setting, sharing one engine and one executor.

> **Killer question:** Verified per-selection operator application ALREADY works (selection.rs:693-697 iterates all selections; vim_handler.rs operators map over the Vec1 of SelectionOffsets; add_cursor at selection.rs:499) but NO selection-set creation/management primitives exist (no regex-split s, line-split x, keep/remove-matching, rotate/collapse-primary anywhere in crates/editor or crates/vim). So for Helix ships as the proof, does v1 require the shared EditorCommand IR plus ModalEditExecutor to add NEW selection-set primitives (split-into-N, regex-select, keep/remove-matching, rotate/collapse-primary) and a grammar maintaining N persistent selections across keystrokes, or is v1 explicitly single-persistent-selection-only, making the proof a degenerate Helix that validates only select-then-act ordering, not Helix defining multi-selection identity?

### Scope/requirements

**A4-Q1. Is the leaf goal per-mode keymaps are themselves scoped bindings the user can edit/override IN SCOPE for Axis 4 v1, or cut to a later milestone -- given the report (section 6) states per-mode bindings are unusable without Axis 2 context-scoped overrides (L3, R3b) and Axis 3 layers/precedence (R2), sequenced as Phase-2 prerequisites?**

- _Why it matters:_ Decides whether the v1 deliverable ships hardcoded per-mode keymaps (engine + IR + Helix proof only) or must also deliver user-editable mode keymaps. Mis-scoping pulls two unrelated Phase-2 axes into this design and balloons the spec.
- _How to answer:_ Product decision: confirm with the initiative owner whether choose your mode via one setting + working Helix is acceptable as v1 WITHOUT user-editable mode keymaps. Cross-check against the dependency spine in the end-goals doc (lines 116-133) which explicitly gates Axis 4 behind Phase-2.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the assumption that pluggable modality implies user-editable mode keymaps in the same shippable unit, when the report explicitly gates the latter on two other axes.

**A4-Q2. Which editor surfaces get pluggable modality, and how are the new engines flag-gated? The code editor VimHandler is gated by FeatureFlag::VimCodeEditor (view.rs:357), but the terminal command editor has its OWN full VimHandler impl (mod.rs:1959) that is ALWAYS-ON (not flag-gated) with its own keymap_context Vim fork. Does Axis 4 cover only the code editor, or both? And are Helix/Kakoune gated behind the existing VimCodeEditor flag, a new ModalEditing flag, or per-engine experimental flags for staged rollout?** _(sharpened)_

- _Why it matters:_ Including the terminal doubles executor work (two impls times N engines) and raises a UX question (selection-first modes in a single-line shell prompt). The flag-gating choice determines rollout safety and whether an unfinished Helix can ship dark. Excluding the terminal leaves an inconsistent boolean-vs-enum split across surfaces.
- _How to answer:_ Read both VimHandler impls (app/src/code/editor/view/vim_handler.rs:23 and app/src/editor/view/mod.rs:1959) and confirm the terminal impl activation gating vs view.rs:357. Product decision on terminal scope; decide flag strategy (reuse VimCodeEditor vs new per-engine flags) for staged Helix/Kakoune rollout.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the implicit assumption that the editor is one thing -- there are two duplicate VimHandler surfaces with different activation gating, and no decided rollout flag for the new engines.

**A4-Q3. What concrete command set defines Helix ships as the proof for sign-off? Minimal select-then-act (basic w/e/b motions extending a single persistent selection plus d/c/y consuming it), or must it include Helix distinguishing multi-selection commands (C add cursor, s/regex select-split, x line-select, percent whole-file, collapse/keep) to count as validating that the IR generalizes?**

- _Why it matters:_ Sets the acceptance bar and directly couples to the multi-selection killer question. A minimal proof validates only ordering/persistence; a full proof forces the missing selection-set primitives (Q5) into the IR/executor/selection model now.
- _How to answer:_ Product decision enumerating the required Helix command list for sign-off, mapped against the proposed ExtendSelection/ApplyOperator primitives AND the missing selection-set primitives from Q5. Cross-reference the section 6 honest-unknown on Helix grammar depth.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks Helix as the proof as underspecified -- a select-then-act toy that drops multi-selection proves the IR for a Helix nobody recognizes.

### Design decision

**A4-Q4. The Entity trait carries one associated type Event (entity.rs:39-40); VimModel Event is VimEvent (vim.rs:1837) and subscribe_to_model is typed on that event (model/context.rs:67). Should all engines share Entity Event = EditorCommand so ONE subscription plus ONE blanket ModalEditExecutor impl (replacing vim.rs:1849) serves every mode -- and in that single executor, can Helix new ExtendSelection(Motion) REUSE vim motion dispatch (the 11-way navigate fan-out at vim.rs:1865-1883) or need a parallel fan-out? Or keep per-engine event types requiring N subscriptions in the ModalEngineModel enum?** _(sharpened)_

- _Why it matters:_ Drives the core API shape and executor trait surface. A shared event plus reused fan-out lets one blanket impl serve vim and helix and collapses the two duplicated VimHandler impls; per-engine events force N subscriptions and N lowering layers, defeating one executor. Whether ExtendSelection reuses navigate decides if the executor trait grows by ~2 methods or duplicates the whole motion table.
- _How to answer:_ Read entity.rs:39-40 (Entity/Event), model/context.rs:67 (subscribe contract), vim.rs:1849-1942 (fan-out). Verify whether one Entity can wrap a boxed dyn ModalEngine inner emitting EditorCommand, vs an enum of distinct Entities; decide whether extend_selection_by_motion delegates into the same navigate/vim_select_for paths with a keep_selection flag (vim_handler.rs:38-56 already uses one).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks enum avoids dyn issues as if free -- an enum still yields N Entity types with N event types unless a shared Event is chosen; and treats the executor as 1:1 when it already contains an 11-way fan-out that ExtendSelection must slot into.

**A4-Q5. The reusable buffer algorithms take vim-namespaced value enums -- vim_inner_word(.., WordType), vim_find_matching_bracket(.., BracketChar), vim_word_iterator_from_offset(.., WordType, WordBound) -- and vim_find_char is NOT generic (concrete &str, find_char.rs:28). Does the mode-agnostic EditorCommand IR carry these vim enums directly (coupling Helix/Kakoune to vim vocabulary), or define neutral motion/operator types with per-engine translation shims into the vim enums at the executor boundary?**

- _Why it matters:_ Defines the central artifact of the axis. Reusing vim enums is cheapest but cements mode-agnostic as a fiction; neutral types add a translation layer but keep the IR honest. This choice ripples through every engine, the executor trait, and future modes.
- _How to answer:_ Read word_iterator.rs:52, matching_brackets.rs:9, text_objects/word.rs:15, find_char.rs:28; list every vim-namespaced enum the algorithms require; decide whether Helix w/b/percent/mi-paren map cleanly onto the same WordType/BracketChar values or need new variants, and whether non-generic vim_find_char needs generalizing for a mode-neutral IR.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the report reused as-is claim, which glosses over that as-is means inheriting vim domain vocabulary into a supposedly neutral IR.

### Code fact to verify

**A4-Q6. Verified the editor ALREADY applies operators across all selections (update_selections_internal iterates selections.iter().zip(...).map(...) at selection.rs:693-697; vim operators map over Vec1 of SelectionOffsets e.g. vim_handler.rs:237,372; add_cursor at selection.rs:499) -- so per-selection apply is NOT the Helix gap. The actual gap: grep finds NO selection-set CREATION/management primitives (no split_selection/select_regex/rotate_selection/keep_matching/collapse-to-primary). Which specific Helix selection-management commands (s regex-split, S, x line-split, percent whole-file, keep/collapse, rotate-primary) require NEW model primitives, and does the IR/ModalEditExecutor own them or do they stay app-level?** _(sharpened)_

- _Why it matters:_ Determines what one executor for Helix actually costs. The report ~90% shared is half-right: the per-selection APPLY path is genuinely reusable, but Helix identity is selection-set MANAGEMENT, which has zero existing primitives. The design must name exactly which new model/IR operations are required, separate from operator application.
- _How to answer:_ Read selection.rs:672-726 (multi-selection apply), :499 (add_cursor), :642 (selections returns Vec1); enumerate Helix selection-set commands and map each to an existing or missing primitive; decide whether new primitives (split/regex-select/keep/rotate/collapse) land in crates/editor selection model, the IR, or the executor.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Refutes the draft own framing that operators assume a single primary selection (false -- they map over all), and refutes the report ~90% shared by pinpointing the truly-missing layer: selection-set creation, which no code path provides.

### Edge case/failure mode

**A4-Q7. VimModel is built once (ctx.add_model) and subscribed once (ctx.subscribe_to_model(&vim_model, Self::handle_vim_event)) at view.rs:359-360; the AppEditorSettings subscription at view.rs:312 has an empty body (no model rebuild), and mode is only re-read live via vim_mode_enabled() (view.rs:1953). When a user changes editing_mode mid-session (Vim to Helix), what happens to in-flight FSA state (pending_action, pending_action_count, pending_visual_object, register, dot_repeat_event, current submode -- vim.rs:42-54) and the existing single subscription, and is the engine Entity swapped or reset in place?**

- _Why it matters:_ An unhandled live switch leaves a half-typed operator pending or a stale subscription pointing at the wrong engine, corrupting the next keystroke. The enum-engine design must specify swap-vs-reset, re-subscription, and pending-state-discard semantics -- none of which exist today because the model is wired exactly once.
- _How to answer:_ Read view.rs:357-421 (construction) and confirm the settings observer at :312 does NOT rebuild the model. Decide: discard pending FSA state plus re-subscribe to a fresh engine Entity on editing_mode change, or keep one Entity holding a swappable inner boxed dyn ModalEngine reset on switch. Specify behavior for an in-flight operator at switch time.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that enum field selected at construction (Step A) covers runtime mode changes -- settings are mutable at runtime and the model is wired exactly once with an empty-bodied settings observer.

**A4-Q8. The report hand-waves that registers remain an app concern and generalize cleanly, but the FSA stores a vim-specific register: char (vim.rs:53), there is a vim-only app/src/vim_registers.rs (RegisterContent/write_to_register, used at vim_handler.rs:309-316,348-355), and a vim-only setting vim_unnamed_system_clipboard (editor.rs:211-220). Helix and Kakoune have different register/clipboard models (Kakoune especially). Does the shared EditorCommand IR plus executor carry a single register model, and does vim_unnamed_system_clipboard become a generalized modal_* setting, stay Vim-only, or get a per-engine analog?** _(added-by-critic)_

- _Why it matters:_ If register semantics are baked vim-specifically into the IR (e.g. register_name: char on Operation/Paste/VisualPaste events at vim.rs:558-599), every engine inherits vim register vocabulary, and the generalizes cleanly claim is untested. Mis-scoping leaves an orphaned vim-only clipboard setting or wrong yank/paste behavior under Helix/Kakoune.
- _How to answer:_ Read vim_registers.rs and the register_name: char fields on VimEventType::Operation/Paste/VisualPaste (vim.rs:558-599); compare Helix/Kakoune register models. Decide whether the register name/model is an IR field, an executor concern, or per-engine, and the fate of vim_unnamed_system_clipboard.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the report registers generalize cleanly assertion -- the IR events already hardcode register_name: char and a vim-only clipboard setting exists, so registers are not yet mode-neutral.

**A4-Q9. The IR is already polluted with vim repeat semantics: VimEventType::Operation carries a replacement_text field explicitly documented as kept empty except for Change when dot-repeated (vim.rs:565-572), and the FSA holds dot_repeat_event: Option of VimEvent driven by VimEvent::for_dot_repeat (vim.rs:56-57). Vim dot, Helix dot (repeat last insert), and Kakoune macro model (q/Q/no dot-repeat) differ. Does the shared EditorCommand IR carry repeat/dot-repeat state, or does each engine own its repeat mechanism with the IR staying stateless?** _(added-by-critic)_

- _Why it matters:_ If dot-repeat state stays in the shared IR, Helix/Kakoune inherit a vim-shaped repeat field that does not match their semantics; if it moves per-engine, the replacement_text/for_dot_repeat plumbing must be extracted from the IR. Either way the report 1:1 mapping, no buffer algorithm needed understates the repeat-state surface.
- _How to answer:_ Read vim.rs:56-57 (dot_repeat_event), the for_dot_repeat impl, and the replacement_text field usage (vim.rs:565-572; vim_handler.rs:144-152,325-326). Decide whether repeat is an IR-level concern or per-engine FSA state, and how macro recording (Kakoune q/Q) maps if at all.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks Vim existing events map 1:1 -- the Operation event already carries a dot-repeat-only replacement_text field, proving the IR is not yet repeat-neutral.

### Dependency/sequencing

**A4-Q10. Step D writes a dynamic format!('Modal:{engine}:{submode}') keymap context, but Context.set is HashSet of &static str (context.rs:5) and every ContextPredicate variant holds &static str (context.rs:11-17), with no FromStr/runtime-key path. Do we represent the per-engine submode cross-product as a CLOSED, compile-time-enumerated set of &static str flags (same mechanism as today VimNormalMode/VimVisualMode, view.rs:2388-2410), or does Axis 4 hard-require Axis 2 interned/Cow context-string refactor (R3a) as a prerequisite?**

- _Why it matters:_ Determines whether Axis 4 is shippable standalone or blocked on Phase-2 engine work. A closed &static str table keeps Axis 4 self-contained and reuses the proven vim-context mechanism; a runtime-derived key pulls the entire Axis-2 string-representation refactor (R3a) onto this axis critical path and reshapes the Step-D seam.
- _How to answer:_ Enumerate the full submode cross-product for vim+helix+kakoune (normal/insert/visual/select/replace/match/etc). If it is a fixed finite set, a closed &static str table suffices -- confirm via context.rs:3-18 and view.rs:2388-2410 that no runtime-derived context key is needed and that format!(...) in Step D was illustrative, not literal.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the report own Step D, which writes format!(...) as if insertable, ignoring that the live Context type forbids non-static keys.

### Migration/back-compat

**A4-Q11. The setting is vim_mode: bool with sync_to_cloud: SyncToCloud::Globally(RespectUserSyncSetting::Yes) at toml_path text_editing.vim_mode_enabled (editor.rs:202-210, no storage_key). When migrating to editing_mode/text_editing.modal_mode, how do mixed-version cloud-synced clients coexist -- dual-write both the legacy bool and the new enum, migrate-on-read via the vim_mode_enabled() shim (editor.rs:285), and which value wins when an OLD client toggles the bool while a NEW client has set Helix?**

- _Why it matters:_ Global cloud sync means an old client overwriting the bool can silently flip a new client out of Helix back to Vim/None, or lose the enum entirely. The design must pick a coexistence contract or risk cross-device setting corruption during rollout.
- _How to answer:_ Read the define_settings_group! macro contract and SyncToCloud::Globally semantics in crates/settings; compare a prior bool-to-enum migration (e.g. how CursorDisplayType enum at editor.rs:192 coexists with its storage_key). Decide dual-write vs migrate-on-read precedence and whether the new enum needs a distinct storage_key.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks Step E keep vim_mode_enabled() as a shim -- a READ shim does nothing for the WRITE/sync path across client versions under global cloud sync.

**A4-Q12. Non-char vim keys are forked by duplicate editable-binding registration with opposing predicates id(Vim)/not-id(Vim) (actions.rs:50-294), yielding distinct named actions (e.g. VimEnter vs Enter). These are EDITABLE bindings whose triggers a user can already override and persist by name to keybindings.yaml. When Step D migrates these to id(ModalEditing) plus a single ModalKeystroke action (renaming/removing the Vim-prefixed action names), what happens to a user existing persisted custom trigger keyed on an old Vim-prefixed action name -- does it silently orphan/no-op, or is there a name-migration map?** _(added-by-critic)_

- _Why it matters:_ Override persistence is name-keyed (keyboard.rs HashMap String to PersistedTrigger; update_custom_trigger filters by name only, keymap.rs:422). Renaming the forked action set on migration would silently drop every existing user customization of those keys, a real cross-version data-loss failure mode the report does not address.
- _How to answer:_ Enumerate the forked Vim-prefixed action names in actions.rs:50-294 and mod.rs:200-205,962-971; check how keybindings.yaml entries map to names (keyboard.rs:169,189-213). Decide whether to keep the old names as aliases, provide a yaml migration, or accept the loss; verify against update_custom_trigger (keymap.rs:422-433).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks Step D seam migration as if purely internal, ignoring that the forked bindings are user-overridable and persisted by name in keybindings.yaml -- renaming them orphans existing customizations.

### Testing/validation

**A4-Q13. What regression net guards the refactor of VimEventType to EditorCommand, the blanket subscriber (vim.rs:1849), and the two VimHandler impls? Are there existing keystroke-to-VimEvent (FSA-level) and keystroke-to-buffer-mutation (handler-level) golden/unit tests we extend, and will each new engine be validated by shared keystroke-trace fixtures asserting the emitted EditorCommand stream?**

- _Why it matters:_ Widening the IR and collapsing two executors is a high-blast-radius refactor; without FSA-level golden tests, vim regressions ship silently and the new engines have no objective correctness bar.
- _How to answer:_ Locate vim FSA tests (grep test-attr in crates/vim/src; check typed_character/keypress assertions) and handler/selection tests (selection_tests.rs, model_tests.rs which already exercise add_cursor). Assess coverage of VimFSA event emission vs handler mutation. Decide a shared keystrokes-to-EditorCommand-vec fixture format usable by vim/helix/kakoune.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that clean FSA layering makes the refactor safe -- clean layering without golden tests still lets a renamed/widened IR silently change vim behavior.

### UX/surface behavior

**A4-Q14. Step E says surface as a dropdown, but vim_mode today is a toggle (ToggleVimMode to toggle_and_save_value, features_page.rs) with TWO dependent toggles vim_unnamed_system_clipboard and vim_status_bar (editor.rs:211-228), and vim_status_bar (default true) drives a runtime status-bar mode indicator. Under editing_mode, (a) where does the dropdown live and what options show when the surface is VimCodeEditor-gated; (b) do the vim-only sub-settings become modal_*, stay Vim-gated, or get dropped; and (c) what does the runtime status bar SHOW for Helix submodes / selection-count vs vim mode string?** _(sharpened)_

- _Why it matters:_ Determines the settings-UI rework scope AND the runtime indicator. Getting (a) wrong offers modes the surface cannot run; (b) wrong leaves orphaned toggles; (c) wrong leaves Helix with no submode/selection-count feedback or a vim-only status bar that lies under other engines.
- _How to answer:_ Read the features_page dropdown infra (e.g. code_editor_line_number_mode_dropdown) and the ToggleVimMode pair; read the status-bar rendering that consumes vim_status_bar/VimMode. Decide dropdown placement, conditional-visibility rules for vim sub-settings per editing_mode, and per-engine status-bar content.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks just make it a dropdown -- vim is a toggle with satellite toggles AND a runtime status indicator, so the migration is a UI plus indicator restructuring, not a control swap.

**A4-Q15. Cursor shape is derived from vim_mode: Option of VimMode carried on the render element (element.rs:203), while users also have an independent CursorDisplayType setting (element.rs:51, editor.rs:192). When a modal mode is active, does the mode per-submode cursor (e.g. block in normal/select, bar in insert) OVERRIDE the user CursorDisplayType, and does that ownership move into Step D proposed ModalCursorState?**

- _Why it matters:_ Two sources of truth for cursor shape will conflict; the design must declare precedence (mode-submode vs user setting) per submode, or users in Helix-insert vs vim-insert see inconsistent/wrong cursors.
- _How to answer:_ Read element.rs where vim_mode/CursorDisplayType jointly decide the rendered cursor (the is_some() fork at :617 and the cursor-shape match). Define the precedence table per (engine, submode).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks Step D ModalCursorState as if cursor shape were mode-owned, ignoring the pre-existing user CursorDisplayType setting it must reconcile with.

### Performance/scale

**A4-Q16. Helix/Kakoune emit ExtendSelection on EVERY motion keystroke against a persistent (potentially N-way) selection, whereas vim computes a single selection only at operator-apply time and discards it. Given update_selections_internal (selection.rs:682-726) calls merge_overlapping_selections then maps plus normalize_selections over the whole Vec1 every update, does per-keystroke multi-selection re-normalization/re-render stay within frame budget for large selection counts (Helix percent/x/s on a large file)?**

- _Why it matters:_ If per-keystroke multi-selection update is O(N selections times buffer work) it can make Helix navigation janky on big files -- a regression the vim apply-once path never exercised. The design may need incremental updates or a selection-count cap.
- _How to answer:_ Profile/inspect update_selections_internal (selection.rs:682-726), merge_overlapping_selections, and normalize_selections cost; check whether UpdateSelectionOffsets rebuilds the full RenderedSelectionSet or updates incrementally. Estimate worst-case selection counts for Helix percent/x/regex-select on a large file.
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Attacks the report differs from vim only in ordering and persistence of selection -- persistence means per-keystroke selection re-normalization over all N selections, a cost vim apply-once path never paid.

<details><summary>Already settled by the report/code — pruned as non-questions (1)</summary>

- ~~A4-Q7: When the blanket VimHandler impl becomes a ModalEditExecutor impl, does the non-1:1 fan-out/no-op lowering (Navigate to 11 methods, ReplaceChar(None) to no-op) stay centralized or get duplicated per engine?~~ — Largely already answered. Report section 2d explicitly documents the non-1:1 dispatch as fact (VimEventType::Navigate fans out to ~11 trait methods at vim.rs:1865-1883; ReplaceChar(None) maps to no method ~vim.rs:1898), and section 5 Step B prescribes ONE blanket executor Subscriber impl replacing vim.rs:1849, so the fan-out is centralized by construction. Verified the fan-out is exactly as described. The only open residual (whether Helix ExtendSelection can reuse vim navigate methods) is folded into sharpened A4-Q3 about the executor trait surface, making this duplicative.

</details>

---

