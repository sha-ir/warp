[← Back to index](./README.md)

## Axis 2 — Scope & context control

**End state:** a power user binds a key differently per context (terminal vs code editor vs modal submode) and the override hits only that scope.

> **Killer question:** When a user binds action `name` in context `C`, what target-identity relation selects WHICH existing same-name binding(s) the override modifies — exact structural `ContextPredicate` equality, subsumption/eval-implication, or a stable binding id — and does the engine MUTATE `custom_trigger` on that matched subset (today's `update_custom_trigger`, keymap.rs:422-433) or INJECT a new higher-precedence binding `{name, trigger, C}`? Critically: do the per-context behaviors users most want to rebind (e.g. enter/backspace-in-Vim) even live in the editable path, given those are `FixedBinding`s (editor/view/mod.rs:197-209; code/editor/view/actions.rs:51-60) that `update_custom_trigger` never touches — meaning Axis 2's flagship cases may be unreachable without Axis 3's Fixed-remappable work?

### Scope/requirements

**A2-Q1. What is the stable, documented context vocabulary users may reference in predicates, versus internal flags they must NOT depend on? Flags today are a mix of auto-inserted `ui_name()` (core/view/mod.rs:114-117) plus ad-hoc literals (`Vim`, `VimNormalMode`, `VimVisualMode`, `Workspace_SingleTab`, `IMEOpen`, `Input`, `VoltronActive`, `NON_EDITABLE_KEYMAP_CONTEXT`, ...) with inconsistent naming and lifetimes.**

- _Why it matters:_ Config-authored predicates are only useful if referenced flags are stable. Many current flags are transient UI state, and `ui_name()` is an internal Rust identifier. Without a curated, versioned vocabulary, every parsed predicate is coupled to refactor-volatile internal strings that change on routine refactors.
- _How to answer:_ Inventory all `context.set.insert(...)`/`map.insert(...)` literals and the `ui_name()` auto-flag. Partition into (supported durable scopes | transient state | internal). Decide the supported subset and a stable naming scheme; feed it into the action/context catalog (Axis 5 R9) for discoverability/validation. Note the Vim flags are gated by the `vim_mode_enabled` setting (view.rs:2395-2401, editor/view/mod.rs:8693-8695), so their presence is conditional.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the assumption that 'contexts are expressible from config' (L6) implies they're usable. Exposing the raw internal flag soup as the user API creates an unversioned coupling to UI internals that breaks user configs on routine refactors.

**A2-Q2. How does the `platform?` field in the proposed `{name, trigger, context?, platform?}` schema (report R3) compose with `context?`, and with the existing per-platform binding split (`PerPlatformKeystroke`, keymap.rs:488; `with_mac_key_binding` vs default, e.g. editor/view/mod.rs:785-788)? Is a scoped override addressed by (name × context) or (name × context × platform), and does context-scoped override interact with the cross-platform foundation (R5/L7)?** _(added-by-critic)_

- _Why it matters:_ Today bindings already diverge by platform (mac vs linux/windows keystrokes registered side-by-side). If a context-scoped override doesn't also carry/disambiguate platform, the same clobber bug reappears across the platform axis (a linux override silently rewrites the mac binding or vice versa). The schema fork (Q2) must decide the full key tuple up front; retrofitting platform later re-opens the migration.
- _How to answer:_ Inspect `PerPlatformKeystroke` (keymap.rs:488+) and how `with_mac_key_binding`/default keystrokes register two bindings. Decide the override key tuple. Check whether the current single-build editor even surfaces non-host-platform bindings (R5/L7 says no). Declare whether platform is in-scope for Axis 2 or deferred to the cross-platform foundation, and how the deferral avoids a second schema migration.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Attacks the assumption that context is the only new dimension. Platform is an existing, orthogonal scoping axis already in the data; ignoring it in the override key re-introduces the clobber across platforms.

### Design decision

**A2-Q3. Does the user file schema stay a flat `HashMap<String, PersistedTrigger>` (keyboard.rs:169) or become a list of `{name, trigger, context?, platform?}` records (report R3, lines 142/256), given one name already maps to N bindings (`editable_bindings_by_name: HashMap<&str, Vec<usize>>`, keymap.rs:30) and a map key structurally forbids two scoped overrides of the same name?** _(sharpened)_

- _Why it matters:_ A name-keyed map cannot hold two different overrides for the same action in two contexts (e.g. an action rebound differently in `VimNormalMode` vs default) — the second clobbers the first at the serde layer before any engine logic runs. This is the foundational schema fork the whole axis hangs on, and it dictates the migration story for existing flat files.
- _How to answer:_ Decide between (a) keep flat map + a separate per-context override section, or (b) move to a record list. Check the serde round-trip and `PersistedTrigger`/`UserDefinedKeybinding` TryFrom (keyboard.rs:167-213), which today only yields Keystrokes/Removed. Prototype both YAML shapes against real same-name multi-context cases. Coordinate with Q18 (platform field) and Q20 (predicate serialization) since both ride this schema.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the assumption that 'name -> trigger' is a sufficient key. It isn't the moment scoping exists — a map silently de-dupes the very thing this axis is meant to enable.

**A2-Q4. What identifies WHICH same-name binding an override targets? `update_custom_trigger` (keymap.rs:422-433) filters by `b.name == name` only. When we add a context, do we match the override's parsed predicate against each binding's `context_predicate` by (a) exact structural `ContextPredicate` equality, (b) subsumption (override-ctx ⊆ binding-ctx via eval-implication), or (c) a stable binding id, and what is the defined behavior when ZERO or MULTIPLE bindings match (no-op? error? apply-to-all)?** _(sharpened)_

- _Why it matters:_ This is the literal mechanism of 'override hits only that scope.' Exact-equality forces users to reproduce the binding's internal predicate verbatim (brittle; exposes internal predicates like `text_entry & id!("VimNormalMode")`); subsumption needs a predicate solver and risks over-applying; id-targeting needs a stable id surfaced in the UI/catalog (Axis 5 R9). The choice ripples into schema, UI editor, and catalog. There is no per-binding handle in the code today for a config to reference.
- _How to answer:_ Spike a modified `update_custom_trigger` taking `Option<ContextPredicate>` and try each relation against a synthetic keymap with same-name bindings under `id!("Vim")` vs `!id!("Vim")`. Observe zero/multi-match behavior. Note it must write to BOTH `editable_bindings` and `editable_custom_action_bindings` (keymap.rs:423-432). Use REAL editable examples (e.g. text_entry-scoped editor actions) — but note Q16: the most-wanted forks are Fixed, not editable.
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Attacks the hand-wave 'just add context to the override.' There is no obvious target relation — equality, subsumption, and id-targeting give materially different UX and failure modes, and the code has no per-binding handle a config could name.

**A2-Q5. Does a context-scoped override MUTATE `custom_trigger` in place on the matched binding(s) (today's `as_lens` mechanism, keymap.rs:741-759), or INJECT a new higher-precedence binding `{name, trigger, predicate}` — and is Axis 3's binding-layer/precedence model (R2) a HARD PREREQUISITE for the inject path, such that Axis 2 cannot ship standalone in Phase 2 if new scopes are in scope?** _(sharpened)_

- _Why it matters:_ Mutate-in-place reuses the existing `custom_trigger`/`original_trigger` machinery and the live-apply path but can only override scopes that already exist as registered bindings; it cannot add a brand-new scope. Inject-new can express genuinely new scopes but needs explicit precedence resolution, which `bindings()` (keymap.rs:454-464) lacks (it's fixed-vs-editable + LIFO only). This directly sequences Axis 2 against Axis 3 and decides whether Axis 2 is a standalone Phase-2 increment.
- _How to answer:_ Enumerate the leaf user stories: 'rebind an EXISTING scoped binding' (mutate suffices) vs 'add a NEW scoped binding for an action with no binding in that scope' (inject required). If any leaf needs inject, declare R2 a hard prerequisite and mark the dependency edge in the spine (end-goals doc lines 116-133). Review `bindings()` ordering (keymap.rs:441-464).
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Attacks the assumption that context-scoped override is a self-contained Axis-2 change. If new scopes (not just overrides of existing bindings) are in scope, it secretly depends on the Axis-3 layer model and can't ship standalone as the roadmap implies.

**A2-Q6. What is the exact GRAMMAR for the `FromStr for ContextPredicate` parser — operator precedence and associativity of `! & | == !=`, parenthesization, whitespace handling, and atom token rules — and must it round-trip losslessly with the Rust macro-built predicates (`id!`/`eq!`/`ne!` + `Not`/`BitAnd`/`BitOr` overloads, context.rs:20-87)?** _(added-by-critic)_

- _Why it matters:_ Q6 settles the parser's output TYPE but not its language. Without defined precedence, `a & b | c` and `!a & b` are ambiguous, and different precedence choices change which scope a predicate selects. The grammar also bounds what the UI/catalog can render and validate. This is a concrete, decision-forcing spec item the draft entirely omits.
- _How to answer:_ Define a grammar (e.g. `!` binds tightest, then `&`, then `|`, with parentheses; `==`/`!=` as `key == value` atoms) and verify it reproduces the structure the macros/operator-overloads build (context.rs:53-84). Write parse + reparse unit tests over representative real predicates (e.g. `CodeEditorView & !IMEOpen & Vim`). Decide whether to mirror an existing engine's grammar (e.g. Zed-style context expressions) for familiarity.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks 'add a FromStr parser' as if the language were obvious. Precedence/associativity are load-bearing: the same token string can select different scopes under different grammars, and an undefined grammar blocks both the parser and the round-trip serializer.

### Code fact to verify

**A2-Q7. Do config-authored predicates evaluate against a SINGLE per-view Context or a merged chain context? `contexts_from_responder_chain` (crates/warpui_core/src/core/app.rs:1839-1864) builds a `Vec<Context>` with NO merge loop (`Context::extend` exists at context.rs:90-97 but is unused here), and `dispatch_keystroke`/`push_keystroke` (core/app.rs:2005-2041; matcher.rs:307-346) eval each predicate against ONE per-view `ctx`. Given the architecture report (line 32) wrongly claims context is 'merged up the responder chain', do we (a) keep per-view eval and constrain the documented vocabulary so cross-level ANDs are forbidden, or (b) build a merged-context variant for predicate eval?** _(sharpened)_

- _Why it matters:_ Determines what a user-authored predicate can express. Under per-view eval, a predicate ANDing flags owned by different chain levels (e.g. `CodeEditorView & Workspace_SingleTab`, where `Workspace_*` is set by an ancestor view) silently NEVER matches because no single view's Context holds both. The schema/parser MUST document this eval boundary or users will write predicates that never fire — and the report's own description is misleading on this point.
- _How to answer:_ Confirmed: core/app.rs:1839-1864 has no extend/merge; matcher.rs:324-377 evals against a single `ctx`. Decide eval boundary: per-view (constrain vocabulary, document that only intra-view flag combinations match) vs merged (add an opt-in merge for predicate eval and audit the precedence implications, since a merged ctx would make ancestor flags visible to leaf bindings).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks both the naive 'any flags can be ANDed in one predicate' assumption AND the architecture report's incorrect 'merged up the responder chain' claim. Reality: predicates see exactly one view's flags at a time.

**A2-Q8. How do config-parsed predicate atoms (runtime `String`s) evaluate against a `Context` whose `set`/`map` are `HashSet/HashMap<&'static str>` and a `ContextPredicate` whose variants hold `&'static str` (context.rs:3-18)? Do we (a) intern/leak strings to `&'static str`, (b) change `Context`/`ContextPredicate` to `Cow<'static, str>`/interned IDs (report R3a), or (c) eval via a side lookup table?**

- _Why it matters:_ This is the concrete L6/R3a blocker. A `FromStr for ContextPredicate` produces `String`s that cannot inhabit the current `&'static str` variants, and `eval` (context.rs:100-120) does `&'static str` comparisons. Whichever fix is chosen ripples through ~265 imperative registration sites and every `keymap_context` impl. Leaking is simplest but unbounded-memory under hot-reload; `Cow`/interning is a wider refactor.
- _How to answer:_ Inspect `ContextPredicate` variants and `eval` (context.rs:9-18,100-120) and `Context` (context.rs:3-7). Estimate blast radius via grep of `.set.insert("...")`/`map.insert` literals and `id!`/`eq!` call sites. Prototype a `FromStr` producing `Cow`-backed atoms vs a `Box::leak` interner with a dedupe cache (bounded for hot-reload), and measure compile/churn.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'just add a FromStr parser.' The parser output type collides with the `&'static str` storage contract the whole engine and 265 call sites rely on — the parser is the easy 10%.

### Edge case/failure mode

**A2-Q9. Do we keep the asymmetric absent-key semantics for config-authored predicates, where `ContextPredicate::NotEqual` returns TRUE when the key is absent (`unwrap_or(true)`, context.rs:113) and `Not(Identifier)` returns true when absent, while `Equal`/`Identifier` return false when absent (context.rs:103-108)? So a config predicate like `mode != "insert"` MATCHES in every view that has no `mode` key at all?**

- _Why it matters:_ Hand-written `!=`/`!` predicates over-match in views that don't define the key, producing bindings that fire in unexpected scopes. This is a silent correctness footgun unique to config authors. The policy (treat absent as not-equal vs require presence) must be decided before the parser ships.
- _How to answer:_ Read `eval` (context.rs:100-120). Decide whether config `!=`/`!` means 'present and different' (require key) or keeps the current 'absent counts as different.' Add targeted unit tests in context_tests.rs for absent-key `!=`/`!` cases (note: context_tests.rs currently has ~1 test fn — coverage is near-zero). Consider a distinct parser-level operator or a presence guard.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that `!=` is the obvious negation of `==`. The existing eval is asymmetric on missing keys, so config `!=`/`!` predicates leak into scopes the author never intended.

**A2-Q10. What happens when a config predicate references an UNKNOWN context atom (typo, or a flag removed by a refactor)? With current eval, an unknown `Identifier`/`Equal` silently never matches and an unknown `NotEqual`/`Not` silently always matches. Do we validate atoms at parse time against a known-flag registry and surface an error, warn-and-keep, or accept silently?**

- _Why it matters:_ Silent failure is the worst outcome for a power-user config: the override either does nothing or applies everywhere, with no feedback, and the direction depends on the operator. Validation requires the curated vocabulary (Q7) and the action/context catalog (Axis 5 R9), forcing a dependency decision.
- _How to answer:_ Decide a validation policy: hard error vs warn-and-keep vs accept. If validating, the `FromStr` parser needs access to the set of known atoms — wire it to the R9 catalog. Add a load-time diagnostic mirroring `load_custom_keybindings`'s existing `log::warn!` on unparseable triggers (keyboard.rs:49-53).
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the assumption that a parser only needs to reject syntax errors. A syntactically valid predicate over a misspelled flag is the common real failure, and today it fails silently in opposite directions depending on the operator.

**A2-Q11. How does context-scoped REMOVAL work, given today's `Removed` maps to `set_custom_trigger(name, Trigger::Empty)` (keyboard.rs:44) which is name-wide and overloads `Trigger::Empty` ('cannot actually be matched', keymap.rs:48, with no real `Unbound`)? Can a user remove a binding in context X while keeping it in context Y, and does that pull in the Axis-3 `Unbound` work (L4/R2)?**

- _Why it matters:_ Per-scope removal is part of 'binds a key differently per context.' But removal funnels through the same name-only path and an overloaded empty trigger, so a scoped removal would either clobber all scopes (today's bug) or require a context-tagged empty/unbound state that doesn't exist — pulling in Axis 3.
- _How to answer:_ Trace `UserDefinedKeybinding::Removed` -> `set_custom_trigger(name, Trigger::Empty)` (keyboard.rs:42-45) -> `update_custom_trigger` (keymap.rs:422). Decide whether scoped removal needs a context-scoped Empty or a real `Unbound` (R2). Add a same-name remove-in-one-context-keep-in-another test case.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that removal is just another trigger value. It's an overloaded `Trigger::Empty` applied name-wide, so scoped removal silently inherits the clobber-all and no-true-unbind problems.

**A2-Q12. How does a context-scoped CHORD override behave when the per-view context changes BETWEEN keystrokes of the chord? `push_keystroke` caches `pending.context` and clears the pending sequence if `pending_ctx != ctx` (matcher.rs:313-321) and only re-checks `context_predicate.eval(ctx)` against the CURRENT ctx (matcher.rs:327). If a chord's first keystroke triggers a mode switch (e.g. enters VimNormalMode) so the second keystroke sees a different Context, does the scoped chord still complete, silently reset, or mis-fire?** _(added-by-critic)_

- _Why it matters:_ Modal submodes are an explicit Axis-2 leaf goal, and modal keystrokes routinely change context mid-sequence. A scoped chord predicate evaluated only against the latest per-view ctx, combined with the pending-clear-on-context-change behavior, can make scoped chords either un-completable or fire in the wrong scope. This composes with the prefix-shadowing/ambiguity problem (Axis 3 L5) and must be specified.
- _How to answer:_ Trace `push_keystroke` (matcher.rs:307-346): note `pending.context` caching, the `pending_ctx != ctx` clear, and `keystrokes.starts_with(&pending.keystrokes) && eval(ctx)`. Construct a unit test where the context mutates between keystroke 1 and 2 of a 2-key chord under a scoped predicate; assert completion/reset behavior. Decide the intended policy (evaluate against entry-context vs current-context).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that chords and contexts compose cleanly. The matcher caches one context per pending sequence and re-evals only the latest ctx, so a mode-switching first keystroke can strand or misroute a scoped chord.

### Dependency/sequencing

**A2-Q13. Of the per-context same-name bindings users actually want to rebind, how many are `FixedBinding`s (unremappable, L9) versus `EditableBinding`s? The flagship forks — enter, backspace, numpadenter in Vim vs not — are FixedBindings (editor/view/mod.rs:197-209; code/editor/view/actions.rs:51-60), and `update_custom_trigger` (keymap.rs:422-433) only ever touches `editable_bindings`/`editable_custom_action_bindings`, never `fixed_bindings`. Does Axis 2 deliver any user-visible value without Axis 3's Fixed-remappable work?** _(added-by-critic)_

- _Why it matters:_ If the most-requested per-context overrides target Fixed bindings, then context-scoped EDITABLE override (the whole of Axis 2's mechanism) cannot reach them — Axis 2 ships but the headline use case stays broken, and the real prerequisite is Axis 3 (L9 audit + Fixed remappability). This re-sequences the roadmap and contradicts the report's L3 framing, which implicitly assumes the clobbered bindings are editable.
- _How to answer:_ Audit: grep `FixedBinding::new` vs `EditableBinding::new` for same-name multi-context pairs (start with Vim/non-Vim forks in editor/view/mod.rs and code/editor/view/actions.rs). Quantify how many user-facing shortcuts with distinct per-context behavior are Fixed. Cross-reference the report's open question on FixedBinding magnitude (end-goals doc line 145; report 'Magnitude of FixedBinding usage'). Decide whether the L9 audit is a hard gate for Axis 2.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the unstated assumption that the same-name multi-context bindings this axis targets are editable. The canonical examples are Fixed, which update_custom_trigger cannot touch at all — so Axis 2's mechanism may not reach its own motivating use cases.

### Migration/back-compat

**A2-Q14. What is the back-compat contract for a context-LESS entry in an existing `keybindings.yaml`? Today a flat `name: trigger` entry clobbers EVERY same-name binding via name-only `update_custom_trigger` (keymap.rs:422). After the schema change, does a context-less entry preserve clobber-all semantics, or change meaning to 'default scope only'?**

- _Why it matters:_ Existing user files (and exported colleague configs) are flat name->string with a `"none"` removal sentinel (keyboard.rs:15,189-213). If context-less now means 'default scope only' instead of 'all scopes,' every existing customization silently changes behavior on upgrade. The migration policy must be explicit and likely needs a deserializer shim.
- _How to answer:_ Decide: context-less = all-scopes (back-compat) vs context-less = a designated default scope. Verify `CustomKeybindings`/`TryFrom<PersistedTrigger>` (keyboard.rs:167-213) and `load_custom_keybindings` (keyboard.rs:37-57) can deserialize old + new shapes simultaneously. Define an auto-migration step if semantics change.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that adding an optional `context` field is non-breaking. The DEFAULT meaning of 'no context' is a behavior change for every file already on disk.

**A2-Q15. How is a `ContextPredicate` SERIALIZED back to text for the write path? `write_custom_keybinding` produces a `PersistedTrigger(String)` (keyboard.rs:64-, 176-187) and there is NO `Display`/`ToString` impl for `ContextPredicate` today (context.rs has only `FromStr`-shaped macros, no formatter). In-app edits must write the scoped predicate to file — what canonical text form, and does FromStr(Display(p)) == p hold for round-trip safety?** _(added-by-critic)_

- _Why it matters:_ The North Star requires file and in-app edits not to clobber each other (round-trip safe). Adding a read-side parser without a matching write-side serializer means in-app scoped edits either can't be persisted or get persisted in a form that doesn't reparse, silently dropping or corrupting overrides on the next load. The serializer must agree with the Q19 grammar.
- _How to answer:_ Confirm no `Display for ContextPredicate` exists. Design a canonical serialization (likely the Q19 grammar's minimal-parenthesized form) and add a `FromStr ∘ Display == identity` proptest. Wire it through `from_editable_lens` (util/bindings.rs:762) write path and `PersistedTrigger`. Decide how to serialize predicates that originated from Rust macros but were never authored as text (e.g. internal flag names that aren't in the supported vocabulary, Q7).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that 'parse predicates from text' is the whole job. Write-back has no Display today; without a round-tripping serializer, in-app scoped edits can't be saved truthfully, breaking the file-is-source-of-truth goal.

**A2-Q16. Does the revert/reset key become `name+context` (from today's name-only), and how does a scoped override interact with `Tracked<EditableBinding>` live-apply notifications (keymap.rs:27, report line 24) and Axis-1 hot-reload reset semantics (the 'currently-applied custom names' set, end-goals doc line 152)? When hot-reload re-applies the whole file, how is a previously-applied scoped override on a SUBSET of same-name bindings reverted without touching its siblings?** _(added-by-critic)_

- _Why it matters:_ Today reset/revert is keyed by `name` and clobbers all same-name bindings; that's the exact bug Axis 2 kills. But the Axis-1 hot-reload 'applied custom names' set is also name-keyed, so on reload it would either fail to revert a scoped override or revert all siblings. The reset key must become name+context (or binding-id) in lockstep with the override key, and the Tracked notification must fire for exactly the mutated subset so the UI re-renders correctly.
- _How to answer:_ Map the revert path: how `set_custom_trigger`(..., None) / removal restores defaults, and how Axis-1's reset set is keyed. Decide the reset granularity (name+context vs stable id) consistent with Q3. Verify `Tracked` mutation notifications fire per-binding when only a subset is mutated (keymap.rs:410-417, 423-432). Add a hot-reload test: apply a scoped override, remove it from the file, reload, assert only that scope reverts.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that scoping only affects the apply path. The REVERT path and Axis-1 hot-reload reset are also name-keyed; if they aren't upgraded to name+context in lockstep, reverting a scoped override silently clobbers or strands its siblings.

### Testing/validation

**A2-Q17. What test harness proves a context-scoped override hits ONLY its scope, given context_tests.rs has ~1 test fn and the keymap tests don't exercise same-name multi-context bindings? Unit test directly on `Matcher::push_keystroke`/`update_custom_trigger` with synthetic contexts, or an integration test across real terminal vs code-editor views?**

- _Why it matters:_ The core claim of the axis ('override hits only that scope') is exactly what today's name-only override gets wrong, so it must be locked by tests. The existing keymap/context tests have essentially no coverage of same-name multi-context bindings, so the harness gap is real and must be designed alongside the feature.
- _How to answer:_ Build a unit test in the keymap crate registering two same-name editable bindings under `id!("Vim")` and `!id!("Vim")`, apply a scoped override, and assert only the scoped one changes (checking BOTH `editable_bindings` and `editable_custom_action_bindings`). Add an integration test (crates/integration Builder/TestStep) for terminal-vs-code-editor end-to-end. Reference real forks at editor/view/mod.rs:197-209 (Fixed) and editor actions (Editable).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that existing keymap tests cover this. They don't exercise same-name-multi-context at all, so 'it passes tests' would be meaningless without a new harness.

### UX/surface behavior

**A2-Q18. Does the settings UI gain a per-context editor (context picker / predicate editor) for a binding, or is per-context scoping config-file-only with the UI deferred? Today `CommandBinding` (app/src/util/bindings.rs:531) has no editable context field, and rows are deduped by `a.name == b.name && a.description == b.description` (settings_view/keybindings.rs), collapsing distinct-context same-name bindings into one row.**

- _Why it matters:_ Defines the axis scope boundary and the UI's relationship to the file. If the UI stays name-keyed while the file gains contexts, the two surfaces diverge (violating the North Star 'what the UI shows is the truth'), and the dedup means scoped bindings are currently invisible in the editor — even displaying them is non-trivial, and saving via the UI would re-clobber scoped overrides.
- _How to answer:_ Decide the cut: file-only (UI deferred to an Axis-5 follow-up) vs UI parity. If parity, design how `CommandBinding`/`from_editable_lens` (util/bindings.rs:762) carries and renders the predicate, and change name+desc dedup to name+context dedup. Cross-reference context-aware conflict work (R6).
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks the assumption that engine scoping alone satisfies the goal. Without UI changes, the editor still presents one row per name and will overwrite scoped overrides, re-introducing the clobber the axis set out to kill.

### Performance/scale

**A2-Q19. What is the current registered binding count n, and at what override count does the linear matcher (`for binding in self.keymap.bindings()` with `context_predicate.eval(ctx)`, matcher.rs:324-327, run once per responder-chain entry, core/app.rs:2014) exceed the per-keystroke frame budget — i.e. is there a concrete binding-count threshold above which Axis 2 must pull R4's trie forward, and does that threshold change under the inject-new model (Q4)?** _(sharpened)_

- _Why it matters:_ If scoped overrides are injected bindings (Q4=inject), n grows by user-overrides × contexts, and `eval` runs O(n × chain-depth) per keystroke in the hot input path. We need current n and a budget to decide whether Axis 2 stays O(n) or co-requires R4. Mutate-in-place (Q4=mutate) keeps n constant, so this question's answer depends on Q4.
- _How to answer:_ Count registered editable + fixed bindings at runtime (instrument `register_*_bindings`; ~273 call sites). Microbenchmark `push_keystroke` against a keymap with +500 synthetic scoped bindings at realistic responder-chain depth; compare to frame budget. Decide trie-now vs trie-later as a function of Q4's outcome.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that adding scoped overrides is free. The matcher is O(n) per keystroke per chain entry with full predicate eval; a power user's inject-style scoped config could materially grow n in the hot path.

<details><summary>Already settled by the report/code — pruned as non-questions (1)</summary>

- ~~A2-Q11 — Can context-scoped overrides ship by mutating per-binding custom_trigger WITHOUT the Axis 3 binding-layer/precedence model (R2), or do they require it?~~ — Duplicative of A2-Q4, which already asks the mutate-vs-inject decision AND explicitly 'does the latter require the Axis 3 binding-layer/precedence model (R2) to exist first?'. The standalone-shippability/sequencing decision Q11 wanted is now folded into a sharpened Q4 (and the unbind-driven dependency is covered by Q15). Keeping both produced two questions resolving the same dependency edge.

</details>

---

