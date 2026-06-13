const fs = require('fs');
const dir = '/home/mhb/warp/.understand-anything/intermediate';
const g = JSON.parse(fs.readFileSync(dir + '/assembled-graph.json', 'utf8'));
const nodeIds = new Set(g.nodes.map(n => n.id));

// ---- layers (already normalized in place) ----
let layers = JSON.parse(fs.readFileSync(dir + '/layers.json', 'utf8'));
if (!Array.isArray(layers) && Array.isArray(layers.layers)) layers = layers.layers;

// ---- tour: normalize ----
let tour = JSON.parse(fs.readFileSync(dir + '/tour.json', 'utf8'));
if (!Array.isArray(tour) && Array.isArray(tour.steps)) tour = tour.steps;
const knownPrefix = /^(file|function|class|module|concept|config|document|service|table|endpoint|pipeline|schema|resource):/;
tour = tour.map(s => {
  if (s.nodesToInspect && !s.nodeIds) { s.nodeIds = s.nodesToInspect; delete s.nodesToInspect; }
  if (s.whyItMatters && !s.description) { s.description = s.whyItMatters; delete s.whyItMatters; }
  s.nodeIds = (s.nodeIds || [])
    .map(id => knownPrefix.test(id) ? id : ('file:' + id))
    .filter(id => nodeIds.has(id));
  return s;
}).sort((a, b) => a.order - b.order);

// ---- assemble full KnowledgeGraph ----
const graph = {
  version: '1.0.0',
  project: {
    name: 'Warp — input/editing/keybinding stack',
    languages: ['rust', 'markdown', 'toml'],
    frameworks: ['serde', 'tokio', 'warpui'],
    description: "Scoped analysis of three Rust crates forming Warp's input/editing/keybinding stack: warpui_core (bespoke in-house UI framework + the keymap/keybinding engine), editor (rich-text editing engine), and vim (modal-editing library). Built to support work on a more configurable keybinding engine, a better keybinding settings UI, and pluggable modal editing modes (vim/helix/kakoune).",
    analyzedAt: new Date().toISOString(),
    gitCommitHash: 'd7ecfac54855bd41e5bc8d7b2c3f44c1895fea0c',
  },
  nodes: g.nodes,
  edges: g.edges,
  layers,
  tour,
};
fs.writeFileSync(dir + '/assembled-graph.json', JSON.stringify(graph, null, 2));
console.log('Assembled: ' + graph.nodes.length + ' nodes, ' + graph.edges.length + ' edges, ' +
  graph.layers.length + ' layers, ' + graph.tour.length + ' tour steps.');
console.log('Tour steps:'); tour.forEach(s => console.log('  ' + s.order + '. ' + s.title + '  [' + s.nodeIds.length + ' nodes]'));
