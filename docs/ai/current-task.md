# Current Task

## Completed: Multi-Project Dashboard Legend & Automatic Dual-Mode Enhancement

**Status:** DONE  
**Completed:** 2026-08-13

### Summary of Changes

1. **Legend & Abbreviations (Kepanjangan Singkatan)**:
   - Menambahkan **Legend Singkatan & Istilah (Glossary)** pada `business.html`, `developer.html`, dan `dashboard.html` (API = Application Programming Interface, DB = Database, AST = Abstract Syntax Tree, CLI = Command Line Interface, BA = Business Analyst, UI = User Interface, HTTP Methods).
   - Menambahkan kepanjangan untuk semua singkatan teknis dan bisnis pada `README.md`, `project-context.md`, dan dokumentasi proyek.

2. **Multi-Project Management Guide**:
   - Menambahkan panduan langkah-demi-langkah pengelolaan banyak proyek pada `dashboard.html` (`codemap project add`, `scan`, `scan-all`, `dashboard`).
   - Menyajikan informasi alur manajemen registry `~/.codemap/projects.json` secara mendalam di `README.md`.

3. **Automatic Dual-Mode Default**:
   - Memastikan semua perintah pemindaian (`codemap diagram`, `full`, `project scan`, `project open`) secara otomatis memproses dan menyajikan **KEDUA mode diagram** (`business.html` + `developer.html`).
