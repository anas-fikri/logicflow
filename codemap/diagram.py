"""CodeMap Diagram — Interactive HTML/SVG diagram builder.

Features:
- Business Flow: horizontal tree/swimlane with cards (user journey)
- Code Flow: D3 force-directed graph (code structure overview)
- Database: tables and queries
- Validasi: endpoint → validation rules
- Click node → detail panel with fields, validations, DB relations
- Dynamic legend per view
- Dark theme, self-contained HTML (D3 inlined)
"""

import json
from pathlib import Path


D3_PATH = Path(__file__).parent.parent / "vendor" / "d3.v7.min.js"


def load_d3():
    if D3_PATH.exists():
        return D3_PATH.read_text()
    return ""


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
#sidebar { width: 260px; background: #161b22; border-right: 1px solid #30363d; display: flex; flex-direction: column; }
#sidebar h2 { padding: 16px; font-size: 14px; color: #58a6ff; border-bottom: 1px solid #30363d; }
#tabs { display: flex; padding: 8px; gap: 4px; flex-wrap: wrap; border-bottom: 1px solid #30363d; }
.tab { padding: 6px 12px; border: 1px solid #30363d; border-radius: 4px; background: transparent; color: #8b949e; cursor: pointer; font-size: 12px; transition: all 0.15s; }
.tab:hover { color: #c9d1d9; border-color: #58a6ff; }
.tab.active { background: #1f6feb; color: #fff; border-color: #1f6feb; }
#filter-box { padding: 8px; border-bottom: 1px solid #30363d; }
#filter-box input { width: 100%; padding: 6px 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 4px; color: #c9d1d9; font-size: 12px; }
#filter-box input:focus { outline: none; border-color: #58a6ff; }
#node-list { flex: 1; overflow-y: auto; }
.list-item { padding: 6px 16px; border-bottom: 1px solid #21262d; cursor: pointer; font-size: 12px; display: flex; align-items: center; gap: 8px; transition: background 0.1s; }
.list-item:hover { background: #21262d; }
.list-item.active { background: #1f6feb33; border-left: 3px solid #58a6ff; }
.list-item .icon { font-size: 14px; }
.list-item .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.list-item .badge { font-size: 9px; color: #484f58; }
#stats { padding: 12px 16px; border-top: 1px solid #30363d; font-size: 11px; color: #484f58; }

/* Canvas */
#canvas-wrap { flex: 1; position: relative; overflow: hidden; }
#canvas { width: 100%; height: 100%; cursor: grab; }
#canvas:active { cursor: grabbing; }

/* Tooltip */
#tooltip { position: fixed; background: #1f2937; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; font-size: 12px; max-width: 320px; z-index: 1000; pointer-events: none; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }

/* Detail panel */
#detail { position: absolute; right: 0; top: 0; width: 420px; height: 100%; background: #161b22; border-left: 1px solid #30363d; overflow-y: auto; transform: translateX(100%); transition: transform 0.25s ease; z-index: 100; }
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
#detail .section .tag.auth { background: #f8514933; color: #f85149; }
#detail .section .tag.public { background: #23863633; color: #3fb950; }
#detail .field-list { list-style: none; }
#detail .field-list li { padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 12px; display: flex; justify-content: space-between; }
#detail .field-list .fname { color: #58a6ff; font-family: monospace; }
#detail .field-list .ftype { color: #8b949e; font-family: monospace; }
#detail .field-list .fflags { color: #d29922; font-size: 10px; }
.link-item { padding: 6px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; color: #58a6ff; transition: background 0.1s; }
.link-item:hover { background: #21262d; }

/* SVG: force-directed edges */
.edge { fill: none; stroke: #30363d; stroke-width: 1.5; transition: stroke-opacity 0.15s, stroke-width 0.15s; }
.edge.calls { stroke: #3fb950; }
.edge.route { stroke: #58a6ff; }
.edge.db { stroke: #d29922; }
.edge.validates { stroke: #8957e5; }
.edge.queries { stroke: #d29922; }
.edge.submits { stroke: #f0883e; }
.edge.has { stroke: #f778ba; }
.edge.highlighted { stroke-opacity: 1 !important; stroke-width: 2.5 !important; }
.edge.dimmed { stroke-opacity: 0.05 !important; }
.node-circle { stroke-width: 1.5; transition: stroke 0.15s, opacity 0.15s; }
.node-circle.selected { stroke: #f0e040; stroke-width: 3; }
.node-box.dimmed { opacity: 0.15; }

/* SVG: tree links */
.tree-link { fill: none; stroke: #30363d; stroke-width: 1.5; opacity: 0.5; transition: opacity 0.15s; }
.tree-link.menu { stroke: #f778ba; }
.tree-link.feature { stroke: #58a6ff; }
.tree-link.validation { stroke: #8957e5; }
.tree-link.table { stroke: #d29922; }
.tree-link.highlighted { opacity: 1; stroke-width: 2.5; }
.lane-header { fill: #8b949e; font-size: 11px; font-weight: 600; text-anchor: middle; text-transform: uppercase; letter-spacing: 1px; }

/* Cards (foreignObject) */
.card { display: flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 6px; background: #161b22; border: 1px solid #30363d; border-left-width: 3px; font-size: 12px; cursor: pointer; white-space: nowrap; transition: all 0.15s; box-shadow: 0 2px 4px rgba(0,0,0,0.3); user-select: none; }
.card:hover { background: #21262d; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
.card.selected { background: #1f6feb33; border-color: #f0e040; box-shadow: 0 0 0 1px #f0e040; }
.card-icon { font-size: 14px; flex-shrink: 0; }
.card-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-method { font-size: 9px; padding: 1px 6px; border-radius: 3px; font-weight: 600; flex-shrink: 0; }
.card-count { font-size: 10px; color: #484f58; flex-shrink: 0; }
.card-expand { font-size: 10px; color: #484f58; flex-shrink: 0; }
.card.menu { border-left-color: #f778ba; }
.card.feature { border-left-color: #58a6ff; }
.card.validation { border-left-color: #8957e5; }
.card.table { border-left-color: #d29922; }
.card.root { border-left-color: #3fb950; }

/* Legend */
.legend { position: absolute; bottom: 12px; left: 12px; background: #161b22ee; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-size: 11px; max-width: 280px; }
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
      <button class="tab active" data-view="business" onclick="setView('business')">Business Flow</button>
      <button class="tab" data-view="flow" onclick="setView('flow')">Code Flow</button>
      <button class="tab" data-view="db" onclick="setView('db')">Database</button>
      <button class="tab" data-view="validation" onclick="setView('validation')">Validasi</button>
    </div>
    <div id="filter-box">
      <input type="text" id="search" placeholder="Cari..." oninput="filterNodes(this.value)">
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

const SCAN = __SCAN_DATA__;

// ─── Code graph (for Code Flow / DB / Validasi tabs) ────────────────────────
const NODES = [], EDGES = [], NODE_MAP = {}, OUT_EDGES = {}, IN_EDGES = {};

// ─── User flow graph (for Code Flow tab) ────────────────────────────────────
const UF_NODES = [], UF_EDGES = [], UF_NODE_MAP = {}, UF_OUT_EDGES = {}, UF_IN_EDGES = {};

// ─── Business tree (for Business Flow tab) ──────────────────────────────────
let businessRoot = null; // d3.hierarchy
let businessTreeData = null;

// ─── Active graph pointers ─────────────────────────────────────────────────
let aNodes, aEdges, aNodeMap, aOutEdges, aInEdges;

// ─── State ─────────────────────────────────────────────────────────────────
let currentView = 'business';
let selectedNode = null;
let simulation = null;
let zoomBehavior = null;
let searchQuery = '';

function asArr(v) { return Array.isArray(v) ? v : (v ? Object.values(v) : []); }

// ─── Human-readable labels ─────────────────────────────────────────────────
const HUMAN_LABELS = {
  'auth': 'Autentikasi', 'certificates': 'Sertifikat', 'templates': 'Template',
  'events': 'Event/Training', 'participants': 'Peserta', 'dashboard': 'Dashboard',
  'settings': 'Pengaturan', 'health': 'System Health', 'root': 'Home',
  'users': 'Manajemen User', 'profile': 'Profil', 'mail': 'Mail',
  'orders': 'Pesanan', 'products': 'Produk', 'reports': 'Laporan',
  'transactions': 'Transaksi', 'invoices': 'Invoice', 'payments': 'Pembayaran',
};

const HUMAN_METHODS = {
  'get': 'Lihat', 'post': 'Tambah', 'put': 'Edit', 'patch': 'Edit', 'delete': 'Hapus', 'any': 'Aksi',
};

const KNOWN_ACTIONS = {
  'login': 'Login', 'logout': 'Logout', 'me': 'Profil Saya',
  'change-password': 'Ubah Password', 'register': 'Daftar',
  'dashboard': 'Dashboard', 'bulk': 'Bulk Aksi', 'import-excel': 'Import Excel',
  'bulk-import': 'Import Massal', 'export': 'Export', 'duplicate': 'Duplikat',
  'thumbnail': 'Thumbnail', 'parse-rundown-excel': 'Parse Rundown',
  'rundown': 'Rundown', 'health': 'System Health', 'settings': 'Pengaturan',
};

function humanLabel(path) {
  if (!path) return '—';
  const key = path.toLowerCase().replace(/^\{(\w+?)s?\}$/, '$1s').replace(/^\{(\w+)\}$/, '$1');
  return HUMAN_LABELS[key] || HUMAN_LABELS[path] || key.charAt(0).toUpperCase() + key.slice(1);
}

function humanAction(ep) {
  const method = (ep.method || 'get').toLowerCase();
  const path = ep.path || '';
  const parts = path.split('/').filter(Boolean);
  const last = parts[parts.length - 1] || path;
  if (KNOWN_ACTIONS[last]) return KNOWN_ACTIONS[last];
  if (/^\{.+\}$/.test(last)) {
    return { get: 'Lihat Detail', put: 'Edit', patch: 'Edit', delete: 'Hapus', post: 'Aksi' }[method] || 'Aksi';
  }
  const verb = HUMAN_METHODS[method] || 'Aksi';
  return verb + ' ' + last.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ─── Colors & icons ────────────────────────────────────────────────────────
const TYPE_COLORS = {
  root: '#3fb950', menu: '#f778ba', feature: '#58a6ff',
  validation: '#8957e5', table: '#d29922', form: '#f0883e',
  endpoint: '#58a6ff', logic: '#3fb950', query: '#e3b341',
};
const TYPE_ICONS = {
  root: '🏠', menu: '📋', feature: '🔵', endpoint: '🔵',
  validation: '🟣', table: '🟡', form: '🟠', logic: '🟢', query: '🟠',
};
const TYPE_LABELS = {
  root: 'APP', menu: 'MENU', feature: 'API', endpoint: 'API',
  validation: 'VAL', table: 'TBL', form: 'FRM', logic: 'FN', query: 'QRY',
};

const NODE_R = 8;

// ─── Build code graph (existing, for Code Flow / DB / Validasi) ──────────────
function buildGraph() {
  let idc = 0;
  function nid() { return 'n' + (idc++); }
  asArr(SCAN.endpoints).forEach(ep => {
    const id = nid();
    NODES.push({ id, type: 'endpoint', label: (ep.path || '').slice(0, 28),
      method: ep.method, path: ep.path, file: ep.file, line: ep.line,
      auth: ep.auth, etype: ep.type, _kind: 'endpoint' });
    NODE_MAP[id] = NODES[NODES.length - 1];
  });
  asArr(SCAN.business_logic).forEach(bl => {
    const id = nid();
    NODES.push({ id, type: 'logic', label: (bl.name || '').slice(0, 24),
      name: bl.name, file: bl.file, line: bl.line, ltype: bl.type, kind: bl.kind, _kind: 'logic' });
    NODE_MAP[id] = NODES[NODES.length - 1];
  });
  asArr(SCAN.validations).slice(0, 60).forEach(v => {
    const id = nid();
    NODES.push({ id, type: 'validation', label: ((v.field || v.rule) || 'validate').slice(0, 22),
      file: v.file, line: v.line, rule: v.rule, field: v.field, raw: v.raw, vkind: v.kind, _kind: 'validation' });
    NODE_MAP[id] = NODES[NODES.length - 1];
  });
  Object.entries(SCAN.database?.tables || {}).forEach(([name, info]) => {
    if (typeof info !== 'object') return;
    const id = nid();
    NODES.push({ id, type: 'table', label: name, file: info.file, line: info.line,
      columns: Array.isArray(info.columns) ? info.columns : [], _kind: 'table' });
    NODE_MAP[id] = NODES[NODES.length - 1];
  });
  asArr(SCAN.database?.queries).slice(0, 40).forEach(q => {
    const id = nid();
    NODES.push({ id, type: 'query', label: ((q.table) || 'query').slice(0, 20),
      file: q.file, line: q.line, table: q.table, operation: q.operation, _kind: 'query' });
    NODE_MAP[id] = NODES[NODES.length - 1];
  });
  asArr(SCAN.forms).forEach(f => {
    const id = nid();
    NODES.push({ id, type: 'form', label: ((f.action || f.type) || '').slice(0, 22),
      file: f.file, line: f.line, action: f.action, ftype: f.type, _kind: 'form' });
    NODE_MAP[id] = NODES[NODES.length - 1];
  });
  NODES.forEach(n => { OUT_EDGES[n.id] = []; IN_EDGES[n.id] = []; });
  NODES.filter(n => n._kind === 'endpoint').forEach(ep => {
    NODES.filter(n => n._kind === 'logic' && n.file === ep.file).forEach(logic => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: ep.id, target: logic.id, relation: 'calls' });
      OUT_EDGES[ep.id].push(eid); IN_EDGES[logic.id].push(eid);
    });
  });
  NODES.filter(n => n._kind === 'logic').forEach(logic => {
    NODES.filter(n => n._kind === 'validation' && n.file === logic.file).forEach(val => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: logic.id, target: val.id, relation: 'validates' });
      OUT_EDGES[logic.id].push(eid); IN_EDGES[val.id].push(eid);
    });
  });
  NODES.filter(n => n._kind === 'logic').forEach(logic => {
    NODES.filter(n => n._kind === 'query' && n.file === logic.file).forEach(q => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: logic.id, target: q.id, relation: 'db' });
      OUT_EDGES[logic.id].push(eid); IN_EDGES[q.id].push(eid);
    });
  });
  NODES.filter(n => n._kind === 'query').forEach(q => {
    NODES.filter(n => n._kind === 'table' && n.label === q.table).forEach(t => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: q.id, target: t.id, relation: 'db' });
      OUT_EDGES[q.id].push(eid); IN_EDGES[t.id].push(eid);
    });
  });
  NODES.filter(n => n._kind === 'form').forEach(f => {
    if (!f.action) return;
    NODES.filter(n => n._kind === 'endpoint' && n.path === f.action).forEach(ep => {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: f.id, target: ep.id, relation: 'route' });
      OUT_EDGES[f.id].push(eid); IN_EDGES[ep.id].push(eid);
    });
  });
  (SCAN.database?.relations || []).forEach(rel => {
    const fromTable = NODES.find(n => n._kind === 'table' && n.label === rel.from_table);
    const toTable = NODES.find(n => n._kind === 'table' && n.label === rel.to_table);
    if (fromTable && toTable) {
      const eid = 'e' + idc++;
      EDGES.push({ id: eid, source: fromTable.id, target: toTable.id, relation: 'db' });
      OUT_EDGES[fromTable.id].push(eid); IN_EDGES[toTable.id].push(eid);
    }
  });
}

// ─── Build user flow graph (for Code Flow tab) ──────────────────────────────
function buildUserFlowGraph() {
  let idc = 0;
  function ufid() { return 'uf' + (idc++); }
  function ufeid() { return 'ufe' + (idc++); }
  function menuName(path) {
    const parts = (path || '').split('/').filter(Boolean);
    if (parts.length === 0) return 'root';
    let start = 0;
    while (start < parts.length && /^(api|v\d+)$/i.test(parts[start])) start++;
    const seg = parts[start] || parts[0] || 'root';
    return seg.replace(/^\{(\w+?)s?\}$/, '$1s').replace(/^\{(\w+)\}$/, '$1');
  }
  const menus = {};
  asArr(SCAN.endpoints).forEach(ep => {
    const mname = menuName(ep.path);
    if (!menus[mname]) {
      const id = ufid();
      const node = { id, type: 'menu', label: humanLabel(mname), _kind: 'menu', endpoints: [] };
      menus[mname] = node; UF_NODES.push(node); UF_NODE_MAP[id] = node;
      UF_OUT_EDGES[id] = []; UF_IN_EDGES[id] = [];
    }
    menus[mname].endpoints.push(ep);
  });
  asArr(SCAN.endpoints).forEach(ep => {
    const mname = menuName(ep.path);
    const menu = menus[mname]; if (!menu) return;
    const id = ufid();
    const node = { id, type: 'feature', label: humanAction(ep),
      method: ep.method, path: ep.path, file: ep.file, line: ep.line,
      auth: ep.auth, etype: ep.type, menuName: mname, _kind: 'feature' };
    UF_NODES.push(node); UF_NODE_MAP[id] = node;
    UF_OUT_EDGES[id] = []; UF_IN_EDGES[id] = [];
    const eid = ufeid();
    UF_EDGES.push({ id: eid, source: menu.id, target: id, relation: 'has' });
    UF_OUT_EDGES[menu.id].push(eid); UF_IN_EDGES[id].push(eid);
  });
  asArr(SCAN.forms).forEach(f => {
    const id = ufid();
    const node = { id, type: 'form', label: ((f.action || f.type) || 'form').slice(0, 22),
      file: f.file, line: f.line, action: f.action, ftype: f.type, _kind: 'form' };
    UF_NODES.push(node); UF_NODE_MAP[id] = node; UF_OUT_EDGES[id] = []; UF_IN_EDGES[id] = [];
    UF_NODES.filter(n => n._kind === 'feature' && n.path === f.action).forEach(feat => {
      const eid = ufeid();
      UF_EDGES.push({ id: eid, source: id, target: feat.id, relation: 'submits' });
      UF_OUT_EDGES[id].push(eid); UF_IN_EDGES[feat.id].push(eid);
    });
  });
  asArr(SCAN.validations).slice(0, 80).forEach(v => {
    const id = ufid();
    const node = { id, type: 'validation', label: ((v.field || v.rule) || 'validate').slice(0, 22),
      file: v.file, line: v.line, rule: v.rule, field: v.field, raw: v.raw, vkind: v.kind, _kind: 'validation' };
    UF_NODES.push(node); UF_NODE_MAP[id] = node; UF_OUT_EDGES[id] = []; UF_IN_EDGES[id] = [];
    UF_NODES.filter(n => n._kind === 'feature' && n.file === v.file).forEach(feat => {
      const eid = ufeid();
      UF_EDGES.push({ id: eid, source: feat.id, target: id, relation: 'validates' });
      UF_OUT_EDGES[feat.id].push(eid); UF_IN_EDGES[id].push(eid);
    });
  });
  Object.entries(SCAN.database?.tables || {}).forEach(([name, info]) => {
    if (typeof info !== 'object') return;
    const id = ufid();
    const node = { id, type: 'table', label: name, file: info.file, line: info.line,
      columns: Array.isArray(info.columns) ? info.columns : [], _kind: 'table' };
    UF_NODES.push(node); UF_NODE_MAP[id] = node; UF_OUT_EDGES[id] = []; UF_IN_EDGES[id] = [];
  });
  asArr(SCAN.database?.queries).slice(0, 40).forEach(q => {
    UF_NODES.filter(n => n._kind === 'feature' && n.file === q.file).forEach(feat => {
      const tbl = UF_NODES.find(n => n._kind === 'table' && n.label === q.table);
      if (tbl) {
        const exists = UF_EDGES.some(e => e.source === feat.id && e.target === tbl.id);
        if (!exists) {
          const eid = ufeid();
          UF_EDGES.push({ id: eid, source: feat.id, target: tbl.id, relation: 'queries' });
          UF_OUT_EDGES[feat.id].push(eid); UF_IN_EDGES[tbl.id].push(eid);
        }
      }
    });
  });
  (SCAN.database?.relations || []).forEach(rel => {
    const fromTable = UF_NODES.find(n => n._kind === 'table' && n.label === rel.from_table);
    const toTable = UF_NODES.find(n => n._kind === 'table' && n.label === rel.to_table);
    if (fromTable && toTable) {
      const eid = ufeid();
      UF_EDGES.push({ id: eid, source: fromTable.id, target: toTable.id, relation: 'db' });
      UF_OUT_EDGES[fromTable.id].push(eid); UF_IN_EDGES[toTable.id].push(eid);
    }
  });
}

// ─── Build business tree (for Business Flow tab) ───────────────────────────
function buildBusinessTree() {
  function menuName(path) {
    const parts = (path || '').split('/').filter(Boolean);
    if (parts.length === 0) return 'root';
    let start = 0;
    while (start < parts.length && /^(api|v\d+)$/i.test(parts[start])) start++;
    const seg = parts[start] || parts[0] || 'root';
    return seg.replace(/^\{(\w+?)s?\}$/, '$1s').replace(/^\{(\w+)\}$/, '$1');
  }

  const appName = document.title.replace(' — CodeMap', '') || 'App';
  const root = { name: appName, type: 'root', children: [] };

  // Group endpoints by menu
  const menus = {};
  asArr(SCAN.endpoints).forEach(ep => {
    const mname = menuName(ep.path);
    if (!menus[mname]) {
      menus[mname] = { name: humanLabel(mname), type: 'menu', menuKey: mname, children: [] };
      root.children.push(menus[mname]);
    }
    // Create feature node
    const feature = {
      name: humanAction(ep),
      type: 'feature',
      method: ep.method, path: ep.path, file: ep.file, line: ep.line,
      auth: ep.auth, etype: ep.type,
      children: [],
    };
    // Add validations as children (same file)
    const valCount = {};
    asArr(SCAN.validations).filter(v => v.file === ep.file).forEach(v => {
      const key = (v.field || '') + ':' + (v.rule || '');
      if (!valCount[key]) {
        valCount[key] = true;
        feature.children.push({
          name: (v.field || v.rule || 'validate'),
          type: 'validation',
          field: v.field, rule: v.rule, raw: v.raw, vkind: v.kind,
        });
      }
    });
    // Add DB tables as children (queries in same file)
    const tables = {};
    asArr(SCAN.database?.queries).filter(q => q.file === ep.file).forEach(q => {
      if (q.table && !tables[q.table]) {
        tables[q.table] = true;
        const tableInfo = SCAN.database?.tables?.[q.table];
        feature.children.push({
          name: q.table,
          type: 'table',
          operation: q.operation,
          columns: (tableInfo && Array.isArray(tableInfo.columns)) ? tableInfo.columns : [],
        });
      }
    });
    // Add forms as children (by action match)
    asArr(SCAN.forms).filter(f => f.action === ep.path).forEach(f => {
      feature.children.push({
        name: 'Form: ' + (f.action || f.type || 'form'),
        type: 'form',
        action: f.action, ftype: f.type,
      });
    });
    if (feature.children.length === 0) delete feature.children;
    menus[mname].children.push(feature);
  });

  // Sort menus: auth first, then dashboard, then alphabetical
  root.children.sort((a, b) => {
    const order = ['auth', 'dashboard', 'root', 'home'];
    const ai = order.indexOf(a.menuKey); const bi = order.indexOf(b.menuKey);
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
    return a.name.localeCompare(b.name);
  });

  businessTreeData = root;
  businessRoot = d3.hierarchy(root);

  // Collapse all except root + menus (depth 0-1)
  businessRoot.descendants().forEach(d => {
    if (d.depth > 1 && d.children) {
      d._children = d.children;
      d.children = null;
    }
  });
}

function toggleTreeNode(d) {
  if (d.children) { d._children = d.children; d.children = null; }
  else if (d._children) { d.children = d._children; d._children = null; }
  renderBusiness();
}

// ─── Render: Business Flow (horizontal tree with cards) ────────────────────
function renderBusiness() {
  const svgEl = document.getElementById('canvas');
  const width = svgEl.clientWidth;
  const height = svgEl.clientHeight;

  d3.select('#canvas').selectAll('*').remove();
  if (simulation) { simulation.stop(); simulation = null; }

  const svg = d3.select('#canvas');
  const root_g = svg.append('g').attr('class', 'zoom-root');

  // Zoom/pan
  zoomBehavior = d3.zoom().scaleExtent([0.05, 5])
    .on('zoom', (e) => root_g.attr('transform', e.transform));
  svg.call(zoomBehavior);
  svg.on('dblclick.zoom', null);

  // Tree layout (horizontal: swap x/y)
  const treeLayout = d3.tree().nodeSize([42, 260])
    .separation((a, b) => a.parent === b.parent ? 1 : 1.4);
  treeLayout(businessRoot);

  // Lane headers
  const laneHeaders = [
    { depth: 0, label: 'Aplikasi' },
    { depth: 1, label: 'Menu' },
    { depth: 2, label: 'Aksi / API' },
    { depth: 3, label: 'Validasi & Database' },
  ];
  laneHeaders.forEach(lh => {
    root_g.append('text')
      .attr('class', 'lane-header')
      .attr('x', lh.depth * 260)
      .attr('y', -25)
      .text(lh.label);
  });

  const nodes = businessRoot.descendants();
  const links = businessRoot.links();

  // Links
  const link = root_g.selectAll('.tree-link')
    .data(links)
    .enter().append('path')
      .attr('class', d => 'tree-link ' + (d.target.data.type || ''))
      .attr('data-target', d => d.target.data.name)
      .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x));

  // Nodes (as foreignObject cards)
  const nodeG = root_g.selectAll('.tree-node')
    .data(nodes)
    .enter().append('g')
      .attr('class', 'tree-node')
      .attr('transform', d => `translate(${d.y},${d.x})`)
      .style('cursor', 'pointer')
      .on('click', (ev, d) => {
        ev.stopPropagation();
        if (ev.shiftKey || (d._children !== undefined) || (d.children !== undefined && d.depth > 0)) {
          // Toggle expand/collapse on click
          if (d._children || (d.children && d.depth > 0)) toggleTreeNode(d);
        }
        selectTreeNode(d);
      })
      .on('mouseover', function(ev, d) { showTreeTooltip(ev, d); })
      .on('mouseout', () => hideTooltip());

  const cardW = 190;
  const cardH = 36;

  nodeG.append('foreignObject')
    .attr('width', cardW)
    .attr('height', cardH)
    .attr('x', -cardW / 2)
    .attr('y', -cardH / 2)
    .html(d => treeCardHTML(d));

  // Stats
  const visibleCount = nodes.length;
  const totalFeatures = asArr(SCAN.endpoints).length;
  const totalMenus = businessRoot.children?.length || 0;
  document.getElementById('stats').textContent =
    `${visibleCount} nodes · ${totalMenus} menus · ${totalFeatures} APIs`;

  // Center initial view
  const rootX = businessRoot.y || 0;
  const rootY = businessRoot.x || 0;
  const initScale = 0.85;
  const initX = width / 2 - rootX * initScale - 80;
  const initY = height / 2 - rootY * initScale;
  svg.call(zoomBehavior.transform, d3.zoomIdentity.translate(initX, initY).scale(initScale));
}

function treeCardHTML(d) {
  const type = d.data.type || 'feature';
  const color = TYPE_COLORS[type] || '#484f58';
  const icon = TYPE_ICONS[type] || '⚫';
  const label = d.data.name || '—';
  const hasChildren = d._children || d.children;
  const isCollapsed = d._children && !d.children;

  let html = `<div class="card ${type}" data-type="${type}">`;
  html += `<span class="card-icon">${icon}</span>`;
  html += `<span class="card-label">${label}</span>`;

  if (type === 'feature' && d.data.method) {
    const m = d.data.method.toLowerCase();
    html += `<span class="card-method method-${m}">${HUMAN_METHODS[m] || m.toUpperCase()}</span>`;
  }
  if (type === 'table' && d.data.columns?.length) {
    html += `<span class="card-count">${d.data.columns.length} col</span>`;
  }
  if (type === 'validation' && d.data.rule) {
    html += `<span class="card-count">${d.data.rule}</span>`;
  }
  if (hasChildren) {
    const count = (d._children || d.children).length;
    html += `<span class="card-count">${count}</span>`;
    html += `<span class="card-expand">${isCollapsed ? '▸' : '▾'}</span>`;
  }
  html += '</div>';
  return html;
}

// ─── Tree selection + detail ───────────────────────────────────────────────
function selectTreeNode(d) {
  selectedNode = d;
  d3.selectAll('.card').classed('selected', false);
  // Find the card in the DOM
  const allNodes = document.querySelectorAll('.tree-node');
  allNodes.forEach(n => {
    if (n.__data__ === d) {
      n.querySelector('.card')?.classList.add('selected');
    }
  });

  // Highlight connected links
  d3.selectAll('.tree-link').classed('highlighted', false);
  // Highlight path from root to this node
  let current = d;
  while (current.parent) {
    d3.selectAll('.tree-link').filter(l => l.target === current).classed('highlighted', true);
    current = current.parent;
  }

  showTreeDetail(d);
}

function showTreeDetail(d) {
  const panel = document.getElementById('detail');
  panel.classList.add('visible');

  const data = d.data;
  document.getElementById('detail-title').textContent = data.name || '—';
  document.getElementById('detail-path').textContent = data.path || data.menuKey || '';

  const body = document.getElementById('detail-body');
  let html = '';

  // Type
  const typeLabel = { root: 'Aplikasi', menu: 'Menu', feature: 'API/Endpoint', validation: 'Validasi', table: 'Table DB', form: 'Form' }[data.type] || data.type;
  html += `<div class="section"><h4>Tipe</h4><div class="row"><span class="tag">${typeLabel}</span></div></div>`;

  // Root
  if (data.type === 'root') {
    const menus = (d.children || d._children || []).map(c => c.data);
    html += `<div class="section"><h4>Menu (${menus.length})</h4>`;
    menus.forEach(m => {
      const featCount = (c => (c.children || c._children || []).length)(d.children?.find(c => c.data.name === m.name) || d._children?.find(c => c.data.name === m.name) || {});
      html += `<div class="link-item" onclick="navigateTree('${m.name}')">📋 ${m.name} (${featCount} fitur)</div>`;
    });
    html += `</div>`;
  }

  // Menu
  if (data.type === 'menu') {
    const features = (d.children || d._children || []);
    html += `<div class="section"><h4>Fitur (${features.length})</h4>`;
    features.forEach(f => {
      const m = (f.data.method || '').toLowerCase();
      const methodTag = m ? `<span class="tag method-${m}">${HUMAN_METHODS[m] || m}</span>` : '';
      html += `<div class="link-item" onclick="navigateTree('${f.data.name}')">${methodTag} ${f.data.name}</div>`;
    });
    html += `</div>`;

    // Aggregate validations + tables
    const allVals = new Set();
    const allTables = new Set();
    features.forEach(f => {
      (f.children || f._children || []).forEach(c => {
        if (c.data.type === 'validation') allVals.add(c.data.field + ': ' + c.data.rule);
        if (c.data.type === 'table') allTables.add(c.data.name);
      });
    });
    if (allVals.size) {
      html += `<div class="section"><h4>Validasi (${allVals.size})</h4>`;
      Array.from(allVals).slice(0, 15).forEach(v => html += `<div class="row"><code>${v}</code></div>`);
      html += `</div>`;
    }
    if (allTables.size) {
      html += `<div class="section"><h4>Table Database (${allTables.size})</h4>`;
      Array.from(allTables).forEach(t => html += `<div class="row"><code style="color:#d29922">${t}</code></div>`);
      html += `</div>`;
    }
  }

  // Feature
  if (data.type === 'feature') {
    html += `<div class="section"><h4>HTTP Method</h4>`;
    const m = (data.method || 'mixed').toLowerCase();
    html += `<div class="row"><span class="tag method-${m}">${HUMAN_METHODS[m] || data.method || 'MIXED'}</span></div></div>`;
    html += `<div class="section"><h4>Path</h4><div class="row"><code>${data.path || '—'}</code></div></div>`;
    html += `<div class="section"><h4>Autentikasi</h4>`;
    html += `<div class="row"><span class="tag ${data.auth === 'auth_required' ? 'auth' : 'public'}">${data.auth === 'auth_required' ? 'Wajib Login' : (data.auth || 'Unknown')}</span></div></div>`;
    if (data.etype) {
      html += `<div class="section"><h4>Framework</h4><div class="row">${data.etype}</div></div>`;
    }

    const children = d.children || d._children || [];
    const validations = children.filter(c => c.data.type === 'validation');
    const tables = children.filter(c => c.data.type === 'table');
    const forms = children.filter(c => c.data.type === 'form');

    if (forms.length) {
      html += `<div class="section"><h4>Form (${forms.length})</h4>`;
      forms.forEach(f => html += `<div class="row"><code>${f.data.name}</code> <span style="color:#8b949e">(${f.data.ftype || 'form'})</span></div>`);
      html += `</div>`;
    }

    if (validations.length) {
      html += `<div class="section"><h4>Validasi Field (${validations.length})</h4>`;
      html += `<ul class="field-list">`;
      const seen = new Set();
      validations.forEach(v => {
        const key = v.data.field + ':' + v.data.rule;
        if (seen.has(key)) return;
        seen.add(key);
        html += `<li><span class="fname">${v.data.field || '—'}</span><span class="ftype">${v.data.rule || '—'}</span></li>`;
      });
      html += `</ul></div>`;
    }

    if (tables.length) {
      html += `<div class="section"><h4>Table Database (${tables.length})</h4>`;
      html += `<ul class="field-list">`;
      tables.forEach(t => {
        const colCount = t.data.columns?.length || 0;
        html += `<li><span class="fname">${t.data.name}</span><span class="ftype">${t.data.operation || ''} ${colCount ? colCount + ' col' : ''}</span></li>`;
      });
      html += `</ul></div>`;
    }

    if (!validations.length && !tables.length && !forms.length) {
      html += `<div class="section"><h4>Detail</h4><div class="row" style="color:#484f58">Tidak ada validasi/form/table terdeteksi untuk endpoint ini.</div></div>`;
    }
  }

  // Validation
  if (data.type === 'validation') {
    html += `<div class="section"><h4>Aturan Validasi</h4>`;
    html += `<div class="row"><strong>Field:</strong> <code>${data.field || '—'}</code></div>`;
    html += `<div class="row"><strong>Rule:</strong> <code>${data.rule || '—'}</code></div>`;
    html += `</div>`;
    if (data.raw) {
      html += `<div class="section"><h4>Code</h4><div class="row"><code style="color:#d29922;font-size:11px">${data.raw}</code></div></div>`;
    }
  }

  // Table
  if (data.type === 'table' && data.columns?.length) {
    html += `<div class="section"><h4>Columns (${data.columns.length})</h4><ul class="field-list">`;
    data.columns.forEach(col => {
      html += `<li><span class="fname">${col.name}</span><span class="ftype">${col.type}</span><span class="fflags">${col.flags || ''}</span></li>`;
    });
    html += `</ul></div>`;
  }

  body.innerHTML = html;
}

function navigateTree(name) {
  // Find and select a tree node by name
  const node = businessRoot.descendants().find(d => d.data.name === name);
  if (node) {
    // Expand parents
    let parent = node.parent;
    while (parent) {
      if (parent._children) { parent.children = parent._children; parent._children = null; }
      parent = parent.parent;
    }
    renderBusiness();
    setTimeout(() => selectTreeNode(node), 100);
  }
}

// ─── Render: Force-directed (Code Flow / DB / Validasi) ─────────────────────
function getViewNodes() {
  const nodes = filteredNodes;
  if (currentView === 'db') return nodes.filter(n => n._kind === 'table' || n._kind === 'query');
  if (currentView === 'validation') return nodes.filter(n => n._kind === 'endpoint' || n._kind === 'feature' || n._kind === 'logic' || n._kind === 'validation');
  if (currentView === 'flow') return nodes; // all code flow
  return nodes;
}

function getViewEdges(nodeIds) {
  const idSet = new Set(nodeIds.map(n => n.id));
  return filteredEdges.filter(e => idSet.has(e.source) && idSet.has(e.target));
}

function nodeRadius(d) {
  const connections = ((aOutEdges[d.id] || []).length + (aInEdges[d.id] || []).length);
  if (d._kind === 'menu') return 14 + Math.min(8, connections / 4);
  if (d._kind === 'feature' || d._kind === 'table') return 10 + Math.min(6, connections / 4);
  return NODE_R + Math.min(6, connections / 3);
}

function render() {
  const svgEl = document.getElementById('canvas');
  const width = svgEl.clientWidth;
  const height = svgEl.clientHeight;

  d3.select('#canvas').selectAll('*').remove();
  if (simulation) { simulation.stop(); simulation = null; }

  const svg = d3.select('#canvas');
  const defs = svg.append('defs');
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

  const root = svg.append('g').attr('class', 'zoom-root');
  zoomBehavior = d3.zoom().scaleExtent([0.05, 8])
    .filter(e => !e.target.closest('.node-box') || e.type !== 'dblclick')
    .on('zoom', (e) => root.attr('transform', e.transform));
  svg.call(zoomBehavior);
  svg.on('dblclick.zoom', null);

  const edgeLayer = root.append('g').attr('class', 'edges');
  const nodeLayer = root.append('g').attr('class', 'nodes');

  const viewNodes = getViewNodes();
  const visibleIds = new Set(viewNodes.map(n => n.id));
  const visibleEdges = getViewEdges(viewNodes).filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));

  const simNodes = viewNodes.map(n => ({ ...n }));
  const simEdges = visibleEdges.map(e => ({ ...e }));

  const link = edgeLayer.selectAll('path').data(simEdges).enter().append('path')
    .attr('class', d => `edge ${d.relation}`)
    .attr('data-source', d => d.source).attr('data-target', d => d.target)
    .attr('marker-end', d => `url(#arrow-${d.relation || 'default'})`)
    .style('fill', 'none').style('stroke-opacity', 0.4);

  const nodeG = nodeLayer.selectAll('g.node-box').data(simNodes, d => d.id).enter().append('g')
    .attr('class', 'node-box').style('cursor', 'pointer')
    .on('click', (ev, d) => { ev.stopPropagation(); selectNode(d); })
    .on('mouseover', function(ev, d) { d3.select(this).select('circle').attr('stroke-width', 3); showTooltip(ev, d); })
    .on('mouseout', function() { d3.select(this).select('circle').attr('stroke-width', 1.5); hideTooltip(); });

  nodeG.append('circle').attr('class', 'node-circle')
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => (TYPE_COLORS[d._kind] || '#484f58') + '33')
    .attr('stroke', d => TYPE_COLORS[d._kind] || '#484f58')
    .attr('stroke-width', 1.5);

  nodeG.append('text').attr('class', 'node-label-force')
    .attr('x', d => nodeRadius(d) + 4).attr('y', d => d._kind === 'menu' ? 5 : 3)
    .attr('text-anchor', 'start')
    .style('font-size', d => d._kind === 'menu' ? '13px' : '10px')
    .style('font-weight', d => d._kind === 'menu' ? '700' : '400')
    .style('fill', d => d._kind === 'menu' ? '#f778ba' : '#c9d1d9')
    .style('pointer-events', 'none')
    .text(d => { const lbl = d.label || d.name || d.id; return lbl.length > 28 ? lbl.slice(0, 27) + '…' : lbl; });

  nodeG.append('text').attr('class', 'type-badge-force')
    .attr('x', 0).attr('y', d => -nodeRadius(d) - 4)
    .attr('text-anchor', 'middle')
    .style('font-size', '8px').style('font-weight', '600')
    .style('fill', d => TYPE_COLORS[d._kind] || '#484f58')
    .style('pointer-events', 'none')
    .text(d => TYPE_LABELS[d._kind] || '');

  const drag = d3.drag()
    .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
    .on('end', (ev, d) => { if (!ev.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; });
  nodeG.call(drag);

  const chargeStrength = currentView === 'flow' ? -120 : -80;
  simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(d => d.id).distance(50 + Math.random() * 50).strength(0.15))
    .force('charge', d3.forceManyBody().strength(chargeStrength))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 14))
    .force('x', d3.forceX(width / 2).strength(0.03))
    .force('y', d3.forceY(height / 2).strength(0.03));

  simulation.on('tick', () => {
    link.attr('d', d => {
      const sx = d.source.x, sy = d.source.y, tx = d.target.x, ty = d.target.y;
      const dx = tx - sx, dy = ty - sy;
      const dr = Math.sqrt(dx * dx + dy * dy) * 1.5;
      return `M${sx},${sy}A${dr},${dr} 0 0,1 ${tx},${ty}`;
    });
    nodeG.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  document.getElementById('stats').textContent =
    `${viewNodes.length} nodes · ${visibleEdges.length} edges`;
}

// ─── Force-directed selection ──────────────────────────────────────────────
function selectNode(node) {
  selectedNode = node;
  d3.selectAll('.node-circle').classed('selected', false);
  d3.selectAll('.node-box').filter(d => d && d.id === node.id).select('circle').classed('selected', true);
  const connected = new Set([node.id]);
  (aOutEdges[node.id] || []).forEach(eid => { const e = aEdges.find(e => e.id === eid); if (e) connected.add(e.target); });
  (aInEdges[node.id] || []).forEach(eid => { const e = aEdges.find(e => e.id === eid); if (e) connected.add(e.source); });
  d3.selectAll('.node-box').classed('dimmed', d => d && !connected.has(d.id));
  d3.selectAll('.edge').classed('highlighted', function() { return this.getAttribute('data-source') === node.id || this.getAttribute('data-target') === node.id; });
  d3.selectAll('.edge').classed('dimmed', function() { return this.getAttribute('data-source') !== node.id && this.getAttribute('data-target') !== node.id; });
  showDetail(node);
}

function clearHighlight() {
  d3.selectAll('.node-box').classed('dimmed', false);
  d3.selectAll('.edge').classed('highlighted', false).classed('dimmed', false);
}

function closeDetail() {
  document.getElementById('detail').classList.remove('visible');
  d3.selectAll('.node-circle').classed('selected', false);
  d3.selectAll('.card').classed('selected', false);
  d3.selectAll('.tree-link').classed('highlighted', false);
  selectedNode = null;
  clearHighlight();
}

// ─── Detail panel (force-directed) ─────────────────────────────────────────
function showDetail(node) {
  const panel = document.getElementById('detail');
  panel.classList.add('visible');
  document.getElementById('detail-title').textContent = node.label || node.name || node.id;
  document.getElementById('detail-path').textContent = `${node.file || '—'} : ${node.line || ''}`;
  const body = document.getElementById('detail-body');
  let html = '';
  html += `<div class="section"><h4>Tipe</h4><div class="row"><span class="tag">${TYPE_LABELS[node._kind] || node._kind}</span> ${node._kind}</div></div>`;

  if (node._kind === 'menu') {
    const features = (aOutEdges[node.id] || []).map(eid => { const e = aEdges.find(e => e.id === eid); return e ? aNodeMap[e.target] : null; }).filter(Boolean);
    html += `<div class="section"><h4>Fitur (${features.length})</h4>`;
    features.forEach(f => html += `<div class="link-item" onclick="selectById('${f.id}')">→ ${f.label} [${f.method || ''}]</div>`);
    html += `</div>`;
  }
  if (node._kind === 'feature' || node._kind === 'endpoint') {
    html += `<div class="section"><h4>HTTP Method</h4><div class="row"><span class="tag method-${(node.method||'mixed').toLowerCase()}">${HUMAN_METHODS[(node.method||'').toLowerCase()] || node.method || 'MIXED'}</span></div></div>`;
    html += `<div class="section"><h4>Path</h4><div class="row"><code>${node.path}</code></div></div>`;
    html += `<div class="section"><h4>Auth</h4><div class="row"><span class="tag ${node.auth === 'auth_required' ? 'auth' : 'public'}">${node.auth === 'auth_required' ? 'Wajib Login' : (node.auth || 'Unknown')}</span></div></div>`;
  }
  if (node._kind === 'validation') {
    html += `<div class="section"><h4>Validasi</h4><div class="row"><strong>Field:</strong> <code>${node.field || '—'}</code></div><div class="row"><strong>Rule:</strong> <code>${node.rule || '—'}</code></div></div>`;
    if (node.raw) html += `<div class="section"><h4>Code</h4><div class="row"><code style="color:#d29922;font-size:11px">${node.raw}</code></div></div>`;
  }
  if (node._kind === 'table' && node.columns?.length) {
    html += `<div class="section"><h4>Columns (${node.columns.length})</h4><ul class="field-list">`;
    node.columns.forEach(col => html += `<li><span class="fname">${col.name}</span><span class="ftype">${col.type}</span><span class="fflags">${col.flags || ''}</span></li>`);
    html += `</ul></div>`;
  }
  const outE = (aOutEdges[node.id] || []).map(eid => aEdges.find(e => e.id === eid)).filter(Boolean);
  const inE = (aInEdges[node.id] || []).map(eid => aEdges.find(e => e.id === eid)).filter(Boolean);
  if (outE.length) {
    html += `<div class="section"><h4>Outgoing (${outE.length})</h4>`;
    outE.slice(0, 20).forEach(e => { const t = aNodeMap[e.target]; if (t) html += `<div class="link-item" onclick="selectById('${e.target}')">→ ${t.label}</div>`; });
    if (outE.length > 20) html += `<div style="color:#484f58;font-size:11px">+${outE.length - 20} more</div>`;
    html += `</div>`;
  }
  if (inE.length) {
    html += `<div class="section"><h4>Incoming (${inE.length})</h4>`;
    inE.slice(0, 20).forEach(e => { const s = aNodeMap[e.source]; if (s) html += `<div class="link-item" onclick="selectById('${e.source}')">← ${s.label}</div>`; });
    if (inE.length > 20) html += `<div style="color:#484f58;font-size:11px">+${inE.length - 20} more</div>`;
    html += `</div>`;
  }
  body.innerHTML = html;
}

function selectById(id) { const node = aNodeMap[id]; if (node) selectNode(node); }

// ─── Tooltip ───────────────────────────────────────────────────────────────
function showTooltip(ev, node) {
  const tip = document.getElementById('tooltip');
  const kind = node._kind;
  const color = TYPE_COLORS[kind] || '#8b949e';
  let inner = `<strong style="color:${color}">${node.label}</strong>`;
  if (node.method) inner += ` <span style="color:#484f58">[${HUMAN_METHODS[(node.method||'').toLowerCase()] || node.method}]</span>`;
  if (node.file) inner += `<div style="color:#484f58;font-size:10px">${node.file}</div>`;
  tip.innerHTML = inner;
  tip.style.display = 'block';
  tip.style.left = (ev.pageX + 12) + 'px';
  tip.style.top = (ev.pageY - 10) + 'px';
}

function showTreeTooltip(ev, d) {
  const tip = document.getElementById('tooltip');
  const type = d.data.type || 'feature';
  const color = TYPE_COLORS[type] || '#8b949e';
  let inner = `<strong style="color:${color}">${d.data.name}</strong>`;
  if (d.data.method) inner += ` <span style="color:#484f58">[${HUMAN_METHODS[(d.data.method||'').toLowerCase()] || d.data.method}]</span>`;
  if (d.data.path) inner += `<div style="color:#484f58;font-size:10px">${d.data.path}</div>`;
  const childCount = (d.children || d._children || []).length;
  if (childCount) inner += `<div style="color:#8b949e">${childCount} item</div>`;
  tip.innerHTML = inner;
  tip.style.display = 'block';
  tip.style.left = (ev.pageX + 12) + 'px';
  tip.style.top = (ev.pageY - 10) + 'px';
}

function hideTooltip() { document.getElementById('tooltip').style.display = 'none'; }

// ─── Sidebar ────────────────────────────────────────────────────────────────
function renderSidebar() {
  const list = document.getElementById('node-list');
  list.innerHTML = '';

  if (currentView === 'business') {
    // Show tree hierarchy in sidebar
    const allNodes = businessRoot ? businessRoot.descendants() : [];
    allNodes.forEach(d => {
      const data = d.data;
      const indent = '  '.repeat(d.depth);
      const icon = TYPE_ICONS[data.type] || '⚫';
      const div = document.createElement('div');
      div.className = 'list-item';
      div.style.paddingLeft = (16 + d.depth * 12) + 'px';
      const count = (d.children || d._children || []).length;
      div.innerHTML = `<span class="icon">${icon}</span><span class="name">${data.name}</span>${count ? `<span class="badge">${count}</span>` : ''}`;
      div.onclick = () => {
        // Expand parents
        let parent = d.parent;
        while (parent) {
          if (parent._children) { parent.children = parent._children; parent._children = null; }
          parent = parent.parent;
        }
        renderBusiness();
        setTimeout(() => selectTreeNode(d), 50);
      };
      list.appendChild(div);
    });
  } else {
    filteredNodes.forEach(node => {
      const div = document.createElement('div');
      div.className = 'list-item';
      div.innerHTML = `<span class="icon">${TYPE_ICONS[node._kind] || '⚫'}</span><span class="name">${node.label}</span><span class="badge">${(aOutEdges[node.id]||[]).length}</span>`;
      div.onclick = () => selectById(node.id);
      list.appendChild(div);
    });
  }
}

function filterNodes(q) {
  searchQuery = q;
  if (currentView === 'business') {
    // Filter sidebar only (tree stays)
    renderSidebar();
    // If search, expand all matching nodes
    if (q) {
      const ql = q.toLowerCase();
      businessRoot.descendants().forEach(d => {
        if ((d.data.name || '').toLowerCase().includes(ql)) {
          let parent = d.parent;
          while (parent) {
            if (parent._children) { parent.children = parent._children; parent._children = null; }
            parent = parent.parent;
          }
        }
      });
      renderBusiness();
      renderSidebar();
    }
  } else {
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
}

// ─── Legend ────────────────────────────────────────────────────────────────
function updateLegend() {
  const el = document.getElementById('legend');
  let html = '';
  if (currentView === 'business') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#3fb950;background:#3fb95033"></div> Aplikasi — Root</div>
      <div class="row"><div class="dot" style="border-color:#f778ba;background:#f778ba33"></div> Menu — Group fitur (Autentikasi, Sertifikat, dll)</div>
      <div class="row"><div class="dot" style="border-color:#58a6ff;background:#58a6ff33"></div> Aksi/API — Endpoint user akses</div>
      <div class="row"><div class="dot" style="border-color:#8957e5;background:#8957e533"></div> Validasi — Aturan validasi field</div>
      <div class="row"><div class="dot" style="border-color:#d29922;background:#d2992233"></div> Table — Database table</div>
      <div class="sep"></div>
      <h5>Cara Pakai</h5>
      <div class="row">▸ Klik card = expand/collapse</div>
      <div class="row">▾ = expanded, ▸ = collapsed</div>
      <div class="row">Scroll = zoom, drag = pan</div>`;
  } else if (currentView === 'flow') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#f778ba;background:#f778ba33"></div> Menu</div>
      <div class="row"><div class="dot" style="border-color:#58a6ff;background:#58a6ff33"></div> API/Feature</div>
      <div class="row"><div class="dot" style="border-color:#8957e5;background:#8957e533"></div> Validation</div>
      <div class="row"><div class="dot" style="border-color:#d29922;background:#d2992233"></div> DB Table</div>
      <div class="sep"></div>
      <h5>Edge Types</h5>
      <div class="row"><div class="line" style="background:#f778ba"></div> has</div>
      <div class="row"><div class="line" style="background:#58a6ff"></div> route</div>
      <div class="row"><div class="line" style="background:#8957e5"></div> validates</div>
      <div class="row"><div class="line" style="background:#d29922"></div> queries/db</div>`;
  } else if (currentView === 'db') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#d29922;background:#d2992233"></div> Table — Database table</div>
      <div class="row"><div class="dot" style="border-color:#e3b341;background:#e3b34133"></div> Query — DB query</div>`;
  } else if (currentView === 'validation') {
    html = `<h5>Node Types</h5>
      <div class="row"><div class="dot" style="border-color:#58a6ff;background:#58a6ff33"></div> API — Endpoint</div>
      <div class="row"><div class="dot" style="border-color:#8957e5;background:#8957e533"></div> Validation — Aturan validasi</div>
      <div class="sep"></div>
      <h5>Edge Types</h5>
      <div class="row"><div class="line" style="background:#8957e5"></div> validates</div>`;
  }
  el.innerHTML = html;
}

// ─── View switching ────────────────────────────────────────────────────────
function setView(view) {
  currentView = view;
  selectedNode = null;
  document.getElementById('detail').classList.remove('visible');

  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === view));

  if (view === 'business') {
    renderBusiness();
  } else {
    // Use user flow graph for 'flow', code graph for db/validation
    if (view === 'flow') {
      aNodes = UF_NODES; aEdges = UF_EDGES; aNodeMap = UF_NODE_MAP;
      aOutEdges = UF_OUT_EDGES; aInEdges = UF_IN_EDGES;
    } else {
      aNodes = NODES; aEdges = EDGES; aNodeMap = NODE_MAP;
      aOutEdges = OUT_EDGES; aInEdges = IN_EDGES;
    }
    filteredNodes = [...aNodes];
    filteredEdges = [...aEdges];
    render();
  }
  renderSidebar();
  updateLegend();
}

// ─── Init ──────────────────────────────────────────────────────────────────
buildGraph();
buildUserFlowGraph();
buildBusinessTree();

// Default to business flow
aNodes = UF_NODES; aEdges = UF_EDGES; aNodeMap = UF_NODE_MAP;
aOutEdges = UF_OUT_EDGES; aInEdges = UF_IN_EDGES;
filteredNodes = [...aNodes];
filteredEdges = [...aEdges];

setView('business');

// Click empty canvas → deselect
document.getElementById('canvas-wrap').addEventListener('click', (e) => {
  if (e.target.tagName === 'svg') closeDetail();
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