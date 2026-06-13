import json

nodes = []
edges = []

def n(id, type, name, filePath, summary, tags, complexity, lineRange=None, languageNotes=None):
    o = {"id": id, "type": type, "name": name}
    if filePath is not None:
        o["filePath"] = filePath
    o["summary"] = summary
    o["tags"] = tags
    o["complexity"] = complexity
    if lineRange is not None:
        o["lineRange"] = lineRange
    if languageNotes is not None:
        o["languageNotes"] = languageNotes
    nodes.append(o)

def e(source, target, type, weight):
    edges.append({"source": source, "target": target, "type": type, "direction": "forward", "weight": weight})

# ---------------- FILE / CONFIG / DOC NODES ----------------
n("file:crates/editor/benches/buffer_bench.rs", "file", "buffer_bench.rs", "crates/editor/benches/buffer_bench.rs",
  "Criterion benchmark suite for the editor Buffer measuring buffer creation, full-text read, incremental edits, and styling over progressively larger inputs.",
  ["benchmark", "test", "editor", "performance", "buffer"], "moderate")

n("config:crates/editor/Cargo.toml", "config", "Cargo.toml", "crates/editor/Cargo.toml",
  "Cargo manifest for the warp_editor crate declaring text-editing dependencies (markdown/HTML parsing, sum_tree, regex) and the buffer_bench Criterion benchmark.",
  ["configuration", "cargo", "rust", "build-system", "dependencies"], "simple")

n("file:crates/editor/src/content/text_tests.rs", "file", "text_tests.rs", "crates/editor/src/content/text_tests.rs",
  "Unit tests for editor content text styling and formatted-table/image markdown handling, covering TextStyle XOR composition, table round-tripping, and image markdown title preservation.",
  ["test", "editor", "text", "markdown", "styling"], "moderate")

n("file:crates/editor/src/multiline_tests.rs", "file", "multiline_tests.rs", "crates/editor/src/multiline_tests.rs",
  "Unit tests for line-ending inference and normalization (LF/CR/CRLF) across MultilineStr construction and apply operations.",
  ["test", "editor", "line-endings", "multiline", "text"], "moderate")

n("file:crates/editor/src/render/model/table_offset_map_tests.rs", "file", "table_offset_map_tests.rs", "crates/editor/src/render/model/table_offset_map_tests.rs",
  "Unit tests for the markdown table cell offset map, validating cell lookup by offset, range queries, separator detection, and style-span handling (bold, links, escapes, nested styles).",
  ["test", "editor", "table", "offset-map", "markdown"], "complex")

n("file:crates/editor/test_data/test_rust_file.rs", "file", "test_rust_file.rs", "crates/editor/test_data/test_rust_file.rs",
  "Large vendored copy of the Rust standard library's std::io and String source used as an 8.7k-line fixture for exercising the editor's parsing, rendering, and benchmark workloads.",
  ["test-fixture", "test-data", "rust", "large-file", "editor"], "complex",
  languageNotes="Not project code: a verbatim std-library snapshot embedded as editor test data and excluded from the crate via the Cargo `exclude` key. Its hundreds of internal std symbols are intentionally not modeled as project nodes.")

n("document:crates/editor/test_fixtures/images/image_test.md", "document", "image_test.md", "crates/editor/test_fixtures/images/image_test.md",
  "Markdown fixture exercising image rendering paths (JPEG/PNG, relative and parent-directory paths, alt/title text) for the editor's markdown image support.",
  ["test-fixture", "markdown", "image", "editor"], "simple")

n("document:crates/editor/test_fixtures/images/README.md", "document", "README.md", "crates/editor/test_fixtures/images/README.md",
  "Describes the image test fixtures directory, cataloguing sample images and the rendering aspects (formats, dimensions, transparency, relative paths) they validate.",
  ["documentation", "test-fixture", "image", "editor"], "simple")

n("config:crates/vim/Cargo.toml", "config", "Cargo.toml", "crates/vim/Cargo.toml",
  "Cargo manifest for the vim crate declaring its dependence on warp_core and warpui_core plus text utilities used for modal editing.",
  ["configuration", "cargo", "rust", "dependencies", "vim"], "simple")

n("file:crates/vim/src/matching_brackets_tests.rs", "file", "matching_brackets_tests.rs", "crates/vim/src/matching_brackets_tests.rs",
  "Unit tests for vim matching-bracket navigation, asserting the matched-bracket position for each bracket pair across a sample buffer.",
  ["test", "vim", "brackets", "navigation", "text-objects"], "moderate")

n("file:crates/vim/src/paragraph_iterator_tests.rs", "file", "paragraph_iterator_tests.rs", "crates/vim/src/paragraph_iterator_tests.rs",
  "Unit tests for the vim paragraph iterator, covering previous/next paragraph traversal across single, multiple, and blank-line-separated paragraphs.",
  ["test", "vim", "paragraph", "iterator", "navigation"], "moderate")

n("file:crates/vim/src/text_objects/block_tests.rs", "file", "block_tests.rs", "crates/vim/src/text_objects/block_tests.rs",
  "Unit tests for vim block text objects (a-block and inner-block), validating bracket-delimited selection ranges including nested cases.",
  ["test", "vim", "text-objects", "block", "selection"], "moderate")

n("file:crates/vim/src/text_objects/paragraph_tests.rs", "file", "paragraph_tests.rs", "crates/vim/src/text_objects/paragraph_tests.rs",
  "Unit tests for vim paragraph text objects (inner-paragraph and a-paragraph) across empty buffers, multiple paragraphs, and blank-line handling.",
  ["test", "vim", "text-objects", "paragraph", "selection"], "moderate")

n("file:crates/vim/src/text_objects/word_tests.rs", "file", "word_tests.rs", "crates/vim/src/text_objects/word_tests.rs",
  "Unit tests for vim word text objects covering inner/a word and inner/a bigword selection across punctuation, whitespace, and symbol boundaries.",
  ["test", "vim", "text-objects", "word", "selection"], "complex")

n("file:crates/vim/src/word_iterator_tests.rs", "file", "word_iterator_tests.rs", "crates/vim/src/word_iterator_tests.rs",
  "Unit tests for the vim word iterator, exhaustively covering forward/backward traversal of word heads and tails with and without symbol boundaries, plus out-of-bounds error handling.",
  ["test", "vim", "word", "iterator", "navigation"], "complex")

n("file:crates/warpui_core/build.rs", "file", "build.rs", "crates/warpui_core/build.rs",
  "Cargo build script for warpui_core defining cfg aliases (macos, native) used for platform-conditional compilation.",
  ["build-system", "build-script", "configuration", "cfg-aliases", "rust"], "simple")

n("config:crates/warpui_core/Cargo.toml", "config", "Cargo.toml", "crates/warpui_core/Cargo.toml",
  "Cargo manifest for the warpui_core crate (the bespoke WarpUI framework), declaring rendering, font, and platform dependencies plus the cfg_aliases build dependency.",
  ["configuration", "cargo", "rust", "dependencies", "build-system"], "moderate")

n("document:crates/warpui_core/README.md", "document", "README.md", "crates/warpui_core/README.md",
  "Whirlwind-tour overview of the WarpUI framework explaining the global App object, entities and handles, app contexts, elements, actions, and views.",
  ["documentation", "overview", "warpui", "architecture", "framework"], "moderate")

n("file:crates/warpui_core/src/core/model/context_tests.rs", "file", "context_tests.rs", "crates/warpui_core/src/core/model/context_tests.rs",
  "Unit tests for the WarpUI model context/spawner, verifying model spawning and behavior when a spawned model is dropped.",
  ["test", "warpui", "model", "context", "spawner"], "moderate")

n("document:crates/warpui_core/src/elements/flex/WARP.md", "document", "WARP.md", "crates/warpui_core/src/elements/flex/WARP.md",
  "Debugging guide for WarpUI Flex layout panics, mapping common infinite-constraint error messages to fixes and explaining flexible vs non-flexible children.",
  ["documentation", "debugging", "warpui", "flex", "layout"], "moderate")

n("file:crates/warpui_core/src/elements/image_tests.rs", "file", "image_tests.rs", "crates/warpui_core/src/elements/image_tests.rs",
  "Unit tests for the WarpUI image element, covering NaN-origin handling, failure/fallback element selection, and loading-timeout behavior across rebuilds, using a TestElement stub.",
  ["test", "warpui", "image", "element", "loading"], "moderate")

n("file:crates/warpui_core/src/elements/new_scrollable/util_tests.rs", "file", "util_tests.rs", "crates/warpui_core/src/elements/new_scrollable/util_tests.rs",
  "Unit tests for new_scrollable scroll-delta utilities, verifying the scroll offsets needed to bring elements fully or partially into view along an axis.",
  ["test", "warpui", "scrolling", "scrollable", "layout"], "moderate")

n("file:crates/warpui_core/src/elements/stack/offset_positioning_tests.rs", "file", "offset_positioning_tests.rs", "crates/warpui_core/src/elements/stack/offset_positioning_tests.rs",
  "Extensive unit tests for stack offset element positioning, validating absolute placement of anchored child elements when bound to parent, window, or unbounded, including overflow handling.",
  ["test", "warpui", "positioning", "anchor", "layout"], "complex")

n("file:crates/warpui_core/src/elements/table/mod_tests.rs", "file", "mod_tests.rs", "crates/warpui_core/src/elements/table/mod_tests.rs",
  "Unit tests for the WarpUI table element covering column-width computation (fixed/flex/fraction/intrinsic), sumtree row-height tracking, scroll offsets, and viewport height estimation.",
  ["test", "warpui", "table", "layout", "sumtree"], "complex")

n("file:crates/warpui_core/src/fonts_tests.rs", "file", "fonts_tests.rs", "crates/warpui_core/src/fonts_tests.rs",
  "Unit test for subpixel glyph alignment computation in the WarpUI font subsystem.",
  ["test", "warpui", "fonts", "subpixel", "rendering"], "simple")

# ---------------- FUNCTION / CLASS NODES ----------------
BB = "crates/editor/benches/buffer_bench.rs"
n(f"function:{BB}:mock_buffer", "function", "mock_buffer", BB,
  "Constructs a test Buffer populated with the given text inside a WarpUI app context for benchmarking.",
  ["benchmark", "helper", "buffer", "setup"], "simple", [16, 33])
n(f"function:{BB}:edit_text", "function", "edit_text", BB,
  "Benchmark workload that applies incremental edits to a buffer to measure edit throughput.",
  ["benchmark", "buffer", "editing", "performance"], "simple", [48, 65])
n(f"function:{BB}:style_text", "function", "style_text", BB,
  "Benchmark workload that applies styling spans across a buffer to measure styling cost.",
  ["benchmark", "buffer", "styling", "performance"], "simple", [67, 86])
n(f"function:{BB}:criterion_benchmark", "function", "criterion_benchmark", BB,
  "Criterion benchmark group registering buffer creation, read, edit, and style benchmarks over varying input sizes.",
  ["benchmark", "criterion", "entry-point", "performance"], "simple", [88, 96])

TT = "crates/editor/src/content/text_tests.rs"
n(f"function:{TT}:test_text_style_xor", "function", "test_text_style_xor", TT,
  "Verifies XOR composition of TextStyle flags, asserting correct toggling of styling attributes across combinations.",
  ["test", "text", "styling", "xor"], "moderate", [11, 72])

TOM = "crates/editor/src/render/model/table_offset_map_tests.rs"
n(f"function:{TOM}:test_simple_table", "function", "test_simple_table", TOM,
  "Builds a basic markdown table and asserts the cell offset map yields correct cell boundaries and contents.",
  ["test", "table", "offset-map", "markdown"], "moderate", [7, 41])
n(f"function:{TOM}:test_table_cell_offset_map_handles_bold_and_links", "function", "test_table_cell_offset_map_handles_bold_and_links", TOM,
  "Validates that the table cell offset map correctly maps character offsets through bold and link style spans.",
  ["test", "table", "offset-map", "styling"], "moderate", [148, 207])

MB = "crates/vim/src/matching_brackets_tests.rs"
n(f"function:{MB}:test_vim_find_matching_bracket", "function", "test_vim_find_matching_bracket", MB,
  "Drives the vim matching-bracket finder across all bracket pairs in a sample buffer, asserting each match position.",
  ["test", "vim", "brackets", "navigation"], "moderate", [10, 63])

BL = "crates/vim/src/text_objects/block_tests.rs"
n(f"function:{BL}:test_vim_a_block", "function", "test_vim_a_block", BL,
  "Asserts the a-block text object selects the full bracket-delimited range including the delimiters.",
  ["test", "vim", "block", "text-objects"], "moderate", [29, 73])
n(f"function:{BL}:test_vim_inner_block", "function", "test_vim_inner_block", BL,
  "Asserts the inner-block text object selects the bracket-delimited range excluding delimiters across nested cases.",
  ["test", "vim", "block", "text-objects"], "moderate", [76, 148])

PT = "crates/vim/src/text_objects/paragraph_tests.rs"
n(f"function:{PT}:vim_inner_paragraph_three_paragraphs", "function", "vim_inner_paragraph_three_paragraphs", PT,
  "Verifies inner-paragraph selection boundaries with three paragraphs separated by blank lines.",
  ["test", "vim", "paragraph", "text-objects"], "moderate", [61, 95])
n(f"function:{PT}:vim_a_paragraph_three_paragraphs", "function", "vim_a_paragraph_three_paragraphs", PT,
  "Verifies a-paragraph selection including trailing blank lines across three paragraphs.",
  ["test", "vim", "paragraph", "text-objects"], "moderate", [122, 157])

WT = "crates/vim/src/text_objects/word_tests.rs"
n(f"function:{WT}:test_vim_inner_word", "function", "test_vim_inner_word", WT,
  "Exhaustively asserts inner-word selection boundaries across letters, punctuation, and whitespace.",
  ["test", "vim", "word", "text-objects"], "moderate", [4, 90])
n(f"function:{WT}:test_vim_a_word", "function", "test_vim_a_word", WT,
  "Exhaustively asserts a-word selection (word plus surrounding whitespace) across many cursor positions.",
  ["test", "vim", "word", "text-objects"], "complex", [93, 252])
n(f"function:{WT}:test_vim_inner_bigword", "function", "test_vim_inner_bigword", WT,
  "Asserts inner-bigword selection treating punctuation as part of the word across boundaries.",
  ["test", "vim", "bigword", "text-objects"], "moderate", [255, 339])
n(f"function:{WT}:test_vim_a_bigword", "function", "test_vim_a_bigword", WT,
  "Asserts a-bigword selection including surrounding whitespace across boundaries.",
  ["test", "vim", "bigword", "text-objects"], "moderate", [342, 451])

WI = "crates/vim/src/word_iterator_tests.rs"
n(f"function:{WI}:test_word_forward_heads", "function", "test_word_forward_heads", WI,
  "Verifies forward iteration over word head positions across a sample buffer.",
  ["test", "vim", "word", "iterator"], "moderate", [9, 78])
n(f"function:{WI}:test_word_backward_heads", "function", "test_word_backward_heads", WI,
  "Verifies backward iteration over word head positions across a sample buffer.",
  ["test", "vim", "word", "iterator"], "moderate", [148, 217])
n(f"function:{WI}:test_word_forward_tails", "function", "test_word_forward_tails", WI,
  "Verifies forward iteration over word tail (end) positions across a sample buffer.",
  ["test", "vim", "word", "iterator"], "moderate", [287, 356])
n(f"function:{WI}:test_word_backward_tails", "function", "test_word_backward_tails", WI,
  "Verifies backward iteration over word tail positions across a sample buffer.",
  ["test", "vim", "word", "iterator"], "moderate", [426, 495])

BR = "crates/warpui_core/build.rs"
n(f"function:{BR}:main", "function", "main", BR,
  "Build-script entry that registers cfg aliases (macos, native) for platform-conditional compilation.",
  ["build-script", "entry-point", "cfg-aliases"], "simple", [8, 13])

CT = "crates/warpui_core/src/core/model/context_tests.rs"
n(f"function:{CT}:test_model_spawner", "function", "test_model_spawner", CT,
  "Verifies that the model spawner creates and tracks a model accessible via its handle within the app context.",
  ["test", "warpui", "model", "spawner"], "moderate", [5, 50])

IT = "crates/warpui_core/src/elements/image_tests.rs"
n(f"class:{IT}:TestElement", "class", "TestElement", IT,
  "Stub Element implementation used by the image tests, providing trivial layout/paint/size/origin/event hooks for driving image-element behavior.",
  ["test", "warpui", "element", "stub", "mock"], "simple", [3, 3])

UT = "crates/warpui_core/src/elements/new_scrollable/util_tests.rs"
n(f"function:{UT}:test_scroll_delta_for_axis_fully_into_view", "function", "test_scroll_delta_for_axis_fully_into_view", UT,
  "Asserts the scroll delta required to bring a target element fully into the viewport along an axis.",
  ["test", "warpui", "scrolling", "layout"], "moderate", [4, 51])
n(f"function:{UT}:test_scroll_delta_for_axis_top_into_view", "function", "test_scroll_delta_for_axis_top_into_view", UT,
  "Asserts scroll-delta computation for aligning an element's top edge into view across many cases.",
  ["test", "warpui", "scrolling", "layout"], "complex", [54, 154])

OP = "crates/warpui_core/src/elements/stack/offset_positioning_tests.rs"
n(f"function:{OP}:parent_anchor_point", "function", "parent_anchor_point", OP,
  "Test helper computing a parent rectangle's anchor point for a given anchor enum value.",
  ["test", "helper", "positioning", "anchor"], "moderate", [56, 81])
n(f"function:{OP}:positioned_element_anchor_point", "function", "positioned_element_anchor_point", OP,
  "Test helper computing a positioned element's anchor point for a given anchor enum value.",
  ["test", "helper", "positioning", "anchor"], "moderate", [85, 110])
n(f"function:{OP}:get_absolute_x_y_position_for_child_element", "function", "get_absolute_x_y_position_for_child_element", OP,
  "Test helper computing the absolute x/y placement of a child element from parent rect and the positioned/child anchor pair.",
  ["test", "helper", "positioning", "layout"], "moderate", [114, 145])
n(f"function:{OP}:test_offset_from_parent_unbounded", "function", "test_offset_from_parent_unbounded", OP,
  "Verifies child element offset relative to the parent when no boundary constraints are applied.",
  ["test", "warpui", "positioning", "layout"], "moderate", [148, 215])
n(f"function:{OP}:test_offset_from_positioned_element_unbounded", "function", "test_offset_from_positioned_element_unbounded", OP,
  "Verifies child element offset relative to a positioned element when no boundary constraints are applied.",
  ["test", "warpui", "positioning", "layout"], "moderate", [546, 618])

MT = "crates/warpui_core/src/elements/table/mod_tests.rs"
n(f"function:{MT}:test_compute_column_widths_mixed", "function", "test_compute_column_widths_mixed", MT,
  "Verifies column width computation for a table mixing fixed, flex, and fractional column sizing.",
  ["test", "warpui", "table", "layout"], "simple", [82, 94])
n(f"function:{MT}:test_sumtree_row_height_invalidation", "function", "test_sumtree_row_height_invalidation", MT,
  "Verifies sumtree-backed row heights are invalidated and recomputed when a row's measured height changes.",
  ["test", "warpui", "table", "sumtree"], "moderate", [221, 245])
n(f"function:{MT}:test_max_scroll_offset_respects_viewport", "function", "test_max_scroll_offset_respects_viewport", MT,
  "Verifies the table's maximum scroll offset is clamped to account for the viewport height.",
  ["test", "warpui", "table", "scrolling"], "moderate", [325, 344])

FT = "crates/warpui_core/src/fonts_tests.rs"
n(f"function:{FT}:test_subpixel_alignment_computation", "function", "test_subpixel_alignment_computation", FT,
  "Verifies subpixel glyph alignment offset computation used for font rendering.",
  ["test", "warpui", "fonts", "subpixel"], "moderate", [4, 42])

# ---------------- CONTAINS EDGES (one per function/class node) ----------------
func_class_ids = [nd["id"] for nd in nodes if nd["type"] in ("function", "class")]
for fid in func_class_ids:
    # file node id is the function id with prefix replaced and trailing :name removed
    fp = next(nd["filePath"] for nd in nodes if nd["id"] == fid)
    e(f"file:{fp}", fid, "contains", 1.0)

# ---------------- TESTED_BY EDGES (production -> test) ----------------
tested_by_pairs = [
    ("crates/editor/src/content/text.rs", "crates/editor/src/content/text_tests.rs"),
    ("crates/editor/src/multiline.rs", "crates/editor/src/multiline_tests.rs"),
    ("crates/editor/src/render/model/table_offset_map.rs", "crates/editor/src/render/model/table_offset_map_tests.rs"),
    ("crates/vim/src/matching_brackets.rs", "crates/vim/src/matching_brackets_tests.rs"),
    ("crates/vim/src/paragraph_iterator.rs", "crates/vim/src/paragraph_iterator_tests.rs"),
    ("crates/vim/src/text_objects/block.rs", "crates/vim/src/text_objects/block_tests.rs"),
    ("crates/vim/src/text_objects/paragraph.rs", "crates/vim/src/text_objects/paragraph_tests.rs"),
    ("crates/vim/src/text_objects/word.rs", "crates/vim/src/text_objects/word_tests.rs"),
    ("crates/vim/src/word_iterator.rs", "crates/vim/src/word_iterator_tests.rs"),
    ("crates/warpui_core/src/core/model/context.rs", "crates/warpui_core/src/core/model/context_tests.rs"),
    ("crates/warpui_core/src/elements/image.rs", "crates/warpui_core/src/elements/image_tests.rs"),
    ("crates/warpui_core/src/elements/new_scrollable/util.rs", "crates/warpui_core/src/elements/new_scrollable/util_tests.rs"),
    ("crates/warpui_core/src/elements/stack/offset_positioning.rs", "crates/warpui_core/src/elements/stack/offset_positioning_tests.rs"),
    ("crates/warpui_core/src/elements/table/mod.rs", "crates/warpui_core/src/elements/table/mod_tests.rs"),
    ("crates/warpui_core/src/fonts.rs", "crates/warpui_core/src/fonts_tests.rs"),
]
for prod, test in tested_by_pairs:
    e(f"file:{prod}", f"file:{test}", "tested_by", 0.5)

# ---------------- DOCUMENTS EDGES ----------------
e("document:crates/warpui_core/README.md", "file:crates/warpui_core/src/core/model/context.rs", "documents", 0.5)
e("document:crates/warpui_core/src/elements/flex/WARP.md", "file:crates/warpui_core/src/elements/flex/mod.rs", "documents", 0.5)
e("document:crates/editor/test_fixtures/images/README.md", "document:crates/editor/test_fixtures/images/image_test.md", "documents", 0.5)

# ---------------- RELATED EDGE ----------------
e("document:crates/editor/test_fixtures/images/image_test.md", "file:crates/editor/src/content/text_tests.rs", "related", 0.5)

# ---------------- CONFIGURES EDGES ----------------
e("config:crates/editor/Cargo.toml", "file:crates/editor/benches/buffer_bench.rs", "configures", 0.6)
e("config:crates/warpui_core/Cargo.toml", "file:crates/warpui_core/build.rs", "configures", 0.6)
e("config:crates/vim/Cargo.toml", "file:crates/vim/src/word_iterator.rs", "configures", 0.6)

out = {"nodes": nodes, "edges": edges}
# validation: unique ids, no self edges
ids = [nd["id"] for nd in nodes]
assert len(ids) == len(set(ids)), "duplicate node ids"
for ed in edges:
    assert ed["source"] != ed["target"], f"self edge {ed}"
print("nodes", len(nodes), "edges", len(edges))
from collections import Counter
print("edge types", Counter(ed["type"] for ed in edges))
with open("/home/mhb/warp/.understand-anything/intermediate/batch-13.json", "w") as f:
    json.dump(out, f, indent=2)
print("written")
