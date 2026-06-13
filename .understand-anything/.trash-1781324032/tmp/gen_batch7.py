import json, math

ROOT = "/home/mhb/warp"
PFX = "crates/editor/src/"

# ---------------- File nodes ----------------
# (path, name, summary, tags, complexity, languageNotes)
files = [
 ("content/undo_tests.rs","undo_tests.rs",
  "Unit tests verifying that the editor's buffer version tracks correctly across edits, undo, redo, stack overflow, and full rollback.",
  ["test","undo-redo","versioning","editor"],"moderate",None),
 ("content/validation.rs","validation.rs",
  "Validates that an editor content buffer is internally consistent (balanced style markers, well-formed block/header decorations) before it is committed.",
  ["validation","content-model","invariants","editor"],"moderate",None),
 ("content/validation_tests.rs","validation_tests.rs",
  "Unit tests exercising validate_content across malformed and well-formed buffers: unmatched style markers, headers, styled code, and block items.",
  ["test","validation","content-model","editor"],"moderate",None),
 ("content/version.rs","version.rs",
  "Defines BufferVersion, a monotonically increasing version stamp used to detect and reconcile changes to the editor content buffer.",
  ["data-model","versioning","content-model"],"simple",None),
 ("decoration/mod.rs","mod.rs",
  "Decoration layer module that updates per-buffer decoration state in response to edit deltas and version changes.",
  ["decoration","editor","data-model"],"simple",None),
 ("editor.rs","editor.rs",
  "Public editor view traits and supporting types: EditorView surface, embedded/runnable block models, text-decoration color maps, and the NavigationKey enum.",
  ["editor","trait-definition","decoration","navigation"],"moderate",
  "Heavy use of trait objects (dyn) to abstract embedded block models behind a uniform view interface."),
 ("lib.rs","lib.rs",
  "Crate root for the editor engine, declaring and re-exporting the content, decoration, model, multiline, render, search, and selection modules.",
  ["entry-point","barrel","crate-root"],"simple",None),
 ("model.rs","model.rs",
  "Core editor model layer: CoreEditorModel drives buffer edits, selections and cursor movement, while PlainTextEditorModel and RichTextEditorModel specialize behavior for plain vs. markdown-rich editing.",
  ["data-model","editor","selection","rich-text"],"complex",
  "Large model module organized as a shared CoreEditorModel plus two facade models that delegate to it for plain-text vs. rich-text semantics."),
 ("multiline.rs","multiline.rs",
  "Line-ending aware string types (MultilineString/Str, AnyMultilineString) plus inference and normalization utilities that keep CR/LF/CRLF handling correct across the editor.",
  ["utility","line-endings","string-types","serialization"],"complex",
  "Newtype wrappers with typestate-like LineFormat markers (LF/CRLF/CR) to encode line-ending guarantees in the type system."),
 ("parallel_util.rs","parallel_util.rs",
  "Small rayon helper providing a Last combinator that collects a parallel iterator while keeping only the final element.",
  ["utility","parallelism","rayon"],"simple",
  "Implements FromParallelIterator/ParallelExtend so the type plugs directly into rayon collect pipelines."),
 ("render/element/broken_embedding.rs","broken_embedding.rs",
  "Renderable element that draws a placeholder/error block when an embedded item (image, mermaid, etc.) fails to load, with a remove button.",
  ["render","ui-element","embedded-block","error-state"],"moderate",None),
 ("render/element/empty.rs","empty.rs",
  "Renderable element representing an empty document line, painting placeholder text and an editor cursor when appropriate.",
  ["render","ui-element","placeholder","cursor"],"moderate",None),
 ("render/element/header.rs","header.rs",
  "Renderable element for markdown header lines, laying out and painting heading text with header-specific styling.",
  ["render","ui-element","markdown","header"],"moderate",None),
 ("render/element/hidden_section.rs","hidden_section.rs",
  "Renderable element for collapsed/hidden document sections, dispatching click events to expand and reporting hidden-section state.",
  ["render","ui-element","collapsible","event-handler"],"moderate",None),
 ("render/element/horizontal_rule.rs","horizontal_rule.rs",
  "Renderable element drawing a markdown horizontal rule, including selection highlight and cursor rectangle handling.",
  ["render","ui-element","markdown","cursor"],"moderate",None),
 ("render/element/image.rs","image.rs",
  "Renderable element that lays out and paints an inline image block within the rich-text editor.",
  ["render","ui-element","image","embedded-block"],"moderate",None),
 ("render/element/lens_element.rs","lens_element.rs",
  "RichTextElementLens renders a windowed sub-range of editor blocks (a lens) for embedding editor content inside other views.",
  ["render","ui-element","lens","viewport"],"moderate",None),
 ("render/element/mermaid.rs","mermaid.rs",
  "Renderable element that lays out and paints a rendered Mermaid diagram block, with a footer and focus-aware interaction.",
  ["render","ui-element","mermaid","embedded-block"],"moderate",None),
 ("render/element/mod.rs","mod.rs",
  "Central rich-text rendering element: owns the block layout/paint pipeline, the RenderableBlock trait, hit-testing, mouse/keyboard dispatch, cursor blink state, and the RichTextAction command surface.",
  ["render","ui-element","event-handler","layout","hit-testing"],"complex",
  "Defines the RenderableBlock trait object interface that every concrete element (image, table, header, etc.) implements, plus a large dispatch_event router."),
 ("render/element/ordered_list.rs","ordered_list.rs",
  "Renderable element for an ordered-list item, rendering its number marker and indentation alongside the line content.",
  ["render","ui-element","markdown","list"],"moderate",None),
 ("render/element/paint.rs","paint.rs",
  "RenderContext paint helpers: converts content coordinates to screen space and draws paragraphs, text, lines, decorations, and cursors for rich-text blocks.",
  ["render","painting","cursor","coordinates"],"complex",
  "Centralizes content-to-screen coordinate mapping so individual elements paint via a shared RenderContext."),
 ("render/element/paragraph.rs","paragraph.rs",
  "Renderable element for a plain paragraph line, painting its text and slash-menu placeholder when empty.",
  ["render","ui-element","paragraph","placeholder"],"moderate",None),
 ("render/element/placeholder.rs","placeholder.rs",
  "BlockPlaceholder draws hint/placeholder text for empty blocks, tracking a layout state machine (PendingLayout/LaidOut/NotShown).",
  ["render","ui-element","placeholder","state-machine"],"moderate",None),
 ("render/element/runnable_command.rs","runnable_command.rs",
  "Renderable element that paints a runnable-command block with a run footer and border, dispatching click-to-run events.",
  ["render","ui-element","runnable-command","event-handler"],"moderate",None),
 ("render/element/table.rs","table.rs",
  "Renderable element for markdown tables: paints backgrounds, borders, cell text, selection and cursor, and handles horizontal scrolling with a draggable scrollbar.",
  ["render","ui-element","table","scrolling"],"complex",
  "Includes a horizontal scrollbar with drag state that must survive renderable recreation, plus selection/cursor geometry math."),
 ("render/element/table_tests.rs","table_tests.rs",
  "Unit tests for table layout geometry, coordinate-to-offset mapping, cell ranges, scrollbar behavior, and selection/cursor offset math.",
  ["test","table","render","geometry"],"complex",None),
]

# ---------------- Sub nodes ----------------
# (kind, path, name, start, end, exported, summary, tags, complexity)
S=[
 # validation.rs
 ("function","content/validation.rs","validate_content",13,140,True,
  "Walks the content buffer enforcing structural invariants: balanced style start/end markers, single text markers, valid header and block-item decorations.",
  ["validation","invariants","content-model"],"complex"),
 # version.rs
 ("class","content/version.rs","BufferVersion",4,17,True,
  "Newtype wrapping a usize version counter for the content buffer, with constructors and accessor used to detect stale state.",
  ["data-model","versioning"],"simple"),
 # decoration/mod.rs
 ("class","decoration/mod.rs","DecorationLayer",7,15,True,
  "Owns decoration state for a buffer and reconciles it against edit deltas and the latest buffer version.",
  ["decoration","data-model","editor"],"simple"),
 # editor.rs
 ("class","editor.rs","EditorView",20,57,True,
  "View-surface trait exposing runnable commands, embedded items, and text decorations for an editor instance.",
  ["trait-definition","editor","view"],"moderate"),
 ("class","editor.rs","TextDecoration",60,66,True,
  "Holds base/override color maps and an optional underline range describing how a span of editor text is decorated.",
  ["data-model","decoration"],"simple"),
 ("function","editor.rs","to_paint_style_override",71,89,True,
  "Builds a paint-time style override for a text range from the decoration's base and override color maps.",
  ["decoration","painting","utility"],"moderate"),
 ("class","editor.rs","EmbeddedItemModel",120,126,True,
  "Trait for embedded item blocks (images, diagrams) defining footer rendering, border, and remove-button behavior.",
  ["trait-definition","embedded-block"],"simple"),
 ("class","editor.rs","RunnableCommandModel",129,141,True,
  "Trait for runnable-command blocks defining footer rendering, border, and downcast support.",
  ["trait-definition","runnable-command"],"simple"),
 ("class","editor.rs","NavigationKey",145,154,True,
  "Enum of directional/navigation keys (Tab, arrows, page up/down) used to drive editor cursor movement.",
  ["enum","navigation","input"],"simple"),
 # model.rs
 ("function","model.rs","apply_edit",35,44,True,
  "Applies an edit action to the model with a given origin and selection model, without autoscroll.",
  ["editor","edit","mutation"],"simple"),
 ("function","model.rs","apply_edit_with_autoscroll",46,61,True,
  "Applies an edit action and optionally autoscrolls the viewport to keep the cursor visible.",
  ["editor","edit","scrolling"],"moderate"),
 ("class","model.rs","CoreEditorModel",68,690,True,
  "Core editing engine: manages the content buffer, selection model, cursor movement, word/line navigation, undo/redo, indentation, and layout rebuilds.",
  ["data-model","editor","selection","undo-redo"],"complex"),
 ("class","model.rs","PlainTextEditorModel",692,780,True,
  "Plain-text facade over CoreEditorModel handling enter, delete, clipboard read, copy-all, and reset for single/plain editors.",
  ["data-model","editor","plain-text"],"moderate"),
 ("class","model.rs","RichTextEditorModel",782,1218,True,
  "Rich-text facade over CoreEditorModel adding markdown semantics: block conversion, links, task lists, placeholders, embeddings, and code-block handling.",
  ["data-model","editor","rich-text","markdown"],"complex"),
 # multiline.rs
 ("class","multiline.rs","LineFormat",50,59,True,
  "Trait abstracting a line-ending format (LF/CRLF/CR) so multiline string types can be parameterized over their ending.",
  ["trait-definition","line-endings"],"simple"),
 ("class","multiline.rs","MultilineString",72,75,True,
  "Owned string newtype carrying a compile-time LineFormat guarantee about its line endings.",
  ["string-types","line-endings","data-model"],"simple"),
 ("class","multiline.rs","AnyMultilineString",87,90,True,
  "Owned multiline string with a runtime-tracked line ending, supporting inference, normalization, and conversion to a specific format.",
  ["string-types","line-endings","serialization"],"moderate"),
 ("class","multiline.rs","IncorrectLineEndingError",102,105,True,
  "Error type reporting a mismatch between the expected and actual line ending when constructing a typed multiline string.",
  ["error-type","line-endings"],"simple"),
 ("function","multiline.rs","try_new",185,205,False,
  "Fallibly constructs a typed multiline string, returning IncorrectLineEndingError if the text's endings do not match the format.",
  ["line-endings","validation","factory"],"moderate"),
 ("class","multiline.rs","TextLineEndings",470,480,True,
  "Enum classifying a text's line endings as single-line or multi-line, with helpers to detect mixed endings and pick a primary ending.",
  ["enum","line-endings"],"moderate"),
 ("function","multiline.rs","evaluate_line_endings",507,537,False,
  "Scans text to count and classify its line endings, producing a TextLineEndings summary used for inference.",
  ["line-endings","analysis","utility"],"moderate"),
 # parallel_util.rs
 ("class","parallel_util.rs","Last",9,11,True,
  "Rayon collector wrapper that consumes a parallel iterator and retains only its last produced element.",
  ["utility","parallelism","rayon"],"simple"),
 # broken_embedding.rs
 ("class","render/element/broken_embedding.rs","RenderableBrokenEmbedding",15,18,True,
  "Renderable block that draws an error/placeholder card with a remove button when an embedded item cannot be displayed.",
  ["render","ui-element","error-state"],"moderate"),
 ("function","render/element/broken_embedding.rs","new",21,65,False,
  "Constructs the broken-embedding renderable, building its footer/remove-button layout from the viewport item and styles.",
  ["render","constructor"],"moderate"),
 ("function","render/element/broken_embedding.rs","paint",97,157,False,
  "Paints the broken-embedding card background, message, and remove button into the frame.",
  ["render","painting"],"complex"),
 # empty.rs
 ("class","render/element/empty.rs","Empty",12,15,True,
  "Renderable block for an empty line, painting placeholder text and the editor cursor.",
  ["render","ui-element","placeholder"],"moderate"),
 # header.rs
 ("class","render/element/header.rs","RenderableHeader",8,11,True,
  "Renderable block for a markdown header line, laying out and painting heading text with header styling.",
  ["render","ui-element","markdown"],"moderate"),
 # hidden_section.rs
 ("class","render/element/hidden_section.rs","RenderableHiddenSection",17,20,True,
  "Renderable block for a collapsed section, dispatching expand clicks and reporting hidden-section state.",
  ["render","ui-element","collapsible"],"moderate"),
 # horizontal_rule.rs
 ("class","render/element/horizontal_rule.rs","HorizontalRule",12,14,True,
  "Renderable block drawing a markdown horizontal rule with selection and cursor handling.",
  ["render","ui-element","markdown"],"moderate"),
 ("function","render/element/horizontal_rule.rs","draw_rect",21,61,False,
  "Draws the horizontal-rule rectangle, applying selection highlight and an optional cursor based on the supplied styles.",
  ["render","painting","cursor"],"moderate"),
 # image.rs
 ("class","render/element/image.rs","RenderableImage",11,17,True,
  "Renderable block that lays out and paints an inline image element.",
  ["render","ui-element","image"],"moderate"),
 ("function","render/element/image.rs","paint",57,102,False,
  "Paints the inline image into the frame at its laid-out bounds, handling selection state.",
  ["render","painting","image"],"moderate"),
 # lens_element.rs
 ("class","render/element/lens_element.rs","RichTextElementLens",19,27,True,
  "Renders a windowed sub-range of editor blocks so editor content can be embedded as a read-only lens inside other views.",
  ["render","ui-element","lens"],"moderate"),
 ("function","render/element/lens_element.rs","layout",60,96,False,
  "Lays out the lens's visible block range within a constraint, computing element size and origin.",
  ["render","layout"],"moderate"),
 ("function","render/element/lens_element.rs","paint",104,146,False,
  "Paints the lens's blocks at the given origin, clipping to the lens bounds.",
  ["render","painting"],"moderate"),
 # mermaid.rs
 ("class","render/element/mermaid.rs","RenderableMermaidDiagram",16,20,True,
  "Renderable block for a rendered Mermaid diagram, owning the image element and an interactive footer.",
  ["render","ui-element","mermaid"],"moderate"),
 ("function","render/element/mermaid.rs","layout",46,116,False,
  "Lays out the Mermaid diagram image and footer, computing sizing and focus-dependent decorations.",
  ["render","layout"],"complex"),
 ("function","render/element/mermaid.rs","paint",118,178,False,
  "Paints the Mermaid diagram image and footer into the frame.",
  ["render","painting"],"complex"),
 # mod.rs (render/element)
 ("class","render/element/mod.rs","RichTextElement",91,130,True,
  "The top-level rich-text render element: holds the block list, viewport, display state/options, and orchestrates layout, paint, and event dispatch.",
  ["render","ui-element","viewport"],"complex"),
 ("class","render/element/mod.rs","DisplayState",136,146,True,
  "Mutable per-frame display state for the editor: cursor visibility, hovered location, and the next blink update deadline.",
  ["render","state","cursor"],"simple"),
 ("class","render/element/mod.rs","DisplayOptions",160,186,True,
  "Configuration controlling how the rich-text element renders: editable/focused flags, cursor blinking, gutters, and vertical expansion behavior.",
  ["render","configuration"],"moderate"),
 ("class","render/element/mod.rs","RenderableBlock",205,298,True,
  "Trait object interface implemented by every concrete renderable block (image, table, header, etc.) defining layout, paint, event dispatch, and bounds.",
  ["trait-definition","render","ui-element"],"complex"),
 ("class","render/element/mod.rs","RichTextAction",307,385,True,
  "Enum of user-driven rich-text actions (scroll, typing, mouse down/drag/up, hover, task-list click) routed through the render element.",
  ["enum","event-handler","render"],"moderate"),
 ("function","render/element/mod.rs","renderable_blocks",824,925,False,
  "Builds the list of concrete RenderableBlock instances for the current visible viewport range from the model's blocks.",
  ["render","layout","factory"],"complex"),
 ("function","render/element/mod.rs","paint",1051,1157,False,
  "Paints all visible renderable blocks, decorations, and cursors for the rich-text element at the given origin.",
  ["render","painting"],"complex"),
 ("function","render/element/mod.rs","dispatch_event",1167,1235,False,
  "Routes input events (mouse, scroll, typing) to the appropriate handlers and target block within the rich-text element.",
  ["event-handler","render","input"],"complex"),
 # ordered_list.rs
 ("class","render/element/ordered_list.rs","RenderableOrderedListItem",16,21,True,
  "Renderable block for an ordered-list item, painting its number marker and indentation with the line content.",
  ["render","ui-element","list"],"moderate"),
 # paint.rs
 ("class","render/element/paint.rs","CursorDisplayType",25,30,True,
  "Enum selecting cursor rendering style: Bar, Block, or Underline.",
  ["enum","cursor","render"],"simple"),
 ("class","render/element/paint.rs","CursorData",34,37,True,
  "Carries per-cursor paint metrics (block width and font size) used when drawing block/bar cursors.",
  ["data-model","cursor","render"],"simple"),
 ("class","render/element/paint.rs","RenderContext",53,76,True,
  "Per-paint context bundling bounds, scroll/viewport offset, decorations and saved positions; provides content-to-screen mapping and draw helpers.",
  ["render","painting","coordinates"],"complex"),
 ("function","render/element/paint.rs","draw_text",199,245,False,
  "Draws a text frame at a content position, applying an optional paint-style override and the base style.",
  ["render","painting","text"],"moderate"),
 # paragraph.rs
 ("class","render/element/paragraph.rs","RenderableParagraph",24,27,True,
  "Renderable block for a plain paragraph line, painting text and an empty-line slash-menu placeholder.",
  ["render","ui-element","paragraph"],"moderate"),
 # placeholder.rs
 ("class","render/element/placeholder.rs","BlockPlaceholder",15,18,True,
  "Draws hint/placeholder text for empty blocks, tracking a layout state machine to decide when and where to show it.",
  ["render","ui-element","placeholder","state-machine"],"moderate"),
 ("function","render/element/placeholder.rs","layout",41,87,False,
  "Lays out the placeholder text relative to an item's content, transitioning the placeholder state machine.",
  ["render","layout","state-machine"],"moderate"),
 ("function","render/element/placeholder.rs","paint",91,128,False,
  "Paints the placeholder text at the computed content origin using the block style.",
  ["render","painting"],"moderate"),
 # runnable_command.rs
 ("class","render/element/runnable_command.rs","RenderableRunnableCommand",13,17,True,
  "Renderable block for a runnable-command block, painting a run footer and border and dispatching click-to-run events.",
  ["render","ui-element","runnable-command"],"moderate"),
 ("function","render/element/runnable_command.rs","paint",61,104,False,
  "Paints the runnable-command block content, footer, and border into the frame.",
  ["render","painting"],"moderate"),
 # table.rs
 ("class","render/element/table.rs","RenderableTable",25,29,True,
  "Renderable block for markdown tables, owning viewport bounds and a horizontal scrollbar and handling paint plus pointer events.",
  ["render","ui-element","table","scrolling"],"complex"),
 ("class","render/element/table.rs","TableLayoutReport",33,40,False,
  "Geometry snapshot of a laid-out table (column widths/lefts, row heights/tops, header height, total height) used for hit-testing and painting.",
  ["data-model","table","geometry"],"simple"),
 ("function","render/element/table.rs","dispatch_event",169,282,False,
  "Handles table pointer events: scrollbar drag, horizontal scroll, and cell selection/cursor placement.",
  ["event-handler","table","scrolling"],"complex"),
 ("function","render/element/table.rs","paint",117,167,False,
  "Paints the table by drawing backgrounds, borders, cell text, selection, cursor, and the horizontal scrollbar.",
  ["render","painting","table"],"moderate"),
 ("function","render/element/table.rs","paint_selection",484,583,False,
  "Computes and paints the highlighted selection region across table cells relative to the table's screen position.",
  ["render","painting","selection","table"],"complex"),
]

def file_id(p): return "file:"+PFX+p
def sub_id(kind,p,name): return ("class:" if kind=="class" else "function:")+PFX+p+":"+name

nodes=[]
for p,name,summ,tags,cx,ln in files:
    n={"id":file_id(p),"type":"file","name":name,"filePath":PFX+p,
       "summary":summ,"tags":tags,"complexity":cx}
    if ln: n["languageNotes"]=ln
    nodes.append(n)

for kind,p,name,s,e,exp,summ,tags,cx in S:
    nodes.append({"id":sub_id(kind,p,name),"type":kind,"name":name,
        "filePath":PFX+p,"lineRange":[s,e],"summary":summ,"tags":tags,"complexity":cx})

edges=[]
# imports
imp=json.load(open(ROOT+"/.understand-anything/intermediate/batches.json"))
bid={}
for b in imp["batches"]:
    if b["batchIndex"]==7: bid=b["batchImportData"]
for src,targets in bid.items():
    for t in targets:
        edges.append({"source":"file:"+src,"target":"file:"+t,"type":"imports","direction":"forward","weight":0.7})
# contains + exports
for kind,p,name,s,e,exp,summ,tags,cx in S:
    edges.append({"source":file_id(p),"target":sub_id(kind,p,name),"type":"contains","direction":"forward","weight":1.0})
    if exp:
        edges.append({"source":file_id(p),"target":sub_id(kind,p,name),"type":"exports","direction":"forward","weight":0.8})
# tested_by (production -> test)
edges.append({"source":file_id("content/validation.rs"),"target":file_id("content/validation_tests.rs"),"type":"tested_by","direction":"forward","weight":0.5})
edges.append({"source":file_id("model.rs"),"target":file_id("content/undo_tests.rs"),"type":"tested_by","direction":"forward","weight":0.5})
edges.append({"source":file_id("render/element/table.rs"),"target":file_id("render/element/table_tests.rs"),"type":"tested_by","direction":"forward","weight":0.5})

# ---- partition into 2 parts by sorted file path ----
sorted_paths=sorted(PFX+p for p,*_ in files)
part_of={}
half=math.ceil(len(sorted_paths)/2)
for i,fp in enumerate(sorted_paths):
    part_of[fp]=1 if i<half else 2

def node_filepath(n): return n["filePath"]
def edge_src_filepath(ed):
    s=ed["source"]
    # strip prefix
    body=s.split(":",1)[1]
    # for file: body is path; for class/function: path:name -> path before last ':' only if name present
    if s.startswith("file:"): return body
    return body.rsplit(":",1)[0]

for part in (1,2):
    pnodes=[n for n in nodes if part_of[node_filepath(n)]==part]
    pedges=[e for e in edges if part_of[edge_src_filepath(e)]==part]
    out={"nodes":pnodes,"edges":pedges}
    fn=ROOT+f"/.understand-anything/intermediate/batch-7-part-{part}.json"
    json.dump(out,open(fn,"w"),indent=1)
    print(f"part{part}: nodes={len(pnodes)} edges={len(pedges)} -> {fn}")

print("total nodes",len(nodes),"total edges",len(edges))
print("total imports",sum(len(v) for v in bid.values()))
