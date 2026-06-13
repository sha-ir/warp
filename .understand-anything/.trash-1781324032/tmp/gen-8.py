import json, math, os

ROOT = '/home/mhb/warp'
OUT_DIR = os.path.join(ROOT, '.understand-anything/intermediate')

# Load batchImportData
with open(os.path.join(OUT_DIR, 'batches.json')) as f:
    bdata = json.load(f)
batch = next(b for b in bdata['batches'] if b['batchIndex'] == 8)
imp = batch['batchImportData']
files_in_batch = [f['path'] for f in batch['files']]

nodes = []
edges = []

def fnode(path, name, summary, tags, complexity, notes=None):
    n = {"id": f"file:{path}", "type": "file", "name": name, "filePath": path,
         "summary": summary, "tags": tags, "complexity": complexity}
    if notes: n["languageNotes"] = notes
    nodes.append(n)

def cls(path, name, lr, summary, tags, complexity, notes=None):
    n = {"id": f"class:{path}:{name}", "type": "class", "name": name, "filePath": path,
         "lineRange": lr, "summary": summary, "tags": tags, "complexity": complexity}
    if notes: n["languageNotes"] = notes
    nodes.append(n)
    edges.append({"source": f"file:{path}", "target": f"class:{path}:{name}", "type": "contains", "direction": "forward", "weight": 1.0})

def fn(path, name, lr, summary, tags, complexity):
    nid = f"function:{path}:{name}"
    nodes.append({"id": nid, "type": "function", "name": name, "filePath": path,
                  "lineRange": lr, "summary": summary, "tags": tags, "complexity": complexity})
    edges.append({"source": f"file:{path}", "target": nid, "type": "contains", "direction": "forward", "weight": 1.0})

def export(path, kind, name):
    edges.append({"source": f"file:{path}", "target": f"{kind}:{path}:{name}", "type": "exports", "direction": "forward", "weight": 0.8})

def implements(path, cname, target):
    edges.append({"source": f"class:{path}:{cname}", "target": target, "type": "implements", "direction": "forward", "weight": 0.9})

def tested_by(prod, test):
    edges.append({"source": f"file:{prod}", "target": f"file:{test}", "type": "tested_by", "direction": "forward", "weight": 0.5})

RB = "class:crates/editor/src/render/element/mod.rs:RenderableBlock"

# ---- 1. task_list.rs ----
p = "crates/editor/src/render/element/task_list.rs"
fnode(p, "task_list.rs", "Renderable element for markdown task lists (checkbox bullets); builds checkbox icon + content layout from styles and a viewport item, then lays out and paints it.", ["component","renderer","markdown","ui-element"], "moderate")
cls(p, "RenderableTaskList", [23,28], "RenderableBlock implementation for a task-list (checkbox) line, holding the checkbox icon, sizing, and placeholder content.", ["component","renderer","data-model"], "moderate")
fn(p, "new", [31,98], "Constructs a RenderableTaskList from completion state, styles, viewport item and mouse state, assembling the checkbox icon and click target.", ["factory","renderer","markdown"], "moderate")
fn(p, "paint", [139,171], "Paints the checkbox icon and the task-list content into the render context at the resolved bounds.", ["renderer","ui-element","paint"], "moderate")
implements(p, "RenderableTaskList", RB)
export(p, "class", "RenderableTaskList")

# ---- 2. temporary_block.rs ----
p = "crates/editor/src/render/element/temporary_block.rs"
fnode(p, "temporary_block.rs", "Renderable element for transient overlay blocks (e.g. inline decorations shown during edits) layered over the normal content.", ["component","renderer","ui-element","overlay"], "moderate")
cls(p, "RenderableTemporaryBlock", [8,12], "RenderableBlock implementation wrapping a viewport item with an overlay decoration and text decoration for temporary on-screen blocks.", ["component","renderer","data-model"], "moderate")
fn(p, "paint", [45,102], "Paints the temporary block's decoration and decorated text overlay into the render context.", ["renderer","paint","overlay"], "moderate")
implements(p, "RenderableTemporaryBlock", RB)
export(p, "class", "RenderableTemporaryBlock")

# ---- 3. text_block.rs ----
p = "crates/editor/src/render/element/text_block.rs"
fnode(p, "text_block.rs", "Minimal renderable element wrapping a viewport item to paint a plain text block.", ["component","renderer","ui-element"], "simple")
cls(p, "RenderableTextBlock", [7,9], "RenderableBlock implementation for a plain paragraph/text block, delegating layout to its viewport item.", ["component","renderer"], "simple")
fn(p, "paint", [30,47], "Paints the text block's laid-out paragraph content into the render context.", ["renderer","paint"], "simple")
implements(p, "RenderableTextBlock", RB)
export(p, "class", "RenderableTextBlock")

# ---- 4. unordered_list.rs ----
p = "crates/editor/src/render/element/unordered_list.rs"
fnode(p, "unordered_list.rs", "Renderable element for markdown bullet (unordered) lists; draws the bullet glyph at the correct indent level alongside the list item content.", ["component","renderer","markdown","ui-element"], "moderate")
cls(p, "RenderableBulletList", [17,22], "RenderableBlock implementation for a bullet list item, holding the bullet glyph, its size, and the placeholder content.", ["component","renderer","data-model"], "moderate")
fn(p, "new", [25,53], "Builds a RenderableBulletList for a given indent level, selecting the bullet glyph and computing its placement from styles.", ["factory","renderer","markdown"], "moderate")
fn(p, "paint", [85,122], "Paints the bullet glyph and the list item content into the render context.", ["renderer","paint","ui-element"], "moderate")
implements(p, "RenderableBulletList", RB)
export(p, "class", "RenderableBulletList")

# ---- 5. layout.rs ----
p = "crates/editor/src/render/layout.rs"
fnode(p, "layout.rs", "Text layout engine: turns text and rich-text styles into laid-out text frames, resolving fonts, paragraph styles, style runs, and converting markdown inline nodes into styled text.", ["service","text-layout","markdown","rendering"], "complex")
cls(p, "TextLayout", [30,36], "Layout helper bundling the layout cache, font cache, rich-text styles and max width used to lay out paragraphs and placeholders.", ["service","text-layout","factory"], "complex")
fn(p, "style_and_font", [165,214], "Resolves a paragraph's effective font and style attributes by merging paragraph styles with rich-text style overrides.", ["text-layout","styling"], "moderate")
fn(p, "markdown_inline_to_text_and_style_runs", [247,313], "Flattens a markdown inline tree into plain text plus the per-range style runs (links, inline code, emphasis) needed to lay it out.", ["markdown","serialization","text-layout"], "complex")
fn(p, "layout_text_with_options", [104,128], "Lays out a string into a text frame with explicit max width and alignment options, applying the given style runs.", ["text-layout","rendering"], "moderate")
fn(p, "layout_placeholder", [131,151], "Lays out placeholder text for an empty block of a given type.", ["text-layout","rendering"], "moderate")
export(p, "class", "TextLayout")

# ---- 6. render/mod.rs ----
p = "crates/editor/src/render/mod.rs"
fnode(p, "mod.rs", "Barrel module for the editor render layer, re-exporting the element, layout and model submodules.", ["barrel","entry-point","module"], "simple")

# ---- 7. render/mod_tests.rs ----
p = "crates/editor/src/render/mod_tests.rs"
fnode(p, "mod_tests.rs", "Integration-style tests for the rendering pipeline, driving edits and markdown through a TestState harness and asserting rendered output and buffer contents.", ["test","rendering","integration-test"], "complex")
cls(p, "TestState", [402,407], "Test harness bundling editor content, selection and render state with helpers to apply edits/selections and assert rendered output.", ["test","fixture"], "complex")

# ---- 8. bounds.rs ----
p = "crates/editor/src/render/model/bounds.rs"
fnode(p, "bounds.rs", "Geometry helpers that compute a block's content, visible, and reserved boxes/origins from a y-offset and block spacing.", ["utility","geometry","layout"], "moderate")
fn(p, "visible_box", [54,63], "Computes the visible bounding box of a block given its y-offset, content size and spacing.", ["geometry","layout"], "simple")
fn(p, "reserved_box", [78,87], "Computes the reserved bounding box (including margins) of a block from its y-offset, content size and spacing.", ["geometry","layout"], "simple")
export(p, "function", "visible_box")
export(p, "function", "reserved_box")

# ---- 9. debug.rs ----
p = "crates/editor/src/render/model/debug.rs"
fnode(p, "debug.rs", "Debug-description utilities: a Describe trait and Description type used to produce human-readable dumps of the render model tree.", ["utility","debug","diagnostics"], "moderate")
cls(p, "Describe", [8,16], "Trait for types that can write a structured human-readable description of themselves for debugging the render tree.", ["debug","trait","diagnostics"], "moderate")
fn(p, "describe_to", [27,69], "Writes a structured debug description of a render-model value into the formatter.", ["debug","diagnostics","serialization"], "moderate")
export(p, "class", "Describe")

# ---- 10. location.rs ----
p = "crates/editor/src/render/model/location.rs"
fnode(p, "location.rs", "Hit-testing for the render model: defines the Location enum (block vs text position) and converts render/viewport x,y coordinates into a concrete document location.", ["data-model","hit-testing","geometry","rendering"], "complex")
cls(p, "Location", [19,43], "Enum describing a hit-tested position as either a Block location or a Text offset within the rendered document.", ["data-model","hit-testing"], "moderate")
fn(p, "coordinates_to_location", [144,229], "Core hit-test: resolves an (x, y) render coordinate to a Location by walking blocks and paragraphs, honoring hit-test options.", ["hit-testing","geometry","algorithm"], "complex")
fn(p, "render_coordinates_to_location", [99,124], "Public hit-test entry converting render-space coordinates into a Location.", ["hit-testing","geometry"], "moderate")
fn(p, "location_in_paragraph_block", [231,255], "Resolves the text location within a paragraph block for a given coordinate.", ["hit-testing","geometry"], "moderate")
export(p, "class", "Location")
export(p, "function", "render_coordinates_to_location")

# ---- 11. location_tests.rs ----
p = "crates/editor/src/render/model/location_tests.rs"
fnode(p, "location_tests.rs", "Tests for coordinate-to-location hit-testing across tables, lists, code blocks, soft-wrapped lines, scrolling, and mermaid blocks.", ["test","hit-testing","rendering"], "complex")

# ---- 12. model/mod.rs (the big one) ----
p = "crates/editor/src/render/model/mod.rs"
fnode(p, "mod.rs", "Core render model of the editor: the central RenderState plus the laid-out block/paragraph/table types, rich-text styles, selections, decorations, viewport char ranges, autoscroll and layout-action handling.", ["data-model","rendering","state-management","core"], "complex",
      notes="Very large module (~4800 lines) aggregating the entire render-side data model; RenderState is the central stateful struct with ~90 methods.")
cls(p, "RenderState", [385,435], "Central render-side state for an editor view: owns content, selections, decorations, viewport, styles and pending edits, and drives layout, scrolling, autoscroll and hit-testing.", ["data-model","state-management","core","rendering"], "complex")
cls(p, "RichTextStyles", [451,492], "Aggregate style configuration for rendered rich text: fonts, colors, code/table/checkbox/horizontal-rule styling and block spacings.", ["data-model","styling","configuration"], "complex")
cls(p, "BlockItem", [748,802], "Enum of all renderable block kinds (paragraph, header, code block, table, task/unordered/ordered list, image, mermaid, horizontal rule, embedded, hidden, trailing newline).", ["data-model","rendering"], "complex")
cls(p, "Paragraph", [960,973], "A laid-out paragraph: its text frame, offset map, sizing, detected URL and spacing, with helpers for character bounds and soft-wrap conversion.", ["data-model","text-layout"], "complex")
cls(p, "ParagraphBlock", [880,882], "A block composed of one or more laid-out paragraphs, exposing combined sizing and line access.", ["data-model","text-layout"], "moderate")
cls(p, "LaidOutTable", [1200,1220], "A fully laid-out markdown table with per-cell layouts, row/column geometry, horizontal scrolling state and hit-testing/offset mapping.", ["data-model","table","scrolling","hit-testing"], "complex")
cls(p, "CellLayout", [1063,1069], "Per-cell layout within a table: line heights, y-offsets, char ranges, widths and caret positions, with line/char hit-testing helpers.", ["data-model","table","text-layout"], "complex")
cls(p, "SoftWrapPoint", [690,713], "A (row, column) position within a soft-wrapped paragraph, with navigation between wrapped rows.", ["data-model","text-layout"], "simple")
cls(p, "RenderedSelection", [4527,4532], "A rendered selection range (head/tail plus cursor bias) used to draw cursors and highlights.", ["data-model","selection"], "moderate")
cls(p, "RenderedSelectionSet", [4611,4613], "Ordered collection of rendered selections supporting iteration, sorting and mapping.", ["data-model","selection","collection"], "moderate")
cls(p, "HiddenBlockConfig", [1598,1604], "Configuration for a collapsed/hidden block region, tracking line count, content length and expansion gutter buttons.", ["data-model","folding"], "moderate")
cls(p, "Decoration", [4731,4739], "A text decoration range (background fill and/or dashed underline) applied during rendering.", ["data-model","decoration"], "simple")
cls(p, "LayoutAction", [3315,3335], "Enum of layout-mutating actions (selection/decoration change, buffer edit, temporary block, autoscroll, scroll-to) processed by RenderState.", ["data-model","state-management","command"], "moderate")
cls(p, "AutoScrollMode", [3282,3297], "Enum of autoscroll strategies (into-viewport, exact-vertical, to-selections, center-offset).", ["data-model","scrolling"], "simple")
fn(p, "handle_layout_action", [2329,2435], "Dispatches a LayoutAction against RenderState, applying selection/decoration/edit/scroll changes and scheduling relayout.", ["state-management","command","rendering"], "complex")
fn(p, "layout_pending_edit", [2599,2740], "Re-lays out the portion of the document affected by a pending edit, splicing new block items into the existing layout.", ["rendering","text-layout","algorithm"], "complex")
fn(p, "autoscroll", [2817,2889], "Adjusts the viewport scroll offsets to satisfy a requested AutoScrollMode (reveal offsets, center, follow selections).", ["scrolling","rendering","algorithm"], "complex")
fn(p, "blocks_in_line_range", [1969,2036], "Returns the laid-out block items intersecting a given line range, used for incremental rendering.", ["rendering","query"], "moderate")
fn(p, "dedupe_hidden_ranges", [2743,2809], "Merges adjacent/overlapping hidden line ranges so collapsed regions render as single blocks.", ["folding","algorithm"], "complex")
fn(p, "multiselect_autoscroll_bounding_box", [2947,3034], "Computes the bounding box covering all selection heads to drive autoscroll for multiple cursors.", ["scrolling","selection","geometry"], "complex")
fn(p, "set_viewport_size", [2143,2165], "Updates the viewport size on RenderState and triggers any layout needed for the new dimensions.", ["state-management","rendering"], "moderate")
fn(p, "draw_selection", [4034,4073], "Draws the active selection (cursors and highlight ranges) for a render model into the context.", ["rendering","selection","paint"], "moderate")
fn(p, "draw_cursor", [4075,4121], "Draws a single cursor at a character offset with the configured cursor styling and bias.", ["rendering","paint","cursor"], "moderate")
fn(p, "draw_charwise_highlight", [4217,4269], "Draws a character-wise selection highlight spanning a start/end offset across possibly soft-wrapped lines.", ["rendering","paint","selection"], "complex")
for c in ["RenderState","RichTextStyles","BlockItem","Paragraph","ParagraphBlock","LaidOutTable","CellLayout","SoftWrapPoint","RenderedSelection","RenderedSelectionSet","HiddenBlockConfig","Decoration","LayoutAction","AutoScrollMode"]:
    export(p, "class", c)

# ---- 13. model/mod_tests.rs ----
p = "crates/editor/src/render/model/mod_tests.rs"
fnode(p, "mod_tests.rs", "Unit tests for the render model: sizing, soft-wrap points, character bounds, ordered-list counting, autoscroll bounding boxes, hidden-range deduping, and table cell/offset hit-testing.", ["test","rendering","data-model"], "complex")

# ---- 14. offset_map.rs ----
p = "crates/editor/src/render/model/offset_map.rs"
fnode(p, "offset_map.rs", "OffsetMap mapping between content (document) offsets and frame (rendered) offsets via selectable text runs, accounting for placeholders.", ["data-model","offset-mapping","text-layout"], "moderate")
cls(p, "OffsetMap", [28,31], "Maps content offsets to frame offsets (and back) through a list of selectable text runs.", ["data-model","offset-mapping"], "moderate")
fn(p, "translate", [87,130], "Translates an offset across the run list, handling placeholder/non-selectable runs between content and frame coordinates.", ["offset-mapping","algorithm"], "moderate")
export(p, "class", "OffsetMap")

# ---- 15. offset_map_tests.rs ----
p = "crates/editor/src/render/model/offset_map_tests.rs"
fnode(p, "offset_map_tests.rs", "Tests for OffsetMap content/frame translation including placeholder runs and an end-to-end mapping scenario.", ["test","offset-mapping"], "complex")

# ---- 16. positioned.rs ----
p = "crates/editor/src/render/model/positioned.rs"
fnode(p, "positioned.rs", "Positioned<T> wrapper that assigns a start char offset, line and y-offset (plus style) to each block item, with constructors for every block kind and bounds helpers.", ["data-model","layout","positioning"], "complex")
cls(p, "Positioned", [20,36], "Generic wrapper attaching start char-offset, line, y-offset and style to a laid-out block item, exposing content/visible/reserved origins.", ["data-model","positioning","geometry"], "complex")
export(p, "class", "Positioned")

# ---- 17. saved_positions.rs ----
p = "crates/editor/src/render/model/saved_positions.rs"
fnode(p, "saved_positions.rs", "Generates stable per-model identifiers for the cursor, text selection and hovered block-start positions.", ["data-model","identifiers","utility"], "simple")
cls(p, "SavedPositions", [6,10], "Holds a model id and derives stable IDs for cursor, text-selection and hovered-block positions.", ["data-model","identifiers"], "simple")
export(p, "class", "SavedPositions")

# ---- 18. table_offset_map.rs ----
p = "crates/editor/src/render/model/table_offset_map.rs"
fnode(p, "table_offset_map.rs", "Offset mapping for markdown tables: maps linear offsets to cell/row/column positions and converts between source markdown offsets and rendered cell offsets.", ["data-model","table","offset-mapping"], "complex")
cls(p, "TableOffsetMap", [18,25], "Maps a linear character offset within a table to its cell/row/column and back, tracking cell ranges and separator positions.", ["data-model","table","offset-mapping"], "complex")
cls(p, "TableCellOffsetMap", [73,77], "Maps between a table cell's rendered offsets and its source markdown offsets via fragment ranges.", ["data-model","table","offset-mapping"], "moderate")
fn(p, "new", [92,140], "Builds a TableOffsetMap from per-cell lengths, computing cumulative cell and row ranges and the row/col index.", ["factory","table","offset-mapping"], "moderate")
fn(p, "position_at_offset", [148,186], "Resolves a linear table offset to a TablePosition (in-cell, on-tab separator, or on-newline).", ["table","offset-mapping","algorithm"], "moderate")
fn(p, "from_inline_and_source", [296,373], "Builds a TableCellOffsetMap by aligning a cell's rendered inline content with its source markdown fragments.", ["table","offset-mapping","markdown"], "complex")
export(p, "class", "TableOffsetMap")
export(p, "class", "TableCellOffsetMap")

# ---- 19. test_utils.rs ----
p = "crates/editor/src/render/model/test_utils.rs"
fnode(p, "test_utils.rs", "Test helpers for the render model: build mock and real laid-out paragraphs, unordered lists and tables from text and styles, plus logging init.", ["test","fixture","utility"], "complex")
fn(p, "layout", [225,309], "Lays out text into render-model paragraphs/blocks for use in tests, mirroring the production layout path.", ["test","fixture","text-layout"], "complex")

# ---- 20. viewport.rs ----
p = "crates/editor/src/render/model/viewport.rs"
fnode(p, "viewport.rs", "Viewport state and iteration: tracks scroll position and size, clamps and autoscrolls scroll offsets, computes viewport sizing, and iterates the block items currently visible.", ["data-model","viewport","scrolling","rendering"], "complex")
cls(p, "ViewportState", [25,40], "Holds viewport width/height and scroll top/left, with scrolling, clamping, autoscroll and sizing operations.", ["data-model","viewport","scrolling"], "complex")
cls(p, "ViewportItem", [49,61], "A block item positioned within the viewport, exposing content/visible/reserved bounds and its block offset.", ["data-model","viewport","geometry"], "moderate")
cls(p, "ScrollPositionSnapshot", [66,72], "Captures a scroll position as a stable first-visible character offset so it survives relayout.", ["data-model","scrolling"], "moderate")
cls(p, "ViewportIterator", [105,114], "Iterator yielding the block viewport items intersecting the current scroll window.", ["data-model","viewport","iterator"], "moderate")
fn(p, "autoscroll", [218,262], "Adjusts scroll top/left so a target item range becomes visible, optionally scrolling horizontally.", ["scrolling","viewport","algorithm"], "moderate")
fn(p, "viewport_size", [290,319], "Computes the viewport size from layout constraints, size buffer and max width.", ["viewport","geometry"], "moderate")
export(p, "class", "ViewportState")
export(p, "class", "ViewportItem")
export(p, "class", "ScrollPositionSnapshot")

# ---- 21. viewport_tests.rs ----
p = "crates/editor/src/render/model/viewport_tests.rs"
fnode(p, "viewport_tests.rs", "Tests for viewport offset math, item-to-block mapping, scroll bounds, and width/height change handling.", ["test","viewport","scrolling"], "moderate")

# ---- 22. search.rs ----
p = "crates/editor/src/search.rs"
fnode(p, "search.rs", "In-editor search: the Searcher drives literal/regex/case-sensitive find over the buffer, navigates between matches, restores selection across edits, and produces result decorations.", ["service","search","state-management"], "complex")
cls(p, "Searcher", [21,31], "Owns search query/options and results over a buffer+selection model, with async search, match navigation, and decoration output.", ["service","search","state-management"], "complex")
fn(p, "run_search", [302,348], "Builds the query and runs an async search over the buffer, updating the stored results.", ["search","async","algorithm"], "moderate")
fn(p, "restore_selected_result", [350,371], "Re-selects the closest valid match after the buffer changes so search selection survives edits.", ["search","selection"], "moderate")
fn(p, "select_previous_result", [214,230], "Moves the selected match to the previous result, wrapping around the result list.", ["search","navigation"], "moderate")
fn(p, "result_decorations", [374,396], "Builds the highlight decorations for all search matches plus the active match.", ["search","decoration","rendering"], "moderate")
export(p, "class", "Searcher")

# ---- 23. search_tests.rs ----
p = "crates/editor/src/search_tests.rs"
fnode(p, "search_tests.rs", "Tests for literal search, match navigation, and search-result validity across edits.", ["test","search"], "complex")

# ---- 24. selection.rs ----
p = "crates/editor/src/selection.rs"
fnode(p, "selection.rs", "Selection engine: the SelectionModel manages cursors and selections, normalizes and validates select actions, and navigates by character/word/line/paragraph including multiselect and skipping rendered mermaid blocks.", ["service","selection","navigation","state-management"], "complex")
cls(p, "SelectionModel", [26,47], "Owns cursors/selections over render+content+selection models, normalizing actions and navigating by character/word/line/paragraph with hidden-line and mermaid awareness.", ["service","selection","navigation","state-management"], "complex")
cls(p, "TextUnit", [51,62], "Enum of navigation granularities (character, word, line boundary, line, paragraph boundary).", ["data-model","navigation"], "simple")
cls(p, "SelectionMode", [66,73], "Enum of selection modes (character, word, line) for drag/extend selection.", ["data-model","selection"], "simple")
fn(p, "begin_selection", [532,587], "Begins a selection at an offset in the given mode, optionally clearing existing selections (drag start).", ["selection","navigation","event-handler"], "moderate")
fn(p, "normalized_character_action", [326,396], "Normalizes a character select action by adjusting offsets around rendered mermaid blocks and clamping to valid bounds.", ["selection","navigation","normalization"], "complex")
fn(p, "update_selections_internal", [672,726], "Applies a selection update, recomputing goal columns and pushing the new selection set into the render model.", ["selection","state-management"], "complex")
fn(p, "navigate_line", [868,920], "Moves a cursor vertically by line, preserving the goal x-column across soft-wrapped and varied-height lines.", ["navigation","selection","algorithm"], "complex")
fn(p, "navigate_word", [835,866], "Moves a cursor by word according to the word policy and direction.", ["navigation","selection"], "moderate")
fn(p, "navigate_line_boundary", [922,981], "Moves a cursor to the start/end line boundary, accounting for indentation and soft wrapping.", ["navigation","selection","algorithm"], "complex")
fn(p, "validate_select_action", [414,455], "Validates and clamps a select action against the current document bounds before applying it.", ["selection","validation"], "moderate")
export(p, "class", "SelectionModel")
export(p, "class", "TextUnit")
export(p, "class", "SelectionMode")

# ---- 25. selection_tests.rs ----
p = "crates/editor/src/selection_tests.rs"
fnode(p, "selection_tests.rs", "Tests for selection movement and navigation: goal-column behavior, word/line/paragraph boundaries, multiselect vertical movement, mermaid-block skipping, and semantic drag selection.", ["test","selection","navigation"], "complex")

# ---- import edges (1:1 from batchImportData) ----
import_edge_count = 0
for src, targets in imp.items():
    for t in targets:
        edges.append({"source": f"file:{src}", "target": f"file:{t}", "type": "imports", "direction": "forward", "weight": 0.7})
        import_edge_count += 1

# ---- tested_by edges ----
tested_by("crates/editor/src/render/model/mod.rs", "crates/editor/src/render/model/mod_tests.rs")
tested_by("crates/editor/src/render/model/mod.rs", "crates/editor/src/render/mod_tests.rs")
tested_by("crates/editor/src/render/model/location.rs", "crates/editor/src/render/model/location_tests.rs")
tested_by("crates/editor/src/render/model/offset_map.rs", "crates/editor/src/render/model/offset_map_tests.rs")
tested_by("crates/editor/src/render/model/viewport.rs", "crates/editor/src/render/model/viewport_tests.rs")
tested_by("crates/editor/src/search.rs", "crates/editor/src/search_tests.rs")
tested_by("crates/editor/src/selection.rs", "crates/editor/src/selection_tests.rs")

# ---- self-check imports ----
expected_imports = sum(len(v) for v in imp.values())
assert import_edge_count == expected_imports, (import_edge_count, expected_imports)

# ---------- Partition per protocol ----------
nodeCount = len(nodes)
edgeCount = len(edges)
print("nodeCount", nodeCount, "edgeCount", edgeCount, "imports", import_edge_count, "expected", expected_imports)

if nodeCount <= 60 and edgeCount <= 120:
    parts = 1
else:
    parts = math.ceil(max(nodeCount/60, edgeCount/120))

sorted_files = sorted(files_in_batch)

def build_groups(parts):
    chunk = math.ceil(len(sorted_files)/parts)
    return [sorted_files[i:i+chunk] for i in range(0, len(sorted_files), chunk)]

def part_counts(groups):
    res = []
    for grp in groups:
        grpset = set(grp)
        pn = [n for n in nodes if n['filePath'] in grpset]
        pn_ids = set(n['id'] for n in pn)
        pe = [e for e in edges if e['source'] in pn_ids]
        res.append((len(pn), len(pe)))
    return res

# bump parts until each part fits within 60 nodes / 120 edges
if parts > 1:
    while True:
        groups = build_groups(parts)
        counts = part_counts(groups)
        if all(nc <= 60 and ec <= 120 for nc, ec in counts):
            break
        parts += 1
        if parts > len(sorted_files):
            groups = build_groups(parts)
            break
else:
    groups = build_groups(parts)
print("parts", parts)
print("groups sizes", [len(g) for g in groups])

def node_file(n):
    if 'filePath' in n:
        return n['filePath']
    # derive from id like type:path:name
    rest = n['id'].split(':',1)[1]
    return rest.rsplit(':',1)[0] if rest.count(':')>=1 and not rest.startswith('crates') else rest
# simpler: every node we emitted has filePath
for n in nodes:
    assert 'filePath' in n, n['id']

written = []
for k, grp in enumerate(groups, start=1):
    grpset = set(grp)
    part_nodes = [n for n in nodes if n['filePath'] in grpset]
    part_node_ids = set(n['id'] for n in part_nodes)
    part_edges = [e for e in edges if e['source'] in part_node_ids]
    frag = {"nodes": part_nodes, "edges": part_edges}
    if parts == 1:
        fname = os.path.join(OUT_DIR, "batch-8.json")
    else:
        fname = os.path.join(OUT_DIR, f"batch-8-part-{k}.json")
    with open(fname, 'w') as fh:
        json.dump(frag, fh, indent=2)
    written.append((fname, len(part_nodes), len(part_edges)))
    print("WROTE", fname, "nodes", len(part_nodes), "edges", len(part_edges))

# validation: every edge source/target resolvable
all_ids = set(n['id'] for n in nodes)
# allowed cross refs: file:<path in imp targets or files>, function/class neighbor symbols
neighbor_targets = set()
neighbor_targets.add(RB)
imp_targets = set()
for v in imp.values():
    for t in v:
        imp_targets.add(f"file:{t}")
bad = []
for e in edges:
    s, t = e['source'], e['target']
    if s not in all_ids:
        bad.append(('SRC', e))
    if t in all_ids: continue
    if t.startswith('file:'): continue  # cross-batch file refs allowed (imports/tested_by within batch already in all_ids)
    if t == RB: continue
    bad.append(('TGT', e))
print("BAD edges:", len(bad))
for b in bad[:20]:
    print(b)
