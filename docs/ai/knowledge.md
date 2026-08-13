# Durable Knowledge

## Scanner

### Framework Detection
- **Laravel**: `Route::get/post/put/patch/delete('path', [Controller, 'method'])`. Regex catch 2 groups. File ext `.php`.
- **Vue Router**: `path: '/login'` di `router/index.ts`. 1 group. Tidak ada method — inferred dari component type.
- **Express**: `app.get/post/put/delete('path', handler)`. 2 groups. File ext `.js/.ts`.
- **Flask**: `@app.route('/path', methods=['GET'])`. 1-2 groups. File ext `.py`.
- **FastAPI**: `@app.get('/path')`. 1-2 groups. File ext `.py`.

### Route Pattern Gotchas
1. **`:pathMatch(.*)*` (Vue Router catch-all)** — strip dengan regex `/:pathMatch\([^)]+\)/` → `catchall` → `humanLabel('catchall')` → "Lainnya".
2. **Leading colon** `:id` — strip dengan `.replace(/^:/, '')`.
3. **Trailing wildcard** `*` — strip dengan `.replace(/\*+$/, '')`.
4. **Brace params** `{id}` — strip dengan `.replace(/^\{(\w+?)s?\}$/, '$1s')`.
5. **`api/` prefix** — skip dengan `while (/^(api|v\d+)$/i.test(parts[start])) start++`.

### Validation Extraction
- **Laravel**: `$request->validate(['field' => 'required|string|max:255'])` — regex catch field + rules string.
- **Vue3**: `rules: { field: [{ required: true, ... }] }` — regex catch field + validator type.
- **Express**: `req.body.field` heuristic — tidak reliable, only catch obvious patterns.
- **Guard**: empty match groups (IndexError) — fixed in commit 3f023a7.

### File Extension Dispatch
```python
LANG_EXT = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.vue': 'vue', '.svelte': 'svelte',
    '.php': 'php', '.cs': 'csharp', '.go': 'golang',
}
# Dispatch: vue/svelte → _scan_js (same as JS/TS)
```

## Diagram

### D3 Inline Bundle
- File: `vendor/d3.v7.min.js` (279KB)
- Cara inline: `Path('vendor/d3.v7.min.js').read_text()` → embed di `<script>` tag.
- Tidak boleh CDN — CORS issue pada `file://` protocol.

### Business Flow Tree Construction
```
Root (App Name)
├── Menu 1 (humanLabel)
│   ├── Feature 1 (humanAction: "Lihat X", "Tambah Y")
│   │   ├── Validation 1
│   │   └── Database Table
│   └── Feature 2
├── Menu 2
└── ...
```

### humanLabel() Logic
1. Check `HUMAN_LABELS[key]` — exact match (auth→Autentikasi)
2. Check `HUMAN_LABELS[path]` — exact path match
3. `catchall` → "Lainnya"
4. Auto-pretty: `key.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase())`
5. Fallback: capitalize first char

### humanAction() Logic
1. Check `KNOWN_ACTIONS[last]` — exact match (login→Login, export→Export)
2. Brace param `{id}` → "Lihat Detail" / "Edit" / "Hapus" (by method)
3. Method verb + last segment: `HUMAN_METHODS[method] + ' ' + pretty(last)`

### Menu Grouping Strategy
- First meaningful segment after `api/`, `v1/`, `v2/` = menu name
- 14 raw segments → 9 grouped menus (cert26 case) → 7 final after `menuName()` fix
- Menus sorted alphabetically in tree

## AI Integration

### 9Router/OmniRoute Payload
```json
{
  "model": "auto",
  "stream": false,
  "messages": [
    {"role": "system", "content": "You are a code documentation assistant..."},
    {"role": "user", "content": "Document these endpoints:\n{json}"}
  ]
}
```

### Reasoning Model Response Parsing
- Standard models: `response.choices[0].message.content`
- Reasoning models (deepseek-r1): `response.choices[0].message.reasoning_content`
- Always check both fields; `content` may be empty for reasoning models.

### Timeout Handling
- Default: 300s per batch
- Batch size: 50 endpoints
- Passman case: 1463 validation entries → 30 batches × 300s = potential 2.5 hours. Timeout karena single-batch attempt.
- Fix: split into smaller batches (future).

## Project Registry

### Registry Structure
```json
{
  "projects": {
    "cert26": {
      "source": "/path/to/backend",
      "title": "Certificate26",
      "scan_file": "~/.logicflow/output/cert26/scan.json",
      "diagram_file": "~/.logicflow/output/cert26/diagram.html",
      "last_scan": "2026-08-13T08:17:58",
      "stats": {"nodes": 127, "menus": 8, "apis": 27, "validations": 48},
      "created": "2026-08-13T08:17:55",
      "exclude": ["node_modules", ".git", "vendor", "dist"]
    }
  }
}
```

### scan-all Implementation
- Iterasi `reg["projects"]` sorted by name
- Per project: call `cmd_project_scan(dummy_args)` — reuse single-project logic
- Error per project tidak hentikan loop — continue ke project berikutnya
- Summary: `{success}/{total} projects scanned successfully`
## 2026-08-13T01:56:01Z
- Task: 
- Status: COMPLETED
- Finding: LogicFlow engine: scanner supports 7+ frameworks (Laravel, Vue Router, Express, Flask, FastAPI, Gin, ASP.NET). D3 v7 inline (279KB) — no CDN. Business Flow horizontal tree with Indonesian labels + auto-pretty fallback. Project registry at ~/.logicflow/projects.json. stream:false mandatory for 9Router/OmniRoute. Single-group route patterns for Vue Router (path only, no method).
