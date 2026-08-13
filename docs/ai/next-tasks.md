# Next Tasks

Prioritas berdasarkan goals.md + known gaps. Pilih satu setelah cek dependensi + user priority.

## High Priority

### 1. Node ID prefix untuk cross-app merged diagrams
**Effort:** 2h | **Depends:** None

Cross-app merge (`merged-pcp.json`) pakai raw node IDs → collision saat node IDs overlap antar repo. Perlu prefix: `cert26_`, `passman_`, `mailcow_`.

Approach:
1. Scanner: `scan.json` output udah punya `meta.repo` field
2. `diagram.py`: prefix node IDs dengan `meta.repo` atau `meta.source` name
3. Test: regenerate `merged-pcp.json` → verify no collision

### 2. Scanner: Next.js App Router support
**Effort:** 3h | **Depends:** None

Next.js 13+ `app/` directory routes belum ter-scan. Pattern:
```ts
// app/dashboard/page.tsx → route /dashboard
// app/api/users/route.ts → API route
```
Scanner perlu handle:
- File-based routing dari `app/[slug]/page.tsx`
- Layout files (`layout.tsx`)
- API route handlers (`route.ts`)

### 3. SVG/PNG export dari diagram
**Effort:** 2h | **Depends:** None

User perlu export diagram untuk slide/presentasi. Options:
1. `canvas.toDataURL('image/png')` → download PNG
2. Inline SVG dari D3 → download SVG
3. Puppeteer screenshot (server-side, overkill)

## Medium Priority

### 4. tree-sitter AST parser upgrade
**Effort:** 4h | **Depends:** None (but complex)

tree-sitter lebih akurat dari regex. Install:
```bash
npm install -g tree-sitter tree-sitter-php tree-sitter-javascript tree-sitter-python
```
Benefit: multi-line validation expressions, nested arrays, complex AST nodes.

### 5. Passman AI timeout fix
**Effort:** 2h | **Depends:** None

Passman punya 1463 validation entries. Single batch → timeout (300s). Fix:
- Batch size dari 50 → 10 endpoints per batch
- Progress indicator di CLI
- Resume capability jika timeout mid-batch

### 6. Dashboard view — overview semua project
**Effort:** 2h | **Depends:** `codemap project` (done)

Generate satu HTML yang show semua project registry: summary stats, last scan date, quick links. Lazy load per diagram.

## Low Priority (backlog)

### 7. Git diff mode — compare routes antar commits
### 8. Lazy-render untuk >5000 nodes
### 9. Scanner: NestJS decorator-based routes
### 10. Scanner: Ruby on Rails resources

## Pick Next
Cek preferensi user. Biasanya preference: (1) Node ID prefix atau (2) Next.js scanner.