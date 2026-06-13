import json, math, os

imp = json.load(open('/home/mhb/warp/.understand-anything/tmp/ua-file-analyzer-input-3.json'))['batchImportData']

B = 'crates/warpui_core/src/'
nodes = []
edges = []

def fn(path):
    return path.split('/')[-1]

# ---- File node helper ----
def file_node(path, summary, tags, complexity, lang_notes=None):
    n = {"id": f"file:{path}", "type": "file", "name": fn(path), "filePath": path,
         "summary": summary, "tags": tags, "complexity": complexity}
    if lang_notes: n["languageNotes"] = lang_notes
    nodes.append(n)

def sub_node(kind, path, name, lr, summary, tags, complexity, exported=True, lang_notes=None):
    nid = f"{kind}:{path}:{name}"
    n = {"id": nid, "type": kind, "name": name, "filePath": path,
         "lineRange": lr, "summary": summary, "tags": tags, "complexity": complexity}
    if lang_notes: n["languageNotes"] = lang_notes
    nodes.append(n)
    edges.append({"source": f"file:{path}", "target": nid, "type": "contains", "direction": "forward", "weight": 1.0})
    if exported:
        edges.append({"source": f"file:{path}", "target": nid, "type": "exports", "direction": "forward", "weight": 0.8})
    return nid

# ============ FILE NODES ============
P = B+'elements/text_tests.rs'
file_node(P, "Unit tests for laid-out text geometry: line/text height, single-line char hit-testing within y-bounds, and selection range merging (overlapping, contiguous, adjacent).",
          ["test","text-layout","hit-testing","selection"], "moderate")

P = B+'elements/uniform_list_tests.rs'
file_node(P, "Integration-style tests for the uniform_list element covering rendering and layered click handling across stacked list items.",
          ["test","ui-element","list","event-handler"], "moderate")

P = B+'elements/viewported_list_tests.rs'
file_node(P, "Extensive tests for the viewported (virtualized) list element: scroll-position preservation when items above/below grow, scroll event emission, and scroll-position invalidation/clamping.",
          ["test","ui-element","virtualized-list","scrolling"], "complex")

P = B+'fonts.rs'
file_node(P, "Font subsystem core: font weight/style/properties model, a glyph metrics-and-raster Cache, font loading and selection, and per-glyph metric/bounds/rasterization queries.",
          ["service","fonts","glyph-cache","rasterization"], "complex",
          "Rust enums (Weight/Style) with conversion helpers and a Cache struct keyed by GlyphKey for memoizing expensive glyph rasterization.")

P = B+'fonts/canvas.rs'
file_node(P, "Defines RasterFormat (pixel formats and bytes-per-pixel) and the Canvas pixel buffer used to hold rasterized glyph bitmaps.",
          ["data-model","rasterization","pixel-buffer"], "simple")

P = B+'fonts/text_layout_system.rs'
file_node(P, "TextLayoutSystem trait abstracting line/text layout and per-character fallback-font requests over the platform font backend.",
          ["type-definition","text-layout","trait","fonts"], "simple")

P = B+'platform/mod.rs'
file_node(P, "Platform abstraction layer: traits for the app Delegate, WindowManager, Window, WindowContext and FontDB plus OS/window/cursor/notification value types shared across native and wasm backends.",
          ["platform","trait","windowing","abstraction"], "complex",
          "Heavy use of trait objects (Delegate, WindowManager, Window) to decouple core UI from OS-specific backends; OperatingSystem enum provides is_mac/is_linux helpers.")

P = B+'platform/wasm.rs'
file_node(P, "WebAssembly platform backend that parses the browser user-agent to report current platform, OS version, browser and version.",
          ["platform","wasm","user-agent","detection"], "moderate")

P = B+'prelude.rs'
file_node(P, "Crate prelude re-exporting the most-used core, elements, platform, presenter and component symbols for ergonomic glob imports.",
          ["barrel","prelude","re-exports"], "simple")

P = B+'presenter.rs'
file_node(P, "Central presenter that drives the layout/paint/event lifecycle: builds the Scene from the view tree, manages a PositionCache, dispatches events and actions, and tracks cursor/repaint scheduling.",
          ["service","layout-engine","rendering","event-dispatch"], "complex",
          "Owns the per-frame pipeline (invalidate -> build_scene -> layout -> paint) and a PositionCache that memoizes element bounds across frames.")

P = B+'presenter_tests.rs'
file_node(P, "Unit test verifying PositionCache caching behavior within the presenter.",
          ["test","layout-engine","caching"], "simple")

P = B+'scene.rs'
file_node(P, "Retained scene graph and draw API: layered primitives (rects, images, icons, glyphs), clipping, z-index, borders, drop shadows and corner radii, plus hit-rect recording for input.",
          ["service","rendering","scene-graph","drawing"], "complex",
          "Builder-style with_* methods on Rect/Border/CornerRadius; Scene maintains ordered Layers and records hit rects for later hit-testing.")

P = B+'text_layout.rs'
file_node(P, "Text shaping and layout engine: produces laid-out Lines/TextFrames with glyph runs, caret positioning, clipping/ellipsis configuration and text styling, backed by a LayoutCache keyed on content+style.",
          ["service","text-layout","shaping","caching"], "complex",
          "Largest module in the crate; LayoutCache memoizes shaped lines by CacheKey to avoid re-shaping unchanged text every frame.")

P = B+'text_layout_tests.rs'
file_node(P, "Unit tests for the text layout engine covering shaping, caret/positioning and caching behavior.",
          ["test","text-layout","shaping"], "moderate")

P = B+'zoom.rs'
file_node(P, "Zoom/scale model: ZoomFactor and a Scale value type used to convert logical to physical sizes across the UI.",
          ["data-model","zoom","scaling"], "simple")

# ui_components
P = B+'ui_components/button.rs'
file_node(P, "Button UI component with text+icon content, alignment, variants and optional tooltip; builds into an Element via the component framework.",
          ["component","button","ui-component","builder"], "complex")
P = B+'ui_components/checkbox.rs'
file_node(P, "Checkbox UI component rendering a labelled toggleable check control built on the shared component framework.",
          ["component","checkbox","ui-component","input"], "moderate")
P = B+'ui_components/chip.rs'
file_node(P, "Chip UI component rendering a compact pill/tag label.",
          ["component","chip","ui-component"], "moderate")
P = B+'ui_components/components.rs'
file_node(P, "Foundation of the ui_components framework: the UiComponent trait, shared UiComponentStyles (size/border/font/padding) with merge semantics, Coords and BorderStyle.",
          ["component","framework","styles","type-definition"], "moderate")
P = B+'ui_components/keyboard_shortcut.rs'
file_node(P, "KeyboardShortcut UI component that renders key chords as styled key caps, mapping keymap keys to platform-appropriate glyphs.",
          ["component","keyboard-shortcut","ui-component","keymap"], "complex")
P = B+'ui_components/link.rs'
file_node(P, "Link UI component rendering clickable hyperlink text with hover/link styling.",
          ["component","link","ui-component"], "moderate")
P = B+'ui_components/list.rs'
file_node(P, "List UI component composing child items with a configurable ListStyle.",
          ["component","list","ui-component"], "simple")
P = B+'ui_components/mod.rs'
file_node(P, "Module barrel re-exporting all ui_components (button, checkbox, slider, switch, etc.).",
          ["barrel","ui-component","re-exports"], "simple")
P = B+'ui_components/progress_bar.rs'
file_node(P, "ProgressBar UI component rendering determinate progress as a filled track.",
          ["component","progress-bar","ui-component"], "simple")
P = B+'ui_components/radio_buttons.rs'
file_node(P, "RadioButtons UI component: a state-handle-backed group of mutually exclusive options with a renderer handling layout, labels and click selection.",
          ["component","radio-buttons","ui-component","state"], "complex")
P = B+'ui_components/segmented_control.rs'
file_node(P, "SegmentedControl UI component presenting a row of selectable button segments with optional labels/tooltips and selection events.",
          ["component","segmented-control","ui-component","event-handler"], "complex")
P = B+'ui_components/slider.rs'
file_node(P, "Slider UI component with a state handle, draggable thumb and configurable track for selecting a value within a range.",
          ["component","slider","ui-component","state"], "complex")
P = B+'ui_components/switch.rs'
file_node(P, "Switch (toggle) UI component backed by a state handle, with optional tooltip and label.",
          ["component","switch","ui-component","state"], "complex")
P = B+'ui_components/text.rs'
file_node(P, "Text UI components: WrappableText plus Span/Paragraph primitives for styled, wrappable rich text.",
          ["component","text","ui-component","typography"], "moderate")
P = B+'ui_components/text_input.rs'
file_node(P, "TextInput UI component wrapping the editor element as a styled single-/multi-line input.",
          ["component","text-input","ui-component","input"], "simple")
P = B+'ui_components/toggle_button.rs'
file_node(P, "ToggleButton UI component rendering an on/off button with label.",
          ["component","toggle-button","ui-component"], "moderate")
P = B+'ui_components/toggle_menu.rs'
file_node(P, "ToggleMenu UI component: a state-handle-backed dropdown menu of toggleable items with a renderer for layout and selection.",
          ["component","menu","ui-component","state"], "complex")
P = B+'ui_components/tool_tip.rs'
file_node(P, "Tooltip UI components (Tooltip and TooltipWithSublabel) rendering hover hint overlays.",
          ["component","tooltip","ui-component","overlay"], "moderate")

# ============ SUB NODES ============
P = B+'fonts.rs'
sub_node("class", P, "Weight", [33,44], "Font weight enum (Thin..Black plus custom) with conversion helpers to/from numeric custom weights.", ["data-model","fonts","enum"], "simple")
sub_node("class", P, "Cache", [206,221], "Per-font glyph cache memoizing advances, typographic/raster bounds and rasterized bitmaps keyed by GlyphKey to avoid recomputing expensive font metrics.", ["singleton","glyph-cache","fonts","performance"], "complex")
sub_node("function", P, "glyph_for_char", [451,494], "Resolves the glyph id for a character in a font, applying fallback handling when the primary font lacks the glyph.", ["fonts","glyph","fallback"], "moderate")

P = B+'fonts/canvas.rs'
sub_node("class", P, "Canvas", [36,45], "Pixel buffer holding a rasterized bitmap (data, size, stride, format) for a glyph or image.", ["data-model","pixel-buffer","rasterization"], "simple")
sub_node("class", P, "RasterFormat", [4,11], "Enum of supported raster pixel formats exposing bytes-per-pixel.", ["data-model","enum","rasterization"], "simple")

P = B+'fonts/text_layout_system.rs'
sub_node("class", P, "TextLayoutSystem", [10,13], "Trait abstracting line/text layout and per-char fallback-font lookup over the platform font backend.", ["trait","text-layout","fonts"], "simple")

P = B+'platform/mod.rs'
sub_node("class", P, "Delegate", [187,273], "Core application delegate trait (25 methods) handling lifecycle, window, input and system callbacks between the platform backend and app.", ["trait","platform","app-delegate","abstraction"], "complex")
sub_node("class", P, "WindowManager", [548,628], "Trait abstracting window creation/management and platform window operations across native and wasm backends.", ["trait","platform","windowing"], "complex")
sub_node("class", P, "Window", [441,459], "Trait describing an OS window: bounds, focus, fullscreen and rendering surface operations.", ["trait","platform","windowing"], "moderate")
sub_node("class", P, "FontDB", [343,431], "Trait abstracting the system font database: enumeration, loading by id/bytes and family lookup.", ["trait","platform","fonts"], "complex")
sub_node("class", P, "OperatingSystem", [656,666], "Enum of supported operating systems with is_mac/is_linux/is_windows and default-shell helpers.", ["data-model","platform","enum"], "simple")

P = B+'platform/wasm.rs'
sub_node("function", P, "current_platform", [55,71], "Detects the current platform from the parsed browser user-agent for the wasm backend.", ["wasm","platform","detection"], "moderate")

P = B+'presenter.rs'
sub_node("class", P, "Presenter", [25,35], "Central presenter owning the view tree, scene, position cache and frame counter; orchestrates the per-frame layout/paint/dispatch pipeline.", ["service","layout-engine","rendering","event-dispatch"], "complex")
sub_node("class", P, "PositionCache", [125,137], "Cache of element bounds/drop-target positions, supporting indefinite and single-frame caching plus visibility/coverage queries.", ["caching","layout-engine","hit-testing"], "moderate")
sub_node("function", P, "build_scene", [333,375], "Builds the Scene for a frame by laying out and painting the view tree starting from the root.", ["rendering","scene-graph","layout"], "moderate")
sub_node("function", P, "dispatch_event", [518,537], "Dispatches an input event through the view tree, producing a DispatchResult with handling/cursor outcomes.", ["event-dispatch","input","hit-testing"], "moderate")

P = B+'scene.rs'
sub_node("class", P, "Scene", [18,27], "Retained scene graph holding ordered layers; exposes draw_rect/image/icon/glyph, layer/clip/z-index management and hit-rect recording.", ["service","scene-graph","rendering","drawing"], "complex")
sub_node("class", P, "CornerRadius", [240,249], "Per-corner radius value type with 16 builder helpers (with_top_left, with_all, merge) for composing rounded-rect geometry.", ["data-model","geometry","builder"], "moderate")
sub_node("function", P, "draw_glyph", [649,670], "Records a glyph draw primitive into the active layer with style/clip applied.", ["rendering","glyph","drawing"], "moderate")

P = B+'text_layout.rs'
sub_node("class", P, "Line", [491,511], "A single laid-out line of text exposing glyph runs, width/height, hit-testing and caret/positioning queries (20 methods).", ["data-model","text-layout","hit-testing"], "complex")
sub_node("class", P, "TextFrame", [689,694], "A multi-line laid-out text frame aggregating Lines with overall geometry and paint operations.", ["data-model","text-layout"], "moderate")
sub_node("class", P, "LayoutCache", [108,111], "Cache memoizing shaped lines/frames by CacheKey so unchanged text is not re-shaped each frame.", ["caching","text-layout","performance"], "moderate")
sub_node("class", P, "TextStyle", [562,574], "Text style value type (font, size, weight, color, decorations) used as part of the layout cache key.", ["data-model","text-layout","styling"], "moderate")

P = B+'zoom.rs'
sub_node("class", P, "Scale", [22,30], "Scale value type converting logical to physical units for high-DPI rendering.", ["data-model","scaling","zoom"], "simple")

# ui_components sub-nodes (primary component structs/traits)
P = B+'ui_components/button.rs'
sub_node("class", P, "Button", [78,98], "Button component (21 builder methods) configuring text+icon content, variant, alignment and tooltip before building an Element.", ["component","button","builder"], "complex")
P = B+'ui_components/checkbox.rs'
sub_node("class", P, "Checkbox", [25,37], "Labelled checkbox component with checked state and click toggling.", ["component","checkbox","input"], "moderate")
P = B+'ui_components/chip.rs'
sub_node("class", P, "Chip", [10,15], "Compact pill/tag label component.", ["component","chip"], "simple")
P = B+'ui_components/components.rs'
sub_node("class", P, "UiComponent", [160,165], "Core trait for ui_components: build() into an Element and with_style() to apply shared UiComponentStyles.", ["trait","component","framework"], "simple")
sub_node("class", P, "UiComponentStyles", [55,72], "Shared style struct (size, border, font, padding, margin) with merge semantics layering overrides over defaults.", ["data-model","styles","framework"], "moderate")
P = B+'ui_components/keyboard_shortcut.rs'
sub_node("class", P, "KeyboardShortcut", [20,28], "Component rendering a key chord as styled key caps, mapping keymap keys to platform glyphs.", ["component","keyboard-shortcut","keymap"], "moderate")
P = B+'ui_components/link.rs'
sub_node("class", P, "Link", [9,18], "Clickable hyperlink text component with hover/link styling.", ["component","link"], "moderate")
P = B+'ui_components/list.rs'
sub_node("class", P, "List", [22,26], "Component composing child items with a configurable ListStyle.", ["component","list"], "simple")
P = B+'ui_components/progress_bar.rs'
sub_node("class", P, "ProgressBar", [4,7], "Determinate progress bar component rendering a filled track.", ["component","progress-bar"], "simple")
P = B+'ui_components/radio_buttons.rs'
sub_node("class", P, "RadioButtons", [347,350], "Mutually-exclusive radio button group component backed by a shared state handle.", ["component","radio-buttons","state"], "moderate")
sub_node("class", P, "RadioButtonStateHandle", [93,95], "Shared, cloneable handle to radio group selection state.", ["state","handle","component"], "simple")
P = B+'ui_components/segmented_control.rs'
sub_node("class", P, "SegmentedControl", [22,31], "Row of selectable button segments with optional labels/tooltips emitting selection events.", ["component","segmented-control","event-handler"], "complex")
P = B+'ui_components/slider.rs'
sub_node("class", P, "Slider", [100,114], "Slider component (17 methods) with draggable thumb and configurable track for picking a value in a range.", ["component","slider","input"], "complex")
sub_node("class", P, "SliderStateHandle", [50,55], "Shared, cloneable handle to slider value/drag state.", ["state","handle","component"], "simple")
P = B+'ui_components/switch.rs'
sub_node("class", P, "Switch", [45,56], "Toggle switch component backed by a state handle with optional tooltip/label.", ["component","switch","state"], "moderate")
P = B+'ui_components/text.rs'
sub_node("class", P, "WrappableText", [12,20], "Wrappable styled text component composing Spans into a Paragraph.", ["component","text","typography"], "moderate")
sub_node("class", P, "Paragraph", [155,157], "Paragraph primitive aggregating styled Spans for rich text.", ["data-model","text","typography"], "simple")
P = B+'ui_components/text_input.rs'
sub_node("class", P, "TextInput", [5,8], "Styled text input component wrapping the editor element.", ["component","text-input","input"], "simple")
P = B+'ui_components/toggle_button.rs'
sub_node("class", P, "ToggleButton", [13,21], "On/off toggle button component with label.", ["component","toggle-button"], "moderate")
P = B+'ui_components/toggle_menu.rs'
sub_node("class", P, "ToggleMenu", [207,212], "Dropdown menu component of toggleable items backed by a shared state handle.", ["component","menu","state"], "moderate")
P = B+'ui_components/tool_tip.rs'
sub_node("class", P, "Tooltip", [6,9], "Hover hint overlay component.", ["component","tooltip","overlay"], "simple")
sub_node("class", P, "TooltipWithSublabel", [73,77], "Tooltip overlay variant with a primary label and secondary sublabel.", ["component","tooltip","overlay"], "simple")

# ============ IMPORT EDGES ============
for filepath, targets in imp.items():
    for t in targets:
        edges.append({"source": f"file:{filepath}", "target": f"file:{t}", "type": "imports", "direction": "forward", "weight": 0.7})

# ============ tested_by EDGES ============
edges.append({"source": f"file:{B}presenter.rs", "target": f"file:{B}presenter_tests.rs", "type": "tested_by", "direction": "forward", "weight": 0.5})
edges.append({"source": f"file:{B}text_layout.rs", "target": f"file:{B}text_layout_tests.rs", "type": "tested_by", "direction": "forward", "weight": 0.5})
edges.append({"source": f"file:{B}scene.rs", "target": f"file:{B}elements/text_tests.rs", "type": "tested_by", "direction": "forward", "weight": 0.5})

# ---- validation: import count ----
need = sum(len(v) for v in imp.values())
got = sum(1 for e in edges if e['type']=='imports')
assert need==got, f"import mismatch {need} vs {got}"
print("nodes", len(nodes), "edges", len(edges), "imports", got)

# ---- partition ----
batchFiles = sorted([f"{p}" for p in imp.keys()])
nodeCount=len(nodes); edgeCount=len(edges)
if nodeCount<=60 and edgeCount<=120:
    parts=1
else:
    parts=math.ceil(max(nodeCount/60, edgeCount/120))
print("parts", parts)

outdir='/home/mhb/warp/.understand-anything/intermediate'
os.makedirs(outdir, exist_ok=True)

if parts==1:
    json.dump({"nodes":nodes,"edges":edges}, open(f"{outdir}/batch-3.json","w"), indent=2)
    print("wrote batch-3.json")
else:
    chunk=math.ceil(len(batchFiles)/parts)
    groups=[set(batchFiles[i*chunk:(i+1)*chunk]) for i in range(parts)]
    # map node id -> filePath
    def node_fp(n):
        return n.get('filePath')
    for k in range(parts):
        grp=groups[k]
        pnodes=[n for n in nodes if node_fp(n) in grp]
        pnodeids=set(n['id'] for n in pnodes)
        pedges=[e for e in edges if e['source'] in pnodeids]
        json.dump({"nodes":pnodes,"edges":pedges}, open(f"{outdir}/batch-3-part-{k+1}.json","w"), indent=2)
        print(f"part {k+1}: files={len(grp)} nodes={len(pnodes)} edges={len(pedges)}")
