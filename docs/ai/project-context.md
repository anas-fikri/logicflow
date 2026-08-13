# Project Context

Project: **CodeMap** — AI-assisted source code scanner & interactive diagram builder

**Project Root:** `/Users/anasfikri/Documents/Projects/others/apps-diagram`

## Summary

CLI tool (Python) untuk memindai source code codebase manapun → extract routes/endpoints, validasi, DB relations, forms, business logic → generate interactive HTML diagram (D3.js) untuk business flow, code flow, database, dan validasi. Support multi-framework: Laravel/PHP, Vue3/TypeScript, Express/Node.js, Flask/FastAPI/Python.

Engine-nya modular: `scan → diagram` pipeline. Bisa berdiri sendiri (non-AI) atau pakai AI LLM untuk generate dokumentasi natural language per endpoint.

Target user: developer dan business analyst yang butuh visualisasi cepat tanpa harus baca semua kode.

## Stack

- **CLI Engine:** Python 3.11, argparse, no external deps
- **Scanner:** AST parsing via `tree-sitter` + regex fallback; multi-language
- **Diagram:** D3.js v7 (inline, 279KB); tree layout + force-directed
- **AI Docs:** HTTP calls ke LLM API (9Router/OmniRoute); streaming disabled
- **Registry:** `~/.codemap/projects.json` + `~/.codemap/output/<name>/`
- **Venv:** hermes venv (`~/hermes/venv/bin/python3`)

## Directory Structure

```
apps-diagram/
├── codemap/                    # Main package
│   ├── __main__.py             # CLI entry point (scan/ai/diagram/full/project)
│   ├── scanner.py              # AST + regex route scanner (739 lines)
│   ├── diagram.py              # D3 HTML diagram builder (1247 lines)
│   ├── ai.py                   # LLM documentation generator (253 lines)
│   └── project.py              # Project registry manager (350+ lines)
├── parsers/                    # Language-specific parsers (stub/extensible)
├── vendor/
│   └── d3.v7.min.js            # D3 inline bundle (279KB)
├── docs/ai/                    # AI toolkit documentation
└── .codemap/                   # Runtime output (gitignored)
    └── output/<name>/
        ├── scan.json
        └── diagram.html
```

## Constraints

1. **D3 must be inline** — `vendor/d3.v7.min.js` bundled directly in HTML output. CDN tidak boleh. Alasan: CORS + offline reliability.
2. **`stream: false`** — Semua payload ke 9Router/OmniRoute harus include `"stream": false`. Default adalah SSE; reasoning models butuh full response.
3. **No SQLite** — User preference. Jangan pakai SQLite untuk persistence.
4. **Node ID prefix** — Cross-app merged diagrams butuh prefix per repo untuk menghindari collision (Belum diimplementasi — lihat next-tasks).
5. **Scan JSON files** — Di-generate per project, tidak di-commit ke repo bersama. Local registry cukup.
6. **Sudo blocked** — Jangan gunakan sudo untuk operasi apapun.

## Conventions

### CLI Commands

```bash
# Individual steps
codemap scan <source-dir> -o scan.json
codemap diagram --graph scan.json -o diagram.html -t "App Title"

# Full pipeline
codemap full <source-dir> -o myapp --title "My App"

# Project management
codemap project add <name> <source> [--title TITLE]
codemap project list
codemap project scan <name>       # scan + diagram
codemap project scan-all          # all projects
codemap project open <name>       # open diagram in browser
codemap project info <name>
codemap project remove <name> [--purge]

# Output location
~/.codemap/projects.json          # registry
~/.codemap/output/<name>/         # per-project artifacts
```

### Naming

- `scan.json` — hasil AST extraction dari scanner
- `*-v4.html` — diagram output versi latest (v4 = horizontal tree + human labels)
- `-fresh-scan.json` — scan dari codebase fresh (belum di-register)
- `codemap-*.html` — diagram lama (legacy force-directed)

### Scanner Pattern Rules

- Route patterns HARUS punya capture group untuk method + path (2 group minimum) untuk Express/Laravel
- Vue Router patterns punya 1 group (path only) — dipisah di dispatch logic
- File extension → language dispatch:
  - `.py` → `python`
  - `.js/.ts/.vue/.svelte` → `javascript`
  - `.php` → `php`
  - `.cs` → `csharp`
  - `.go` → `golang`