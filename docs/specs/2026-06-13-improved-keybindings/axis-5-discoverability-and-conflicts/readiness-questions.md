[← Back to index](../README.md)

## Axis 5 — Discoverability & truthful conflicts

**End state:** the user can find any bindable action, see its real binding + scope, and get honest, actionable conflict feedback.

> **Killer question:** What is the conflict "scope unit" and the predicate-overlap rule it uses — exact-ContextPredicate-equality, BindingGroup-equality, or real predicate satisfiability/overlap — given that EditableBindingLens.context is private (keymap.rs:311), CommandBinding carries no scope field (bindings.rs:531-541), and no overlap/SAT routine exists for ContextPredicate (only point-evaluation eval() at context.rs:100-120)? Every other "truthful conflict" and "scope column in the catalog" decision in this axis is downstream of this one.

### Scope/requirements

**A5-Q1. What is the catalog's single source of truth, and how does it reconcile with the two existing static surfaces? Today there is a name-only curated catalog (resource_center/utils.rs:8-114) AND a read-only cheatsheet (keybindings_page.rs, empty KeybindingsAction enum). Is catalog v1 a live startup walk of get_key_bindings(), and does it REPLACE, reconcile, or coexist with these two? If coexist, what prevents three drifting sources of truth?** _(added-by-critic)_

- _Why it matters:_ The North Star is 'what the UI shows is the truth'. Leaving a hand-maintained static catalog alongside a live one guarantees drift and re-creates the discoverability gap. Defines whether the cheatsheet is unified or kept.
- _How to answer:_ Read resource_center/utils.rs:8-114 and keybindings_page.rs:69-382. Decide: derive cheatsheet sections from the live manifest, or deprecate the static lists.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Treats 'add a catalog' as additive; ignores the two pre-existing static catalogs that will silently contradict it.

### Design decision

**A5-Q2. To make a binding's scope visible/conflict-keyable, do we make EditableBindingLens.context pub (private at keymap.rs:311) and thread it into a new CommandBinding scope field (today CommandBinding has none, bindings.rs:531-541; from_editable_lens at bindings.rs:762 never reads lens.context), or approximate scope from the already-pub `group` field? Note BindingGroup is 12 SEMANTIC categories (Settings/Navigation/Terminal/..., bindings.rs:797-810), not context scopes (terminal vs code-editor vs vim-normal), so it cannot distinguish per-context collisions.** _(sharpened)_

- _Why it matters:_ Per-binding scope is unreadable from the UI today; this gates both context-aware conflicts (R6) and the catalog's scope column (R9). Choosing `group` as a proxy silently re-introduces the false positives R6 is meant to kill.
- _How to answer:_ Read keymap.rs:307-318 (lens fields) and bindings.rs:531-541,762-771; engine owner decides whether to expose ContextPredicate or a derived scope id. Prototype a CommandBinding.scope field fed from lens.context.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Treats context-aware conflicts as a UI-only change when scope is engine-private; and assumes `group` is a usable scope proxy when it is a semantic category.

### Code fact to verify

**A5-Q3. How do read-only FIXED bindings get a stable, persistable catalog id? They ARE enumerable today via get_key_bindings() (app.rs:1699 -> matcher.rs:303 -> keymap.rs:454), but FixedBinding::as_lens hardcodes name: Default::default() (empty, keymap.rs:633) and the only identifier is a process-local atomic BindingId (keymap.rs:264-271) assigned in registration order — not stable across builds/runs and not currently persistable. Do we add a `name`/stable-id field to FixedBinding (~146 register sites) or synthesize one (e.g. from group+trigger+description)?** _(sharpened)_

- _Why it matters:_ No stable string id means fixed bindings can't be searched-by-name, deduped, conflict-named, or referenced by the change-keybinding agent. The draft's 'no public fixed_bindings' premise was false; the real blocker is namelessness + non-stable id.
- _How to answer:_ Read keymap.rs:277-286 (FixedBinding), 631-642 (as_lens), 264-272 (BindingId). Audit register_fixed_bindings sites (matcher.rs:89, ~146 callers) for cost of adding a name vs a synthesized-id strategy.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Original premise mis-stated that fixed bindings aren't enumerable; the corrected risk is that their lens identity (empty name + volatile BindingId) cannot anchor a catalog.

**A5-Q4. Are the binding validators usable on the release-build edit path? is_binding_pty_compliant / is_binding_cross_platform run only through validate_bindings(), which (with register/set_default_binding_validator) is entirely #[cfg(debug_assertions)] (matcher.rs:159-203) and runs at registration, not on set_custom_trigger. Do we lift them into a release-safe AppContext::validate_trigger(name, trigger) reusing the registered validators, and is the inline warning advisory or blocking?** _(added-by-critic)_

- _Why it matters:_ R10 (validators on the edit path) is in this axis. If the validators are compiled out of release, 'inline-warn before persisting' has no implementation; this determines whether R10 is a small wire-up or a real refactor of the validator registry.
- _How to answer:_ Read matcher.rs:155-203 and confirm_keystroke_editing (keybindings.rs:669). Verify the validator fns' cfg-gates and whether the registry survives in release builds.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes validators are callable on save; they are debug-only and run at registration, not on user edits.

### Edge case/failure mode

**A5-Q5. What is the operational definition of 'two bindings on the same keystroke conflict'? There is no satisfiability/overlap routine for ContextPredicate — only point-eval at context.rs:100-120. Do we ship (a) exact predicate structural equality, (b) BindingGroup equality, or (c) a real can-both-be-true overlap check, and if (c), how do we compute it for And/Or/Not/Equal/NotEqual predicates without a SAT solver?** _(added-by-critic)_

- _Why it matters:_ This single rule defines whether conflict feedback is 'truthful'. (a) misses real collisions across differently-spelled-but-overlapping predicates; (c) is the only honest answer but needs a new engine primitive. Picking wrong makes the whole axis' headline feature lie in the opposite direction.
- _How to answer:_ Read context.rs:9-18 (predicate variants) and 100-120 (eval). Spike a predicate-overlap function over the existing 7 variants; evaluate cost/correctness vs exact-equality on the real binding set walked from get_key_bindings().
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Assumes 'context-aware' is just adding a context to the map key, hiding that overlap of arbitrary predicates is an unsolved primitive in this engine.

**A5-Q6. Should conflict detection scan fixed bindings and custom-action bindings, not just editable ones? ConflictMap is built only from the editable list shown in the editor (keybindings.rs:135-146, source at :758), so a user rebind that collides with a FixedBinding (get_key_bindings at app.rs:1699 exposes them) or a custom-action binding (custom_action_bindings at app.rs:1911) reports 'no conflict' — the opposite of truthful.** _(added-by-critic)_

- _Why it matters:_ Silent collisions with non-editable bindings are exactly the bugs users hit (e.g. rebinding over a fixed escape/paste). If the conflict map's universe is wrong, 'names the colliding action' (G1/R6) still lies.
- _How to answer:_ Read keybindings.rs:104-146 (ConflictMap build) and app.rs:1699,1911. Decide the binding universe; verify fixed/custom lenses carry enough identity to name the collision (see Q4 — fixed lenses have empty name).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes the editable list is the whole keymap; ignores that fixed and custom-action bindings are invisible to the current conflict map.

**A5-Q7. How does conflict detection handle chords and prefix-shadowing once chord capture (G4/R8) lands? ConflictMap keys on a single Keystroke (keybindings.rs:106) and update() takes one Keystroke (keybindings.rs:110-121), but chords are Vec<Keystroke>, and the matcher is first-match-wins so a complete short binding silently shadows any longer chord sharing its prefix (L5, matcher.rs:307-346). Is prefix-shadow a 'conflict' the UI must surface, and how is ConflictMap rekeyed to Vec<Keystroke> + prefix relationships?** _(added-by-critic)_

- _Why it matters:_ Chord capture is in this axis' Phase-1 scope; without chord-aware conflicts the new multi-key bindings would collide invisibly and shadow each other, which is the precise dishonesty this axis targets.
- _How to answer:_ Read keybindings.rs:104-146 (ConflictMap), bindings.rs:491-499 (1-elem vec today), matcher.rs:307-346 (prefix/early-return). Design a chord-and-prefix conflict key; decide if prefix-shadow is surfaced as conflict vs warning.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes conflict = identical single keystroke; ignores chords and the first-match prefix-shadow semantics that produce silent overrides.

**A5-Q8. How does the catalog/search represent one action NAME that is bound in multiple contexts? A name maps to several bindings with distinct ContextPredicates (editable_bindings_by_name: HashMap<&str, Vec<usize>>, keymap.rs:30), and the editor's dedup_by collapses same-name+same-description rows but NOT same-name/different-description ones (keybindings.rs:782, see comment 766-781). Is each (name, context) a separate catalog entry, or one entry with N scopes?** _(added-by-critic)_

- _Why it matters:_ 'See its real binding + scope' is incoherent if the catalog shows one row for a name that actually resolves to different triggers/actions per context. Also governs whether search-by-name returns 1 or N hits.
- _How to answer:_ Read keymap.rs:24-38 (name index), 422-433 (name-keyed override), keybindings.rs:759-783 (sort+dedup). Decide entry granularity; align with Q1's scope field.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes name uniquely identifies a binding; the engine explicitly maps one name to a Vec of context-distinct bindings.

**A5-Q9. How are actions with no keyboard trigger represented in the catalog, search, conflict, and the Unbound filter? CommandBinding.trigger is Option<Keystroke> and trigger_to_keystroke (bindings.rs:234) returns None for Standard/Custom/Empty triggers — so Standard-action and currently-unbound editable bindings have trigger=None. Do they appear in the catalog, are they searchable, and do they (correctly) never conflict?** _(added-by-critic)_

- _Why it matters:_ 'Find ANY bindable action' and the R7 'Unbound' filter chip require triggerless/unbound entries to be first-class. If they're filtered out (like the cheatsheet's trigger.is_some() filter), the catalog is incomplete.
- _How to answer:_ Read bindings.rs:234-260 (trigger_to_keystroke), 534 (Option<Keystroke>), utils.rs trigger.is_some() filter. Decide catalog inclusion and Unbound-filter semantics.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes every action has a keystroke; Standard/Custom/Empty-trigger actions have none and would silently vanish from a trigger-keyed catalog.

**A5-Q10. Does conflict detection and the catalog account for platform-split bindings, or explicitly scope to the running OS only? Keystrokes are resolved to the current OS at parse/construction (Keystroke::parse maps cmdorctrl via OperatingSystem::get(), keymap.rs:914-919; new_per_platform at keymap.rs:497-508), so a binding that is cmd-on-mac / ctrl-on-linux is only ever seen as one OS's keystroke. The conflict map and catalog therefore can't detect a collision that only exists on the OTHER platform.** _(added-by-critic)_

- _Why it matters:_ 'Truthful' conflicts and a portable catalog are misleading if they silently reflect only the current OS. Tied to R5/L7 (platform-in-data-model); the design doc must state whether cross-platform truthfulness is in or out of scope.
- _How to answer:_ Read keymap.rs:497-508,688-713,914-919 (platform resolution) and report R5/L7. Product/eng decision: current-OS-only with an explicit caveat, or wait on R5.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Assumes one machine sees the whole keymap; platform divergence is baked at parse, so other-OS conflicts are invisible.

### Dependency/sequencing

**A5-Q11. Where is the Phase-1/Phase-2 scope line for this axis? The report sequences search-by-name, chord capture, validators, and catalog-v1 as Phase 1 (independent), but context-aware/truthful conflicts (R6) as Phase 2 because they depend on Axis 2's context-scoped data model (exposing + threading ContextPredicate). Can ANY 'truthful conflict' ship in Phase 1 (e.g. a best-effort exact-same-context check using Q1's scope field), or is all conflict-truthfulness gated on Axis 2?** _(added-by-critic)_

- _Why it matters:_ Determines what this design doc can actually promise to ship without the Axis 2 engine work. Mis-scoping ships either a still-lying conflict UI in Phase 1 or stalls the whole axis behind the engine refactor.
- _How to answer:_ Cross-read report §4 R6, §7 phasing, and end-goals Dependency Spine. Decide whether a Phase-1 'exact-context-only' conflict mode is acceptable interim truthfulness.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Assumes truthful conflicts are a Phase-1 quick win; they structurally depend on the Axis 2 context model that isn't built yet.

### Migration/back-compat

**A5-Q12. What stable key and snapshot format does the persisted action manifest (R9, for the change-keybinding agent) use, and how does it reference fixed bindings? BindingId is non-deterministic across runs (keymap.rs:264-271), fixed lenses have no name (keymap.rs:633), and descriptions can be dynamic (materialize_description, bindings.rs:785-791) so a frozen snapshot may capture a stale string. Is the key the editable `name`, and are nameless fixed bindings simply unreferenceable until Q4 is resolved?** _(added-by-critic)_

- _Why it matters:_ An agent that maps 'description -> action id without guessing' (R9) needs a key that survives rebuilds and points at a real action. Keying on BindingId breaks across versions; excluding fixed bindings limits what the agent can rebind.
- _How to answer:_ Read bindings.rs:785-791 (dynamic desc), keymap.rs:264-271 (id), 294/633 (names). Decide manifest schema, regeneration trigger, and on-disk location; depends on Q4.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes BindingId or description is a durable key; both are volatile, and fixed bindings lack any name to key on.

### Testing/validation

**A5-Q13. What is the regression strategy for conflict truthfulness and catalog completeness against ~265 imperative register sites? Concretely: a golden test asserting that known non-overlapping contexts (e.g. the id!("Vim") vs !id!("Vim") forked bindings, actions.rs:51-60) produce NO conflict while a same-context collision DOES; and a test that every binding from get_key_bindings() appears in the catalog with a resolvable id. How do we keep these from rotting as bindings are added across 109 files?** _(added-by-critic)_

- _Why it matters:_ Both deliverables (truthful conflicts, complete catalog) are only as trustworthy as their tests. Without a completeness test over the live binding set, new register sites silently drop out of the catalog and re-open the discoverability gap.
- _How to answer:_ Read matcher.rs:303 (get_bindings) and the Vim fork at actions.rs:51-60. Design unit tests over a built keymap fixture; consider a CI assertion that every registered name has a catalog entry.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes correctness once; ignores that 265 scattered register sites guarantee drift without a completeness/overlap test harness.

### UX/surface behavior

**A5-Q14. What is the hard-vs-soft conflict policy on save? confirm_keystroke_editing (keybindings.rs:669-699) currently performs NO conflict check and always calls set_custom_keybinding. Do we (a) warn-only, (b) block save on a same-context 'hard' conflict, or (c) offer one-click rebind/swap that unbinds the loser? And what exactly does 'Conflicts with: <description>' show when N bindings collide?** _(added-by-critic)_

- _Why it matters:_ End-goal explicitly lists 'optional save-gate on hard conflicts' and 'one-click rebind/swap'. This is the user-visible contract of the axis; ambiguity here blocks the render path (render_clicked at keybindings.rs:307) and the save path design.
- _How to answer:_ Read keybindings.rs:669-722 (confirm/temporary) and 270-324 (conflict render). Product decision on gate vs warn; design the swap affordance and multi-collision display.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Assumes a warning border is enough; never decides whether the system should refuse to persist a genuine same-context collision.

**A5-Q15. When search-by-name is added (R7 extends filter_bindings_including_keystroke, which never reads binding.name today, bindings.rs:625-687), do we surface the raw internal id (e.g. 'editor_view:delete_all_left', namespace:action convention only) to the user, or use it as a hidden search key only? And does name-search expose bindings that the display dedup (keybindings.rs:782) currently hides?** _(added-by-critic)_

- _Why it matters:_ Axis headline is 'search by action name / internal id'. Showing raw ids is power-user-friendly but ugly; hiding them limits agent/discoverability value. Interaction with dedup determines whether matches are even reachable in the list.
- _How to answer:_ Read bindings.rs:625-687 (filter) and keybindings.rs:782 (dedup). Product decision on raw-id visibility; verify dedup doesn't drop name-only matches.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Assumes 'add name to fuzzy match' is free; ignores that dedup can hide the very rows a name search should return.

---

