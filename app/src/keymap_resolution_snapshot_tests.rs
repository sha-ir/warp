//! X13 — keymap resolution-snapshot freeze (throwaway spike harness).
//!
//! Captures `(context, trigger, OS) -> winning action` resolved through the REAL
//! matcher, frozen as a committed golden BEFORE any `bindings()` reorder lands.
//! This is the regression net the Phase-2 engine refactors diff against (A3-Q4,
//! which reorders `bindings()` by `(layer, recency)` and can silently flip the
//! winner for any registration; also A3-Q16/A3-Q17).
//!
//! Capture entrypoint: `AppContext::bindings_for_context_snapshot` (test-util),
//! which mirrors the per-context half of `key_bindings_for_view` (first lens per
//! trigger = the winner `push_keystroke` would fire). Build-config-relative: a
//! single native build snapshots only its own OS (OperatingSystem::get() is
//! compile-time fixed; per-platform keystrokes are resolved-and-discarded at
//! registration), so the golden is partitioned by OS.
//!
//! Regenerate (bless):
//!   BLESS=1 cargo test -p warp -- --ignored --nocapture x13_resolution_snapshot
//! Verify (diff vs golden):
//!   cargo test -p warp -- --ignored --nocapture x13_resolution_snapshot

use std::collections::BTreeMap;
use std::path::PathBuf;

use warpui::keymap::{BindingLens, Context, Keystroke, Trigger};
use warpui::platform::OperatingSystem;
use warpui::App;

/// A curated, flattened responder-chain context. The live matcher resolves over a
/// `Vec<Context>` chain (focused view -> root) with cross-view precedence; we flatten
/// each chain into one `Context`, which is a documented approximation (it can mask
/// cross-view precedence but is consistent for before/after characterization).
struct Fixture {
    name: &'static str,
    set: &'static [&'static str],
    map: &'static [(&'static str, &'static str)],
}

/// ~12 fixtures harvested from the real `id!(...)` vocabulary (top tags: IMEOpen,
/// Workspace, EditorView, Terminal, RichTextEditorView, Input, Vim, PaneGroup,
/// LongRunningCommand, ...). Chosen to maximize coverage of distinct resolution
/// branches incl. the `!id!("IMEOpen")` suppression path and the modal-mode branch.
const FIXTURES: &[Fixture] = &[
    Fixture { name: "bare_root", set: &["RootView"], map: &[] },
    Fixture { name: "terminal_idle_empty", set: &["Terminal", "TerminalView_EmptyBlockList"], map: &[] },
    Fixture {
        name: "terminal_long_running",
        set: &["Terminal", "TerminalView_NonEmptyBlockList", "LongRunningCommand"],
        map: &[("TerminalView_BlockSelectionCardinality", "None")],
    },
    Fixture {
        name: "terminal_alt_screen",
        set: &["Terminal", "TerminalView_NonEmptyBlockList", "AltScreen", "ActiveAltScreenSelection"],
        map: &[],
    },
    Fixture {
        name: "terminal_block_selected",
        set: &["Terminal", "TerminalView_NonEmptyBlockList", "ActiveBlockTextSelection"],
        map: &[("TerminalView_BlockSelectionCardinality", "One")],
    },
    Fixture {
        name: "input_focused_ime_open",
        set: &["Terminal", "Input", "EditorFocused", "TerminalView_EmptyBlockList", "IMEOpen"],
        map: &[],
    },
    Fixture {
        name: "agent_input",
        set: &["Terminal", "Input", "AIInput", "VoltronActive", "UniversalDeveloperInput"],
        map: &[],
    },
    Fixture {
        name: "workspace_multi_tab_pane_drag",
        set: &["Workspace", "Workspace_MultipleTabs", "PaneGroup", "PaneGroup_PaneDragging", "PaneGroup_MultiplePanes"],
        map: &[],
    },
    Fixture {
        name: "code_editor_vim_normal",
        set: &["EditorView", "CodeEditorView", "Vim", "VimNormalMode", "FindBarAvailable"],
        map: &[],
    },
    Fixture {
        name: "richtext_notebook_editing",
        set: &["RichTextEditorView", "NotebookView", "NotebookEditing", "EditorIsEditable", "BlockInsertionMenu", "HasCommandSelection"],
        map: &[],
    },
    Fixture { name: "drive_index", set: &["Workspace", "DriveIndex", "WarpDrive_BelongsToTeam"], map: &[] },
    Fixture {
        name: "flagged_terminal",
        set: &["Terminal", "TerminalView_EmptyBlockList", "Vim_Mode_Enabled", "Notifications_Enabled", "Copy_On_Select"],
        map: &[],
    },
];

fn build_context(f: &Fixture) -> Context {
    let mut c = Context::default();
    for &s in f.set {
        c.set.insert(s);
    }
    for &(k, v) in f.map {
        c.map.insert(k, v);
    }
    c
}

/// Canonical, parse-compatible keystroke string (e.g. `ctrl-c`, `cmd-shift-a`).
/// `cmdorctrl` is already resolved to `ctrl`/`cmd` at registration time, so this
/// reflects the build's OS faithfully.
fn fmt_keystroke(k: &Keystroke) -> String {
    let mut s = String::new();
    if k.cmd {
        s.push_str("cmd-");
    }
    if k.ctrl {
        s.push_str("ctrl-");
    }
    if k.alt {
        s.push_str("alt-");
    }
    if k.shift {
        s.push_str("shift-");
    }
    if k.meta {
        s.push_str("meta-");
    }
    s.push_str(&k.key);
    s
}

fn fmt_trigger(t: &Trigger) -> String {
    match t {
        Trigger::Keystrokes(ks) => ks.iter().map(fmt_keystroke).collect::<Vec<_>>().join(" "),
        Trigger::Standard(a) => format!("Standard({a:?})"),
        Trigger::Custom(tag) => format!("Custom({tag})"),
        Trigger::Empty => "Empty".to_string(),
    }
}

/// Winner cell. Actions are `Arc<dyn Action>` with no stable id (BindingId is a
/// volatile per-run AtomicUsize, so it must NOT go in the golden). Editable bindings
/// have a stable `name`; fixed bindings have an empty name, so we fall back to the
/// action's Debug — the best available stable key for fixed bindings.
fn fmt_winner(b: &BindingLens) -> String {
    if b.name.is_empty() {
        format!("fixed:{:?}", b.action)
    } else {
        format!("editable:{}", b.name)
    }
}

fn golden_path(os_str: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("test_data")
        .join("keymap")
        .join(format!("resolution_table.{os_str}.txt"))
}

/// Print a compact line-level diff (first 40 differing lines) so a winner flip is
/// reviewable without re-reading the whole golden.
fn print_diff(expected: &str, actual: &str) {
    let exp: Vec<&str> = expected.lines().collect();
    let act: Vec<&str> = actual.lines().collect();
    let mut shown = 0;
    let max = exp.len().max(act.len());
    for i in 0..max {
        let e = exp.get(i).copied().unwrap_or("<missing>");
        let a = act.get(i).copied().unwrap_or("<missing>");
        if e != a {
            eprintln!("  line {}:\n    - {e}\n    + {a}", i + 1);
            shown += 1;
            if shown >= 40 {
                eprintln!("  ... (diff truncated at 40 lines)");
                break;
            }
        }
    }
}

#[test]
#[ignore = "X13 resolution-snapshot capture/regression; boots the full app, run explicitly"]
fn x13_resolution_snapshot() {
    App::test((), |mut app| async move {
        // The existing headless harness wires ~89 mock singletons + experiments::init
        // + workspace::init (cascade: modal/native_modal/notebooks/settings).
        crate::workspace::view::tests::initialize_app(&mut app);
        // Layer the remaining production keybinding inits (lib.rs "Register initial
        // keybindings" block) to reach full ~266-binding coverage.
        app.update(crate::x13_register_keybinding_inits);
        let coverage = "FULL: view::tests::initialize_app (workspace cascade + experiments) + x13_register_keybinding_inits (production lib.rs:1649-1693 inits)";

        let os = OperatingSystem::get();
        let os_str = format!("{os:?}").to_lowercase();

        let rows = app.read(|ctx| {
            let mut rows: Vec<String> = Vec::new();
            for f in FIXTURES {
                // First lens per trigger wins (precedence order preserved by the matcher).
                let mut winners: BTreeMap<String, String> = BTreeMap::new();
                for lens in ctx.bindings_for_context_snapshot(build_context(f)) {
                    if matches!(lens.trigger, Trigger::Empty) {
                        continue;
                    }
                    let trig = fmt_trigger(lens.trigger);
                    winners.entry(trig).or_insert_with(|| fmt_winner(&lens));
                }
                for (trig, winner) in winners {
                    rows.push(format!("{}\t{}\t{}", f.name, trig, winner));
                }
            }
            rows.sort();
            rows
        });

        let header = format!(
            "# Warp keymap resolution snapshot (X13 — frozen pre-reorder baseline)\n\
             # DO NOT EDIT BY HAND. Regenerate: BLESS=1 cargo test -p warp -- --ignored --nocapture x13_resolution_snapshot\n\
             # os = {os_str}\n\
             # coverage = {coverage}\n\
             # winner = editable:<name> | fixed:<action Debug>;  columns are TAB-separated: context<TAB>trigger<TAB>winner\n\
             # rows = {n}\n\
             #\n",
            n = rows.len(),
        );
        let content = format!("{header}{}\n", rows.join("\n"));

        let path = golden_path(&os_str);
        if std::env::var_os("BLESS").is_some() {
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, &content).unwrap();
            eprintln!("X13: blessed {} ({} rows)", path.display(), rows.len());
        } else {
            let expected = std::fs::read_to_string(&path).unwrap_or_else(|_| {
                panic!(
                    "X13 golden missing at {}. Generate it first: BLESS=1 cargo test -p warp -- --ignored --nocapture x13_resolution_snapshot",
                    path.display()
                )
            });
            if expected != content {
                eprintln!("X13 resolution snapshot drifted vs {}:", path.display());
                print_diff(&expected, &content);
                panic!("X13 resolution snapshot drifted. If intentional, re-bless with BLESS=1.");
            }
            eprintln!("X13: snapshot matches golden ({} rows)", rows.len());
        }
    });
}
