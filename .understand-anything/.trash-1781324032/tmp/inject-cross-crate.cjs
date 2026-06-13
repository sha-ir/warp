const fs = require('fs');
const { execSync } = require('child_process');
const GP = '/home/mhb/warp/.understand-anything/intermediate/assembled-graph.json';
const g = JSON.parse(fs.readFileSync(GP, 'utf8'));

const crateDir = { warpui_core: 'crates/warpui_core', editor: 'crates/editor', vim: 'crates/vim' };

// file nodes present in graph (by relative path)
const fileNodePaths = new Set(g.nodes.filter(n => n.type === 'file').map(n => n.id.replace(/^file:/, '')));
// symbol name -> set of defining file paths (from "type:path:Name" node ids)
const symToPaths = new Map();
for (const n of g.nodes) {
  if (n.type !== 'class' && n.type !== 'function') continue;
  const m = n.id.match(/^(?:class|function):(.+):([^:]+)$/);
  if (!m) continue;
  const path = m[1], name = m[2];
  if (!symToPaths.has(name)) symToPaths.set(name, new Set());
  symToPaths.get(name).add(path);
}

const edgeKey = (s, t, ty) => s + ' ' + t + ' ' + ty;
const existing = new Set(g.edges.map(e => edgeKey(e.source, e.target, e.type)));

const files = execSync("git ls-files crates/warpui_core crates/editor crates/vim", { encoding: 'utf8' })
  .split('\n').filter(f => f.endsWith('.rs'));

let added = 0; const sample = []; const perPair = {};
for (const src of files) {
  if (!fileNodePaths.has(src)) continue;
  const text = fs.readFileSync(src, 'utf8');
  const re = /use\s+(warpui_core|editor|vim)\s*::([\s\S]*?);/g;
  let m; const wanted = new Map();
  while ((m = re.exec(text)) !== null) {
    const crate = m[1];
    if (src.startsWith(crateDir[crate] + '/')) continue; // skip same-crate
    const syms = m[2].match(/\b[A-Z][A-Za-z0-9]+\b/g) || [];
    if (!wanted.has(crate)) wanted.set(crate, new Set());
    for (const s of syms) wanted.get(crate).add(s);
  }
  for (const [crate, syms] of wanted) {
    for (const sym of syms) {
      const defs = symToPaths.get(sym);
      if (!defs) continue;
      const inCrate = [...defs].filter(p => p.startsWith(crateDir[crate] + '/'));
      if (inCrate.length !== 1) continue; // unambiguous only
      const tgt = inCrate[0];
      if (tgt === src) continue;
      const k = edgeKey('file:' + src, 'file:' + tgt, 'imports');
      if (existing.has(k)) continue;
      existing.add(k);
      g.edges.push({ source: 'file:' + src, target: 'file:' + tgt, type: 'imports', weight: 0.7 });
      added++;
      const pk = src.split('/')[1] + ' -> ' + crate;
      perPair[pk] = (perPair[pk] || 0) + 1;
      if (sample.length < 10) sample.push(src + '  --imports-->  ' + tgt + '  (' + sym + ')');
    }
  }
}

fs.writeFileSync(GP, JSON.stringify(g, null, 2));
console.log('Cross-crate imports edges added:', added);
console.log('By crate pair:', JSON.stringify(perPair));
console.log('Sample:'); sample.forEach(s => console.log('  ' + s));
console.log('Graph now:', g.nodes.length, 'nodes,', g.edges.length, 'edges');
