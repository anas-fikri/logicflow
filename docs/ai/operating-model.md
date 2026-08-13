# Operating Model

## Lifecycle

CodeMap mengikuti pipeline `scan → diagram` (non-AI) atau `scan → ai → diagram` (with AI docs).

### Scan Phase
1. User provide source directory
2. Scanner traverse files, detect language by extension
3. Per file: extract routes (regex), validations (AST/heuristic), DB relations (regex), forms (regex), business logic (heuristic)
4. Output: JSON (`scan.json`) dengan struktur: `{endpoints, validations, business_logic, forms, database, files, meta}`

### Diagram Phase
1. Load scan JSON
2. Build 4 views:
   - **Business Flow** (default) — horizontal tree, kiri→kanan: App → Menu → Aksi/API → Validasi & DB. Card-based expand/collapse. Label bahasa Indonesia.
   - **Code Flow** — force-directed graph (D3), semua node + edge. Interaktif: click highlight, detail panel.
   - **Database** — table relations (ERD-style).
   - **Validasi** — list all validation rules, grouped by field.
3. D3.js v7 di-inline di HTML output (279KB bundle).
4. Output: standalone HTML file (buka di browser, no server needed).

### AI Phase (optional)
1. Load scan JSON
2. Kirim ke LLM API (9Router/OmniRoute) dengan prompt template
3. Payload: `{"stream": false, "model": "...", "messages": [...]}`
4. Parse response: reasoning models pakai `reasoning_content`, bukan `content`
5. Output: Markdown documentation per endpoint

### Project Management
- Registry: `~/.codemap/projects.json`
- Per-project output: `~/.codemap/output/<name>/{scan.json,diagram.html}`
- `scan-all` untuk batch re-scan semua project terdaftar

## Source of Truth

| What | Where |
|------|-------|
| Project registry | `~/.codemap/projects.json` |
| Per-project scan data | `~/.codemap/output/<name>/scan.json` |
| Per-project diagram | `~/.codemap/output/<name>/diagram.html` |
| Scanner patterns | `codemap/scanner.py` → `ROUTE_PATTERNS` dict |
| Diagram templates | `codemap/diagram.py` → `build()` method |
| Human labels mapping | `codemap/diagram.py` → `HUMAN_LABELS` dict |
| AI prompt template | `codemap/ai.py` → `generate()` method |
| D3 source | `vendor/d3.v7.min.js` (inline di HTML) |

## Roles

- **Hermes Agent** — primary AI developer untuk CodeMap
- **Codex/Claude Code** — bisa delegate untuk task tertentu (lihat AGENTS.md)
- **User (Anas)** — PM + tester. Approve design, verify usability.