"""CodeMap AI — Natural language documentation generator.

Uses LLM API to analyze scan results and produce:
- Business flow descriptions
- Architecture overviews
- API documentation in plain language
- Onboarding guides
"""

import json
import os
import sys
from pathlib import Path


class AIDocumenter:
    """Generate AI-powered documentation from scan data."""

    SYSTEM_PROMPT = """You are a senior software architect and technical writer.
Analyze source code scan data and produce clear, actionable documentation
for developers and stakeholders. Focus on business value, not just code trivia.

Your output should be:
- In Bahasa Indonesia with English technical terms where appropriate
- Structured with clear headings and bullet points
- Focused on HOW and WHY, not just WHAT
- Suitable for onboarding new developers

Sections to produce:
1. Ringkasan Eksekutif (Executive Summary)
2. Arsitektur Aplikasi (Application Architecture)
3. Alur Bisnis Utama (Main Business Flows)
4. Endpoint API (API Endpoints)
5. Model Data (Data Model)
6. Validasi & Keamanan (Validation & Security)
7. Panduan Onboarding (Onboarding Guide)
"""

    def __init__(self, api_url=None, api_key=None, model=None):
        self.api_url = api_url or os.environ.get("AI_API_URL", "")
        self.api_key = api_key or os.environ.get("AI_API_KEY", "")
        self.model = model or os.environ.get("AI_MODEL", "default")

    def generate(self, scan_result, context=None):
        """Generate AI documentation from scan result."""
        if not self.api_url or not self.api_key:
            return self._generate_fallback(scan_result, context)

        # Build prompt from scan data
        prompt = self._build_prompt(scan_result, context)

        try:
            return self._call_llm(prompt)
        except Exception as e:
            print(f"AI generation failed: {e}", file=sys.stderr)
            return self._generate_fallback(scan_result, context)

    def _build_prompt(self, scan_result, context):
        summary = scan_result.get("summary", {})
        endpoints = scan_result.get("endpoints", [])
        tables = scan_result.get("database", {}).get("tables", {})
        validations = scan_result.get("validations", [])
        business = scan_result.get("business_logic", [])
        forms = scan_result.get("forms", [])

        prompt_parts = []

        if context:
            prompt_parts.append(f"KONTEKS BISNIS:\n{context}\n")

        prompt_parts.append(f"""SCAN RESULT SUMMARY:
- Bahasa: {', '.join(summary.get('languages', []))}
- File dipindai: {summary.get('total_files', 0)}
- Endpoint API: {summary.get('total_endpoints', 0)}
- Tabel DB: {summary.get('total_tables', 0)}
- Validasi: {summary.get('total_validations', 0)}
- Form/Page: {summary.get('total_forms', 0)}
- Business logic: {summary.get('total_business_logic', 0)}

METHOD BREAKDOWN:
{json.dumps(dict(list(summary.get('endpoints_by_method', {}).items())[:5]), indent=2)}

API ENDPOINTS (10 contoh):
{json.dumps(endpoints[:10], indent=2, ensure_ascii=False)}

TABLES (5 contoh):
{json.dumps(list(tables.items())[:5], indent=2, ensure_ascii=False)}

VALIDATIONS (5 contoh):
{json.dumps(validations[:5], indent=2, ensure_ascii=False)}

BUSINESS LOGIC (5 contoh):
{json.dumps(business[:5], indent=2, ensure_ascii=False)}

FORMS (5 contoh):
{json.dumps(forms[:5], indent=2, ensure_ascii=False)}

TUGAS:
Buat dokumentasi lengkap dengan 7 section di atas.
Fokus ke: bagaimana aplikasi ini bekerja, alur data, dan panduan developer baru.
""")

        return "\n".join(prompt_parts)

    def _call_llm(self, prompt):
        """Call LLM API."""
        import urllib.request
        import urllib.error

        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg = result["choices"][0]["message"]
            return msg.get("content") or msg.get("reasoning_content", "")

    def _generate_fallback(self, scan_result, context):
        """Fallback when AI API unavailable — generate structured docs manually."""
        summary = scan_result.get("summary", {})
        endpoints = scan_result.get("endpoints", [])
        tables = scan_result.get("database", {}).get("tables", {})
        validations = scan_result.get("validations", [])
        business = scan_result.get("business_logic", [])
        forms = scan_result.get("forms", [])

        lines = []
        lines.append(f"# CodeMap AI Documentation — {scan_result.get('meta', {}).get('root', 'Project')}\n")
        lines.append(f"*Dihasilkan dari scan otomatis. Untuk AI-enhanced docs, setup AI_API_URL + AI_API_KEY.*\n")

        # 1. Executive Summary
        lines.append("## 1. Ringkasan Eksekutif\n")
        lines.append(f"Proyek ini dibangun dengan stack: **{', '.join(summary.get('languages', []))}**.")
        lines.append(f"Terdapat **{summary.get('total_files', 0)} file** yang dipindai.")
        lines.append(f"Aplikasi mengekspos **{summary.get('total_endpoints', 0)} endpoint API**.")
        lines.append(f"Model data terdiri dari **{summary.get('total_tables', 0)} tabel**.")
        lines.append("")

        # 2. Architecture
        lines.append("## 2. Arsitektur Aplikasi\n")
        lines.append("```\n┌─────────────────────────────────────────────┐")
        
        # Group endpoints by path prefix
        grouped = {}
        for ep in endpoints[:30]:
            path = ep.get("path", "/")
            prefix = "/" + "/".join(path.strip("/").split("/")[:2]) if "/" in path.strip("/") else "/"
            grouped.setdefault(prefix, []).append(ep)

        services = sorted(grouped.keys())
        if services:
            for svc in services[:6]:
                eps = grouped[svc]
                methods = list(set(e.get("method","?") for e in eps))
                lines.append(f"│  [{','.join(methods)}] {svc:<40} │")
        lines.append("└─────────────────────────────────────────────┘\n")

        # 3. Business Flows
        lines.append("## 3. Alur Bisnis Utama\n")
        if business:
            lines.append("**Fungsi Bisnis Terdeteksi:**\n")
            seen = set()
            for fn in business[:15]:
                name = fn.get("name", "")
                if name not in seen:
                    seen.add(name)
                    ftype = fn.get("type", "function")
                    lines.append(f"- `{name}` — {ftype} @ {fn.get('file','?')}:{fn.get('line','?')}")
        lines.append("")

        # 4. API Endpoints
        lines.append("## 4. Endpoint API\n")
        if endpoints:
            lines.append("| Method | Path | File | Auth |")
            lines.append("|--------|------|------|------|")
            for ep in endpoints[:20]:
                lines.append(
                    f"| {ep.get('method','MIXED'):6} | `{ep['path']}` | "
                    f"{ep['file'].split('/')[-1]} | {ep.get('auth','?')} |"
                )
            if len(endpoints) > 20:
                lines.append(f"\n*... +{len(endpoints)-20} endpoint lainnya*\n")
        else:
            lines.append("*Tidak ada endpoint yang terdeteksi.*\n")

        # 5. Data Model
        lines.append("## 5. Model Data\n")
        if tables:
            lines.append(f"Terdapat **{len(tables)} tabel** dalam sistem:\n")
            for tbl, info in list(tables.items())[:10]:
                cols = info.get("columns", [])
                col_names = ", ".join(f"`{c['name']}`" for c in cols[:5])
                extra = f" (+{len(cols)-5} kolom)" if len(cols) > 5 else ""
                lines.append(f"- `{tbl}` — {col_names}{extra}")
            if len(tables) > 10:
                lines.append(f"\n*... +{len(tables)-10} tabel lainnya*\n")
        else:
            lines.append("*Tidak ada tabel yang terdeteksi (atau belum ada file SQL).*\n")

        # 6. Validation
        lines.append("## 6. Validasi & Keamanan\n")
        if validations:
            rules = {}
            for v in validations[:30]:
                rule = v.get("rule", v.get("type", "unknown"))
                rules[rule] = rules.get(rule, 0) + 1
            lines.append("**Rule Validasi Terdeteksi:**\n")
            for rule, count in sorted(rules.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"- `{rule}` — {count}x")
            lines.append("")
        else:
            lines.append("*Tidak ada validasi yang terdeteksi.*\n")

        # 7. Onboarding Guide
        lines.append("## 7. Panduan Onboarding Developer Baru\n")
        lines.append("### Struktur Direktori\n")
        if endpoints:
            files_with_eps = sorted(set(ep["file"] for ep in endpoints[:50]))
            lines.append("File utama dengan endpoint:")
            for f in files_with_eps[:10]:
                lines.append(f"- `{f}`")
            lines.append("")
        lines.append("### Langkah Setup\n")
        lines.append("1. Clone repository")
        lines.append("2. Install dependencies (`npm install` / `pip install` / `composer install`)")
        lines.append("3. Setup database sesuai schema di file SQL")
        lines.append("4. Copy `.env.example` → `.env`, isi konfigurasi")
        lines.append("5. Jalankan aplikasi dan verify endpoint dengan curl/postman\n")
        lines.append("### API Testing Checklist\n")
        for ep in endpoints[:8]:
            lines.append(f"- [ ] `{ep.get('method','GET')} {ep['path']}` — {ep.get('file','?').split('/')[-1]}")
        lines.append("")

        lines.append("---\n*Dihasilkan oleh CodeMap AI v1.0.0*")
        return "\n".join(lines)
