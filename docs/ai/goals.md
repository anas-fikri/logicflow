# Goals

## Primary Goal

Build a portable, self-contained source code visualizer + dual-mode interactive diagram generator yang bisa menghasilkan Business Flow dan Developer Graph dari codebase apapun dalam hitungan menit — tanpa AI (*Artificial Intelligence*), tanpa *dependency* eksternal berat, dan tanpa setup *database*.

---

## Sub-Goals

### Done ✅

- [x] Multi-language route scanner (PHP/Laravel, JS/Express, JS/Vue Router SPA, Python/Flask, Python/FastAPI, Go/Gin, C#/ASP.NET)
- [x] **Dual-mode diagram otomatis**: setiap scan menghasilkan `business.html` + `developer.html` sekaligus
- [x] **Business Flow** — horizontal tree card-based, label Bahasa Indonesia, expand/collapse, detail panel
- [x] **Developer Graph** — D3.js (*Data-Driven Documents*) force-directed, sidebar filter, highlight relasi
- [x] **Legend Singkatan & Istilah (Glossary)** di setiap diagram dan dashboard
- [x] **Multi-Project Dashboard** (`dashboard.html`) — grid project, search, panduan manajemen
- [x] Validation extraction (form rules, required fields, regex patterns)
- [x] Database (*Basis Data*) table/relation extraction (MySQL syntax)
- [x] Project registry CLI (*Command Line Interface*): `logicflow project` dengan `add`, `scan`, `scan-all`, `open`, `list`, `dashboard`
- [x] AI (*Artificial Intelligence*) documentation mode (LLM API integration, `stream:false`)
- [x] D3.js v7 inline bundle (279 KB, offline-ready, tanpa CDN)

### In Progress 🔄

- [ ] Node ID prefix untuk cross-app merged diagrams (hindari collision)
- [ ] tree-sitter AST (*Abstract Syntax Tree*) parser untuk extraction lebih akurat
- [ ] Lazy-render / web-worker untuk diagram dengan >5000 nodes

### Not Started ⬜

- [ ] Scanner untuk Next.js App Router (route groups, layouts)
- [ ] Scanner untuk NestJS decorator-based routes (`@Controller`, `@Get`)
- [ ] Scanner untuk Ruby on Rails (`resources`, `routes.rb`)
- [ ] SVG (*Scalable Vector Graphics*) / PNG export dari diagram
- [ ] Git diff mode — highlight perubahan routes antar commits

---

## Success Criteria

| Kriteria | Target |
|----------|--------|
| Scan speed (1000 files PHP) | < 10 detik |
| Diagram render (500 nodes) | < 3 detik |
| Framework detection | ≥ 7 framework |
| Label quality (Indonesian) | Semua menu label readable |
| CLI usability | 1-command: `logicflow project scan <name>` |
| Zero console errors | 100% clean |
| Dual-mode automatic | Setiap scan otomatis hasilkan business.html + developer.html |

---

## Priority (When in Doubt)

1. Scanner accuracy (semakin banyak pattern, semakin berguna)
2. Diagram readability (business user fokus)
3. CLI ergonomics (project management)
4. Performance (large codebase)
5. AI integration (optional enhancement)
