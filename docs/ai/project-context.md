# Project Context

Project: **LogicFlow** — Source Code Visualizer, Dual-Mode Diagram Generator & Multi-Project Dashboard

**Project Root:** `/Users/anasfikri/Documents/Projects/others/apps-diagram`

## Summary

Aplikasi CLI (*Command Line Interface* / Antarmuka Baris Perintah) berbasis Python 3.11 untuk memindai *source code* codebase multi-framework (Laravel/PHP, Vue Router, Express/JavaScript, Flask/FastAPI/Python, Go, C#) tanpa AI (*Artificial Intelligence*) → secara **otomatis menghasilkan 2 mode diagram HTML (*HyperText Markup Language*) interaktif sekaligus**:

1. **Mode Awam (`business.html`)**: Business Flow *horizontal tree card-based* dengan label Bahasa Indonesia untuk Business Analyst (BA) / Client / Pengguna Non-Teknis.
2. **Mode Developer (`developer.html`)**: Developer Force-Directed Graph interaktif menggunakan D3.js (*Data-Driven Documents*) untuk menginspeksi API (*Application Programming Interface*) Route, Business Logic (Controller), Validation, & DB (*Database*).

Dilengkapi **Unified Multi-Project Dashboard (`dashboard.html`)** yang diproduksi oleh perintah CLI `logicflow project dashboard` untuk mengelola banyak proyek dalam satu tampilan terpusat. Setiap komponen diagram dan dashboard dilengkapi dengan **Legend Singkatan & Istilah (Glossary)**.

## Stack & Arsitektur

- **CLI Engine:** Python 3.11 (Standard Library, argparse, no external dependencies)
- **Scanner:** AST (*Abstract Syntax Tree*) parsing + regex patterns (Multi-framework)
- **Diagram Generator:** D3.js v7 (*Data-Driven Documents*, inline 279 KB, offline-ready, no CDN)
- **Project Registry:** `~/.logicflow/projects.json` & `~/.logicflow/dashboard.html`
- **Output:** `~/.logicflow/output/<name>/{scan.json, business.html, developer.html}`

## Glossary of Abbreviations (Legend Singkatan)

- **API**: *Application Programming Interface* (Antarmuka Pemrograman Aplikasi)
- **AST**: *Abstract Syntax Tree* (Pohon Sintaks Abstrak)
- **CLI**: *Command Line Interface* (Antarmuka Baris Perintah)
- **BA**: *Business Analyst* (Analis Bisnis)
- **UI**: *User Interface* (Antarmuka Pengguna)
- **DB**: *Database* (Basis Data & Skema Tabel)
- **JSON**: *JavaScript Object Notation*
- **HTML**: *HyperText Markup Language*
- **D3.js**: *Data-Driven Documents JavaScript library*
- **CORS**: *Cross-Origin Resource Sharing*
- **CDN**: *Content Delivery Network* (Jaringan Pengiriman Konten)

## Constraints & Rules

1. **D3 must be inline** — `vendor/d3.v7.min.js` di-bundle langsung di file HTML (279 KB). Tanpa CDN / CORS issue.
2. **No SQLite** — Penyimpanan data registry menggunakan JSON (*JavaScript Object Notation*) pada `projects.json`.
3. **Automatic Dual-Mode** — Pemindaian tunggal secara otomatis memproduksi `business.html` dan `developer.html`.
4. **Mandatory Abbreviations Legend** — Setiap dokumentasi wajib menyertakan kepanjangan singkatan, dan setiap diagram/dashboard wajib memuat komponen Legend.
