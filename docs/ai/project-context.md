# Project Context

Project: **CodeMap** — Source Code Scanner & Dual-Mode Interactive Diagram Builder

**Project Root:** `/Users/anasfikri/Documents/Projects/others/apps-diagram`

## Summary

CLI tool (Python 3.11) untuk memindai source code codebase (Laravel, Vue Router, Express, Flask, FastAPI, Go, C#) tanpa AI → menghasilkan 2 mode diagram HTML interaktif:

1. **Mode Awam (`business.html`)**: Business Flow horizontal tree card-based dengan label Indonesia untuk Business Analyst / Client.
2. **Mode Developer (`developer.html`)**: Developer Force-Directed Graph interaktif untuk menginspeksi route, logic, validation, & DB.

Juga dilengkapi **Unified Project Dashboard (`dashboard.html`)** yang diproduksi oleh `codemap project dashboard`.

## Stack

- **CLI Engine:** Python 3.11, argparse, no external dependencies
- **Scanner:** AST parsing + regex patterns (Multi-framework)
- **Diagram:** D3.js v7 (inline 279KB, offline-ready, no CDN)
- **Registry:** `~/.codemap/projects.json` & `~/.codemap/dashboard.html`
- **Output:** `~/.codemap/output/<name>/{scan.json, business.html, developer.html}`

## Directory Structure

```
apps-diagram/
├── codemap/                    # Main package
│   ├── __main__.py             # CLI entry point (scan/ai/diagram/full/project)
│   ├── scanner.py              # AST + regex scanner engine
│   ├── diagram.py              # Dual-mode HTML diagram dispatcher
│   ├── dashboard.py            # Unified dashboard HTML builder
│   ├── ai.py                   # Optional LLM documentation generator
│   └── project.py              # Project registry CLI manager
├── vendor/
│   └── d3.v7.min.js            # D3 inline bundle (279KB)
├── docs/ai/                    # AI toolkit documentation
└── .codemap/                   # Runtime output (gitignored)
```

## Constraints

1. **D3 must be inline** — `vendor/d3.v7.min.js` bundled directly in HTML output. No CDN allowed.
2. **No SQLite** — JSON file storage for registry (`projects.json`).
3. **Dual Mode Output** — Single scan generates both `business.html` and `developer.html`.
