# Improved Keybindings — Design-Readiness Questions (Adversarial)

**Date:** 2026-06-13
**Status:** Question-set (input to per-axis brainstorm -> spec -> plan cycles)
**Companion to:** [`2026-06-13-improved-keybindings-end-goals-design.md`](./2026-06-13-improved-keybindings-end-goals-design.md) and the architecture report at [`.understand-anything/keybindings-architecture-report.md`](../../.understand-anything/keybindings-architecture-report.md)

## Purpose

For each capability axis, the **questions that must be answered before a dev design doc can be written**. These are not the design — they are the interrogation that de-risks it. Each was generated adversarially (attack the naive implementation), then critiqued (prune what the report/code already answers, sharpen the rest, add what a skeptic would catch). Every question carries _why it matters_, _how to answer it_, and _who/what can answer it_ (`code-investigation` = go read/measure; `user-product-decision` = a product call; `prototype-spike` = build a throwaway; `external-research` = study Helix/Kakoune etc.; `cross-team-decision` = needs another owner).

## How to use this

1. Take one axis (the end-goals doc recommends starting with **Axis 1 + the Phase-1 slice of Axis 5**).
2. Answer its **killer question** first — it gates the rest.
3. Walk the `code-investigation` questions (cheap, unblock facts), then force the `user-product-decision` / `prototype-spike` ones.
4. Carry the **cross-axis questions** into whichever axis you start, since they constrain the schema/abstraction choices that are expensive to reverse later.

---

## Initiative-wide

> **Meta question:** Is the "binding layer / context-scope / mode" the report calls "one missing primitive ... the same feature viewed from three angles" (report L13, L228-229) actually ONE engine abstraction that must be designed and built once up front — a single resolved-binding store with explicit (layer, recency) precedence, context predicates parsed from data, an Unbound state, and platform-unresolved keystrokes, which the hot-reload watcher (Axis 1), the settings-UI override/conflict path (Axis 5), the context-scoped override (Axis 2), and every modal engine (Axis 4) all read and write through — or is it genuinely three separable recommendations (R2 layers, R3 context schema, Step D modal contexts) that the phased roadmap (report §7) can ship independently across Phases 1/2/3? If it is one primitive, the entire phase ordering is mis-cut: the "independent" Phase-1 quick wins either build throwaway scaffolding over today's flat name→trigger HashMap (keyboard.rs:169) or must wait for the core; if it is three, the program needs an explicit, written contract at each seam (file ↔ layer ↔ matcher ↔ catalog). Every sequencing, rework-risk, and team-allocation decision in the initiative hinges on this single architectural call.

**Readiness risk:** Sequencing is the most at-risk dimension initiative-wide. The roadmap presents Phases 1→2→3 as a clean dependency chain with "independent, no schema/engine change" Phase-1 quick wins (end-goals L117), but the whole-picture view shows those quick wins all commit to a data shape the Phase-2 engine core must then break: hot-reload reset bookkeeping is name-keyed (must become name+context, Axis 2-Q19); import/export and chord-capture writes serialize the flat current-OS-resolved map (must become {name,trigger,context?,platform?} records, R3b, and carry unresolved cmdorctrl/{mac,other}, R5); catalog v1 walks editable-only with non-stable ids (must add fixed bindings + stable keys, Axis 3/Axis 5). So the "independent" wins are forward-INCOMPATIBLE unless co-designed against the Phase-2 schema now. Compounding this, the one shared primitive (binding layer/context-scope) is assigned to three different phases, and R3b is simultaneously placed in Axis 1 (end-goals L52-53) and Phase 2 (report §7) — an unresolved scope contradiction. Requirements clarity is a close second (that R3b contradiction, plus the FixedBinding magnitude unknown), but sequencing binds first: even with perfect requirements, the current phase cut risks building and discarding most of the Phase-1 surface area.

### Cross-axis & sequencing questions

These span two or more axes or concern build order — answer them before committing to any single-axis schema or abstraction.

**X1. Is there ONE in-memory resolved-binding data structure that the hot-reload watcher writes into (Axis 1), context-scoped overrides target (Axis 2), the layer/precedence resolver owns (Axis 3), modal mode-packs register into (Axis 4), and the catalog/conflict detector reads from (Axis 5) — or do we accept the four-plus parallel collections that exist today (fixed_bindings, editable_bindings, fixed_custom_action_bindings, editable_custom_action_bindings; keymap.rs:391-411) growing into even more per-axis stores?**

- _Axes:_ Axis 1, Axis 2, Axis 3, Axis 4, Axis 5
- _Why it matters:_ The report (L13, L228-229) asserts all three goals converge on one primitive, yet R2/R3b/Step-D are scoped to three separate phases and update_custom_trigger already maintains two collections in lockstep (keymap.rs:422-433) while three match paths walk bindings() independently (matcher.rs:324,351,363). If each axis invents its own store, hot-reload reset (Axis 1), name+context targeting (Axis 2), unbind/precedence (Axis 3), and modal layers (Axis 4) will each re-implement resolution differently and drift. This is the structural decision that all sequencing flows from.
- _How to answer:_ Design-spike a single LayeredKeymap (layer tag + context predicate + Unbound) and prove that the Axis-1 watcher reload, an Axis-2 name+context override, an Axis-4 mode-pack, and the Axis-5 catalog walk are all expressible as reads/writes against that one structure, replacing the four current vecs. Confirm Tracked<EditableBinding> live-render (keymap.rs:24) survives the unification or is replaced by a layer-revision counter (Axis 3-Q11).
- _Answerable by:_ `prototype-spike`

**X2. Should Phase-1 ship the Phase-2 RECORD file schema ({name, trigger, context?, platform?}, R3b) from day one — with context/platform simply absent in v1 — so the on-disk format, the reset/applied-set key, the import/export payload, and the chord-capture write are NEVER broken, rather than shipping over today's flat HashMap<String, PersistedTrigger> (keyboard.rs:169) and forcing a migration when Axis 2/Axis 5/Axis 6 land?**

- _Axes:_ Axis 1, Axis 2, Axis 5, Axis 6
- _Why it matters:_ Every Phase-1 'quick win' writes the flat map: hot-reload reset is name-keyed, import/export (R7) round-trips it, chord capture threads Trigger::Keystrokes through it. If Phase 2 then changes the schema to records, read_custom_keybindings returns None on any deserialize change (keyboard.rs:132-138) and silently drops every user's bindings on upgrade (Axis 1-Q17), and every Phase-1-exported file becomes legacy. Committing the record schema up front (even with all-None scope/platform) decouples the file format from the engine refactor and makes the quick wins genuinely forward-compatible.
- _How to answer:_ Decide the canonical record schema and a back-compat deserializer that accepts today's flat 'name: trigger' entries as records with context=None/platform=None, then build all Phase-1 writers/readers against it. This is a cross-team architecture commitment binding Axes 1/2/5/6 before any Phase-1 code lands.
- _Answerable by:_ `cross-team-decision`

**X3. Does the Phase-1 import/export quick win (R7) require platform-in-data-model (R5, Axis 6) as a hard prerequisite, given keybindings.yaml persists RESOLVED current-OS strings ('cmd-d' on mac, 'ctrl-d' on linux; keyboard.rs:176-187) — so a mac export imported on Linux is a literal cmd binding Linux rarely emits — or is Phase-1 import explicitly same-platform-only, contradicting the north-star 'drop in a colleague's config and it just works' (end-goals L54)?**

- _Axes:_ Axis 5, Axis 6, Axis 1
- _Why it matters:_ Import/export is sequenced as an independent Phase-1 win, but the 'portable data' promise is false cross-platform until R5 lands (Phase 2+), because builders discard the inactive platform at registration (keymap.rs:660,688-713) and the file carries only one OS's resolved string. Either R5's cmdorctrl token form is pulled into Phase 1 (Axis 6-Q9 split), or portability is quietly downgraded to same-OS — a product decision the roadmap never makes explicit.
- _How to answer:_ Product decision: define whether v1 import/export is same-platform-only (and label it so) or whether the cmdorctrl-token slice of R5 (parse already round-trips it, keymap.rs:914-919) ships alongside Axis 1 in Phase 1. Tie to the X2 schema decision since the full {mac,other} pair needs the record schema.
- _Answerable by:_ `user-product-decision`

**X4. What exactly must the action catalog (R9) contain to serve BOTH the settings UI and the change-keybinding agent skill, and is the Phase-1 catalog-v1 (a startup walk of editable_bindings() only, current-OS, context-less, keyed on the editable `name`) sufficient — or does the agent need stable ids for nameless fixed bindings (as_lens hardcodes name=Default, keymap.rs:633; BindingId is non-deterministic, keymap.rs:264-271), per-context scope (Axis 2), and platform variants (Axis 6) that only Phases 2-3 produce, meaning the catalog is inherently versioned, not 'done' in Phase 1?**

- _Axes:_ Axis 5, Axis 3, Axis 4, Axis 6
- _Why it matters:_ The catalog is the single contract feeding two very different consumers: a human-facing settings list and a machine agent that maps description→action id without guessing. The agent needs a frozen, stable, build-invariant key; the UI tolerates dynamic descriptions (materialize_description, bindings.rs:785-791). Fixed bindings (Axis 3 naming work), contexts (Axis 2), and platform splits (Axis 6) are all things the agent will want but Phase-1 cannot supply — so a 'v1' catalog risks locking the agent onto an incomplete manifest, or forcing the agent to re-key when Phase 2/3 extend it.
- _How to answer:_ Cross-team decision between the settings-UI owner and the agent-skill owner: define the manifest's stable key (editable name now; synthesized stable id for fixed bindings, Axis 5-Q4), its versioning story, and whether UI and agent consume the SAME serialization. Specify which fields are guaranteed-stable vs best-effort, and gate the agent contract on it.
- _Answerable by:_ `cross-team-decision`

**X5. Should the FixedBinding magnitude audit (how many of the 397 FixedBinding::new sites, all keystroke triggers per keymap.rs:525, sit in a user-reachable context) be done ONCE as initiative-level groundwork before any axis is scoped — given it simultaneously gates Axis 3 (are fixed bindings a contained Unbound refactor or a ~400-site identity project), Axis 4 (the flagship per-mode forks enter/backspace-in-Vim are FixedBindings that update_custom_trigger never touches, actions.rs:51-60; editor/view/mod.rs:197-209), and Axis 5 (the catalog promises 'read-only fixed bindings' and truthful conflict must scan them, Axis 5-Q3)?**

- _Axes:_ Axis 3, Axis 4, Axis 5
- _Why it matters:_ The end-goals doc gates the whole 'remappable fixed bindings' leaf on this audit (L78, L145), but the audit's result also decides whether Axis 4 can rebind its flagship keys at all, what fraction of the catalog is currently unreferenceable, and whether conflict detection is structurally blind to a large class. The report's L9/§6 claim that Fixed is 'reserved for internal/transient' is empirically contradicted by the code-editor registering its entire navigation set as Fixed under id!("CodeEditorView") (Axis 3 killer). One audit resolves three axes' scope.
- _How to answer:_ Code investigation: enumerate all FixedBinding::new sites, classify each by whether its context_predicate is a user-reachable view (CodeEditorView, terminal editor) vs internal/transient (modal-escape, lightbox, onboarding), and produce the count. This is mechanical grep-and-classify over keymap.rs registration sites across 109 files — do it before scoping Axes 3/4/5.
- _Answerable by:_ `code-investigation`

**X6. Must the question 'is key K active for action A in context C right now?' be unified into ONE predicate-walk before Axes 2, 3, and 4 build on it — given that today it has four overlapping answers (context_predicate=Just(false), the zero-arg enabled_predicate closure keymap.rs:626-627, Trigger::Empty keymap.rs:660, and soon Unbound) resolved across THREE independent match paths (push_keystroke matcher.rs:324, match_standard :351, match_custom :363) — or do Axis 2 (scoped match), Axis 3 (unbind/precedence), and Axis 4 (modal submode contexts) each bolt their semantics onto the current fragmented matcher?**

- _Axes:_ Axis 2, Axis 3, Axis 4
- _Why it matters:_ Axis 2 adds context-scoped matching, Axis 3 adds Unbound + (layer,recency), Axis 4 adds Modal:{engine}:{submode} contexts — all three are answers to the same resolution question, but layered onto a matcher that already answers it four inconsistent ways across three code paths (Axis 3-Q16, Q19). If they aren't unified first, an Unbound in one path won't suppress in another, and a scoped modal override may resolve differently for Keystroke vs Standard vs Custom triggers.
- _How to answer:_ Prototype the unified resolver (single bindings() walk that applies layer, context predicate, and Unbound uniformly across all three trigger kinds) and verify Axis-2 scoping, Axis-3 unbind, and Axis-4 modal contexts all express through it. Decide whether this resolver is shared infrastructure that lands before Phase-2 axis work, not inside any one axis.
- _Answerable by:_ `prototype-spike`

**X7. Is the ContextPredicate string-identity refactor (R3a: Cow<'static,str>/interned ids replacing the &'static str in Context/ContextPredicate, context.rs:3-18) a SINGLE shared prerequisite that both Axis 2 (config-authored runtime predicate atoms) and Axis 4 (dynamic Modal:{engine}:{submode} contexts, Step D) depend on — and if Axis 4 sidesteps it with a CLOSED compile-time enum of &'static str submode flags (the mechanism used by VimNormalMode/VimVisualMode today, view.rs:2388-2410), does that fork the context system into two vocabularies (static-compiled vs config-parsed) that conflict detection and the catalog must then reconcile?**

- _Axes:_ Axis 2, Axis 4, Axis 6
- _Why it matters:_ Axis 2-Q6 and Axis 4-Q1 are the same underlying refactor seen from two axes: config predicates need runtime strings, modal submodes need dynamic context keys. If R3a lands once, both are unblocked; if Axis 4 avoids it via a closed enum to ship sooner, then config-authored predicates (Axis 2) and engine-internal flags (Axis 4) live in different string worlds, and Axis 5's conflict/overlap logic must handle both. This determines whether R3a is on the critical path for Phase 2 AND Phase 3, or escapable.
- _How to answer:_ Spike R3a once and measure blast radius across Context/ContextPredicate (40+ consumers), then test whether a closed submode enum satisfies Axis 4 without it. Decide whether to do R3a as shared groundwork or accept a documented two-vocabulary split with an explicit reconciliation rule for the catalog/conflict code.
- _Answerable by:_ `prototype-spike`

**X8. Does Axis 1's 'quick win' hot-reload actually require Axis 3's user-LAYER object to be built first to be non-throwaway — given its reset bookkeeping (the 'currently-applied custom names' set, end-goals L152) is name-keyed and must become name+context once Axis 2 lands (Axis 2-Q19), and the reset operation 'revert removed entries to default' becomes 'rebuild the user layer' once Axis 3 lands (Axis 3-Q18)?**

- _Axes:_ Axis 1, Axis 2, Axis 3
- _Why it matters:_ Hot-reload is the flagship Phase-1 win and the report calls it low-risk by copying the settings watcher. But its reset semantics are the one part that the Phase-2 engine core invalidates: a name-only applied-set cannot revert a context-scoped override on a subset of same-name bindings without clobbering its siblings. So either Axis 1 writes into the eventual layer structure from day one (making Axis 3's layer model a prerequisite, contradicting 'independent Phase 1'), or Phase-1 reset is knowingly rebuilt in Phase 2.
- _How to answer:_ Sequencing decision: choose between (a) co-designing the user-layer object now so Axis 1 writes into it (pulls Axis 3 partially into Phase 1), or (b) shipping a name-only applied-set as explicitly temporary scaffolding with a planned Phase-2 rewrite. Tie to X2 (record schema) since the applied-set key and the file key should match.
- _Answerable by:_ `cross-team-decision`

**X9. Does Axis 2's mutate-vs-inject decision (mutate custom_trigger on the matched subset via as_lens, keymap.rs:741-759, vs INJECT a new higher-precedence {name, trigger, predicate} binding) force a single co-designed engine change spanning Axes 2/3/4 — because Axis 4 mode-packs (Step D) must ADD bindings predicated on Modal:{engine}:{submode}, which is the inject path, which is exactly Axis 3's layer model — collapsing the roadmap's sequential 'Axis 2 then Axis 3 then Axis 4' into one engine deliverable?**

- _Axes:_ Axis 2, Axis 3, Axis 4
- _Why it matters:_ If Axis 2 chooses in-place mutation (no new bindings), mode-packs that introduce keys not present in defaults can't use it and need the inject/layer path anyway; if Axis 2 chooses inject, it has already built most of Axis 3's layer machinery. Axis 2-Q4 and Axis 3-Q10 each flag the other as a prerequisite — seen together, the dependency is mutual, meaning the three cannot ship as independent sequential phases. This reshapes the entire Phase-2/Phase-3 boundary.
- _How to answer:_ Engine design-spike: prototype a mode-pack (even a stub vim layer) as injected higher-precedence bindings and confirm whether the same inject mechanism serves Axis-2 user overrides. If yes, merge R2+R3b+(mode-pack registration) into one co-designed engine change and re-cut the phase boundary accordingly.
- _Answerable by:_ `prototype-spike`

**X10. Is 'truthful conflict detection' (the Axis 5 north-star, end-goals L41 'what the UI shows is the truth') gated on BOTH Axis 2 (a real ContextPredicate overlap/satisfiability check, since only point-eval exists today, context.rs:100-120) AND R5/Axis 6 (platform-parameterized resolution, since the conflict map keys on a bare current-OS Keystroke and cannot see a collision that exists only on the other platform, Axis 6-Q17) — making the north-star the LAST capability to land rather than an incremental Phase-2 win?**

- _Axes:_ Axis 5, Axis 2, Axis 6
- _Why it matters:_ The roadmap puts context-aware conflicts in Phase 2 as depending only on Axis 2's context exposure, but the whole-picture view adds a second hard dependency: platform. A binding that is cmd-on-mac/ctrl-on-linux is only ever seen as one OS's keystroke (keymap.rs:914-919), so conflict truthfulness across platforms requires R5's stored both-sides model AND a platform-parameterized ConflictMap. 'The UI shows the truth' therefore cannot be honest until both Axis 2 overlap logic and the Axis 6 platform model exist.
- _How to answer:_ Cross-team scoping decision: define what 'truthful conflict v1' guarantees (e.g., same-OS, same-context exact-predicate-equality) vs the full claim (cross-platform, predicate-overlap), and sequence the honest-UI milestone after both Axis 2 overlap and R5 land. Decide whether a best-effort exact-context same-OS check can ship earlier without overclaiming.
- _Answerable by:_ `cross-team-decision`

**X11. Who owns the action-name alias/migration map, given action `name` is the stable key shared by the file loader (Axis 1: unknown names silently no-op, keymap.rs:423-432), the catalog and agent skill (Axis 5/R9: name is the persistable id), and Axis 4's Step-D migration that RENAMES a batch of them (Vim-prefixed actions like VimEnter collapse into one ModalKeystroke, actions.rs:50-294) — orphaning users' persisted custom triggers keyed on the old names (Axis 4-Q15, Axis 1-Q10)?**

- _Axes:_ Axis 4, Axis 1, Axis 5
- _Why it matters:_ Action names are an implicit public API the moment users hand-edit keybindings.yaml, the catalog references them, and the agent skill maps to them. With ~437 inline static-str names that drift across releases, any Axis-4 rename silently breaks persisted bindings and stale catalog/agent references unless a shared alias map exists and is consulted by the file loader, the catalog builder, AND the modal migration. This must be shared infrastructure, not three private fixes.
- _How to answer:_ Cross-team decision establishing a single name-alias/migration registry consulted at file load, catalog generation, and modal migration; define its format and the policy for surfacing unknown/renamed names (warn-and-keep vs silent). Enumerate the Step-D renames (code investigation) to seed it before Axis 4 renames anything.
- _Answerable by:_ `cross-team-decision`

**X12. Does the cumulative load of Axis 2 (inject-new context-scoped bindings multiplying binding count, Axis 2-Q11), Axis 4 (mode-pack layers + Helix emitting ExtendSelection on every keystroke against N-way selections, Axis 4-Q13), and Axis 6 (unresolved platform keystrokes needing per-binding resolution on the hot path, Axis 6-Q4) push the matcher's O(n) linear scan with derived PartialEq over all six Keystroke fields on every keypress (matcher.rs:324-337) past frame budget — making the trie/ambiguity work (R4) NOT the optional, deferrable item the roadmap calls it but a shared prerequisite?**

- _Axes:_ Axis 2, Axis 3, Axis 4, Axis 6
- _Why it matters:_ R4 is sequenced as optional/deferred behind cheaper prereqs (report §7), and Axis 3-Q8 even questions whether a trie beats the current scan at a few hundred bindings. But three axes independently grow either the binding count (injected overrides, mode-packs) or the per-binding cost (platform resolution), and the matcher runs once per responder-chain entry per keystroke. If the combined effect crosses budget, R4 must move earlier and becomes shared, not optional.
- _How to answer:_ Benchmark spike: measure current n and per-keystroke scan cost, then project under (a) realistic injected-override counts, (b) a vim mode-pack layer, and (c) inline platform resolution. Establish the binding-count threshold where the linear scan breaks budget and decide whether R4 stays deferred or becomes a Phase-2 prerequisite.
- _Answerable by:_ `prototype-spike`

**X13. Should a single full-keymap resolution-snapshot harness — capturing (context, keystroke, OS) → winning action over the real ~265 registration sites at startup (Axis 3-Q20) — be built as shared test infrastructure BEFORE any axis refactors, so Axis 2 (scoped override hits only its scope), Axis 3 (precedence/unbind), Axis 4 (modal contexts don't change non-modal resolution), Axis 5 (catalog completeness), and Axis 6 (other-platform resolution) all diff against the same golden baseline — rather than each axis writing isolated unit fixtures that can't prove 'no unrelated binding changed winner'?**

- _Axes:_ Axis 2, Axis 3, Axis 4, Axis 5, Axis 6
- _Why it matters:_ Today's coverage is near-zero for resolution (matcher_tests.rs has 3 tests with no shadowing/precedence/unbind coverage; context_tests.rs ~1 test). Each axis refactors the same resolver, but a per-axis fixture can only prove its own case, not the global invariant that every other binding still resolves identically. A shared OS-and-context-parameterized snapshot is the only regression net that catches cross-axis breakage and also gives Axis 6 its missing target-OS injection seam (Axis 6-Q12: OperatingSystem::get() has no native override).
- _How to answer:_ Build the snapshot harness once (introduce the test-only target-OS seam for get(), walk all registrations, serialize the resolution table) and adopt it as the mandatory before/after diff for every axis. This is a test-strategy investment decision plus the engineering to add the OS-injection seam — agree on it as shared groundwork before Phase-2 work starts.
- _Answerable by:_ `cross-team-decision`

---

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

## Axis 6 — Cross-cutting foundation (platform-in-data-model + dependency spine)

**End state:** a single build can show/edit both mac and linux/windows bindings (R5) — prerequisite for any cross-platform binding editor; plus the dependency spine that sequences the whole initiative.

> **Killer question:** Two facts are now code-verified: (a) OperatingSystem::get() is compile-time-fixed with no native runtime override (platform/mod.rs:668-683; wasm OnceLock has no public setter, wasm.rs:8), and (b) the platform builders resolve-and-DISCARD the inactive platform at registration — EditableBinding::new starts at Trigger::Empty (keymap.rs:660), with_mac/with_linux noop on the other OS (keymap.rs:688-713), new_per_platform picks one string at build (keymap.rs:502-507) — so the non-current platform's binding does not exist as runtime data. Given this, R5's "resolve only at display via get()" cannot show the other platform at all. So which canonical unresolved model do we commit to: (A) a stored {mac, other} keystroke pair carried through registration — which expresses the majority full-keystroke-divergent sites (the 157 with_mac/with_linux and 181 cmd_or_ctrl_shift cases like cmd-[ vs ctrl-shift-{) but touches ~330 registration sites AND requires Axis 2's structured record file schema; or (B) a cmdorctrl modifier on Keystroke that auto-synthesizes the other side — cheap and flat-string compatible but provably unable to represent the dominant full-keystroke-divergence case — and does the chosen model thread an explicit target-platform parameter (not get()) through parse, resolve, displayed(), the matcher, and the validators?

### Scope/requirements

**A6-Q1. Does 'show/edit both mac and linux/windows bindings' (R5 end state) require full EDITING of the non-current platform's binding, or only read-only DISPLAY of it alongside an editable current-platform binding?**

- _Why it matters:_ Editing a platform you are not running on means the matcher never exercises that binding locally, the edit-path validators (R10 / A6-Q13) must run for an absent platform, and the user cannot test their change — materially harder and riskier than read-only display. The doc must fix this boundary before any UI or schema work.
- _How to answer:_ Product decision: define whether the cross-platform editor is view-only for the inactive platform (lower risk, ships sooner) or fully editable (requires platform-parameterized validation, capture, and conflict-check). Cross-reference Axis 5 validators (R10) and A6-Q17.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Conflates 'show both' with 'edit both'; editing a binding you cannot trigger or test locally is a much harder and riskier requirement that pulls in platform-parameterized validation and conflict detection.

**A6-Q2. There is a SECOND keystroke-persistence surface beyond keybindings.yaml: global hotkey / QuakeMode bindings stored in settings.toml as QuakeModeSettings.keybinding: Option<Keystroke> (settings/mod.rs:334-338) and slash-command activation via PerPlatformKeystroke (search/slash_command_menu/static_commands/bindings.rs:17). Does R5's 'platform in the data model' cover these surfaces, or only the keymap/keybindings.yaml?** _(added-by-critic)_

- _Why it matters:_ If platform-in-data-model touches the Keystroke type itself, these settings-stored keystrokes are affected (and are the cloud-sync consumers from A6-Q3). If the cross-platform editor is supposed to show/edit ALL bindings a user sees, the global hotkey must participate too — but it lives in a different file, a different settings struct, and uses a different per-platform construct (PerPlatformKeystroke, keymap.rs:488-493). Leaving it out makes 'edit both platforms' partial; including it widens scope into settings serialization.
- _How to answer:_ Read QuakeModeSettings (settings/mod.rs:334-358), PerPlatformKeystroke usages (slash_command bindings.rs:17, keymap.rs:497-508), and decide (product + code) whether R5's scope is keymap-only or all Keystroke-backed bindings; reconcile with A6-Q3's serialization impact.
- _Answerable by:_ `user-product-decision`
- _Adversarial angle:_ Assumes keybindings.yaml is the only place keystrokes persist; QuakeMode/global-hotkey keystrokes live in settings.toml with their own PerPlatformKeystroke path and are likely the cloud-synced Keystroke consumers, so the platform model and the editor scope must explicitly include or exclude them.

### Design decision

**A6-Q3. Which canonical unresolved Keystroke representation do we commit to: (a) add a cmd_or_ctrl: bool onto the flat Keystroke struct (keymap.rs:320-328) — note this changes the derived Serialize/Hash/PartialEq used by 40+ consumers incl. synced settings; (b) a stored {mac, other} Keystroke (or Vec<Keystroke>) pair at the Trigger level (keymap.rs:43-49) that survives registration; or (c) a ModifierSet/PrimaryModifier enum? Because the builders discard the inactive platform at registration (EditableBinding::new=Trigger::Empty keymap.rs:660; with_mac/with_linux noop keymap.rs:688-713), only a model that CARRIES both sides can satisfy R5's 'show both'.** _(sharpened)_

- _Why it matters:_ This single type choice fixes the rest of the axis: the matcher (matcher.rs:324-337 derived PartialEq scan), the file schema, displayed(), the validators, and how many of the ~330 platform-divergent registration sites must change. Option (a) cannot express full-keystroke divergence (the majority case); option (b) can but doubles storage, forces a resolution step, requires a structured file schema (Axis 2), and a re-registration migration. Picking wrong invalidates every downstream design decision.
- _How to answer:_ Prototype each variant against Keystroke (keymap.rs:320), Trigger (keymap.rs:43-49), normalized()/displayed() (keymap.rs:970,998), matcher push_keystroke (matcher.rs:307-346), and the registration builders (keymap.rs:688-726, 497-508); weigh against the audited site distribution from A6-Q6.
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ The report frames 'CmdOrCtrl modifier OR a {mac,other} pair' as interchangeable; they are not — only the pair expresses bindings whose KEY (not just modifier) differs, and only a model carried through REGISTRATION (not parse-time) can show a platform the build is not running on, since the builders currently discard it.

### Code fact to verify

**A6-Q4. What exactly consumes Keystroke's derived serde (keymap.rs:320 derives Serialize/Deserialize/Hash/PartialEq) beyond the normalized()-string paths? Specifically: does settings cloud-sync serialize QuakeModeSettings.keybinding: Option<Keystroke> (settings/mod.rs:334-338, which derives Serialize/Deserialize AND settings_value) via the struct form or via to_file_value() (the normalized string, keymap.rs:345-354)? The keymap.rs:333 comment states 'Serde continues to use the default struct form for cloud sync and other in-memory consumers.'** _(sharpened)_

- _Why it matters:_ If any persisted/synced format serializes Keystroke field-by-field (struct serde), then adding a cmd_or_ctrl field (A6-Q2 option a) is a breaking, migration-requiring change to SYNCED SETTINGS — not just keybindings.yaml. The draft assumed 'keybindings aren't cloud-synced (keybindings.rs:1108) → safe', but Keystroke is a shared type used by QuakeMode/global-hotkey settings and 40+ ui_components/menu/onboarding sites, so the blast radius extends past keybindings into settings sync.
- _How to answer:_ Trace how SettingsManager serializes QuakeModeSettings for the settings file vs cloud sync (does it call SettingsValue::to_file_value or serde_json on the struct?); grep struct-serde consumers of Keystroke across ui_components, platform/menu.rs, onboarding, settings/import; confirm keybindings.yaml itself stores PersistedTrigger(String) via normalized() (keyboard.rs:174-187) so it is insulated, but settings are not.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes Keystroke is a private in-memory type and that 'keybindings not synced' makes mutation safe; it is actually wired into settings_value, schema_gen, AND a cloud-synced settings struct (QuakeModeSettings), so changing the struct silently breaks a serialized/synced format.

**A6-Q5. There are FOUR platform-divergence mechanisms, not three: (1) cmdorctrl parse tokens — 140 sites; (2) cmd_or_ctrl_shift() which does a FULL-keystroke swap cmd-[ → ctrl-shift-{ — 181 sites (bindings.rs:863-888); (3) EditableBinding::with_mac/with_linux_or_windows arbitrary per-OS keystroke — 157 sites (keymap.rs:688-713); (4) FixedBinding::new_per_platform {mac, linux_and_windows} — 13 sites (keymap.rs:497-508). Audit how many of all four are pure cmd↔ctrl swaps vs genuine key/chord divergence, then choose the canonical model and define how the other three lower into it.** _(sharpened)_

- _Why it matters:_ The draft (and report) framed cmdorctrl as the platform story and pegged it at ~50 sites; the reality is 140 cmdorctrl PLUS 181 cmd_or_ctrl_shift (which the draft missed entirely and which is itself a full-keystroke swap) PLUS 157 with_mac/with_linux — the dominant case is arbitrary per-OS keystrokes that a cmdorctrl-only model CANNOT represent. The canonical representation must be chosen against the real ~490-site distribution, not the report's emphasis, or it cannot store the majority of bindings.
- _How to answer:_ Re-run the census (grep counts: cmdorctrl 140, cmd_or_ctrl_shift 181, with_mac 101 + with_linux 56, new_per_platform 13) and sample each bucket to classify pure-modifier-swap vs full-keystroke divergence; pick the representation covering the majority and specify a desugaring/codemod for the other three.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes cmdorctrl is the whole platform story and undercounts it 3x; the dominant mechanisms (with_mac at 157 and cmd_or_ctrl_shift at 181) allow arbitrary per-OS keystrokes that cmdorctrl cannot express.

### Edge case/failure mode

**A6-Q6. Can the data model express a binding whose mac and non-mac sides differ in the KEY itself, not just the primary modifier — the documented cmd_or_ctrl_shift pattern 'cmd-[' (mac) vs 'ctrl-shift-{' (other) at bindings.rs:854-861,863-888 — and can such a pair be displayed and conflict-checked on a platform where only one side was ever constructed at registration?** _(sharpened)_

- _Why it matters:_ This is not a rare edge: it is the 181-site cmd_or_ctrl_shift mechanism. If the model only handles cmd↔ctrl substitution, these sites cannot be stored, displayed, or edited cross-platform, and R6 conflict detection cannot reason about the inactive platform's chord. This bounds what 'edit both platforms' can actually mean.
- _How to answer:_ Read cmd_or_ctrl_shift (bindings.rs:863-888) and sample with_mac/with_linux call sites; verify how often the two sides differ beyond the modifier (shift addition, bracket↔brace, different key); test the chosen representation (A6-Q2) against this case and define how the synthesized side is derived or stored.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Naively assumes platforms differ only by swapping cmd for ctrl; cmd_or_ctrl_shift (the single largest mechanism) swaps the entire chord including the key, and the noop builders mean the inactive chord was never parsed into a Keystroke.

**A6-Q7. Keystroke carries SEPARATE cmd AND meta fields (keymap.rs:325-326); normalized() emits 'meta-' and displayed() renders cmd as 'Logo' on non-mac (keymap.rs:984-1030), yet cmdorctrl maps only to cmd-or-ctrl, never meta/super. When we synthesize the linux/windows view of a mac cmd-X binding, do we produce ctrl-X even though real Linux bindings legitimately use meta/super — and is that mapping lossy?**

- _Why it matters:_ If {mac, other} resolution conflates the Logo/super (meta) key with ctrl, the cross-platform editor will mis-display or mis-store bindings that actually use meta on Linux, producing wrong or unmatchable shortcuts. The model must define how meta participates so the platform mapping is not silently lossy.
- _How to answer:_ Read the Keystroke modifier fields (keymap.rs:320-328), normalized()/displayed() cmd-vs-meta handling (keymap.rs:970-1030), and grep linux bindings using meta/super; decide whether the unresolved model maps cmd↔ctrl only or also accounts for meta/super as a distinct primary modifier.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes cmd maps cleanly to ctrl on Linux; ignores the separate meta/super (Logo) modifier that real Linux bindings use, making any cmd→ctrl-only synthesis lossy.

**A6-Q8. For multi-keystroke chords, can platform divergence occur PER-KEYSTROKE within the chord, or only as a whole-chord swap? cmdorctrl resolves per token inside Keystroke::parse (keymap.rs:914-919) so a chord like 'cmdorctrl-k cmdorctrl-d' diverges per-keystroke, whereas with_mac/with_linux swap the entire space-separated string (keymap.rs:715-726). How does the chosen unresolved model and the on-disk string (PersistedTrigger space-join, keyboard.rs:180) represent a chord where only the SECOND keystroke differs across platforms?** _(added-by-critic)_

- _Why it matters:_ If the model stores divergence at the Trigger/whole-chord level (a {mac,other} pair of Vec<Keystroke>), it forces duplicating the entire chord even when one keystroke differs, and the matcher's per-keystroke Pending buffer (matcher.rs:313-337) must still resolve each element. If it stores per-Keystroke, chord encoding and conflict-checking must compose per element. Getting this wrong makes chords either unrepresentable or silently mis-resolved.
- _How to answer:_ Read Keystroke::parse (keymap.rs:906-968), with_key_binding chord split (keymap.rs:719-724), PersistedTrigger round-trip (keyboard.rs:176-211), and matcher pending logic (matcher.rs:313-337); test the chosen model against a chord with mixed per-keystroke platform divergence.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes platform divergence is a single-keystroke or whole-chord concern; chords can diverge at one element only, which a whole-chord {mac,other} pair represents wastefully and a per-keystroke model must compose correctly.

### Dependency/sequencing

**A6-Q9. Can platform-in-data-model ship on the current flat HashMap<String, PersistedTrigger> file (keyboard.rs:169, single normalized string), or is it gated behind Axis 2's record-based schema (R3b {name, trigger, context?, platform?}) because a flat string can carry a 'cmdorctrl-X' token but cannot express a full {mac:'cmd-[', other:'ctrl-shift-{'} pair?**

- _Why it matters:_ The end-goals doc labels Axis 6 'independent'. But a cmdorctrl token fits the flat string (Keystroke::parse already handles it, keymap.rs:914-919) while the full-keystroke pair — the majority case (A6-Q6) — needs a structured record, pulling in Axis 2. So R5's DEPTH determines whether it is independent or downstream of Phase 2, reordering the dependency spine.
- _How to answer:_ Read keyboard.rs:167-213 (CustomKeybindings/PersistedTrigger) and R3b in the report (§3); determine the minimum file schema for each candidate model from A6-Q2, and whether a cmdorctrl-only Phase-1 slice can ship on the flat string with full-pair deferred to the Axis 2 record schema.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Takes the doc's 'independent' label at face value; the flat string schema can carry cmdorctrl but not a full {mac,other} pair, so the expressive version of R5 depends on the Axis 2 schema it was claimed to be independent of.

**A6-Q10. Given that R5 touches only Keystroke/Trigger/parse/displayed/matcher/validators (verified: no layer or ContextPredicate machinery), and that its cmdorctrl form fits the flat file while its full-pair form needs Axis 2's schema (A6-Q9), should R5 be SPLIT — a cmdorctrl-modifier slice shipped in Phase 1 alongside Axis 1, and the full {mac,other} pair + cross-platform editor deferred to Phase 2 alongside the record schema — rather than treated as one monolithic 'independent stretch'?** _(sharpened)_

- _Why it matters:_ The report's 'one missing primitive underlies all three goals' narrative is about layer/mode/context-scope and explicitly lists platform as separate/independent; platform divergence is genuinely orthogonal to the engine refactor. Deciding split-vs-monolith and parallel-vs-serial changes whether a shippable cross-platform foundation lands early or is over-serialized behind the engine work, affecting the whole initiative timeline.
- _How to answer:_ Cross-read report §6/§7 and the end-goals Dependency Spine against the symbols R5 actually touches; with initiative owners, decide whether to carve a Phase-1 cmdorctrl slice (de-risks early) from a Phase-2 full-pair editor, and who owns each.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Accepts the tidy 'everything funnels through one primitive' framing OR the flat 'independent' label; the truth is in between — R5 is orthogonal to layers/context but its expressive form is coupled to the Axis 2 file schema, so a single sequencing label is wrong.

**A6-Q11. R6 conflict detection (Axis 5) keys ConflictMap on the bare Keystroke and evaluates context against the CURRENT context set. When the editor displays/edits the INACTIVE platform's bindings, how does conflict detection work for that platform — given it cannot resolve the inactive side via get(), cannot evaluate that platform's runtime context, and two mac bindings may collide only after mac resolution? Does R5 require R6 to become platform-parameterized as a hard prerequisite?** _(added-by-critic)_

- _Why it matters:_ If 'edit both platforms' (A6-Q8) includes editing, the user must see honest conflicts for the platform they are NOT on — but the conflict map and context eval are inherently current-OS. Either the cross-platform editor ships without conflict feedback for the inactive platform (a truthfulness regression against the North Star), or R6 must take a target-OS parameter, coupling Axis 6 to Axis 5's Phase-2 work and reordering the spine.
- _How to answer:_ Cross-read R6 (report §4) and the ConflictMap keyed on Keystroke (settings_view/keybindings.rs:106) against the chosen resolution model (A6-Q2); decide whether conflict detection is in-scope for the inactive platform and whether R6 must be platform-parameterized before R5 can claim 'edit both'.
- _Answerable by:_ `cross-team-decision`
- _Adversarial angle:_ Assumes display/edit of the other platform is self-contained; truthful conflict feedback for the inactive platform requires resolving and context-evaluating a platform the build is not running on, which today's current-OS ConflictMap cannot do — silently coupling R5 to R6.

### Migration/back-compat

**A6-Q12. keybindings.yaml persists normalized RESOLVED strings — 'cmd-d' on mac, 'ctrl-d' on linux (keyboard.rs:176-187, round-tripped via Keystroke::normalized). When platform-in-data-model lands, how do we (a) emit the unresolved form to disk ('cmdorctrl-d' token, which Keystroke::parse already round-trips at keymap.rs:914-919, vs a structured {mac,other} record), and (b) read existing resolved files WITHOUT misinterpreting a mac-written 'cmd-d' as a deliberate mac-only override?**

- _Why it matters:_ Today a colleague's mac config dropped on Linux contains literal 'cmd-d', which on Linux fails is_binding_cross_platform and resolves to an unusable binding — the Axis 1 portability promise ('drop in a colleague's config and it just works') is unmet. The legacy-read rule decides whether existing users silently lose bindings or get them reinterpreted, and whether the file becomes truly portable.
- _How to answer:_ Read keyboard.rs:167-213 (PersistedTrigger From/TryFrom round-trip) and Keystroke::parse cmdorctrl handling (keymap.rs:914-919); decide the on-disk encoding and a back-compat read rule (e.g. treat a bare resolved 'cmd-X'/'ctrl-X' as platform-agnostic-by-default unless explicitly tagged mac-only) and a migration/upgrade pass.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes the existing file is already platform-portable; in fact it stores OS-resolved strings, so naive reuse makes mac configs unusable on Linux and conflates 'happens to be cmd' with 'intentionally mac-only'.

**A6-Q13. is_binding_cross_platform (bindings.rs:918-933) currently runs only as the DEBUG default validator (lib.rs:1395, set_default_binding_validator is #[cfg(debug_assertions)]) and merely flags: on non-mac, keystroke.cmd == true → invalid (it returns Yes immediately on mac). Once keystrokes are unresolved, what is the validator's new contract — is a bare cmdorctrl/{mac,other} pair auto-valid, and does a mac-side cmd with NO explicit other-platform mapping become a hard failure rather than today's silent pass-on-mac?** _(sharpened)_

- _Why it matters:_ Platform-in-data-model redefines 'cross-platform valid'. Today the check is one-directional (only catches stray cmd on non-mac) and debug-only; if the model demands an explicit other-platform mapping, formerly-silent bindings must be flagged or auto-defaulted, and the rule must move to the release edit path (R10) so the editor can warn before persisting an unbound-on-one-platform shortcut.
- _How to answer:_ Read is_binding_cross_platform (bindings.rs:918-933), is_pty_non_compliant_binding_allowed (bindings.rs:909-914), and validate_bindings (matcher.rs:159-203); define the post-change validity rule for bare cmdorctrl, full {mac,other} pairs, and single-platform-only bindings, and whether it gates registration or the edit path (ties to R10).
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes the existing validator carries over unchanged; it is debug-only, one-directional (only cmd-on-non-mac), and the unresolved model changes the definition of 'cross-platform valid', potentially turning today's silent passes into failures.

### Testing/validation

**A6-Q14. Integration/unit tests assert keystrokes via with_keystrokes(['cmdorctrl-up']) / cmd_or_ctrl_shift() which resolve to the CI build's OS, and there is NO native override for OperatingSystem::get() (only the wasm OnceLock at wasm.rs:8). What test-only target-OS injection seam do we introduce so a single-OS CI runner can assert that the OTHER platform's binding resolves, displays, conflict-checks, and validates correctly?** _(sharpened)_

- _Why it matters:_ Without an injectable target OS, the cross-platform behavior R5 introduces is fundamentally untestable on a single-OS runner — the same missing primitive as the killer question. The seam (e.g. a #[cfg(test)] settable OnceLock/override or a target-OS parameter threaded through resolve/display) must be designed alongside the feature, not bolted on after, and must be the SAME seam the editor uses (not a test-only fork).
- _How to answer:_ Review existing cmdorctrl test usages (crates/integration test helpers; keymap_tests.rs) and the wasm OnceLock pattern (wasm.rs:7-59); spike a test-only native target-OS injection and confirm whether the production cross-platform path reuses it or a separate explicit target-OS parameter.
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Assumes existing cmdorctrl tests already cover cross-platform behavior; they only ever exercise the build's own OS via get() and cannot validate the other platform's resolution, display, or conflict-check.

### UX/surface behavior

**A6-Q15. displayed() (keymap.rs:998-1030) hardcodes ⌘/⌃/⇧ vs Ctrl/Alt/Shift/Logo by OperatingSystem::get().is_mac() and is called across 21 files. Will the cross-platform editor add a separate displayed_for(target_os) used only by the settings/catalog surfaces, leaving all other call sites on the current-OS path — or will displayed() itself gain a target-OS parameter (touching all 21 callers)?**

- _Why it matters:_ Threading a target platform into displayed() touches 21 callers and risks regressing every shortcut hint in the app (tooltips, menus, onboarding callouts); a parallel display function confines the change to the editor. This decides the surface area, blast radius, and review risk of the display half of R5.
- _How to answer:_ Read displayed() (keymap.rs:998-1030, note cmd renders as 'Logo' on non-mac) and enumerate its 21 call-site files; decide between a new platform-parameterized display path scoped to the editor vs modifying the shared signature.
- _Answerable by:_ `code-investigation`
- _Adversarial angle:_ Assumes display is a single localized change; displayed()'s is_mac() branching is replicated implicitly across 21 surfaces, so 'just show the other platform' is a wide refactor unless scoped to a parallel function.

### Performance/scale

**A6-Q16. matcher.push_keystroke (matcher.rs:307-346) does an O(n) linear scan over all bindings on EVERY keypress, comparing Vec<Keystroke> via starts_with using DERIVED PartialEq over all six fields (matcher.rs:324-337). With unresolved storage, where does resolution happen — inline per-binding on the hot path, or once at registration into a current-OS resolved cache (with the unresolved form kept only for the display/editor surface)?**

- _Why it matters:_ A resolved key event can no longer be compared directly against an unresolved stored binding (the field sets differ). Either every scan pays resolution per keystroke per binding on the dispatch hot path, or we maintain a parallel resolved copy for matching plus an unresolved copy for display. This decides runtime dispatch cost and whether the matcher must change at all.
- _How to answer:_ Read matcher.rs:307-346 and bindings() (keymap.rs:454-464); spike a resolve-at-registration cache vs inline resolution and measure scan cost against the hundreds of registered bindings; confirm the resolved cache stays correct under Tracked<EditableBinding> custom-trigger updates (keymap.rs:422-433).
- _Answerable by:_ `prototype-spike`
- _Adversarial angle:_ Assumes 'resolve at match time' is free; it sits on the per-keypress linear-scan hot path and must not regress dispatch latency, and the derived PartialEq means an unresolved binding will never match a resolved key event directly.

<details><summary>Already settled by the report/code — pruned as non-questions (1)</summary>

- ~~Is OperatingSystem::get() truly the only resolution oracle, and is it compile-time-fixed with no native runtime override — meaning a single Linux build literally cannot ask 'what is the mac binding' via get()? (A6-Q1)~~ — Answered by code during this review. OperatingSystem::get() (platform/mod.rs:668-683) is a compile-time cfg_if over target_family/target_os with no parameter and no setter; the only non-compile-time path is wasm::current_platform() which reads a PRIVATE static OnceLock<OperatingSystem> (wasm.rs:8) initialized once from the browser user agent, with no public override API. Confirmed: a single native build cannot represent the platform it is not running on via get(). The verification is complete; the surviving DESIGN implication (must thread an explicit target-platform parameter) is now folded into the killer question and into the sharpened A6-Q2, so keeping Q1 as an open question is redundant.

</details>

---

## Summary of effort

- Axes interrogated: **6/6**
- Per-axis design-readiness questions: **102**
- Cross-axis / sequencing questions: **13**
- Method: 6 adversarial generators -> 6 adversarial critics (prune/sharpen/fill) -> 1 cross-axis synthesis, all grounded in the architecture report + live code.
