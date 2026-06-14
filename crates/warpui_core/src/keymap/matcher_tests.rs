use super::*;
use crate::keymap::macros::*;

#[test]
fn test_matcher() -> anyhow::Result<()> {
    #[derive(Debug, PartialEq)]
    enum Action {
        A(String),
        B,
        AB,
    }

    let keymap = Keymap::new(vec![
        FixedBinding::new("a", Action::A("b".into()), id!("a")),
        FixedBinding::new("b", Action::B, id!("a")),
        FixedBinding::new("a b", Action::AB, id!("a") | id!("b")),
    ]);

    let mut ctx_a = Context::default();
    ctx_a.set.insert("a");

    let mut ctx_b = Context::default();
    ctx_b.set.insert("b");

    let mut matcher = Matcher::new(keymap);

    let view_id = EntityId::new();

    // Basic match
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b".into())
    );

    // Multi-keystroke match
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AB
    );

    // Failed matches don't interfere with matching subsequent keys
    assert!(matcher.test_keystroke("x", view_id, &ctx_a).is_none());
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b".into())
    );

    // Pending keystrokes are cleared when the context changes
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::B
    );

    let mut ctx_c = Context::default();
    ctx_c.set.insert("c");

    // Pending keystrokes are maintained per-view
    let view_id1 = EntityId::new();
    let view_id2 = EntityId::new();
    assert_ne!(view_id1, view_id2);
    assert!(matcher.test_keystroke("a", view_id1, &ctx_b).is_none());
    assert!(matcher.test_keystroke("a", view_id2, &ctx_c).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id1, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AB
    );

    Ok(())
}

#[test]
fn test_editable_binding_matching() {
    #[derive(Debug, PartialEq)]
    enum Action {
        A(&'static str),
        B,
        AOrB,
    }

    let mut keymap = Keymap::default();
    use crate::keymap::macros::*;
    keymap.register_editable_bindings([
        EditableBinding::new("a", "Action for A", Action::A("b"))
            .with_key_binding("a")
            .with_context_predicate(id!("a")),
        EditableBinding::new("b", "Action for B", Action::B)
            .with_key_binding("b")
            .with_context_predicate(id!("a")),
        EditableBinding::new("a_or_b", "Action for A or B", Action::AOrB)
            .with_key_binding("a b")
            .with_context_predicate(id!("a") | id!("b")),
    ]);

    let mut ctx_a = Context::default();
    ctx_a.set.insert("a");

    let mut ctx_b = Context::default();
    ctx_b.set.insert("b");

    let mut matcher = Matcher::new(keymap);

    let view_id = EntityId::new();

    // Basic match
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b"),
    );

    // Multi-keystroke match
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AOrB
    );

    // Failed matches don't interfere with matching subsequent keys
    assert!(matcher.test_keystroke("x", view_id, &ctx_a).is_none());
    assert_eq!(
        matcher
            .test_keystroke("a", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::A("b")
    );

    // Pending keystrokes are cleared when the context changes
    assert!(matcher.test_keystroke("a", view_id, &ctx_b).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id, &ctx_a)
            .unwrap()
            .as_action::<Action>(),
        &Action::B
    );

    let mut ctx_c = Context::default();
    ctx_c.set.insert("c");

    // Pending keystrokes are maintained per-view
    let view_id1 = EntityId::new();
    let view_id2 = EntityId::new();
    assert_ne!(view_id1, view_id2);
    assert!(matcher.test_keystroke("a", view_id1, &ctx_b).is_none());
    assert!(matcher.test_keystroke("a", view_id2, &ctx_c).is_none());
    assert_eq!(
        matcher
            .test_keystroke("b", view_id1, &ctx_b)
            .unwrap()
            .as_action::<Action>(),
        &Action::AOrB
    );
}

#[test]
fn test_bindings_for_context() {
    #[derive(Debug)]
    enum Action {
        A,
        B,
        C,
    }
    let keymap = Keymap::new(vec![
        FixedBinding::new("a", Action::A, id!("a")),
        FixedBinding::new("b", Action::B, id!("b")),
        FixedBinding::new("c", Action::C, id!("b")),
    ]);
    let matcher = Matcher::new(keymap);

    let mut ctx_a = Context::default();
    ctx_a.set.insert("a");

    let mut ctx_b = Context::default();
    ctx_b.set.insert("b");

    // Getting bindings for the 'a' context returns a single result
    let ctx_a_bindings = matcher
        .bindings_for_context(ctx_a)
        .filter_map(|bind| match bind.trigger {
            Trigger::Keystrokes(keys) => {
                assert_eq!(keys.len(), 1);
                Some(keys[0].normalized())
            }
            _ => None,
        })
        .collect::<Vec<_>>();

    assert_eq!(ctx_a_bindings.len(), 1);
    assert_eq!(ctx_a_bindings, vec!["a"]);

    // Getting bindings for the 'b' context returns two results, in the reverse order they
    // added, so the "c" binding first followed by the "b" binding
    let ctx_b_bindings = matcher
        .bindings_for_context(ctx_b)
        .filter_map(|bind| match bind.trigger {
            Trigger::Keystrokes(keys) => {
                assert_eq!(keys.len(), 1);
                Some(keys[0].normalized())
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(ctx_b_bindings, vec!["c", "b"]);
}

// ----------------------------------------------------------------------------
// X9 spike: Unbound tombstone kernel
// ----------------------------------------------------------------------------

fn assert_unbound(result: MatchResult, path: &str) {
    assert!(
        matches!(result, MatchResult::Unbound),
        "{path}: expected MatchResult::Unbound (tombstone short-circuit)"
    );
}

fn assert_is_action(result: MatchResult, path: &str) {
    assert!(
        matches!(result, MatchResult::Action(_)),
        "{path}: expected MatchResult::Action (baseline, before tombstone)"
    );
}

fn expect_action(result: MatchResult, path: &str) -> Arc<dyn Action> {
    match result {
        MatchResult::Action(action) => action,
        _ => panic!("{path}: expected MatchResult::Action"),
    }
}

/// X9 (A) — keystroke path: an injected Unbound tombstone on `ctrl-c` suppresses a
/// SEPARATE lower-precedence `ctrl-c` binding through `push_keystroke`, returning
/// `MatchResult::Unbound` via the ONE shared `resolve_matched_binding` helper.
#[test]
fn test_tombstone_suppresses_keystroke_via_shared_helper() {
    #[derive(Debug, PartialEq)]
    enum Action {
        Copy,
    }

    let keymap = Keymap::new(vec![FixedBinding::new("ctrl-c", Action::Copy, always!())]);
    let mut matcher = Matcher::new(keymap);
    let view_id = EntityId::new();
    let ctx = Context::default();

    // Baseline: ctrl-c resolves to the lower-precedence fixed Copy action.
    assert_is_action(
        matcher.push_keystroke(Keystroke::parse("ctrl-c").unwrap(), view_id, &ctx),
        "push_keystroke baseline",
    );

    // Inject an Unbound tombstone on ctrl-c at the highest precedence.
    matcher.inject_binding(
        EditableBinding::new("unbind_copy", "", Action::Copy)
            .with_key_binding("ctrl-c")
            .with_context_predicate(always!())
            .as_tombstone(),
    );

    // Now ctrl-c is suppressed: Unbound, NOT the separate lower-precedence binding.
    assert_unbound(
        matcher.push_keystroke(Keystroke::parse("ctrl-c").unwrap(), view_id, &ctx),
        "push_keystroke after tombstone",
    );
}

/// X9 (A) — standard path: the SAME shared helper routes `match_standard` to
/// `Unbound` when a tombstone outranks a separate lower-precedence standard binding.
#[test]
fn test_tombstone_suppresses_standard_via_shared_helper() {
    #[derive(Debug, PartialEq)]
    enum Action {
        Close,
    }

    let keymap = Keymap::new(vec![FixedBinding::standard(
        StandardAction::Close,
        Action::Close,
        always!(),
    )]);
    let mut matcher = Matcher::new(keymap);
    let ctx = Context::default();

    // Baseline.
    assert_is_action(
        matcher.match_standard(StandardAction::Close, &ctx),
        "match_standard baseline",
    );

    matcher.inject_binding(
        EditableBinding::new("unbind_close", "", Action::Close)
            .with_standard_action(StandardAction::Close)
            .with_context_predicate(always!())
            .as_tombstone(),
    );

    assert_unbound(
        matcher.match_standard(StandardAction::Close, &ctx),
        "match_standard after tombstone",
    );
}

/// X9 (A) — custom path (PRIMARY trigger) plus the SECOND macOS-menu surface:
/// a custom-triggered tombstone suppresses both `match_custom` AND
/// `binding_for_custom_action_in_context`.
#[test]
fn test_tombstone_suppresses_custom_primary_and_second_surface() {
    #[derive(Debug, PartialEq)]
    enum Action {
        Real,
    }
    const TAG: CustomTag = 7;

    // Register the fixed binding via the Matcher so `fixed_custom_action_bindings`
    // (the dual list read by the second surface) is populated.
    let mut matcher = Matcher::new(Keymap::default());
    matcher.register_fixed_bindings([FixedBinding::custom(TAG, Action::Real, "Real", always!())]);
    let ctx = Context::default();

    // Baseline: both surfaces resolve the action.
    assert_is_action(matcher.match_custom(TAG, &ctx), "match_custom baseline");
    assert!(
        matcher
            .binding_for_custom_action_in_context(TAG, &ctx)
            .is_some(),
        "second-surface baseline should resolve"
    );

    matcher.inject_binding(
        EditableBinding::new("unbind_real", "", Action::Real)
            .with_custom_action(TAG)
            .with_context_predicate(always!())
            .as_tombstone(),
    );

    // match_custom (primary `Trigger::Custom` arm) short-circuits to Unbound.
    assert_unbound(
        matcher.match_custom(TAG, &ctx),
        "match_custom after tombstone",
    );
    // SECOND SURFACE: macOS-menu lookup now returns None (action is unbound).
    assert!(
        matcher
            .binding_for_custom_action_in_context(TAG, &ctx)
            .is_none(),
        "second surface must honor the tombstone and return None"
    );
}

/// X9 (A) — custom path via the `original_trigger` DUAL-CHECK (matcher.rs:370-373,
/// the "match_custom leak"): a tombstone whose current trigger was overridden to a
/// keystroke still suppresses the custom action through the SAME shared helper, and
/// the second surface honors it too.
#[test]
fn test_tombstone_suppresses_custom_via_original_trigger_dual_check() {
    #[derive(Debug, PartialEq)]
    enum Action {
        Real,
    }
    const TAG: CustomTag = 9;

    let mut matcher = Matcher::new(Keymap::default());
    matcher.register_fixed_bindings([FixedBinding::custom(TAG, Action::Real, "Real", always!())]);
    let ctx = Context::default();

    assert_is_action(matcher.match_custom(TAG, &ctx), "match_custom baseline");

    // Inject a custom-triggered tombstone, then override its trigger to a keystroke.
    // `as_lens` then exposes trigger=Keystrokes, original_trigger=Some(Custom(TAG)),
    // so only the dual-check arm can match TAG.
    matcher.inject_binding(
        EditableBinding::new("unbind9", "", Action::Real)
            .with_custom_action(TAG)
            .with_context_predicate(always!())
            .as_tombstone(),
    );
    matcher.set_custom_trigger(
        "unbind9".to_string(),
        Trigger::Keystrokes(vec![Keystroke::parse("z").unwrap()]),
    );

    // Primary arm no longer matches (trigger is now a keystroke); the original_trigger
    // dual-check matches and routes through the SAME helper to Unbound.
    assert_unbound(
        matcher.match_custom(TAG, &ctx),
        "match_custom via original_trigger dual-check",
    );
    assert!(
        matcher
            .binding_for_custom_action_in_context(TAG, &ctx)
            .is_none(),
        "second surface must honor the tombstone via original_trigger too"
    );
}

/// X9 (B) — CONSISTENCY GATE: after an inject OVERRIDE of `copy` (not a tombstone),
/// the matcher, the name-keyed reader `get_binding_by_name`, and the dual
/// custom-action list `binding_for_custom_action_in_context` all return the SAME
/// overridden action — proving inject is a FULL override, not a matcher-only
/// half-override. (Requires the `get_binding_by_name` reverse-ordering reader
/// plumbing; see the comment on that method.)
#[test]
fn test_inject_override_consistency_gate() {
    #[derive(Debug, PartialEq)]
    enum Copy {
        Original,
        Override,
    }
    const TAG: CustomTag = 42;

    let mut matcher = Matcher::new(Keymap::default());
    matcher.register_editable_bindings([EditableBinding::new("copy", "Copy", Copy::Original)
        .with_custom_action(TAG)
        .with_context_predicate(always!())]);
    let ctx = Context::default();

    // Baseline: all three readers agree on the ORIGINAL before any override.
    let baseline = expect_action(matcher.match_custom(TAG, &ctx), "baseline matcher");
    assert_eq!(baseline.as_action::<Copy>(), &Copy::Original);
    assert_eq!(
        matcher
            .get_binding_by_name("copy")
            .unwrap()
            .action
            .as_action::<Copy>(),
        &Copy::Original
    );
    assert_eq!(
        matcher
            .binding_for_custom_action_in_context(TAG, &ctx)
            .unwrap()
            .action
            .as_action::<Copy>(),
        &Copy::Original
    );

    // Inject an OVERRIDE (a real binding, NOT a tombstone) at highest precedence.
    matcher.inject_binding(
        EditableBinding::new("copy", "Copy", Copy::Override)
            .with_custom_action(TAG)
            .with_context_predicate(always!()),
    );

    // CONSISTENCY GATE: matcher, name-reader, and macOS-menu surface must all agree.
    let matcher_action = expect_action(matcher.match_custom(TAG, &ctx), "override matcher");
    assert_eq!(
        matcher_action.as_action::<Copy>(),
        &Copy::Override,
        "matcher must resolve the override (LIFO precedence)"
    );
    assert_eq!(
        matcher
            .get_binding_by_name("copy")
            .unwrap()
            .action
            .as_action::<Copy>(),
        &Copy::Override,
        "get_binding_by_name must agree with the matcher (no name-reader half-override)"
    );
    assert_eq!(
        matcher
            .binding_for_custom_action_in_context(TAG, &ctx)
            .unwrap()
            .action
            .as_action::<Copy>(),
        &Copy::Override,
        "binding_for_custom_action_in_context (macOS menu) must agree with the matcher"
    );
}

impl Matcher {
    fn test_keystroke(
        &mut self,
        keystroke: &str,
        view_id: EntityId,
        ctx: &Context,
    ) -> Option<Arc<dyn Action>> {
        match self.push_keystroke(Keystroke::parse(keystroke).unwrap(), view_id, ctx) {
            MatchResult::Action(action) => Some(action),
            _ => None,
        }
    }
}

trait AsAction {
    fn as_action<A: Action>(&self) -> &A;
}

impl AsAction for Arc<dyn Action> {
    fn as_action<A: Action>(&self) -> &A {
        self.as_ref().as_any().downcast_ref::<A>().unwrap()
    }
}
