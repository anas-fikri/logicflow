"""CodeMap Diagram — Interactive HTML/SVG diagram builder.

Features:
- D3 force-directed layout (Obsidian-style: circles, curves, zoom/pan/drag)
- Multiple views: User Flow (business), Code Flow, Database, Validations
- Click node → highlight connected edges + show details
- Detail panel: fields, validations, DB relations
- Dynamic legend per view
- Dark theme, self-contained HTML (D3 inlined)
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
#tabs { display: flex; padding: 8px; gap: 4px; flex-wrap: wrap; border-bottom: 1px solid #30363d; }
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
.edge { fill: none; stroke: #30363d; stroke-width: 1.5; transition: stroke-opacity 0.15s, stroke-width 0.15s; }
.edge.calls { stroke: #3fb950; }
.edge.route { stroke: #58a6ff; }
.edge.db { stroke: #d29922; }
.edge.validates { stroke: #8957e5; }
.edge.contains { stroke: #484f58; }
.edge.queries { stroke: #d29922; }
.edge.submits { stroke: #f0883e; }
.edge.has { stroke: #f778ba; }
.edge.highlighted { stroke-opacity: 1 !important; stroke-width: 2.5 !important; }
.edge.dimmed { stroke-opacity: 0.05 !important; }
.node-circle { stroke-width: 1.5; transition: stroke 0.15s, opacity 0.15s; }
.node-circle.selected { stroke: #f0e040; stroke-width: 3; }
.node-box.dimmed { opacity: 0.15; }
.node-label-force { font-size: 10px; fill: #c9d1d9; pointer-events: none; }
.type-badge-force { font-size: 8px; font-weight: 600; pointer-events: none; }

/* Legend */
.legend { position: absolute; bottom: 12px; left: 12px; background: #161b22ee; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-size: 11px; max-width: 260px; }
.legend h5 { font-size: 10px; color: #8b949e; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px; }
.legend .row { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.legend .dot { width: 10px; height: 10px; border-radius: 50%; border: 1.5px solid; flex-shrink: 0; }
.legend .line { width: 14px; height: 2px; border-radius: 2px; flex-shrink: 0; }
.legend .sep { height: 1px; background: #30363d; margin: 6px 0; }
</style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <h2>📊 __TITLE__</h2>
    <div id="tabs">
      <button class="tab active" data-view="userflow" onclick="setView('userflow')">User Flow</button>
      <button class="tab" data-view="flow" onclick="setView('flow')">Code Flow</button>
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
    <div id="legend" class="legend"></div>
  </div>
</div>

<script>
__D3_JS__

// ─── Data injected by Python ────────────────────────────────────────────────
const SCAN = __SCAN_DATA__;

// ─── Code graph (existing) ──────────────────────────────────────────────────
const NODES = [];
const EDGES = [];
const NODE_MAP = {};
const OUT_EDGES = {};
const IN_EDGES = {};

// ─── User flow graph (business-centric) ─────────────────────────────────────
const UF_NODES = [];
const UF_EDGES = [];
const UF_NODE_MAP = {};
const UF_OUT_EDGES = {};
const UF_IN_EDGES = {};

// ─── Active graph pointers (swapped on view change) ─────────────────────────
let aNodes, aEdges, aNodeMap, aOutEdges, aInEdges;

// ─── Helpers ────────────────────────────────────────────────────────────────
function asArr(v) { return Array.isArray(v) ? v : (v ? Object.values(v) : []); }

// ─── Build code graph from scan data ────────────────────────────────────────
function buildGraph() {
  let idc = 0;
  function nid() { return 'n' + (idc++); }

  // Endpoint nodes
  asArr(SCAN.endpoints).forEach(ep => {
    const id = nid();
    const node = {
      id, type: 'endpoint', label: (ep.path || '').slice(0, 28),
      method: ep.method, path: ep.path, file: ep.file, line: ep.line,
      auth: ep.auth, etype: ep.type,
      _kind: 'endpoint',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Controller/business logic nodes
  asArr(SCAN.business_logic).forEach(bl => {
    const id = nid();
    const node = {
      id, type: 'logic', label: (bl.name || '').slice(0, 24),
      name: bl.name, file: bl.file, line: bl.line,
      ltype: bl.type, kind: bl.kind,
      _kind: 'logic',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Validation nodes
  asArr(SCAN.validations).slice(0, 60).forEach(v => {
    const id = nid();
    const node = {
      id, type: 'validation', label: ((v.field || v.rule) || 'validate').slice(0, 22),
      file: v.file, line: v.line, rule: v.rule, field: v.field,
      raw: v.raw, vkind: v.kind,
      _kind: 'validation',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Database table nodes
  Object.entries(SCAN.database?.tables || {}).forEach(([name, info]) => {
    if (typeof info !== 'object') return;
    const id = nid();
    const node = {
      id, type: 'table', label: name,
      file: info.file, line: info.line,
      columns: Array.isArray(info.columns) ? info.columns : [],
      _kind: 'table',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // DB query nodes
  asArr(SCAN.database?.queries).slice(0, 40).forEach(q => {
    const id = nid();
    const node = {
      id, type: 'query', label: ((q.table) || 'query').slice(0, 20),
      file: q.file, line: q.line, table: q.table, operation: q.operation,
      _kind: 'query',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Form nodes
  asArr(SCAN.forms).forEach(f => {
    const id = nid();
    const node = {
      id, type: 'form', label: ((f.action || f.type) || '').slice(0, 22),
      file: f.file, line: f.line, action: f.action, ftype: f.type,
      _kind: 'form',
    };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Build edges
  NODES.forEach(n => {
    OUT_EDGES[n.id] = [];
    IN_EDGES[n.id] = [];
  });

  NODES.filter(n => n._kind === 'endpoint').forEach(ep => {
    NODES.filter(n => n._kind === 'logic' && n.file === ep.file).forEach(logic => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: ep.id, target: logic.id, relation: 'calls' });
      OUT_EDGES[ep.id].push(eid);
      IN_EDGES[logic.id].push(eid);
    });
  });

  NODES.filter(n => n._kind === 'logic').forEach(logic => {
    NODES.filter(n => n._kind === 'validation' && n.file === logic.file).forEach(val => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: logic.id, target: val.id, relation: 'validates' });
      OUT_EDGES[logic.id].push(eid);
      IN_EDGES[val.id].push(eid);
    });
  });

  NODES.filter(n => n._kind === 'logic').forEach(logic => {
    NODES.filter(n => n._kind === 'query' && n.file === logic.file).forEach(q => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: logic.id, target: q.id, relation: 'db' });
      OUT_EDGES[logic.id].push(eid);
      IN_EDGES[q.id].push(eid);
    });
  });

  NODES.filter(n => n._kind === 'query').forEach(q => {
    NODES.filter(n => n._kind === 'table' && n.label === q.table).forEach(t => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: q.id, target: t.id, relation: 'db' });
      OUT_EDGES[q.id].push(eid);
      IN_EDGES[t.id].push(eid);
    });
  });

  NODES.filter(n => n._kind === 'form').forEach(f => {
    if (!f.action) return;
    NODES.filter(n => n._kind === 'endpoint' && n.path === f.action).forEach(ep => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: f.id, target: ep.id, relation: 'route' });
      OUT_EDGES[f.id].push(eid);
      IN_EDGES[ep.id].push(eid);
    });
  });

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

// ─── Build user flow graph (business-centric) ───────────────────────────────
function buildUserFlowGraph() {
  let idc = 0;
  function ufid() { return 'uf' + (idc++); }
  function ufeid() { return 'ufe' + (idc++); }

  // Helper: extract menu name from path — group by first meaningful segment
  function menuName(path) {
    const parts = (path || '').split('/').filter(Boolean);
    if (parts.length === 0) return 'root';
    // Skip 'api' / 'v1' / 'v2' prefixes
    let start = 0;
    while (start < parts.length && /^(api|v\d+)$/i.test(parts[start])) start++;
    const seg = parts[start] || parts[0] || 'root';
    // Strip dynamic params: {template} → templates, {certificate} → certificates
    return seg.replace(/^\{(\w+?)s?\}$/, '$1s').replace(/^\{(\w+)\}$/, '$1');
  }

  // 1. Group endpoints by path prefix → Menu nodes
  const menus = {};
  asArr(SCAN.endpoints).forEach(ep => {
    const mname = menuName(ep.path);
    if (!menus[mname]) {
      const id = ufid();
      const node = {
        id, type: 'menu', label: mname,
        _kind: 'menu',
        endpoints: [],
      };
      menus[mname] = node;
      UF_NODES.push(node); UF_NODE_MAP[id] = node;
      UF_OUT_EDGES[id] = [];
      UF_IN_EDGES[id] = [];
    }
    menus[mname].endpoints.push(ep);
  });

  // 2. Create feature nodes (endpoints) → connect menu → feature
  asArr(SCAN.endpoints).forEach(ep => {
    const mname = menuName(ep.path);
    const menu = menus[mname];
    if (!menu) return;

    const id = ufid();
    const node = {
      id, type: 'feature', label: (ep.path || '').slice(0, 30),
      method: ep.method, path: ep.path, file: ep.file, line: ep.line,
      auth: ep.auth, etype: ep.type, menuName: mname,
      _kind: 'feature',
    };
    UF_NODES.push(node); UF_NODE_MAP[id] = node;
    UF_OUT_EDGES[id] = [];
    UF_IN_EDGES[id] = [];

    const eid = ufeid();
    UF_EDGES.push({ id: eid, source: menu.id, target: id, relation: 'has' });
    UF_OUT_EDGES[menu.id].push(eid);
    UF_IN_EDGES[id].push(eid);
  });

  // 3. Forms → connect to features by action path match
  asArr(SCAN.forms).forEach(f => {
    const id = ufid();
    const node = {
      id, type: 'form', label: ((f.action || f.type) || 'form').slice(0, 22),
      file: f.file, line: f.line, action: f.action, ftype: f.type,
      _kind: 'form',
    };
    UF_NODES.push(node); UF_NODE_MAP[id] = node;
    UF_OUT_EDGES[id] = [];
    UF_IN_EDGES[id] = [];

    // Connect form → feature (by action path match)
    UF_NODES.filter(n => n._kind === 'feature' && n.path === f.action).forEach(feat => {
      const eid = ufeid();
      UF_EDGES.push({ id: eid, source: id, target: feat.id, relation: 'submits' });
      UF_OUT_EDGES[id].push(eid);
      UF_IN_EDGES[feat.id].push(eid);
    });
  });

  // 4. Validations → connect to features (by file match)
  asArr(SCAN.validations).slice(0, 80).forEach(v => {
    const id = ufid();
    const node = {
      id, type: 'validation', label: ((v.field || v.rule) || 'validate').slice(0, 22),
      file: v.file, line: v.line, rule: v.rule, field: v.field,
      raw: v.raw, vkind: v.kind,
      _kind: 'validation',
    };
    UF_NODES.push(node); UF_NODE_MAP[id] = node;
    UF_OUT_EDGES[id] = [];
    UF_IN_EDGES[id] = [];

    // Connect feature → validation (by file match)
    UF_NODES.filter(n => n._kind === 'feature' && n.file === v.file).forEach(feat => {
      const eid = ufeid();
      UF_EDGES.push({ id: eid, source: feat.id, target: id, relation: 'validates' });
      UF_OUT_EDGES[feat.id].push(eid);
      UF_IN_EDGES[id].push(eid);
    });
  });

  // 5. DB Tables
  Object.entries(SCAN.database?.tables || {}).forEach(([name, info]) => {
    if (typeof info !== 'object') return;
    const id = ufid();
    const node = {
      id, type: 'table', label: name,
      file: info.file, line: info.line,
      columns: Array.isArray(info.columns) ? info.columns : [],
      _kind: 'table',
    };
    UF_NODES.push(node); UF_NODE_MAP[id] = node;
    UF_OUT_EDGES[id] = [];
    UF_IN_EDGES[id] = [];
  });

  // 6. Queries → connect feature → table directly
  asArr(SCAN.database?.queries).slice(0, 40).forEach(q => {
    UF_NODES.filter(n => n._kind === 'feature' && n.file === q.file).forEach(feat => {
      const tbl = UF_NODES.find(n => n._kind === 'table' && n.label === q.table);
      if (tbl) {
        const eid = ufeid();
        // Avoid duplicate edges
        const exists = UF_EDGES.some(e => e.source === feat.id && e.target === tbl.id);
        if (!exists) {
          UF_EDGES.push({ id: eid, source: feat.id, target: tbl.id, relation: 'queries' });
          UF_OUT_EDGES[feat.id].push(eid);
          UF_IN_EDGES[tbl.id].push(eid);
        }
      }
    });
  });

  // 7. DB relations (FK → table)
  (SCAN.database?.relations || []).forEach(rel => {
    const fromTable = UF_NODES.find(n => n._kind === 'table' && n.label === rel.from_table);
    const toTable = UF_NODES.find(n => n._kind === 'table' && n.label === rel.to_table);
    if (fromTable && toTable) {
      const eid = ufeid();
      UF_EDGES.push({ id: eid, source: fromTable.id, target: toTable.id, relation: 'db' });
      UF_OUT_EDGES[fromTable.id].push(eid);
      UF_IN_EDGES[toTable.id].push(eid);
    }
  });
}

// ─── Colors & labels ────────────────────────────────────────────────────────
const TYPE_COLORS = {
  endpoint: '#58a6ff',
  feature: '#58a6ff',
  logic: '#3fb950',
  validation: '#8957e5',
  table: '#d29922',
  query: '#e3b341',
  form: '#f0883e',
  menu: '#f778ba',
};

const TYPE_LABELS = {
  endpoint: 'API',
  feature: 'API',
  logic: 'FN',
  validation: 'VAL',
  table: 'TBL',
  query: 'QRY',
  form: 'FRM',
  menu: 'MENU',
};

const TYPE_ICONS = {
  endpoint: '🔵', feature: '🔵', logic: '🟢', validation: '🟣',
  table: '🟡', query: '🟠', form: '🟠', menu: '🟪',
};

// ─── Layout config ──────────────────────────────────────────────────────────
const NODE_R = 8;
let currentView = 'userflow';
let collapsedNodes = new Set();
let selectedNode = null;
let filteredNodes = [];
let filteredEdges = [];
let simulation = null;
let zoomBehavior = null;

// ─── View filtering ─────────────────────────────────────────────────────────
function getViewNodes() {
  const nodes = filteredNodes;
  if (currentView === 'db') {
    return nodes.filter(n => n._kind === 'table' || n._kind === 'query');
  } else if (currentView === 'validation') {
    return nodes.filter(n => n._kind === 'endpoint' || n._kind === 'feature' || n._kind === 'logic' || n._kind === 'validation');
  } else if (currentView === 'userflow') {
    return nodes.filter(n => n._kind === 'menu' || n._kind === 'feature' || n._kind === 'form' || n._kind === 'validation' || n._kind === 'table');
  }
  // flow = all code graph
  return nodes;
}

function getViewEdges(nodeIds) {
  const idSet = new Set(nodeIds.map(n => n.id));
  return filteredEdges.filter(e => idSet.has(e.source) && idSet.has(e.target));
}

// ─── Node radius by type ────────────────────────────────────────────────────
function nodeRadius(d) {
  const connections = ((aOutEdges[d.id] || []).length + (aInEdges[d.id] || []).length);
  if (d._kind === 'menu') return 14 + Math.min(8, connections / 4);
  if (d._kind === 'feature' || d._kind === 'table') return 10 + Math.min(6, connections / 4);
  return NODE_R + Math.min(6, connections / 3);
}

// ─── Render: D3 Force-Directed ──────────────────────────────────────────────
function render() {
  const svgEl = document.getElementById('canvas');
  const width = svgEl.clientWidth;
  const height = svgEl.clientHeight;

  // Clear everything
  d3.select('#canvas').selectAll('*').remove();
  if (simulation) { simulation.stop(); simulation = null; }

  const svg = d3.select('#canvas');
  const defs = svg.append('defs');

  // Arrowhead markers
  const edgeColors = [
    ['arrow-calls', '#3fb950'], ['arrow-route', '#58a6ff'],
    ['arrow-db', '#d29922'], ['arrow-validates', '#8957e5'],
    ['arrow-contains', '#484f58'], ['arrow-queries', '#d29922'],
    ['arrow-submits', '#f0883e'], ['arrow-has', '#f778ba'],
    ['arrow-default', '#58a6ff'],
  ];
  edgeColors.forEach(([name, color]) => {
    defs.append('marker').attr('id', name).attr('viewBox', '0 -5 10 10')
      .attr('refX', 12).attr('refY', 0).attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto-start-reverse')
      .append('path').attr('d', 'M0,-5 L10,0 L0,5').attr('fill', color);
  });

  // Root group for zoom/pan
  const root = svg.append('g').attr('class', 'zoom-root');

  // Zoom behavior
  zoomBehavior = d3.zoom().scaleExtent([0.05, 8])
    .filter(e => !e.target.closest('.node-box') || e.type !== 'dblclick')
    .on('zoom', (e) => root.attr('transform', e.transform));
  svg.call(zoomBehavior);
  svg.on('dblclick.zoom', null);

  const edgeLayer = root.append('g').attr('class', 'edges');
  const nodeLayer = root.append('g').attr('class', 'nodes');

  // Get visible nodes (respect collapse)
  const viewNodes = getViewNodes();
  const visibleNodes = viewNodes.filter(n => {
    if (collapsedNodes.has(n.id)) return true;
    const parents = (aInEdges[n.id] || []).map(eid => {
      const e = aEdges.find(x => x.id === eid);
      return e ? e.source : null;
    });
    return !parents.some(p => collapsedNodes.has(p));
  });
  const visibleIds = new Set(visibleNodes.map(n => n.id));
  const visibleEdges = getViewEdges(visibleNodes).filter(e =>
    visibleIds.has(e.source) && visibleIds.has(e.target) &&
    !collapsedNodes.has(e.source) && !collapsedNodes.has(e.target)
  );

  // Build D3-compatible copies
  const simNodes = visibleNodes.map(n => ({ ...n }));
  const simEdges = visibleEdges.map(e => ({ ...e }));

  // Edges
  const link = edgeLayer.selectAll('path')
    .data(simEdges)
    .enter().append('path')
      .attr('class', d => `edge ${d.relation}`)
      .attr('data-source', d => d.source)
      .attr('data-target', d => d.target)
      .attr('marker-end', d => `url(#arrow-${d.relation || 'default'})`)
      .style('fill', 'none')
      .style('stroke-opacity', 0.4);

  // Nodes — circle + label
  const nodeG = nodeLayer.selectAll('g.node-box')
    .data(simNodes, d => d.id)
    .enter().append('g')
      .attr('class', 'node-box')
      .style('cursor', 'pointer')
      .on('click', (ev, d) => { ev.stopPropagation(); selectNode(d); })
      .on('dblclick', function(ev, d) {
        ev.stopPropagation();
        if ((aOutEdges[d.id] || []).length > 0) toggleCollapse(d.id);
      })
      .on('mouseover', function(ev, d) {
        d3.select(this).select('circle').attr('stroke-width', 3);
        showTooltip(ev, d);
      })
      .on('mouseout', function() {
        d3.select(this).select('circle').attr('stroke-width', 1.5);
        hideTooltip();
      });

  // Circle
  nodeG.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => (TYPE_COLORS[d._kind] || '#484f58') + '33')
    .attr('stroke', d => TYPE_COLORS[d._kind] || '#484f58')
    .attr('stroke-width', 1.5);

  // Label — bigger for menu nodes
  nodeG.append('text')
    .attr('class', 'node-label-force')
    .attr('x', d => nodeRadius(d) + 4)
    .attr('y', d => d._kind === 'menu' ? 5 : 3)
    .attr('text-anchor', 'start')
    .style('font-size', d => d._kind === 'menu' ? '13px' : '10px')
    .style('font-weight', d => d._kind === 'menu' ? '700' : '400')
    .style('fill', d => d._kind === 'menu' ? '#f778ba' : '#c9d1d9')
    .style('pointer-events', 'none')
    .text(d => {
      const lbl = d.label || d.name || d.id;
      return lbl.length > 28 ? lbl.slice(0, 27) + '…' : lbl;
    });

  // Type badge
  nodeG.append('text')
    .attr('class', 'type-badge-force')
    .attr('x', 0).attr('y', d => -nodeRadius(d) - 4)
    .attr('text-anchor', 'middle')
    .style('font-size', '8px')
    .style('fill', d => TYPE_COLORS[d._kind] || '#484f58')
    .style('pointer-events', 'none')
    .style('font-weight', '600')
    .text(d => TYPE_LABELS[d._kind] || '');

  // Drag
  const drag = d3.drag()
    .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
    .on('end',   (ev, d) => { if (!ev.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; });
  nodeG.call(drag);

  // Force simulation — tuned per view
  const chargeStrength = currentView === 'userflow' ? -120 : -80;
  const linkDistance = currentView === 'userflow' ? 70 + Math.random() * 50 : 50 + Math.random() * 40;

  simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(d => d.id).distance(linkDistance).strength(0.15))
    .force('charge', d3.forceManyBody().strength(chargeStrength))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 14))
    .force('x', d3.forceX(width / 2).strength(0.03))
    .force('y', d3.forceY(height / 2).strength(0.03));

  simulation.on('tick', () => {
    link
      .attr('d', d => {
        const sx = d.source.x, sy = d.source.y;
        const tx = d.target.x, ty = d.target.y;
        const dx = tx - sx, dy = ty - sy;
        const dr = Math.sqrt(dx*dx + dy*dy) * 1.5;
        return `M${sx},${sy}A${dr},${dr} 0 0,1 ${tx},${ty}`;
      });

    nodeG.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  // Stats
  document.getElementById('stats').textContent =
    `${visibleNodes.length} nodes · ${visibleEdges.length} edges · ${collapsedNodes.size} collapsed`;
}

// ─── Selection + highlight ──────────────────────────────────────────────────
function selectNode(node) {
  selectedNode = node;
  d3.selectAll('.node-circle').classed('selected', false);
  d3.selectAll('.node-box').filter(d => d && d.id === node.id).select('circle').classed('selected', true);

  // Highlight connected
  const connected = new Set([node.id]);
  (aOutEdges[node.id] || []).forEach(eid => {
    const e = aEdges.find(e => e.id === eid);
    if (e) connected.add(e.target);
  });
  (aInEdges[node.id] || []).forEach(eid => {
    const e = aEdges.find(e => e.id === eid);
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
  d3.selectAll('.node-circle').classed('selected', false);
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

  // Menu details
  if (node._kind === 'menu') {
    const features = (aOutEdges[node.id] || []).map(eid => {
      const e = aEdges.find(x => x.id === eid);
      return e ? aNodeMap[e.target] : null;
    }).filter(Boolean);
    html += `<div class="section">
      <h4>Features (${features.length})</h4>`;
    features.forEach(f => {
      html += `<div class="link-item" onclick="selectById('${f.id}')">→ ${f.label} [${f.method || ''}]</div>`;
    });
    html += `</div>`;
  }

  // Feature/endpoint details
  if (node._kind === 'feature' || node._kind === 'endpoint') {
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
    if (node.etype) {
      html += `<div class="section">
        <h4>Framework</h4>
        <div class="row">${node.etype}</div>
      </div>`;
    }
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
  const outE = (aOutEdges[node.id] || []).map(eid => aEdges.find(e => e.id === eid)).filter(Boolean);
  const inE = (aInEdges[node.id] || []).map(eid => aEdges.find(e => e.id === eid)).filter(Boolean);

  if (outE.length > 0) {
    html += `<div class="section">
      <h4>Calls / Outgoing (${outE.length})</h4>`;
    outE.slice(0, 20).forEach(e => {
      const target = aNodeMap[e.target];
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
      const source = aNodeMap[e.source];
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
  const node = aNodeMap[id];
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
  inner += `<div style="color:#8b949e">↳ ${(aOutEdges[node.id]||[]).length} out, ${(aInEdges[node.id]||[]).length} in</div>`;
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

  filteredNodes.forEach(node => {
    const div = document.createElement('div');
    div.className = 'list-item';
    div.innerHTML = `<span class="icon">${TYPE_ICONS[node._kind] || '⚫'}</span>
      <span class="name">${node.label}</span>
      <span class="count">${(aOutEdges[node.id]||[]).length}</span>`;
    div.onclick = () => selectById(node.id);
    list.appendChild(div);
  });
}

function filterNodes(q) {
  if (!q) {
    filteredNodes = [...aNodes];
    filteredEdges = [...aEdges];
  } else {
    const ql = q.toLowerCase();
    filteredNodes = aNodes.filter(n =>
      (n.label || '').toLowerCase().includes(ql) ||
      (n.path || '').toLowerCase().includes(ql) ||
      (n.name || '').toLowerCase().includes(ql) ||
      (n.file || '').toLowerCase().includes(ql)
    );
    const ids = new Set(filteredNodes.map(n => n.id));
    filteredEdges = aEdges.filter(e => ids.has(e.source) && ids.has(e.target));
  }
  render();
  renderSidebar();
}

// ─── Legend ──────────────────────────────────────────────────────────────────
function updateLegend() {
  const el = document.getElementById('legend');
  let html = '';

  if (currentView === 'userflow') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#f778ba;background:#f778ba33"></div> Menu — Group fitur (Profile, POS, dll)</div>
      <div class="row"><div class="dot" style="border-color:#58a6ff;background:#58a6ff33"></div> Feature/API — Endpoint user akses</div>
      <div class="row"><div class="dot" style="border-color:#f0883e;background:#f0883e33"></div> Form — Form yang user isi</div>
      <div class="row"><div class="dot" style="border-color:#8957e5;background:#8957e533"></div> Validation — Aturan validasi field</div>
      <div class="row"><div class="dot" style="border-color:#d29922;background:#d2992233"></div> DB Table — Table database</div>
      <div class="sep"></div>
      <h5>Edge Types</h5>
      <div class="row"><div class="line" style="background:#f778ba"></div> has — Menu memiliki feature</div>
      <div class="row"><div class="line" style="background:#f0883e"></div> submits — Form submit ke API</div>
      <div class="row"><div class="line" style="background:#8957e5"></div> validates — API validasi field</div>
      <div class="row"><div class="line" style="background:#d29922"></div> queries — API akses table</div>`;
  } else if (currentView === 'flow') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#58a6ff;background:#58a6ff33"></div> API — Endpoint</div>
      <div class="row"><div class="dot" style="border-color:#3fb950;background:#3fb95033"></div> Function — Business logic</div>
      <div class="row"><div class="dot" style="border-color:#8957e5;background:#8957e533"></div> Validation — Aturan validasi</div>
      <div class="row"><div class="dot" style="border-color:#d29922;background:#d2992233"></div> Table — Database table</div>
      <div class="row"><div class="dot" style="border-color:#e3b341;background:#e3b34133"></div> Query — DB query</div>
      <div class="row"><div class="dot" style="border-color:#f0883e;background:#f0883e33"></div> Form — HTML form</div>
      <div class="sep"></div>
      <h5>Edge Types</h5>
      <div class="row"><div class="line" style="background:#3fb950"></div> calls — Endpoint → function</div>
      <div class="row"><div class="line" style="background:#8957e5"></div> validates — Function → validation</div>
      <div class="row"><div class="line" style="background:#d29922"></div> db — Query → table</div>
      <div class="row"><div class="line" style="background:#58a6ff"></div> route — Form → endpoint</div>`;
  } else if (currentView === 'db') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#d29922;background:#d2992233"></div> Table — Database table</div>
      <div class="row"><div class="dot" style="border-color:#e3b341;background:#e3b34133"></div> Query — DB query</div>
      <div class="sep"></div>
      <h5>Edge Types</h5>
      <div class="row"><div class="line" style="background:#d29922"></div> db — Query/Table relation</div>`;
  } else if (currentView === 'validation') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#58a6ff;background:#58a6ff33"></div> API — Endpoint</div>
      <div class="row"><div class="dot" style="border-color:#3fb950;background:#3fb95033"></div> Function — Business logic</div>
      <div class="row"><div class="dot" style="border-color:#8957e5;background:#8957e533"></div> Validation — Aturan validasi</div>
      <div class="sep"></div>
      <h5>Edge Types</h5>
      <div class="row"><div class="line" style="background:#3fb950"></div> calls — Endpoint → function</div>
      <div class="row"><div class="line" style="background:#8957e5"></div> validates — Function → validation</div>`;
  }

  el.innerHTML = html;
}

// ─── View switching ─────────────────────────────────────────────────────────
function setView(view) {
  currentView = view;
  collapsedNodes.clear();
  clearHighlight();
  selectedNode = null;
  document.getElementById('detail').classList.remove('visible');

  // Swap active graph
  if (view === 'userflow') {
    aNodes = UF_NODES; aEdges = UF_EDGES; aNodeMap = UF_NODE_MAP;
    aOutEdges = UF_OUT_EDGES; aInEdges = UF_IN_EDGES;
  } else {
    aNodes = NODES; aEdges = EDGES; aNodeMap = NODE_MAP;
    aOutEdges = OUT_EDGES; aInEdges = IN_EDGES;
  }

  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === view));
  filteredNodes = [...aNodes];
  filteredEdges = [...aEdges];
  render();
  renderSidebar();
  updateLegend();
}

// ─── Init ────────────────────────────────────────────────────────────────────
buildGraph();
buildUserFlowGraph();

// Default to user flow view
aNodes = UF_NODES; aEdges = UF_EDGES; aNodeMap = UF_NODE_MAP;
aOutEdges = UF_OUT_EDGES; aInEdges = UF_IN_EDGES;
filteredNodes = [...aNodes];
filteredEdges = [...aEdges];
render();
renderSidebar();
updateLegend();

// Click empty canvas → deselect
document.getElementById('canvas-wrap').addEventListener('click', (e) => {
  if (e.target.tagName === 'svg' || (e.target.tagName === 'rect' && !e.target.classList.contains('node-circle'))) {
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