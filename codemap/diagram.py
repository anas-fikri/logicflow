"""CodeMap Diagram — Interactive HTML/SVG diagram builder.

Features:
- SVG-based node-link diagram (no external libs)
- Click node → highlight connected edges + show details
- Detail panel: validation, fields, DB relations
- Arrowheads on edges
- Collapse/expand on double-click
- Pan/zoom
- Dark theme, self-contained HTML
"""

import json
import os
from pathlib import Path


# ─── D3.js vendor ────────────────────────────────────────────────────────────

D3_PATH = Path(__file__).parent.parent / "vendor" / "d3.v7.min.js"


def load_d3():
    if D3_PATH.exists():
        return D3_PATH.read_text()
    return ""  # Fallback: no D3


# ─── HTML template ───────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ — CodeMap</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; overflow: hidden; }

#app { display: flex; height: 100vh; }

/* Sidebar */
#sidebar { width: 280px; background: #161b22; border-right: 1px solid #30363d; display: flex; flex-direction: column; }
#sidebar h2 { padding: 16px; font-size: 14px; color: #58a6ff; border-bottom: 1px solid #30363d; }
#tabs { display: flex; padding: 8px; gap: 4px; border-bottom: 1px solid #30363d; }
.tab { padding: 6px 12px; border: 1px solid #30363d; border-radius: 4px; background: transparent; color: #8b949e; cursor: pointer; font-size: 12px; transition: all 0.15s; }
.tab:hover { color: #c9d1d9; border-color: #58a6ff; }
.tab.active { background: #1f6feb; color: #fff; border-color: #1f6feb; }
#filter-box { padding: 8px; border-bottom: 1px solid #30363d; }
#filter-box input { width: 100%; padding: 6px 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 4px; color: #c9d1d9; font-size: 12px; }
#filter-box input:focus { outline: none; border-color: #58a6ff; }
#node-list { flex: 1; overflow-y: auto; }
.list-item { padding: 8px 16px; border-bottom: 1px solid #21262d; cursor: pointer; font-size: 12px; display: flex; align-items: center; gap: 8px; transition: background 0.1s; }
.list-item:hover { background: #21262d; }
.list-item.active { background: #1f6feb33; border-left: 3px solid #58a6ff; }
.list-item .icon { font-size: 14px; }
.list-item .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.list-item .count { font-size: 10px; color: #484f58; }
#stats { padding: 12px 16px; border-top: 1px solid #30363d; font-size: 11px; color: #484f58; }

/* Canvas */
#canvas-wrap { flex: 1; position: relative; overflow: hidden; }
#canvas { width: 100%; height: 100%; cursor: grab; }
#canvas:active { cursor: grabbing; }

/* Tooltip */
#tooltip { position: fixed; background: #1f2937; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; font-size: 12px; max-width: 320px; z-index: 1000; pointer-events: none; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }

/* Detail panel */
#detail { position: absolute; right: 0; top: 0; width: 400px; height: 100%; background: #161b22; border-left: 1px solid #30363d; overflow-y: auto; transform: translateX(100%); transition: transform 0.25s ease; z-index: 100; }
#detail.visible { transform: translateX(0); }
#detail .header { padding: 16px; border-bottom: 1px solid #30363d; position: sticky; top: 0; background: #161b22; z-index: 1; }
#detail .header h3 { font-size: 16px; color: #58a6ff; margin-bottom: 4px; }
#detail .header .path { font-size: 11px; color: #484f58; }
#detail .close-btn { position: absolute; top: 16px; right: 16px; background: none; border: none; color: #8b949e; font-size: 20px; cursor: pointer; }
#detail .close-btn:hover { color: #f85149; }
#detail .section { padding: 16px; border-bottom: 1px solid #21262d; }
#detail .section h4 { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
#detail .section .row { padding: 4px 0; font-size: 13px; }
#detail .section .tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 10px; background: #30363d; color: #c9d1d9; margin-right: 4px; }
#detail .section .tag.method-get { background: #238636; color: #fff; }
#detail .section .tag.method-post { background: #d29922; color: #fff; }
#detail .section .tag.method-put { background: #1f6feb; color: #fff; }
#detail .section .tag.method-delete { background: #da3633; color: #fff; }
#detail .section .tag.method-mixed { background: #8957e5; color: #fff; }
#detail .section .tag.auth { background: #f8514933; color: #f85149; }
#detail .section .tag.public { background: #23863633; color: #3fb950; }
#detail .field-list { list-style: none; }
#detail .field-list li { padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 12px; display: flex; justify-content: space-between; }
#detail .field-list .fname { color: #58a6ff; font-family: monospace; }
#detail .field-list .ftype { color: #8b949e; font-family: monospace; }
#detail .field-list .fflags { color: #d29922; font-size: 10px; }
.link-item { padding: 6px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; color: #58a6ff; transition: background 0.1s; }
.link-item:hover { background: #21262d; }

/* SVG styles */
.node-rect { rx: 6; stroke: #30363d; stroke-width: 1.5; transition: stroke 0.15s, opacity 0.15s; }
.node-rect.selected { stroke: #f0e040; stroke-width: 3; }
.node-rect.collapsed { stroke-dasharray: 4 3; opacity: 0.6; }
.node-rect.dimmed { opacity: 0.2; }
.node-text { fill: #ffffff; font-size: 11px; font-weight: 500; pointer-events: none; text-anchor: middle; dominant-baseline: middle; text-shadow: 0 0 4px rgba(0,0,0,0.8); }
.node-label { fill: #b1bac4; font-size: 9px; pointer-events: none; text-anchor: end; }
.collapse-badge { fill: #f0e040; font-size: 11px; pointer-events: none; font-weight: 700; text-anchor: middle; dominant-baseline: middle; }
.edge { fill: none; stroke: #30363d; stroke-width: 1.5; transition: stroke-opacity 0.15s, stroke-width 0.15s; }
.edge.calls { stroke: #3fb950; }
.edge.route { stroke: #58a6ff; }
.edge.contains { stroke: #484f58; stroke-width: 1; }
.edge.db { stroke: #d29922; }
.edge.validates { stroke: #8957e5; }
.edge.highlighted { stroke-width: 3; stroke-opacity: 1; filter: drop-shadow(0 0 4px currentColor); }
.edge.dimmed { stroke-opacity: 0.08; }
.col-label { fill: #8b949e; font-size: 13px; font-weight: 600; text-anchor: middle; text-transform: uppercase; letter-spacing: 1px; }
.col-line { stroke: #21262d; stroke-width: 1; stroke-dasharray: 4 4; }
.legend { position: absolute; bottom: 12px; left: 12px; background: #161b22ee; border: 1px solid #30363d; border-radius: 6px; padding: 10px; font-size: 11px; }
.legend .row { display: flex; align-items: center; gap: 6px; margin: 2px 0; }
.legend .swatch { width: 14px; height: 3px; border-radius: 2px; }
</style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <h2>📊 __TITLE__</h2>
    <div id="tabs">
      <button class="tab active" data-view="flow" onclick="setView('flow')">Flow</button>
      <button class="tab" data-view="db" onclick="setView('db')">Database</button>
      <button class="tab" data-view="validation" onclick="setView('validation')">Validasi</button>
    </div>
    <div id="filter-box">
      <input type="text" id="search" placeholder="Cari node..." oninput="filterNodes(this.value)">
    </div>
    <div id="node-list"></div>
    <div id="stats"></div>
  </div>
  <div id="canvas-wrap">
    <svg id="canvas"></svg>
    <div id="tooltip"></div>
    <div id="detail">
      <div class="header">
        <button class="close-btn" onclick="closeDetail()">×</button>
        <h3 id="detail-title">—</h3>
        <div class="path" id="detail-path">—</div>
      </div>
      <div id="detail-body"></div>
    </div>
    <div class="legend">
      <div class="row"><div class="swatch" style="background:#58a6ff"></div> Route</div>
      <div class="row"><div class="swatch" style="background:#3fb950"></div> Calls</div>
      <div class="row"><div class="swatch" style="background:#d29922"></div> Database</div>
      <div class="row"><div class="swatch" style="background:#8957e5"></div> Validates</div>
      <div class="row"><div class="swatch" style="background:#484f58"></div> Contains</div>
    </div>
  </div>
</div>

<script>
__D3_JS__

// ─── Data injected by Python ────────────────────────────────────────────────
const SCAN = __SCAN_DATA__;
const NODES = [];
const EDGES = [];
const NODE_MAP = {};
const OUT_EDGES = {};
const IN_EDGES = {};

// ─── Build graph from scan data ─────────────────────────────────────────────
function buildGraph() {
  let idc = 0;
  function nid() { return 'n' + (idc++); }

  // Endpoint nodes
  (SCAN.endpoints || []).forEach(ep => {
    const id = nid();
    const node = {
      id, type: 'endpoint', label: ep.path.slice(0, 28),
      method: ep.method, path: ep.path, file: ep.file, line: ep.line,
      auth: ep.auth, etype: ep.type,
      _kind: 'endpoint',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Controller/business logic nodes
  (SCAN.business_logic || []).forEach(bl => {
    const id = nid();
    const node = {
      id, type: 'logic', label: bl.name.slice(0, 24),
      name: bl.name, file: bl.file, line: bl.line,
      ltype: bl.type, kind: bl.kind,
      _kind: 'logic',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Validation nodes
  (SCAN.validations || []).slice(0, 60).forEach(v => {
    const id = nid();
    const node = {
      id, type: 'validation', label: (v.field || v.rule || 'validate').slice(0, 22),
      file: v.file, line: v.line, rule: v.rule, field: v.field,
      raw: v.raw, vkind: v.kind,
      _kind: 'validation',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Database table nodes
  const tables = SCAN.database?.tables || {};
  Object.entries(tables).forEach(([name, info]) => {
    const id = nid();
    const node = {
      id, type: 'table', label: name,
      file: info.file, line: info.line,
      columns: info.columns || [],
      _kind: 'table',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // DB query nodes
  (SCAN.database?.queries || []).slice(0, 40).forEach(q => {
    const id = nid();
    const node = {
      id, type: 'query', label: (q.table || 'query').slice(0, 20),
      file: q.file, line: q.line, table: q.table, operation: q.operation,
      _kind: 'query',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Form nodes
  (SCAN.forms || []).forEach(f => {
    const id = nid();
    const node = {
      id, type: 'form', label: (f.action || f.type).slice(0, 22),
      file: f.file, line: f.line, action: f.action, ftype: f.type,
      _kind: 'form',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Build edges: connect endpoints → logic (same file)
  NODES.forEach(n => {
    OUT_EDGES[n.id] = [];
    IN_EDGES[n.id] = [];
  });

  // endpoint → logic (same file)
  NODES.filter(n => n._kind === 'endpoint').forEach(ep => {
    NODES.filter(n => n._kind === 'logic' && n.file === ep.file).forEach(logic => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: ep.id, target: logic.id, relation: 'calls' });
      OUT_EDGES[ep.id].push(eid);
      IN_EDGES[logic.id].push(eid);
    });
  });

  // logic → validation (same file)
  NODES.filter(n => n._kind === 'logic').forEach(logic => {
    NODES.filter(n => n._kind === 'validation' && n.file === logic.file).forEach(val => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: logic.id, target: val.id, relation: 'validates' });
      OUT_EDGES[logic.id].push(eid);
      IN_EDGES[val.id].push(eid);
    });
  });

  // logic → query (same file)
  NODES.filter(n => n._kind === 'logic').forEach(logic => {
    NODES.filter(n => n._kind === 'query' && n.file === logic.file).forEach(q => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: logic.id, target: q.id, relation: 'db' });
      OUT_EDGES[logic.id].push(eid);
      IN_EDGES[q.id].push(eid);
    });
  });

  // query → table (by table name)
  NODES.filter(n => n._kind === 'query').forEach(q => {
    NODES.filter(n => n._kind === 'table' && n.label === q.table).forEach(t => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: q.id, target: t.id, relation: 'db' });
      OUT_EDGES[q.id].push(eid);
      IN_EDGES[t.id].push(eid);
    });
  });

  // form → endpoint (by action path)
  NODES.filter(n => n._kind === 'form').forEach(f => {
    if (!f.action) return;
    NODES.filter(n => n._kind === 'endpoint' && n.path === f.action).forEach(ep => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: f.id, target: ep.id, relation: 'route' });
      OUT_EDGES[f.id].push(eid);
      IN_EDGES[ep.id].push(eid);
    });
  });

  // DB relations (FK → table)
  (SCAN.database?.relations || []).forEach(rel => {
    const fromTable = NODES.find(n => n._kind === 'table' && n.label === rel.from_table);
    const toTable = NODES.find(n => n._kind === 'table' && n.label === rel.to_table);
    if (fromTable && toTable) {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: fromTable.id, target: toTable.id, relation: 'db' });
      OUT_EDGES[fromTable.id].push(eid);
      IN_EDGES[toTable.id].push(eid);
    }
  });
}

// ─── Color by type ──────────────────────────────────────────────────────────
const TYPE_COLORS = {
  endpoint: '#58a6ff',
  logic: '#3fb950',
  validation: '#8957e5',
  table: '#d29922',
  query: '#e3b341',
  form: '#f0883e',
};

const TYPE_LABELS = {
  endpoint: 'API',
  logic: 'FN',
  validation: 'VAL',
  table: 'TBL',
  query: 'QRY',
  form: 'FRM',
};

// ─── Layout ──────────────────────────────────────────────────────────────────
const MARGIN = { top: 60, right: 80, bottom: 40, left: 80 };
const NODE_W = 160;
const NODE_H = 36;
const LAYER_GAP = 240;
const NODE_GAP = 12;

let currentView = 'flow';
let collapsedNodes = new Set();
let selectedNode = null;
let filteredNodes = [];
let filteredEdges = [];

function getFlowLayers() {
  const layers = [[], [], [], [], []];
  const placed = new Set();

  // Layer 0: forms
  filteredNodes.filter(n => n._kind === 'form').forEach(n => {
    layers[0].push(n); placed.add(n.id);
  });

  // Layer 1: endpoints
  filteredNodes.filter(n => n._kind === 'endpoint').forEach(n => {
    layers[1].push(n); placed.add(n.id);
  });

  // Layer 2: logic
  filteredNodes.filter(n => n._kind === 'logic').forEach(n => {
    layers[2].push(n); placed.add(n.id);
  });

  // Layer 3: validation + query
  filteredNodes.filter(n => n._kind === 'validation' || n._kind === 'query').forEach(n => {
    layers[3].push(n); placed.add(n.id);
  });

  // Layer 4: tables
  filteredNodes.filter(n => n._kind === 'table').forEach(n => {
    layers[4].push(n); placed.add(n.id);
  });

  // Unplaced nodes → layer 2
  filteredNodes.forEach(n => {
    if (!placed.has(n.id)) layers[2].push(n);
  });

  return layers;
}

function getDBLayers() {
  const layers = [[], []];
  filteredNodes.filter(n => n._kind === 'table').forEach(n => layers[0].push(n));
  filteredNodes.filter(n => n._kind === 'query').forEach(n => layers[1].push(n));
  return layers;
}

function getValidationLayers() {
  const layers = [[], []];
  filteredNodes.filter(n => n._kind === 'endpoint' || n._kind === 'logic').forEach(n => layers[0].push(n));
  filteredNodes.filter(n => n._kind === 'validation').forEach(n => layers[1].push(n));
  return layers;
}

function render() {
  const svg = d3.select('#canvas');
  svg.selectAll('*').remove();
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;

  // Arrowhead markers
  const defs = svg.append('defs');
  const edgeColors = [
    ['arrow-calls', '#3fb950'],
    ['arrow-route', '#58a6ff'],
    ['arrow-db', '#d29922'],
    ['arrow-validates', '#8957e5'],
    ['arrow-contains', '#484f58'],
    ['arrow-default', '#58a6ff'],
  ];
  edgeColors.forEach(([name, color]) => {
    defs.append('marker').attr('id', name).attr('viewBox', '0 -5 10 10')
      .attr('refX', 10).attr('refY', 0).attr('markerWidth', 7).attr('markerHeight', 7)
      .attr('orient', 'auto-start-reverse')
      .append('path').attr('d', 'M0,-5 L10,0 L0,5').attr('fill', color);
  });

  // Layers
  let layers;
  let labels;
  if (currentView === 'flow') {
    layers = getFlowLayers();
    labels = ['Form/Page', 'Endpoint', 'Logic', 'Validate/Query', 'Database'];
  } else if (currentView === 'db') {
    layers = getDBLayers();
    labels = ['Tables', 'Queries'];
  } else {
    layers = getValidationLayers();
    labels = ['Endpoint/Logic', 'Validation'];
  }

  // Column labels + lines
  labels.forEach((l, i) => {
    svg.append('text').attr('x', MARGIN.left + i * LAYER_GAP + NODE_W/2)
      .attr('y', 28).attr('text-anchor', 'middle').attr('class', 'col-label').text(l);
    svg.append('line').attr('x1', MARGIN.left + i * LAYER_GAP)
      .attr('y1', 40).attr('x2', MARGIN.left + i * LAYER_GAP).attr('y2', height)
      .attr('class', 'col-line');
  });

  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);
  const edgeLayer = g.append('g');
  const nodeLayer = g.append('g');

  // Positions
  const positions = {};
  const visibleLayers = layers.map(layer =>
    layer.filter(n => {
      if (collapsedNodes.has(n.id)) return true;
      const parents = (IN_EDGES[n.id] || []).map(eid => {
        const e = EDGES.find(e => e.id === eid);
        return e ? e.source : null;
      });
      return !parents.some(p => collapsedNodes.has(p));
    })
  );

  visibleLayers.forEach((layer, li) => {
    if (!layer || layer.length === 0) return;
    const totalH = layer.length * (NODE_H + NODE_GAP) - NODE_GAP;
    const startY = Math.max(0, (height - MARGIN.top - MARGIN.bottom - totalH) / 2);
    layer.forEach((node, ni) => {
      positions[node.id] = { x: li * LAYER_GAP, y: startY + ni * (NODE_H + NODE_GAP) };
    });
  });

  // Edges
  filteredEdges.forEach(e => {
    const sp = positions[e.source];
    const tp = positions[e.target];
    if (!sp || !tp) return;

    // Skip if either endpoint collapsed
    if (collapsedNodes.has(e.source) || collapsedNodes.has(e.target)) return;

    const cls = `edge ${e.relation}`;
    const marker = `arrow-${e.relation === 'contains' ? 'contains' : e.relation}`;
    const startX = sp.x + NODE_W;
    const startY2 = sp.y + NODE_H/2;
    const endX = tp.x;
    const endY = tp.y + NODE_H/2;

    edgeLayer.append('path')
      .attr('class', cls)
      .attr('data-source', e.source)
      .attr('data-target', e.target)
      .attr('marker-end', `url(#${marker})`)
      .attr('d', `M${startX},${startY2} C${startX+40},${startY2} ${endX-40},${endY} ${endX},${endY}`)
      .style('stroke-opacity', 0.5);
  });

  // Nodes
  visibleLayers.forEach((layer, li) => {
    if (!layer || layer.length === 0) return;
    const totalH = layer.length * (NODE_H + NODE_GAP) - NODE_GAP;
    const startY = Math.max(0, (height - MARGIN.top - MARGIN.bottom - totalH) / 2);

    layer.forEach((node, ni) => {
      const x = li * LAYER_GAP;
      const y = startY + ni * (NODE_H + NODE_GAP);
      const isCollapsed = collapsedNodes.has(node.id);
      const hasChildren = (OUT_EDGES[node.id] || []).length > 0;
      const color = TYPE_COLORS[node._kind] || '#484f58';
      const typeLabel = TYPE_LABELS[node._kind] || '';

      const ng = nodeLayer.append('g')
        .attr('class', 'node-box')
        .attr('transform', `translate(${x},${y})`)
        .datum(node)
        .on('click', (ev) => { ev.stopPropagation(); selectNode(node); })
        .on('dblclick', function(ev) {
          ev.stopPropagation();
          if (hasChildren) toggleCollapse(node.id);
        })
        .on('mouseover', function(ev) {
          d3.select(this).select('rect').attr('stroke-width', 2.5);
          showTooltip(ev, node);
        })
        .on('mouseout', function() {
          d3.select(this).select('rect').attr('stroke-width', 1.5);
          hideTooltip();
        });

      ng.append('rect')
        .attr('class', `node-rect${isCollapsed ? ' collapsed' : ''}`)
        .attr('width', NODE_W).attr('height', NODE_H)
        .attr('fill', color + '22')
        .attr('stroke', color);

      // Method badge for endpoints
      if (node.method) {
        ng.append('text')
          .attr('x', 8).attr('y', NODE_H/2)
          .attr('class', 'node-label')
          .attr('text-anchor', 'start')
          .attr('fill', color)
          .style('font-weight', '700')
          .style('font-size', '9px')
          .text(node.method.slice(0, 4).toUpperCase());
      }

      ng.append('text')
        .attr('class', 'node-text')
        .attr('x', NODE_W/2 + 10).attr('y', NODE_H/2)
        .text(node.label);

      // Type label
      ng.append('text')
        .attr('class', 'node-label')
        .attr('x', NODE_W - 4).attr('y', 10)
        .attr('fill', '#b1bac4')
        .text(typeLabel);

      // Collapse badge
      if (hasChildren) {
        ng.append('text')
          .attr('class', 'collapse-badge')
          .attr('x', NODE_W - 14).attr('y', NODE_H/2)
          .text(isCollapsed ? '▶' : '▼');
      }
    });
  });

  // Stats
  document.getElementById('stats').textContent =
    `${NODES.length} nodes · ${EDGES.length} edges · ${collapsedNodes.size} collapsed`;
}

// ─── Selection + highlight ──────────────────────────────────────────────────
function selectNode(node) {
  selectedNode = node;
  d3.selectAll('.node-rect').classed('selected', false);
  d3.selectAll('.node-box').filter(d => d && d.id === node.id).select('rect').classed('selected', true);

  // Highlight connected
  const connected = new Set([node.id]);
  (OUT_EDGES[node.id] || []).forEach(eid => {
    const e = EDGES.find(e => e.id === eid);
    if (e) connected.add(e.target);
  });
  (IN_EDGES[node.id] || []).forEach(eid => {
    const e = EDGES.find(e => e.id === eid);
    if (e) connected.add(e.source);
  });

  d3.selectAll('.node-box').classed('dimmed', d => d && !connected.has(d.id));
  d3.selectAll('.edge').classed('highlighted', function() {
    return this.getAttribute('data-source') === node.id || this.getAttribute('data-target') === node.id;
  });
  d3.selectAll('.edge').classed('dimmed', function() {
    return this.getAttribute('data-source') !== node.id && this.getAttribute('data-target') !== node.id;
  });

  showDetail(node);
}

function clearHighlight() {
  d3.selectAll('.node-box').classed('dimmed', false);
  d3.selectAll('.edge').classed('highlighted', false).classed('dimmed', false);
}

function toggleCollapse(nodeId) {
  if (collapsedNodes.has(nodeId)) collapsedNodes.delete(nodeId);
  else collapsedNodes.add(nodeId);
  render();
}

function closeDetail() {
  document.getElementById('detail').classList.remove('visible');
  d3.selectAll('.node-rect').classed('selected', false);
  selectedNode = null;
  clearHighlight();
}

// ─── Detail panel ────────────────────────────────────────────────────────────
function showDetail(node) {
  const panel = document.getElementById('detail');
  panel.classList.add('visible');

  document.getElementById('detail-title').textContent = node.label || node.name || node.id;
  document.getElementById('detail-path').textContent = `${node.file || '—'} : ${node.line || ''}`;

  const body = document.getElementById('detail-body');
  let html = '';

  // Type + kind
  html += `<div class="section">
    <h4>Tipe</h4>
    <div class="row"><span class="tag">${TYPE_LABELS[node._kind] || node._kind}</span> ${node._kind}</div>
  </div>`;

  // Endpoint details
  if (node._kind === 'endpoint') {
    html += `<div class="section">
      <h4>HTTP Method</h4>
      <div class="row"><span class="tag method-${(node.method||'mixed').toLowerCase()}">${node.method || 'MIXED'}</span></div>
    </div>`;
    html += `<div class="section">
      <h4>Path</h4>
      <div class="row"><code>${node.path}</code></div>
    </div>`;
    html += `<div class="section">
      <h4>Auth</h4>
      <div class="row"><span class="tag ${node.auth === 'auth_required' ? 'auth' : 'public'}">${node.auth || 'unknown'}</span></div>
    </div>`;
    html += `<div class="section">
      <h4>Framework</h4>
      <div class="row">${node.etype || '—'}</div>
    </div>`;
  }

  // Logic details
  if (node._kind === 'logic') {
    html += `<div class="section">
      <h4>Function</h4>
      <div class="row"><code>${node.name}</code></div>
      <div class="row" style="color:#8b949e">Type: ${node.ltype || 'function'}</div>
    </div>`;
  }

  // Validation details
  if (node._kind === 'validation') {
    html += `<div class="section">
      <h4>Validation Rule</h4>
      <div class="row"><strong>Field:</strong> <code>${node.field || '—'}</code></div>
      <div class="row"><strong>Rule:</strong> <code>${node.rule || '—'}</code></div>
      <div class="row"><strong>Kind:</strong> ${node.vkind || '—'}</div>
    </div>`;
    if (node.raw) {
      html += `<div class="section">
        <h4>Raw Code</h4>
        <div class="row"><code style="color:#d29922">${node.raw}</code></div>
      </div>`;
    }
  }

  // Table details — show columns
  if (node._kind === 'table' && node.columns && node.columns.length > 0) {
    html += `<div class="section">
      <h4>Columns (${node.columns.length})</h4>
      <ul class="field-list">`;
    node.columns.forEach(col => {
      html += `<li>
        <span class="fname">${col.name}</span>
        <span class="ftype">${col.type}</span>
        <span class="fflags">${col.flags || ''}</span>
      </li>`;
    });
    html += `</ul></div>`;
  }

  // Query details
  if (node._kind === 'query') {
    html += `<div class="section">
      <h4>Query</h4>
      <div class="row"><strong>Table:</strong> <code>${node.table || '—'}</code></div>
      <div class="row"><strong>Operation:</strong> <code>${node.operation || '—'}</code></div>
    </div>`;
  }

  // Form details
  if (node._kind === 'form') {
    html += `<div class="section">
      <h4>Form</h4>
      <div class="row"><strong>Action:</strong> <code>${node.action || '—'}</code></div>
      <div class="row"><strong>Type:</strong> ${node.ftype || '—'}</div>
    </div>`;
  }

  // Connected edges
  const outE = (OUT_EDGES[node.id] || []).map(eid => EDGES.find(e => e.id === eid)).filter(Boolean);
  const inE = (IN_EDGES[node.id] || []).map(eid => EDGES.find(e => e.id === eid)).filter(Boolean);

  if (outE.length > 0) {
    html += `<div class="section">
      <h4>Calls / Outgoing (${outE.length})</h4>`;
    outE.slice(0, 20).forEach(e => {
      const target = NODE_MAP[e.target];
      if (target) {
        html += `<div class="link-item" onclick="selectById('${e.target}')">→ ${target.label}</div>`;
      }
    });
    if (outE.length > 20) html += `<div style="color:#484f58;font-size:11px">+${outE.length - 20} more</div>`;
    html += `</div>`;
  }

  if (inE.length > 0) {
    html += `<div class="section">
      <h4>Called by / Incoming (${inE.length})</h4>`;
    inE.slice(0, 20).forEach(e => {
      const source = NODE_MAP[e.source];
      if (source) {
        html += `<div class="link-item" onclick="selectById('${e.source}')">← ${source.label}</div>`;
      }
    });
    if (inE.length > 20) html += `<div style="color:#484f58;font-size:11px">+${inE.length - 20} more</div>`;
    html += `</div>`;
  }

  body.innerHTML = html;
}

function selectById(id) {
  const node = NODE_MAP[id];
  if (node) selectNode(node);
}

// ─── Tooltip ────────────────────────────────────────────────────────────────
function showTooltip(ev, node) {
  const tip = document.getElementById('tooltip');
  const kind = node._kind;
  const color = TYPE_COLORS[kind] || '#8b949e';
  let inner = `<strong style="color:${color}">${node.label}</strong>`;
  if (node.method) inner += ` <span style="color:#484f58">[${node.method}]</span>`;
  if (node.file) inner += `<div style="color:#484f58;font-size:10px">${node.file}:${node.line || ''}</div>`;
  inner += `<div style="color:#8b949e">↳ ${(OUT_EDGES[node.id]||[]).length} out, ${(IN_EDGES[node.id]||[]).length} in</div>`;
  tip.innerHTML = inner;
  tip.style.display = 'block';
  tip.style.left = (ev.pageX + 12) + 'px';
  tip.style.top = (ev.pageY - 10) + 'px';
}

function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

// ─── Sidebar ────────────────────────────────────────────────────────────────
function renderSidebar() {
  const list = document.getElementById('node-list');
  list.innerHTML = '';

  const icons = {
    endpoint: '🔵', logic: '🟢', validation: '🟣',
    table: '🟡', query: '🟠', form: '🔴',
  };

  filteredNodes.forEach(node => {
    const div = document.createElement('div');
    div.className = 'list-item';
    div.innerHTML = `<span class="icon">${icons[node._kind] || '⚫'}</span>
      <span class="name">${node.label}</span>
      <span class="count">${(OUT_EDGES[node.id]||[]).length}</span>`;
    div.onclick = () => selectById(node.id);
    list.appendChild(div);
  });
}

function filterNodes(q) {
  if (!q) {
    filteredNodes = [...NODES];
    filteredEdges = [...EDGES];
  } else {
    const ql = q.toLowerCase();
    filteredNodes = NODES.filter(n =>
      (n.label || '').toLowerCase().includes(ql) ||
      (n.path || '').toLowerCase().includes(ql) ||
      (n.name || '').toLowerCase().includes(ql) ||
      (n.file || '').toLowerCase().includes(ql)
    );
    const ids = new Set(filteredNodes.map(n => n.id));
    filteredEdges = EDGES.filter(e => ids.has(e.source) && ids.has(e.target));
  }
  render();
  renderSidebar();
}

// ─── View switching ─────────────────────────────────────────────────────────
function setView(view) {
  currentView = view;
  collapsedNodes.clear();
  clearHighlight();
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === view));
  render();
}

// ─── Zoom + pan ──────────────────────────────────────────────────────────────
function initZoom() {
  const svg = d3.select('#canvas');
  const zoom = d3.zoom().scaleExtent([0.05, 8])
    .filter(e => !e.target.closest('.node-box') || e.type !== 'dblclick')
    .on('zoom', e => svg.attr('transform', e.transform));
  svg.call(zoom);
  svg.on('dblclick.zoom', null);
}

// ─── Init ────────────────────────────────────────────────────────────────────
buildGraph();
filteredNodes = [...NODES];
filteredEdges = [...EDGES];
initZoom();
render();
renderSidebar();

// Click empty canvas → deselect
document.getElementById('canvas-wrap').addEventListener('click', (e) => {
  if (e.target.tagName === 'svg' || e.target.tagName === 'rect' && !e.target.classList.contains('node-rect')) {
    closeDetail();
  }
});
</script>
</body>
</html>"""


class DiagramBuilder:
    """Build interactive HTML diagram from scan data."""

    def build(self, scan_result, title="CodeMap"):
        d3_js = load_d3()
        scan_json = json.dumps(scan_result, ensure_ascii=False)

        html = HTML_TEMPLATE.replace("__D3_JS__", d3_js)
        html = html.replace("__SCAN_DATA__", scan_json)
        html = html.replace("__TITLE__", title)
        return html