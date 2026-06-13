const fs=require("fs");
const r=JSON.parse(fs.readFileSync("/home/mhb/warp/.understand-anything/tmp/ua-arch-results.json","utf8"));
const inp=JSON.parse(fs.readFileSync("/home/mhb/warp/.understand-anything/tmp/ua-arch-input.json","utf8"));
const dg=r.directoryGroups;
const byId=new Map(inp.fileNodes.map(n=>[n.id,n]));
const base="file:crates/warpui_core/src/";
const ebase="file:crates/editor/src/";

// helper: build id from a warpui_core src-root filename
const wc=n=>"file:crates/warpui_core/src/"+n;
const ed=n=>"file:crates/editor/src/"+n;

// per-file overrides for the mixed src-root groups
const fr_srcroot=["presenter.rs","presenter_tests.rs","lib.rs","prelude.rs","util.rs","util_tests.rs","units.rs","time.rs"].map(wc);
const keymap_srcroot=["keymap.rs","keymap_tests.rs","event.rs","actions.rs"].map(wc);
const text_srcroot=["fonts.rs","fonts_tests.rs","text_layout.rs","text_layout_tests.rs","text_selection_utils.rs"].map(wc);
const render_srcroot=["scene.rs","scene_tests.rs","image_cache.rs","image_cache_tests.rs","clipboard.rs","clipboard_utils.rs","clipboard_utils_tests.rs","modals.rs","notification.rs","accessibility.rs","zoom.rs"].map(wc);
const support_srcroot=["app_focus_telemetry.rs","app_focus_telemetry_tests.rs","traces.rs","test.rs"].map(wc);

const g=k=>dg[k]||[];

const layers=[
  {id:"layer:framework-runtime",name:"Framework Runtime",
   description:"The bespoke GPUI-like reactive UI runtime of warpui_core — App/AppContext, model/view/autotracking, the presenter layout-and-event-dispatch loop, the native+wasm async executor, and crate-root utilities every other layer builds on.",
   nodeIds:[...g("warpui_core/core"),...g("warpui_core/async"),...fr_srcroot]},

  {id:"layer:ui-elements",name:"UI Elements & Layout",
   description:"warpui_core's renderable element and layout tree — flex, table, stack, scrollable, drag, alignment, container box-model and text elements that compose into the view hierarchy.",
   nodeIds:[...g("warpui_core/elements")]},

  {id:"layer:ui-components",name:"UI Components",
   description:"Higher-level reusable widgets built on the element tree — buttons, sliders, switches, segmented controls and similar interactive controls.",
   nodeIds:[...g("warpui_core/ui_components")]},

  {id:"layer:keymap",name:"Keymap / Input Engine",
   description:"The keybinding engine — Keymap, Fixed/Editable bindings, Triggers, Context/ContextPredicate matching and the input Matcher state machine, plus the event model and action enum it dispatches.",
   nodeIds:[...g("warpui_core/keymap"),...keymap_srcroot]},

  {id:"layer:text-fonts",name:"Text & Fonts",
   description:"Text buffer primitives (TextBuffer trait, points/offsets), the font database and glyph metrics, and text shaping/layout with selection geometry that the UI and editor render on.",
   nodeIds:[...g("warpui_core/text"),...g("warpui_core/fonts"),...text_srcroot]},

  {id:"layer:rendering-platform",name:"Rendering, Platform & Windowing",
   description:"Scene/paint rendering, image caching, OS abstraction (clipboard, modals, notifications, accessibility) and window state — the low-level platform integration beneath the framework.",
   nodeIds:[...g("warpui_core/rendering"),...g("warpui_core/platform"),...g("warpui_core/windowing"),...render_srcroot]},

  {id:"layer:editor-content",name:"Editor Content Model",
   description:"The rich-text editing data model of the editor crate — Buffer, selections, undo, anchors, search and multiline handling that hold and mutate document state.",
   nodeIds:[...g("editor/content"),...g("editor/(src-root)")]},

  {id:"layer:editor-render",name:"Editor Rendering & Decoration",
   description:"The editor's rendering pipeline — RenderState/layout model, renderable block elements and text decorations that paint the content model through warpui_core.",
   nodeIds:[...g("editor/render"),...g("editor/decoration")]},

  {id:"layer:vim",name:"Vim Modal Engine",
   description:"The standalone modal-editing library — the vim state machine, motions, text objects, find-char, iterators and registers that drive vim-style editing over the editor's buffers.",
   nodeIds:[...g("vim/(src-root)"),...g("vim/text_objects"),...g("vim/(root)")]},

  {id:"layer:support",name:"Telemetry, Tooling & Project Support",
   description:"Cross-cutting support and project scaffolding — telemetry/tracing, view-tree debug, asset cache, the integration-test harness, benches, test fixtures/data, crate manifests and documentation.",
   nodeIds:[...g("warpui_core/telemetry"),...g("warpui_core/debug"),...g("warpui_core/assets"),...g("warpui_core/integration"),...g("warpui_core/(root)"),...g("warpui_core/test_data"),...support_srcroot,...g("editor/(root)"),...g("editor/test_fixtures"),...g("editor/test_data"),...g("editor/benches")]},
];

// validation
const all=inp.fileNodes.map(n=>n.id);
const seen=new Map();
let dup=0;
for(const L of layers){for(const id of L.nodeIds){if(seen.has(id)){dup++;console.error("DUP:",id);}seen.set(id,L.id);if(!byId.has(id)){console.error("UNKNOWN:",id);}}}
const missing=all.filter(id=>!seen.has(id));
let total=0;layers.forEach(L=>total+=L.nodeIds.length);
console.error("Layers:",layers.length,"Assigned:",total,"Input:",all.length,"Dups:",dup,"Missing:",missing.length);
if(missing.length){console.error("MISSING IDS:");missing.forEach(m=>console.error("  ",m));}
console.error("Per-layer counts:");layers.forEach(L=>console.error("  ",String(L.nodeIds.length).padStart(3),L.id));

if(missing.length===0 && dup===0 && total===all.length){
  fs.writeFileSync("/home/mhb/warp/.understand-anything/intermediate/layers.json",JSON.stringify(layers,null,2));
  console.error("\nWROTE layers.json OK");
}else{
  console.error("\nVALIDATION FAILED — not writing");process.exit(1);
}
