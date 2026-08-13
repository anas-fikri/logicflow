# Application Map

## Verified Surfaces

### Scanner (`codemap/scanner.py` — 739 lines)

**Input:** source directory path
**Output:** JSON `{endpoints, validations, business_logic, forms, database, files, meta}`

**Supported languages:**
| Language | Route Pattern | Validation | DB | Forms |
|----------|-------------|------------|----|----|
| PHP (Laravel) | `Route::get/post/...` | `$request->validate()` | `Schema::create` | `<form>` |
| JS/TS (Express) | `app.get/post/...` | `req.body.x` heuristic | — | — |
| JS/TS (Vue Router) | `path: '/x'` | `v-model` rules | — | — |
| Python (Flask) | `@app.route` | `@required` | SQLAlchemy | `WTForms` |
| Python (FastAPI) | `@app.get/post` | Pydantic | SQLAlchemy | — |
| Go (Gin) | `r.GET/POST` | binding tags | GORM | — |
| C# (ASP.NET) | `[HttpGet]` | DataAnnotations | EF | Razor |

**Route pattern dispatch:**
- 2-group patterns (method + path) → Express, Laravel, Flask, FastAPI
- 1-group patterns (path only) → Vue Router, React Router (static)
- `menuName()` extract first meaningful segment after stripping `api/`, `v1/`, etc.

### Diagram (`codemap/diagram.py` — 1247 lines)

**Input:** scan JSON
**Output:** standalone HTML (D3.js inline)

**Views:**
| Tab | Layout | Purpose |
|-----|--------|---------|
| Business Flow | Horizontal tree (kiri→kanan) | Business user. App → Menu → Aksi → Validasi & DB. Card-based. |
| Code Flow | Force-directed (D3) | Developer. All nodes + edges. Click highlight. |
| Database | ERD-style table relations | DBA. FK lines between tables. |
| Validasi | List grouped by field | QA. All validation rules. |

**Label system:**
- `HUMAN_LABELS` dict → Indonesian translation (auth→Autentikasi, certificates→Sertifikat)
- `humanLabel()` → auto-pretty: hyphens/snake_case → Title Case
- `humanAction()` → method verb + last path segment (get→Lihat, post→Tambah, delete→Hapus)
- `menuName()` → strip `:pathMatch(.*)`, wildcards, trailing `*`, leading `:`

### AI Docs (`codemap/ai.py` — 253 lines)

**Input:** scan JSON
**Output:** Markdown documentation

- API: 9Router (`http://localhost:20128/v1/chat/completions`) atau OmniRoute
- Payload: `{"stream": false, "model": "auto", "messages": [...]}`
- Reasoning models: parse `reasoning_content` field, bukan `content`
- Timeout: 300s (per batch)
- Batch mode: split endpoints into chunks of 50

### Project Manager (`codemap/project.py` — 350+ lines)

**Registry:** `~/.logicflow/projects.json`
**Output:** `~/.logicflow/output/<name>/{scan.json,diagram.html}`

**Commands:** add, list, scan, scan-all, diagram, info, remove, open

## Known Gaps

1. **Node ID collision** — cross-app merge (`merged-pcp.json`) pakai raw node IDs. Perlu prefix per repo.
2. **No Next.js App Router** — `app/` directory routes belum ter-scan.
3. **No NestJS decorators** — `@Controller`, `@Get` belum ter-scan.
4. **No lazy-render** — diagram >5000 nodes render lambat di browser.
5. **No git diff mode** — belum bisa compare routes antar commits.
6. **No SVG/PNG export** — screenshot manual only.
7. **Passman AI timeout** — 1463 validation entries gagal diproses dalam 300s.