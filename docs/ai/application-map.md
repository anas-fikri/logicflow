# Application Map

## Verified Surfaces

### Scanner (`logicflow/scanner.py`)

**Input:** Source directory path
**Output:** JSON `{endpoints, validations, business_logic, forms, database, files, meta}`

**Supported Frameworks & Languages:**
| Language | Route Detection | Validation | DB (*Database*) | Notes |
|----------|----------------|------------|-----------------|-------|
| PHP (Laravel) | `Route::get/post/...` | `$request->validate()` | `Schema::create` | Multi-group pattern |
| JS/TS (Express.js) | `app.get/post/...` | `req.body.x` heuristic | — | Multi-group |
| JS/TS (Vue Router) | `path: '/x'` | `v-model` rules | — | Single-group (path only) |
| Python (Flask) | `@app.route` | `@required` | SQLAlchemy | Multi-group |
| Python (FastAPI) | `@app.get/post` | Pydantic models | SQLAlchemy | Multi-group |
| Go (Gin) | `r.GET/POST` | binding tags | GORM | Multi-group |
| C# (ASP.NET) | `[HttpGet]` | DataAnnotations | Entity Framework | Multi-group |
| SPA (*Single Page Application*) | `.vue`/`.svelte` | — | — | Dispatched to JS scanner |

**Route pattern dispatch:**
- 2-group patterns (method + path) → Express, Laravel, Flask, FastAPI
- 1-group patterns (path only) → Vue Router, React Router (static)
- `menuName()` strips `/api/v1/` prefix, extracts first meaningful segment

---

### Diagram Generator (`logicflow/diagram.py`)

**Input:** Scan JSON
**Output:** Dual-mode standalone HTML (*HyperText Markup Language*) files with D3.js (*Data-Driven Documents*) inline

| Mode | File | Layout | Audience |
|------|------|--------|----------|
| Business Flow | `business.html` | Horizontal tree (kiri→kanan) | BA (*Business Analyst*) / Client / pengguna non-teknis |
| Developer Graph | `developer.html` | Force-directed D3.js graph | Developer / Software Engineer |

**Both files include:**
- **Legend Singkatan & Istilah (Glossary)** — API = Application Programming Interface, DB = Database, AST = Abstract Syntax Tree, HTTP Methods, dst.
- Sidebar search & filter
- Detail panel (klik node)
- Topbar mode-switch ke counterpart diagram + tombol kembali ke Dashboard

**Label system:**
- `HUMAN_LABELS` dict — Indonesian translation (auth→Autentikasi, certificates→Sertifikat)
- `humanLabel()` — auto-pretty: hyphens/snake_case → Title Case
- `humanAction()` — method verb + path segment (GET→Lihat, POST→Tambah, DELETE→Hapus)
- `menuName()` — strip `:pathMatch(.*)`, wildcards, trailing `*`, leading `:`

---

### Dashboard (`logicflow/dashboard.py`)

**Input:** Projects registry dict
**Output:** `dashboard.html` — central multi-project landing page

**Features:**
- Multi-project card grid (stats: menus, API endpoints, total nodes)
- Real-time search filter
- 1-click buttons to Business Flow & Developer Graph per project
- Panduan Manajemen Multi-Project (step-by-step guide)
- Legend Singkatan & Istilah (Glossary section)

---

### AI Docs (`logicflow/ai.py`)

**Input:** Scan JSON
**Output:** Markdown documentation (optional)

- API: LLM via `AI_API_URL` (9Router/OmniRoute default)
- Payload: `{"stream": false, "model": "auto", "messages": [...]}`
- Reasoning models: parse `reasoning_content` field
- Timeout: 300s per batch
- Batch mode: chunks of 50 endpoints

---

### Project Manager (`logicflow/project.py`)

**Registry:** `~/.logicflow/projects.json`
**Output dir:** `~/.logicflow/output/<name>/{scan.json, business.html, developer.html}`
**Dashboard:** `~/.logicflow/dashboard.html`

**CLI Commands:**
| Command | Description |
|---------|-------------|
| `logicflow project add <name> <path>` | Daftarkan project baru ke registry |
| `logicflow project list` | Daftar project terdaftar + statistik |
| `logicflow project scan <name>` | Scan + generate dual-mode diagrams otomatis |
| `logicflow project scan-all` | Scan ulang semua project sekaligus |
| `logicflow project open <name>` | Buka diagram di browser (default: both modes) |
| `logicflow project dashboard` | Buka unified dashboard.html di browser |
| `logicflow project info <name>` | Detail project (paths, stats, last scan) |
| `logicflow project remove <name>` | Hapus project dari registry |

---

## Known Gaps

1. **Node ID collision** — cross-app merge pakai raw node IDs, perlu prefix per repo.
2. **No Next.js App Router** — `app/` directory routes belum ter-scan.
3. **No NestJS decorators** — `@Controller`, `@Get` belum ter-scan.
4. **No lazy-render** — diagram >5000 nodes render lambat di browser.
5. **No git diff mode** — belum bisa compare routes antar commits.
6. **No SVG/PNG export** — screenshot manual only.
