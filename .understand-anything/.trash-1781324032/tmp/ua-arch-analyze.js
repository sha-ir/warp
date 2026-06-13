#!/usr/bin/env node
'use strict';

const fs = require('fs');

function main() {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!inputPath || !outputPath) {
    console.error('Usage: ua-arch-analyze.js <input.json> <output.json>');
    process.exit(1);
  }

  const raw = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const fileNodes = raw.fileNodes || [];
  const importEdges = raw.importEdges || [];
  const allEdges = raw.allEdges || [];

  const idToNode = new Map();
  for (const n of fileNodes) idToNode.set(n.id, n);

  // ---- Common prefix of all file paths ----
  const paths = fileNodes.map(n => n.filePath);
  function commonPrefixDir(paths) {
    if (paths.length === 0) return '';
    const segArrays = paths.map(p => p.split('/'));
    let prefix = [];
    const first = segArrays[0];
    for (let i = 0; i < first.length - 1; i++) {
      const seg = first[i];
      if (segArrays.every(a => a.length > i + 1 && a[i] === seg)) {
        prefix.push(seg);
      } else break;
    }
    return prefix.length ? prefix.join('/') + '/' : '';
  }
  const prefix = commonPrefixDir(paths);

  // ---- A. Directory Grouping ----
  // Multi-crate layout: common prefix is `crates/`. Grouping at the crate level
  // (3 groups) is too coarse for layer detection, so descend one level past any
  // `src/` segment to produce crate + src-subdirectory granular groups that map
  // cleanly onto architectural layers.
  function groupKey(filePath) {
    let rest = filePath;
    if (prefix && rest.startsWith(prefix)) rest = rest.slice(prefix.length);
    const segs = rest.split('/');
    if (segs.length === 1) return '(root)';
    const crate = segs[0];
    if (segs[1] === 'src') {
      // file directly under src/ -> crate/src-root ; else crate/<subdir>
      if (segs.length <= 3) return crate + '/(src-root)';
      return crate + '/' + segs[2];
    }
    // non-src crate dirs (test_fixtures, benches, test_data, etc.) or crate root files
    if (segs.length === 2) return crate + '/(root)';
    return crate + '/' + segs[1];
  }
  const directoryGroups = {};
  for (const n of fileNodes) {
    const k = groupKey(n.filePath);
    (directoryGroups[k] = directoryGroups[k] || []).push(n.id);
  }

  // ---- B. Node Type Grouping ----
  const nodeTypeGroups = {};
  for (const n of fileNodes) {
    (nodeTypeGroups[n.type] = nodeTypeGroups[n.type] || []).push(n.id);
  }

  // ---- C. Import Adjacency: fan-in / fan-out ----
  const fileFanOut = {};
  const fileFanIn = {};
  for (const n of fileNodes) { fileFanOut[n.id] = 0; fileFanIn[n.id] = 0; }
  for (const e of importEdges) {
    if (fileFanOut[e.source] !== undefined) fileFanOut[e.source]++;
    if (fileFanIn[e.target] !== undefined) fileFanIn[e.target]++;
  }

  // group-of helper
  const idToGroup = new Map();
  for (const [g, ids] of Object.entries(directoryGroups)) {
    for (const id of ids) idToGroup.set(id, g);
  }

  // ---- E. Inter-Group Import Frequency ----
  const interMap = {}; // "from||to" -> count
  for (const e of importEdges) {
    const gs = idToGroup.get(e.source);
    const gt = idToGroup.get(e.target);
    if (gs === undefined || gt === undefined) continue;
    if (gs === gt) continue;
    const key = gs + '||' + gt;
    interMap[key] = (interMap[key] || 0) + 1;
  }
  const interGroupImports = Object.entries(interMap)
    .map(([k, count]) => { const [from, to] = k.split('||'); return { from, to, count }; })
    .sort((a, b) => b.count - a.count);

  // ---- F. Intra-Group Import Density ----
  const intraGroupDensity = {};
  const groupTotalEdges = {};
  const groupInternalEdges = {};
  for (const g of Object.keys(directoryGroups)) { groupTotalEdges[g] = 0; groupInternalEdges[g] = 0; }
  for (const e of importEdges) {
    const gs = idToGroup.get(e.source);
    const gt = idToGroup.get(e.target);
    if (gs === undefined && gt === undefined) continue;
    if (gs !== undefined) groupTotalEdges[gs]++;
    if (gt !== undefined && gt !== gs) groupTotalEdges[gt]++;
    if (gs !== undefined && gs === gt) {
      groupInternalEdges[gs]++;
      // counted once in total above; add internal also counts as a total edge for the group
      groupTotalEdges[gs]++; // ensure internal contributes to total once more for ratio sense
    }
  }
  for (const g of Object.keys(directoryGroups)) {
    const internal = groupInternalEdges[g];
    const total = groupTotalEdges[g];
    intraGroupDensity[g] = {
      internalEdges: internal,
      totalEdges: total,
      density: total > 0 ? +(internal / total).toFixed(3) : 0
    };
  }

  // ---- D. Cross-Category Dependency Analysis ----
  const crossMap = {}; // fromType||toType||edgeType -> count
  for (const e of allEdges) {
    const sn = idToNode.get(e.source);
    const tn = idToNode.get(e.target);
    if (!sn || !tn) continue;
    if (sn.type === 'file' && tn.type === 'file') continue; // only cross-category
    const key = sn.type + '||' + tn.type + '||' + e.type;
    crossMap[key] = (crossMap[key] || 0) + 1;
  }
  const crossCategoryEdges = Object.entries(crossMap)
    .map(([k, count]) => { const [fromType, toType, edgeType] = k.split('||'); return { fromType, toType, edgeType, count }; })
    .sort((a, b) => b.count - a.count);

  // ---- G. Directory Pattern Matching ----
  const dirPattern = [
    [['routes','api','controllers','endpoints','handlers'], 'api'],
    [['services','core','lib','domain','logic'], 'service'],
    [['models','db','data','persistence','repository','entities'], 'data'],
    [['components','views','pages','ui','layouts','screens'], 'ui'],
    [['middleware','plugins','interceptors','guards'], 'middleware'],
    [['utils','helpers','common','shared','tools'], 'utility'],
    [['config','constants','env','settings'], 'config'],
    [['__tests__','test','tests','spec','specs'], 'test'],
    [['types','interfaces','schemas','contracts','dtos'], 'types'],
    [['hooks'], 'hooks'],
    [['store','state','reducers','actions','slices'], 'state'],
    [['assets','static','public'], 'assets'],
    [['migrations'], 'data'],
    [['management','commands'], 'config'],
    [['templatetags'], 'utility'],
    [['signals'], 'service'],
    [['serializers'], 'api'],
    [['cmd'], 'entry'],
    [['internal'], 'service'],
    [['pkg'], 'utility'],
    [['dto','request','response'], 'types'],
    [['entity'], 'data'],
    [['controller'], 'api'],
    [['routers'], 'api'],
    [['composables'], 'service'],
    [['blueprints'], 'api'],
    [['mailers','jobs','channels'], 'service'],
    [['bin'], 'entry'],
    [['docs','documentation','wiki'], 'documentation'],
    [['deploy','deployment','infra','infrastructure'], 'infrastructure'],
    [['.github','.gitlab','.circleci'], 'ci-cd'],
    [['k8s','kubernetes','helm','charts'], 'infrastructure'],
    [['terraform','tf'], 'infrastructure'],
    [['docker'], 'infrastructure'],
    [['sql','database','schema'], 'data'],
  ];
  const dirPatternMap = {};
  for (const [names, label] of dirPattern) for (const nm of names) dirPatternMap[nm] = label;

  function filePattern(name, filePath) {
    const lower = name.toLowerCase();
    if (/\.(test|spec)\.[^.]+$/.test(name) || /^test_.*\.py$/.test(name) ||
        /_test\.go$/.test(name) || /Test\.java$/.test(name) || /_spec\.rb$/.test(name) ||
        /Test\.php$/.test(name) || /Tests\.cs$/.test(name) || /_tests\.rs$/.test(name)) return 'test';
    if (/\.d\.ts$/.test(name)) return 'types';
    if (name === 'manage.py') return 'entry';
    if (name === 'wsgi.py' || name === 'asgi.py') return 'config';
    if (name === 'main.rs' || name === 'lib.rs') return 'entry';
    if (name === 'Application.java' || name === 'Program.cs') return 'entry';
    if (name === 'config.ru') return 'entry';
    if (['Cargo.toml','go.mod','Gemfile','pom.xml','build.gradle','composer.json'].includes(name)) return 'config';
    if (name === 'Dockerfile' || /^docker-compose\..*/.test(name)) return 'infrastructure';
    if (/\.(tf|tfvars)$/.test(name)) return 'infrastructure';
    if (name === '.gitlab-ci.yml' || name === 'Jenkinsfile') return 'ci-cd';
    if (/\.sql$/.test(name)) return 'data';
    if (/\.(graphql|gql|proto)$/.test(name)) return 'types';
    if (/\.(md|rst)$/.test(name)) return 'documentation';
    if (name === 'Makefile') return 'infrastructure';
    if (name === 'build.rs') return 'config';
    return null;
  }

  const patternMatches = {};
  for (const g of Object.keys(directoryGroups)) {
    // group keys look like `crate/subdir`; match on the trailing subdir segment
    const sub = g.split('/').pop().replace(/[()]/g, '').toLowerCase();
    if (dirPatternMap[sub]) patternMatches[g] = dirPatternMap[sub];
  }

  // file-level pattern matches (per node) for richer signal
  const filePatternMatches = {};
  for (const n of fileNodes) {
    const fp = filePattern(n.name, n.filePath);
    if (fp) filePatternMatches[n.id] = fp;
  }

  // ---- H. Deployment Topology Detection ----
  const allNames = fileNodes.map(n => ({ name: n.name, path: n.filePath, id: n.id }));
  const infraFiles = [];
  let hasDockerfile = false, hasCompose = false, hasK8s = false, hasTerraform = false, hasCI = false;
  for (const f of allNames) {
    if (f.name === 'Dockerfile' || /^Dockerfile\./.test(f.name)) { hasDockerfile = true; infraFiles.push(f.path); }
    else if (/^docker-compose\..*/.test(f.name)) { hasCompose = true; infraFiles.push(f.path); }
    else if (/\.(tf|tfvars)$/.test(f.name)) { hasTerraform = true; infraFiles.push(f.path); }
    else if (f.path.includes('.github/workflows') || f.name === '.gitlab-ci.yml' || f.name === 'Jenkinsfile') { hasCI = true; infraFiles.push(f.path); }
    else if (/k8s|kubernetes|helm|charts/.test(f.path)) { hasK8s = true; infraFiles.push(f.path); }
  }
  const deploymentTopology = { hasDockerfile, hasCompose, hasK8s, hasTerraform, hasCI, infraFiles };

  // ---- I. Data Pipeline Detection ----
  const dataPipeline = {
    schemaFiles: allNames.filter(f => /\.(sql|graphql|gql|proto|prisma)$/.test(f.name)).map(f => f.path),
    migrationFiles: allNames.filter(f => /migrations?\//.test(f.path)).map(f => f.path),
    dataModelFiles: allNames.filter(f => /\/(models|entities|entity)\//.test(f.path)).map(f => f.path),
    apiHandlerFiles: allNames.filter(f => /\/(routes|controllers|handlers|api|endpoints)\//.test(f.path)).map(f => f.path),
  };

  // ---- J. Documentation Coverage ----
  const docNodes = fileNodes.filter(n => n.type === 'document' || /\.(md|rst)$/.test(n.name));
  const docGroups = new Set(docNodes.map(n => idToGroup.get(n.id)));
  const groups = Object.keys(directoryGroups);
  const groupsWithDocs = [...docGroups].filter(g => g !== undefined).length;
  const totalGroups = groups.length;
  const undocumentedGroups = groups.filter(g => !docGroups.has(g));
  const docCoverage = {
    groupsWithDocs,
    totalGroups,
    coverageRatio: totalGroups ? +(groupsWithDocs / totalGroups).toFixed(2) : 0,
    undocumentedGroups
  };

  // ---- K. Dependency Direction ----
  const pairNet = {}; // "a|b" sorted -> {a->b, b->a}
  for (const { from, to, count } of interGroupImports) {
    const key = [from, to].sort().join('|||');
    pairNet[key] = pairNet[key] || {};
    pairNet[key][from + '>' + to] = count;
  }
  const dependencyDirection = [];
  const seenPairs = new Set();
  for (const { from, to } of interGroupImports) {
    const key = [from, to].sort().join('|||');
    if (seenPairs.has(key)) continue;
    seenPairs.add(key);
    const fwd = interMap[from + '||' + to] || 0;
    const bwd = interMap[to + '||' + from] || 0;
    if (fwd >= bwd) dependencyDirection.push({ dependent: from, dependsOn: to });
    else dependencyDirection.push({ dependent: to, dependsOn: from });
  }

  // ---- File Stats ----
  const filesPerGroup = {};
  for (const [g, ids] of Object.entries(directoryGroups)) filesPerGroup[g] = ids.length;
  const nodeTypeCounts = {};
  for (const [t, ids] of Object.entries(nodeTypeGroups)) nodeTypeCounts[t] = ids.length;

  const fileStats = {
    totalFileNodes: fileNodes.length,
    commonPrefix: prefix,
    filesPerGroup,
    nodeTypeCounts
  };

  const result = {
    scriptCompleted: true,
    commonPrefix: prefix,
    directoryGroups,
    nodeTypeGroups,
    crossCategoryEdges,
    interGroupImports,
    intraGroupDensity,
    patternMatches,
    filePatternMatches,
    deploymentTopology,
    dataPipeline,
    docCoverage,
    dependencyDirection,
    fileStats,
    fileFanIn,
    fileFanOut
  };

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  console.error('Analysis complete. Groups:', Object.keys(directoryGroups).length, 'Files:', fileNodes.length);
  process.exit(0);
}

try { main(); }
catch (err) { console.error('FATAL:', err && err.stack ? err.stack : err); process.exit(1); }
