# 🚀 LogicFlow

**Source Code Visualizer & Dual-Mode Interactive Diagram Generator**

Scan source code dan generate 2 mode diagram dalam satu HTML:
- **Business Flow** — Alur bisnis berbasis stage & prerequisite (Bahasa Indonesia)
- **Developer Graph** — Force-directed graph endpoint, controller, validation, database

---

## 📦 Install (Pilih Salah Satu)

### Metode 1: PyPI (Recommended)
```bash
pip install logicflow
logicflow
```

### Metode 2: Standalone Binary (macOS arm64)
```bash
# Download dari GitHub Releases
curl -LO https://github.com/anas-fikri/logicflow/releases/download/v1.2.0/logicflow
chmod +x logicflow
./logicflow
```

### Metode 3: Install Script (Auto-detect Python)
```bash
curl -fsSL https://raw.githubusercontent.com/anas-fikri/logicflow/main/install.sh | bash
logicflow
```

### Metode 4: Development Install (dari Source)
```bash
git clone https://github.com/anas-fikri/logicflow.git
cd logicflow
pip install -e .
logicflow
```

---

## 🎯 Quick Start

```bash
# Mode 1: Interactive Wizard (Recommended untuk pertama kali)
logicflow

# Mode 2: CLI Langsung
logicflow project add-remote my-api https://github.com/owner/my-repo
logicflow project scan my-api
logicflow project open my-api

# Mode 3: Scan Lokal
logicflow scan /path/to/source-code
logicflow diagram /path/to/source-code --mode both
```

---

## 📋 Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| **Dual-Mode Diagram** | Business Flow (waterfall) + Developer Graph (force-directed) |
| **Remote Repository** | Clone & scan GitHub/GitLab/Bitbucket langsung dari URL |
| **Interactive Wizard** | Menu TTY untuk user yang prefer guided workflow |
| **Multi-Project Dashboard** | Unified dashboard untuk semua project terdaftar |
| **AST-Based Scanning** | Ekstrak endpoint, validation, database, business logic |
| **Zero CDN** | Offline-first, semua dependency embedded |
| **Bahasa Indonesia** | Label Business Flow dalam Bahasa Indonesia |

---

## 🛠️ Development

```bash
# Clone repo
git clone https://github.com/anas-fikri/logicflow.git
cd logicflow

# Install dependencies
pip install -e ".[dev]"

# Run linter & type checker
ruff check logicflow/
mypy logicflow/

# Build distribution
python3 -m build
./build-binary.sh
```

---

## 📊 Supported Languages

- **JavaScript/TypeScript** — Express, NestJS, Next.js, vanilla JS
- **Python** — Flask, Django, FastAPI
- **PHP** — Laravel, CodeIgniter, vanilla PHP

---

## 🚀 Distribution

| Platform | Command | Status |
|----------|---------|--------|
| **PyPI** | `pip install logicflow` | ✅ Published v1.2.0 |
| **macOS** | Binary (arm64) | ✅ Built |
| **Linux** | Binary (x86_64) | ⬜ CI/CD auto-build |
| **Windows** | Binary (.exe) | ⬜ CI/CD auto-build |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

Built with ❤️ for developers who need to understand codebase quickly.
