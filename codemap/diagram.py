"""CodeMap Diagram — Split Dual-Mode HTML Diagram Builder.

Modes:
  business   Awam / BA mode: clean horizontal tree, card-based, Indonesian labels, high-level
  developer  Dev mode: force-directed graph with full technical detail (routes, DB, validations, functions)
"""

import json
from pathlib import Path

D3_PATH = Path(__file__).parent.parent / "vendor" / "d3.v7.min.js"


def load_d3():
    if D3_PATH.exists():
        return D3_PATH.read_text()
    return ""


# ─── Business Flow HTML Template (Non-Technical / Awam) ─────────────────────

BUSINESS_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ — Business Flow | CodeMap</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; overflow: hidden; }
#app { display: flex; height: 100vh; }

/* Topbar */
#topbar { position: absolute; top: 0; left: 0; right: 0; height: 48px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; z-index: 200; }
#topbar .title { font-size: 15px; font-weight: 600; color: #58a6ff; display: flex; align-items: center; gap: 8px; }
#topbar .mode-switch { display: flex; gap: 8px; align-items: center; }
#topbar .mode-btn { padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; text-decoration: none; cursor: pointer; transition: all 0.15s; border: 1px solid #30363d; }
#topbar .mode-btn.active { background: #238636; color: #fff; border-color: #238636; }
#topbar .mode-btn.inactive { background: #21262d; color: #8b949e; }
#topbar .mode-btn.inactive:hover { color: #c9d1d9; border-color: #58a6ff; }
#topbar .dash-btn { background: #1f6feb; color: #fff; border: none; padding: 5px 12px; border-radius: 6px; font-size: 12px; text-decoration: none; font-weight: 500; }
#topbar .dash-btn:hover { background: #388bfd; }

/* Main area */
#main { display: flex; width: 100%; height: calc(100vh - 48px); margin-top: 48px; }

/* Sidebar */
#sidebar { width: 280px; background: #161b22; border-right: 1px solid #30363d; display: flex; flex-direction: column; }
#sidebar-header { padding: 12px 16px; border-bottom: 1px solid #30363d; }
#sidebar-header h3 { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
#filter-box input { width: 100%; padding: 7px 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 12px; }
#filter-box input:focus { outline: none; border-color: #58a6ff; }
#node-tree { flex: 1; overflow-y: auto; padding: 8px 0; }
.tree-item { padding: 6px 12px; cursor: pointer; font-size: 12px; display: flex; align-items: center; gap: 6px; transition: background 0.1s; border-left: 2px solid transparent; }
.tree-item:hover { background: #21262d; }
.tree-item.selected { background: #1f6feb22; border-left-color: #58a6ff; }
.tree-item .icon { font-size: 13px; flex-shrink: 0; }
.tree-item .label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-item .badge { font-size: 10px; padding: 1px 5px; border-radius: 10px; background: #30363d; color: #8b949e; }
#stats { padding: 10px 16px; border-top: 1px solid #30363d; font-size: 11px; color: #484f58; }

/* Canvas */
#canvas-wrap { flex: 1; position: relative; overflow: hidden; background: #0d1117; }
#canvas { width: 100%; height: 100%; cursor: grab; }
#canvas:active { cursor: grabbing; }

/* Tooltip */
#tooltip { position: fixed; background: #1f2937; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; font-size: 12px; max-width: 320px; z-index: 1000; pointer-events: none; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }

/* Detail panel */
#detail { position: absolute; right: 0; top: 0; width: 380px; height: 100%; background: #161b22; border-left: 1px solid #30363d; overflow-y: auto; transform: translateX(100%); transition: transform 0.25s ease; z-index: 100; box-shadow: -4px 0 16px rgba(0,0,0,0.4); }
#detail.visible { transform: translateX(0); }
#detail .header { padding: 16px; border-bottom: 1px solid #30363d; position: sticky; top: 0; background: #161b22; z-index: 1; }
#detail .header h3 { font-size: 15px; color: #58a6ff; margin-bottom: 4px; }
#detail .header .subtitle { font-size: 11px; color: #8b949e; }
#detail .close-btn { position: absolute; top: 16px; right: 16px; background: none; border: none; color: #8b949e; font-size: 20px; cursor: pointer; }
#detail .close-btn:hover { color: #f85149; }
#detail .section { padding: 14px 16px; border-bottom: 1px solid #21262d; }
#detail .section h4 { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
#detail .section .row { padding: 3px 0; font-size: 12px; }
#detail .tag { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; background: #30363d; color: #c9d1d9; font-weight: 500; margin-right: 4px; }
#detail .tag.method-get { background: #238636; color: #fff; }
#detail .tag.method-post { background: #d29922; color: #fff; }
#detail .tag.method-put { background: #1f6feb; color: #fff; }
#detail .tag.method-delete { background: #da3633; color: #fff; }
#detail .tag.auth { background: #f8514933; color: #f85149; }
#detail .tag.public { background: #23863633; color: #3fb950; }
.item-link { padding: 5px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; color: #58a6ff; display: flex; align-items: center; gap: 6px; transition: background 0.1s; }
.item-link:hover { background: #21262d; }

/* SVG Tree Elements */
.tree-link { fill: none; stroke: #30363d; stroke-width: 1.5; opacity: 0.6; transition: opacity 0.15s, stroke 0.15s; }
.tree-link.highlighted { stroke: #58a6ff !important; opacity: 1 !important; stroke-width: 2.5 !important; }
.lane-header { fill: #484f58; font-size: 11px; font-weight: 600; text-anchor: middle; text-transform: uppercase; letter-spacing: 1px; }

/* Cards (foreignObject) */
.card { display: flex; align-items: center; gap: 6px; padding: 7px 10px; border-radius: 6px; background: #161b22; border: 1px solid #30363d; border-left-width: 4px; font-size: 12px; cursor: pointer; white-space: nowrap; transition: all 0.15s; box-shadow: 0 2px 4px rgba(0,0,0,0.3); user-select: none; width: 100%; height: 100%; }
.card:hover { background: #21262d; box-shadow: 0 4px 8px rgba(0,0,0,0.5); transform: translateY(-1px); }
.card.selected { background: #1f6feb22; border-color: #58a6ff; box-shadow: 0 0 0 1px #58a6ff; }
.card-icon { font-size: 13px; flex-shrink: 0; }
.card-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.card-method { font-size: 9px; padding: 1px 5px; border-radius: 3px; font-weight: 600; flex-shrink: 0; text-transform: uppercase; }
.card-method.get { background: #238636; color: #fff; }
.card-method.post { background: #d29922; color: #fff; }
.card-method.put, .card-method.patch { background: #1f6feb; color: #fff; }
.card-method.delete { background: #da3633; color: #fff; }
.card-count { font-size: 10px; color: #8b949e; flex-shrink: 0; background: #21262d; padding: 1px 5px; border-radius: 8px; }
.card-expand { font-size: 10px; color: #8b949e; flex-shrink: 0; margin-left: 2px; }

.card.root { border-left-color: #3fb950; }
.card.menu { border-left-color: #f778ba; }
.card.feature { border-left-color: #58a6ff; }
.card.validation { border-left-color: #8957e5; }
.card.table { border-left-color: #d29922; }

/* Legend */
.legend { position: absolute; bottom: 12px; left: 12px; background: #161b22ee; border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; font-size: 11px; max-width: 300px; backdrop-filter: blur(4px); }
.legend h5 { font-size: 10px; color: #8b949e; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px; }
.legend .row { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.legend .bar { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.legend .sep { height: 1px; background: #30363d; margin: 6px 0; }
</style>
</head>
<body>
<div id="app">
  <div id="topbar">
    <div class="title">
      <span>📊</span>
      <span>__TITLE__</span>
      <span style="font-size:11px;color:#8b949e;font-weight:400">— Business Flow (Modus Awam)</span>
    </div>
    <div class="mode-switch">
      <span class="mode-btn active">💼 Alur Bisnis</span>
      <a href="__DEV_FILE__" class="mode-btn inactive">⚡ Developer Graph</a>
      <a href="dashboard.html" class="dash-btn">🏠 Dashboard</a>
    </div>
  </div>

  <div id="main">
    <div id="sidebar">
      <div id="sidebar-header">
        <h3>Menu Aplikasi</h3>
        <div id="filter-box">
          <input type="text" id="search" placeholder="Cari menu atau fitur..." oninput="filterTree(this.value)">
        </div>
      </div>
      <div id="node-tree"></div>
      <div id="stats"></div>
    </div>

    <div id="canvas-wrap">
      <svg id="canvas"></svg>
      <div id="tooltip"></div>
      <div id="detail">
        <div class="header">
          <button class="close-btn" onclick="closeDetail()">×</button>
          <h3 id="detail-title">—</h3>
          <div class="subtitle" id="detail-subtitle">—</div>
        </div>
        <div id="detail-body"></div>
      </div>
      <div id="legend" class="legend">
        <h5>Komponen Diagram</h5>
        <div class="row"><div class="bar" style="background:#3fb950"></div> <strong>Aplikasi</strong> — Proyek utama</div>
        <div class="row"><div class="bar" style="background:#f778ba"></div> <strong>Menu</strong> — Kelompok modul bisnis</div>
        <div class="row"><div class="bar" style="background:#58a6ff"></div> <strong>Fitur / Aksi</strong> — Halaman / aksi user</div>
        <div class="row"><div class="bar" style="background:#8957e5"></div> <strong>Validasi</strong> — Rules input field</div>
        <div class="row"><div class="bar" style="background:#d29922"></div> <strong>Database Table</strong> — Penyimpanan data</div>
        <div class="sep"></div>
        <h5>Panduan Navigasi</h5>
        <div class="row">▸ Klik card = buka / tutup cabang</div>
        <div class="row">Scroll mouse = Zoom, Drag = Geser</div>
      </div>
    </div>
  </div>
</div>

<script>
__D3_JS__

const SCAN = __SCAN_DATA__;

// Human Label Translators
const HUMAN_LABELS = {
  'auth': 'Autentikasi', 'certificates': 'Sertifikat', 'templates': 'Template',
  'events': 'Event/Training', 'participants': 'Peserta', 'dashboard': 'Dashboard',
  'settings': 'Pengaturan', 'health': 'System Health', 'root': 'Home',
  'users': 'Manajemen User', 'profile': 'Profil', 'mail': 'Mail',
  'orders': 'Pesanan', 'products': 'Produk', 'reports': 'Laporan',
  'transactions': 'Transaksi', 'invoices': 'Invoice', 'payments': 'Pembayaran',
  'vault': 'Brankas', 'unlock': 'Buka Kunci', 'org': 'Organisasi',
  'login': 'Login', 'register': 'Daftar', 'help': 'Bantuan',
  'error': 'Error', 'contacts': 'Kontak', 'calendar': 'Kalender',
  'folder': 'Folder', 'rules': 'Aturan', 'send': 'Kirim', 'preferences': 'Preferensi',
  'stats': 'Statistik', 'password': 'Password', 'change-password': 'Ubah Password',
  'accept-organization': 'Terima Undangan', 'system': 'Sistem',
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
  let key = path.toLowerCase().replace(/^\{(\w+?)s?\}$/, '$1s').replace(/^\{(\w+)\}$/, '$1');
  if (HUMAN_LABELS[key]) return HUMAN_LABELS[key];
  if (HUMAN_LABELS[path]) return HUMAN_LABELS[path];
  if (key === 'catchall') return 'Lainnya';
  return key.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
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

function asArr(v) { return Array.isArray(v) ? v : (v ? Object.values(v) : []); }

function menuName(path) {
  const parts = (path || '').split('/').filter(Boolean);
  if (parts.length === 0) return 'root';
  let start = 0;
  while (start < parts.length && /^(api|v\d+)$/i.test(parts[start])) start++;
  const seg = parts[start] || parts[0] || 'root';
  let clean = seg.replace(/:pathMatch\([^)]+\)/, 'catchall').replace(/^:/, '').replace(/\*+$/, '');
  const final = (clean === '*' || clean === '(.*)' || clean === '(*)' || clean === '' || clean === 'catchall') ? 'catchall' : clean;
  if (final === 'root') return 'root';
  return final.replace(/^\{(\w+?)s?\}$/, '$1s').replace(/^\{(\w+)\}$/, '$1').replace(/-\d+$/, '');
}

// Global Tree State
let treeRoot = null;
let zoomBehavior = null;
let selectedNode = null;

function buildTree() {
  const appTitle = document.title.split(' — ')[0] || 'App';
  const root = { name: appTitle, type: 'root', children: [] };
  const menus = {};

  asArr(SCAN.endpoints).forEach(ep => {
    const mname = menuName(ep.path);
    if (!menus[mname]) {
      menus[mname] = { name: humanLabel(mname), type: 'menu', menuKey: mname, children: [] };
      root.children.push(menus[mname]);
    }

    const feature = {
      name: humanAction(ep),
      type: 'feature',
      method: ep.method,
      path: ep.path,
      file: ep.file,
      auth: ep.auth,
      children: [],
    };

    // Validations child
    const valSet = new Set();
    asArr(SCAN.validations).filter(v => v.file === ep.file).forEach(v => {
      const key = (v.field || '') + ':' + (v.rule || '');
      if (!valSet.has(key)) {
        valSet.add(key);
        feature.children.push({
          name: 'Validasi: ' + (v.field || v.rule || 'rule'),
          type: 'validation',
          field: v.field,
          rule: v.rule,
          raw: v.raw,
        });
      }
    });

    // DB Tables child
    const tblSet = new Set();
    asArr(SCAN.database?.queries).filter(q => q.file === ep.file).forEach(q => {
      if (q.table && !tblSet.has(q.table)) {
        tblSet.add(q.table);
        const tblInfo = SCAN.database?.tables?.[q.table];
        feature.children.push({
          name: 'Tabel: ' + q.table,
          type: 'table',
          tableName: q.table,
          columns: (tblInfo && Array.isArray(tblInfo.columns)) ? tblInfo.columns : [],
        });
      }
    });

    if (feature.children.length === 0) delete feature.children;
    menus[mname].children.push(feature);
  });

  // Sort menus
  root.children.sort((a, b) => a.name.localeCompare(b.name));

  treeRoot = d3.hierarchy(root);
  // Auto collapse depth > 1
  treeRoot.descendants().forEach(d => {
    if (d.depth > 1 && d.children) {
      d._children = d.children;
      d.children = null;
    }
  });
}

function renderTree() {
  const svgEl = document.getElementById('canvas');
  const width = svgEl.clientWidth;
  const height = svgEl.clientHeight;

  d3.select('#canvas').selectAll('*').remove();

  const svg = d3.select('#canvas');
  const root_g = svg.append('g').attr('class', 'zoom-root');

  zoomBehavior = d3.zoom().scaleExtent([0.1, 4])
    .on('zoom', (e) => root_g.attr('transform', e.transform));
  svg.call(zoomBehavior);

  const treeLayout = d3.tree().nodeSize([44, 250])
    .separation((a, b) => a.parent === b.parent ? 1 : 1.3);
  treeLayout(treeRoot);

  // Lane headers
  const lanes = ['Aplikasi', 'Menu Utama', 'Fitur / Aksi', 'Validasi & DB'];
  lanes.forEach((l, i) => {
    root_g.append('text')
      .attr('class', 'lane-header')
      .attr('x', i * 250)
      .attr('y', -30)
      .text(l);
  });

  const nodes = treeRoot.descendants();
  const links = treeRoot.links();

  // Links
  root_g.selectAll('.tree-link')
    .data(links).enter().append('path')
    .attr('class', 'tree-link')
    .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x));

  // Node Cards
  const cardW = 190;
  const cardH = 36;

  const nodeG = root_g.selectAll('.tree-node')
    .data(nodes).enter().append('g')
    .attr('class', 'tree-node')
    .attr('transform', d => `translate(${d.y},${d.x})`)
    .on('click', (ev, d) => {
      ev.stopPropagation();
      if (d._children || (d.children && d.depth > 0)) {
        if (d.children) { d._children = d.children; d.children = null; }
        else { d.children = d._children; d._children = null; }
        renderTree();
      }
      selectNode(d);
    });

  nodeG.append('foreignObject')
    .attr('width', cardW)
    .attr('height', cardH)
    .attr('x', -cardW / 2)
    .attr('y', -cardH / 2)
    .html(d => buildCardHTML(d));

  // Center initial view
  const initScale = 0.85;
  const initX = width / 3;
  const initY = height / 2 - (treeRoot.x || 0) * initScale;
  svg.call(zoomBehavior.transform, d3.zoomIdentity.translate(initX, initY).scale(initScale));

  // Stats
  const totalMenus = treeRoot.children ? treeRoot.children.length : 0;
  const totalEndpoints = asArr(SCAN.endpoints).length;
  document.getElementById('stats').textContent = `${totalMenus} Menu Utama · ${totalEndpoints} Endpoints`;

  renderSidebarTree();
}

function buildCardHTML(d) {
  const type = d.data.type || 'feature';
  const label = d.data.name || '—';
  const hasChildren = d._children || d.children;
  const isCollapsed = d._children && !d.children;
  const method = (d.data.method || '').toLowerCase();

  let icon = '🔵';
  if (type === 'root') icon = '🏠';
  if (type === 'menu') icon = '📋';
  if (type === 'validation') icon = '🟣';
  if (type === 'table') icon = '🟡';

  let html = `<div class="card ${type}">`;
  html += `<span class="card-icon">${icon}</span>`;
  html += `<span class="card-label">${label}</span>`;
  if (method) html += `<span class="card-method ${method}">${method}</span>`;
  if (hasChildren) {
    const count = (d._children || d.children).length;
    html += `<span class="card-count">${count}</span>`;
    html += `<span class="card-expand">${isCollapsed ? '▸' : '▾'}</span>`;
  }
  html += '</div>';
  return html;
}

function selectNode(d) {
  selectedNode = d;
  d3.selectAll('.card').classed('selected', false);
  const data = d.data;

  // Show panel
  const panel = document.getElementById('detail');
  panel.classList.add('visible');
  document.getElementById('detail-title').textContent = data.name;
  document.getElementById('detail-subtitle').textContent = data.path || data.type;

  const body = document.getElementById('detail-body');
  let html = '';

  html += `<div class="section"><h4>Tipe Modul</h4><div class="row"><span class="tag">${data.type.toUpperCase()}</span></div></div>`;

  if (data.method) {
    html += `<div class="section"><h4>HTTP Method & Path</h4><div class="row"><span class="tag method-${data.method.toLowerCase()}">${data.method}</span> <code>${data.path}</code></div></div>`;
  }
  if (data.file) {
    html += `<div class="section"><h4>Source File</h4><div class="row"><code>${data.file}</code></div></div>`;
  }
  if (data.type === 'menu') {
    const children = (d.children || d._children || []);
    html += `<div class="section"><h4>Fitur Dalam Menu Ini (${children.length})</h4>`;
    children.forEach(c => {
      html += `<div class="item-link" onclick="focusNode('${c.data.name}')">🔹 ${c.data.name}</div>`;
    });
    html += '</div>';
  }
  if (data.type === 'validation') {
    html += `<div class="section"><h4>Rule Detail</h4><div class="row">Field: <code>${data.field || '—'}</code></div><div class="row">Rule: <code>${data.rule || '—'}</code></div></div>`;
  }
  if (data.type === 'table' && data.columns) {
    html += `<div class="section"><h4>Kolom Table (${data.columns.length})</h4>`;
    data.columns.forEach(col => {
      html += `<div class="row"><code>${col.name}</code> <span style="color:#8b949e">(${col.type})</span></div>`;
    });
    html += '</div>';
  }

  body.innerHTML = html;
}

function closeDetail() {
  document.getElementById('detail').classList.remove('visible');
}

function renderSidebarTree() {
  const treeEl = document.getElementById('node-tree');
  treeEl.innerHTML = '';

  const nodes = treeRoot ? treeRoot.descendants() : [];
  nodes.forEach(d => {
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.style.paddingLeft = (12 + d.depth * 12) + 'px';
    const icon = d.data.type === 'root' ? '🏠' : d.data.type === 'menu' ? '📋' : '🔵';
    item.innerHTML = `<span class="icon">${icon}</span><span class="label">${d.data.name}</span>`;
    item.onclick = () => {
      // expand parents
      let parent = d.parent;
      while (parent) {
        if (parent._children) { parent.children = parent._children; parent._children = null; }
        parent = parent.parent;
      }
      renderTree();
      selectNode(d);
    };
    treeEl.appendChild(item);
  });
}

function filterTree(q) {
  if (!q) { renderSidebarTree(); return; }
  const ql = q.toLowerCase();
  const treeEl = document.getElementById('node-tree');
  treeEl.innerHTML = '';
  treeRoot.descendants().forEach(d => {
    if (d.data.name.toLowerCase().includes(ql)) {
      const item = document.createElement('div');
      item.className = 'tree-item';
      item.innerHTML = `<span class="label">${d.data.name}</span>`;
      item.onclick = () => selectNode(d);
      treeEl.appendChild(item);
    }
  });
}

function focusNode(name) {
  const match = treeRoot.descendants().find(d => d.data.name === name);
  if (match) {
    let parent = match.parent;
    while (parent) {
      if (parent._children) { parent.children = parent._children; parent._children = null; }
      parent = parent.parent;
    }
    renderTree();
    selectNode(match);
  }
}

buildTree();
renderTree();
</script>
</body>
</html>
"""


# ─── Developer Graph HTML Template (Technical / Devs) ────────────────────────

DEV_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ — Developer Graph | CodeMap</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; overflow: hidden; }
#app { display: flex; height: 100vh; }

/* Topbar */
#topbar { position: absolute; top: 0; left: 0; right: 0; height: 48px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; z-index: 200; }
#topbar .title { font-size: 15px; font-weight: 600; color: #3fb950; display: flex; align-items: center; gap: 8px; }
#topbar .mode-switch { display: flex; gap: 8px; align-items: center; }
#topbar .mode-btn { padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; text-decoration: none; cursor: pointer; transition: all 0.15s; border: 1px solid #30363d; }
#topbar .mode-btn.active { background: #238636; color: #fff; border-color: #238636; }
#topbar .mode-btn.inactive { background: #21262d; color: #8b949e; }
#topbar .mode-btn.inactive:hover { color: #c9d1d9; border-color: #58a6ff; }
#topbar .dash-btn { background: #1f6feb; color: #fff; border: none; padding: 5px 12px; border-radius: 6px; font-size: 12px; text-decoration: none; font-weight: 500; }
#topbar .dash-btn:hover { background: #388bfd; }

#main { display: flex; width: 100%; height: calc(100vh - 48px); margin-top: 48px; }

/* Sidebar */
#sidebar { width: 280px; background: #161b22; border-right: 1px solid #30363d; display: flex; flex-direction: column; }
#sidebar-header { padding: 12px 16px; border-bottom: 1px solid #30363d; }
#sidebar-header h3 { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
#filter-box input { width: 100%; padding: 6px 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 4px; color: #c9d1d9; font-size: 12px; font-family: monospace; }
#filter-box input:focus { outline: none; border-color: #3fb950; }
#node-list { flex: 1; overflow-y: auto; }
.node-item { padding: 6px 12px; border-bottom: 1px solid #21262d; cursor: pointer; font-size: 11px; font-family: monospace; display: flex; align-items: center; justify-content: space-between; transition: background 0.1s; }
.node-item:hover { background: #21262d; }
.node-item.selected { background: #23863633; border-left: 3px solid #3fb950; }
.node-item .kind { font-size: 9px; padding: 1px 4px; border-radius: 3px; font-weight: 600; text-transform: uppercase; }
.kind-endpoint { background: #1f6feb33; color: #58a6ff; }
.kind-logic { background: #23863633; color: #3fb950; }
.kind-table { background: #d2992233; color: #d29922; }
.kind-validation { background: #8957e533; color: #a371f7; }

#stats { padding: 10px 16px; border-top: 1px solid #30363d; font-size: 11px; color: #484f58; font-family: monospace; }

/* Canvas */
#canvas-wrap { flex: 1; position: relative; overflow: hidden; background: #0d1117; }
#canvas { width: 100%; height: 100%; cursor: grab; }
#canvas:active { cursor: grabbing; }

/* Detail panel */
#detail { position: absolute; right: 0; top: 0; width: 400px; height: 100%; background: #161b22; border-left: 1px solid #30363d; overflow-y: auto; transform: translateX(100%); transition: transform 0.25s ease; z-index: 100; font-size: 12px; }
#detail.visible { transform: translateX(0); }
#detail .header { padding: 14px 16px; border-bottom: 1px solid #30363d; position: sticky; top: 0; background: #161b22; z-index: 1; }
#detail .header h3 { font-size: 14px; color: #3fb950; font-family: monospace; }
#detail .close-btn { position: absolute; top: 14px; right: 16px; background: none; border: none; color: #8b949e; font-size: 18px; cursor: pointer; }
#detail .section { padding: 12px 16px; border-bottom: 1px solid #21262d; }
#detail .section h4 { font-size: 10px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
#detail code { background: #0d1117; padding: 2px 6px; border-radius: 4px; color: #e6edf3; font-family: monospace; font-size: 11px; }

/* SVG Graph Elements */
.edge { fill: none; stroke: #30363d; stroke-width: 1.5; stroke-opacity: 0.4; }
.edge.highlighted { stroke-opacity: 1 !important; stroke-width: 2.5 !important; stroke: #58a6ff !important; }
.edge.dimmed { stroke-opacity: 0.05 !important; }
.node-box.dimmed { opacity: 0.15; }
.node-circle { stroke-width: 1.5; transition: all 0.15s; }
.node-circle.selected { stroke: #f0e040 !important; stroke-width: 3 !important; }
</style>
</head>
<body>
<div id="app">
  <div id="topbar">
    <div class="title">
      <span>⚡</span>
      <span>__TITLE__</span>
      <span style="font-size:11px;color:#8b949e;font-weight:400">— Developer Force-Directed Graph</span>
    </div>
    <div class="mode-switch">
      <a href="__BIZ_FILE__" class="mode-btn inactive">💼 Alur Bisnis</a>
      <span class="mode-btn active">⚡ Developer Graph</span>
      <a href="dashboard.html" class="dash-btn">🏠 Dashboard</a>
    </div>
  </div>

  <div id="main">
    <div id="sidebar">
      <div id="sidebar-header">
        <h3>Code Nodes</h3>
        <div id="filter-box">
          <input type="text" id="search" placeholder="Filter node / path / SQL..." oninput="filterGraph(this.value)">
        </div>
      </div>
      <div id="node-list"></div>
      <div id="stats"></div>
    </div>

    <div id="canvas-wrap">
      <svg id="canvas"></svg>
      <div id="detail">
        <div class="header">
          <button class="close-btn" onclick="closeDetail()">×</button>
          <h3 id="detail-title">—</h3>
        </div>
        <div id="detail-body"></div>
      </div>
    </div>
  </div>
</div>

<script>
__D3_JS__

const SCAN = __SCAN_DATA__;

const NODES = [];
const EDGES = [];
const NODE_MAP = {};
let simulation = null;
let zoomBehavior = null;

const TYPE_COLORS = {
  endpoint: '#58a6ff',
  logic: '#3fb950',
  table: '#d29922',
  validation: '#a371f7',
  query: '#e3b341',
};

function buildGraphData() {
  let idc = 0;
  function nid() { return 'n' + (idc++); }

  // Endpoints
  (SCAN.endpoints || []).forEach(ep => {
    const id = nid();
    const node = { id, kind: 'endpoint', label: (ep.method || 'GET') + ' ' + ep.path, file: ep.file, line: ep.line, method: ep.method, path: ep.path };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Business Logic
  (SCAN.business_logic || []).forEach(bl => {
    const id = nid();
    const node = { id, kind: 'logic', label: 'fn ' + bl.name, file: bl.file, line: bl.line, name: bl.name };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Database Tables
  Object.entries(SCAN.database?.tables || {}).forEach(([name, info]) => {
    const id = nid();
    const node = { id, kind: 'table', label: 'table ' + name, columns: info.columns || [] };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Validations
  (SCAN.validations || []).slice(0, 50).forEach(v => {
    const id = nid();
    const node = { id, kind: 'validation', label: 'val ' + (v.field || v.rule), rule: v.rule, field: v.field, file: v.file };
    NODES.push(node); NODE_MAP[id] = node;
  });

  // Edges: Endpoint -> Logic (same file)
  NODES.filter(n => n.kind === 'endpoint').forEach(ep => {
    NODES.filter(n => n.kind === 'logic' && n.file === ep.file).forEach(lg => {
      EDGES.push({ source: ep.id, target: lg.id, relation: 'calls' });
    });
  });

  // Edges: Logic -> Validation (same file)
  NODES.filter(n => n.kind === 'logic').forEach(lg => {
    NODES.filter(n => n.kind === 'validation' && n.file === lg.file).forEach(val => {
      EDGES.push({ source: lg.id, target: val.id, relation: 'validates' });
    });
  });
}

function renderGraph() {
  const svgEl = document.getElementById('canvas');
  const width = svgEl.clientWidth;
  const height = svgEl.clientHeight;

  d3.select('#canvas').selectAll('*').remove();

  const svg = d3.select('#canvas');
  const root = svg.append('g').attr('class', 'zoom-root');

  zoomBehavior = d3.zoom().scaleExtent([0.1, 8])
    .on('zoom', (e) => root.attr('transform', e.transform));
  svg.call(zoomBehavior);

  const simNodes = NODES.map(n => ({ ...n }));
  const simEdges = EDGES.map(e => ({ ...e }));

  const link = root.append('g').selectAll('line')
    .data(simEdges).enter().append('line')
    .attr('class', 'edge');

  const nodeG = root.append('g').selectAll('g')
    .data(simNodes).enter().append('g')
    .attr('class', 'node-box')
    .style('cursor', 'pointer')
    .on('click', (ev, d) => selectDevNode(d));

  nodeG.append('circle')
    .attr('class', 'node-circle')
    .attr('r', 8)
    .attr('fill', d => TYPE_COLORS[d.kind] || '#8b949e')
    .attr('stroke', '#0d1117');

  nodeG.append('text')
    .attr('x', 12)
    .attr('y', 4)
    .style('font-size', '10px')
    .style('fill', '#c9d1d9')
    .style('font-family', 'monospace')
    .text(d => d.label);

  simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(d => d.id).distance(60))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(20));

  simulation.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    nodeG.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  document.getElementById('stats').textContent = `${NODES.length} nodes · ${EDGES.length} edges`;
  renderSidebarList();
}

function selectDevNode(d) {
  d3.selectAll('.node-circle').classed('selected', false);
  d3.selectAll('.node-box').filter(n => n.id === d.id).select('circle').classed('selected', true);

  const panel = document.getElementById('detail');
  panel.classList.add('visible');
  document.getElementById('detail-title').textContent = d.label;

  const body = document.getElementById('detail-body');
  let html = `<div class="section"><h4>Kind</h4><code>${d.kind}</code></div>`;
  if (d.file) html += `<div class="section"><h4>File</h4><code>${d.file}:${d.line || 1}</code></div>`;
  if (d.columns) {
    html += `<div class="section"><h4>Schema Kolom</h4>`;
    d.columns.forEach(c => html += `<div style="padding:2px 0"><code>${c.name}</code> (${c.type})</div>`);
    html += '</div>';
  }

  body.innerHTML = html;
}

function closeDetail() {
  document.getElementById('detail').classList.remove('visible');
}

function renderSidebarList() {
  const list = document.getElementById('node-list');
  list.innerHTML = '';
  NODES.forEach(n => {
    const item = document.createElement('div');
    item.className = 'node-item';
    item.innerHTML = `<span>${n.label}</span><span class="kind kind-${n.kind}">${n.kind}</span>`;
    item.onclick = () => selectDevNode(n);
    list.appendChild(item);
  });
}

function filterGraph(q) {
  const list = document.getElementById('node-list');
  list.innerHTML = '';
  const ql = q.toLowerCase();
  NODES.filter(n => n.label.toLowerCase().includes(ql)).forEach(n => {
    const item = document.createElement('div');
    item.className = 'node-item';
    item.innerHTML = `<span>${n.label}</span><span class="kind kind-${n.kind}">${n.kind}</span>`;
    item.onclick = () => selectDevNode(n);
    list.appendChild(item);
  });
}

buildGraphData();
renderGraph();
</script>
</body>
</html>
"""


class DiagramBuilder:
    """Build interactive HTML diagram (business or developer mode)."""

    def build(self, scan_result, title="CodeMap", mode="business", dev_file=None, biz_file=None):
        """Build single mode HTML diagram."""
        d3_js = load_d3()
        scan_json = json.dumps(scan_result, ensure_ascii=False)

        if mode == "developer":
            html = DEV_TEMPLATE.replace("__D3_JS__", d3_js)
            html = html.replace("__SCAN_DATA__", scan_json)
            html = html.replace("__TITLE__", title)
            html = html.replace("__BIZ_FILE__", biz_file or "business.html")
            return html
        else:
            html = BUSINESS_TEMPLATE.replace("__D3_JS__", d3_js)
            html = html.replace("__SCAN_DATA__", scan_json)
            html = html.replace("__TITLE__", title)
            html = html.replace("__DEV_FILE__", dev_file or "developer.html")
            return html

    def build_both(self, scan_result, title="CodeMap"):
        """Build dual mode: returns (business_html, developer_html)."""
        biz = self.build(scan_result, title=title, mode="business", dev_file="developer.html", biz_file="business.html")
        dev = self.build(scan_result, title=title, mode="developer", dev_file="developer.html", biz_file="business.html")
        return biz, dev
