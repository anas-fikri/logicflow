"""LogicFlow Dashboard — HTML Generator for Project Registry.

Generates a unified dashboard.html showing all registered projects,
their stats, and links to open Business Flow or Developer Graph.
"""

import html as html_lib

DASHBOARD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LogicFlow Dashboard — Management & Visualisasi Multi-Project</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-height: 100vh; display: flex; flex-direction: column; }

header { background: #161b22; border-bottom: 1px solid #30363d; padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }
header .brand { display: flex; align-items: center; gap: 12px; }
header .brand h1 { font-size: 20px; font-weight: 700; color: #58a6ff; }
header .brand .version { font-size: 11px; background: #30363d; padding: 2px 8px; border-radius: 12px; color: #8b949e; }
header .subtitle { font-size: 13px; color: #8b949e; margin-top: 4px; }

main { flex: 1; max-width: 1240px; width: 100%; margin: 0 auto; padding: 32px 24px; display: flex; flex-direction: column; gap: 28px; }

/* Banner Guidance */
.guide-banner { background: #161b22; border: 1px solid #30363d; border-left: 4px solid #58a6ff; border-radius: 8px; padding: 20px 24px; }
.guide-banner h2 { font-size: 16px; color: #58a6ff; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.guide-banner p { font-size: 13px; color: #8b949e; line-height: 1.5; margin-bottom: 12px; }
.guide-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.step-card { background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px 16px; font-size: 12px; }
.step-card .step-num { color: #58a6ff; font-weight: 700; margin-bottom: 4px; }
.step-card code { background: #161b22; color: #79c0ff; padding: 2px 6px; border-radius: 4px; font-family: monospace; }

.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.search-box input { width: 340px; padding: 9px 14px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 13px; }
.search-box input:focus { outline: none; border-color: #58a6ff; }

.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }

.project-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.15s; }
.project-card:hover { border-color: #58a6ff; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }

.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.card-header h2 { font-size: 18px; font-weight: 600; color: #e6edf3; }
.card-header .lang-tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; background: #21262d; color: #58a6ff; text-transform: uppercase; font-weight: 600; }

.card-meta { font-size: 12px; color: #8b949e; margin-bottom: 16px; display: flex; flex-direction: column; gap: 4px; }
.card-meta .path { font-family: monospace; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.card-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 20px; background: #0d1117; padding: 12px; border-radius: 6px; border: 1px solid #21262d; }
.stat-box { text-align: center; }
.stat-box .num { font-size: 16px; font-weight: 700; color: #58a6ff; }
.stat-box .lbl { font-size: 10px; color: #8b949e; text-transform: uppercase; margin-top: 2px; }

.card-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.btn { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 9px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; transition: all 0.15s; cursor: pointer; border: 1px solid transparent; }
.btn-biz { background: #238636; color: #fff; }
.btn-biz:hover { background: #2ea043; }
.btn-dev { background: #1f6feb; color: #fff; }
.btn-dev:hover { background: #388bfd; }

/* Legend Section */
.legend-section { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px 24px; margin-top: 12px; }
.legend-section h3 { font-size: 15px; color: #e6edf3; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
.legend-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.legend-item { background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 10px 14px; }
.legend-item .term { font-weight: 700; color: #58a6ff; font-size: 12px; font-family: monospace; }
.legend-item .full { color: #e6edf3; font-size: 12px; font-weight: 600; margin-top: 2px; }
.legend-item .desc { color: #8b949e; font-size: 11px; margin-top: 4px; line-height: 1.4; }

.empty-state { text-align: center; padding: 64px 20px; color: #8b949e; background: #161b22; border: 1px dashed #30363d; border-radius: 8px; }
.empty-state h3 { font-size: 16px; margin-bottom: 8px; color: #c9d1d9; }
.empty-state code { background: #0d1117; padding: 4px 8px; border-radius: 4px; color: #58a6ff; font-family: monospace; }

footer { border-top: 1px solid #30363d; padding: 16px 32px; text-align: center; font-size: 12px; color: #484f58; background: #161b22; margin-top: auto; }
</style>
</head>
<body>

<header>
  <div>
    <div class="brand">
      <h1>LogicFlow Dashboard</h1>
      <span class="version">v1.1.0</span>
    </div>
    <div class="subtitle">Management & Visualisasi Multi-Project (Otomatis Dual-Mode: Business Flow & Developer Graph)</div>
  </div>
</header>

<main>
  <!-- Multi-Project Guide -->
  <section class="guide-banner">
    <h2>🗺️ Cara Pengelolaan Multi-Project di LogicFlow Dashboard</h2>
    <p>LogicFlow menyimpan seluruh metadata project di registry <code>~/.logicflow/projects.json</code>. Setiap project yang discan akan **otomatis menghasilkan 2 mode visualisasi** sekaligus (Business Flow & Mode Developer).</p>
    <div class="guide-steps">
      <div class="step-card">
        <div class="step-num">1. Tambah Project Baru</div>
        <div>Daftarkan codebase ke registry:</div>
        <code>logicflow project add &lt;nama&gt; &lt;path_source&gt; --title "&lt;Judul&gt;"</code>
      </div>
      <div class="step-card">
        <div class="step-num">2. Scan Otomatis Both Modes</div>
        <div>Pindai & buat diagram dual-mode:</div>
        <code>logicflow project scan &lt;nama&gt;</code>
      </div>
      <div class="step-card">
        <div class="step-num">3. Scan Semua Project</div>
        <div>Pindai ulang seluruh project sekaligus:</div>
        <code>logicflow project scan-all</code>
      </div>
    </div>
  </section>

  <div class="toolbar">
    <div class="search-box">
      <input type="text" id="search" placeholder="Cari project terdaftar (nama, path, bahasa)..." oninput="filterProjects(this.value)">
    </div>
    <div style="font-size:13px;color:#8b949e;" id="total-summary">__TOTAL_PROJECTS__ Project Terdaftar</div>
  </div>

  <div class="project-grid" id="grid">
    __PROJECT_CARDS__
  </div>

  __EMPTY_STATE__

  <!-- Legend Section -->
  <section class="legend-section">
    <h3>📖 Legend Singkatan & Istilah (Glossary of Abbreviations)</h3>
    <div class="legend-grid">
      <div class="legend-item">
        <div class="term">API</div>
        <div class="full">Application Programming Interface</div>
        <div class="desc">Antarmuka Pemrograman Aplikasi yang menghubungkan antarmuka pengguna (UI) dengan server backend.</div>
      </div>
      <div class="legend-item">
        <div class="term">AST</div>
        <div class="full">Abstract Syntax Tree</div>
        <div class="desc">Pohon Sintaks Abstrak yang digunakan scanner untuk mengurai dan menganalisis kode program tanpa AI.</div>
      </div>
      <div class="legend-item">
        <div class="term">CLI</div>
        <div class="full">Command Line Interface</div>
        <div class="desc">Antarmuka baris perintah terminal tempat menjalankan aplikasi LogicFlow.</div>
      </div>
      <div class="legend-item">
        <div class="term">BA</div>
        <div class="full">Business Analyst</div>
        <div class="desc">Analis Bisnis yang menggunakan Mode Business Flow untuk memahami alur proses aplikasi.</div>
      </div>
      <div class="legend-item">
        <div class="term">UI / UX</div>
        <div class="full">User Interface / User Experience</div>
        <div class="desc">Tampilan Antarmuka Pengguna (UI) dan Pengalaman Pengguna (UX) pada aplikasi.</div>
      </div>
      <div class="legend-item">
        <div class="term">DB</div>
        <div class="full">Database (Basis Data)</div>
        <div class="desc">Penyimpanan data permanen berupa tabel, kolom, dan relasi antar data.</div>
      </div>
      <div class="legend-item">
        <div class="term">HTTP Methods</div>
        <div class="full">GET, POST, PUT, DELETE</div>
        <div class="desc">GET (Ambil data), POST (Tambah data), PUT/PATCH (Ubah data), DELETE (Hapus data).</div>
      </div>
      <div class="legend-item">
        <div class="term">JSON</div>
        <div class="full">JavaScript Object Notation</div>
        <div class="desc">Format pertukaran data ringan yang digunakan untuk menyimpan hasil pemindaian kode.</div>
      </div>
      <div class="legend-item">
        <div class="term">HTML</div>
        <div class="full">HyperText Markup Language</div>
        <div class="desc">Format file halaman web interaktif yang dihasilkan oleh LogicFlow untuk visualisasi.</div>
      </div>
    </div>
  </section>
</main>

<footer>
  LogicFlow CLI — Corporate Source Code Visualizer & Multi-Project Dashboard
</footer>

<script>
function filterProjects(q) {
  const cards = document.querySelectorAll('.project-card');
  const ql = q.toLowerCase();
  let visible = 0;
  cards.forEach(c => {
    const text = c.textContent.toLowerCase();
    if (text.includes(ql)) {
      c.style.display = 'flex';
      visible++;
    } else {
      c.style.display = 'none';
    }
  });
  document.getElementById('total-summary').textContent = visible + ' Project Ditampilkan';
}
</script>
</body>
</html>
"""


class DashboardBuilder:
    """Generate interactive dashboard.html from registry data."""

    def build(self, registry):
        """Build HTML string from projects registry dict."""
        projects = registry.get("projects", {})
        cards_html = []

        for name, p in sorted(projects.items()):
            title = p.get("title", name)
            source = p.get("source", "—")
            last = p.get("last_scan", "—")
            if last and last != "—":
                last = last[:19].replace("T", " ")

            stats = p.get("stats") or {}
            menus = stats.get("menus", 0)
            apis = stats.get("apis", 0)
            nodes = stats.get("nodes", 0)
            langs = ", ".join(stats.get("languages", [])) or "Multi-lang"

            # Output paths relative to ~/.logicflow/dashboard.html
            biz_url = f"output/{name}/business.html"
            dev_url = f"output/{name}/developer.html"

            # Escape all user-controlled values to prevent XSS / HTML injection
            safe_name = html_lib.escape(str(name))
            safe_title = html_lib.escape(str(title))
            safe_source = html_lib.escape(str(source))
            safe_langs = html_lib.escape(str(langs))
            safe_last = html_lib.escape(str(last))
            safe_menus = html_lib.escape(str(menus))
            safe_apis = html_lib.escape(str(apis))
            safe_nodes = html_lib.escape(str(nodes))
            # URL-encode project name for href safety (only alphanumeric + dash/underscore allowed)
            import re as _re
            safe_url_name = _re.sub(r'[^a-zA-Z0-9_\-]', '_', str(name))
            biz_url = f"output/{safe_url_name}/business.html"
            dev_url = f"output/{safe_url_name}/developer.html"

            card = f"""
    <div class="project-card" data-name="{safe_name}">
      <div>
        <div class="card-header">
          <h2>{safe_title}</h2>
          <span class="lang-tag">{safe_langs}</span>
        </div>
        <div class="card-meta">
          <div class="path" title="{safe_source}">📁 {safe_source}</div>
          <div>🕒 Pemindaian Terakhir: {safe_last}</div>
        </div>
        <div class="card-stats">
          <div class="stat-box">
            <div class="num">{safe_menus}</div>
            <div class="lbl">Menu (UI)</div>
          </div>
          <div class="stat-box">
            <div class="num">{safe_apis}</div>
            <div class="lbl">API</div>
          </div>
          <div class="stat-box">
            <div class="num">{safe_nodes}</div>
            <div class="lbl">Node</div>
          </div>
        </div>
      </div>
      <div class="card-actions">
        <a href="{biz_url}" class="btn btn-biz">💼 Business Flow</a>
        <a href="{dev_url}" class="btn btn-dev">⚡ Mode Developer (Graph)</a>
      </div>
    </div>
"""
            cards_html.append(card)

        total = len(projects)
        if total == 0:
            empty_state = """
  <div class="empty-state">
    <h3>Belum Ada Project Terdaftar</h3>
    <p>Daftarkan project pertama Anda dengan perintah CLI berikut:</p>
    <br>
    <code>logicflow project add myapp /path/to/source --title "My Application"</code>
    <br><br>
    <code>logicflow project scan myapp</code>
  </div>
"""
        else:
            empty_state = ""

        html = DASHBOARD_TEMPLATE.replace("__TOTAL_PROJECTS__", str(total))
        html = html.replace("__PROJECT_CARDS__", "\n".join(cards_html))
        html = html.replace("__EMPTY_STATE__", empty_state)
        return html
