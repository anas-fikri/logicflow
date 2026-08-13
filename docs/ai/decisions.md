# Durable Decisions

## Architecture

### Decision: D3 inline in HTML, not CDN
**Date:** 2026-08-10  
**Reason:** CORS errors when opening local HTML files with CDN D3. Offline reliability requirement. Inline bundle (279KB) ensures file works anywhere.
**Status:** IMPLEMENTED

### Decision: Horizontal tree for Business Flow, force-directed for Code Flow
**Date:** 2026-08-12  
**Reason:** Business user mudah baca tree kiri→kanan. Developer suka explore force-directed untuk understand connections.
**Status:** IMPLEMENTED — 2 separate views in same HTML

### Decision: Indonesian labels + auto-pretty
**Date:** 2026-08-12  
**Reason:** Target user (Anas + tim) Indonesia. Label harus readable. `humanLabel()` auto-convert snake_case/hyphens ke Title Case.
**Status:** IMPLEMENTED — HUMAN_LABELS dict + auto-pretty fallback

### Decision: `stream: false` for all LLM API calls
**Date:** 2026-08-09  
**Reason:** 9Router default SSE streaming. Reasoning models (deepseek-r1) butuh full response parsing — `reasoning_content` field. Streaming incompatible.
**Status:** IMPLEMENTED in `ai.py`

### Decision: Project registry in `~/.codemap/` not in project dir
**Date:** 2026-08-13  
**Reason:** Scan JSON dan HTML output tidak ikut di-commit. Registry di home directory supaya persistensi antar clone. Output per project: `~/.codemap/output/<name>/`.
**Status:** IMPLEMENTED in `project.py`

## Scanner Patterns

### Decision: Regex primary, AST heuristic secondary
**Date:** 2026-08-09  
**Reason:** tree-sitter install + config overhead. Regex catch majority cases (routes, validation, DB). AST needed only for complex PHP multi-line expressions.
**Status:** IMPLEMENTED — regex in `ROUTE_PATTERNS`, AST guards in `_scan_php()`

### Decision: Single-group vs multi-group route patterns
**Date:** 2026-08-13  
**Reason:** Vue Router `path: '/login'` hanya punya 1 capture group (path). Express patterns punya 2 (method + path). Dispatch logic handle both cases — Vue Router routes stored with method inferred from component type.
**Status:** IMPLEMENTED — `len(groups) >= 1` guard for Vue Router

### Decision: `.vue`/`.svelte` files dispatched to JS scanner
**Date:** 2026-08-13  
**Reason:** Vue Router patterns exist in `.ts`/`.js` but also in `router/index.ts`. Dispatch `.vue`/`.svelte` to `_scan_js()` to catch Vue Router definitions.
**Status:** IMPLEMENTED

## Diagram Design

### Decision: Card-based expand/collapse over circle nodes
**Date:** 2026-08-12  
**Reason:** Business user lebih familiar dengan card UI. Expand/collapse lebih natural dari hover tooltip. User approved horizontal tree + cards.
**Status:** IMPLEMENTED — v4 Business Flow tab

### Decision: Badge colors per level (root=grey, menu=pink, feature=blue, sub=orange)
**Date:** 2026-08-12  
**Reason:** Visual hierarchy instantly readable. Badge color menunjukkan depth tanpa perlu hover. Consistent color scheme across all diagrams.
**Status:** IMPLEMENTED — TYPE_COLORS in `diagram.py`

### Decision: 4-lane structure: Aplikasi → Menu → Aksi/API → Validasi & Database
**Date:** 2026-08-12  
**Reason:** Mirrors real app architecture. Business analyst bisa trace dari menu sampai field validasi dan tabel.
**Status:** IMPLEMENTED — lane headers in Business Flow tree

## Performance

### Decision: No lazy-render yet (threshold: 5000 nodes)
**Date:** 2026-08-13  
**Reason:** Max tested: mailcow 819 nodes renders <3s. Lazy-render adds complexity — implement only when real-world >5000 node diagrams appear.
**Status:** FUTURE — next-tasks.md item