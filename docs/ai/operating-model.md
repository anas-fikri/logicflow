# Operating Model

## Lifecycle

LogicFlow mengikuti pipeline `scan → diagram` (non-AI) atau `scan → ai → diagram` (with AI docs).

### Scan Phase
1. User provide source directory
2. Scanner traverse files, detect language by extension
3. Per file: extract routes (regex), validations (AST/heuristic), DB relations (regex), forms (regex), business logic (heuristic)
4. Output: JSON (`scan.json`) dengan struktur: `{endpoints, validations, business_logic, forms, database, files, meta}`

### Diagram Phase
1. Load scan JSON
2. **Otomatis** menghasilkan **2 file HTML** sekaligus:
   - `business.html` — **Business Flow**: horizontal tree kiri→kanan: App → Menu → Aksi/API → Validasi & DB. Card-based expand/collapse. Label Bahasa Indonesia. Legend Singkatan & Istilah.
   - `developer.html` — **Developer Graph**: D3.js (*Data-Driven Documents*) force-directed graph, semua node + edge. Interaktif: klik highlight, detail panel. Legend Tipe Node & Singkatan.
3. D3.js v7 di-inline di setiap HTML output (279 KB bundle, offline-ready, tanpa CDN).
4. Setiap file HTML self-contained — buka langsung di browser, tanpa server.
5. Topbar mode-switch di setiap diagram menghubungkan ke counterpart + Dashboard.

### AI Phase (optional)
1. Load scan JSON
2. Kirim ke LLM API (9Router/OmniRoute) dengan prompt template
3. Payload: `{"stream": false, "model": "...", "messages": [...]}`
4. Parse response: reasoning models pakai `reasoning_content`, bukan `content`
5. Output: Markdown documentation per endpoint

### Project Management
- Registry: `~/.logicflow/projects.json`
- Per-project output: `~/.logicflow/output/<name>/{scan.json,diagram.html}`
- `scan-all` untuk batch re-scan semua project terdaftar

## Source of Truth

| What | Where |
|------|-------|
| Project registry | `~/.logicflow/projects.json` |
| Per-project scan data | `~/.logicflow/output/<name>/scan.json` |
| Business Flow diagram | `~/.logicflow/output/<name>/business.html` |
| Developer Graph diagram | `~/.logicflow/output/<name>/developer.html` |
| Unified Dashboard | `~/.logicflow/dashboard.html` |
| Scanner patterns | `logicflow/scanner.py` → `ROUTE_PATTERNS` dict |
| Business diagram template | `logicflow/diagram.py` → `BusinessDiagramBuilder` |
| Developer diagram template | `logicflow/diagram.py` → `DevDiagramBuilder` |
| Human labels mapping | `logicflow/diagram.py` → `HUMAN_LABELS` dict |
| Dashboard template | `logicflow/dashboard.py` → `DashboardBuilder` |
| AI prompt template | `logicflow/ai.py` → `generate()` method |
| D3.js source | `vendor/d3.v7.min.js` (inline di HTML output) |

## Roles

- **Hermes Agent** — primary AI developer untuk LogicFlow
- **Codex/Claude Code** — bisa delegate untuk task tertentu (lihat AGENTS.md)
- **User (Anas)** — PM + tester. Approve design, verify usability.