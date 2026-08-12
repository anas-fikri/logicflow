# apps-diagram

CLI tools untuk visualisasi dan analisis source code.

## CodeMap — Corporate AI Source Scanner

Corporate AI Agent untuk memindai source code aplikasi. Dua mode operasi:

### Mode Non-AI (scan)
AST-based extraction — no AI required:
- Endpoint API (method, path, file, line)
- Validasi input (form/page validation rules)
- Database relations (tables, columns, queries)
- Controller & business logic detection
- Import/dependency mapping
- Output: JSON + Markdown

### Mode AI (ai)
LLM-powered documentation:
- Natural language docs dari scan result
- Arsitektur overview
- Business flow explanation
- Onboarding guide untuk developer baru
- Output: Markdown (natural language)

### Mode Diagram
Interactive HTML/SVG diagram:
- Click node → highlight connected edges + detail panel
- Validation rules per node
- Database relations view
- Tab views (default, database, validation)
- Pure SVG/HTML5 — no Mermaid.js
- D3.js inline (offline-ready)

---

## Usage

```bash
cd ~/Documents/Projects/others/apps-diagram

# Scan only (JSON + Markdown)
python3 -m codemap scan /path/to/project --languages js,ts,py --format both

# Scan + AI docs (needs AI_API_URL + AI_API_KEY env vars)
AI_API_URL="http://localhost:20128/v1/chat/completions" \
AI_API_KEY="your-key" \
python3 -m codemap ai /path/to/project --model "auto/fast"

# Scan + interactive diagram
python3 -m codemap diagram /path/to/project --title "My App"

# Full pipeline: scan → AI docs → diagram
python3 -m codemap full /path/to/project --output myapp
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AI_API_URL` | — | LLM API endpoint (e.g. `http://localhost:20128/v1/chat/completions`) |
| `AI_API_KEY` | — | API key for LLM service |
| `AI_MODEL` | `auto/best-chat` | Model to use |

### CLI Options

```
scan:
  --languages    Comma-separated: js,ts,py,php,go,java,cs,rb,sh,sql  (default: all)
  --exclude      Comma-separated patterns to skip (default: node_modules,.git,dist,build)
  --format       json | markdown | both  (default: both)
  --output       Output file path

ai:
  --scan-only    Use existing scan JSON instead of re-scanning
  --context      Business context description (helps LLM generate better docs)
  --model        Model ID (default: auto/best-chat)

diagram:
  --scan         Re-scan instead of using --graph
  --graph        Use existing scan JSON / graph.json
  --title        Diagram title

full:
  (combines scan + ai + diagram in one command)
```

---

## Output Files

| File | Description |
|---|---|
| `codemap.json` | Structured scan result (endpoints, validations, DB, logic) |
| `codemap.md` | Markdown summary dari scan |
| `codemap-ai.md` | Natural language docs dari LLM |
| `codemap.html` | Interactive diagram |

---

## Supported Languages

| Language | Endpoints | Validation | DB Relations | Logic |
|---|---|---|---|---|
| JavaScript/TypeScript | ✅ | ✅ | ✅ | ✅ |
| Python | ✅ | ✅ | ✅ | ✅ |
| PHP | ✅ | ✅ | ✅ | ✅ |
| Go | ✅ | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ✅ | ✅ |
| C# | ✅ | ✅ | ✅ | ✅ |
| Ruby | ✅ | ✅ | ✅ | ✅ |
| Shell | ✅ | — | — | ✅ |
| SQL | — | — | ✅ | — |

---

## Architecture

```
codemap/
├── __init__.py       Version 1.0.0
├── __main__.py       CLI entry, mode dispatch (scan/ai/diagram/full)
├── scanner.py        AST extraction engine (endpoints, validations, DB, logic)
├── ai.py             LLM documentation generator
├── diagram.py        Interactive SVG/HTML diagram builder
└── parsers/          Modular per-language parsers (extensible)
```

### Scanner Extractor Fields

**Endpoints:**
```json
{
  "method": "GET|POST|PUT|DELETE|PATCH",
  "path": "/api/users/:id",
  "file": "src/routes/users.js",
  "line": 42,
  "auth": "optional|required|none",
  "validation": ["email", "min_length:8"]
}
```

**Validations:**
```json
{
  "rule": "email",
  "field": "user_email",
  "file": "src/forms/register.vue",
  "line": 15,
  "type": "format"
}
```

**Database Relations:**
```json
{
  "table": "users",
  "columns": [{"name": "id", "type": "INT"}, {"name": "email", "type": "VARCHAR"}],
  "query": "SELECT * FROM users WHERE id = ?",
  "file": "src/models/user.js",
  "line": 23
}
```

---

## Test Results (mailcow-frontend)

```
Files scanned:      40
Endpoints found:     5
Validations:        764
Database queries:   14
Business logic:     40
Services:           4

Diagram nodes:       119
Diagram edges:       92
Tab views:           3 (default, database, validation)
```

---

## Dependencies

- Python 3.9+
- `d3.v7.min.js` — bundled inline in diagram output (no CDN needed)
- LLM API optional (falls back to structured templates without it)

No external Python packages required (stdlib only).

---

## Other Tools

### render.py — Force-Directed Graph
Graphify scan output → D3 force-directed graph.
```
python3 render.py graph.json --title "App Graph" --output out.html
```

### flow.py — Flow/Dependency Graph
Graphify scan output → layered DAG.
```
python3 flow.py graph.json --title "App Flow" --output out.html
```

Features: arrowheads (6 marker types), highlight path on select, collapse/expand, tree view.
