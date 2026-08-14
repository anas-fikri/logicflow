#!/usr/bin/env python3
"""LogicFlow Interactive Wizard — TTY menu-driven interactive interface.

Walks users through:
1. Register local project
2. Register remote repository (GitHub / GitLab / Bitbucket)
3. Scan registered project
4. Sync remote project
5. View project list & details
6. Open interactive diagrams in browser
7. Open multi-project dashboard
8. Remove project (with purge option)
"""

from __future__ import annotations

import getpass
import os
import sys
from dataclasses import dataclass
from typing import Any

from logicflow import project as _proj
from logicflow import remote as _remote


@dataclass(slots=True)
class _Args:
    """Mutable placeholder untuk argparse.Namespace (interaktif mode)."""

    name: str = ""
    source: str = ""
    title: str = ""
    exclude: list[str] | None = None
    force: bool = False
    pull: bool = False
    url: str = ""
    branch: str | None = None
    subdir: str | None = None
    token: str | None = None
    mode: str = "both"
    purge: bool = False

# ── ANSI Styling helpers ──────────────────────────────────────────────────────

_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _supports_color() -> bool:
    """Check if stdout is TTY and supports ANSI colors."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(text: str, color: str) -> str:
    if _supports_color():
        return f"{color}{text}{_RESET}"
    return text


# ── Generic Prompt Helpers ───────────────────────────────────────────────────


def prompt_input(
    label: str,
    default: str = "",
    required: bool = False,
    secret: bool = False,
) -> str:
    """Prompt user for text input with optional default and validation."""
    prompt_str = label
    if default:
        prompt_str += f" {_c(f'[{default}]', _DIM)}"
    prompt_str += ": "

    while True:
        try:
            if secret:
                val = getpass.getpass(prompt_str).strip()
            else:
                val = input(prompt_str).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperasi dibatalkan.")
            sys.exit(0)

        if not val and default:
            return default
        if not val and required:
            print(_c("  ⚠️ Input ini wajib diisi.", _RED))
            continue
        return val


def prompt_confirm(label: str, default: bool = True) -> bool:
    """Prompt user for Yes/No question."""
    suffix = " [Y/n]" if default else " [y/N]"
    try:
        ans = input(label + _c(suffix, _DIM) + ": ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nOperasi dibatalkan.")
        sys.exit(0)

    if not ans:
        return default
    return ans in ("y", "yes", "ya", "1")


def prompt_select_project(projects: dict, message: str = "Pilih project") -> str | None:
    """Show numbered list of projects and return selected project name."""
    if not projects:
        print(_c("\nBelum ada project terdaftar.", _YELLOW))
        return None

    print(f"\n{_c(message, _BOLD)}:")
    items = sorted(projects.items())
    for idx, (name, p) in enumerate(items, 1):
        is_remote = _remote.is_remote_project(p)
        ptype = _c(f"remote ({p.get('remote_platform','git')})", _CYAN) if is_remote else _c("local", _DIM)
        nodes = p.get("stats", {}).get("nodes", "—") if p.get("stats") else "—"
        print(f"  {_c(str(idx), _GREEN)}. {_c(name, _BOLD):<20} {p.get('title',''):<22} [{ptype}] ({nodes} nodes)")

    print(f"  {_c('0', _RED)}. Batal")

    while True:
        try:
            choice = input(_c(f"\nPilih nomor (0-{len(items)}): ", _BOLD)).strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if choice == "0":
            return None
        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(items):
                return items[num - 1][0]
        print(_c(f"Pilihan tidak valid. Ketik 1-{len(items)} atau 0.", _RED))


# ── Interactive Sub-Flows ────────────────────────────────────────────────────


def wizard_add_local() -> None:
    """Walkthrough: Add Local Project."""
    print(f"\n{_c('=== 📁 Tambah Project Lokal ===', _BOLD)}")
    name = prompt_input("Nama Project (ID unik)", required=True)

    # Sanitize name
    name = name.lower().replace(" ", "-")

    while True:
        source_path = prompt_input("Path Folder Source Code", required=True)
        abs_path = os.path.abspath(os.path.expanduser(source_path))
        if os.path.isdir(abs_path):
            break
        print(_c(f"  ⚠️ Folder tidak ditemukan: {abs_path}", _RED))

    default_title = name.replace("-", " ").replace("_", " ").title()
    title = prompt_input("Judul Display Diagram", default=default_title)

    # Call project module
    args = _Args()
    args.name = name
    args.source = abs_path
    args.title = title
    args.exclude = ["node_modules", ".git", "vendor", "dist"]
    args.force = True

    _proj.cmd_project_add(args)

    if prompt_confirm("\nJalankan scanning & buat diagram sekarang?"):
        args_scan = Args()
        args_scan.name = name
        args_scan.pull = False
        _proj.cmd_project_scan(args_scan)
        prompt_open_diagram(name)


def wizard_add_remote() -> None:
    """Walkthrough: Add Remote Repository."""
    print(f"\n{_c('=== 🌐 Tambah Repository Remote (GitHub/GitLab) ===', _BOLD)}")
    print(_c("Contoh URL: https://github.com/owner/repo atau URL /tree/branch/subdir", _DIM))

    url = prompt_input("URL Repository", required=True)
    parsed = _remote.parse_remote_url(url)

    # Infer default project name from repo URL
    default_name = parsed["clone_url"].rstrip(".git").split("/")[-1].lower()
    name = prompt_input("Nama Project", default=default_name, required=True)
    name = name.lower().replace(" ", "-")

    branch = prompt_input("Branch (kosongkan untuk default branch)", default=parsed["branch"] or "")
    subdir = prompt_input("Subdirectory (kosongkan bila scan seluruh repo)", default=parsed["subdir"] or "")
    token = prompt_input("Personal Access Token (opsional untuk private repo)", secret=True)

    default_title = name.replace("-", " ").replace("_", " ").title()
    title = prompt_input("Judul Display Diagram", default=default_title)

    args = _Args()
    args.name = name
    args.url = url
    args.branch = branch or None
    args.subdir = subdir or None
    args.token = token or None
    args.title = title
    args.exclude = ["node_modules", ".git", "vendor", "dist"]
    args.force = True

    _proj.cmd_project_add_remote(args)

    if prompt_confirm("\nJalankan scanning & buat diagram sekarang?"):
        args_scan = Args()
        args_scan.name = name
        args_scan.pull = False
        _proj.cmd_project_scan(args_scan)
        prompt_open_diagram(name)


def wizard_scan_project() -> None:
    """Walkthrough: Scan Existing Project."""
    reg = _proj._load_registry()
    name = prompt_select_project(reg["projects"], "Pilih Project untuk Di-Scan")
    if not name:
        return

    p = reg["projects"][name]
    args = _Args()
    args.name = name
    args.pull = False

    if _remote.is_remote_project(p) and prompt_confirm("Pull commit terbaru dari remote sebelum scan?"):
        args.pull = True

    _proj.cmd_project_scan(args)
    prompt_open_diagram(name)


def wizard_sync_project() -> None:
    """Walkthrough: Sync Remote Project."""
    reg = _proj._load_registry()
    remote_projects = {k: v for k, v in reg["projects"].items() if _remote.is_remote_project(v)}

    if not remote_projects:
        print(_c("\nBelum ada project remote terdaftar. Gunakan Opsi 2 untuk menambah repo remote.", _YELLOW))
        return

    name = prompt_select_project(remote_projects, "Pilih Remote Project untuk Di-Sync")
    if not name:
        return

    args = _Args()
    args.name = name

    _proj.cmd_project_sync(args)
    prompt_open_diagram(name)


def wizard_list_projects() -> None:
    """Walkthrough: View Project List."""
    print(f"\n{_c('=== 📋 Daftar Project Terdaftar ===', _BOLD)}")
    _proj.cmd_project_list(_Args())

    reg = _proj._load_registry()
    if reg["projects"] and prompt_confirm("\nLihat detail spesifik dari satu project?"):
        name = prompt_select_project(reg["projects"], "Pilih Project")
        if name:
            args = Args()
            args.name = name
            print()
            _proj.cmd_project_info(args)


def wizard_open_project() -> None:
    """Walkthrough: Open Diagram / Dashboard."""
    reg = _proj._load_registry()
    if not reg["projects"]:
        print(_c("\nBelum ada project terdaftar.", _YELLOW))
        return

    print(f"\n{_c('=== 🖥️ Buka Diagram / Dashboard ===', _BOLD)}")
    print(f"  1. Buka {_c('Unified Multi-Project Dashboard', _BOLD)}")
    print("  2. Buka Diagram Spesifik Project")

    choice = input("\nPilih (1-2): ").strip()

    if choice == "1":
        _proj.cmd_project_dashboard(_Args())
    elif choice == "2":
        name = prompt_select_project(reg["projects"], "Pilih Project")
        if name:
            print("\nPilih Mode Diagram:")
            print("  1. Both (Buka Business Flow & Developer Graph)")
            print("  2. Business Flow saja")
            print("  3. Developer Graph saja")
            m_choice = input("Pilih (1-3) [default: 1]: ").strip()

            mode_map = {"1": "both", "2": "business", "3": "developer", "": "both"}
            args = Args()
            args.name = name
            args.mode = mode_map.get(m_choice, "both")
            _proj.cmd_project_open(args)


def wizard_remove_project() -> None:
    """Walkthrough: Remove Project."""
    reg = _proj._load_registry()
    name = prompt_select_project(reg["projects"], "Pilih Project yang Akan Dihapus")
    if not name:
        return

    purge = prompt_confirm(f"Hapus juga file diagram & cache clone lokal untuk '{name}'?", default=False)

    args = _Args()
    args.name = name
    args.purge = purge

    _proj.cmd_project_remove(args)


def prompt_open_diagram(name: str) -> None:
    """Ask if user wants to open the diagram right after scan."""
    if prompt_confirm("\nBuka diagram di browser sekarang?"):
        args = _Args()
        args.name = name
        args.mode = "both"
        _proj.cmd_project_open(args)


# ── Main Wizard Loop ──────────────────────────────────────────────────────────


def run_wizard() -> None:
    """Run interactive terminal menu loop."""
    print(_c("\n" + "═" * 60, _CYAN))
    print(_c("  🚀 LogicFlow — Interactive Project Visualizer Wizard", _BOLD))
    print(_c("═" * 60, _CYAN))

    while True:
        reg = _proj._load_registry()
        count = len(reg["projects"])

        print(f"\n{_c('MENU UTAMA', _BOLD)} {_c(f'({count} project terdaftar)', _DIM)}:")
        print(f"  {_c('1', _GREEN)}. 📁 Tambah Project Lokal")
        print(f"  {_c('2', _GREEN)}. 🌐 Tambah Repository Remote (GitHub / GitLab)")
        print(f"  {_c('3', _GREEN)}. 🔍 Scan Project Existing")
        print(f"  {_c('4', _GREEN)}. 🔄 Sync Remote Project (Pull & Re-scan)")
        print(f"  {_c('5', _GREEN)}. 📋 Lihat Daftar Project & Details")
        print(f"  {_c('6', _GREEN)}. 🖥️ Buka Diagram / Dashboard di Browser")
        print(f"  {_c('7', _RED)}. 🗑️ Hapus Project")
        print(f"  {_c('0', _DIM)}. Exit")

        try:
            choice = input(_c("\nPilih nomor (0-7): ", _BOLD)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa! 👋")
            sys.exit(0)

        if choice == "1":
            wizard_add_local()
        elif choice == "2":
            wizard_add_remote()
        elif choice == "3":
            wizard_scan_project()
        elif choice == "4":
            wizard_sync_project()
        elif choice == "5":
            wizard_list_projects()
        elif choice == "6":
            wizard_open_project()
        elif choice == "7":
            wizard_remove_project()
        elif choice in ("0", "exit", "quit", "q"):
            print("\nSampai jumpa! 👋")
            sys.exit(0)
        else:
            print(_c("Pilihan tidak valid. Masukkan angka 0-7.", _RED))
