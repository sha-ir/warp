[← Back to index](./README.md)

## Axis 3 — Layering, precedence & unbinding

**End state:** bindings resolve through explicit layers (default < user < mode-pack), and a user can truly disable a default, not just shadow it.

> **Killer question:** FixedBinding::new ALWAYS produces a Trigger::Keystrokes (keymap.rs:511-525), and the code editor registers its entire core navigation/editing set as Fixed under user-reachable contexts — up/down/left/right→Move* (app/src/code/editor/view/actions.rs:131-146), home/end, enter/tab/backspace/delete with Vim forks (:51-176), shift-arrows — all predicated on id!(\"CodeEditorView\"). So of the 397 FixedBinding::new sites, how many sit in a context an end user would plausibly want to rebind versus genuinely internal/transient (modal-escape, onboarding callouts, lightbox nav)? This single classification decides whether Axis 3's 'fixed bindings become auditable/remappable' leaf is a contained Unbound+precedence refactor or a ~400-site identity-and-migration project — and it empirically refutes the report's L9/§6 claim (which the end-goals doc gates the whole leaf on) that Fixed is 'reserved for internal/transient.'

### Scope/requirements

**A3-Q1. Of the 397 FixedBinding::new sites (all of which are keystroke triggers — keymap.rs:525), how many sit in a user-reachable view context a user would plausibly rebind (code-editor up/down/left/right/enter/tab/backspace/delete, actions.rs:51-176) versus genuinely internal/transient (modal-escape, onboarding callouts, lightbox nav), and which subset is in-scope for 'remappable' in this axis?** _(sharpened)_

- _Why it matters:_ Determines whether Axis 3 is a contained precedence/Unbound change or a ~400-site fixed→editable identity migration. The report's L9/§6 claim ('Fixed reserved for internal/transient') is empirically false — the code editor's entire core nav/edit set is Fixed under id!("CodeEditorView") — so the migration cost is unknown and must be measured before promising 'remappable'.
- _How to answer:_ Script-classify all FixedBinding::new sites by (a) context predicate user-reachability (real view like CodeEditorView/EditorView/notebooks vs modal/onboarding/lightbox), (b) whether an EditableBinding of the same key already coexists in that context. NOTE the trigger-kind axis is moot (all ::new are Trigger::Keystrokes, keymap.rs:525). Produce a tagged table: remappable-candidate / leave-as-fixed, with per-file counts (top files: editor/view/mod.rs:49, terminal/view/init.rs:38, code/editor/view/actions.rs:38).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the report's assumption that user-facing shortcuts are all EditableBinding; the live code shows core navigation/editing keys are Fixed.

**A3-Q2. Does Axis 3 implement only {default, user} layers now with a reserved-empty mode-pack slot, or must the layer enum + resolution be proven end-to-end with at least one real mode-pack (vim) before it's 'done'?**

- _Why it matters:_ End-goal names default < user < mode-pack, but mode-packs are Phase 3 / Axis 4. Building a 2-layer system that can't actually host a mode-pack risks a second refactor; demanding a full mode-pack now over-scopes Phase 2. The done-ness boundary must be explicit.
- _How to answer:_ Cross-team decision with the Axis 4 owner: define the minimal mode-pack contract (how vim's contextual bindings register as a layer — today via id!("Vim") forks at actions.rs:51-60) and require Axis 3 to validate resolution with a stub or real vim layer rather than a hypothetical one.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Attacks designing layers for two layers when the requirement is N layers with mode-packs that don't exist yet.

### Design decision

**A3-Q3. How do fixed bindings acquire a stable, portable identity for audit/override given FixedBinding has no name field (keymap.rs:277-286), as_lens hardcodes name=Default (keymap.rs:633), and BindingId is an unstable per-run atomic counter (keymap.rs:264-272)?** _(sharpened)_

- _Why it matters:_ A user file and the catalog can only reference a binding by a stable key; fixed bindings have none and BindingId changes every launch. The design must pick: add a &'static str name at every Fixed site, promote them to EditableBinding, or derive a stable id (hash of action TypeId + context predicate). This choice dictates the data model and the migration surface across ~265 register sites.
- _How to answer:_ Decide among {add name, promote to editable, derive synthetic id}. Test feasibility of a derived id by checking whether (action TypeId + serialized context predicate) is unique per fixed binding — the fork at actions.rs:51-60 (enter→Enter under !Vim vs enter→VimEnter under Vim) gives distinct action+context, but grep for same-action+same-context duplicates (e.g. shift-backspace at actions.rs:91-100) that would collide a synthetic id.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'just expose fixed bindings in the UI' — there is literally no stable handle to key an override on, and BindingId is non-deterministic across runs.

**A3-Q4. Should a 'layer' be a tag field on each binding in the existing flat Vec resolved by a (layer, recency) sort, or physically separate per-layer collections composed at query time in bindings() (keymap.rs:454-464) — and how does either reconcile with the fact that user overrides today are an in-place custom_trigger mutation (keymap.rs:300,422-433), not a layer at all?** _(sharpened)_

- _Why it matters:_ Central data-structure decision for the whole axis. It determines how today's in-place override becomes a real 'user layer', how mode-packs slot in, and how the matcher iterates. A wrong choice forces a second refactor when Axis 4 mode-packs land.
- _How to answer:_ Prototype both against Keymap (keymap.rs:24-38): (a) add layer: enum + stable sort key and sort in bindings(); (b) hold Vec-per-layer and chain() in precedence order. Account for the parallel shadow collections fixed_custom_action_bindings/editable_custom_action_bindings (keymap.rs:396,411) that must stay consistent (see Q17). Evaluate against O(n) resolution and Tracked invalidation (Q11).
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Attacks 'just add a priority number' — overrides today aren't a layer, they mutate the default binding in place, so 'layer' must be invented, not tagged.

**A3-Q5. What is the precedence truth table for a user-layer Unbind interacting with lower (default) and higher (mode-pack) layers on the same (key, context): does Unbind disable only the same-name binding, or all bindings of that key+context, and can a higher mode-pack layer re-bind an unbound key?**

- _Why it matters:_ This is the core semantic the axis exists to deliver ('truly disable a default'). Without an explicit truth table, the matcher's first-match-wins (matcher.rs:324-338) gives ad-hoc results, and 'default < user < mode-pack' is undefined when user says Unbind but a mode-pack binds the same key.
- _How to answer:_ Author the resolution matrix for the 8 combinations of {default-bind, user-bind/unbind, mode-pack-bind} x (same-name vs same-key). Decide whether Unbind is key-scoped (a 'block') or name-scoped (a 'remove'). Validate against the duplicate-fork case at actions.rs:51-60 where one key maps to two actions under opposing predicates.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks 'unbind is obvious' — it conflates name-removal with key-disable, and the layer interaction with mode-packs is genuinely ambiguous.

### Code fact to verify

**A3-Q6. Is binding registration order deterministic and stable across releases/platforms, given precedence falls back to 'recency' = registration order produced by ~265 register_* calls fired during view init across 109 files, and given editable_bindings_by_name resolves ties by first-enabled (keymap.rs:379-385)?** _(sharpened)_

- _Why it matters:_ R2 makes (layer, recency) the user-visible precedence rule. If registration order is a function of nondeterministic view-init timing, 'recency' silently changes which binding wins across builds — the opposite of the axis goal ('trust the UI shows the truth').
- _How to answer:_ Trace the register_fixed_bindings/register_editable_bindings call chain from app startup (core/app.rs:1619-1639) through view setup; determine if order is fixed by a deterministic init sequence or depends on lazy view creation/responder chain. Check what happens when two views register the same name (editable_bindings_by_name: HashMap<&str, Vec<usize>>, keymap.rs:30) and which wins via get_binding_by_name (:379-385, first enabled).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks treating 'recency' as a sound precedence axis when it may be an accident of initialization timing.

**A3-Q7. If user overrides move from in-place custom_trigger mutation (keymap.rs:300,422-433) to a separate layer, what drives the live re-render that Tracked<EditableBinding> provides today — keep per-binding Tracked, or move to a layer-level revision counter?**

- _Why it matters:_ Live-apply of in-app edits is the one thing that already works (report §2c). It relies on Tracked's DerefMut→track_update (tracked.rs:50-54): update_custom_trigger mutates each binding through `editable_bindings.iter_mut()` over Tracked values (keymap.rs:430-432), firing invalidation. A layering refactor storing overrides elsewhere can silently break live-apply and the settings list.
- _How to answer:_ Read Tracked DerefMut (tracked.rs:50-54) and where the settings UI subscribes (settings_view/keybindings.rs on_page_selected, :748-784). Verify what notifies on set_custom_trigger (matcher.rs:137-141→keymap.rs:422-433). Decide tracking granularity for layers and prove the settings list still updates on override.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'layers are just data' — they sit under an autotracking system whose invalidation must be preserved or live edits stop applying.

**A3-Q8. Does the layer refactor unify or shadow the parallel custom-action collections fixed_custom_action_bindings and editable_custom_action_bindings (keymap.rs:396,411), which are maintained alongside the main vecs and updated in lockstep by update_custom_trigger (keymap.rs:422-433) and walked separately via custom_action_bindings() (keymap.rs:474)?** _(added-by-critic)_

- _Why it matters:_ Q3's 'tag a layer field on the flat Vec' ignores that the keymap already keeps duplicate shadow vecs for Custom-trigger bindings. A layer model that tags only the primary vec will desync these shadows (used by default_binding_for_custom_action, matcher.rs:229-243), reintroducing the dual-maintenance bug class. The data-structure decision must account for them.
- _How to answer:_ Map every place the four collections (fixed_bindings, editable_bindings, fixed_custom_action_bindings, editable_custom_action_bindings) are read/written. Decide whether layers replace the shadow vecs with a single layered store + a derived Custom index, or whether each layer must carry its own custom-action shadow. Validate update_custom_trigger's dual write (keymap.rs:422-433) collapses cleanly.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'layers are just a tag' — there are already parallel shadow collections that any precedence refactor must keep coherent.

### Edge case/failure mode

**A3-Q9. Must a real Unbound state suppress the original_trigger fallback in match_custom (verified at matcher.rs:370-373), and does doing so break the intended 'rebind a menu action's keystroke but keep the menu item firing' behavior that the fallback was built for?**

- _Why it matters:_ Today 'none'→Trigger::Empty (keyboard.rs:44) sets custom_trigger=Empty but leaves original_trigger=Custom(tag); match_custom still matches original_trigger (matcher.rs:370-373), so a Custom-action binding is NOT actually unbound. A naive Unbound that ignores this leaks dispatch; an aggressive one that strips fallback breaks legitimate rebinds. 'Unbound' vs 'rebound' must be disentangled.
- _How to answer:_ Read matcher.rs:363-377 and trace what original_trigger is for (menu/CustomAction dispatch). Define separate states: Rebound (keep original_trigger fallback) vs Unbound (suppress all matching incl. original_trigger). Add a failing test that 'none' on a Custom-triggered editable binding still fires today.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that Trigger::Empty already means 'unbound' — it doesn't for Custom triggers, which is exactly the class fixed/menu bindings use.

**A3-Q10. In the new model, are Unbound bindings excluded from the precedence walk / catalog / conflict detection, or retained as tombstones — given EditableBinding::new defaults trigger=Empty (keymap.rs:660) and removal sets custom_trigger=Empty (keybindings.rs:592), both still yielded by bindings()?**

- _Why it matters:_ Empty/Unbound entries currently survive iteration and are only skipped because they aren't Keystrokes (matcher.rs:325). If the layer system treats an Unbind as a tombstone, a mode-pack can know a key was deliberately disabled; if it drops them, unbound entries may resurface as false conflicts in Axis 5's conflict map (which keys on Option<Keystroke>, keybindings.rs:135).
- _How to answer:_ Decide tombstone vs delete. Trace which consumers walk bindings() (matcher push/match_*, settings_view/keybindings.rs ConflictMap). Ensure an Unbound entry is invisible to conflict detection but visible to layer resolution as a 'block'.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the assumption that 'unbound = gone' — a disabled default must persist as a tombstone for layering and to avoid phantom conflicts.

**A3-Q11. Does the (layer, recency) precedence and the new Unbound state apply uniformly across ALL THREE match paths that independently walk bindings() — push_keystroke for Keystrokes (matcher.rs:324), match_standard for Standard (matcher.rs:351), match_custom for Custom (matcher.rs:363) — or only to keystroke matching?** _(added-by-critic)_

- _Why it matters:_ The draft and report frame layering/precedence around the Keystrokes linear scan, but Standard (Quit/Paste/Close, actions.rs:8-19) and Custom (menu) triggers resolve by the same first-match-over-bindings() rule in two separate loops. If the layer ordering and Unbound suppression are wired only into push_keystroke, unbinding or re-layering a menu/Standard action silently does nothing — a correctness hole exactly where fixed/menu bindings live (Q5).
- _How to answer:_ Read matcher.rs:307-377. Confirm all three loops consume keymap.bindings() in the same order. Specify that the resolver's layer sort and Unbound/tombstone handling are applied once at the bindings() level (or in a shared helper) so all three paths inherit them, and add fixtures for Standard and Custom unbind/precedence (Q12).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks the Keystrokes-only framing — precedence/Unbound that ignores match_standard/match_custom leaks dispatch for the very menu/app actions users most want to disable.

**A3-Q12. How does a user-layer Unbound relate to the THREE existing suppression mechanisms — context_predicate=Just(false), the zero-arg enabled_predicate closure (keymap.rs:626-627), and Trigger::Empty (keymap.rs:660) — so that 'is this key active in this context?' has a single, well-defined answer instead of four overlapping ones?** _(added-by-critic)_

- _Why it matters:_ A binding can already be inert for three different reasons, and the resolver/UI must collapse them to decide 'customized vs unbound vs default'. Adding a fourth (layer Unbound) without specifying its interaction makes both the precedence walk and the settings 'state' badge (Q15) ambiguous — e.g. a binding disabled by enabled_predicate could be misreported as user-unbound.
- _How to answer:_ Define a single is_active(binding, ctx, layers) predicate and a single classify_state() that orders the four mechanisms. Decide whether Unbound is a distinct layer entry (tombstone) or reuses Trigger::Empty, and ensure enabled_predicate=false and context=false render as 'unavailable' not 'user-unbound'. Add tests for each suppression source.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks adding a fourth 'off' switch without unifying the existing three — produces contradictory 'is it bound?' answers between matcher and UI.

### Dependency/sequencing

**A3-Q13. Is Axis 2's context-scoped override (R3b, name+context targeting) a hard prerequisite for the 'remappable fixed bindings' leaf, given fixed keys are duplicate-registered under opposing predicates (actions.rs:51-60: enter→Enter under !Vim, enter→VimEnter under Vim) and update_custom_trigger is name-only (keymap.rs:422-433, clobbers all same-name)?**

- _Why it matters:_ Making 'enter' remappable by a single identity is dangerous when one key maps to two actions by context — a name-only override would rebind both. This defines the shippable slice: can layering+Unbound ship for the editable set first and defer fixed remap until Axis 2 lands?
- _How to answer:_ Confirm update_custom_trigger is name-only (keymap.rs:422-433) and that fixed forks share keystrokes across predicates (actions.rs:51-176). Decide whether Axis 3 ships {layers + Unbound for named editable bindings} now and gates fixed-remap behind Axis 2's context scope.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Attacks treating Axis 3 as independent — its remappable-fixed leaf is unusable without Axis 2's context scope.

**A3-Q14. Is the new user-layer data structure the same object Axis 1's hot-reload writes into, and does it own the 'currently-applied custom names' set needed to revert removed entries to default on reload (report §6 R1 open question), rather than that bookkeeping being bolted on separately in Axis 1?** _(added-by-critic)_

- _Why it matters:_ Today overrides are in-place custom_trigger mutations with no record of which names are user-set (the only reset path is update_custom_trigger(name, None), keymap.rs:422-433). The report flags hot-reload reset semantics as an open question requiring an 'applied custom names' set. A real user layer is the natural home for that set; if Axis 3 builds the layer without it, Axis 1 duplicates the bookkeeping and the two can desync.
- _How to answer:_ Cross-team with the Axis 1 owner: define the user-layer write API so load_custom_keybindings (lib.rs:2557) and a future watcher both target it, and so diffing the layer against a prior snapshot yields the revert-to-default set. Confirm remove_custom_trigger (matcher.rs:146) becomes 'remove from user layer'.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Attacks treating Axis 3's layer and Axis 1's hot-reload reset as separate — the layer IS the place the 'applied names' set should live, or both axes reinvent it.

### Migration/back-compat

**A3-Q15. When a first-class Unbound replaces the overloaded Trigger::Empty, does the on-disk 'none' sentinel (keyboard.rs:15,44→UserDefinedKeybinding::Removed) keep meaning 'unbind' and migrate silently vs via a schema bump — and since fixed bindings have no name, how does the file express disabling a nameless default key, especially given platform is baked at parse (cmd vs ctrl, L7/keymap.rs:914-919) so a key-scoped disable is platform-specific?** _(sharpened)_

- _Why it matters:_ Existing keybindings.yaml files encode removal as 'none' (name-scoped). Reinterpreting that breaks every existing user's unbinds. A name-keyed 'none' cannot disable a nameless fixed default (Q2), so the schema may need a key-scoped disable — which re-introduces the platform problem a name-scoped override avoided.
- _How to answer:_ Read keyboard.rs:15-57,176-213 TryFrom/serialization. Decide: keep 'none' as name-scoped unbind for back-compat; add an optional key-scoped disable entry for fixed defaults, and decide whether it stores a resolved per-OS keystroke (non-portable) or a logical default identity (needs R5 platform-in-data-model). Confirm load_custom_keybindings (lib.rs:2557) can distinguish Unbound from default-absent on reload.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks 'just add an Unbound variant' — it silently changes existing files' meaning and a key-scoped disable for nameless fixed defaults is platform-dependent.

### Testing/validation

**A3-Q16. What is the golden-test harness for the new resolver, given matcher_tests.rs (251 lines) has exactly three tests (test_matcher, test_editable_binding_matching, test_bindings_for_context) and ZERO coverage of shadowing, chord-prefix, precedence ordering, or unbind?**

- _Why it matters:_ A precedence/Unbound/ambiguity rewrite of push_keystroke and bindings() with no characterization tests will regress silently. The current real bugs (short-shadows-chord at matcher.rs:329-331; editable-always-beats-fixed at keymap.rs:454-464) should become the first fixtures so the new behavior is pinned and the old behavior's change is intentional.
- _How to answer:_ Design a table-driven suite: (keymap layers, active context, keystroke sequence) → expected MatchResult incl. a new Unbound outcome. Seed it with regression fixtures for the verified shadow case and editable-vs-fixed precedence, and for all three match paths (Q16).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks shipping a resolver rewrite on faith — there is currently nothing asserting precedence or chord behavior.

**A3-Q17. Beyond synthetic unit fixtures (Q12), is there a full-keymap resolution snapshot — captured at startup over the real ~265 registration sites as (context, keystroke)→action — that can be diffed before/after the refactor to prove no real binding changed winner unintentionally?** _(added-by-critic)_

- _Why it matters:_ Q12 pins designed behaviors on small fixtures, but the precedence rewrite touches bindings() which feeds every real binding registered across 109 files. Reordering from fixed-vs-editable-LIFO to (layer, recency) can flip winners in production contexts no unit fixture covers. A characterization snapshot is the only regression net that scales to the real keymap.
- _How to answer:_ Build a debug harness that enumerates representative contexts (CodeEditorView, terminal EditorView, modal/Vim) and, for each, walks get_bindings() (matcher.rs:303) to emit a stable sorted (context, trigger)→action table; snapshot it on master, then assert equality (modulo intended changes) after the refactor. Reuse the existing #[cfg(debug_assertions)] validate_bindings scaffolding (matcher.rs:181-203).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Attacks pinning only hand-picked fixtures — a (layer, recency) reorder can silently change which of two real same-key bindings wins in a context nobody wrote a fixture for.

### UX/surface behavior

**A3-Q18. Is the chord-ambiguity fix in-scope for Axis 3 (end-goals bullet 4) or deferred to R4, and if in-scope, what policy replaces the immediate exact-match return (matcher.rs:329-331) so a short binding no longer always shadows a longer chord: fixed timeout (what ms?), per-binding 'prefix' opt-in, or disallow registering a short binding that prefixes a longer one in the same context?** _(sharpened)_

- _Why it matters:_ Verified: the early return makes a complete short binding ALWAYS shadow a prefix-sharing chord, order-independently. The roadmap files R4 as 'optional/medium', so its place in Axis 3 must be settled. Any wait-based fix adds input latency to every shadowed short binding (a felt-responsiveness regression), so the policy is a real UX/latency tradeoff, not a free correctness fix.
- _How to answer:_ First decide scope (Axis 3 now vs deferred R4). If in-scope, pick the policy and, if timeout-based, a value and whether it applies globally or only to keys that are a known chord prefix. Spike latency by instrumenting push_keystroke for keys that currently exact-return (matcher.rs:329-331) but have a longer candidate.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks 'just do longest-match' — it silently taxes every short binding with a wait, which power users will notice.

**A3-Q19. Given a 'Default'/restore affordance already exists for customized editable bindings (keybindings.rs:50 RESET_BUTTON_TEXT, :617 reset_to_default_keystroke), what NEW surface does the layer model require: a third display state 'user-unbound' distinct from 'never bound', and a restore path for (a) a user-layer Unbound and (b) nameless fixed-default disables that have no row in today's editable-only list (keybindings.rs:754)?** _(sharpened)_

- _Why it matters:_ If user-unbound is indistinguishable from never-bound, or if disabling a nameless fixed default has no visible/reversible row, users can disable a default and get stuck — contradicting the axis's 'trust what the UI shows' north star. The UI affordance is the surface contract of the layer model.
- _How to answer:_ Decide the three display states (default / customized / user-unbound) and extend the existing reset path to pop a user-layer Unbound. Verify original_trigger (keymap.rs:315) still carries the default so restore is exact, and decide how fixed-binding rows (currently invisible, keybindings.rs:754) surface so a fixed default can be disabled AND restored.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Attacks shipping a precedence model with no visible/reversible surface for the new unbound state and for nameless fixed defaults.

### Performance/scale

**A3-Q20. Is a per-context trie (R4) even in-scope for Axis 3, given the current linear scan runs over only a few hundred bindings and enabled_predicate is confirmed context-free (a zero-arg closure, keymap.rs:626-627) so only context_predicate must be filtered live each keystroke — does a live-filtered trie actually beat the current O(n) scan at this scale?** _(sharpened)_

- _Why it matters:_ Section 6 flags trie correctness as an open risk. Since enabled_predicate takes no args, only context filtering is dynamic — but a per-keystroke context re-filter may make a trie slower than today's scan over a few hundred bindings. This decides whether the chord fix (Q7) needs a trie at all in this axis or is premature optimization.
- _How to answer:_ Count bindings eligible in a typical context; microbenchmark the linear scan in push_keystroke (matcher.rs:324-338) vs a candidate-set trie that re-filters by context each keystroke. Decide: keep linear scan for Axis 3 and defer the trie, or build it only if the chord policy demands it.
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Attacks 'add a trie for speed' — context filtering may force per-keystroke rebuild that erases the win at this scale.

<details><summary>Already settled by the report/code — pruned as non-questions (3)</summary>

- ~~Q1 sub-axis: classify FixedBinding::new sites by trigger kind (keystroke vs Standard/Custom).~~ — Already answered by code: FixedBinding::new unconditionally builds Trigger::Keystrokes (keymap.rs:511-525, `trigger: Trigger::Keystrokes(keys)`), so 100% of the 397 ::new sites are keystroke-triggered. Fixed bindings with Standard/Custom triggers come from a different constructor path. The only discriminating axis left is context user-reachability + coexisting same-key editable — folded into the sharpened Q1.
- ~~Q8 sub-question: confirm enabled_predicate is context-free (takes no args).~~ — Answered by code: enabled_predicate is invoked as a zero-arg closure — is_enabled() does `self.enabled_predicate.is_none_or(|predicate| predicate())` (keymap.rs:626-627). It is context-free; only context_predicate filtering must be live per keystroke. Folded into sharpened Q8 so the question now turns purely on whether a per-context trie is even in-scope for Axis 3.
- ~~Q15 premise: 'restore default' must be made a first-class action.~~ — Partially already implemented: a 'Default' reset affordance exists for customized editable bindings — RESET_BUTTON_TEXT="Default" (settings_view/keybindings.rs:50), KeybindingsViewAction::ResetToDefaultKeyStroke→reset_to_default_keystroke (:165,:617) calling reset_keybinding_to_default (util/bindings.rs). Sharpened Q15 drops the already-built piece and targets the genuinely-missing 'user-unbound vs never-bound' display state and restore for nameless fixed-default disables (which have no row in today's editable-only list, keybindings.rs:754).

</details>

---

