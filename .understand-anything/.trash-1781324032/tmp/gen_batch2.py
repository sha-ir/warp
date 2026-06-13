import json, math, os

BASE = "crates/warpui_core/src/"

# ---- import data (verbatim from batchImportData) ----
imports = {
 "core/autotracking/autotracking_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "core/view/context_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "debug/mod.rs": ["debug/root_view.rs","debug/view_tree_debug_view.rs"],
 "debug/root_view.rs": ["elements/mod.rs"],
 "debug/view_tree_debug_view.rs": ["elements/mod.rs"],
 "elements/child_view.rs": ["presenter.rs"],
 "elements/clipped_scrollable.rs": ["event.rs","scene.rs","units.rs"],
 "elements/clipped_scrollable_tests.rs": ["elements/mod.rs","platform/mod.rs","units.rs"],
 "elements/clipped_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "elements/container_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "elements/debug.rs": ["event.rs","scene.rs"],
 "elements/drag/draggable.rs": ["elements/mod.rs","event.rs","platform/mod.rs","presenter.rs","scene.rs"],
 "elements/drag/drop_target.rs": ["elements/mod.rs","event.rs"],
 "elements/drag/mod.rs": ["elements/drag/draggable.rs","elements/drag/drop_target.rs"],
 "elements/drag_resize.rs": ["event.rs","platform/mod.rs"],
 "elements/event_handler_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "elements/flex/mod_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "elements/flex/wrap_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "elements/formatted_text_element_tests.rs": ["elements/mod.rs","fonts.rs","text_layout.rs","text/mod.rs"],
 "elements/hoverable_tests.rs": ["elements/mod.rs","fonts.rs","platform/mod.rs"],
 "elements/list.rs": [],
 "elements/list_tests.rs": ["elements/mod.rs"],
 "elements/mod.rs": ["elements/align.rs","elements/child_view.rs","elements/clipped_scrollable.rs","elements/clipped.rs","elements/constrained_box.rs","elements/container.rs","elements/debug.rs","elements/dismiss.rs","elements/drag_resize.rs","elements/drag/mod.rs","elements/empty.rs","elements/event_handler.rs","elements/flex/mod.rs","elements/formatted_text_element.rs","elements/hoverable.rs","elements/icon.rs","elements/image.rs","elements/list.rs","elements/live.rs","elements/min_size.rs","elements/new_scrollable/mod.rs","elements/percentage.rs","elements/rect.rs","elements/resizable.rs","elements/scrollable.rs","elements/selectable_area.rs","elements/shared_scrollbar.rs","elements/shimmering_text.rs","elements/size_constraint_switch.rs","elements/stack/mod.rs","elements/table/mod.rs","elements/text.rs","elements/uniform_list.rs","elements/viewported_list.rs","event.rs","platform/mod.rs","scene.rs","text/mod.rs","text/word_boundaries.rs"],
 "elements/percentage.rs": [],
 "elements/rect.rs": ["event.rs","scene.rs"],
 "elements/resizable.rs": ["event.rs","platform/mod.rs"],
 "elements/scrollable.rs": ["elements/mod.rs","event.rs","scene.rs","units.rs"],
 "elements/scrollable_tests.rs": ["elements/mod.rs","platform/mod.rs","presenter.rs"],
 "elements/shimmering_text.rs": ["elements/mod.rs","elements/shimmering_text/config.rs","elements/shimmering_text/glyph_index.rs","fonts.rs","platform/mod.rs","text_layout.rs"],
 "elements/shimmering_text/config.rs": [],
 "elements/shimmering_text/glyph_index.rs": [],
 "elements/size_constraint_switch_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "elements/stack/mod_tests.rs": ["elements/mod.rs","platform/mod.rs"],
 "elements/stack/offset_positioning.rs": ["presenter.rs"],
}

# ---- file nodes ----
# (rel, name, type, summary, tags, complexity, languageNotes|None)
files = [
 ("core/autotracking/autotracking_tests.rs","autotracking_tests.rs","file",
  "Unit tests for the reactive autotracking system, verifying that views and models re-render only when a tracked dependency actually changes.",
  ["test","autotracking","reactivity","rendering"],"complex",None),
 ("core/view/context_tests.rs","context_tests.rs","file",
  "Unit tests for the view context's task-spawning API, covering spawn, abortable spawn, and the view spawner.",
  ["test","view-context","async","task-spawning"],"moderate",None),
 ("debug/mod.rs","mod.rs","file",
  "Module barrel for the debug view-tree tooling, re-exporting the root debug view and the view-tree inspector.",
  ["barrel","module","debug"],"simple",None),
 ("debug/root_view.rs","root_view.rs","file",
  "Top-level debug overlay view that hosts the view-tree inspector as its only child.",
  ["debug","view","ui-component"],"simple",None),
 ("debug/view_tree_debug_view.rs","view_tree_debug_view.rs","file",
  "Interactive debug panel that renders the live view hierarchy as an indented, hoverable list for highlighting views in the running UI.",
  ["debug","view-tree","inspector","ui-component"],"complex",None),
 ("elements/child_view.rs","child_view.rs","file",
  "Single-line re-export wiring a child-view helper from the presenter layer into the elements module.",
  ["re-export","view","stub"],"simple",None),
 ("elements/clipped_scrollable.rs","clipped_scrollable.rs","file",
  "Scrollable element that clips its content and drives scroll position, selection-anchored scrolling, and scroll-to-position behavior along a single axis.",
  ["scrollable","element","clipping","scroll"],"complex",None),
 ("elements/clipped_scrollable_tests.rs","clipped_scrollable_tests.rs","file",
  "Unit tests for the clipped scrollable element, exercising scroll-to-position behavior.",
  ["test","scrollable","clipping"],"moderate",None),
 ("elements/clipped_tests.rs","clipped_tests.rs","file",
  "Unit tests for the clipped element, verifying click handling through stacked and clipped layers.",
  ["test","clipping","event-handling"],"complex",None),
 ("elements/container_tests.rs","container_tests.rs","file",
  "Unit tests for the container element, verifying overlay click handling.",
  ["test","container","event-handling"],"moderate",None),
 ("elements/debug.rs","debug.rs","file",
  "Debug element wrapper that overlays a configurable colored, optionally dashed border around its child for visualizing layout bounds, plus a Debug extension trait.",
  ["debug","element","layout","border"],"moderate",None),
 ("elements/drag/draggable.rs","draggable.rs","file",
  "Draggable element implementing pointer-driven drag-and-drop with drag thresholds, axis locking, bounds clamping, drop-target detection, and drag lifecycle callbacks.",
  ["drag-and-drop","element","interaction","gesture"],"complex",None),
 ("elements/drag/drop_target.rs","drop_target.rs","file",
  "Drop-target element that registers its bounds and payload data so draggables can detect when they hover or release over it.",
  ["drag-and-drop","drop-target","element","interaction"],"moderate",None),
 ("elements/drag/mod.rs","mod.rs","file",
  "Module barrel re-exporting the draggable and drop-target elements.",
  ["barrel","module","drag-and-drop"],"simple",None),
 ("elements/drag_resize.rs","drag_resize.rs","file",
  "Element that adds a vertical drag-resize handle to its child, tracking drag state and emitting resize-update and resize-end callbacks.",
  ["resize","element","interaction","event-handler"],"moderate",None),
 ("elements/event_handler_tests.rs","event_handler_tests.rs","file",
  "Unit tests for the event-handler element, covering layered click handling, mouse-in behavior, and event propagation.",
  ["test","event-handling","interaction"],"complex",None),
 ("elements/flex/mod_tests.rs","mod_tests.rs","file",
  "Unit tests for the flex layout element, asserting main/cross-axis alignment and spacing across rows and columns.",
  ["test","flex","layout"],"complex",None),
 ("elements/flex/wrap_tests.rs","wrap_tests.rs","file",
  "Unit tests for the flex wrap element, asserting how children wrap across runs under spacing and size constraints.",
  ["test","flex","wrap","layout"],"complex",None),
 ("elements/formatted_text_element_tests.rs","formatted_text_element_tests.rs","file",
  "Unit tests for the formatted-text element, covering heading font-size multipliers, multibyte text replacements, and smart selection.",
  ["test","text","formatting"],"complex",None),
 ("elements/hoverable_tests.rs","hoverable_tests.rs","file",
  "Unit tests for the hoverable element, covering click handling and hover-in/out behavior with and without delays.",
  ["test","hover","interaction"],"complex",None),
 ("elements/list.rs","list.rs","file",
  "Ordered-list numbering model that tracks indentation levels and auto-assigns sequential numbers, rendering them as decimals, letters, or roman numerals.",
  ["list","numbering","formatting","data-model"],"moderate",None),
 ("elements/list_tests.rs","list_tests.rs","file",
  "Unit tests for the ordered-list numbering model, covering automatic numbering, indent jumps, resets, and roman/alphabet conversion.",
  ["test","list","numbering"],"complex",None),
 ("elements/mod.rs","mod.rs","file",
  "Core elements module defining the foundational Element and ParentElement traits, geometry primitives (Point, Axis, Margin, Padding, Fill), and selection/clickable traits, while re-exporting every concrete element type.",
  ["barrel","element","trait-definition","geometry","core"],"complex",
  "Central trait module: defines the object-safe Element trait implemented by every UI element, plus extension traits on Vector2F/RectF."),
 ("elements/percentage.rs","percentage.rs","file",
  "Element that sizes its child to a percentage of the available width and/or height.",
  ["layout","element","sizing","percentage"],"moderate",None),
 ("elements/rect.rs","rect.rs","file",
  "Primitive rectangle element supporting solid or gradient fills, corner radius, borders, and drop shadows.",
  ["element","rendering","primitive","geometry"],"moderate",None),
 ("elements/resizable.rs","resizable.rs","file",
  "Resizable element with a draggable dragbar on a configurable side, clamping size within bounds and emitting resize lifecycle callbacks.",
  ["resize","element","interaction","layout"],"complex",None),
 ("elements/scrollable.rs","scrollable.rs","file",
  "Scrollable element rendering a draggable scrollbar thumb and handling mousewheel, drag, and click-to-jump scrolling along one axis.",
  ["scrollable","element","scrollbar","interaction"],"complex",None),
 ("elements/scrollable_tests.rs","scrollable_tests.rs","file",
  "Unit tests for the scrollable element, covering clipped scrolling, scrollbar-gutter clicks, and stacked-view scroll handling.",
  ["test","scrollable","scrollbar"],"complex",None),
 ("elements/shimmering_text.rs","shimmering_text.rs","file",
  "Text element that renders an animated shimmer sweep across its glyphs by computing per-glyph color overrides over time.",
  ["text","animation","element","rendering"],"complex",None),
 ("elements/shimmering_text/config.rs","config.rs","file",
  "Configuration struct controlling shimmer animation period, radius, and padding.",
  ["config","animation","shimmer"],"simple",None),
 ("elements/shimmering_text/glyph_index.rs","glyph_index.rs","file",
  "Newtype wrapper around a glyph index with an f32 accessor.",
  ["newtype","glyph","utility"],"simple",None),
 ("elements/size_constraint_switch_tests.rs","size_constraint_switch_tests.rs","file",
  "Unit tests for the size-constraint-switch element, verifying which child renders under max-width/height/size conditions.",
  ["test","layout","sizing"],"complex",None),
 ("elements/stack/mod_tests.rs","mod_tests.rs","file",
  "Unit tests for the stack element, covering z-index painting and relative positioning bound to window and anchors.",
  ["test","stack","positioning"],"complex",None),
 ("elements/stack/offset_positioning.rs","offset_positioning.rs","file",
  "Geometry engine for stack child positioning: computes child position and size constraints from parent/anchor relationships, axis anchors, and pixel/percentage offsets, with window-bounds clamping.",
  ["layout","positioning","geometry","anchor","stack"],"complex",
  "Heavy use of enums (anchors, bounds modes, offset types) to model the combinatorics of 2D relative positioning."),
]

# ---- sub nodes: (filerel, kind, name, startLine, endLine, summary, tags, exported, complexity) ----
subs = [
 ("debug/root_view.rs","class","DebugRootView",10,12,
  "Root debug view that wraps and displays the view-tree inspector as its child.",
  ["debug","view","ui-component"],True,"simple"),

 ("debug/view_tree_debug_view.rs","class","ViewTreeDebugView",88,94,
  "Stateful debug view that renders the live view hierarchy as a hoverable uniform list and handles highlight actions.",
  ["debug","view-tree","inspector","stateful"],True,"complex"),
 ("debug/view_tree_debug_view.rs","class","ViewTreeDebugAction",76,79,
  "Action enum for the view-tree debug view, e.g. highlighting a selected view.",
  ["debug","action","enum"],True,"simple"),

 ("elements/clipped_scrollable.rs","class","ClippedScrollStateHandle",58,65,
  "Shared handle exposing scroll position, selection-anchor adjustment, and hover controls for a clipped scrollable.",
  ["scroll","state-handle","scrollable"],True,"complex"),
 ("elements/clipped_scrollable.rs","class","ClippedScrollable",187,198,
  "Single-axis scrollable element that clips content and drives scroll-to-position and selection-anchored scrolling.",
  ["scrollable","element","clipping"],True,"complex"),
 ("elements/clipped_scrollable.rs","class","ScrollToPositionMode",21,30,
  "Enum selecting how a target is scrolled into view: fully into view or top-aligned into view.",
  ["scroll","enum","mode"],True,"simple"),

 ("elements/debug.rs","class","DebugElement",15,22,
  "Element wrapper that paints a configurable colored, optionally dashed debug border around its child.",
  ["debug","element","border"],True,"moderate"),
 ("elements/debug.rs","class","Debug",110,114,
  "Extension trait adding .debug() and .debug_with_options() wrappers to any element.",
  ["debug","trait","extension"],True,"simple"),

 ("elements/drag/draggable.rs","class","DraggableState",27,30,
  "Shared drag state tracking whether a drag is active, the cursor offset within the element, and overlay-paint suppression.",
  ["drag","state","interaction"],True,"moderate"),
 ("elements/drag/draggable.rs","class","Draggable",239,263,
  "Element implementing drag-and-drop with configurable thresholds, axis locking, bounds, drop-target detection, and lifecycle callbacks.",
  ["drag-and-drop","element","interaction"],True,"complex"),
 ("elements/drag/draggable.rs","class","DragState",94,116,
  "Enum modeling the drag lifecycle: idle, waiting-to-drag, and actively dragging.",
  ["drag","state","enum"],False,"simple"),

 ("elements/drag/drop_target.rs","class","DropTarget",47,50,
  "Element that registers its bounds and payload data so draggables can detect drops over it.",
  ["drop-target","element","drag-and-drop"],True,"moderate"),
 ("elements/drag/drop_target.rs","class","DropTargetPosition",22,25,
  "Records a drop target's bounds and associated drop data for hit testing.",
  ["drop-target","geometry","data-model"],True,"simple"),

 ("elements/drag_resize.rs","class","DragResizeState",24,27,
  "Tracks the active drag-resize gesture, consuming vertical pointer deltas.",
  ["resize","state","interaction"],True,"simple"),
 ("elements/drag_resize.rs","class","DragResizeElement",63,70,
  "Element that adds a drag-resize handle to its child and emits resize-update and resize-end callbacks.",
  ["resize","element","interaction"],True,"moderate"),

 ("elements/list.rs","class","ListIndentLevel",20,24,
  "Bounded ordered-list indentation level supporting shift-left/right and per-level number formatting.",
  ["list","indentation","enum"],True,"moderate"),
 ("elements/list.rs","class","ListNumbering",96,106,
  "Stateful ordered-list numbering that assigns sequential indices per indentation level.",
  ["list","numbering","stateful"],True,"moderate"),
 ("elements/list.rs","function","number_to_roman",177,191,
  "Converts a 0-based integer into its lowercase roman-numeral string for ordered list labels.",
  ["formatting","conversion","utility"],False,"simple"),
 ("elements/list.rs","function","number_to_alphabet",164,173,
  "Converts a 0-based integer into a repeating-alphabet label (a, b, ..., aa) for ordered lists.",
  ["formatting","conversion","utility"],False,"simple"),

 ("elements/mod.rs","class","Element",106,179,
  "Core object-safe trait implemented by every UI element, defining layout, after-layout, paint, sizing, event dispatch, and bounds.",
  ["trait","element","core","layout"],True,"complex"),
 ("elements/mod.rs","class","ParentElement",181,202,
  "Trait for elements that accept and manage child elements via add_child/with_children builders.",
  ["trait","element","composition"],True,"moderate"),
 ("elements/mod.rs","class","SelectableElement",754,799,
  "Trait for elements participating in text selection: get/expand selection, smart-select, and clickable-bounds calculation.",
  ["trait","selection","element"],True,"moderate"),
 ("elements/mod.rs","class","Axis",248,251,
  "Horizontal/vertical axis enum with inversion and point-projection helpers used throughout layout.",
  ["geometry","axis","enum"],True,"simple"),

 ("elements/percentage.rs","class","Percentage",9,13,
  "Element that sizes its child to a percentage of the available width and/or height.",
  ["layout","element","sizing"],True,"moderate"),

 ("elements/rect.rs","class","Rect",11,21,
  "Rectangle primitive element with solid/gradient fills, corner radius, borders, and drop shadows.",
  ["element","primitive","rendering"],True,"moderate"),

 ("elements/resizable.rs","class","Resizable",24,38,
  "Element exposing a draggable dragbar that lets the user resize its child within bounds, with resize lifecycle callbacks.",
  ["resize","element","interaction"],True,"complex"),
 ("elements/resizable.rs","class","ResizableState",50,54,
  "Shared resizable state tracking current size, bounds, and resize mode.",
  ["resize","state","interaction"],True,"moderate"),

 ("elements/scrollable.rs","class","Scrollable",137,181,
  "Element rendering a draggable scrollbar and handling wheel, drag, and click-to-jump scrolling along one axis.",
  ["scrollable","element","scrollbar"],True,"complex"),
 ("elements/scrollable.rs","class","ScrollableElement",75,96,
  "Trait for elements exposing scroll data and mousewheel handling to the scroll machinery.",
  ["trait","scroll","element"],True,"moderate"),

 ("elements/shimmering_text.rs","class","ShimmeringTextElement",78,93,
  "Text element that computes animated per-glyph shimmer color overrides over time and paints the result.",
  ["text","animation","element"],True,"complex"),

 ("elements/shimmering_text/config.rs","class","ShimmerConfig",18,27,
  "Configuration for the shimmer animation: period, shimmer radius, and padding.",
  ["config","animation","shimmer"],True,"simple"),

 ("elements/stack/offset_positioning.rs","class","OffsetPositioning",11,14,
  "Computes a stack child's position and size constraint from parent/anchor relationships and pixel/percentage offsets.",
  ["positioning","layout","geometry"],True,"complex"),
 ("elements/stack/offset_positioning.rs","class","Anchor",238,248,
  "Nine-point anchor enum with x/y axis projection used for relative positioning of stack children.",
  ["anchor","geometry","enum"],True,"moderate"),
]

# ---- implements edges: (impl_file, impl_class, target_file, target_class) ----
implements = [
 ("elements/debug.rs","DebugElement","elements/mod.rs","Element"),
 ("elements/drag/draggable.rs","Draggable","elements/mod.rs","Element"),
 ("elements/drag/drop_target.rs","DropTarget","elements/mod.rs","Element"),
 ("elements/drag_resize.rs","DragResizeElement","elements/mod.rs","Element"),
 ("elements/clipped_scrollable.rs","ClippedScrollable","elements/mod.rs","Element"),
 ("elements/clipped_scrollable.rs","ClippedScrollable","elements/scrollable.rs","ScrollableElement"),
 ("elements/percentage.rs","Percentage","elements/mod.rs","Element"),
 ("elements/rect.rs","Rect","elements/mod.rs","Element"),
 ("elements/resizable.rs","Resizable","elements/mod.rs","Element"),
 ("elements/scrollable.rs","Scrollable","elements/mod.rs","Element"),
 ("elements/scrollable.rs","Scrollable","elements/scrollable.rs","ScrollableElement"),
 ("elements/shimmering_text.rs","ShimmeringTextElement","elements/mod.rs","Element"),
]

# ---- tested_by edges: (production_rel, test_rel) -- only where production is an in-batch node ----
tested = [
 ("elements/clipped_scrollable.rs","elements/clipped_scrollable_tests.rs"),
 ("elements/scrollable.rs","elements/scrollable_tests.rs"),
 ("elements/list.rs","elements/list_tests.rs"),
]

# ---- partition (alphabetical, 2 parts of 17) ----
all_rel = [f[0] for f in files]
ordered = sorted(all_rel)
assert len(ordered)==34
part_of = {}
half = math.ceil(len(ordered)/2)  # 17
for i,r in enumerate(ordered):
    part_of[r] = 1 if i < half else 2

def fid(rel): return "file:"+BASE+rel
def cid(rel,name): return "class:"+BASE+rel+":"+name
def fnid(rel,name): return "function:"+BASE+rel+":"+name

nodes = {1:[], 2:[]}
edges = {1:[], 2:[]}

# file nodes
for rel,name,typ,summ,tags,cx,ln in files:
    n = {"id":fid(rel),"type":typ,"name":name,"filePath":BASE+rel,
         "summary":summ,"tags":tags,"complexity":cx}
    if ln: n["languageNotes"]=ln
    nodes[part_of[rel]].append(n)

# sub nodes + contains/exports
for rel,kind,name,s,e,summ,tags,exp,cx in subs:
    p = part_of[rel]
    nid = cid(rel,name) if kind=="class" else fnid(rel,name)
    nodes[p].append({"id":nid,"type":kind,"name":name,"filePath":BASE+rel,
                     "lineRange":[s,e],"summary":summ,"tags":tags,"complexity":cx})
    edges[p].append({"source":fid(rel),"target":nid,"type":"contains","direction":"forward","weight":1.0})
    if exp:
        edges[p].append({"source":fid(rel),"target":nid,"type":"exports","direction":"forward","weight":0.8})

# imports
for rel, targets in imports.items():
    p = part_of[rel]
    for t in targets:
        edges[p].append({"source":fid(rel),"target":"file:"+BASE+t,"type":"imports","direction":"forward","weight":0.7})

# implements (edge lives with source's part)
for irel,iclass,trel,tclass in implements:
    p = part_of[irel]
    edges[p].append({"source":cid(irel,iclass),"target":cid(trel,tclass),"type":"implements","direction":"forward","weight":0.9})

# tested_by (source = production)
for prod,test in tested:
    p = part_of[prod]
    edges[p].append({"source":fid(prod),"target":fid(test),"type":"tested_by","direction":"forward","weight":0.5})

outdir = "/home/mhb/warp/.understand-anything/intermediate"
os.makedirs(outdir, exist_ok=True)

# import self-check
imp_total = sum(len(v) for v in imports.values())
imp_emitted = sum(1 for p in (1,2) for ed in edges[p] if ed["type"]=="imports")
assert imp_total==imp_emitted==107, (imp_total,imp_emitted)

for k in (1,2):
    frag = {"nodes":nodes[k],"edges":edges[k]}
    path = os.path.join(outdir, f"batch-2-part-{k}.json")
    with open(path,"w") as fh:
        json.dump(frag, fh, indent=2)
    # validate node ids referenced by edges within part OR are file:/class:/function: refs
    nid_set = {n["id"] for n in nodes[k]}
    for ed in edges[k]:
        assert ed["source"]!=ed["target"], ed
    print(f"part {k}: nodes={len(nodes[k])} edges={len(edges[k])} -> {path}")
    # breakdown
    from collections import Counter
    c = Counter(ed["type"] for ed in edges[k])
    print("   edge types:", dict(c))

print("TOTAL nodes:", len(nodes[1])+len(nodes[2]), "edges:", len(edges[1])+len(edges[2]))
print("imports emitted:", imp_emitted)
