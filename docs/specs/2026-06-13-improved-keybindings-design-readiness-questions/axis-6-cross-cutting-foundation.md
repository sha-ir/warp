[← Back to index](./README.md)

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

