#!/usr/bin/env python3
"""
flow.py — flow-based graph renderer (DAG, horizontal, collapsible)
Input: graphify graph.json
Output: self-contained HTML with 3 views:
  - User: entry → API calls → data layer (top-to-bottom flow)
  - Dev: file tree + call hierarchy
  - Manager: app-level overview
"""
import json, sys, argparse
from pathlib import Path
from collections import defaultdict

D3 = open(Path(__file__).parent / "vendor" / "d3.v7.min.js").read()

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; overflow: hidden; height: 100vh; display: flex; flex-direction: column; }

#header { height: 52px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; align-items: center; padding: 0 16px; gap: 12px; flex-shrink: 0; z-index: 10; }
#header h1 { font-size: 15px; font-weight: 600; color: #58a6ff; }
#header .stats { font-size: 12px; color: #8b949e; }

#view-tabs { display: flex; gap: 4px; margin-left: 16px; padding-left: 16px; border-left: 1px solid #30363d; }
.tab { padding: 5px 14px; border-radius: 6px; border: 1px solid #30363d; background: #21262d; color: #c9d1d9; cursor: pointer; font-size: 12px; transition: all 0.15s; }
.tab:hover { background: #30363d; border-color: #58a6ff; }
.tab.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }
.tab[data-view="user"].active { background: #238636; border-color: #238636; }
.tab[data-view="dev"].active { background: #1f6feb; border-color: #1f6feb; }
.tab[data-view="manager"].active { background: #8957e5; border-color: #8957e5; }
.tab[data-view="tree"].active { background: #d29922; border-color: #d29922; }

/* TREE VIEW */
.tree-link { fill: none; stroke: #30363d; stroke-width: 1.5; }
.tree-link.imports { stroke: #58a6ff; stroke-dasharray: 4 2; }
.tree-link.calls { stroke: #3fb950; }
.tree-node { cursor: pointer; }
.tree-node:hover circle { stroke-width: 3px; }
.tree-text { fill: #ffffff; font-size: 11px; font-family: monospace; pointer-events: none; dominant-baseline: middle; text-shadow: 0 0 3px rgba(0,0,0,0.8); }
.tree-badge { fill: #484f58; font-size: 9px; pointer-events: none; }

#body { display: flex; flex: 1; overflow: hidden; }

/* SIDEBAR */
#sidebar { width: 260px; background: #161b22; border-right: 1px solid #30363d; overflow-y: auto; flex-shrink: 0; }
#sidebar h3 { font-size: 11px; text-transform: uppercase; color: #8b949e; margin: 12px 12px 4px; letter-spacing: 0.5px; }
#sidebar input { width: calc(100% - 24px); margin: 8px 12px; padding: 6px 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 12px; }
.tree-item { padding: 5px 12px; cursor: pointer; font-size: 12px; color: #8b949e; display: flex; align-items: center; gap: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tree-item:hover { background: #1f2937; color: #c9d1d9; }
.tree-item.active { background: #1f6feb33; color: #58a6ff; border-right: 2px solid #58a6ff; }
.tree-item .icon { font-size: 10px; width: 12px; flex-shrink: 0; }
.tree-item .count { margin-left: auto; font-size: 10px; color: #484f58; }
.tree-children { padding-left: 16px; display: none; }
.tree-children.open { display: block; }
.tree-item.has-children > .icon { color: #8b949e; }

/* MAIN CANVAS */
#canvas-wrap { flex: 1; overflow: hidden; position: relative; }
#canvas-wrap svg { width: 100%; height: 100%; display: block; }

/* NODE STYLES */
.node-box { cursor: pointer; }
.node-rect { fill: #1f2937; stroke: #30363d; stroke-width: 1.5px; rx: 6; transition: all 0.15s; }
.node-rect:hover { stroke: #58a6ff; stroke-width: 2px; filter: brightness(1.2); }
.node-text { fill: #ffffff; font-size: 11px; font-family: monospace; pointer-events: none; dominant-baseline: middle; font-weight: 500; }
.node-label { fill: #b1bac4; font-size: 9px; font-family: monospace; pointer-events: none; }
.node-rect.type-entry { fill: #0d3b0d; stroke: #238636; }
.node-rect.type-page { fill: #0d1f3b; stroke: #1f6feb; }
.node-rect.type-api { fill: #1f1b3b; stroke: #8957e5; }
.node-rect.type-db { fill: #2d1f1f; stroke: #f85149; }
.node-rect.type-lib { fill: #1f2d1f; stroke: #3fb950; }
.node-rect.type-component { fill: #1f2d3b; stroke: #58a6ff; }
.node-rect.type-file { fill: #21262d; stroke: #484f58; }
.node-rect.highlighted { stroke: #f0e040; stroke-width: 2.5px; filter: brightness(1.3); }
.node-rect.selected { stroke: #58a6ff; stroke-width: 3px; }

/* EDGE STYLES */
.edge { fill: none; stroke: #30363d; stroke-width: 1.5; }
.edge.imports { stroke: #58a6ff; stroke-dasharray: 4 2; }
.edge.calls { stroke: #3fb950; }
.edge.contains { stroke: #484f58; stroke-width: 1; }
.edge.api { stroke: #8957e5; stroke-width: 2; }
.edge:hover { stroke-width: 2.5; }
.edge.highlighted { stroke-width: 3; stroke-opacity: 1; filter: drop-shadow(0 0 4px currentColor); }
.edge.dimmed { stroke-opacity: 0.1; }
.node-rect.dimmed { opacity: 0.25; }
.node-box.dimmed { opacity: 0.25; }
.node-rect.collapsed { stroke-dasharray: 4 3; opacity: 0.6; }
.collapse-badge { fill: #f0e040; font-size: 10px; pointer-events: none; font-weight: 700; text-anchor: middle; dominant-baseline: middle; }

/* TOOLTIP */
#tooltip { position: fixed; background: #1f2937; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; font-size: 12px; color: #c9d1d9; max-width: 300px; z-index: 1000; pointer-events: none; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
#tooltip strong { color: #58a6ff; display: block; margin-bottom: 4px; }
#tooltip .row { margin: 2px 0; }
#tooltip .tag { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; background: #30363d; margin: 2px 2px 2px 0; }

/* LEGEND */
#legend { position: absolute; bottom: 16px; right: 16px; background: #161b22cc; border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; font-size: 11px; backdrop-filter: blur(4px); }
#legend h4 { font-size: 10px; text-transform: uppercase; color: #8b949e; margin-bottom: 6px; }
.legend-item { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
.legend-swatch { width: 20px; height: 3px; border-radius: 2px; }
.legend-swatch.imports { background: #58a6ff; border-top: 3px dashed #58a6ff; height: 0; }
.legend-swatch.calls { background: #3fb950; }
.legend-swatch.contains { background: #484f58; }
.legend-swatch.api { background: #8957e5; height: 4px; }

/* CONTROLS */
#controls { position: absolute; top: 12px; right: 16px; display: flex; gap: 6px; }
.ctrl-btn { padding: 5px 10px; background: #21262d; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; cursor: pointer; font-size: 12px; }
.ctrl-btn:hover { background: #30363d; }

/* NODE DETAIL PANEL */
#detail { position: absolute; top: 0; right: 0; width: 300px; height: 100%; background: #161b22ee; border-left: 1px solid #30363d; padding: 16px; overflow-y: auto; display: none; backdrop-filter: blur(4px); }
#detail.visible { display: block; }
#detail h3 { font-size: 14px; color: #58a6ff; margin-bottom: 8px; word-break: break-all; }
#detail .meta { font-size: 11px; color: #8b949e; margin-bottom: 12px; }
#detail .section { margin: 12px 0; }
#detail .section h4 { font-size: 11px; text-transform: uppercase; color: #8b949e; margin-bottom: 6px; }
#detail .link-item { padding: 4px 0; font-size: 12px; color: #c9d1d9; cursor: pointer; }
#detail .link-item:hover { color: #58a6ff; }
#detail .close-btn { position: absolute; top: 12px; right: 12px; background: none; border: none; color: #8b949e; cursor: pointer; font-size: 18px; }

/* Collapsed node indicator */
.collapsed-indicator { fill: #484f58; font-size: 10px; font-family: monospace; text-anchor: middle; dominant-baseline: middle; pointer-events: none; }

/* Flow columns */
.flow-col { fill: #0d1117; }
.col-label { fill: #8b949e; font-size: 10px; font-family: monospace; text-anchor: middle; }
.col-line { stroke: #21262d; stroke-width: 1; stroke-dasharray: 4 4; }

/* Print */
@media print { #sidebar, #header, #controls, #legend { display: none !important; } #canvas-wrap { width: 100% !important; } }
"""

JS_HEADER = """
const GRAPH_DATA = __GRAPH_DATA__;
const NODES = GRAPH_DATA.nodes;
const EDGES = GRAPH_DATA.edges;
let currentView = 'user';
let highlightedNode = null;
let selectedNode = null;
let nodeMap = {};
NODES.forEach(n => nodeMap[n.id] = n);

// Build adjacency lists
const outEdges = {};
const inEdges = {};
EDGES.forEach(e => {
  if (!outEdges[e.source]) outEdges[e.source] = [];
  if (!inEdges[e.target]) inEdges[e.target] = [];
  outEdges[e.source].push(e);
  inEdges[e.target].push(e);
});

// Node type inference
function inferType(node) {
  const id = node.id;
  const file = node.source_file || '';
  const label = node.label || '';
  if (id === file) return 'file';
  if (file.includes('/pages/') || id.includes('page')) return 'page';
  if (file.includes('/lib/api') || label.startsWith('api') || label.match(/^(login|logout|fetch|get|post|put|delete)/)) return 'api';
  if (file.includes('/components/')) return 'component';
  if (file.includes('server.js') && label.match(/listen|get|post|put|delete|use$/)) return 'api';
  if (id.match(/^(mysql|mongo|postgres|redis|query|db|conn)/i)) return 'db';
  if (label.match(/^(useState|useEffect|useCallback|useMemo|import|export)/)) return 'lib';
  return 'lib';
}
NODES.forEach(n => { if (!n._type) n._type = inferType(n); });

// Build tree from contains edges
function buildTree(rootId) {
  const visited = new Set();
  const layers = [];
  let current = [rootId];
  while (current.length > 0) {
    const next = [];
    const layerNodes = [];
    current.forEach(id => {
      if (visited.has(id)) return;
      visited.add(id);
      const node = nodeMap[id];
      if (node) layerNodes.push(node);
      const children = (outEdges[id] || []).filter(e => e.relation === 'contains').map(e => e.target);
      children.forEach(cid => { if (!visited.has(cid)) next.push(cid); });
    });
    if (layerNodes.length > 0) layers.push(layerNodes);
    current = next;
  }
  return layers;
}

// Entry points
const ENTRY_NODES = NODES.filter(n => n.id === n.source_file);
const APP_ENTRY = ENTRY_NODES.find(n => n.source_file.includes('App.jsx')) || ENTRY_NODES.find(n => n.source_file.includes('server.js'));
"""

# Rest of JS inserted per-view
JS_USER = """
// USER FLOW: entry -> contains -> calls (depth 3)
// Build user-centric call chain
function buildUserFlow() {
  const result = [];
  const seen = new Set();
  const queue = [];
  
  // Start from server entry
  const serverNode = nodeMap['server'] || APP_ENTRY;
  if (serverNode) {
    queue.push({ id: serverNode.id, depth: 0, path: [] });
  }
  
  // Or from pages
  NODES.filter(n => n._type === 'page').forEach(n => {
    queue.push({ id: n.id, depth: 0, path: [] });
  });
  
  const bfs = [];
  const visited = new Set();
  while (queue.length > 0) {
    const { id, depth, path } = queue.shift();
    if (depth > 3 || visited.has(id)) continue;
    visited.add(id);
    const node = nodeMap[id];
    if (!node) continue;
    if (!seen.has(id)) {
      seen.add(id);
      bfs.push({ node, depth, path: [...path, id] });
    }
    // Follow calls + contains edges
    const nextEdges = (outEdges[id] || []).filter(e => ['calls', 'contains', 'method'].includes(e.relation));
    nextEdges.forEach(e => {
      if (!visited.has(e.target)) queue.push({ id: e.target, depth: depth + 1, path: [...path, id] });
    });
  }
  
  // Group by depth layer
  const layers = [];
  for (let d = 0; d <= 3; d++) {
    layers.push(bfs.filter(x => x.depth === d).map(x => ({ node: x.node, children: (outEdges[x.node.id] || []).filter(e => ['calls','contains'].includes(e.relation)).map(e => nodeMap[e.target]).filter(Boolean) })));
  }
  return layers;
}
"""

JS_DEV = """
// DEV FLOW: file-centric call hierarchy
function buildDevFlow() {
  // Group all nodes by source file
  const byFile = {};
  NODES.forEach(n => {
    const f = n.source_file || 'unknown';
    if (!byFile[f]) byFile[f] = [];
    byFile[f].push(n);
  });
  
  // Build hierarchy: file -> contains -> calls
  const files = Object.keys(byFile).sort();
  return files.map(file => {
    const nodes = byFile[file];
    const root = nodes.find(n => n.id === n.source_file) || nodes[0];
    const children = nodes.filter(n => n.id !== root.id);
    return { file, root, children };
  });
}
"""

JS_MANAGER = """
// MANAGER VIEW: app-level summary
function buildManagerView() {
  // Group by directory (app)
  const byDir = {};
  NODES.forEach(n => {
    const file = n.source_file || '';
    const parts = file.split('/');
    const dir = parts.length > 1 ? parts[0] : 'root';
    if (!byDir[dir]) byDir[dir] = { files: new Set(), nodes: [], entryPoints: [], apiCalls: [] };
    byDir[dir].files.add(file);
    byDir[dir].nodes.push(n);
    if (n._type === 'api' || (n.source_file && n.source_file.includes('server.js'))) {
      byDir[dir].apiCalls.push(n);
    }
    if (n.id === n.source_file) byDir[dir].entryPoints.push(n);
  });
  
  return Object.entries(byDir).map(([dir, data]) => ({
    id: dir,
    label: dir,
    files: data.files.size,
    nodes: data.nodes.length,
    entryPoints: data.entryPoints.length,
    apiCalls: data.apiCalls.length,
    children: data.nodes.slice(0, 10), // top nodes
  }));
}
"""

JS_RENDER = """
// Layout constants
const MARGIN = { top: 40, right: 40, bottom: 40, left: 40 };
const NODE_W = 160;
const NODE_H = 36;
const LAYER_GAP = 200;
const NODE_GAP = 12;

function layoutFlowLayers(layers) {
  const svg = d3.select('#canvas');
  svg.selectAll('*').remove();
  
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  const innerW = width - MARGIN.left - MARGIN.right;
  
  // Draw column headers
  const layerLabels = ['Entry', 'Handler', 'Logic', 'Data'];
  layerLabels.forEach((label, i) => {
    const x = MARGIN.left + i * LAYER_GAP + NODE_W / 2;
    svg.append('text').attr('x', x).attr('y', 20)
      .attr('text-anchor', 'middle').attr('class', 'col-label').text(label);
    svg.append('line').attr('x1', x).attr('y1', 28).attr('x2', x).attr('y2', height - MARGIN.bottom)
      .attr('class', 'col-line');
  });
  
  const nodeGroups = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);
  
  layers.forEach((layer, layerIdx) => {
    if (!layer || layer.length === 0) return;
    const x = layerIdx * LAYER_GAP;
    
    const totalH = layer.length * (NODE_H + NODE_GAP) - NODE_GAP;
    const startY = (height - MARGIN.top - MARGIN.bottom - totalH) / 2;
    
    layer.forEach((item, nodeIdx) => {
      const node = item.node || item;
      const y = startY + nodeIdx * (NODE_H + NODE_GAP);
      
      // Draw edge from previous layer
      if (layerIdx > 0 && item.children) {
        item.children.forEach(child => {
          const childNode = typeof child === 'object' ? child : nodeMap[child];
          if (!childNode) return;
          // Find position
        });
      }
      
      // Draw edges (calls from this node)
      (item.children || []).forEach(child => {
        if (!child || !child.id) return;
        const childLayer = layers.slice(layerIdx + 1).findIndex(l => l && l.some(i => (i.node || i).id === child.id));
        if (childLayer < 0) return;
        const tx = (layerIdx + 1 + childLayer) * LAYER_GAP;
      });
      
      // Node group
      const g = nodeGroups.append('g')
        .attr('class', 'node-box')
        .attr('transform', `translate(${x}, ${y})`)
        .on('click', () => selectNode(node))
        .on('mouseover', (event) => showTooltip(event, node))
        .on('mouseout', hideTooltip);
      
      g.append('rect')
        .attr('class', `node-rect type-${node._type || 'lib'}`)
        .attr('width', NODE_W).attr('height', NODE_H);
      
      // Label
      const label = node.label || node.id;
      const displayLabel = label.length > 22 ? label.slice(0, 20) + '…' : label;
      g.append('text').attr('class', 'node-text').attr('x', NODE_W / 2).attr('y', NODE_H / 2)
        .attr('text-anchor', 'middle').text(displayLabel);
      
      // Type badge
      if (node._type) {
        g.append('text').attr('class', 'node-label')
          .attr('x', NODE_W - 4).attr('y', 10)
          .attr('text-anchor', 'end')
          .attr('fill', '#484f58')
          .text(node._type.toUpperCase());
      }
      
      // File location
      if (node.source_file) {
        g.append('text').attr('class', 'node-label')
          .attr('x', 4).attr('y', NODE_H - 6)
          .attr('fill', '#30363d')
          .text(node.source_file.split('/').pop());
      }
    });
  });
  
  // Draw edges on top
  drawEdges(svg, layers);
}

function drawEdges(svg, layers) {
  layers.forEach((layer, li) => {
    if (!layer || li === 0) return;
    layer.forEach((item, ni) => {
      const node = item.node || item;
      const children = item.children || [];
      const prevLayer = layers[li - 1];
      
      children.forEach(child => {
        if (!child || !child.id) return;
        const childNode = typeof child === 'object' ? child : nodeMap[child];
        if (!childNode) return;
        
        // Find previous layer node that connects
        const prevNodes = (outEdges[childNode.id] || [])
          .filter(e => e.relation === 'contains')
          .map(e => nodeMap[e.source])
          .filter(Boolean);
        
        prevNodes.forEach(prev => {
          if (!prev) return;
          const px = (li - 1) * LAYER_GAP + NODE_W;
          const py = (height, startY) => {
            const idx = layers[li-1].findIndex(i => (i.node||i).id === prev.id);
            const totalH = layers[li-1].length * (NODE_H + NODE_GAP) - NODE_GAP;
            const sY = (svg.node().clientHeight - MARGIN.top - MARGIN.bottom - totalH) / 2;
            return sY + idx * (NODE_H + NODE_GAP) + NODE_H / 2;
          };
          
          const startX = (li - 1) * LAYER_GAP + NODE_W;
          const startY2 = py(svg.node().clientHeight, MARGIN.top);
          const endX = li * LAYER_GAP;
          const endY2 = py(svg.node().clientHeight, MARGIN.top);
          
          if (startY2 === null || endY2 === null) return;
          
          svg.append('path')
            .attr('class', `edge ${childNode._type || 'calls'}`)
            .attr('d', `M${startX},${startY2} C${(startX+endX)/2},${startY2} ${(startX+endX)/2},${endY2} ${endX},${endY2}`)
            .style('opacity', 0.6);
        });
      });
    });
  });
}
"""

JS_SHARED = """
function selectNode(node) {
  selectedNode = node;
  d3.selectAll('.node-rect').classed('selected', false);
  d3.selectAll('.node-box').filter(d => (d && d.id) === node.id).select('rect').classed('selected', true);
  
  // Highlight connected edges + nodes, dim rest
  const connected = new Set([node.id]);
  (outEdges[node.id] || []).forEach(e => connected.add(e.target));
  (inEdges[node.id] || []).forEach(e => connected.add(e.source));
  
  d3.selectAll('.node-box').classed('dimmed', d => d && !connected.has(d.id));
  d3.selectAll('.edge').classed('highlighted', function() {
    const s = this.getAttribute('data-source');
    const t = this.getAttribute('data-target');
    return s === node.id || t === node.id;
  });
  d3.selectAll('.edge').classed('dimmed', function() {
    const s = this.getAttribute('data-source');
    const t = this.getAttribute('data-target');
    return s !== node.id && t !== node.id;
  });
  
  showDetail(node);
}

function clearHighlight() {
  d3.selectAll('.node-box').classed('dimmed', false);
  d3.selectAll('.edge').classed('highlighted', false).classed('dimmed', false);
}

function showTooltip(event, node) {
  const tip = document.getElementById('tooltip');
  const type = node._type || 'lib';
  const file = node.source_file || '';
  const loc = node.source_location || '';
  tip.innerHTML = `<strong>${node.label || node.id}</strong>
    <div class="row"><span class="tag">${type}</span>${loc ? '<span class="tag">'+loc+'</span>' : ''}</div>
    <div class="row" style="color:#484f58;font-size:10px">${file}</div>
    <div class="row">↳ ${(outEdges[node.id]||[]).length} calls, ${(inEdges[node.id]||[]).length} refs</div>`;
  tip.style.display = 'block';
  tip.style.left = (event.pageX + 12) + 'px';
  tip.style.top = (event.pageY - 10) + 'px';
}

function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

function showDetail(node) {
  const panel = document.getElementById('detail');
  panel.classList.add('visible');
  
  const outgoing = (outEdges[node.id] || []).map(e => nodeMap[e.target]).filter(Boolean);
  const incoming = (inEdges[node.id] || []).map(e => nodeMap[e.source]).filter(Boolean);
  
  panel.innerHTML = `
    <button class="close-btn" onclick="closeDetail()">×</button>
    <h3>${node.label || node.id}</h3>
    <div class="meta">
      <div><span class="tag">${node._type || 'lib'}</span></div>
      <div style="margin-top:4px">${node.source_file || ''} ${node.source_location || ''}</div>
    </div>
    <div class="section">
      <h4>Calls (${outgoing.length})</h4>
      ${outgoing.slice(0,20).map(e => `<div class="link-item" onclick="focusNode('${e.id}')">${e.label || e.id}</div>`).join('')}
      ${outgoing.length > 20 ? `<div style="color:#484f58;font-size:11px">+${outgoing.length-20} more</div>` : ''}
    </div>
    <div class="section">
      <h4>Called by (${incoming.length})</h4>
      ${incoming.slice(0,20).map(e => `<div class="link-item" onclick="focusNode('${e.id}')">${e.label || e.id}</div>`).join('')}
      ${incoming.length > 20 ? `<div style="color:#484f58;font-size:11px">+${incoming.length-20} more</div>` : ''}
    </div>
  `;
}

function closeDetail() {
  document.getElementById('detail').classList.remove('visible');
  d3.selectAll('.node-rect').classed('selected', false);
  selectedNode = null;
  clearHighlight();
}

function focusNode(id) {
  const node = nodeMap[id];
  if (!node) return;
  closeDetail();
  // Highlight and scroll
  d3.selectAll('.node-rect').classed('highlighted', d => d && d.id === id);
  const box = d3.selectAll('.node-box').filter(d => d && d.id === id);
  box.each(function(d) {
    const transform = d3.select(this).attr('transform');
    const match = transform.match(/translate\(([^,]+),([^)]+)\)/);
    if (match) {
      const svg = d3.select('#canvas');
      svg.transition().duration(500).attr('transform', 
        `translate(${-parseFloat(match[1])+svg.node().clientWidth/2},${-parseFloat(match[2])+svg.node().clientHeight/2})`);
    }
  });
}

function renderView(view) {
  currentView = view;
  collapsedNodes.clear();
  clearHighlight();
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === view));
  
  if (view === 'user') {
    const layers = buildUserFlow();
    renderFlow(layers);
    renderSidebar_user();
  } else if (view === 'dev') {
    renderDevView();
    renderSidebar_dev();
  } else if (view === 'tree') {
    renderTreeView();
    renderSidebar_tree();
  } else if (view === 'manager') {
    renderManagerView();
    renderSidebar_manager();
  }
}

// --- TREE VIEW (conventional hierarchy) ---
function buildTreeData() {
  // Build file → children hierarchy from contains edges
  const fileMap = {};
  NODES.forEach(n => {
    const f = n.source_file || 'unknown';
    if (!fileMap[f]) fileMap[f] = { id: 'file:' + f, label: f.split('/').pop(), type: 'file', file: f, children: [] };
    fileMap[f].children.push({ id: n.id, label: n.label || n.id, type: n._type || 'lib', file: f, loc: n.source_location || '' });
  });
  
  // Group files by directory
  const dirMap = {};
  Object.values(fileMap).forEach(fn => {
    const parts = fn.file.split('/');
    const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : 'root';
    if (!dirMap[dir]) dirMap[dir] = { id: 'dir:' + dir, label: dir, type: 'dir', children: [] };
    dirMap[dir].children.push(fn);
  });
  
  // Root
  const root = { id: 'root', label: 'Project', type: 'root', children: Object.values(dirMap) };
  return root;
}

function renderTreeView() {
  const svg = d3.select('#canvas');
  svg.selectAll('*').remove();
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  
  const root = d3.hierarchy(buildTreeData());
  const treeLayout = d3.tree().size([height - 80, width - 200]);
  treeLayout(root);
  
  const g = svg.append('g').attr('transform', 'translate(80, 40)');
  
  // Links
  g.selectAll('.tree-link')
    .data(root.links())
    .join('path')
    .attr('class', 'tree-link')
    .attr('d', d3.linkHorizontal()
      .x(d => d.y)
      .y(d => d.x));
  
  // Nodes
  const nodes = g.selectAll('.tree-node')
    .data(root.descendants())
    .join('g')
    .attr('class', 'tree-node')
    .attr('transform', d => `translate(${d.y},${d.x})`)
    .on('click', (event, d) => {
      if (d.data.file && d.data.id) selectNode(nodeMap[d.data.id] || { id: d.data.id, label: d.data.label, source_file: d.data.file, _type: d.data.type });
    })
    .on('mouseover', (event, d) => {
      if (d.data.id && nodeMap[d.data.id]) showTooltip(event, nodeMap[d.data.id]);
    })
    .on('mouseout', hideTooltip);
  
  nodes.append('circle')
    .attr('r', d => d.data.type === 'file' ? 5 : d.data.type === 'dir' ? 7 : 4)
    .attr('fill', d => {
      const colors = { root: '#58a6ff', dir: '#d29922', file: '#8957e5', page: '#1f6feb', api: '#8957e5', component: '#58a6ff', lib: '#3fb950', db: '#f85149' };
      return colors[d.data.type] || '#79c0ff';
    })
    .attr('stroke', '#30363d')
    .attr('stroke-width', 1.5);
  
  nodes.append('text')
    .attr('class', 'tree-text')
    .attr('x', d => d.children ? -10 : 10)
    .attr('text-anchor', d => d.children ? 'end' : 'start')
    .text(d => {
      const label = d.data.label || d.data.id;
      return label.length > 28 ? label.slice(0, 26) + '…' : label;
    });
  
  // Badge: node count per file
  nodes.filter(d => d.data.type === 'file' && d.data.children)
    .append('text')
    .attr('class', 'tree-badge')
    .attr('x', 10).attr('y', 12)
    .text(d => d.data.children.length + ' nodes');
}

function renderSidebar_tree() {
  const sidebar = document.getElementById('file-list');
  sidebar.innerHTML = '<h3>Directory Tree</h3>';
  
  const data = buildTreeData();
  function renderNode(node, depth) {
    const div = document.createElement('div');
    div.className = 'tree-item';
    div.style.paddingLeft = (12 + depth * 16) + 'px';
    const icon = node.type === 'dir' ? '📂' : node.type === 'file' ? '📄' : '•';
    div.innerHTML = `<span class="icon">${icon}</span>${node.label}<span class="count">${(node.children||[]).length}</span>`;
    div.onclick = () => { closeDetail(); if (node.id && nodeMap[node.id]) focusNode(node.id); };
    sidebar.appendChild(div);
    if (node.children) node.children.forEach(c => renderNode(c, depth + 1));
  }
  data.children.forEach(d => renderNode(d, 0));
}

function renderFlow(layers, preserveCollapse) {
  const svg = d3.select('#canvas');
  if (!preserveCollapse) collapsedNodes.clear();
  svg.selectAll('*').remove();
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  
  // Define arrowhead markers
  const defs = svg.append('defs');
  const edgeTypes = [
    { name: 'arrow-default', color: '#58a6ff' },
    { name: 'arrow-imports', color: '#58a6ff' },
    { name: 'arrow-calls', color: '#3fb950' },
    { name: 'arrow-contains', color: '#484f58' },
    { name: 'arrow-api', color: '#8957e5' },
    { name: 'arrow-highlight', color: '#f0e040' },
  ];
  edgeTypes.forEach(t => {
    defs.append('marker')
      .attr('id', t.name).attr('viewBox', '0 -5 10 10')
      .attr('refX', 10).attr('refY', 0).attr('markerWidth', 7).attr('markerHeight', 7)
      .attr('orient', 'auto-start-reverse')
      .append('path').attr('d', 'M0,-5 L10,0 L0,5').attr('fill', t.color);
  });
  
  // Column labels
  const labels = ['Entry', 'Handler', 'Logic', 'Data'];
  labels.forEach((l, i) => {
    svg.append('text').attr('x', MARGIN.left + i * LAYER_GAP + NODE_W/2)
      .attr('y', 20).attr('text-anchor', 'middle').attr('class', 'col-label').text(l);
    svg.append('line').attr('x1', MARGIN.left + i * LAYER_GAP)
      .attr('y1', 30).attr('x2', MARGIN.left + i * LAYER_GAP).attr('y2', height)
      .attr('class', 'col-line').attr('transform', `translate(0,${MARGIN.top})`);
  });
  
  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);
  const edgeLayer = g.append('g').attr('class', 'edge-layer');
  const nodeLayer = g.append('g').attr('class', 'node-layer');
  
  // Store positions for edge drawing
  const positions = {};
  
  // Filter out children of collapsed nodes
  const visibleLayers = layers.map((layer, li) => {
    return (layer || []).filter(item => {
      const node = item.node || item;
      // Check if any ancestor is collapsed
      const parents = (inEdges[node.id] || []).map(e => e.source);
      return !parents.some(p => collapsedNodes.has(p));
    });
  });
  
  visibleLayers.forEach((layer, li) => {
    if (!layer || layer.length === 0) return;
    const x = li * LAYER_GAP;
    const totalH = layer.length * (NODE_H + NODE_GAP) - NODE_GAP;
    const startY = Math.max(0, (height - MARGIN.top - MARGIN.bottom - totalH) / 2);
    
    layer.forEach((item, ni) => {
      const node = item.node || item;
      const y = startY + ni * (NODE_H + NODE_GAP);
      positions[node.id] = { x, y, li, ni };
    });
  });
  
  // Draw edges first (behind nodes)
  visibleLayers.forEach((layer, li) => {
    if (!layer || li === 0) return;
    layer.forEach((item, ni) => {
      const node = item.node || item;
      const pos = positions[node.id];
      if (!pos) return;
      
      const parents = (inEdges[node.id] || []).map(e => ({ edge: e, source: nodeMap[e.source] })).filter(p => p.source);
      parents.forEach(({ edge: rel, source: parent }) => {
        const ppos = positions[parent.id];
        if (!ppos) return;
        
        const cls = rel ? `edge ${rel.relation}` : 'edge';
        const marker = rel ? `arrow-${rel.relation}` : 'arrow-default';
        const startX = ppos.x + NODE_W;
        const startY2 = ppos.y + NODE_H / 2;
        const endX = pos.x;
        const endY = pos.y + NODE_H / 2;
        
        edgeLayer.append('path')
          .attr('class', cls)
          .attr('data-source', parent.id)
          .attr('data-target', node.id)
          .attr('marker-end', `url(#${marker})`)
          .attr('d', `M${startX},${startY2} C${startX+40},${startY2} ${endX-40},${endY} ${endX},${endY}`)
          .style('opacity', 0.6);
      });
    });
  });
  
  // Draw nodes
  visibleLayers.forEach((layer, li) => {
    if (!layer || layer.length === 0) return;
    const x = li * LAYER_GAP;
    const totalH = layer.length * (NODE_H + NODE_GAP) - NODE_GAP;
    const startY = Math.max(0, (height - MARGIN.top - MARGIN.bottom - totalH) / 2);
    
    layer.forEach((item, ni) => {
      const node = item.node || item;
      const y = startY + ni * (NODE_H + NODE_GAP);
      const isCollapsed = collapsedNodes.has(node.id);
      const hasChildren = (outEdges[node.id] || []).some(e => ['calls','contains','method'].includes(e.relation));
      
      const ng = nodeLayer.append('g').attr('class', 'node-box').attr('transform', `translate(${x},${y})`)
        .datum(node)
        .on('click', (event) => { event.stopPropagation(); selectNode(node); })
        .on('dblclick', function(event) {
          event.stopPropagation();
          if (hasChildren) toggleCollapse(node.id);
        })
        .on('mouseover', function(event) { d3.select(this).select('rect').attr('stroke-width', 2.5); showTooltip(event, node); })
        .on('mouseout', function() { d3.select(this).select('rect').attr('stroke-width', 1.5); hideTooltip(); });
      
      ng.append('rect')
        .attr('class', `node-rect type-${node._type||'lib'}${isCollapsed ? ' collapsed' : ''}`)
        .attr('width', NODE_W).attr('height', NODE_H);
      
      const label = (node.label||node.id).slice(0, 22);
      ng.append('text').attr('class', 'node-text').attr('x', NODE_W/2).attr('y', NODE_H/2).attr('text-anchor', 'middle').text(label);
      
      if (node._type) {
        ng.append('text').attr('class', 'node-label').attr('x', NODE_W-4).attr('y', 10).attr('text-anchor','end').attr('fill','#b1bac4').text(node._type.toUpperCase());
      }
      
      // Collapse/expand badge
      if (hasChildren) {
        ng.append('text').attr('class', 'collapse-badge').attr('x', 12).attr('y', NODE_H/2)
          .text(isCollapsed ? '▶' : '▼');
      }
    });
  });
  
  // Store layout for re-render
  currentLayout = { positions, visibleLayers };
}

function renderSidebar_user() {
  const sidebar = document.getElementById('file-list');
  sidebar.innerHTML = '<h3>Entry Points</h3>';
  
  const entries = ENTRY_NODES.slice(0, 20);
  entries.forEach(n => {
    const div = document.createElement('div');
    div.className = 'tree-item';
    div.innerHTML = `<span class="icon">▸</span>${n.label || n.id}<span class="count">${(outEdges[n.id]||[]).length}</span>`;
    div.onclick = () => { closeDetail(); focusNode(n.id); };
    sidebar.appendChild(div);
  });
}

function renderDevView() {
  const svg = d3.select('#canvas');
  svg.selectAll('*').remove();
  const files = [...new Set(NODES.map(n => n.source_file))].filter(Boolean).sort();
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  
  const BOX_W = 200;
  const BOX_H = 300;
  const COLS = Math.max(1, Math.floor((width - MARGIN.left - MARGIN.right) / (BOX_W + 20)));
  
  files.forEach((file, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    const x = MARGIN.left + col * (BOX_W + 20);
    const y = MARGIN.top + row * (BOX_H + 20);
    
    const fileNodes = NODES.filter(n => n.source_file === file);
    const root = fileNodes.find(n => n.id === n.source_file) || fileNodes[0];
    const children = fileNodes.filter(n => n.id !== root?.id).slice(0, 12);
    
    const fg = svg.append('g').attr('transform', `translate(${x},${y})`);
    
    // File box
    fg.append('rect').attr('class', 'node-rect type-file').attr('width', BOX_W).attr('height', BOX_H).attr('rx', 8);
    fg.append('text').attr('class', 'node-text').attr('x', 10).attr('y', 20).text((file.split('/').pop() || file).slice(0, 28));
    fg.append('text').attr('class', 'node-label').attr('x', 10).attr('y', 34).attr('fill', '#484f58').text(file);
    
    // Children nodes
    children.forEach((child, ci) => {
      const cy = 50 + ci * 20;
      const rel = (outEdges[child.id]||[])[0];
      
      fg.append('circle').attr('cx', 8).attr('cy', cy+6).attr('r', 2).attr('fill', rel ? '#3fb950' : '#484f58');
      fg.append('text').attr('class', 'node-label').attr('x', 16).attr('y', cy+8)
        .attr('fill', '#8b949e').text((child.label||child.id).slice(0, 26));
    });
    
    if (children.length > 12) {
      fg.append('text').attr('class', 'node-label').attr('x', 10).attr('y', 50+12*20+10)
        .attr('fill', '#484f58').text(`+${children.length-12} more`);
    }
    
    // Entry indicator
    if (root && root.id === root.source_file) {
      fg.append('rect').attr('x', BOX_W-30).attr('y', 4).attr('width', 26).attr('height', 14)
        .attr('fill', '#238636').attr('rx', 3);
      fg.append('text').attr('x', BOX_W-17).attr('y', 14).attr('text-anchor','middle')
        .attr('fill', '#fff').attr('font-size', '8').text('ROOT');
    }
  });
}

function renderSidebar_dev() {
  const sidebar = document.getElementById('file-list');
  sidebar.innerHTML = '<h3>Files</h3>';
  
  const files = [...new Set(NODES.map(n => n.source_file))].filter(Boolean).sort();
  files.forEach(file => {
    const nodes = NODES.filter(n => n.source_file === file);
    const div = document.createElement('div');
    div.className = 'tree-item has-children';
    div.innerHTML = `<span class="icon">▸</span>${file.split('/').pop()}<span class="count">${nodes.length}</span>`;
    div.onclick = () => { closeDetail(); focusFile(file); };
    sidebar.appendChild(div);
  });
}

function focusFile(file) {
  const svg = d3.select('#canvas');
  const files = [...new Set(NODES.map(n => n.source_file))].filter(Boolean).sort();
  const i = files.indexOf(file);
  if (i < 0) return;
  const BOX_W = 200, BOX_H = 300, COLS = Math.max(1, Math.floor((svg.node().clientWidth - MARGIN.left - MARGIN.right) / (BOX_W + 20)));
  const col = i % COLS;
  const row = Math.floor(i / COLS);
  const x = MARGIN.left + col * (BOX_W + 20);
  const y = MARGIN.top + row * (BOX_H + 20);
  svg.transition().duration(500).attr('transform', `translate(${-x + svg.node().clientWidth/2 - BOX_W/2},${-y + svg.node().clientHeight/2 - BOX_H/2})`);
}

function renderManagerView() {
  const svg = d3.select('#canvas');
  svg.selectAll('*').remove();
  const width = svg.node().clientWidth;
  const height = svg.node().clientHeight;
  
  const data = buildManagerView();
  const APP_W = 220, APP_H = 160, GAP = 30;
  const COLS = Math.max(1, Math.floor((width - MARGIN.left - MARGIN.right) / (APP_W + GAP)));
  
  data.forEach((app, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    const x = MARGIN.left + col * (APP_W + GAP);
    const y = MARGIN.top + row * (APP_H + GAP);
    
    const ag = svg.append('g').attr('transform', `translate(${x},${y})`);
    ag.append('rect').attr('class', 'node-rect type-file').attr('width', APP_W).attr('height', APP_H).attr('rx', 8)
      .on('click', () => { closeDetail(); focusApp(app.id); });
    
    ag.append('text').attr('x', 12).attr('y', 24).attr('fill', '#58a6ff').attr('font-size', '13').attr('font-weight', '600').text(app.label);
    
    const stats = [
      `📁 ${app.files} files`,
      `▣ ${app.nodes} nodes`,
      `→ ${app.apiCalls} API`,
      `◎ ${app.entryPoints} entries`,
    ];
    stats.forEach((s, si) => {
      ag.append('text').attr('x', 12).attr('y', 44 + si * 18).attr('fill', '#8b949e').attr('font-size', '11').text(s);
    });
  });
}

function renderSidebar_manager() {
  const sidebar = document.getElementById('file-list');
  sidebar.innerHTML = '<h3>Apps / Modules</h3>';
  
  const data = buildManagerView();
  data.forEach(app => {
    const div = document.createElement('div');
    div.className = 'tree-item';
    div.innerHTML = `<span class="icon">▤</span>${app.label}<span class="count">${app.nodes}</span>`;
    div.onclick = () => { closeDetail(); focusApp(app.id); };
    sidebar.appendChild(div);
  });
}

function focusApp(dirId) {
  const svg = d3.select('#canvas');
  const data = buildManagerView();
  const i = data.findIndex(a => a.id === dirId);
  if (i < 0) return;
  const APP_W = 220, APP_H = 160, GAP = 30;
  const COLS = Math.max(1, Math.floor((svg.node().clientWidth - MARGIN.left - MARGIN.right) / (APP_W + GAP)));
  const col = i % COLS;
  const row = Math.floor(i / COLS);
  const x = MARGIN.left + col * (APP_W + GAP);
  const y = MARGIN.top + row * (APP_H + GAP);
  svg.transition().duration(500).attr('transform', `translate(${-x + svg.node().clientWidth/2 - APP_W/2},${-y + svg.node().clientHeight/2 - APP_H/2})`);
}

// Zoom + pan
function initZoom() {
  const svg = d3.select('#canvas');
  // Disable dblclick zoom — we use it for collapse/expand
  const zoom = d3.zoom().scaleExtent([0.05, 8])
    .filter(e => !e.target.closest('.node-box') || e.type !== 'dblclick')
    .on('zoom', e => svg.attr('transform', e.transform));
  svg.call(zoom);
  svg.on('dblclick.zoom', null); // disable zoom on canvas dblclick
}

// Track collapse state
let collapsedNodes = new Set();
let currentLayout = null; // {nodes, edges, positions}

function toggleCollapse(nodeId) {
  if (collapsedNodes.has(nodeId)) {
    collapsedNodes.delete(nodeId);
  } else {
    collapsedNodes.add(nodeId);
  }
  if (currentView === 'user') {
    const layers = buildUserFlow();
    renderFlow(layers, true);
  }
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Flow Diagram</title>
<script>""" + D3 + """</script>
<style>""" + CSS + """</style>
</head>
<body>

<div id="header">
  <h1>{title}</h1>
  <div class="stats" id="stats"></div>
  <div id="view-tabs">
    <button class="tab active" data-view="user" onclick="renderView('user')">User</button>
    <button class="tab" data-view="dev" onclick="renderView('dev')">Developer</button>
    <button class="tab" data-view="tree" onclick="renderView('tree')">Tree</button>
    <button class="tab" data-view="manager" onclick="renderView('manager')">Manager</button>
  </div>
</div>

<div id="body">
  <div id="sidebar">
    <input type="text" id="search" placeholder="Filter nodes..." oninput="filterNodes(this.value)">
    <div id="file-list"></div>
  </div>
  <div id="canvas-wrap">
    <svg id="canvas"></svg>
    <div id="controls">
      <button class="ctrl-btn" onclick="d3.select('#canvas').attr('transform','');">Reset</button>
      <button class="ctrl-btn" onclick="window.print()">PDF</button>
    </div>
    <div id="legend">
      <h4>Edge Types</h4>
      <div class="legend-item"><div class="legend-swatch calls"></div>imports</div>
      <div class="legend-item"><div class="legend-swatch calls"></div>calls</div>
      <div class="legend-item"><div class="legend-swatch contains"></div>contains</div>
      <div class="legend-item"><div class="legend-swatch api"></div>API</div>
      <div class="legend-item"><div class="legend-swatch" style="background:#30363d;height:0;border-top:3px solid #30363d;border-bottom:3px solid #30363d"></div>external ref</div>
    </div>
    <div id="detail"></div>
  </div>
</div>

<div id="tooltip"></div>

<script>
// --- Constants ---
const MARGIN = {top: 60, right: 40, bottom: 40, left: 40};
const NODE_W = 160, NODE_H = 36, LAYER_GAP = 200, NODE_GAP = 12;

// --- Data ---
""" + JS_HEADER + """

// --- Views ---
""" + JS_USER + """
""" + JS_DEV + """
""" + JS_MANAGER + """

// --- Shared ---
""" + JS_SHARED + """

// --- Init ---
document.getElementById('stats').textContent = `${NODES.length} nodes · ${EDGES.length} edges`;
initZoom();
renderView('user');
</script>
</body>
</html>"""

def main():
    p = argparse.ArgumentParser(description="Flow-based diagram renderer")
    p.add_argument('graph', help='graphify graph.json')
    p.add_argument('--title', '-t', default='')
    p.add_argument('--output', '-o', default='')
    a = p.parse_args()
    
    graph = json.load(open(a.graph))
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    
    # Filter dangling edges
    node_ids = {n['id'] for n in nodes}
    clean_edges = [e for e in edges if e['source'] in node_ids and e['target'] in node_ids]
    
    clean_nodes = []
    seen = set()
    for n in nodes:
        if n['id'] not in seen:
            seen.add(n['id'])
            clean_nodes.append(n)
    
    graph_data = {'nodes': clean_nodes, 'edges': clean_edges}
    
    title = a.title or Path(a.graph).parent.parent.name
    
    html = HTML_TEMPLATE.replace('__GRAPH_DATA__', json.dumps(graph_data))
    html = html.replace('{title}', title)
    
    output = Path(a.output) if a.output else Path('flow-diagram.html')
    output.write_text(html, encoding='utf-8')
    print(f"Wrote {output} ({output.stat().st_size // 1024} KB)")


if __name__ == '__main__':
    main()
