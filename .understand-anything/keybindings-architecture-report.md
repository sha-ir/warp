# Warp Keybindings — Architecture & Improvement Report

## 1. Executive summary

- **Today's shape:** Keybindings are *code, not data*. A single `Keymap` (`crates/warpui_core/src/keymap.rs:24-38`) holds two parallel vectors — immutable `FixedBinding`s and overridable `EditableBinding`s — registered imperatively at view-init time across ~265 scattered call sites in ~109 files. Matching is a linear, first-match-wins scan (`matcher.rs:307-346`). The only runtime customization is *overriding an existing editable binding's trigger by name*, persisted to a flat `keybindings.yaml` that is applied once at launch and never watched.

- **Engine (Goal 1) highest-leverage change:** Add a **file watcher + reload path for `keybindings.yaml`** to match `settings.toml` hot-reload — it is the single biggest configurability papercut for *external* edits: manual `keybindings.yaml` changes need a restart (`app/src/lib.rs:2557`), even though in-app edits made through the settings UI already apply live (§2c). The deeper structural change is a **binding-layer/precedence model** plus a **context-scoped, data-driven user schema** (the engine already supports rich `ContextPredicate`s internally; the user file collapses them away).

- **Settings UI (Goal 2) highest-leverage change:** Make **conflict detection context-aware and actionable**. Today `ConflictMap` keys on `Keystroke` alone with no context predicate (`app/src/settings_view/keybindings.rs:106`), produces false positives, names no colliding action, and never blocks a save. Secondary wins: search-by-action-name, chord capture, import/export.

- **Modal (Goal 3) highest-leverage change:** Generalize the already-clean `VimFSA → VimEvent → VimHandler` pipeline into a **pluggable `ModalEngine` + mode-agnostic `EditorCommand` IR**, and replace the boolean `text_editing.vim_mode_enabled` setting (`app/src/settings/editor.rs:202-210`) with an `EditingMode` enum. The buffer algorithms in `crates/vim` (text objects, word iterators, bracket matcher) are already generic and reusable by Helix/Kakoune.

- **Cross-cutting truth:** All three goals converge on one missing primitive — **a first-class notion of "binding layer / mode / context-scope" in the engine**. Per-mode keymaps (modal), per-context overrides (UI), and data-driven config (engine) are the *same feature* viewed from three angles.

---

## 2. Current architecture

### (a) The keymap engine

The core is `Keymap` (`crates/warpui_core/src/keymap.rs:24-38`), holding two binding kinds plus a name index:

- **`FixedBinding`** (`keymap.rs:277-286`): compiled-in and immutable. It has fields `trigger / action / command_description / context_predicate / enabled_predicate / group / id` — **no `name`, no `custom_trigger`**. Its doc comment states it "can't be reconfigured with a custom key binding trigger" (`keymap.rs:275`), and its `as_lens` hardcodes `name: Default::default()` / `original_trigger: None` (`keymap.rs:631-642`). Fixed bindings are therefore non-overridable.
- **`EditableBinding`** (`keymap.rs:293-304`): carries `name: &'static str` (`:294`) and `custom_trigger: Option<Trigger>` (`:300`). When `custom_trigger` is `Some`, `as_lens` (`keymap.rs:741-759`) substitutes it for the default `trigger` (recording `original_trigger`) — but only for that one binding. Editable bindings are wrapped in `Tracked<T>` (`core/autotracking/tracked.rs:19-55`) so mutations notify the autotracking UI.

A **`Trigger`** (`keymap.rs:43-49`) is one of `Keystrokes(Vec<Keystroke>)`, `Standard(StandardAction)`, `Custom(CustomTag)`, or `Empty`.

**Matching** is owned by `Matcher` (`matcher.rs:13-30`), which holds the `Keymap` plus per-`EntityId` `Pending` buffers (`matcher.rs:32-36`). `push_keystroke` (`matcher.rs:307-346`) appends to the view's pending buffer, clears it on context change, then **linearly scans `keymap.bindings()`** for the first binding whose keystroke vector `starts_with` the pending buffer and whose `context_predicate.eval(ctx)` is true. An **exact-length match returns `Action` immediately** (`matcher.rs:329-331`); a longer match yields `Pending`. There is no trie/index, no ambiguity timeout, and no longest-match disambiguation (grep for `timeout|ambig|longest` in `keymap/` returns nothing). A consequence: a complete short binding **shadows** any longer chord sharing its prefix in the same context.

**Precedence is purely iteration order.** `bindings()` (`keymap.rs:454-464`) yields `editable_bindings()` (enabled editable bindings in **reverse-registration / LIFO** order, `keymap.rs:441-447`) then `fixed_bindings.iter().rev()`. First match wins; there is no priority/specificity/sort mechanism anywhere in `keymap.rs`/`matcher.rs`.

**`Context`** (`context.rs:3-7`) is `HashSet<&'static str>` + `HashMap<&'static str, &'static str>`, built per-view by `keymap_context` (`core/mod.rs:252`) and merged up the responder chain (`app.rs:1846-1864`). **`ContextPredicate`** (`context.rs:9-18`) supports exactly `Identifier`, `Equal`, `NotEqual`, `Not`, `And`, `Or`, `Just(bool)`, evaluated in `context.rs:100-120`. Predicates are **constructed only in Rust** via macros (`id!`/`eq!`/`ne!`/`always!`, `context.rs:20-87`) and operator overloads — **there is no `FromStr`/parser** for `ContextPredicate`, and keys are `&'static str`, so contexts cannot be created from runtime/config data.

**Platform divergence** (`cmd` vs `ctrl`) is resolved at parse/construction, not stored: `Keystroke::parse` maps `"cmdorctrl"` to `cmd` or `ctrl` via `OperatingSystem::get()` (`keymap.rs:914-919`), and `new_per_platform` (`keymap.rs:497-508`) / `with_mac_key_binding` / `with_linux_or_windows_key_binding` (`keymap.rs:688-713`) pick one string at build time. A live `Keystroke` holds only the current OS's modifiers — there is no `cmdorctrl` field on the struct (`keymap.rs:320-328`).

**Action spaces.** `Trigger::Standard` wraps `StandardAction`, a **closed 10-variant enum** (`actions.rs:8-19`: Close/Hide/HideOtherApps/ShowAllApps/Quit/Zoom/Minimize/BringAllToFront/ToggleFullScreen/Paste). `Trigger::Custom` wraps `CustomTag` (= `isize`, `keymap.rs:41`), in practice a **closed set** backed by the `CustomAction` enum — `From<CustomTag> for CustomAction` panics via `.expect("All custom actions are handled.")` on unknown tags (`app/src/util/bindings.rs:226-231`). Action payloads themselves are *open* (blanket `impl<T> Action for T where T: Any + Debug + Send + Sync`, `core/action.rs:23-30`) but only do anything if a handler is registered **at runtime** (via `add_typed_action` during view registration) into a `HashMap` keyed by `(ActionType, ViewType)` (`app.rs:1259-1263`, lookup at `app.rs:1486-1529`). *(Note: the original research said "compile time"; corrected — the key *types* are compile-time-known, the registry is runtime-populated.)*

### (b) Config & load pipeline

**Defaults are compiled in, registered at runtime, distributed.** Each view's setup calls `app.register_fixed_bindings([...])` / `app.register_editable_bindings([...])` (`core/app.rs:1619-1639` → `matcher.rs:89,112` → `keymap.rs:391,405`). There are **~265 combined call sites across 109 files** (146 `register_fixed_bindings` + 119 `register_editable_bindings`; e.g. `app/src/root_view.rs:426,448`, `app/src/editor/view/mod.rs:188`). There is **no single default keymap table and no on-disk default file** (no `include_str!` of a keymap, no `DEFAULT_KEYMAP` const). Binding names are inline `&'static str` literals like `"editor_view:delete_all_left"` (`app/src/code/editor/view/actions.rs:560`); the `namespace:action` form is convention, never parsed.

**The user file** lives entirely in `app/src/keyboard.rs`. It is `keybindings.yaml` (`keyboard.rs:33`) under `config_local_dir()` (`keyboard.rs:95-97`), platform/channel-specific (`paths.rs:85-126`). Its schema is a **flat `HashMap<String, PersistedTrigger>`** (`keyboard.rs:169`) — action-name → a single normalized keystroke string (space-separated for chords, `keyboard.rs:176-187`), with the literal `"none"` meaning "remove" (`keyboard.rs:15,189-213`). The `TryFrom` only ever produces `Keystrokes` or `Removed`; it **cannot express context/scope, platform, or Standard/Custom triggers**.

**Load is launch-only.** `load_custom_keybindings` (the sole function that pushes file contents into the live keymap via `app.set_custom_trigger`) is called only from `launch()` (`app/src/lib.rs:2557`). The file is **not watched**: the config watcher `handle_warp_managed_paths_event` (`app/src/user_config/native.rs:74-134`) emits reload events for themes/workflows/launch-configs/tab-configs/settings.toml but has **no branch for `keybindings.yaml`**. By contrast `settings.toml` hot-reloads via `reload_from_disk` + `SettingsManager::reload_all_public_settings` (`crates/settings/src/manager.rs:327`, wired in `app/src/settings/init.rs`). External edits to `keybindings.yaml` therefore require a restart. *(Precision note: the underlying `read_custom_keybindings` (`keyboard.rs:128-139`) is also called on in-app add/remove at `keyboard.rs:71,89`, so the file is read more than once per session — but those reads never apply *external* edits to the running app.)*

**Override is by name, context-blind.** Each entry calls `app.set_custom_trigger(name, ...)` → `update_custom_trigger` (`keymap.rs:422-433`), which filters editable bindings **only by `name`** and overrides every binding sharing that name regardless of its `ContextPredicate`. One name can map to several bindings with distinct contexts (`editable_bindings_by_name: HashMap<&'static str, Vec<usize>>`, `keymap.rs:30`), and all get the same trigger.

**No real action catalog.** Descriptions are supplied inline at ~437 `EditableBinding::new` registration sites; the authoritative enumeration is the live registry walked via `ctx.editable_bindings()`. There is a *static, name-only* catalog grouping ~80 names into categories in `app/src/resource_center/utils.rs:8-114`, plus a 5-entry hardcoded list *with* descriptions in `get_additional_keybindings()` — but no comprehensive `(id, description, default, context)` manifest.

### (c) The settings UI

There are **two surfaces**:

1. **The editor** — `app/src/settings_view/keybindings.rs` (Settings → Keyboard shortcuts).
2. **A read-only cheatsheet** — `app/src/resource_center/keybindings_page.rs`. Its action enum `KeybindingsAction {}` is empty (`:69-70`), it overrides no `handle_action`, it filters bound shortcuts (`trigger.is_some()`) into hardcoded curated sections (`utils.rs:8-114`), and it only links back to the editor via `WorkspaceAction::ConfigureKeybindingSettings` (`:360-382`).

**The editor's list** comes from the live keymap: `on_page_selected` (`keybindings.rs:748-784`) collects `ctx.editable_bindings()` (`:754` → `app.rs:1788` → `matcher.rs:294` → `keymap.rs:441`), maps each lens via `CommandBinding::from_editable_lens` (`app/src/util/bindings.rs:762`), sorts by description+name, then `dedup_by(|a,b| a.name==b.name && a.description==b.description)` (`:782`). **Only editable bindings appear**; fixed bindings and custom menu actions cannot be rebound here.

**Search** goes through `filter_bindings_including_keystroke` (`app/src/util/bindings.rs:625-687`): it fuzzy-matches `binding.description.in_context(...)` (`:650-653`) and/or parses a keystroke from text like `"cmd d"` via `convert_search_term_to_keystroke` (`:571`). It **never references `binding.name`** — the internal action id is unsearchable.

**Capture & persist.** Clicking a row calls `ctx.disable_key_bindings_dispatching()` (`keybindings.rs:578`) so keystrokes aren't consumed as app actions; an `EventHandler::on_keydown` dispatches `KeystrokeDefined(index, keystroke)` (`:293-301`) into `set_temporary_keystroke_state` (`:701-722`), which writes a **single** `unsaved_binding: Option<Keystroke>` (`:88`) — each keydown overwrites the prior, so **chords cannot be captured from the UI** even though `UserDefinedKeybinding::Keystrokes(Vec1<Keystroke>)` (`keyboard.rs:20-25`) and the YAML format support them. Save (`confirm_keystroke_editing`, `:669`) calls `set_custom_keybinding` (`bindings.rs:491-506`), which does **both** `ctx.set_custom_trigger` (live in-memory, `matcher.rs:137-141`) **and** `write_custom_keybinding` (`keyboard.rs:64-75`) — so changes apply **live, no restart**.

**Conflict detection is shallow.** `ConflictMap` is `HashMap<Keystroke, usize>` (`keybindings.rs:106`) keyed on the bare `Keystroke` (which has no context field, `keymap.rs:321-328`). It flags any keystroke used by >1 editable binding (`:123`) **regardless of whether their context predicates overlap**, renders only a warning border + text `SHORTCUT_CONFLICT_WARNING_TEXT` (`:48,270-276,313-324`), and **never blocks saving** (the confirm path performs no conflict check).

**No per-context editing.** Custom triggers are saved/loaded purely by name → `update_custom_trigger` applies to *every* editable binding of that name across all views/contexts, including same-name rows that the display dedup did *not* collapse (because they have different descriptions). `CommandBinding` exposes no editable context/predicate field (`bindings.rs:531-541`).

### (d) Modal / vim

The stack is cleanly layered into four tiers:

1. **Keystroke fork (input → mode).** Printable chars reach the rich-text render element, which holds `vim_mode: Option<VimMode>` (`crates/editor/src/render/element/mod.rs:127`) and forks on `self.vim_mode.is_some()` in `handle_typed_characters` (`mod.rs:726-743`), dispatching `vim_user_typed` vs `user_typed`. The terminal `EditorView` has the same fork in `typed_characters` (`app/src/editor/view/element.rs:617-621`: `VimUserInsert` vs `UserInsert`). The fork is **boolean** — all four `VimMode` variants collapse to `is_some()`.

2. **Action → engine.** `VimUserTyped` is handled at `app/src/code/editor/view/actions.rs:824-837`, calling `vim_user_insert` (`view.rs:2081-2091`) → `VimModel::typed_character` (`vim.rs:1813`). Non-char keys are forked by **duplicate binding registration** with opposing predicates `id!("Vim")` / `!id!("Vim")` (`actions.rs:51-60`), yielding distinct actions (e.g. `Enter` vs `VimEnter`) where the Vim variant routes through `vim_keystroke`. *(Precision note: only non-char keys needing vim-specific handling are forked — enter/numpadenter/shift-enter/backspace/delete/tab; navigation/selection keys like arrows/home/end keep a single binding.)* The `"Vim"`/`"VimNormalMode"`/`"VimVisualMode"` context flags are inserted in `keymap_context` (`app/src/code/editor/view.rs:2388-2410`).

3. **Engine (pure FSA).** `VimFSA` (`crates/vim/src/vim.rs:37`) holds `mode: VimMode` (`:38`; enum `Normal/Insert/Visual(MotionType)/Replace` at `:14-20`) plus pending-command state. `typed_character` (`:749`) and `keypress` (`:775`) consume one keystroke and return `Option<VimEvent>` (`:524`) **without ever mutating a buffer** (a grep of the FSA region for buffer-edit calls returns nothing; the design intent is documented at `vim.rs:1796-1798`). The verb-then-motion grammar lives here as `PendingAction::Operation { operator, pending_operand }` (`:242-257`). Char→meaning is **hardcoded match arms** (`handle_normal_nothing_pending`, `:896-1053`), not a data table.

4. **Event → execution.** `VimModel` (`vim.rs:1800`) wraps the FSA as a warpui `Entity` and emits `VimEvent`. A blanket `impl<T: VimHandler> VimSubscriber for T` (`vim.rs:1849-1942`) lowers each `VimEventType` (`:540-599`) to a `VimHandler` (`:1945-2064`) trait method via `handle_vim_event` (`:1853-1941`). `VimHandler` is implemented **twice**: `CodeEditorView` (`app/src/code/editor/view/vim_handler.rs:23`, delegating to `model.vim_*`) and the terminal `EditorView` (`app/src/editor/view/mod.rs:1959`, using `self.edit(...)`). This is the **vim-mode** mutation path — *not* a universal one: non-vim editing (`UserTyped`/`Backspace`/`Delete`/`Enter`/paste) mutates the model directly (`actions.rs:823,839,841,847`; `mod.rs:8424`). And dispatch is **not strictly 1:1**: `VimEventType::Navigate` fans out to ~11 trait methods by inner `VimMotion` (`vim.rs:1865-1883`), and `ReplaceChar(None)` maps to no method. *(This corrects the originally-overstated "all mutation flows through VimHandler" claim, which was refuted.)*

**Activation** is a single bool: `vim_mode_enabled() = supports_vim_mode && AppEditorSettings::vim_mode_enabled()` (`view.rs:1952-1953`), backed by `text_editing.vim_mode_enabled` (bool, default `false`, `settings/editor.rs:202-210`, accessor `:285-287`). `supports_vim_mode` is itself gated by `FeatureFlag::VimCodeEditor` for the code editor (`view.rs:357`). There is **no setting to select among multiple modal schemes** — Helix/Kakoune are entirely absent from the engine (their only appearance is the unrelated external-editor launcher `app/src/util/file/external_editor/mod.rs:267-268`).

### Key-event flow (ASCII)

```
            keypress (physical key / typed char)
                          |
        +-----------------+------------------+
        |                                    |
  PRINTABLE CHAR                       NON-CHAR KEY
        |                                    |
  RichTextElement.handle_typed_characters    keymap context system
  (element/mod.rs:726-743)                   dispatch_keystroke (app.rs:2005)
        |                                            |
  self.vim_mode.is_some() ? ----no--> user_typed     Matcher.push_keystroke
        |                              (UserInsert)   (matcher.rs:307-346)
       yes                                            | linear scan bindings()
        |                                             | editable(rev/LIFO) -> fixed(rev)
  vim_user_typed / VimUserInsert                      | first match wins (no trie/timeout)
        |                                             |
  vim_user_insert (view.rs:2081)        +-------------+--------------+
        |                               |                            |
  VimModel.typed_character        id!("Vim") match?            !id!("Vim") match?
  (vim.rs:1813)                    -> VimEnter / VimTab...      -> Enter / Tab...
        |                               |                            |
        +------------> VimFSA  <--------+ vim_keystroke              | model.enter / user_insert
                    (vim.rs:37)         (view.rs:2094)              (direct mutation)
                       |
                  Option<VimEvent>  (pure, no buffer touch)
                       |
            VimModel emits -> VimSubscriber blanket impl (vim.rs:1849)
                       |
            handle_vim_event -> VimHandler method (vim.rs:1945)
                       |
       CodeEditorView::* (vim_handler.rs:23)  |  EditorView::* (mod.rs:1959)
                       |
              selection + buffer mutation
```

---

## 3. Goal 1 — A more flexible & configurable engine

### Confirmed limitations

| # | Limitation | Evidence |
|---|---|---|
| L1 | **No hot-reload of `keybindings.yaml`.** Applied once in `launch()`; the config watcher has no branch for the file. *External/manual* edits need a restart — in-app settings-UI edits already apply live via `set_custom_trigger` (§2c), so this only bites users who hand-edit the YAML. | `app/src/lib.rs:2557`; `app/src/user_config/native.rs:74-134` (no keybindings branch); contrast `crates/settings/src/manager.rs:327` |
| L2 | **User file cannot express context, platform, or Standard/Custom triggers.** Flat `HashMap<String, PersistedTrigger>`; `TryFrom` yields only `Keystrokes`/`Removed`. | `app/src/keyboard.rs:169,189-213` |
| L3 | **Overrides are name-keyed and context-blind.** `update_custom_trigger` filters only by `name`, clobbering all same-name bindings regardless of `ContextPredicate`. | `keymap.rs:422-433` |
| L4 | **No binding layers / explicit precedence.** Precedence is only fixed-vs-editable + reverse-registration LIFO; first match wins; no priority/sort. You cannot truly *unbind* a default except by overloading `Trigger::Empty`. | `keymap.rs:454-464`; grep found no priority/sort/specificity |
| L5 | **Linear O(n) scan, no ambiguity policy.** A complete short binding silently shadows any longer chord sharing the prefix; no trie, no timeout, no longest-match. | `matcher.rs:307-346` (early return `:329-331`); no `timeout/ambig/longest` hits |
| L6 | **Contexts are `&'static str` and predicates are Rust-only.** No `FromStr` parser; config/extensions cannot express new contexts or conditions. | `context.rs:3-18,20-87`; no `FromStr` for `ContextPredicate` |
| L7 | **Platform is baked at parse.** A single build holds only the current OS's binding — blocker for a cross-platform settings UI. | `keymap.rs:914-919,497-508,688-713` |
| L8 | **Closed Standard/Custom action spaces; no data-driven registration.** New actions/bindings/contexts cannot be added from config; only existing editable triggers can be overridden. | `actions.rs:8-19`; `bindings.rs:226-231`; `keymap.rs:422-433`; ~265 imperative register sites |
| L9 | **Fixed bindings cannot be remapped or unbound at all.** `FixedBinding` has no name and is documented "can't be reconfigured." *(Partial: the codebase does NOT establish a "large fraction" of shortcuts are Fixed — `FixedBinding` appears reserved for internal/transient bindings; user-facing shortcuts are `EditableBinding`.)* | `keymap.rs:275-286` |

### Recommendations

**R1 — Live file watcher for `keybindings.yaml` (quick win).** Reuse the watcher pattern that drives `reload_all_public_settings` (`app/src/settings/init.rs`, `crates/watcher/src/home_watcher.rs`). On a change event for `keybinding_file_path()` (`keyboard.rs:95`), re-run a reload that first **resets custom triggers for names no longer present** (`remove_custom_trigger`, `matcher.rs:146`) then re-applies `set_custom_trigger` for the parsed map. This needs a new "currently-applied custom names" set so removed entries revert to default. Low risk; copies an existing proven mechanism; eliminates the biggest papercut (L1).

**R2 — Binding-layer / source model with explicit precedence (deep refactor).** Extend `Keymap` (`keymap.rs:24-38`) with a `layer`/`priority` tag per binding (default / user / mode-pack / extension) and resolve `bindings()` (`keymap.rs:454-464`) by `(layer, recency)` instead of the fixed-vs-editable + LIFO assumption. Add an explicit `Unbound` state rather than overloading `Trigger::Empty`. This is the foundation that per-mode keymaps (Goal 3) and clean user overrides build on (addresses L3, L4, L9).

**R3 — Data-driven, context-scoped user schema (deep refactor).** Extend `CustomKeybindings` (`keyboard.rs:169`) from `HashMap<String, PersistedTrigger>` to a list of records `{ name, trigger, context?: predicate, platform? }`. Add a `FromStr` parser for `ContextPredicate` supporting the existing `& | ! == !=` grammar (`context.rs:20-87`), switch `Context`/`ContextPredicate` string storage to `Cow<'static, str>` or interned IDs, and thread the parsed predicate through `set_custom_trigger` so `update_custom_trigger` (`keymap.rs:422`) can match `name + context`, not name alone. Preserve `eval()`'s shape (`context.rs:100-120`). Addresses L2, L3, L6.

**R4 — Indexed lookup + ambiguity policy (medium).** In `matcher.rs`, build a per-context-eligible trie keyed by `Keystroke`; change `Pending` (`matcher.rs:32-36`) to track a candidate set; in `push_keystroke` distinguish "exact-only" from "exact-with-longer-prefix" and add a configurable resolution policy (immediate vs wait-for-timeout). Keep `bindings()` precedence order as the tiebreaker. Addresses L5.

**R5 — Represent platform in the data model (medium).** Store `Trigger` keystrokes with an unresolved `CmdOrCtrl` modifier or a `{mac, other}` pair, resolving only at match/display time via `OperatingSystem::get()`. Update `Keystroke::parse`/`normalized`/`displayed`. Required for a cross-platform settings UI (L7).

---

## 4. Goal 2 — Settings UI for keybindings

### Confirmed gaps

| # | Gap | Evidence |
|---|---|---|
| G1 | **Conflict detection is context-blind, non-actionable, non-blocking.** Keyed on bare `Keystroke`; flags false positives across non-overlapping contexts; never names the colliding action; never prevents save. | `keybindings.rs:104-133` (`HashMap<Keystroke,usize>`), `48,270-276,313-324`; confirm path `669-699` has no check |
| G2 | **No per-context view or editing.** Editing a row changes the binding for every view/context registered under that name (save-by-name → `update_custom_trigger`). `CommandBinding` has no editable context field. | `keybindings.rs:782` (dedup name+desc), `bindings.rs:491-506`, `keymap.rs:422-433`, `bindings.rs:531-541` |
| G3 | **Search ignores internal action names.** Only description fuzzy-match + keystroke parse; the `name` field is never consulted. | `bindings.rs:625-687`, `convert_search_term_to_keystroke:571`; `name` used only at `bindings.rs:517,900` |
| G4 | **Single-keystroke capture only.** `unsaved_binding: Option<Keystroke>` overwrites on each keydown; `set_custom_keybinding` hardcodes a 1-element vec — even though the format supports `Vec1<Keystroke>` chords. | `keybindings.rs:88,293-301,701-722`, `bindings.rs:491-499`; format at `keyboard.rs:20-25,176-211` |
| G5 | **Fixed bindings are invisible & uneditable; no unbound/custom filters; no import/export.** Editor lists only `editable_bindings()`; keybindings are local-only, never synced. | `keybindings.rs:754`; `keybindings.rs:1108` (no cloud sync) |
| G6 | **No discoverability of all bindable actions.** No `(id, namespace, description, default, context)` catalog; descriptions live inline at ~437 registration sites. | `bindings.rs` registration sites; static name-only catalog `resource_center/utils.rs:8-114` |

### Recommendations

**R6 — Context-aware conflict detection that names the collision (quick-to-medium).** Replace `ConflictMap` with a map keyed on `(Keystroke, context-group)` using each `CommandBinding`'s context predicate/group (`EditableBindingLens.context`, `keymap.rs:311`; `BindingGroup`, `bindings.rs:797`). Store conflicting binding *names* so `render_clicked` (`keybindings.rs:307`) can show "Conflicts with: \<description\>" and offer one-click rebind/swap. Optionally gate Save on an unresolved *hard* (same-context) conflict. Directly addresses G1.

**R7 — Search by action name + filter chips + import/export (quick win).** Extend `filter_bindings_including_keystroke` (`bindings.rs:650`) to also fuzzy-match `binding.name`. Add filter chips (All / Customized / Unbound / Conflicts) driven by `trigger.is_some()` and presence of `original_trigger` (`keymap.rs:315`). Add Import/Export buttons reading/writing `keybindings.yaml` via the existing `keyboard.rs:95-139` save/read functions. Addresses G3, G5.

**R8 — Chord capture in the editor (medium).** Change `KeyBindingModifyingState.unsaved_binding` from `Option<Keystroke>` to `Vec<Keystroke>`; have `set_temporary_keystroke_state` (`keybindings.rs:710`) **push** rather than overwrite, with a short timeout / explicit "add next key" affordance; thread `Trigger::Keystrokes(vec)` through `confirm_keystroke_editing` and `set_custom_keybinding` (`bindings.rs:491`). The data model and YAML already support it. Addresses G4.

**R9 — Surface a real action catalog incl. read-only fixed bindings (medium, depends on engine work).** Add a startup pass that walks all registered bindings via `Matcher::editable_bindings()` (and, after R2, fixed bindings too) and emits a structured manifest `(name, BindingDescription, group keymap.rs:253, context predicate, default trigger, fixed-vs-editable)`. Feed it into the settings UI to display (read-only) fixed bindings and group/flag conflicts, and persist it for the change-keybinding skill so an agent can map a description → action id without guessing. Addresses G6, G5.

**R10 — Run binding validators on the edit path (quick win).** `is_binding_pty_compliant` / `is_binding_cross_platform` exist but are `#[cfg(debug_assertions)]`, run only at registration via `validate_bindings()` (`matcher.rs:159-203`); `set_custom_trigger` performs no validation. Expose a release-build `AppContext::validate_trigger(name, trigger) -> IsBindingValid` reusing the registered validators, and call it from `confirm_keystroke_editing` (`keybindings.rs:669`) to inline-warn (e.g. "shadows a PTY control char" / "cmd-only on Linux") before persisting.

---

## 5. Goal 3 — Modal editing modes (vim / helix / kakoune)

### What is vim-specific vs reusable

**Vim-specific (must be generalized):**
- `VimMode` is a **closed enum** (`vim.rs:14-20`) and mode identity leaks as **literal strings** `"Vim"`/`"VimNormalMode"`/`"VimVisualMode"` in `keymap_context` (`view.rs:2388-2410`) and `id!("Vim")` binding predicates (`actions.rs:50-294`, `mod.rs:200-205,962-971`). A selection-first mode with different submodes cannot be expressed without editing all three.
- The view stores a **concrete `ModelHandle<VimModel>`** (`view.rs:271`, `mod.rs:1810`); the element stores a **concrete `Option<VimMode>`** (`element.rs:203`); cursor shape matches `VimMode` directly (`element.rs:1535-1539`). No abstraction seam.
- The grammar is **hardcoded verb-then-motion**: operator captured first as `PendingAction::Operation{operator, pending_operand}` (`vim.rs:242-257`), and `operation()` (`vim.rs:1981`) **fuses** "compute selection from motion" then "apply verb" in one step (`vim_handler.rs:144-429`). This is the *inverse* of Helix/Kakoune's select-then-act.
- Key→action mapping is **hardcoded match arms** (`handle_normal_nothing_pending`, `vim.rs:896-1053`), not a data table.
- Activation is **boolean** (`view.rs:1952`, `settings/editor.rs:202-210`).
- The editor-side `VimHandler` execution is **duplicated** across `CodeEditorView` (`vim_handler.rs:23`) and terminal `EditorView` (`mod.rs:1959`).

**Already reusable (the good news):**
- `VimFSA` is a **pure, UI/buffer-agnostic keystroke→event interpreter** (`vim.rs:37`, no buffer mutation), bridged by a **blanket `impl<T: VimHandler> VimSubscriber`** (`vim.rs:1849`) to a real `VimHandler` trait (`vim.rs:1945`). This 4-tier `FSA → VimEvent IR → blanket subscriber → handler` layering is exactly the shape a pluggable design needs.
- The **buffer algorithms** in `crates/vim` are generic over `T: TextBuffer + ?Sized` and reference no FSA/keymap state: text objects (`text_objects/word.rs:15` `vim_inner_word<T,C>`, plus paragraph/quote/block), word iterators (`word_iterator.rs:52`), matching brackets (`matching_brackets.rs:9`). *(Partial: `find_char.rs:28` is NOT generic — it operates on a concrete `&str` (which impls `TextBuffer`); and all of these take vim-namespaced value enums like `WordType`/`BracketChar`/`FindCharMotion`, so reuse pulls in vim's domain types even though it's independent of the keymap.)*
- The **dispatch seam is narrow**: only two touch points bind input to vim — the element's `Option<VimMode>` check (`element/mod.rs:726`, `element.rs:617`) and the keymap `"Vim"` context (`view.rs:2394`).

### Proposed pluggable editing-mode design

**Step A — `ModalEngine` trait + boxed/enum engine on the view.** Introduce, in `crates/vim` (or a new `crates/modal`):

```rust
trait ModalEngine {
    fn typed_character(&mut self, c: char, ctx) -> Option<EditorCommand>;
    fn keypress(&mut self, ks: &Keystroke, ctx) -> Option<EditorCommand>;
    fn state(&self) -> ModalState;      // active flag + submode + desired cursor shape
    fn interrupt(&mut self, ctx);
    fn force_insert_mode(&mut self, ctx);
}
```

`VimModel` already has `typed_character`/`keypress`/`state`/`interrupt`/`force_insert_mode` (`vim.rs:1804-1834`), so it implements this almost for free. Change the view field at `view.rs:271` / `mod.rs:1810` from `ModelHandle<VimModel>` to an enum `ModalEngineModel { Vim(VimModel), Helix(HelixModel), Kakoune(KakouneModel) }` (an enum avoids `dyn`-in-`ModelHandle` issues), selected at construction from the editing-mode setting (`view.rs:357-369`).

**Step B — mode-agnostic `EditorCommand` IR.** Extract a crate-level superset of `VimEventType` (`vim.rs:540`) that adds the two primitives a selection-first scheme needs: `ExtendSelection(Motion)` (a persistent, keep-selection motion) and `ApplyOperator(Operator)` (operand-less verb on the existing selection). Vim's existing events map 1:1; Helix/Kakoune emit `ExtendSelection` + `ApplyOperator`. Provide **one** blanket `impl<T: ModalEditExecutor> Subscriber` replacing `vim.rs:1849`.

**Step C — shared executor.** Rename/extend `VimHandler` (`vim.rs:1945`) into `ModalEditExecutor`, adding `extend_selection_by_motion(motion, count, ctx)` (a keep-selection variant of existing `navigate_*` — the model already supports a `keep_selection` flag, used at `vim_handler.rs:38-56`) and `apply_operator_to_selection(operator, ctx)` (generalize the existing `visual_operator`, `vim_handler.rs:507`). One executor impl then serves vim *and* helix; this also lets us collapse the duplicated execution across both editor views (`vim_handler.rs:23`, `mod.rs:1959`) toward a shared core.

**Step D — generalize the two seams.** Change the element field `vim_mode: Option<VimMode>` (`element.rs:203`, `element/mod.rs:127`) to `modal: Option<ModalCursorState>` (active flag + `CursorDisplayType`), keep the fork as `if self.modal.is_some()` but dispatch a generic `ModalUserTyped` action. In `keymap_context` (`view.rs:2388-2410`) insert a stable `"ModalEditing"` context plus a dynamic `format!("Modal:{engine}:{submode}")`, and migrate the structural non-char bindings (enter/tab/backspace/escape, `actions.rs:50-294`) to predicate on `id!("ModalEditing")` + a single `ModalKeystroke` action. Per-engine key meaning stays inside each FSA, since the bulk of keys flow through the single char path.

**Step E — enum setting.** Replace `vim_mode: bool` (`settings/editor.rs:202-210`) with `editing_mode: EditingMode { None, Vim, Helix, Kakoune }` (default `None`), toml `text_editing.modal_mode`. Keep `vim_mode_enabled()` (`editor.rs:285`) as a back-compat shim returning `editing_mode == Vim`. This mirrors existing enum settings in the same group (`CursorDisplayType` at `editor.rs:192`, `CodeEditorLineNumberMode` at `editor.rs:229`), so it's a well-trodden pattern; surface it as a dropdown in settings.

### How a selection-first mode maps differently

- **Vim (verb-then-motion):** FSA captures operator → operand → emits a single fused `Operation` (`vim.rs:242-257,1981`). Selection is *computed from the motion at apply time* and discarded.
- **Helix/Kakoune (select-then-act):** every motion emits `ExtendSelection(Motion)`, which the executor applies **persistently** (the selection survives between keystrokes — exactly `extend_selection_by_motion` with `keep_selection = true`). A subsequent verb emits `ApplyOperator(Operator)` that consumes the *current* selection (`apply_operator_to_selection`). The buffer/selection mechanics are ~90% shared with vim's existing `visual_operator` path; the difference is purely *ordering and persistence of selection*, which lives entirely in the FSA's grammar and is expressed through the two new IR commands — **no new buffer algorithm is required**. The text objects, word iterators, and bracket matcher (`text_objects/`, `word_iterator.rs:52`, `matching_brackets.rs:9`) are reused as-is; registers (`app/src/vim_registers.rs`) remain an app concern and generalize cleanly.

---

## 6. Cross-cutting risks, open questions, and dependencies

**Where the goals interact:**
- **Per-mode bindings need BOTH engine and UI work.** A pluggable modal scheme (Goal 3, Step D) registers bindings predicated on `Modal:{engine}:{submode}` contexts. But the settings UI's conflict detection is context-blind (Goal 2, G1) and overrides are name-keyed and context-blind (Goal 1, L3) — so vim-normal vs helix-normal bindings on the same key would all collide under today's model and all be clobbered by a single override. **The context-scoped override (R3) and context-aware conflict map (R6) are prerequisites** for per-mode keymaps to be editable.
- **Binding layers (R2) underpin both modal packs and clean user overrides.** Each mode is naturally a *layer*; user overrides are another. Building R2 once serves both Goal 1 and Goal 3.
- **The action catalog (R9) depends on engine introspection** (walking fixed + editable bindings) and feeds both the settings UI and the change-keybinding agent skill.
- **Platform-in-data-model (R5)** is independent but is a hard prerequisite for any cross-platform binding editor.

**Honest unknowns / things to verify before building:**
- **Magnitude of `FixedBinding` usage.** The research could NOT confirm that "a large fraction" of user-facing shortcuts are Fixed — the only `FixedBinding` sites observed are internal/transient (modal escape, lightbox nav, onboarding callouts). *Before promising "make everything remappable," audit how many user-visible shortcuts are actually Fixed* — the migration cost (and whether it's even needed) hinges on this.
- **`ModelHandle<dyn ModalEngine>` feasibility.** The research recommends an enum over `dyn` because `ModelHandle` is generic over a concrete type; this needs verification against the warpui `Entity`/`ModelHandle` machinery before committing to the API shape.
- **Trie correctness under context-dependent eligibility.** R4's trie must be rebuilt or filtered per active context set, and must preserve the existing `bindings()` precedence as a tiebreaker; the interaction with `Tracked<EditableBinding>` invalidation needs design.
- **Hot-reload reset semantics (R1).** Reverting a removed entry to its *default* requires a reliable "currently-applied custom names" set; today there is no such bookkeeping, and `update_custom_trigger(name, None)` is the only reset path (`keymap.rs:422-433`).
- **Helix/Kakoune grammar depth.** The select-then-act mapping is sketched at the IR level; real Helix has multi-selection and a richer command set whose fit onto a single `ExtendSelection`/`ApplyOperator` pair is unproven beyond the basic cases.

---

## 7. Phased roadmap

### Phase 1 — Quick wins, no schema/engine changes (low risk)
1. **Hot-reload `keybindings.yaml` (R1):** wire the existing config watcher (`native.rs:74-134`) to call a reload that resets-then-reapplies custom triggers. Add the "applied custom names" set.
2. **Search by action name + filter chips + import/export (R7):** extend `filter_bindings_including_keystroke` (`bindings.rs:650`) and add UI controls over existing `keyboard.rs` read/write.
3. **Chord capture (R8):** `unsaved_binding: Vec<Keystroke>`, push instead of overwrite, thread `Trigger::Keystrokes(vec)` through save.
4. **Validators on the edit path (R10):** expose a release-build `validate_trigger` and call it from `confirm_keystroke_editing`.
5. **Action catalog v1 (R9, partial):** startup pass emitting a `(name, description, group, context, default)` manifest from `editable_bindings()`; surface read-only in the UI and persist for the agent skill.

*Deliverable: a materially more usable existing UI, plus the introspection data later phases depend on. No backwards-incompat changes.*

### Phase 2 — Engine model changes (medium risk; enables real scoping)
1. **Binding layers + explicit precedence + `Unbound` state (R2):** tag bindings, resolve `bindings()` by `(layer, recency)`.
2. **`ContextPredicate` `FromStr` parser + `Cow`/interned context strings (R3a):** unblock data-driven contexts.
3. **Context-scoped user schema (R3b):** evolve `CustomKeybindings` to records `{name, trigger, context?, platform?}`; thread context through `set_custom_trigger`/`update_custom_trigger` so overrides match `name+context`.
4. **Context-aware conflict detection (R6):** re-key `ConflictMap` on `(Keystroke, context-group)`, name the colliding action, optional hard-conflict save gate.
5. **(Optional) trie + ambiguity policy (R4)** and **platform-in-data-model (R5)** as the foundation for a cross-platform editor.

*Deliverable: users can scope, disable, and reliably override bindings; conflict UI tells the truth. This is the prerequisite layer for modal packs.*

### Phase 3 — Pluggable modal editing (highest risk; depends on Phase 2 contexts)
1. **`ModalEngine` trait + enum engine field (Step A)** and **enum `EditingMode` setting (Step E):** replace the boolean gate; settings dropdown.
2. **Mode-agnostic `EditorCommand` IR + `ModalEditExecutor` (Steps B/C):** add `ExtendSelection`/`ApplyOperator`; collapse the duplicated `VimHandler` impls toward a shared executor.
3. **Generalize the two dispatch seams (Step D):** `Option<ModalCursorState>` element fork; `Modal:{engine}:{submode}` keymap contexts; `ModalKeystroke` structural bindings — all predicated via the Phase-2 context system.
4. **Ship Helix (select-then-act) as the proof:** a second FSA emitting the shared IR, reusing the generic `crates/vim` buffer algorithms (text objects, word iterators, bracket matcher) and registers; Kakoune follows the same template.

*Deliverable: vim/helix/kakoune coexist behind one setting, sharing one executor and one matcher, with per-mode bindings that the Phase-2 UI can scope and edit.*

**Sequencing rationale:** Phase 1 is independently shippable and de-risks the rest by producing the action catalog and proving the watcher pattern. Phase 3's per-mode bindings are *unusable* without Phase 2's context-scoped overrides and conflict detection (Section 6), so the engine model must land first. The deepest refactors (trie R4, platform R5, full modal pluggability) are deferred behind their cheaper prerequisites.