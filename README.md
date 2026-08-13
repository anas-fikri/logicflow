# LogicFlow — Corporate Source Code Visualizer

**LogicFlow** adalah aplikasi CLI (*Command Line Interface* / Antarmuka Baris Perintah) berbasis Python 3.11 tanpa AI (*Artificial Intelligence*) yang memindai *source code* aplikasi multi-framework dan secara **otomatis menghasilkan 2 mode diagram HTML (*HyperText Markup Language*) interaktif sekaligus** beserta **Dashboard Terpusat untuk Manajemen Multi-Project**.

---

## 📖 Mode Visualisasi Otomatis (Dual-Mode)

Setiap kali Anda menjalankan pemindaian (*scan*), LogicFlow secara otomatis memproduksi dua mode diagram:

1. **💼 Business Flow (`business.html`)**:
   - Diagram *horizontal tree* berbasis *card* yang intuitif dan mudah dipahami oleh pengguna non-teknis, Client, maupun BA (*Business Analyst*).
   - Pengelompokan berdasarkan menu utama aplikasi dengan label Bahasa Indonesia.
   - Detail aksi pengguna, aturan validasi form, dan keterhubungan tabel DB (*Database*).
2. **⚡ Mode Developer (Developer Graph / `developer.html`)**:
   - Diagram *force-directed graph* berbasis D3.js (*Data-Driven Documents*) interaktif khusus untuk *Software Engineer* / Developer.
   - Menampilkan struktur teknis *node-by-node*: API (*Application Programming Interface*) Route / Endpoint, Business Logic (Controller / Handler), Form Validation, dan Skema Tabel DB (*Database*).

Setiap diagram dilengkapi **Legend Singkatan & Istilah (Glossary)** di bagian pojok kiri bawah untuk memudahkan navigasi.

---

## 🗺️ Cara Mengelola & Menampilkan Banyak Project (Multi-Project Dashboard)

Jika Anda memindai lebih dari 1 project, LogicFlow mengelolanya secara otomatis melalui **Project Registry Manager** (`~/.logicflow/projects.json`) dan menyajikannya dalam satu halaman landing page terpusat di `dashboard.html`.

### Alur Manajemen Multi-Project:

1. **Daftarkan Project Baru ke Registry**:
   ```bash
   # Contoh menambah project 1 (Laravel Certificate)
   logicflow project add cert26 /path/to/laravel-cert26 --title "Certificate 26"

   # Contoh menambah project 2 (Mailcow Frontend)
   logicflow project add mailcow /path/to/mailcow-frontend --title "Mailcow Frontend"

   # Contoh menambah project 3 (Passman Vue SPA)
   logicflow project add passman /path/to/passman-src --title "Passman Password Manager"
   ```

2. **Memindai & Memproduksi Dual-Mode Diagram Otomatis**:
   ```bash
   # Pindai project spesifik (otomatis menghasilkan business.html + developer.html)
   logicflow project scan cert26

   # Pindai SELURUH project terdaftar sekaligus dalam 1 perintah
   logicflow project scan-all
   ```

3. **Membuka Dashboard Multi-Project Terpusat**:
   ```bash
   logicflow project dashboard
   ```
   *Perintah ini akan membuka `dashboard.html` di peramban web (browser).*
   - **Tampilan Grid Project**: Setiap project tampil sebagai *card* terpisah dengan ringkasan statistik (jumlah Menu UI, jumlah API Endpoint, total Code Node, dan bahasa pemrograman).
   - **Pencarian Real-Time**: Bar pencarian untuk menyaring project berdasarkan nama, path, atau teknologi.
   - **Navigasi 1-Klik**: Tombol langsung menuju `💼 Mode Awam (Business)` atau `⚡ Mode Developer (Graph)`.

4. **Membuka Diagram Project via CLI**:
   ```bash
   # Membuka dual-mode diagram project di browser (default: both)
   logicflow project open cert26

   # Atau buka mode spesifik
   logicflow project open cert26 --mode business
   logicflow project open cert26 --mode developer
   ```

5. **Melihat Daftar Project Terdaftar**:
   ```bash
   logicflow project list
   logicflow project info cert26
   ```

---

## 🚀 Perintah CLI (*Command Line Interface*) Standalone

Selain melalui Project Registry, Anda juga dapat menjalankan LogicFlow secara langsung pada direktori mana saja:

```bash
# Otomatis hasilkan JSON scan data + Dual-Mode Diagram (Business & Developer)
logicflow full /path/to/source -o myapp -t "My Application"

# Atau dari file JSON yang sudah ada
logicflow diagram --graph scan.json -o myapp -m both -t "My Application"
```

---

## 📚 Legend Singkatan & Istilah (Glossary of Abbreviations)

Semua singkatan yang digunakan di dalam dokumentasi, aplikasi CLI, diagram interaktif, dan *dashboard* telah dilengkapi dengan legend resmi:

| Singkatan | Kepanjangan Bahasa Inggris | Penjelasan & Arti dalam Bahasa Indonesia |
| :--- | :--- | :--- |
| **API** | *Application Programming Interface* | Antarmuka Pemrograman Aplikasi yang menghubungkan antarmuka pengguna (UI) dengan server backend. |
| **AST** | *Abstract Syntax Tree* | Pohon Sintaks Abstrak yang digunakan scanner untuk mengurai dan menganalisis kode program tanpa AI. |
| **CLI** | *Command Line Interface* | Antarmuka Baris Perintah terminal tempat menjalankan perintah aplikasi LogicFlow. |
| **BA** | *Business Analyst* | Analis Bisnis yang menganalisis kebutuhan sistem dan alur proses bisnis aplikasi. |
| **UI** | *User Interface* | Antarmuka Pengguna (tampilan visual halaman web / aplikasi). |
| **UX** | *User Experience* | Pengalaman Pengguna saat berinteraksi dengan aplikasi. |
| **DB** | *Database* | Basis Data (penyimpanan data berupa tabel, kolom, dan relasi). |
| **SPA** | *Single Page Application* | Aplikasi Web Satu Halaman (misal berbasis Vue.js / React / Svelte). |
| **D3 / D3.js** | *Data-Driven Documents JavaScript library* | Pustaka JavaScript untuk visualisasi grafik & data interaktif berbasis SVG. |
| **JSON** | *JavaScript Object Notation* | Format standar pertukaran dan penyimpanan data terstruktur. |
| **HTML** | *HyperText Markup Language* | Format standar file halaman web interaktif. |
| **CORS** | *Cross-Origin Resource Sharing* | Mekanisme keamanan peramban web dalam membatasi akses lintas domain. |
| **CDN** | *Content Delivery Network* | Jaringan Pengiriman Konten web (LogicFlow **TIDAK** menggunakan CDN, seluruh D3.js di-bundle offline). |
| **LLM** | *Large Language Model* | Model Bahasa AI (digunakan opsional pada perintah `codemap ai`). |
| **HTTP** | *Hypertext Transfer Protocol* | Protokol web untuk pengiriman data (Method: GET, POST, PUT, PATCH, DELETE). |

---

## 🛠️ Stack & Spesifikasi Teknikal

- **CLI Engine**: Python 3.11 (*Standard Library*, tanpa *dependency* eksternal pihak ketiga)
- **Visualisasi Grafik**: D3.js v7 (*Data-Driven Documents*, di-bundle secara *offline* 279 KB, tanpa CDN)
- **Penyimpanan Metadata**: JSON (*JavaScript Object Notation*) di `~/.logicflow/projects.json`
- **Sistem Operasi**: macOS / Linux / Microsoft Windows

---

## 🤝 Lisensi

MIT License. Developed for fast code analysis, multi-project management, and stakeholder presentation.
