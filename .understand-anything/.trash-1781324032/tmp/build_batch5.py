import json, math, os

P = "crates/warpui_core/src/"
inp = json.load(open("/home/mhb/warp/.understand-anything/tmp/ua-file-analyzer-input-5.json"))
imp = inp["batchImportData"]

def fid(p): return "file:"+p
def cid(p,n): return "class:"+p+":"+n
def fnid(p,n): return "function:"+p+":"+n

nodes = []
edges = []

def filenode(path, summary, tags, complexity, lang=None):
    n = {"id":fid(path),"type":"file","name":path.split("/")[-1],"filePath":path,
         "summary":summary,"tags":tags,"complexity":complexity}
    if lang: n["languageNotes"]=lang
    nodes.append(n)

def classnode(path,name,lr,summary,tags,complexity,exported=True):
    nodes.append({"id":cid(path,name),"type":"class","name":name,"filePath":path,
        "lineRange":lr,"summary":summary,"tags":tags,"complexity":complexity})
    edges.append({"source":fid(path),"target":cid(path,name),"type":"contains","direction":"forward","weight":1.0})
    if exported:
        edges.append({"source":fid(path),"target":cid(path,name),"type":"exports","direction":"forward","weight":0.8})

def funcnode(path,name,lr,summary,tags,complexity,exported=True):
    nodes.append({"id":fnid(path,name),"type":"function","name":name,"filePath":path,
        "lineRange":lr,"summary":summary,"tags":tags,"complexity":complexity})
    edges.append({"source":fid(path),"target":fnid(path,name),"type":"contains","direction":"forward","weight":1.0})
    if exported:
        edges.append({"source":fid(path),"target":fnid(path,name),"type":"exports","direction":"forward","weight":0.8})

# ---------- FILE NODES ----------
filenode(P+"image_cache.rs",
 "Image decoding, resizing, and caching subsystem: defines image types (SVG, static/animated bitmaps), a custom image header format, fit/resize logic, and the ImageCache keyed by source and render parameters.",
 ["image-cache","rendering","caching","decoding"],"complex")
filenode(P+"keymap.rs",
 "Core keybinding model defining keystrokes, fixed and editable bindings, triggers, binding descriptions, and the Keymap registry used to look up and customize bindings.",
 ["keymap","keybindings","data-model","customization"],"complex",
 "Heavy use of builder-pattern constructors (with_* methods) over binding types.")
filenode(P+"keymap/matcher.rs",
 "Keystroke matcher that registers bindings, resolves pending multi-key sequences, validates bindings per context, and maps keystrokes to standard or custom actions.",
 ["keymap","matcher","input","state-machine"],"complex")
filenode(P+"keymap/matcher_tests.rs",
 "Unit tests for the keystroke Matcher covering binding registration, editable-binding matching, and context-scoped binding lookup.",
 ["test","keymap","matcher"],"moderate")
filenode(P+"lib.rs",
 "Crate root for warpui_core: declares and re-exports all submodules (actions, elements, keymap, platform, rendering, windowing, telemetry, etc.) and defines the Gradient type.",
 ["entry-point","barrel","crate-root","module-declaration"],"simple",
 "Rust crate root assembling the module tree via mod/pub use declarations.")
filenode(P+"modals.rs",
 "Defines platform alert-dialog value types (alert dialogs, buttons, callbacks) and modal identifiers used to present native modal dialogs.",
 ["modals","dialog","data-model","platform"],"moderate")
filenode(P+"notification.rs",
 "Desktop notification model: notification content builder, send-error and permission-outcome enums, and notification response data.",
 ["notification","data-model","platform"],"moderate")
filenode(P+"platform/app.rs",
 "Application-level platform callback layer wiring native app lifecycle events (activation, window lifecycle, file/URL open, sleep/wake, modal responses) to Rust callbacks.",
 ["platform","app-lifecycle","event-handler","dispatcher"],"complex")
filenode(P+"platform/file_picker.rs",
 "File picker configuration types describing allowed file types and open/save dialog options.",
 ["file-picker","configuration","platform","builder"],"moderate")
filenode(P+"platform/keyboard.rs",
 "Physical keyboard key code definitions (NativeKeyCode, PhysicalKey, and the exhaustive KeyCode enum) modeling W3C key codes across platforms.",
 ["keyboard","key-codes","input","platform"],"complex",
 "Large data-only enum mirroring the W3C UI Events KeyboardEvent.code value set.")
filenode(P+"platform/menu.rs",
 "Native menu model: menu bar, menus, menu items, item property changes, and custom menu items with click/update callbacks.",
 ["menu","platform","data-model","event-handler"],"moderate")
filenode(P+"platform/test/app.rs",
 "Test stub of the platform App entry point that no-ops initialization for headless test runs.",
 ["test","platform","stub"],"simple")
filenode(P+"platform/test/delegate.rs",
 "Test/headless implementations of the platform delegate surface: stub AppDelegate, IntegrationTestDelegate, Window, WindowManager, and FontDB for integration tests.",
 ["test","platform","mock","delegate"],"complex",
 "cfg(test) trait-implementation stubs satisfying platform delegate traits with no-op bodies.")
filenode(P+"platform/test/mod.rs",
 "Test platform module barrel re-exporting the test App and delegate implementations.",
 ["test","barrel","module-declaration"],"simple")
filenode(P+"rendering/gpu_info.rs",
 "GPU device and backend descriptors (device type, graphics backend, device info) used to report rendering hardware.",
 ["rendering","gpu","data-model"],"moderate")
filenode(P+"rendering/mod.rs",
 "Rendering configuration types: thin-stroke policy, glyph config, GPU power preference, overall Config, and corner-radius conversion helpers.",
 ["rendering","configuration","gpu","data-model"],"moderate")
filenode(P+"rendering/texture_cache.rs",
 "GPU texture cache mapping image assets to texture handles with frame-based eviction of unused entries.",
 ["texture-cache","rendering","gpu","caching"],"moderate")
filenode(P+"rendering/texture_cache_tests.rs",
 "Unit tests verifying TextureCache eviction and retention behavior across frames and asset lifetimes.",
 ["test","texture-cache","rendering"],"moderate")
filenode(P+"telemetry/event_store.rs",
 "Telemetry event store buffering events, managing session creation/staleness, and building identify, app-active, and named telemetry events.",
 ["telemetry","event-store","session","data-model"],"complex")
filenode(P+"telemetry/event_store_tests.rs",
 "Unit tests for EventStore session initialization, queue emptiness, and app-active event generation after activity/inactivity.",
 ["test","telemetry","event-store"],"moderate")
filenode(P+"telemetry/mod.rs",
 "Telemetry facade exposing functions to create, record, and flush events and route them to the EventStore.",
 ["telemetry","facade","instrumentation"],"moderate")
filenode(P+"test.rs",
 "Test support module providing a logging/tracing init helper for unit tests.",
 ["test","utility","setup"],"simple")
filenode(P+"text_selection_utils.rs",
 "Helpers for rendering text selection across newlines, including newline tick geometry and row/offset-based selection-crossing checks.",
 ["text-selection","geometry","utility","rendering"],"moderate")
filenode(P+"time.rs",
 "Time utilities returning the current time, with a test-overridable offset for deterministic tests.",
 ["time","utility","testing"],"simple",
 "Uses cfg(test) to swap the real clock for an offset-controllable test clock.")
filenode(P+"traces.rs",
 "In-process performance trace recorder that timestamps named events between start and end markers.",
 ["tracing","performance","instrumentation","telemetry"],"moderate")
filenode(P+"util.rs",
 "General-purpose utilities: post-increment helper, saving bytes to a file, and string-to-integer parsing.",
 ["utility","parsing","helpers"],"moderate")
filenode(P+"windowing/mod.rs",
 "Per-window event dispatch layer defining window callbacks and the dispatcher that routes input, resize, move, scene-build, and frame-draw events.",
 ["windowing","event-handler","dispatcher","rendering"],"moderate")
filenode(P+"windowing/state.rs",
 "Application window state manager owning stage, active window, window stack, and fullscreen state, driving window lifecycle, focus, geometry, and appearance via the platform.",
 ["windowing","window-management","state","platform"],"complex")
filenode(P+"windowing/system.rs",
 "Windowing-system detection enum (X11/Wayland/AppKit/Windows) derived from a raw display handle, gating programmatic window activation.",
 ["windowing","platform","detection"],"moderate")

# ---------- CLASS / FUNCTION NODES ----------
classnode(P+"image_cache.rs","ImageCache",[801,805],
 "In-memory cache of rendered images keyed by asset source, bounds, fit type, and animation behavior; decodes, resizes, caches, and evicts image renditions.",
 ["image-cache","caching","rendering","data-model"],"complex")
classnode(P+"image_cache.rs","ImageType",[462,468],
 "Enum classifying decoded image data (SVG, static/animated bitmap, unrecognized) with byte decoding, sizing, and rasterization-to-Image conversion.",
 ["image","decoding","enum","serialization"],"complex")
classnode(P+"image_cache.rs","AnimatedImage",[425,430],
 "Holds decoded animated image frames and total duration, selecting the current frame for a given elapsed time.",
 ["image","animation","data-model"],"moderate")
funcnode(P+"image_cache.rs","resize_image",[578,622],
 "Resizes a static bitmap to fit target bounds according to the requested FitType (cover/contain/stretch).",
 ["image","resize","utility"],"moderate",exported=False)
funcnode(P+"image_cache.rs","resize_dimensions",[633,668],
 "Computes target pixel dimensions for a resize, preserving aspect ratio for cover/contain fits.",
 ["image","resize","geometry","utility"],"moderate")

classnode(P+"keymap.rs","Keymap",[25,38],
 "Central registry of fixed and editable key bindings, indexing them by name and exposing custom-action and editable binding views.",
 ["keymap","keybindings","registry","data-model"],"complex")
classnode(P+"keymap.rs","Keystroke",[321,328],
 "Represents a single keystroke (modifier flags plus key) with parsing from strings, normalization, display formatting, and JSON schema support.",
 ["keybindings","parsing","serialization","input"],"complex")
classnode(P+"keymap.rs","FixedBinding",[277,286],
 "Non-editable key binding pairing a trigger with an action and context predicate, with per-platform and builder-style constructors.",
 ["keybindings","binding","builder","data-model"],"complex")
classnode(P+"keymap.rs","EditableBinding",[293,304],
 "User-customizable key binding with default and custom triggers, offering builder configuration of context, platform key bindings, and actions.",
 ["keybindings","binding","builder","customization"],"complex")
classnode(P+"keymap.rs","BindingDescription",[77,90],
 "Describes a binding's human-readable label with optional context-specific and dynamically resolved overrides.",
 ["keybindings","description","localization"],"moderate")

classnode(P+"keymap/matcher.rs","Matcher",[14,30],
 "Stateful keystroke matcher that registers bindings, tracks pending multi-keystroke sequences, validates bindings per context, and resolves keystrokes to standard or custom actions.",
 ["keymap","matcher","input","state-machine"],"complex")

classnode(P+"notification.rs","UserNotification",[11,18],
 "Builder-style value type describing a desktop notification (title, body, payload data, optional sound) to be sent to the platform.",
 ["notification","builder","data-model"],"moderate")

classnode(P+"platform/app.rs","AppCallbackDispatcher",[57,60],
 "Dispatches application-level platform events (activation, window lifecycle, files/URLs opened, sleep/wake, menu and modal responses) to registered Rust callbacks.",
 ["platform","app-lifecycle","event-handler","dispatcher"],"complex")

classnode(P+"platform/file_picker.rs","FilePickerConfiguration",[62,67],
 "Builder describing an open-file dialog's allowed file types, folder/file selection, and multi-select behavior.",
 ["file-picker","configuration","builder","platform"],"moderate")

classnode(P+"platform/keyboard.rs","KeyCode",[85,529],
 "Exhaustive enum of physical keyboard key codes (W3C UI Events code values) spanning alphanumerics, modifiers, function, media, and numpad keys.",
 ["keyboard","key-codes","enum","input"],"complex")

classnode(P+"platform/menu.rs","CustomMenuItem",[112,117],
 "Application menu item carrying display properties plus click and update callbacks and an optional submenu.",
 ["menu","platform","event-handler","data-model"],"moderate")

classnode(P+"platform/test/delegate.rs","WindowManager",[66,68],
 "Test double for the platform window manager, tracking opened test windows and stubbing display, activation, and window-ordering queries.",
 ["test","platform","window-management","mock"],"complex")
classnode(P+"platform/test/delegate.rs","FontDB",[507,507],
 "Test/no-op font database stub implementing glyph metrics, rasterization, and text-layout entry points for headless integration tests.",
 ["test","fonts","text-layout","mock"],"complex")
classnode(P+"platform/test/delegate.rs","AppDelegate",[30,33],
 "Test delegate implementing the platform app-delegate surface (cursor, clipboard, file pickers, notifications, modals) with stub behavior.",
 ["test","platform","delegate","mock"],"complex")

classnode(P+"rendering/texture_cache.rs","TextureCache",[26,31],
 "Frame-indexed cache mapping image assets to GPU texture handles, inserting on demand and evicting textures unused for too many frames.",
 ["texture-cache","rendering","gpu","caching"],"moderate")

classnode(P+"telemetry/event_store.rs","EventStore",[18,24],
 "Buffers telemetry events, manages session lifecycle and staleness, and constructs identify, app-active, and named events for later flushing.",
 ["telemetry","event-store","session","data-model"],"complex")

classnode(P+"traces.rs","Traces",[13,18],
 "Lightweight in-process trace recorder that timestamps named events between a start and end marker for performance tracing.",
 ["tracing","telemetry","performance","instrumentation"],"moderate",exported=False)

classnode(P+"windowing/mod.rs","WindowCallbackDispatcher",[56,59],
 "Dispatches per-window events (input, resize, move, scene build, frame draw results, cursor position) to registered window callbacks.",
 ["windowing","event-handler","dispatcher","rendering"],"moderate")

classnode(P+"windowing/state.rs","WindowManager",[54,57],
 "Owns application window state (stage, active window, window stack, fullscreen) and drives window lifecycle, focus, display geometry, and blur/title operations via the platform.",
 ["windowing","window-management","state","platform"],"complex")

classnode(P+"windowing/system.rs","System",[10,15],
 "Enum identifying the host windowing system (X11, Wayland, AppKit, Windows), derived from a raw display handle and gating programmatic window activation.",
 ["windowing","platform","enum","detection"],"moderate")

funcnode(P+"text_selection_utils.rs","selection_crosses_newline_row_based",[42,60],
 "Determines whether a text selection spans across a newline at a given row using row/column selection coordinates.",
 ["text-selection","geometry","utility"],"moderate")
funcnode(P+"text_selection_utils.rs","selection_crosses_newline_offset_based",[68,85],
 "Determines whether a text selection crosses a line's trailing newline using absolute character offsets.",
 ["text-selection","geometry","utility"],"moderate")

funcnode(P+"util.rs","parse_i32",[35,66],
 "Parses a string into an i32, handling sign and surfacing parse errors; used for value/config parsing.",
 ["parsing","utility","validation"],"moderate")

# ---------- IMPORT EDGES ----------
imp_count = 0
for src, targets in imp.items():
    for t in targets:
        edges.append({"source":fid(src),"target":fid(t),"type":"imports","direction":"forward","weight":0.7})
        imp_count += 1

# ---------- TESTED_BY EDGES ----------
def tb(prod,test):
    edges.append({"source":fid(prod),"target":fid(test),"type":"tested_by","direction":"forward","weight":0.5})
tb(P+"keymap/matcher.rs", P+"keymap/matcher_tests.rs")
tb(P+"keymap.rs", P+"keymap/matcher_tests.rs")
tb(P+"rendering/texture_cache.rs", P+"rendering/texture_cache_tests.rs")
tb(P+"telemetry/event_store.rs", P+"telemetry/event_store_tests.rs")

print("nodes",len(nodes),"edges",len(edges),"imports",imp_count)

# ---------- PARTITION ----------
allfiles = sorted(imp.keys())
parts = max(math.ceil(len(nodes)/60), math.ceil(len(edges)/120))
print("parts",parts)
per = math.ceil(len(allfiles)/parts)
groups = [set(allfiles[i*per:(i+1)*per]) for i in range(parts)]

# map node id -> filePath
node_fp = {n["id"]: n["filePath"] for n in nodes}

outdir = "/home/mhb/warp/.understand-anything/intermediate"
os.makedirs(outdir, exist_ok=True)
written=[]
total_n=0; total_e=0
for k,g in enumerate(groups, start=1):
    pn = [n for n in nodes if n["filePath"] in g]
    pnids = {n["id"] for n in pn}
    pe = [e for e in edges if e["source"] in pnids]
    frag = {"nodes":pn,"edges":pe}
    # validate edges: source must be in pnids
    for e in pe:
        assert e["source"] in pnids, e
    fn = f"{outdir}/batch-5-part-{k}.json"
    json.dump(frag, open(fn,"w"), indent=2)
    written.append((fn,len(pn),len(pe)))
    total_n+=len(pn); total_e+=len(pe)

# verify no node/edge lost
assert total_n==len(nodes), (total_n,len(nodes))
assert total_e==len(edges), (total_e,len(edges))
for w in written: print(w)
print("TOTAL nodes",total_n,"edges",total_e)
