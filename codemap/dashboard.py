"""CodeMap Dashboard — HTML Generator for Project Registry.

Generates a unified dashboard.html showing all registered projects,
their stats, and links to open Business Flow or Developer Graph.
"""

import json
from pathlib import Path

DASHBOARD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeMap Dashboard — Management & Visualisasi Project</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-height: 100vh; display: flex; flex-direction: column; }

header { background: #161b22; border-bottom: 1px solid #30363d; padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }
header .brand { display: flex; align-items: center; gap: 12px; }
header .brand h1 { font-size: 20px; font-weight: 700; color: #58a6ff; }
header .brand .version { font-size: 11px; background: #30363d; padding: 2px 8px; border-radius: 12px; color: #8b949e; }
header .subtitle { font-size: 13px; color: #8b949e; margin-top: 4px; }

main { flex: 1; max-width: 1200px; width: 100%; margin: 0 auto; padding: 32px 24px; }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.search-box input { width: 320px; padding: 9px 14px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 13px; }
.search-box input:focus { outline: none; border-color: #58a6ff; }

.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }

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
.btn { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 8px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; transition: all 0.15s; cursor: pointer; border: 1px solid transparent; }
.btn-biz { background: #238636; color: #fff; }
.btn-biz:hover { background: #2ea043; }
.btn-dev { background: #1f6feb; color: #fff; }
.btn-dev:hover { background: #388bfd; }

.empty-state { text-align: center; padding: 64px 20px; color: #8b949e; }
.empty-state h3 { font-size: 16px; margin-bottom: 8px; color: #c9d1d9; }
.empty-state code { background: #161b22; padding: 4px 8px; border-radius: 4px; color: #58a6ff; font-family: monospace; }

footer { border-top: 1px solid #30363d; padding: 16px 32px; text-align: center; font-size: 12px; color: #484f58; background: #161b22; }
</style>
</head>
<body>

<header>
  <div>
    <div class="brand">
      <h1>CodeMap Dashboard</h1>
      <span class="version">v1.0.0</span>
    </div>
    <div class="subtitle">Visualisasi Source Code & Analisis Arsitektur Aplikasi</div>
  </div>
</header>

<main>
  <div class="toolbar">
    <div class="search-box">
      <input type="text" id="search" placeholder="Cari project terdaftar..." oninput="filterProjects(this.value)">
    </div>
    <div style="font-size:13px;color:#8b949e;" id="total-summary">__TOTAL_PROJECTS__ Project Terdaftar</div>
  </div>

  <div class="project-grid" id="grid">
    __PROJECT_CARDS__
  </div>

  __EMPTY_STATE__
</main>

<footer>
  CodeMap CLI — Corporate Source Code Visualizer & Diagram Generator
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

            # Output paths relative or absolute
            biz_url = f"output/{name}/business.html"
            dev_url = f"output/{name}/developer.html"

            card = f"""
    <div class="project-card" data-name="{name}">
      <div>
        <div class="card-header">
          <h2>{title}</h2>
          <span class="lang-tag">{langs}</span>
        </div>
        <div class="card-meta">
          <div class="path" title="{source}">📁 {source}</div>
          <div>🕒 Last scan: {last}</div>
        </div>
        <div class="card-stats">
          <div class="stat-box">
            <div class="num">{menus}</div>
            <div class="lbl">Menu</div>
          </div>
          <div class="stat-box">
            <div class="num">{apis}</div>
            <div class="lbl">APIs</div>
          </div>
          <div class="stat-box">
            <div class="num">{nodes}</div>
            <div class="lbl">Nodes</div>
          </div>
        </div>
      </div>
      <div class="card-actions">
        <a href="{biz_url}" class="btn btn-biz">💼 Mode Awam</a>
        <a href="{dev_url}" class="btn btn-dev">⚡ Developer</a>
      </div>
    </div>
"""
            cards_html.append(card)

        total = len(projects)
        if total == 0:
          empty_state = """
  <div class="empty-state">
    <h3>Belum Ada Project Terdaftar</h3>
    <p>Gunakan perintah CLI berikut untuk menambahkan project:</p>
    <br>
    <code>codemap project add myapp /path/to/source --title "My Application"</code>
    <br><br>
    <code>codemap project scan myapp</code>
  </div>
"""
        else:
          empty_state = ""

        html = DASHBOARD_TEMPLATE.replace("__TITLE__", "CodeMap Dashboard")
        html = html.replace("__TOTAL_PROJECTS__", str(total))
        html = html.replace("__PROJECT_CARDS__", "\n".join(cards_html))
        html = html.replace("__EMPTY_STATE__", empty_state)
        return html
