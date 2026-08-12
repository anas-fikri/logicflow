#!/usr/bin/env python3
"""
apps-diagram renderer — custom D3.js force-directed graph from graphify graph.json
Output: self-contained interactive HTML (no mermaid, no external deps except D3 CDN)

Usage:
    python3 render.py <graph.json> [--output diagram.html] [--mode manager|developer|all]
"""
import json
import sys
import argparse
from pathlib import Path

D3_CONTENT = open(Path(__file__).parent / "vendor" / "d3.v7.min.js").read()

HTML_PREFIX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""" + "{title}" + """ — Apps Diagram</title>
<script>""" + D3_CONTENT + """</script>
<style>
@media print {
  #toolbar, #sidebar, #info-panel { display: none !important; }
  #graph { margin: 0 !important; width: 100% !important; height: 100vh !important; }
}

* { margin: 0; padding: 0; box-sizing: border-box; }

#toolbar {
  position: fixed; top: 0; left: 0; right: 0; height: 52px;
  background: #161b22; border-bottom: 1px solid #30363d;
  display: flex; align-items: center; padding: 0 16px; gap: 12px; z-index: 100;
}
#toolbar h1 { font-size: 15px; font-weight: 600; color: #58a6ff; white-space: nowrap; }
#toolbar .stats { font-size: 12px; color: #8b949e; }
#toolbar .spacer { flex: 1; }
.btn {
  padding: 6px 14px; border-radius: 6px; border: 1px solid #30363d;
  background: #21262d; color: #c9d1d9; cursor: pointer; font-size: 13px;
  transition: all 0.15s;
}
.btn:hover { background: #30363d; border-color: #58a6ff; }
.btn.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }
.btn[data-mode="flow"].active { background: #7c3aed; border-color: #7c3aed; }
.btn-group { display: flex; gap: 4px; }
#view-modes { display: flex; gap: 4px; margin-left: 16px; padding-left: 16px; border-left: 1px solid #30363d; }
#view-modes span { font-size: 11px; color: #8b949e; align-self: center; margin-right: 4px; }

#sidebar {
  position: fixed; left: 0; top: 52px; bottom: 0; width: 280px;
  background: #161b22; border-right: 1px solid #30363d;
  overflow-y: auto; padding: 12px; z-index: 50;
}
#sidebar h3 { font-size: 11px; text-transform: uppercase; color: #8b949e; margin-bottom: 8px; letter-spacing: 0.5px; }
.filter-chip {
  display: inline-block; padding: 3px 10px; margin: 2px; border-radius: 12px;
  font-size: 11px; cursor: pointer; border: 1px solid #30363d; background: #21262d;
  transition: all 0.15s;
}
.filter-chip:hover { border-color: #58a6ff; }
.filter-chip.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }

#info-panel {
  position: fixed; right: 0; top: 52px; bottom: 0; width: 320px;
  background: #161b22; border-left: 1px solid #30363d;
  overflow-y: auto; padding: 16px; z-index: 50;
  transform: translateX(100%); transition: transform 0.2s;
}
#info-panel.open { transform: translateX(0); }
#info-panel h2 { font-size: 14px; color: #58a6ff; margin-bottom: 8px; word-break: break-all; }
#info-panel .meta { font-size: 12px; color: #8b949e; margin-bottom: 12px; }
#info-panel .section { margin-bottom: 16px; }
#info-panel .section-title { font-size: 11px; text-transform: uppercase; color: #8b949e; margin-bottom: 6px; }
#info-panel .edge-list { list-style: none; }
#info-panel .edge-list li {
  padding: 4px 8px; margin: 2px 0; border-radius: 4px; background: #21262d;
  font-size: 12px; cursor: pointer; transition: background 0.15s;
}
#info-panel .edge-list li:hover { background: #30363d; }
#info-panel .close {
  position: absolute; top: 12px; right: 12px; cursor: pointer;
  font-size: 18px; color: #8b949e;
}
#info-panel .close:hover { color: #c9d1d9; }

#graph { margin-left: 280px; margin-top: 52px; width: calc(100% - 280px); height: calc(100vh - 52px); }
#graph svg { width: 100%; height: 100%; }

.node circle { stroke: #30363d; stroke-width: 1.5px; cursor: pointer; transition: r 0.15s; }
.node text {
  font-size: 11px; fill: #ffffff; pointer-events: none;
  text-anchor: middle; dominant-baseline: middle;
  text-shadow: 0 0 4px rgba(0,0,0,0.9), 0 1px 2px rgba(0,0,0,0.8);
  font-weight: 500;
}
.node:hover circle { stroke-width: 3px; }
.node.selected circle { stroke: #58a6ff; stroke-width: 3px; }

.link { stroke-opacity: 0.4; transition: stroke-opacity 0.15s; }
.link.highlighted { stroke-opacity: 1; stroke-width: 2px; }
.link.dimmed { stroke-opacity: 0.08; }
.node.dimmed { opacity: 0.2; }

/* Relation colors */
.link.imports_from, .link.imports { stroke: #58a6ff; }
.link.calls, .link.indirect_call { stroke: #f0883e; }
.link.contains { stroke: #3fb950; }
.link.references, .link.method { stroke: #bc8cff; }

/* Node type colors (by source_file extension or prefix) */
.node[data-type="server"] circle { fill: #f0883e; }
.node[data-type="config"] circle { fill: #d29922; }
.node[data-type="model"] circle { fill: #3fb950; }
.node[data-type="route"] circle { fill: #58a6ff; }
.node[data-type="service"] circle { fill: #f85149; }
.node[data-type="util"] circle { fill: #8b949e; }
.node[data-type="ref"] circle { fill: #6e7681; r: 4; }
.node[data-type="default"] circle { fill: #79c0ff; }

#legend {
  position: fixed; bottom: 12px; left: 292px;
  background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 8px 12px; z-index: 50; font-size: 11px;
}
#legend .item { display: flex; align-items: center; gap: 6px; margin: 2px 0; }
#legend .dot { width: 10px; height: 10px; border-radius: 50%; }

.tooltip {
  position: absolute; pointer-events: none; z-index: 200;
  background: #1c2128; border: 1px solid #444c56; border-radius: 6px;
  padding: 6px 10px; font-size: 12px; max-width: 300px;
  opacity: 0; transition: opacity 0.15s;
}
.tooltip.visible { opacity: 1; }
.tooltip .tt-label { color: #58a6ff; font-weight: 600; }
.tooltip .tt-file { color: #8b949e; font-size: 11px; }

/* Search */
#search {
  padding: 4px 10px; border-radius: 6px; border: 1px solid #30363d;
  background: #0d1117; color: #c9d1d9; font-size: 13px; width: 180px;
}
#search:focus { outline: none; border-color: #58a6ff; }

/* Mode toggle */
.mode-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
</style>
</head>
<body>

<div id="toolbar">
  <h1>🏗 {{TITLE}}</h1>
  <span class="stats" id="stats">— nodes, — edges</span>
  <div class="spacer"></div>
  <span class="mode-label">View</span>
  <div class="btn-group">
    <button class="btn active" data-mode="all" onclick="setMode('all')">All</button>
    <button class="btn" data-mode="manager" onclick="setMode('manager')">Manager</button>
    <button class="btn" data-mode="developer" onclick="setMode('developer')">Developer</button>
    <button class="btn" data-mode="flow" onclick="setMode('flow')">Flow</button>
  </div>
  <input type="text" id="search" placeholder="Search nodes..." oninput="searchNodes(this.value)">
  <button class="btn" onclick="exportPNG()">PNG</button>
  <button class="btn" onclick="exportSVG()">SVG</button>
  <button class="btn" onclick="window.print()">PDF</button>
</div>

<div id="sidebar">
  <h3>Filter by Relation</h3>
  <div id="relation-filters"></div>
  <h3 style="margin-top:16px">Filter by Type</h3>
  <div id="type-filters"></div>
  <h3 style="margin-top:16px">Controls</h3>
  <div style="font-size:12px;color:#8b949e;line-height:1.6">
    <div>• Click node → details</div>
    <div>• Scroll → zoom</div>
    <div>• Drag → pan</div>
    <div>• Drag node → reposition</div>
    <div>• Double-click → collapse/expand</div>
  </div>
</div>

<div id="graph">
  <svg id="svg"></svg>
</div>

<div id="info-panel">
  <span class="close" onclick="closePanel()">×</span>
  <h2 id="info-label"></h2>
  <div class="meta" id="info-meta"></div>
  <div class="section">
    <div class="section-title">Connections (Out)</div>
    <ul class="edge-list" id="info-out"></ul>
  </div>
  <div class="section">
    <div class="section-title">Connections (In)</div>
    <ul class="edge-list" id="info-in"></ul>
  </div>
</div>

<div id="legend">
  <div class="item"><div class="dot" style="background:#f0883e"></div>Server/Entry</div>
  <div class="item"><div class="dot" style="background:#3fb950"></div>Contains</div>
  <div class="item"><div class="dot" style="background:#58a6ff"></div>Imports</div>
  <div class="item"><div class="dot" style="background:#f85149"></div>Service</div>
  <div class="item"><div class="dot" style="background:#bc8cff"></div>References</div>
  <div class="item"><div class="dot" style="background:#6e7681"></div>External Ref</div>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
const GRAPH_DATA = __GRAPH_DATA__;
const APP_NAME = "{{TITLE}}";

// --- Classify node type ---
function nodeType(n) {
  const id = (n.id || '').toLowerCase();
  const file = (n.source_file || '').toLowerCase();
  const label = (n.label || '').toLowerCase();

  if (id.startsWith('ref_')) return 'ref';
  if (file.includes('server') || file.includes('index') || file.includes('main') || file.includes('app.')) {
    if (id.endsWith('_app') || id === 'server' || id.includes('_server')) return 'server';
  }
  if (label.includes('route') || label.includes('router') || id.includes('route')) return 'route';
  if (label.includes('model') || label.includes('schema') || id.includes('model')) return 'model';
  if (label.includes('service') || label.includes('controller') || id.includes('service') || id.includes('controller')) return 'service';
  if (label.includes('config') || label.includes('env') || id.includes('config') || id.includes('_port') || id.includes('_host') || id.includes('_origins')) return 'config';
  if (label.includes('util') || label.includes('helper') || id.includes('util') || id.includes('helper')) return 'util';
  if (file.endsWith('.js') || file.endsWith('.ts') || file.endsWith('.php') || file.endsWith('.py')) return 'default';
  return 'default';
}

// --- Manager view: collapse to file-level only ---
function buildManagerView(nodes, edges) {
  // Group nodes by source_file
  const fileGroups = {};
  const nodeById = {};
  nodes.forEach(n => {
    nodeById[n.id] = n;
    const f = n.source_file || 'unknown';
    if (!fileGroups[f]) fileGroups[f] = { id: 'file:' + f, label: f, source_file: f, _children: [], _type: nodeType(n) };
    fileGroups[f]._children.push(n);
  });
  const mNodes = Object.values(fileGroups);

  // Aggregate edges between file groups
  // Handle D3 mutated edges where source/target are objects
  const edgeMap = {};
  edges.forEach(e => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source;
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target;
    const srcNode = nodeById[srcId];
    const tgtNode = nodeById[tgtId];
    if (!srcNode || !tgtNode) return;
    const srcFile = srcNode.source_file || 'unknown';
    const tgtFile = tgtNode.source_file || 'unknown';
    if (srcFile === tgtFile) return;
    const key = 'file:' + srcFile + '|file:' + tgtFile;
    if (!edgeMap[key]) edgeMap[key] = { source: 'file:' + srcFile, target: 'file:' + tgtFile, relation: e.relation, count: 1 };
    else edgeMap[key].count++;
  });
  const mEdges = Object.values(edgeMap).map(e => ({ ...e, id: e.source + '|' + e.target, weight: e.count }));
  return { nodes: mNodes, edges: mEdges };
}

// --- State ---
let currentMode = 'all';
let activeRelations = new Set();
let activeTypes = new Set();
let allNodes = GRAPH_DATA.nodes;
let allEdges = GRAPH_DATA.edges;
let filteredNodes = allNodes;
let filteredEdges = allEdges;
let selectedNode = null;

// --- Init filters ---
function initFilters() {
  const relations = [...new Set(filteredEdges.map(e => e.relation))];
  const types = [...new Set(filteredNodes.map(n => n._type || nodeType(n)))];

  const relDiv = document.getElementById('relation-filters');
  relDiv.innerHTML = relations.map(r =>
    `<span class="filter-chip active" data-rel="${r}" onclick="toggleRelation('${r}', this)">${r}</span>`
  ).join('');

  const typeDiv = document.getElementById('type-filters');
  typeDiv.innerHTML = types.map(t =>
    `<span class="filter-chip active" data-type="${t}" onclick="toggleType('${t}', this)">${t}</span>`
  ).join('');

  activeRelations = new Set(relations);
  activeTypes = new Set(types);
}

function toggleRelation(r, el) {
  if (activeRelations.has(r)) { activeRelations.delete(r); el.classList.remove('active'); }
  else { activeRelations.add(r); el.classList.add('active'); }
  applyFilters();
}
function toggleType(t, el) {
  if (activeTypes.has(t)) { activeTypes.delete(t); el.classList.remove('active'); }
  else { activeTypes.add(t); el.classList.add('active'); }
  applyFilters();
}

function buildFlowView(nodes, edges) {
  // Find route-like nodes: labels containing app.get/post/put/delete/patch, router, route, or HTTP methods
  const routePatterns = /^(app\.(get|post|put|delete|patch|use|all)|router\.(get|post|put|delete|patch|use|all)|route|endpoint|api\.)/i;
  const nodeById = {};
  nodes.forEach(n => { nodeById[n.id] = n; });

  // Find route nodes
  const routeNodes = nodes.filter(n => {
    const label = (n.label || n.id || '').toLowerCase();
    return routePatterns.test(label) ||
      ['route', 'endpoint', 'controller'].includes(n._type || nodeType(n));
  });

  if (routeNodes.length === 0) return { nodes: [], edges: [] };

  // BFS from each route node, following calls/contains edges, max depth 3
  const flowNodeIds = new Set();
  const flowEdges = [];

  routeNodes.forEach(route => {
    flowNodeIds.add(route.id);
    let frontier = [route.id];
    for (let depth = 0; depth < 3 && frontier.length > 0; depth++) {
      const nextFrontier = [];
      edges.forEach(e => {
        const srcId = typeof e.source === 'object' ? e.source.id : e.source;
        const tgtId = typeof e.target === 'object' ? e.target.id : e.target;
        if (frontier.includes(srcId) && ['calls', 'indirect_call', 'contains', 'method'].includes(e.relation)) {
          if (!flowNodeIds.has(tgtId)) {
            flowNodeIds.add(tgtId);
            nextFrontier.push(tgtId);
          }
          flowEdges.push(e);
        }
      });
      frontier = nextFrontier;
    }
  });

  const flowNodes = nodes.filter(n => flowNodeIds.has(n.id));
  return { nodes: flowNodes, edges: flowEdges };
}

function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));

  if (mode === 'manager') {
    const mv = buildManagerView(allNodes, allEdges);
    filteredNodes = mv.nodes;
    filteredEdges = mv.edges;
  } else if (mode === 'developer') {
    // Developer: all nodes, only code relations (imports/calls/contains), no refs
    filteredNodes = allNodes;
    filteredEdges = allEdges.filter(e =>
      ['imports', 'imports_from', 'calls', 'indirect_call', 'contains', 'method'].includes(e.relation)
    );
  } else if (mode === 'flow') {
    // Flow: route → handler → response (BFS from route nodes)
    const fv = buildFlowView(allNodes, allEdges);
    filteredNodes = fv.nodes;
    filteredEdges = fv.edges;
  } else {
    // All: everything
    filteredNodes = allNodes;
    filteredEdges = allEdges;
  }
  initFilters();
  applyFilters();
}

function applyFilters() {
  let nodes = filteredNodes;
  let edges = filteredEdges;

  // Filter edges by relation
  edges = edges.filter(e => activeRelations.has(e.relation));
  const connectedIds = new Set();
  edges.forEach(e => { connectedIds.add(e.source); connectedIds.add(e.target); });

  // Filter nodes by type and connectivity
  nodes = nodes.filter(n => {
    const t = n._type || nodeType(n);
    return activeTypes.has(t);
  });

  // Keep only nodes that appear in filtered edges OR all nodes if no edges
  // Handle D3 mutated edges where source/target are objects
  if (currentMode !== 'manager') {
    const nodeIds = new Set(nodes.map(n => n.id));
    edges = edges.filter(e => {
      const srcId = typeof e.source === 'object' ? e.source.id : e.source;
      const tgtId = typeof e.target === 'object' ? e.target.id : e.target;
      return nodeIds.has(srcId) && nodeIds.has(tgtId);
    });
  }

  updateStats(nodes, edges);
  render(nodes, edges);
}

function updateStats(nodes, edges) {
  document.getElementById('stats').textContent = `${nodes.length} nodes, ${edges.length} edges`;
}

// --- D3 Render ---
let svg, g, linkGroup, nodeGroup, simulation;

function initSVG() {
  const svgEl = document.getElementById('svg');
  svg = d3.select(svgEl);
  svg.selectAll('*').remove();

  const width = svgEl.clientWidth;
  const height = svgEl.clientHeight;

  // Zoom support
  const zoom = d3.zoom()
    .scaleExtent([0.1, 8])
    .on('zoom', (event) => g.attr('transform', event.transform));
  svg.call(zoom);

  g = svg.append('g');
  linkGroup = g.append('g').attr('class', 'links');
  nodeGroup = g.append('g').attr('class', 'nodes');

  simulation = d3.forceSimulation()
    .force('link', d3.forceLink().id(d => d.id).distance(d => 60 + Math.random() * 40).strength(0.3))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 4));
}

function nodeRadius(d) {
  const t = d._type || nodeType(d);
  if (t === 'ref') return 4;
  if (t === 'config') return 5;
  // Size by connection count
  const connections = filteredEdges.filter(e => e.source === d.id || e.target === d.id).length;
  return Math.min(6 + connections * 0.5, 14);
}

function render(nodes, edges) {
  if (!simulation) initSVG();
  simulation.stop();

  const link = linkGroup.selectAll('line')
      .data(edges, d => d.id)
      .join('line')
      .attr('stroke', d => relationColor(d.relation))
      .attr('stroke-width', d => Math.sqrt(d.weight || 1))
      .attr('stroke-opacity', 0.55)
      .attr('marker-end', 'url(#arrowhead)');

    // D3 v7 pattern: enter/merge/exit all via .join()
    const node = nodeGroup.selectAll('g.node')
      .data(nodes, d => d.id)
      .join(
        enter => {
          const g = enter.append('g')
            .attr('class', 'node')
            .style('cursor', 'pointer')
            .call(d3.drag()
              .on('start', dragStart)
              .on('drag', dragging)
              .on('end', dragEnd))
            .on('click', (event, d) => { event.stopPropagation(); selectNode(d); })
            .on('mouseover', (event, d) => showTooltip(event, d))
            .on('mouseout', hideTooltip);
          g.append('circle')
            .attr('r', d => nodeRadius(d))
            .attr('fill', d => nodeColor(d));
          g.append('text')
            .text(d => truncate(d.label || d.id, 20))
            .attr('y', d => -nodeRadius(d) - 6)
            .attr('font-size', d => nodeRadius(d) > 8 ? 11 : 9);
          return g;
        }
      );

    // Restart simulation
    simulation.nodes(nodes);
    simulation.force('link').links(edges);
    simulation.alpha(1).restart();

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

function relationColor(r) {
  const colors = {
    'imports_from': '#58a6ff', 'imports': '#58a6ff',
    'calls': '#f0883e', 'indirect_call': '#f0883e',
    'contains': '#3fb950',
    'references': '#bc8cff', 'method': '#bc8cff',
  };
  return colors[r] || '#8b949e';
}

function nodeColor(d) {
  const t = d._type || nodeType(d);
  const colors = {
    'server': '#f0883e', 'config': '#d29922', 'model': '#3fb950',
    'route': '#58a6ff', 'service': '#f85149', 'util': '#8b949e',
    'ref': '#6e7681', 'default': '#79c0ff',
  };
  return colors[t] || '#79c0ff';
}

function truncate(s, n) { return s.length > n ? s.slice(0, n - 1) + '…' : s; }

// --- Tooltip ---
function showTooltip(event, d) {
  const tt = document.getElementById('tooltip');
  tt.innerHTML = `<div class="tt-label">${d.label || d.id}</div><div class="tt-file">${d.source_file || ''}</div>`;
  tt.classList.add('visible');
  tt.style.left = (event.pageX + 12) + 'px';
  tt.style.top = (event.pageY - 28) + 'px';
}
function hideTooltip() { document.getElementById('tooltip').classList.remove('visible'); }

// --- Node selection ---
function selectNode(d) {
  selectedNode = d;
  document.querySelectorAll('.node').forEach(n => n.classList.remove('selected'));
  d3.select(this).classed('selected', true);

  // Highlight connected edges
  const connected = new Set([d.id]);
  linkGroup.selectAll('line')
    .classed('highlighted', e => (e.source.id === d.id || e.target.id === d.id))
    .classed('dimmed', e => !(e.source.id === d.id || e.target.id === d.id));
  nodeGroup.selectAll('.node')
    .classed('dimmed', n => !connected.has(n.id) && !isConnected(n.id, d.id));

  // Info panel
  const panel = document.getElementById('info-panel');
  panel.classList.add('open');
  document.getElementById('info-label').textContent = d.label || d.id;
  document.getElementById('info-meta').textContent = `File: ${d.source_file || '?'} | Type: ${d._type || nodeType(d)}`;

  const outEdges = filteredEdges.filter(e => (e.source.id || e.source) === d.id);
  const inEdges = filteredEdges.filter(e => (e.target.id || e.target) === d.id);

  document.getElementById('info-out').innerHTML = outEdges.map(e =>
    `<li onclick="selectById('${(e.target.id || e.target)}')">${e.relation} → ${nodeLabel(e.target)}</li>`
  ).join('') || '<li style="color:#8b949e">None</li>';

  document.getElementById('info-in').innerHTML = inEdges.map(e =>
    `<li onclick="selectById('${(e.source.id || e.source)}')">${nodeLabel(e.source)} → ${e.relation}</li>`
  ).join('') || '<li style="color:#8b949e">None</li>';
}

function nodeLabel(n) { return n.label || n.id || n; }
function isConnected(id1, id2) {
  return filteredEdges.some(e =>
    (e.source.id === id1 && e.target.id === id2) ||
    (e.source.id === id2 && e.target.id === id1)
  );
}

function selectById(id) {
  const node = filteredNodes.find(n => n.id === id);
  if (node) selectNode(node);
}

function closePanel() {
  document.getElementById('info-panel').classList.remove('open');
  selectedNode = null;
  document.querySelectorAll('.node').forEach(n => n.classList.remove('selected', 'dimmed'));
  linkGroup.selectAll('line').classed('highlighted', false).classed('dimmed', false);
}

// --- Search ---
function searchNodes(query) {
  if (!query) {
    nodeGroup.selectAll('.node').classed('dimmed', false);
    return;
  }
  const q = query.toLowerCase();
  nodeGroup.selectAll('.node').classed('dimmed', d => {
    const label = (d.label || d.id || '').toLowerCase();
    const file = (d.source_file || '').toLowerCase();
    return !label.includes(q) && !file.includes(q);
  });
}

// --- Drag ---
function dragStart(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x; d.fy = d.y;
}
function dragging(event, d) { d.fx = event.x; d.fy = event.y; }
function dragEnd(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null; d.fy = null;
}

// --- Export PNG ---
function exportPNG() {
  const svgEl = document.getElementById('svg');
  // Clone SVG and set explicit dimensions
  const clone = svgEl.cloneNode(true);
  const w = svgEl.clientWidth || 1200;
  const h = svgEl.clientHeight || 800;
  clone.setAttribute('width', w);
  clone.setAttribute('height', h);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  const svgData = new XMLSerializer().serializeToString(clone);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const img = new Image();
  const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);
  img.onload = () => {
    canvas.width = w * 2;
    canvas.height = h * 2;
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);
    const a = document.createElement('a');
    a.download = APP_NAME.replace(/[^a-z0-9]/gi, '_') + '_diagram.png';
    a.href = canvas.toDataURL('image/png');
    a.click();
  };
  img.onerror = () => { URL.revokeObjectURL(url); alert('PNG export failed. Try SVG export.'); };
  img.src = url;
}

function exportSVG() {
  const svgEl = document.getElementById('svg');
  const clone = svgEl.cloneNode(true);
  const w = svgEl.clientWidth || 1200;
  const h = svgEl.clientHeight || 800;
  clone.setAttribute('width', w);
  clone.setAttribute('height', h);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  const svgData = new XMLSerializer().serializeToString(clone);
  const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
  const a = document.createElement('a');
  a.download = APP_NAME.replace(/[^a-z0-9]/gi, '_') + '_diagram.svg';
  a.href = URL.createObjectURL(blob);
  a.click();
}

// --- Init ---
initSVG();
initFilters();
updateStats(filteredNodes, filteredEdges);
render(filteredNodes, filteredEdges);

// Resize
window.addEventListener('resize', () => {
  simulation.force('center', d3.forceCenter(
    document.getElementById('svg').clientWidth / 2,
    document.getElementById('svg').clientHeight / 2
  ));
  simulation.alpha(0.3).restart();
});
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Render graphify graph.json to interactive HTML")
    parser.add_argument("graph_json", help="Path to graph.json")
    parser.add_argument("--output", "-o", default="diagram.html", help="Output HTML path")
    parser.add_argument("--title", "-t", default=None, help="Diagram title (default: from folder name)")
    args = parser.parse_args()

    graph_path = Path(args.graph_json)
    if not graph_path.exists():
        print(f"Error: {graph_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(graph_path) as f:
        data = json.load(f)

    # Clean data for embedding
    clean_nodes = []
    for n in data.get("nodes", []):
        clean_nodes.append({
            "id": n.get("id", ""),
            "label": n.get("label", n.get("id", "")),
            "source_file": n.get("source_file", ""),
            "source_location": n.get("source_location", ""),
        })

    clean_edges = []
    for e in data.get("edges", []):
        clean_edges.append({
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "relation": e.get("relation", "unknown"),
        })

    # Filter edges: only keep edges where both source & target exist in nodes
    node_ids = {n["id"] for n in clean_nodes}
    clean_edges = [e for e in clean_edges if e["source"] in node_ids and e["target"] in node_ids]

    graph_data = {"nodes": clean_nodes, "edges": clean_edges}

    title = args.title or graph_path.parent.parent.name

    html = HTML_PREFIX.replace("__GRAPH_DATA__", json.dumps(graph_data))
    html = html.replace("{title}", title)

    output = Path(args.output)
    output.write_text(html, encoding="utf-8")
    print(f"Wrote {output} ({output.stat().st_size // 1024} KB)")
    print(f"Open with: file://{output.resolve()}")


if __name__ == "__main__":
    main()