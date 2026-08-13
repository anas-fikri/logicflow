# Handoff

## Latest: 2026-08-13 — Documentation Setup + Project Manager

### What was done

1. **Scanner fix: Vue Router support**
   - Added Vue Router pattern `path: '/x'` ke `ROUTE_PATTERNS["javascript"]`
   - Dispatch `.vue`/`.svelte` files ke `_scan_js()`
   - Support single-group route patterns (Vue Router hanya punya 1 capture group)
   - Hasil: Passman 0 → 18 endpoints terdeteksi

2. **Diagram fix: label sanitization**
   - `menuName()`: strip `:pathMatch(.*)*`, trailing `*`, leading `:`
   - `humanLabel()`: auto-pretty hyphens/snake_case → Title Case
   - 12 label Indonesia baru: vault=Brankas, unlock=Buka Kunci, org=Organisasi, dll
   - `catchall` → "Lainnya"

3. **Project Manager CLI (`codemap project`)**
   - Registry: `~/.codemap/projects.json`
   - Output: `~/.codemap/output/<name>/{scan.json,diagram.html}`
   - Commands: add, list, scan, scan-all, diagram, info, remove, open
   - 3 projects terdaftar: cert26, passman, mailcow

4. **ai-toolkit documentation setup**
   - `ai-init` scaffold
   - Semua `docs/ai/*.md` terisi data real hasil audit kode
   - `ai-state.json` update

### Commits
- `f82d919` — codemap: vue router + dynamic engine fixes
- `b5edcbf` — codemap: project manager (codemap project CLI)

### Test Results

| App | Framework | Menus | APIs | Nodes | Errors |
|-----|-----------|-------|------|-------|--------|
| Certificate26 | Laravel (PHP) | 8 | 27 | 127 | 0 |
| Passman | Vue3 + TS (SPA) | 11 | 18 | 659 | 0 |
| Mailcow Frontend | Express (JS) | 13 | 14 | 819 | 0 |

### State
- Branch: `main`
- Git: clean (semua committed)
- Server: `python3 -m http.server 8847` (port 8847)
- Registry: 3 projects active
- Latest diagram version: v4 (horizontal tree + human labels)

### Next Session
- Lihat `next-tasks.md` untuk prioritas
- `codemap project list` untuk status registry
- `codemap project scan-all` untuk re-scan semua project