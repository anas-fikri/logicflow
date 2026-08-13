# Goals

## Primary Goal
Build a portable, self-contained source code scanner + interactive diagram tool yang bisa generate business flow diagram dari codebase apapun dalam hitungan menit — tanpa perlu install deps berat atau setup database.

## Sub-Goals

### Done
- [x] Multi-language route scanner (PHP/Laravel, JS/Express, JS/Vue Router, Python/Flask, Python/FastAPI, Go, C#)
- [x] D3.js interactive diagram (tree + force-directed) dengan inline D3
- [x] Business Flow tab — horizontal tree, label bahasa Indonesia, card-based expand/collapse
- [x] Validation extraction (form rules, required fields, regex patterns)
- [x] Database table/relation extraction (MySQL syntax)
- [x] Project registry (`codemap project` CLI) dengan `scan`, `scan-all`, `open`, `list`
- [x] AI documentation mode (LLM API integration, stream:false)

### In Progress
- [ ] Node ID prefix untuk cross-app merged diagrams (hindari collision)
- [ ] tree-sitter AST parser untuk extraction lebih akurat
- [ ] Lazy-render / web-worker untuk diagram dengan >5000 nodes
- [ ] SVG/PNG export dari diagram

### Not Started
- [ ] Scanner untuk Next.js App Router (route groups, layouts)
- [ ] Scanner untuk NestJS decorator-based routes
- [ ] Scanner untuk Ruby on Rails (resources/routes)
- [ ] Dashboard view — overview semua project registry dalam satu HTML
- [ ] Git diff mode — highlight perubahan routes antar commits

## Success Criteria

| Kriteria | Target |
|----------|--------|
| Scan speed (1000 files PHP) | < 10 detik |
| Diagram render (500 nodes) | < 3 detik |
| Framework detection | ≥ 3 framework |
| Label quality (Indonesian) | semua menu label readable |
| CLI usability | 1-command: `codemap project scan <name>` |
| Zero console errors | 100% clean |

## Priority (when in doubt)

1. Scanner accuracy (semakin banyak pattern, semakin berguna)
2. Diagram readability (business user fokus)
3. CLI ergonomics (project management)
4. Performance (large codebase)
5. AI integration (optional enhancement)