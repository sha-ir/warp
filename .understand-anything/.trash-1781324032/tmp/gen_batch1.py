import json, math, os

ROOT = '/home/mhb/warp'
extract = json.load(open(f'{ROOT}/.understand-anything/tmp/ua-file-extract-results-1.json'))
batches = json.load(open(f'{ROOT}/.understand-anything/intermediate/batches.json'))
batch = next(b for b in batches['batches'] if b['batchIndex'] == 1)
import_data = batch['batchImportData']

# Build lookups from extract results
res_by_path = {r['path']: r for r in extract['results']}
def cls_range(path, name):
    for c in res_by_path[path]['classes']:
        if c['name'] == name:
            return [c['startLine'], c['endLine']]
    raise KeyError(f'class {name} in {path}')
def fn_range(path, name):
    for f in res_by_path[path]['functions']:
        if f['name'] == name:
            return [f['startLine'], f['endLine']]
    raise KeyError(f'fn {name} in {path}')
def exports_set(path):
    return {e['name'] for e in res_by_path[path]['exports']}

P = 'crates/warpui_core/src/'

# File-node metadata: path -> (summary, tags, complexity, languageNotes)
files_meta = {
 P+'elements/align.rs': ("Element wrapper that aligns its single child within the allocated space according to an Alignment (corners, edges, centers), forwarding layout/paint/selection to the child.", ["ui-element","layout","alignment","selection-forwarding"], "moderate", None),
 P+'elements/clipped.rs': ("Element that clips its child's painting to a bounded region (optionally a fixed size), used to constrain overflow during rendering.", ["ui-element","clipping","painting","layout"], "moderate", None),
 P+'elements/constrained_box.rs': ("Element that imposes min/max width and height constraints on its child before laying it out, with fluent builder methods for each bound.", ["ui-element","layout","constraints","builder"], "moderate", None),
 P+'elements/container.rs': ("Box-model element providing margin, padding, background fill/gradient, border, corner radius, drop shadow and overlay around a child; the primary styling primitive of warpui.", ["ui-element","box-model","styling","builder"], "complex", "Heavy use of fluent `with_*` builder methods returning Self for chained construction."),
 P+'elements/dismiss.rs': ("Element that detects clicks/events outside its child and invokes a dismiss handler, optionally blocking interaction with other elements (used for popovers/menus).", ["ui-element","event-handling","dismiss","overlay"], "moderate", None),
 P+'elements/empty.rs': ("Zero-content placeholder element that occupies layout space but paints nothing and ignores events.", ["ui-element","placeholder","layout"], "simple", None),
 P+'elements/flex/mod.rs': ("Flexbox layout engine (row/column) distributing space among children via flex factors, main/cross axis alignment and spacing; defines the Flex element plus Expanded/Shrinkable wrappers and alignment enums.", ["ui-element","layout","flexbox","selection-forwarding"], "complex", "Implements a Flutter-style flex algorithm with FlexFit (Tight/Loose) and a two-pass layout in the large `layout` method."),
 P+'elements/flex/wrap.rs': ("Wrapping flex layout that flows children into multiple runs along the main axis, breaking to a new line when space is exhausted; includes run-fill helpers.", ["ui-element","layout","flex-wrap","multi-line"], "complex", None),
 P+'elements/formatted_text_element.rs': ("Rich-text rendering element for formatted/markdown content: headings, code blocks, lists, hyperlinks, inline code, hover/click handlers, text selection and secret redaction.", ["ui-element","text-rendering","rich-text","selection"], "complex", "Largest element in the batch (~2600 lines); the 440-line `layout` method lays out heterogeneous line types into text frames."),
 P+'elements/hoverable.rs': ("Interaction wrapper element adding hover and click handling (single/double/middle/right/back/forward), hover-in/out delays, cursor changes and drag propagation around a child.", ["ui-element","event-handling","hover","mouse-interaction"], "complex", None),
 P+'elements/live.rs': ("Element wrapper that requests periodic repaints of its child at a fixed interval, enabling animations and live-updating content.", ["ui-element","animation","repaint","wrapper"], "moderate", None),
 P+'elements/min_size.rs': ("Element that enforces a minimum size on its child, expanding the child's measured size up to at least the constraint floor.", ["ui-element","layout","constraints","selection-forwarding"], "moderate", None),
 P+'elements/new_scrollable/dual_axis_config.rs': ("Scroll configuration for elements that scroll on both axes simultaneously: manages per-axis scroll offsets, drag/hover state, clipping and scroll-to-position painting.", ["scrolling","layout","dual-axis","state-management"], "complex", None),
 P+'elements/new_scrollable/mod.rs': ("Core scrollable container: wraps a child, draws and hit-tests scrollbars, handles mouse drag/wheel scrolling, selection anchoring during scroll, and exposes horizontal/vertical/both constructors.", ["scrolling","ui-element","scrollbar","event-handling"], "complex", "Defines the NewScrollableElement trait plus ScrollableState (single/both axis) and scrollbar-rendering state."),
 P+'elements/new_scrollable/scrollable_tests.rs': ("Unit and integration tests for the scrollable element covering clipped scrolling, selection re-anchoring, click-to-scroll and scroll-to-position across single and dual axes.", ["test","scrolling","integration-test","selection"], "complex", None),
 P+'elements/new_scrollable/single_axis_config.rs': ("Scroll configuration for elements that scroll on a single axis: layout, painting, drag/hover state, scroll-data computation and delta clamping for one direction.", ["scrolling","layout","single-axis","state-management"], "complex", None),
 P+'elements/new_scrollable/util.rs': ("Free-function helpers for scrollable layout: deriving child constraints per axis, scrolling clipped handles by a delta, applying sensitivity, and computing scroll deltas to bring a region into view.", ["scrolling","utility","layout","geometry"], "moderate", None),
 P+'elements/selectable_area.rs': ("Element that turns its child into a mouse-driven text-selection region: tracks selection head/tail, smart/word/rect selection, drag updates and right-click handling, emitting selection fragments.", ["ui-element","selection","event-handling","text-selection"], "complex", None),
 P+'elements/shared_scrollbar.rs': ("Pure geometry helpers shared across scrollables: computes scrollbar track/thumb bounds, thumb position percentages, and translates pointer movement and wheel deltas into scroll offsets.", ["scrolling","scrollbar","geometry","utility"], "moderate", None),
 P+'elements/size_constraint_switch.rs': ("Responsive element that picks one of several child variants based on whether the available size satisfies a size constraint condition (width/height/area thresholds).", ["ui-element","responsive","layout","conditional"], "moderate", None),
 P+'elements/stack/mod.rs': ("Z-ordered stack element that overlays absolutely-positioned and overlay children on top of a base child, with broadcast or waterfall event dispatch and per-child positioning.", ["ui-element","layout","z-stacking","overlay"], "complex", None),
 P+'elements/stack/overlay.rs': ("Lightweight wrapper marking a child as an overlay layer within a Stack, painted above the base content.", ["ui-element","overlay","stacking","wrapper"], "simple", None),
 P+'elements/stack/positioned.rs': ("Stack child wrapper that applies an absolute offset/positioning to its child via parent-data, used for placing overlays at explicit coordinates.", ["ui-element","positioning","stacking","layout"], "moderate", None),
 P+'elements/stack/save_position.rs': ("Stack helper element that records its child's painted screen position under a position id, enabling later lookup of rich-content anchor points.", ["ui-element","positioning","state-tracking","stacking"], "moderate", None),
 P+'elements/table/mod.rs': ("Virtualized table element: lazily renders rows, measures intrinsic column widths, supports fixed/flex/fraction/intrinsic column sizing, headers, striped backgrounds, dividers and vertical scrolling.", ["ui-element","table","virtualization","layout"], "complex", "Row heights are measured incrementally and cached in TableState to support virtualized scrolling over large row counts."),
 P+'elements/text.rs': ("Core text element rendering a single styled string with highlights, soft-wrapping, autosizing, clickable/hoverable char ranges and full mouse-driven text selection.", ["ui-element","text-rendering","selection","styling"], "complex", None),
 P+'elements/uniform_list.rs': ("Virtualized list element for uniform-height items: renders only visible items, supports scroll-to-item, autoscroll and visible-item notifications.", ["ui-element","list","virtualization","scrolling"], "complex", None),
 P+'elements/viewported_list.rs': ("Virtualized variable-height list element with incremental height measurement, scroll preservation across content changes, and scroll-to-index with offsets.", ["ui-element","list","virtualization","scroll-preservation"], "complex", None),
 P+'event.rs': ("Input event model for warpui: defines the Event enum (key, mouse, scroll, drag, IME) plus modifier/key state and a DispatchedEvent carrier with z-index-aware coordinate handling and DPI scaling.", ["event-model","input","mouse","keyboard"], "complex", None),
 P+'text/header.rs': ("Markdown block heading sizes (H1-H6) with font-size multipliers, weights and labels, plus conversions to/from heading levels.", ["text","markdown","headings","enum"], "moderate", None),
 P+'text/mod.rs': ("Text-selection and buffer abstractions: selection type/direction classification, a TextBuffer trait over char/point/offset navigation, and char-indexing utilities for UTF-8 strings.", ["text","selection","buffer","utility"], "complex", None),
 P+'text/point.rs': ("Row/column Point type for text coordinates with arithmetic, ordering and zero/initialization helpers.", ["text","geometry","coordinates","value-type"], "moderate", None),
 P+'text/word_boundaries.rs': ("Word-boundary detection over a TextBuffer: an iterator that walks forward/backward to word starts and ends under configurable boundary policies (default, whitespace-only, custom).", ["text","word-boundaries","iterator","selection"], "complex", None),
 P+'text/words.rs': ("Small word-splitting helpers: find the next word start in a string and classify word/subword boundary characters.", ["text","word-boundaries","utility"], "simple", None),
 P+'units.rs': ("Typed length units for the layout system: Lines and Pixels newtypes with conversions (via line height), arithmetic, comparison and IntoPixels/IntoLines traits.", ["units","geometry","value-type","layout"], "complex", "Newtype wrappers around f32/f64 with operator overloads and approx-eq, preventing accidental mixing of line- and pixel-space measurements."),
}

# classes[path] = { name: (summary, tags, complexity) }
classes = {}
functions = {}
def C(path): classes.setdefault(path, {})
def F(path): functions.setdefault(path, {})

# ---- align
p=P+'elements/align.rs'; C(p)
classes[p]['Align']=("Element that positions its child within the parent box per an Alignment, delegating selection/word-expansion to the child.",["ui-element","alignment","builder"],"moderate")

p=P+'elements/clipped.rs'; C(p)
classes[p]['Clipped']=("Element that clips child painting to a region or fixed size during the paint pass.",["ui-element","clipping","painting"],"moderate")

p=P+'elements/constrained_box.rs'; C(p)
classes[p]['ConstrainedBox']=("Element applying min/max width/height constraints to its child via chained builder methods.",["ui-element","constraints","builder"],"moderate")

p=P+'elements/container.rs'; C(p)
classes[p]['Container']=("Box-model styling element (margin, padding, background, border, radius, shadow, overlay) wrapping a single child.",["ui-element","box-model","styling","builder"],"complex")

p=P+'elements/dismiss.rs'; C(p)
classes[p]['Dismiss']=("Element invoking a handler when an event lands outside its child, for dismissing popovers/menus.",["ui-element","dismiss","event-handling"],"moderate")

p=P+'elements/empty.rs'; C(p)
classes[p]['Empty']=("Empty placeholder element occupying space but painting nothing.",["ui-element","placeholder"],"simple")

p=P+'elements/flex/mod.rs'; C(p); F(p)
classes[p]['Flex']=("Row/column flex container distributing space by flex factors with main/cross alignment and spacing.",["ui-element","flexbox","layout"],"complex")
classes[p]['Expanded']=("Flex child wrapper that fills available main-axis space with a Tight fit.",["ui-element","flexbox","wrapper"],"simple")
classes[p]['Shrinkable']=("Flex child wrapper that takes a flex factor with a Loose fit, shrinking as needed.",["ui-element","flexbox","wrapper"],"simple")
classes[p]['LayoutState']=("Internal flex layout result holding computed leading/between spacing for main-axis distribution.",["layout","flexbox","state"],"simple")
classes[p]['MainAxisAlignment']=("Enum of main-axis alignments: Start, End, Center, SpaceBetween, SpaceEvenly.",["enum","flexbox","alignment"],"simple")
classes[p]['CrossAxisAlignment']=("Enum of cross-axis alignments: Start, End, Center, Stretch.",["enum","flexbox","alignment"],"simple")
classes[p]['MainAxisSize']=("Enum controlling whether a flex container hugs (Min) or fills (Max) the main axis.",["enum","flexbox","sizing"],"simple")
classes[p]['FlexFit']=("Enum for how a flexible child is fit: Tight (must fill) or Loose (may shrink).",["enum","flexbox","sizing"],"simple")

p=P+'elements/flex/wrap.rs'; C(p)
classes[p]['Wrap']=("Wrapping flex container flowing children into runs that break onto new lines along the cross axis.",["ui-element","flex-wrap","layout"],"complex")
classes[p]['WrapChild']=("Per-child layout record in a Wrap tracking its element and laid-out/painted state.",["ui-element","flex-wrap","state"],"simple")
classes[p]['WrapFill']=("Wrap child that fills remaining or entire run space, with a minimum-space requirement.",["ui-element","flex-wrap","wrapper"],"simple")

p=P+'elements/formatted_text_element.rs'; C(p); F(p)
classes[p]['FormattedTextElement']=("Rich formatted-text element rendering headings, lists, code blocks, hyperlinks and inline code with hover/click and selection support.",["ui-element","rich-text","text-rendering","selection"],"complex")
classes[p]['HeadingFontSizeMultipliers']=("Per-heading-level (h1-h6) font-size multiplier configuration for rich text.",["rich-text","headings","config"],"simple")
classes[p]['FrameMouseHandlers']=("Per-text-frame registry of click/hover handlers, styles and secret-replacement ranges with glyph/byte offsets.",["rich-text","event-handling","state"],"moderate")
classes[p]['LaidOutTextFrame']=("Enum of laid-out frame kinds (Text, CodeBlock, Indented, LineBreak) with geometry and hit-testing helpers.",["enum","rich-text","layout"],"moderate")
classes[p]['LineType']=("Enum classifying a formatted line as ordered/unordered list, formatted line, code block or line break.",["enum","rich-text","markdown"],"simple")
classes[p]['SnappingPolicy']=("Policy controlling selection snapping behaviour (snap on gaps, snap to ends, char-index adjustment).",["selection","policy","config"],"simple")
classes[p]['HyperlinkLens']=("Enum distinguishing a hyperlink target as a URL or an in-app Action.",["enum","rich-text","hyperlink"],"simple")
functions[p]['layout']=("Lays out heterogeneous formatted line types (headings, lists, code blocks) into positioned text frames within the constraint.",["layout","rich-text","text-layout"],"complex")
functions[p]['position_for_point']=("Maps an absolute screen point to a text position/selection bound under a snapping policy for hit-testing selections.",["selection","hit-testing","text"],"complex")
functions[p]['handle_mouse_moved']=("Handles mouse movement over formatted text to update hyperlink/hover highlight state and cursor.",["event-handling","hover","rich-text"],"complex")

p=P+'elements/hoverable.rs'; C(p); F(p)
classes[p]['Hoverable']=("Interaction wrapper adding hover/click/mouse handlers, hover delays and cursor control around a child.",["ui-element","hover","event-handling","builder"],"complex")
classes[p]['MouseState']=("Shared mouse-interaction state for a hoverable: click count, hover flags and hover-in/out timers.",["state","hover","mouse-interaction"],"moderate")
classes[p]['HoverTimerType']=("Enum tagging a hover timer as HoverIn or HoverOut, with an opposite() helper.",["enum","hover","timer"],"simple")
functions[p]['handle_mouse_moved']=("Processes mouse-moved events to (de)bounce hover-in/out transitions and run hover callbacks.",["event-handling","hover","mouse-interaction"],"complex")

p=P+'elements/live.rs'; C(p)
classes[p]['LiveElement']=("Wrapper that schedules periodic repaints of its child at a fixed interval for animation.",["ui-element","animation","repaint"],"moderate")

p=P+'elements/min_size.rs'; C(p)
classes[p]['MinSize']=("Element enforcing a minimum size on its child during layout.",["ui-element","constraints","layout"],"moderate")

# ---- new_scrollable
p=P+'elements/new_scrollable/dual_axis_config.rs'; C(p); F(p)
classes[p]['DualAxisConfig']=("Two-axis scroll state and behaviour: per-axis offsets, drag/hover, clipping and scroll-to-position painting.",["scrolling","dual-axis","state-management"],"complex")
classes[p]['AxisConfiguration']=("Enum of a single axis's scroll mode: Manual (caller-driven) or Clipped (framework-clipped scrolling).",["enum","scrolling","config"],"moderate")
classes[p]['ScrollToPosition']=("Enum describing a scroll-to target across Dual, Horizontal or Vertical axes.",["enum","scrolling"],"simple")
classes[p]['ClippedAxisConfiguration']=("Per-axis clipped-scroll configuration holding the scroll handle, max size and child-stretch flag.",["scrolling","config","state"],"simple")
functions[p]['scroll_to_position_and_paint_clipped']=("Scrolls a clipped child to bring a target position into view, then paints it clipped to the viewport.",["scrolling","painting","clipping"],"complex")

p=P+'elements/new_scrollable/mod.rs'; C(p); F(p)
classes[p]['NewScrollable']=("Scrollable container element wrapping a child with scrollbars, drag/wheel scrolling and selection-aware scroll anchoring.",["ui-element","scrolling","scrollbar"],"complex")
classes[p]['NewScrollableElement']=("Trait implemented by scrollable child elements exposing axis, scroll-data and scroll operations.",["trait","scrolling","abstraction"],"moderate")
classes[p]['ScrollableAxis']=("Enum of scroll axes: Horizontal, Vertical or Both.",["enum","scrolling"],"simple")
classes[p]['ScrollableState']=("Enum of scrollable internal state for single-axis vs both-axes configurations driving layout and event handling.",["scrolling","state-management"],"complex")
classes[p]['ScrollbarRenderState']=("Computed scrollbar render geometry: track/thumb bounds, position and size percentages and padding.",["scrolling","scrollbar","geometry"],"moderate")
classes[p]['ScrollableAppearance']=("Scrollbar appearance config holding scrollbar size and whether it is overlaid on content.",["scrolling","scrollbar","config"],"simple")
functions[p]['draw_scrollbars']=("Draws horizontal/vertical scrollbar tracks and thumbs for the current scroll state and appearance.",["scrolling","scrollbar","painting"],"complex")
functions[p]['mousewheel']=("Handles mouse-wheel scroll deltas, applying sensitivity and propagating unhandled scroll to the parent.",["scrolling","event-handling","mouse-interaction"],"complex")

p=P+'elements/new_scrollable/scrollable_tests.rs'; C(p)
classes[p]['BasicScrollableView']=("Test view harness wiring up a scrollable with configurable axes to exercise scroll and click behaviour.",["test","scrolling","harness"],"moderate")
classes[p]['ScrollableElement']=("Test element implementing NewScrollableElement with fixed child elements for scroll assertions.",["test","scrolling","fixture"],"moderate")
classes[p]['SelectableProbeElement']=("Test probe element recording selection-API calls (get/expand/smart-select) for assertions.",["test","selection","fixture"],"moderate")

p=P+'elements/new_scrollable/single_axis_config.rs'; C(p)
classes[p]['SingleAxisConfig']=("Single-axis scroll state and behaviour: layout, painting, drag/hover, scroll-data and delta clamping for one direction.",["scrolling","single-axis","state-management"],"complex")

p=P+'elements/new_scrollable/util.rs'; F(p)
functions[p]['child_constraint_for_axis']=("Derives the child's layout constraint along a scroll axis, accounting for clipping and scrollbar size.",["scrolling","layout","utility"],"moderate")
functions[p]['scroll_clipped_scrollable_handle_with_delta']=("Advances a clipped scroll handle by a delta, clamping to the child/viewport bounds.",["scrolling","utility","geometry"],"moderate")
functions[p]['scroll_delta_for_axis']=("Computes the scroll delta needed to bring a region's bounds into the viewport for a given mode.",["scrolling","utility","geometry"],"moderate")

p=P+'elements/selectable_area.rs'; C(p); F(p)
classes[p]['SelectableArea']=("Element turning a child into a text-selection region with smart/word/rect selection and selection-handler callbacks.",["ui-element","selection","text-selection","event-handling"],"complex")
classes[p]['InternalSelection']=("Internal selection state tracking head/tail bounds, expansion, reversal and smart-selection anchors.",["selection","state-management"],"moderate")
classes[p]['SelectionHandle']=("Shared handle for an in-progress selection allowing external start/clear and type queries.",["selection","state","handle"],"moderate")
classes[p]['SelectionBound']=("Enum of selection anchor kinds (Relative point, TopLeft, BottomRight, Top, Bottom) convertible to absolute points.",["enum","selection","geometry"],"moderate")
classes[p]['Selection']=("Concrete selection value holding start/end bounds and a rect-selection flag.",["selection","value-type"],"simple")
functions[p]['update_selection']=("Updates the active selection's tail to a new absolute position, applying smart/word/rect expansion rules.",["selection","event-handling"],"complex")

p=P+'elements/shared_scrollbar.rs'; C(p); F(p)
classes[p]['ScrollbarAppearance']=("Scrollbar styling config: width, overlay flag and padding between child and scrollbar.",["scrolling","scrollbar","config"],"simple")
classes[p]['ScrollbarGeometry']=("Computed scrollbar track/thumb geometry with helpers for thumb presence and center position.",["scrolling","scrollbar","geometry"],"moderate")
functions[p]['compute_scrollbar_geometry']=("Computes scrollbar track and thumb bounds and position/size percentages from scroll data along an axis.",["scrolling","scrollbar","geometry"],"moderate")
functions[p]['scroll_delta_for_pointer_movement']=("Translates scrollbar-thumb pointer movement into a content scroll delta.",["scrolling","scrollbar","geometry"],"moderate")

p=P+'elements/size_constraint_switch.rs'; C(p)
classes[p]['SizeConstraintSwitch']=("Responsive element selecting an active child variant based on which size constraint the available space satisfies.",["ui-element","responsive","conditional"],"moderate")
classes[p]['SizeConstraintCondition']=("Enum of size predicates (WidthLessThan, HeightLessThan, SizeSmallerThan) used to switch child variants.",["enum","responsive","constraints"],"simple")

p=P+'elements/stack/mod.rs'; C(p)
classes[p]['Stack']=("Z-ordered stack overlaying positioned and overlay children over a base child with configurable event dispatch.",["ui-element","z-stacking","overlay","layout"],"complex")
classes[p]['EventDispatchMode']=("Enum controlling stack event dispatch: Broadcast to all children or Waterfall until handled.",["enum","event-handling","stacking"],"simple")

p=P+'elements/stack/overlay.rs'; C(p)
classes[p]['Overlay']=("Wrapper marking a child as an overlay layer painted above base content in a Stack.",["ui-element","overlay","stacking"],"simple")

p=P+'elements/stack/positioned.rs'; C(p)
classes[p]['Positioned']=("Stack child wrapper applying an absolute offset to its child via parent-data.",["ui-element","positioning","stacking"],"moderate")

p=P+'elements/stack/save_position.rs'; C(p)
classes[p]['SavePosition']=("Stack helper recording its child's painted position under an id for later anchor lookup.",["ui-element","positioning","state-tracking"],"moderate")

p=P+'elements/table/mod.rs'; C(p); F(p)
classes[p]['Table']=("Virtualized table element with intrinsic/flex/fixed column sizing, headers, striped rows, dividers and vertical scrolling.",["ui-element","table","virtualization"],"complex")
classes[p]['TableState']=("Mutable table state: row store, measured heights, scroll position, viewport and cached column widths for virtualization.",["table","state-management","virtualization"],"complex")
classes[p]['TableStateHandle']=("Shared handle over TableState exposing invalidation, scroll-to-row and row-count/render-fn mutation.",["table","state","handle"],"moderate")
classes[p]['TableConfig']=("Table styling/behaviour config: borders, dividers, cell padding, header background, row backgrounds and vertical sizing.",["table","config","styling"],"moderate")
classes[p]['TableColumnWidth']=("Enum of column sizing strategies: Fixed, Flex, Fraction or Intrinsic.",["enum","table","layout"],"simple")
classes[p]['TableHeader']=("Header cell descriptor holding content and an optional explicit width.",["table","value-type","header"],"simple")
classes[p]['RowBackground']=("Row background config supporting uniform or striped (even/odd) colouring with per-row resolution.",["table","styling","value-type"],"simple")
functions[p]['compute_column_widths']=("Resolves final column pixel widths from sizing strategies and measured intrinsic widths within the available width.",["table","layout","measurement"],"complex")

p=P+'elements/text.rs'; C(p); F(p)
classes[p]['Text']=("Single styled-string text element with highlights, soft-wrap, autosize, clickable/hoverable ranges and selection.",["ui-element","text-rendering","selection","styling"],"complex")
classes[p]['Highlight']=("Styling overlay (text style + foreground color) applied to a highlighted character range.",["text-rendering","styling","value-type"],"simple")
classes[p]['HighlightedRange']=("A highlight paired with the sorted indices it applies to, with range-merging support.",["text-rendering","styling","value-type"],"simple")
classes[p]['Styles']=("Bundle of font properties and styles applied at specific glyph indices.",["text-rendering","styling","value-type"],"simple")
classes[p]['LaidOutText']=("Enum of laid-out text representations (None, single Line, multi-line Frame) with width/height/paint helpers.",["enum","text-rendering","layout"],"moderate")
functions[p]['merge_overlapping_ranges']=("Merges a list of possibly-overlapping index ranges into a minimal non-overlapping set for highlight application.",["text-rendering","utility","ranges"],"moderate")

p=P+'elements/uniform_list.rs'; C(p)
classes[p]['UniformList']=("Virtualized uniform-height list rendering only visible items with scroll-to-item and autoscroll.",["ui-element","list","virtualization"],"complex")
classes[p]['UniformListState']=("Shared scroll state for a UniformList: current scroll-top and pending scroll-to target.",["list","state-management"],"simple")

p=P+'elements/viewported_list.rs'; C(p); F(p)
classes[p]['List']=("Virtualized variable-height list element rendering only items within the viewport.",["ui-element","list","virtualization"],"complex")
classes[p]['ListState']=("Shared handle over a viewported list's content, scroll position and measurement state.",["list","state","handle"],"moderate")
classes[p]['ListStateInner']=("Inner list state: item content, measured heights, viewport height, scroll preservation and scroll channel.",["list","state-management","virtualization"],"moderate")
classes[p]['ScrollOffset']=("Scroll position expressed as a list-item index plus a pixel offset from that item's start.",["list","scrolling","value-type"],"simple")
classes[p]['ScrollPreservation']=("Policy holding an adjustment function to preserve scroll position across content changes.",["list","scroll-preservation","policy"],"simple")
functions[p]['absolute_pixels_to_scroll_offset']=("Converts an absolute pixel scroll position into an item-index-plus-offset ScrollOffset using measured heights.",["list","scrolling","measurement"],"moderate")

p=P+'event.rs'; C(p); F(p)
classes[p]['Event']=("Enum of all input events: key down, scroll wheel, mouse buttons/drag/move, modifiers, typed characters, drag-and-drop and IME marked text.",["enum","event-model","input"],"complex")
classes[p]['DispatchedEvent']=("Carrier wrapping a raw Event with z-index-aware dispatch context during event propagation.",["event-model","dispatch"],"moderate")
classes[p]['ModifiersState']=("Bitset-like state of active keyboard modifiers (alt, cmd, shift, ctrl, func).",["event-model","keyboard","state"],"simple")
classes[p]['KeyEventDetails']=("Detailed key-event info distinguishing left/right alt and the key without modifiers.",["event-model","keyboard","value-type"],"simple")
classes[p]['InBoundsExt']=("Extension trait adding in_bounds bounds-checking to event/position types.",["trait","event-model","geometry"],"simple")
functions[p]['scale_up']=("Scales an event's coordinates by a zoom factor, producing a DPI/zoom-adjusted event.",["event-model","geometry","scaling"],"complex")

p=P+'text/header.rs'; C(p)
classes[p]['BlockHeaderSize']=("Enum of markdown heading levels (Header1-6) with font-size multipliers, weights, labels and conversions.",["enum","markdown","headings"],"moderate")

p=P+'text/mod.rs'; C(p); F(p)
classes[p]['SelectionType']=("Enum classifying a selection as Simple, Semantic, Lines or Rect, derived from click count/modifiers.",["enum","selection","text"],"simple")
classes[p]['SelectionDirection']=("Enum of selection direction: Forward or Backward.",["enum","selection"],"simple")
classes[p]['TextBuffer']=("Trait abstracting a text buffer with char/point/offset navigation and word-boundary queries.",["trait","text","buffer","navigation"],"complex")
classes[p]['IsRect']=("Boolean-like enum (True/False) flagging whether a selection is a rectangular selection.",["enum","selection"],"simple")
functions[p]['char_slice']=("Returns the substring of a string between character (not byte) start/end indices, handling UTF-8.",["text","utility","utf-8"],"moderate")
functions[p]['count_chars_up_to_byte']=("Counts the number of characters before a given byte offset in a UTF-8 string.",["text","utility","utf-8"],"simple")

p=P+'text/point.rs'; C(p)
classes[p]['Point']=("Row/column text coordinate with arithmetic, ordering and zero helpers.",["text","coordinates","value-type"],"moderate")

p=P+'text/word_boundaries.rs'; C(p)
classes[p]['WordBoundaries']=("Iterator over word boundaries in a TextBuffer, walking to word starts/ends per a boundary policy.",["text","word-boundaries","iterator"],"complex")
classes[p]['WordBoundariesPolicy']=("Enum of word-boundary policies: Default, Custom or OnlyWhitespace.",["enum","text","word-boundaries"],"simple")

p=P+'text/words.rs'; F(p)
functions[p]['split_at_next_word_start']=("Splits a string at the start of the next word, returning the leading segment and remainder.",["text","word-boundaries","utility"],"moderate")

p=P+'units.rs'; C(p)
classes[p]['Lines']=("Newtype length in text lines with conversion to pixels (via line height), arithmetic and comparison.",["units","value-type","layout"],"moderate")
classes[p]['Pixels']=("Newtype length in pixels with conversion to lines (via line height), arithmetic and comparison.",["units","value-type","layout"],"moderate")

# ---------- Build nodes & edges ----------
nodes = []
edges = []
seen_node_ids = set()

def add_node(node):
    if node['id'] in seen_node_ids:
        return
    seen_node_ids.add(node['id'])
    nodes.append(node)

def fname(path):
    return path.split('/')[-1]

# File nodes
for path,(summary,tags,complexity,ln) in files_meta.items():
    n = {"id":f"file:{path}","type":"file","name":fname(path),"filePath":path,
         "summary":summary,"tags":tags,"complexity":complexity}
    if ln: n["languageNotes"]=ln
    add_node(n)

# Class nodes + contains/exports
for path, cmap in classes.items():
    exps = exports_set(path)
    for name,(summary,tags,complexity) in cmap.items():
        cid=f"class:{path}:{name}"
        add_node({"id":cid,"type":"class","name":name,"filePath":path,
                  "lineRange":cls_range(path,name),"summary":summary,"tags":tags,"complexity":complexity})
        edges.append({"source":f"file:{path}","target":cid,"type":"contains","direction":"forward","weight":1.0})
        if name in exps:
            edges.append({"source":f"file:{path}","target":cid,"type":"exports","direction":"forward","weight":0.8})

# Function nodes + contains/exports
for path, fmap in functions.items():
    exps = exports_set(path)
    for name,(summary,tags,complexity) in fmap.items():
        fid=f"function:{path}:{name}"
        add_node({"id":fid,"type":"function","name":name,"filePath":path,
                  "lineRange":fn_range(path,name),"summary":summary,"tags":tags,"complexity":complexity})
        edges.append({"source":f"file:{path}","target":fid,"type":"contains","direction":"forward","weight":1.0})
        if name in exps:
            edges.append({"source":f"file:{path}","target":fid,"type":"exports","direction":"forward","weight":0.8})

# Import edges (1:1 from batchImportData)
for path, targets in import_data.items():
    for t in targets:
        edges.append({"source":f"file:{path}","target":f"file:{t}","type":"imports","direction":"forward","weight":0.7})

# Implements edges -> Element trait (cross-batch, in elements/mod.rs)
ELEMENT_TRAIT = "class:crates/warpui_core/src/elements/mod.rs:Element"
element_impls = [
 (P+'elements/align.rs','Align'),(P+'elements/clipped.rs','Clipped'),
 (P+'elements/constrained_box.rs','ConstrainedBox'),(P+'elements/container.rs','Container'),
 (P+'elements/dismiss.rs','Dismiss'),(P+'elements/empty.rs','Empty'),
 (P+'elements/flex/mod.rs','Flex'),(P+'elements/flex/mod.rs','Expanded'),(P+'elements/flex/mod.rs','Shrinkable'),
 (P+'elements/flex/wrap.rs','Wrap'),(P+'elements/flex/wrap.rs','WrapFill'),(P+'elements/flex/wrap.rs','WrapChild'),
 (P+'elements/formatted_text_element.rs','FormattedTextElement'),
 (P+'elements/hoverable.rs','Hoverable'),(P+'elements/live.rs','LiveElement'),
 (P+'elements/min_size.rs','MinSize'),
 (P+'elements/new_scrollable/mod.rs','NewScrollable'),
 (P+'elements/selectable_area.rs','SelectableArea'),
 (P+'elements/size_constraint_switch.rs','SizeConstraintSwitch'),
 (P+'elements/stack/mod.rs','Stack'),(P+'elements/stack/overlay.rs','Overlay'),
 (P+'elements/stack/positioned.rs','Positioned'),(P+'elements/stack/save_position.rs','SavePosition'),
 (P+'elements/table/mod.rs','Table'),(P+'elements/text.rs','Text'),
 (P+'elements/uniform_list.rs','UniformList'),(P+'elements/viewported_list.rs','List'),
 (P+'elements/new_scrollable/scrollable_tests.rs','ScrollableElement'),
 (P+'elements/new_scrollable/scrollable_tests.rs','SelectableProbeElement'),
]
for path,name in element_impls:
    edges.append({"source":f"class:{path}:{name}","target":ELEMENT_TRAIT,"type":"implements","direction":"forward","weight":0.9})

# implements NewScrollableElement (in-batch trait) for test ScrollableElement
NSE = f"class:{P}elements/new_scrollable/mod.rs:NewScrollableElement"
edges.append({"source":f"class:{P}elements/new_scrollable/scrollable_tests.rs:ScrollableElement","target":NSE,"type":"implements","direction":"forward","weight":0.9})

# calls (high confidence)
edges.append({"source":f"function:{P}elements/new_scrollable/dual_axis_config.rs:scroll_to_position_and_paint_clipped",
              "target":f"function:{P}elements/new_scrollable/util.rs:scroll_clipped_scrollable_handle_with_delta",
              "type":"calls","direction":"forward","weight":0.8})
edges.append({"source":f"function:{P}elements/new_scrollable/mod.rs:mousewheel",
              "target":f"function:{P}elements/new_scrollable/util.rs:child_constraint_for_axis",
              "type":"calls","direction":"forward","weight":0.8})

# tested_by (production -> test)
test_file = f"file:{P}elements/new_scrollable/scrollable_tests.rs"
for prod in ['new_scrollable/mod.rs','new_scrollable/dual_axis_config.rs','new_scrollable/single_axis_config.rs','new_scrollable/util.rs']:
    edges.append({"source":f"file:{P}elements/{prod}","target":test_file,"type":"tested_by","direction":"forward","weight":0.5})

# ---------- Partition into parts ----------
all_paths = sorted(files_meta.keys())
N = len(all_paths)
parts = 4
chunk = math.ceil(N/parts)
groups = [all_paths[i:i+chunk] for i in range(0, N, chunk)]

def node_file(n):
    return n.get('filePath')

outdir = f'{ROOT}/.understand-anything/intermediate'
total_nodes=0; total_edges=0
written=[]
for k, group in enumerate(groups, start=1):
    gset = set(group)
    part_nodes = [n for n in nodes if node_file(n) in gset]
    part_node_ids = {n['id'] for n in part_nodes}
    # edges whose source is in this part's nodes
    part_edges = [e for e in edges if e['source'] in part_node_ids]
    frag = {"nodes":part_nodes,"edges":part_edges}
    fp = f'{outdir}/batch-1-part-{k}.json'
    json.dump(frag, open(fp,'w'), indent=1)
    written.append((fp,len(part_nodes),len(part_edges)))
    total_nodes+=len(part_nodes); total_edges+=len(part_edges)

print("total imports in data:", sum(len(v) for v in import_data.values()))
print("total import edges emitted:", sum(1 for e in edges if e['type']=='imports'))
print("TOTAL nodes:",len(nodes)," edges:",len(edges))
for fp,nn,ee in written:
    print(f"  {fp}: nodes={nn} edges={ee}")
print("partition node sum:",total_nodes," edge sum:",total_edges)
# sanity: every node assigned to exactly one part
assert total_nodes==len(nodes), (total_nodes,len(nodes))
