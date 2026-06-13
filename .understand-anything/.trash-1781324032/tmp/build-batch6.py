import json, math, os

BASE = "crates/editor/src/content/"
def fp(name): return BASE + name

# import data
batches = json.load(open('/home/mhb/warp/.understand-anything/intermediate/batches.json'))
b6 = next(b for b in batches['batches'] if b['batchIndex']==6)
imp = b6['batchImportData']

# ---------- File node metadata ----------
# (filename) -> (summary, tags, complexity)
files = {
 "anchor.rs": ("Defines text anchors that track stable positions across edits via a sum-tree, plus the Anchors registry that keeps live anchor handles in sync with buffer mutations.",
   ["data-model","anchor-tracking","sum-tree","editor-core"], "complex"),
 "anchor_tests.rs": ("Unit tests validating anchor creation, resolution, and survival across insertions/deletions in the buffer.",
   ["test","anchor-tracking","editor-core"], "complex"),
 "buffer.rs": ("Central rich-text buffer engine: owns the sum-tree text store, selections, undo, styling, markdown export and emits BufferEvents; the primary content model the editor mutates.",
   ["data-model","editor-core","text-buffer","central-type","rich-text"], "complex"),
 "buffer_tests.rs": ("Extensive unit-test suite exercising Buffer editing, styling, selection, undo/redo, markdown round-tripping and embedded-item behavior.",
   ["test","editor-core","text-buffer"], "complex"),
 "core.rs": ("Low-level editing engine that translates CoreEditorActions into concrete buffer/text mutations (insertion, styling, block creation) and produces reversible results for undo.",
   ["editor-core","edit-engine","text-mutation","styling"], "complex"),
 "cursor.rs": ("Cursor utilities for traversing the buffer sum-tree by char offset, skipping zero-width markers, and slicing sub-trees of text fragments.",
   ["editor-core","cursor","sum-tree","traversal"], "complex"),
 "cursor_tests.rs": ("Unit tests for buffer cursor traversal, marker skipping, and offset slicing.",
   ["test","cursor","editor-core"], "moderate"),
 "diff.rs": ("Computes minimal text diffs (via imara-diff) used to auto-reload files without wiping undo history or disrupting anchors.",
   ["editor-core","diff","incremental-update"], "moderate"),
 "edit.rs": ("Layout/edit pipeline: lays out styled buffer blocks into rendered paragraphs, tables, and mermaid diagrams, computes render deltas, and detects URLs.",
   ["editor-core","layout","rendering","edit-engine"], "complex"),
 "edit_tests.rs": ("Unit tests for the layout/edit pipeline covering block layout, tables, render deltas and URL highlighting.",
   ["test","layout","editor-core"], "complex"),
 "find.rs": ("Regex-based search over a Buffer using the regex_automata DFA API directly against the non-contiguous buffer bytes.",
   ["editor-core","search","regex","find"], "complex"),
 "find_tests.rs": ("Unit tests for buffer search covering regex, case sensitivity, hidden ranges and match navigation.",
   ["test","search","editor-core"], "complex"),
 "hidden_lines_model.rs": ("Per-editor model tracking hidden line ranges independently of buffer content so multiple editors can fold the same buffer differently.",
   ["editor-core","folding","data-model","selection"], "complex"),
 "markdown.rs": ("Bidirectional markdown bridge: parses markdown into buffer content and serializes styled buffer blocks back to markdown/HTML/formatted text.",
   ["editor-core","markdown","serialization","parsing"], "complex"),
 "markdown_tests.rs": ("Unit tests for markdown parsing and serialization round-trips against buffer content.",
   ["test","markdown","serialization"], "complex"),
 "mermaid_diagram.rs": ("Helpers that turn fenced mermaid code blocks into rendered diagram assets and compute their layout size.",
   ["editor-core","mermaid","rendering","asset"], "moderate"),
 "mermaid_diagram_tests.rs": ("Unit tests for mermaid diagram asset generation and sizing.",
   ["test","mermaid","rendering"], "moderate"),
 "mod.rs": ("Module barrel for the editor content layer, declaring and re-exporting the buffer, anchor, cursor, edit, find, markdown, selection and undo submodules.",
   ["barrel","entry-point","editor-core"], "simple"),
 "outline.rs": ("Builds a structural outline of buffer blocks (headings/blocks) by walking the text sum-tree.",
   ["editor-core","outline","sum-tree","navigation"], "moderate"),
 "outline_tests.rs": ("Unit tests for block outline extraction from buffer content.",
   ["test","outline","editor-core"], "complex"),
 "segmentation.rs": ("Word and grapheme-cluster segmentation for rich-text buffers, implementing the TextBuffer API over buffer cursors.",
   ["editor-core","segmentation","text-buffer","word-boundaries"], "moderate"),
 "segmentation_tests.rs": ("Unit tests for word and grapheme segmentation over buffer content.",
   ["test","segmentation","editor-core"], "complex"),
 "selection.rs": ("Defines a single Selection (head/tail/bias) and the SelectionSet collection of resolved selections.",
   ["data-model","selection","editor-core"], "moderate"),
 "selection_model.rs": ("Anchor-backed selection model that maps selections to/from buffer offsets, merges overlaps, and tracks cursors across edits.",
   ["editor-core","selection","anchor-tracking","data-model"], "complex"),
 "text.rs": ("Core rich-text data model: BufferText sum-tree of block items with style runs, markers, summaries, and the text-style/block-style type system.",
   ["data-model","editor-core","text-buffer","sum-tree","styling"], "complex"),
 "undo.rs": ("Undo/redo stack grouping core editor actions into reversible, time-bounded atomic steps with selection restoration.",
   ["editor-core","undo-redo","history","data-model"], "complex"),
}

# file node type override: mod.rs is barrel/entry-point but still 'file'
def file_node(name):
    summ,tags,cx = files[name]
    return {"id":"file:"+fp(name),"type":"file","name":name,"filePath":fp(name),
            "summary":summ,"tags":tags,"complexity":cx}

# ---------- Sub-nodes ----------
# each: (filename, kind, name, [start,end], summary, tags, complexity, exported)
C="class"; F="function"
sub = [
 # anchor.rs
 ("anchor.rs",C,"Anchor",[17,21],"Reference-counted handle to a tracked position; while a handle lives the anchor stays synced with edits.",["anchor-tracking","data-model","handle"],"simple",True),
 ("anchor.rs",C,"Anchors",[86,89],"Registry of live anchors stored in a sum-tree; creates, updates, resolves and validates anchors against edits.",["anchor-tracking","registry","sum-tree"],"moderate",True),

 # buffer.rs
 ("buffer.rs",C,"Buffer",[541,561],"The central rich-text buffer: sum-tree text store plus selections, undo, styling and markdown export; mutated through ~150 methods and emits BufferEvents.",["central-type","text-buffer","editor-core","rich-text"],"complex",True),
 ("buffer.rs",C,"BufferEvent",[127,161],"Enum of events the buffer emits (content changed, selection changed, etc.) consumed by editor models.",["event-handler","enum","editor-core"],"moderate",True),
 ("buffer.rs",C,"BufferEditAction",[259,348],"Enum describing high-level edit actions applied to the buffer (insert, delete, style, indent, block ops).",["enum","edit-engine","data-model"],"moderate",True),
 ("buffer.rs",C,"BufferSelectAction",[164,197],"Enum of selection-mutating actions with helpers to read/replace selection offsets.",["enum","selection","data-model"],"moderate",True),
 ("buffer.rs",C,"EditOrigin",[415,425],"Enum tagging whether an edit originated from the user, undo, or programmatic source.",["enum","edit-engine","provenance"],"simple",True),
 ("buffer.rs",C,"BufferSnapshot",[514,517],"Immutable snapshot of buffer text used for diffing and read-only access.",["data-model","snapshot","text-buffer"],"simple",True),
 ("buffer.rs",C,"LineIndentation",[5366,5372],"Computes leading indentation of a line and supports unindent operations.",["indentation","data-model","editor-core"],"moderate",True),
 ("buffer.rs",C,"StyledBufferBlock",[5414,5417],"A styled block of buffer content with helpers for content length and embedded-item expansion.",["data-model","styling","block"],"moderate",True),
 ("buffer.rs",F,"convert_text_with_style_to_formatted_text",[5918,6025],"Converts a styled buffer text run into markdown_parser FormattedText for export/rendering.",["serialization","styling","conversion"],"moderate",True),
 ("buffer.rs",F,"should_autoscroll",[376,410],"Decides whether an edit should trigger autoscroll based on AutoScrollBehavior and selection movement.",["scrolling","edit-engine","heuristic"],"moderate",False),

 # core.rs
 ("core.rs",C,"CoreEditorAction",[27,38],"A single low-level editor action with anchor-bias configuration, the unit the editing engine applies.",["edit-engine","data-model","editor-core"],"moderate",True),
 ("core.rs",C,"CoreEditorActionType",[62,91],"Enum of concrete core edit operations (insert, replace, style, block mutations).",["enum","edit-engine","editor-core"],"moderate",True),
 ("core.rs",F,"edit",[494,1066],"The core editing routine that applies an action to the buffer/text tree, updating styles, blocks, anchors and producing a reversible result.",["edit-engine","text-mutation","central-logic"],"complex",False),
 ("core.rs",F,"apply_core_edit_actions",[134,364],"Applies a batch of core edit actions in sequence, threading selection deltas and accumulating reversible actions.",["edit-engine","text-mutation","batch"],"complex",True),
 ("core.rs",F,"reverse_core_edit_action",[454,492],"Builds the inverse of a core edit action for undo support.",["undo-redo","edit-engine"],"moderate",True),
 ("core.rs",F,"style_text",[1144,1219],"Applies text-style changes across a range, splitting and merging style runs in the buffer tree.",["styling","text-mutation","editor-core"],"moderate",False),

 # cursor.rs
 ("cursor.rs",C,"BufferCursor",[19,22],"Cursor over the buffer sum-tree giving char/byte/point navigation while skipping zero-width markers.",["cursor","traversal","sum-tree"],"moderate",True),
 ("cursor.rs",C,"BufferSumTree",[273,297],"Extension wrapper over the buffer's SumTree of text fragments with item replacement and range queries.",["sum-tree","data-model","editor-core"],"moderate",True),

 # diff.rs
 ("diff.rs",C,"TextDiff",[18,21],"A computed diff between two strings expressed as byte ranges and replacements applicable to the buffer.",["diff","data-model","incremental-update"],"simple",True),
 ("diff.rs",F,"diff_internal",[63,113],"Runs imara-diff over interned tokens to produce minimal char-offset edits between old and new text.",["diff","algorithm","editor-core"],"moderate",False),

 # edit.rs
 ("edit.rs",C,"LayoutTask",[651,685],"A unit of layout work that lays out one styled block (text/table/mermaid) into rendered output.",["layout","rendering","task"],"moderate",True),
 ("edit.rs",C,"LayOutArgs",[220,241],"Accumulator threading layout state (offsets, runs, newlines) while laying out a block.",["layout","rendering","state"],"moderate",False),
 ("edit.rs",C,"EditDelta",[172,181],"Delta describing how an edit changes layout, used to incrementally update rendered content.",["layout","incremental-update","data-model"],"moderate",True),
 ("edit.rs",C,"ParsedUrl",[198,204],"A URL detected in buffer text with its range and hyperlink, produced during URL highlighting.",["url-detection","data-model"],"simple",True),
 ("edit.rs",F,"layout_text_block",[959,1151],"Lays out a styled text block into rendered paragraphs, resolving styles, fonts and inline layout.",["layout","rendering","text"],"complex",False),
 ("edit.rs",F,"layout_table_block",[1187,1329],"Lays out a table block, measuring cells and producing rendered table geometry.",["layout","rendering","table"],"complex",False),
 ("edit.rs",F,"highlight_urls",[1419,1485],"Scans buffer text with urlocator to detect URLs and emit hyperlink style spans.",["url-detection","styling","scanning"],"moderate",False),

 # find.rs
 ("find.rs",C,"Engine",[129,140],"Search engine that compiles a Query into a regex DFA and finds matches across the buffer bytes.",["search","regex","engine"],"moderate",True),
 ("find.rs",C,"SearchConfig",[69,75],"Configuration for a search: case sensitivity, regex mode, and hidden-range skipping.",["search","config","data-model"],"simple",True),
 ("find.rs",C,"SearchDirection",[374,377],"Enum controlling forward/backward DFA traversal and its start-state/advance logic.",["search","enum","dfa"],"moderate",True),
 ("find.rs",C,"Match",[38,43],"A single search match expressed as a buffer range.",["search","data-model"],"simple",True),

 # hidden_lines_model.rs
 ("hidden_lines_model.rs",C,"HiddenLinesModel",[20,25],"Per-editor model storing hidden (folded) line ranges keyed by buffer version with intersection and materialization queries.",["folding","data-model","editor-core","central-type"],"complex",True),

 # markdown.rs
 ("markdown.rs",C,"BufferMarkdownParser",[50,53],"Parses markdown source into styled buffer content blocks.",["markdown","parsing","editor-core"],"moderate",True),
 ("markdown.rs",C,"BufferToFormattedText",[407,409],"Converts buffer content into markdown_parser FormattedText and computes edits to apply formatted text back.",["markdown","serialization","conversion"],"moderate",True),
 ("markdown.rs",C,"MarkdownStyle",[36,46],"Enum/options describing markdown serialization style (GFM tables, HTML, etc.).",["markdown","enum","config"],"simple",True),
 ("markdown.rs",F,"serialize",[735,1037],"Serializes styled buffer blocks to markdown, handling headers, lists, tables, code blocks and inline styles.",["markdown","serialization","central-logic"],"complex",False),
 ("markdown.rs",F,"to_markdown",[61,159],"Renders parsed/styled content into a markdown string, walking blocks and inline fragments.",["markdown","serialization"],"moderate",False),
 ("markdown.rs",F,"append_formatting",[218,331],"Appends inline formatting spans (bold, code, links) while building markdown output.",["markdown","serialization","styling"],"moderate",False),

 # mermaid_diagram.rs
 ("mermaid_diagram.rs",C,"MermaidDiagramAsset",[18,18],"Asset descriptor for a rendered mermaid diagram derived from a fenced code block.",["mermaid","asset","data-model"],"simple",True),
 ("mermaid_diagram.rs",F,"mermaid_asset_source",[22,40],"Builds the asset source string/config used to render a mermaid diagram block.",["mermaid","rendering","asset"],"moderate",True),

 # outline.rs
 ("outline.rs",C,"BlockOutline",[14,21],"A single outline entry describing a buffer block (type, range) for navigation.",["outline","data-model","navigation"],"simple",True),
 ("outline.rs",C,"BlockOutlines",[24,27],"Collection of block outlines built by walking the text sum-tree.",["outline","data-model","collection"],"simple",True),

 # segmentation.rs
 ("segmentation.rs",C,"Chars",[66,72],"Grapheme/word iterator over buffer text implementing the segmentation TextBuffer API.",["segmentation","iterator","text-buffer"],"moderate",True),

 # selection.rs
 ("selection.rs",C,"Selection",[7,13],"A single selection with head, tail and text-style bias.",["selection","data-model","editor-core"],"simple",True),
 ("selection.rs",C,"SelectionSet",[73,75],"Ordered collection of selections with push/truncate/iteration and an offset map.",["selection","collection","data-model"],"moderate",True),

 # selection_model.rs
 ("selection_model.rs",C,"BufferSelectionModel",[23,27],"Anchor-backed selection model mapping selections to/from offsets, merging overlaps and tracking cursors across edits.",["selection","anchor-tracking","central-type","editor-core"],"complex",True),
 ("selection_model.rs",C,"SelectionSnapshot",[15,21],"Snapshot of resolved selection state reported on SelectionChanged events.",["selection","snapshot","data-model"],"simple",True),

 # text.rs
 ("text.rs",C,"BufferText",[541,571],"Sum-tree of buffer block items holding text fragments, markers and style runs; the core text storage.",["central-type","text-buffer","sum-tree","data-model"],"complex",True),
 ("text.rs",C,"BufferBlockItem",[398,410],"Enum of buffer block items (paragraph, list, table, code, embed) with markdown/plain-text rendering helpers.",["enum","data-model","block","rendering"],"moderate",True),
 ("text.rs",C,"BlockType",[367,370],"Enum classifying the type of a buffer block.",["enum","data-model","block"],"simple",True),
 ("text.rs",C,"BufferTextStyle",[1045,1051],"Bitflag-style text style descriptor (bold, weight, etc.) for a text run.",["styling","data-model"],"simple",True),
 ("text.rs",C,"TextStyles",[1319,1330],"Set of applied inline text styles with toggle/query helpers and collision resolution.",["styling","data-model","editor-core"],"moderate",True),
 ("text.rs",C,"TextStylesWithMetadata",[1084,1093],"Text styles plus metadata (color, link content) with rich mutation and query API.",["styling","data-model","metadata"],"moderate",True),
 ("text.rs",C,"BufferBlockStyle",[867,893],"Style attributes for a whole block (table, list, line-break and formatting behavior).",["styling","block","data-model"],"moderate",True),
 ("text.rs",C,"CodeBlockType",[693,700],"Enum of code-block kinds with markdown representation mapping.",["enum","code-block","markdown"],"simple",True),
 ("text.rs",C,"IndentUnit",[994,997],"Indentation unit (width, char unit, tab-stop text) used for list/block indentation.",["indentation","data-model"],"simple",True),
 ("text.rs",C,"BufferSummary",[1664,1668],"Sum-tree summary aggregating line/block/link counts and style summaries for the buffer text.",["sum-tree","summary","data-model"],"moderate",True),

 # undo.rs
 ("undo.rs",C,"UndoStack",[176,184],"Time-bounded undo/redo stack grouping reversible editor actions into atomic steps with version tracking.",["undo-redo","history","central-type","editor-core"],"complex",True),
 ("undo.rs",C,"UndoStackItem",[53,59],"One atomic undo entry bundling reversible actions and the selection to restore.",["undo-redo","data-model","history"],"moderate",False),
 ("undo.rs",C,"ReversibleEditorActions",[21,25],"A group of reversible editor actions plus the selection state to restore on undo.",["undo-redo","data-model"],"simple",True),
 ("undo.rs",C,"UndoActionType",[28,34],"Enum classifying undo action types (atomic vs non-atomic addition/deletion).",["undo-redo","enum","data-model"],"simple",True),
]

def sub_id(fn,kind,name): return ("class:" if kind==C else "function:")+fp(fn)+":"+name
def sub_node(fn,kind,name,rng,summ,tags,cx,exp):
    return {"id":sub_id(fn,kind,name),"type":("class" if kind==C else "function"),
            "name":name,"filePath":fp(fn),"lineRange":rng,"summary":summ,"tags":tags,"complexity":cx}

# ---------- Build nodes ----------
nodes = []
for name in files: nodes.append(file_node(name))
for s in sub: nodes.append(sub_node(*s))

# ---------- Build edges ----------
edges = []
# imports
for src, tgts in imp.items():
    for t in tgts:
        edges.append({"source":"file:"+src,"target":"file:"+t,"type":"imports","direction":"forward","weight":0.7})
# contains + exports
for fn,kind,name,rng,summ,tags,cx,exp in sub:
    sid=sub_id(fn,kind,name)
    edges.append({"source":"file:"+fp(fn),"target":sid,"type":"contains","direction":"forward","weight":1.0})
    if exp:
        edges.append({"source":"file:"+fp(fn),"target":sid,"type":"exports","direction":"forward","weight":0.8})
# tested_by (production -> test)
pairs = [("anchor.rs","anchor_tests.rs"),("buffer.rs","buffer_tests.rs"),("cursor.rs","cursor_tests.rs"),
         ("edit.rs","edit_tests.rs"),("find.rs","find_tests.rs"),("markdown.rs","markdown_tests.rs"),
         ("mermaid_diagram.rs","mermaid_diagram_tests.rs"),("outline.rs","outline_tests.rs"),
         ("segmentation.rs","segmentation_tests.rs")]
for prod,test in pairs:
    edges.append({"source":"file:"+fp(prod),"target":"file:"+fp(test),"type":"tested_by","direction":"forward","weight":0.5})

# sanity: import edge count == sum of import lists
expected_imports = sum(len(v) for v in imp.values())
actual_imports = sum(1 for e in edges if e['type']=='imports')
assert expected_imports==actual_imports, (expected_imports, actual_imports)

# ---------- Partition by file alphabetically ----------
all_files = sorted(files.keys())  # filenames
# map filePath(full) -> filename for node grouping
def node_filename(n):
    fpv = n.get('filePath')
    return fpv.replace(BASE,"") if fpv else None

N=len(all_files)
nodeCount=len(nodes); edgeCount=len(edges)
parts = math.ceil(max(nodeCount/60, edgeCount/120))
parts = max(parts,1)
# force at least enough parts; use 3 for safety if computed <3 given edge concentration
chunk = math.ceil(N/parts)
groups = [set(all_files[i:i+chunk]) for i in range(0,N,chunk)]
parts = len(groups)

outdir='/home/mhb/warp/.understand-anything/intermediate'
print("totals: nodes=%d edges=%d expectedImports=%d parts=%d"%(nodeCount,edgeCount,expected_imports,parts))

# node id -> filename
nid_file = {n['id']: node_filename(n) for n in nodes}

written=[]
for k,g in enumerate(groups,1):
    part_nodes=[n for n in nodes if node_filename(n) in g]
    part_node_ids=set(n['id'] for n in part_nodes)
    # edges whose source node is in this part (source file in group)
    part_edges=[]
    for e in edges:
        src=e['source']
        # source is always a file: or class:/function: belonging to a file in this batch
        if src.startswith('file:'):
            sf = src[len('file:'):].replace(BASE,"")
            # only our batch files have group membership; sf may be full path for non-batch? sources are always batch files
            if sf in g: part_edges.append(e)
        else:
            if src in part_node_ids: part_edges.append(e)
    frag={"nodes":part_nodes,"edges":part_edges}
    if parts==1:
        path=os.path.join(outdir,"batch-6.json")
    else:
        path=os.path.join(outdir,"batch-6-part-%d.json"%k)
    json.dump(frag,open(path,'w'),indent=1)
    written.append((path,len(part_nodes),len(part_edges)))
    print("wrote",path,"nodes=",len(part_nodes),"edges=",len(part_edges))

print("TOTAL written nodes:",sum(w[1] for w in written),"edges:",sum(w[2] for w in written))
