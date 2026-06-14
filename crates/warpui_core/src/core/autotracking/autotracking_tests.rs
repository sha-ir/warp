use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use super::*;
use crate::elements::Empty;
use crate::platform::WindowStyle;
use crate::{App, AppContext, Element, Entity, ModelHandle, TypedActionView, View};

#[derive(Default)]
struct Model {
    first: Tracked<usize>,
    second: Tracked<bool>,
    third: Tracked<isize>,
}

impl Entity for Model {
    type Event = ();
}

struct TestView {
    model: ModelHandle<Model>,
    field: Tracked<usize>,
    other_field: Tracked<bool>,
    counter: Arc<AtomicUsize>,
}

impl TestView {
    fn new(model: ModelHandle<Model>, counter: Arc<AtomicUsize>) -> Self {
        TestView {
            model,
            field: Tracked::new(0),
            other_field: Tracked::new(false),
            counter,
        }
    }
}

impl Entity for TestView {
    type Event = ();
}

impl View for TestView {
    fn ui_name() -> &'static str {
        "TestView"
    }

    fn render(&self, app: &AppContext) -> Box<dyn Element> {
        // While rendering, we explicitly read / depend on the fields `first` and `second` of
        // model, as well as `field` of the View itself.

        // We explicitly do _not_ depend on `Model::third` nor `other_field` on the View.
        let model = self.model.as_ref(app);
        let _first = *model.first;
        let _second = *model.second;
        let _field = *self.field;

        // Increment the render counter so that we can track how often a View is rendered
        self.counter.fetch_add(1, Ordering::Relaxed);

        Empty::new().finish()
    }
}

impl TypedActionView for TestView {
    type Action = ();
}

#[test]
fn test_update_view_dependency_rerenders() {
    App::test((), |mut app| async move {
        let model_handle = app.add_model(|_| Model::default());

        let render_counter = Arc::new(AtomicUsize::new(0));
        let (_, view_handle) = app.add_window(WindowStyle::NotStealFocus, |_| {
            TestView::new(model_handle.clone(), render_counter.clone())
        });

        // Force the window to be rendered the first time
        view_handle.update(&mut app, |_, _| {});
        assert_eq!(render_counter.load(Ordering::Relaxed), 1);

        // Update an internal View dependency and confirm that it causes a rerender of the View
        view_handle.update(&mut app, |view, _| {
            *view.field += 1;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 2);
    });
}

#[test]
fn test_update_view_non_dependency_no_rerender() {
    App::test((), |mut app| async move {
        let model_handle = app.add_model(|_| Model::default());

        let render_counter = Arc::new(AtomicUsize::new(0));
        let (_, view_handle) = app.add_window(WindowStyle::NotStealFocus, |_| {
            TestView::new(model_handle.clone(), render_counter.clone())
        });

        // Force the window to be rendered the first time
        view_handle.update(&mut app, |_, _| {});
        assert_eq!(render_counter.load(Ordering::Relaxed), 1);

        // Update an internal View field that is not a dependency and confirm that it does not
        // cause a rerender of the View
        view_handle.update(&mut app, |view, _| {
            *view.other_field = true;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 1);
    });
}

#[test]
fn test_update_model_dependency_rerenders() {
    App::test((), |mut app| async move {
        let model_handle = app.add_model(|_| Model::default());

        let render_counter = Arc::new(AtomicUsize::new(0));
        let (_, view_handle) = app.add_window(WindowStyle::NotStealFocus, |_| {
            TestView::new(model_handle.clone(), render_counter.clone())
        });

        // Force the window to be rendered the first time
        view_handle.update(&mut app, |_, _| {});
        assert_eq!(render_counter.load(Ordering::Relaxed), 1);

        // Update a Model dependency and confirm that it causes a rerender of the View
        model_handle.update(&mut app, |model, _| {
            *model.first += 1;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 2);

        // Update another Model dependency and confirm that it causes a rerender
        model_handle.update(&mut app, |model, _| {
            *model.second = true;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 3);
    });
}

#[test]
fn test_update_model_non_dependency_no_rerender() {
    App::test((), |mut app| async move {
        let model_handle = app.add_model(|_| Model::default());

        let render_counter = Arc::new(AtomicUsize::new(0));
        let (_, view_handle) = app.add_window(WindowStyle::NotStealFocus, |_| {
            TestView::new(model_handle.clone(), render_counter.clone())
        });

        // Force the window to be rendered the first time
        view_handle.update(&mut app, |_, _| {});
        assert_eq!(render_counter.load(Ordering::Relaxed), 1);

        // Update a Model field that is not a dependency and confirm that it does not
        // cause a rerender of the View
        model_handle.update(&mut app, |model, _| {
            *model.third -= 1000;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 1);
    });
}

#[test]
fn test_updates_multiple_sources() {
    App::test((), |mut app| async move {
        let model_handle = app.add_model(|_| Model::default());

        let render_counter = Arc::new(AtomicUsize::new(0));
        let (_, view_handle) = app.add_window(WindowStyle::NotStealFocus, |_| {
            TestView::new(model_handle.clone(), render_counter.clone())
        });

        // Force the window to be rendered the first time
        view_handle.update(&mut app, |_, _| {});
        assert_eq!(render_counter.load(Ordering::Relaxed), 1);

        // Update several Model dependencies and confirm it causes a single rerender
        model_handle.update(&mut app, |model, _| {
            *model.first += 1;
            *model.second = true;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 2);

        // Update a View dependency and confirm it causes another rerender
        view_handle.update(&mut app, |view, _| {
            *view.field += 100;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 3);

        // Update a field that is not a dependency and confirm that it doesn't cause a rerender
        view_handle.update(&mut app, |view, _| {
            *view.other_field = true;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 3);

        // Update a non-dependency on the Model and confirm that there is no rerender
        model_handle.update(&mut app, |model, _| {
            *model.third -= 100;
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 3);

        // Update the view _and_ the model in the same call and confirm that it causes a single
        // rerender
        view_handle.update(&mut app, |view, ctx| {
            *view.field += 20;
            view.model.update(ctx, |model, _| {
                *model.first += 23;
            });
        });
        assert_eq!(render_counter.load(Ordering::Relaxed), 4);
    });
}

#[test]
fn test_model_updates_multiple_views() {
    struct OtherView {
        model: ModelHandle<Model>,
        counter: Arc<AtomicUsize>,
    }

    impl OtherView {
        fn new(model: ModelHandle<Model>, counter: Arc<AtomicUsize>) -> Self {
            OtherView { model, counter }
        }
    }

    impl Entity for OtherView {
        type Event = ();
    }

    impl View for OtherView {
        fn ui_name() -> &'static str {
            "OtherView"
        }

        fn render(&self, app: &AppContext) -> Box<dyn Element> {
            let model = self.model.as_ref(app);
            // This view depends on `second` and `third` in the model, so updates to those should
            // cause it to rerender (overlapping `second` with the main test view)
            let _second = *model.second;
            let _third = *model.third;

            self.counter.fetch_add(1, Ordering::Relaxed);

            Empty::new().finish()
        }
    }

    App::test((), |mut app| async move {
        let model_handle = app.add_model(|_| Model::default());

        let first_render_counter = Arc::new(AtomicUsize::new(0));
        let (window_id, first_view) = app.add_window(WindowStyle::NotStealFocus, |_| {
            TestView::new(model_handle.clone(), first_render_counter.clone())
        });

        let second_render_counter = Arc::new(AtomicUsize::new(0));
        let _second_view = app.add_view(window_id, |_| {
            OtherView::new(model_handle.clone(), second_render_counter.clone())
        });

        // Force the window to be rendered the first time
        first_view.update(&mut app, |_, _| {});
        assert_eq!(first_render_counter.load(Ordering::Relaxed), 1);
        assert_eq!(second_render_counter.load(Ordering::Relaxed), 1);

        // Update a field on the model that _only_ the first view depends on and confirm that is
        // the only view rerendered
        model_handle.update(&mut app, |model, _| {
            *model.first += 100;
        });
        assert_eq!(first_render_counter.load(Ordering::Relaxed), 2);
        assert_eq!(second_render_counter.load(Ordering::Relaxed), 1);

        // Update a field on the model that _both_ views depend on and confirm both are rerendered
        model_handle.update(&mut app, |model, _| {
            *model.second = true;
        });
        assert_eq!(first_render_counter.load(Ordering::Relaxed), 3);
        assert_eq!(second_render_counter.load(Ordering::Relaxed), 2);

        // Update a field on the model that _only_ the second view depends on and confirm that is
        // the only view rerendered
        model_handle.update(&mut app, |model, _| {
            *model.third -= 55;
        });
        assert_eq!(first_render_counter.load(Ordering::Relaxed), 3);
        assert_eq!(second_render_counter.load(Ordering::Relaxed), 3);
    });
}

// ---- A3-Q4 / A3-Q7: live-apply invalidation identity ----------------------------------
//
// After the per-layer refactor, does editing a binding's override still invalidate a view that
// read it via get_binding_by_name at render time? It does IFF get_binding_by_name resolves the
// SAME Tracked<EditableBinding> that update_custom_trigger mutates. A single re-render (count == 2)
// is the identity witness; a split base/override design would leave the view never invalidated
// (count stuck at 1).

struct BindingView {
    counter: Arc<AtomicUsize>,
}

impl Entity for BindingView {
    type Event = ();
}

impl View for BindingView {
    fn ui_name() -> &'static str {
        "BindingView"
    }

    fn render(&self, app: &AppContext) -> Box<dyn Element> {
        // Reading the binding by name during render derefs its Tracked, recording a dependency
        // edge on that TrackedId (rendering_view == Some here).
        if let Some(binding) = app.get_binding_by_name("a3q4.test") {
            let _ = binding.trigger;
        }
        self.counter.fetch_add(1, Ordering::Relaxed);
        Empty::new().finish()
    }
}

impl TypedActionView for BindingView {
    type Action = ();
}

#[test]
fn a3q4_live_apply_invalidation_identity() {
    use crate::keymap::macros::*;
    use crate::keymap::{EditableBinding, Keystroke, Trigger};

    App::test((), |mut app| async move {
        // Register an editable binding and establish a user override BEFORE subscribing, so the
        // test exercises the post-move "override in place" state, not the pre-edit baseline.
        app.update(|ctx| {
            ctx.register_editable_bindings([EditableBinding::new("a3q4.test", "A3Q4 test", ())
                .with_key_binding("ctrl-a")
                .with_context_predicate(id!("c"))]);
            ctx.set_custom_trigger(
                "a3q4.test".to_string(),
                Trigger::Keystrokes(vec![Keystroke::parse("ctrl-b").unwrap()]),
            );
        });

        let counter = Arc::new(AtomicUsize::new(0));
        let (_, view_handle) = app.add_window(WindowStyle::NotStealFocus, |_| BindingView {
            counter: counter.clone(),
        });

        // First render subscribes the view to the binding's TrackedId.
        view_handle.update(&mut app, |_, _| {});
        assert_eq!(counter.load(Ordering::Relaxed), 1, "initial render");

        // Edit the override OUTSIDE render. If get_binding_by_name resolved the SAME Tracked the
        // edit mutates, the view is invalidated and re-renders exactly once.
        app.update(|ctx| {
            ctx.set_custom_trigger(
                "a3q4.test".to_string(),
                Trigger::Keystrokes(vec![Keystroke::parse("ctrl-c").unwrap()]),
            );
        });
        view_handle.update(&mut app, |_, _| {});

        assert_eq!(
            counter.load(Ordering::Relaxed),
            2,
            "live-apply: editing the override must invalidate the render-subscribed view exactly once"
        );
    });
}
