# CodeMap

CLI Tool (Python 3.11) untuk memindai source code aplikasi (multi-framework) tanpa AI dan menghasilkan 2 mode visualisasi diagram HTML interaktif:

1. **💼 Mode Awam (Business Flow)**: Diagram tree horizontal yang mudah dipahami oleh Pengguna Awam / Business Analyst / Client, lengkap dengan pengelompokan menu utama, label bahasa Indonesia, aksi user, dan detail validasi/database.
2. **⚡ Mode Developer (Developer Graph)**: Diagram force-directed interaktif untuk Developer yang menampilkan hubungan teknis lengkap antara route/endpoint API, controller, business logic, validasi, dan skema tabel database.

Termasuk **Dashboard Project Registry** untuk mengelola dan membuka visualisasi berbagai project dalam satu tampilan terpusat.

---

## 🚀 Fitur Utama

- **Zero AI Required**: Scan cepat menggunakan AST parsing & regex extractor.
- **Multi-Framework**:
  - PHP / Laravel
  - Vue 3 / Vue Router (SPA)
  - JavaScript / Express.js
  - Python / Flask & FastAPI
  - Go / C# ASP.NET
- **Dual-Mode Diagram Output**:
  - `business.html` — Card-based horizontal tree, label bahasa Indonesia, awam-friendly.
  - `developer.html` — D3 force-directed graph dengan detail relasi kode.
- **Self-Contained & Offline-Ready**: D3.js v7 di-bundle langsung di dalam file HTML (Tanpa CDN / CORS issue).
- **Project Registry & Dashboard**: Kelola multiple codebase dengan `codemap project` CLI dan dashboard HTML.

---

## 💻 Cara Penggunaan CLI

### 1. Project Management & Dashboard

```bash
# Tambahkan project ke registry
codemap project add cert26 /path/to/laravel-app --title "Certificate 26"

# Scan & buat diagram dual-mode untuk project
codemap project scan cert26

# Scan semua project terdaftar sekaligus
codemap project scan-all

# Buka Dashboard terpusat di browser
codemap project dashboard

# Buka diagram spesifik project
codemap project open cert26 --mode business
codemap project open cert26 --mode developer

# Lihat daftar project terdaftar
codemap project list
```

### 2. Standalone Scan & Diagram Pipeline

```bash
# Scan source code ke JSON / Markdown
codemap scan /path/to/source -o scan.json -f json

# Build diagram dari JSON (Dual Mode)
codemap diagram --graph scan.json -o myapp -m both -t "My Application"

# Pipeline lengkap (Scan + Both Diagrams)
codemap full /path/to/source -o myapp -t "My Application"
```

---

## 📁 Struktur Output Project

Setiap project yang discan via `codemap project scan <name>` disimpan di `~/.codemap/output/<name>/`:

```
~/.codemap/
├── projects.json         # File registry project
├── dashboard.html        # Landing page dashboard
└── output/
    └── <name>/
        ├── scan.json     # Data AST extraction
        ├── business.html # Diagram Mode Awam (Business Flow)
        └── developer.html# Diagram Mode Developer (Force Graph)
```

---

## 🛠️ Stack & Spesifikasi Teknikal

- **CLI Engine**: Python 3.11 (Standard Library, tanpa dependencies external python)
- **Visualisasi**: D3.js v7 (Inlined 279KB)
- **Data Persistence**: JSON (`~/.codemap/projects.json`)
- **Compatibility**: macOS / Linux / Windows

---

## 🤝 Lisensi

MIT License. Developed for fast code analysis and stakeholder presentation.
