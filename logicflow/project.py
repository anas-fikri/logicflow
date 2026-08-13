#!/usr/bin/env python3
"""LogicFlow Project Manager — registry for managing multiple project scans & diagrams.

Stores project metadata in ~/.logicflow/projects.json
Each project tracks: source path, scan JSON, business diagram, developer diagram, last scan date, stats.

Usage:
  logicflow project add <name> <source-path> [--title TITLE]
  logicflow project add-remote <name> <url> [--token TOKEN] [--branch BRANCH]
                                             [--subdir PATH] [--title TITLE]
  logicflow project list
  logicflow project scan <name>           # re-scan (remote: pull dulu)
  logicflow project sync <name>           # pull latest + re-scan (remote only)
  logicflow project diagram <name>        # regenerate diagrams from existing scan
  logicflow project info <name>           # show project details
  logicflow project remove <name> [--purge]
  logicflow project open <name> [--mode business|developer]
  logicflow project dashboard             # open unified dashboard in browser
  logicflow project scan-all              # re-scan all projects"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from logicflow import remote as _remote

REGISTRY_DIR = Path.home() / ".logicflow"
REGISTRY_FILE = REGISTRY_DIR / "projects.json"
OUTPUT_DIR = REGISTRY_DIR / "output"
DASHBOARD_FILE = REGISTRY_DIR / "dashboard.html"


def _load_registry():
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"projects": {}}


def _save_registry(reg):
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Atomic write: write to temp file then replace to avoid corruption on interrupt
    tmp_fd, tmp_path = tempfile.mkstemp(dir=REGISTRY_DIR, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, REGISTRY_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    _generate_dashboard(reg)


def _generate_dashboard(reg):
    """Generate global dashboard.html."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from logicflow.dashboard import DashboardBuilder

    builder = DashboardBuilder()
    html = builder.build(reg)
    with open(DASHBOARD_FILE, "w") as f:
        f.write(html)


def _project_dir(name):
    return OUTPUT_DIR / name


def _ensure_project_dir(name):
    d = _project_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_project_add(args):
    """Register a new project."""
    source = os.path.abspath(args.source)
    if not os.path.isdir(source):
        print(f"Error: source directory not found: {source}")
        sys.exit(1)

    reg = _load_registry()
    name = args.name
    if name in reg["projects"] and not args.force:
        print(f"Error: project '{name}' already exists. Use --force to overwrite.")
        sys.exit(1)

    title = args.title or name.replace("-", " ").replace("_", " ").title()
    reg["projects"][name] = {
        "source": source,
        "title": title,
        "scan_file": None,
        "business_diagram": None,
        "developer_diagram": None,
        "last_scan": None,
        "stats": None,
        "created": datetime.now(tz=timezone.utc).isoformat(),
        "exclude": args.exclude or ["node_modules", ".git", "vendor", "dist"],
    }
    _save_registry(reg)
    print(f"Project '{name}' added.")
    print(f"  Source: {source}")
    print(f"  Title:  {title}")
    print(f"  Run 'logicflow project scan {name}' to generate dual-mode diagrams.")


def cmd_project_list(args):
    """List all registered projects."""
    reg = _load_registry()
    projects = reg["projects"]
    if not projects:
        print("No projects registered. Use 'logicflow project add <name> <path>' to add one.")
        return

    print(f"{'Name':<18} {'Title':<22} {'Menus':>5} {'APIs':>5} {'Nodes':>6} {'Last Scan':<19}")
    print("-" * 80)
    for name, p in sorted(projects.items()):
        stats = p.get("stats") or {}
        last = p.get("last_scan", "—")
        if last and last != "—":
            last = last[:19].replace("T", " ")
        menus = stats.get("menus", "—")
        apis = stats.get("apis", "—")
        nodes = stats.get("nodes", "—")
        print(f"{name:<18} {p.get('title','—'):<22} {menus!s:>5} {apis!s:>5} {nodes!s:>6} {last:<19}")


def _remote_pull_if_needed(name: str, p: dict, force_pull: bool = False) -> None:
    """Untuk remote project: pull latest sebelum scan."""
    if not _remote.is_remote_project(p):
        return
    _remote.check_git_available()
    repo_dir = _remote.REPOS_DIR / name
    if not repo_dir.exists():
        # Belum pernah clone — lakukan sekarang
        print("  Remote repo belum ada lokal, clone dulu …")
        _remote.ensure_local_clone(
            name=name,
            clone_url=p["remote_url"],
            branch=p.get("remote_branch"),
            token=p.get("remote_token"),
        )
    elif force_pull:
        _remote.pull_repo(
            dest=repo_dir,
            token=p.get("remote_token"),
            clone_url=p["remote_url"],
        )


def cmd_project_scan(args):
    """Re-scan project source and regenerate dual-mode diagrams."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    p = reg["projects"][name]

    # Remote project: pull latest sebelum scan
    _remote_pull_if_needed(name, p, force_pull=getattr(args, "pull", False))

    source = _remote.get_scan_root(p, name)
    exclude = p.get("exclude", ["node_modules", ".git", "vendor", "dist"])
    d = _ensure_project_dir(name)
    scan_file = str(d / "scan.json")
    biz_file = str(d / "business.html")
    dev_file = str(d / "developer.html")

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from logicflow.diagram import DiagramBuilder
    from logicflow.scanner import CodeScanner

    print(f"Scanning {source} ...")
    scanner = CodeScanner(root=source, exclude=exclude, project_name=name)
    result = scanner.scan()

    with open(scan_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  Scan JSON:   {scan_file} ({os.path.getsize(scan_file)} bytes)")

    builder = DiagramBuilder()
    biz_html, dev_html = builder.build_both(result, title=p.get("title", name))

    with open(biz_file, "w", encoding="utf-8") as f:
        f.write(biz_html)
    print(f"  Business:    {biz_file} ({os.path.getsize(biz_file)} bytes)")

    with open(dev_file, "w", encoding="utf-8") as f:
        f.write(dev_html)
    print(f"  Developer:   {dev_file} ({os.path.getsize(dev_file)} bytes)")

    # Update stats
    eps = result.get("endpoints", [])
    menus = set()
    for ep in eps:
        path = ep.get("path", "")
        parts = [x for x in path.split("/") if x and x not in ("api", "v1", "v2")]
        if parts:
            menus.add(parts[0])

    reg["projects"][name]["scan_file"] = scan_file
    reg["projects"][name]["business_diagram"] = biz_file
    reg["projects"][name]["developer_diagram"] = dev_file
    reg["projects"][name]["last_scan"] = datetime.now(tz=timezone.utc).isoformat()
    reg["projects"][name]["stats"] = {
        "endpoints": len(eps),
        "menus": len(menus),
        "apis": len(eps),
        "nodes": len(eps) + len(result.get("business_logic", [])) + len(result.get("validations", [])) + 1,
        "validations": len(result.get("validations", [])),
        "bizlogic": len(result.get("business_logic", [])),
        "languages": list({ep.get("language", "") for ep in eps}) if eps else [],
    }
    _save_registry(reg)

    s = reg["projects"][name]["stats"]
    print(f"  Stats: {s['nodes']} nodes, {s['menus']} menus, {s['apis']} APIs, {s['validations']} validations")


def cmd_project_diagram(args):
    """Regenerate diagrams from existing scan JSON."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    p = reg["projects"][name]
    scan_file = p.get("scan_file")
    if not scan_file or not os.path.isfile(scan_file):
        print(f"Error: no scan file for project '{name}'. Run 'logicflow project scan {name}' first.")
        sys.exit(1)

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from logicflow.diagram import DiagramBuilder

    with open(scan_file, encoding="utf-8") as f:
        result = json.load(f)

    d = _project_dir(name)
    biz_file = str(d / "business.html")
    dev_file = str(d / "developer.html")

    builder = DiagramBuilder()
    biz_html, dev_html = builder.build_both(result, title=p.get("title", name))

    with open(biz_file, "w", encoding="utf-8") as f:
        f.write(biz_html)
    with open(dev_file, "w", encoding="utf-8") as f:
        f.write(dev_html)

    reg["projects"][name]["business_diagram"] = biz_file
    reg["projects"][name]["developer_diagram"] = dev_file
    _save_registry(reg)
    print("Diagrams regenerated:")
    print(f"  Business:  {biz_file}")
    print(f"  Developer: {dev_file}")


def cmd_project_add_remote(args):
    """Register remote GitHub/GitLab repo dan clone ke lokal."""
    _remote.check_git_available()

    url = args.url
    if not _remote.validate_git_url(url):
        print(f"Error: URL tidak valid atau bukan git repo: {url}")
        sys.exit(1)

    parsed = _remote.parse_remote_url(url)
    clone_url = parsed["clone_url"]
    branch = args.branch or parsed["branch"]
    subdir = args.subdir or parsed["subdir"]
    token = getattr(args, "token", None) or os.environ.get("LOGICFLOW_TOKEN")

    reg = _load_registry()
    name = args.name
    if name in reg["projects"] and not args.force:
        print(f"Error: project '{name}' sudah ada. Gunakan --force untuk overwrite.")
        sys.exit(1)

    title = args.title or name.replace("-", " ").replace("_", " ").title()

    # Clone ke ~/.logicflow/repos/<name>/
    _remote.ensure_local_clone(
        name=name,
        clone_url=clone_url,
        branch=branch,
        token=token,
        force_clone=args.force,
    )

    # Resolve scan root (dengan subdir jika ada)
    scan_root = str((_remote.REPOS_DIR / name / subdir) if subdir else (_remote.REPOS_DIR / name))

    reg["projects"][name] = {
        "source": scan_root,          # path lokal actual yg di-scan
        "remote_url": clone_url,       # bare clone URL (tanpa token)
        "remote_branch": branch,
        "remote_subdir": subdir or "",
        "remote_platform": parsed["platform"],
        "remote_token": token,         # NOTE: disimpan di registry lokal saja
        "title": title,
        "scan_file": None,
        "business_diagram": None,
        "developer_diagram": None,
        "last_scan": None,
        "stats": None,
        "created": datetime.now(tz=timezone.utc).isoformat(),
        "exclude": args.exclude or ["node_modules", ".git", "vendor", "dist"],
    }
    _save_registry(reg)

    print(f"Project '{name}' (remote) berhasil ditambahkan.")
    print(f"  Platform:  {parsed['platform']}")
    print(f"  URL:       {parsed['original_url']}")
    print(f"  Branch:    {branch or 'default'}")
    print(f"  Subdir:    {subdir or '—'}")
    print(f"  Clone dir: {_remote.REPOS_DIR / name}")
    print(f"  Scan root: {scan_root}")
    print(f"  Jalankan: logicflow project scan {name}")


def cmd_project_sync(args):
    """Pull latest dari remote + re-scan (untuk remote project)."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' tidak ditemukan.")
        sys.exit(1)

    p = reg["projects"][name]
    if not _remote.is_remote_project(p):
        print(f"Project '{name}' adalah project lokal. Gunakan 'scan' saja.")
        sys.exit(1)

    print(f"Syncing '{name}' dari {p['remote_url']} …")

    # Force pull
    _remote.check_git_available()
    repo_dir = _remote.REPOS_DIR / name
    if not repo_dir.exists():
        _remote.ensure_local_clone(
            name=name,
            clone_url=p["remote_url"],
            branch=p.get("remote_branch"),
            token=p.get("remote_token"),
        )
    else:
        _remote.pull_repo(
            dest=repo_dir,
            token=p.get("remote_token"),
            clone_url=p["remote_url"],
        )

    # Re-scan setelah pull
    args.pull = False  # skip redudant pull di cmd_project_scan
    cmd_project_scan(args)


def cmd_project_info(args):
    """Show project details."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' tidak ditemukan.")
        sys.exit(1)

    p = reg["projects"][name]
    is_remote = _remote.is_remote_project(p)
    print(f"Project: {name}")
    print(f"  Title:       {p.get('title', '—')}")
    print(f"  Type:        {'remote (' + p.get('remote_platform','git') + ')' if is_remote else 'local'}")
    if is_remote:
        print(f"  Remote URL:  {p.get('remote_url', '—')}")
        print(f"  Branch:      {p.get('remote_branch') or 'default'}")
        print(f"  Subdir:      {p.get('remote_subdir') or '—'}")
        print(f"  Clone dir:   {_remote.REPOS_DIR / name}")
    print(f"  Scan root:   {_remote.get_scan_root(p, name)}")
    print(f"  Scan file:   {p.get('scan_file', '—')}")
    print(f"  Business:    {p.get('business_diagram', '—')}")
    print(f"  Developer:   {p.get('developer_diagram', '—')}")
    print(f"  Last scan:   {p.get('last_scan', '—')}")
    stats = p.get("stats")
    if stats:
        print(f"  Stats: {stats.get('nodes')} nodes, {stats.get('menus')} menus, {stats.get('apis')} APIs")


def cmd_project_remove(args):
    """Remove project from registry."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    removed_entry = reg["projects"].pop(name)
    _save_registry(reg)

    purge = getattr(args, "purge", False)
    if purge:
        d = _project_dir(name)
        # SECURITY: prevent path traversal — ensure d is inside OUTPUT_DIR
        try:
            resolved = d.resolve()
            if not str(resolved).startswith(str(OUTPUT_DIR.resolve())):
                print(f"Error: refusing to delete '{d}' — outside output directory.")
                sys.exit(1)
        except (OSError, ValueError) as e:
            print(f"Error resolving path: {e}")
            sys.exit(1)
        if d.exists():
            import shutil
            shutil.rmtree(d)
            print(f"Project '{name}' removed + output files purged.")

        # Juga hapus clone lokal kalau ini remote project
        if removed_entry and _remote.is_remote_project(removed_entry) and _remote.remove_local_clone(name):
            print(f"  Clone lokal di ~/.logicflow/repos/{name} dihapus.")
    else:
        print(f"Project '{name}' removed from registry.")


def cmd_project_open(args):
    """Open diagram in default browser."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    p = reg["projects"][name]
    mode = getattr(args, "mode", "both") or "both"

    def _safe_open_url(file_path):
        """Open file:// URL safely — validate path is absolute and exists."""
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            print(f"Error: file not found: {abs_path}")
            sys.exit(1)
        url = f"file://{abs_path}"
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return url

    if mode == "both":
        biz_path = p.get("business_diagram")
        dev_path = p.get("developer_diagram")
        if not biz_path or not os.path.isfile(biz_path):
            print(f"Error: diagrams for '{name}' not found. Run 'logicflow project scan {name}' first.")
            sys.exit(1)
        print(f"Opening Dual-Mode Diagrams for '{name}':")
        url_biz = _safe_open_url(biz_path)
        url_dev = _safe_open_url(dev_path)
        print(f"  💼 Business Flow: {url_biz}")
        print(f"  ⚡ Mode Developer Graph: {url_dev}")
    else:
        target_key = "business_diagram" if mode == "business" else "developer_diagram"
        file_path = p.get(target_key)
        if not file_path or not os.path.isfile(file_path):
            print(f"Error: no {mode} diagram for '{name}'. Run 'logicflow project scan {name}' first.")
            sys.exit(1)
        url = _safe_open_url(file_path)
        print(f"Opening {mode} diagram: {url}")


def cmd_project_dashboard(args):
    """Open unified dashboard in browser."""
    reg = _load_registry()
    _generate_dashboard(reg)

    if not DASHBOARD_FILE.exists():
        print("Error: failed to generate dashboard.")
        sys.exit(1)

    abs_path = os.path.abspath(DASHBOARD_FILE)
    url = f"file://{abs_path}"
    print(f"Opening Dashboard: {url}")
    subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cmd_project_scan_all(args):
    """Re-scan all registered projects."""
    reg = _load_registry()
    projects = reg["projects"]
    if not projects:
        print("No projects registered.")
        return

    total = len(projects)
    success = 0
    for i, name in enumerate(sorted(projects), 1):
        print(f"\n[{i}/{total}] Scanning {name} ...")
        try:
            class DummyArgs:
                pass
            dummy = DummyArgs()
            dummy.name = name
            cmd_project_scan(dummy)
            success += 1
        except (OSError, RuntimeError, SystemExit) as e:
            print(f"  ERROR: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR (unexpected): {e}")

    print(f"\nDone: {success}/{total} projects scanned successfully.")


def setup_project_subparser(sub):
    """Add 'project' subcommand to argparse."""
    sp = sub.add_parser("project", help="Manage multiple projects (registry & dashboard)")
    sub_p = sp.add_subparsers(dest="project_command", required=True)

    # add
    p = sub_p.add_parser("add", help="Register a local project")
    p.add_argument("name", help="Project name (unique identifier)")
    p.add_argument("source", help="Path to source directory")
    p.add_argument("-t", "--title", help="Display title for diagram")
    p.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor", "dist"])
    p.add_argument("--force", action="store_true", help="Overwrite existing project")
    p.set_defaults(func=cmd_project_add)

    # add-remote
    p = sub_p.add_parser("add-remote", help="Register & clone a remote GitHub/GitLab repo")
    p.add_argument("name", help="Project name (unique identifier)")
    p.add_argument("url", help="Git clone URL or tree URL (e.g. https://github.com/owner/repo)")
    p.add_argument("--token", help="Personal access token for private repo (or set LOGICFLOW_TOKEN env)")
    p.add_argument("--branch", help="Branch name to clone/scan")
    p.add_argument("--subdir", help="Subdirectory path within the repo to scan")
    p.add_argument("-t", "--title", help="Display title for diagram")
    p.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor", "dist"])
    p.add_argument("--force", action="store_true", help="Overwrite existing project clone")
    p.set_defaults(func=cmd_project_add_remote)

    # list
    p = sub_p.add_parser("list", help="List all registered projects")
    p.set_defaults(func=cmd_project_list)

    # scan
    p = sub_p.add_parser("scan", help="Re-scan project + regenerate dual diagrams")
    p.add_argument("name", help="Project name")
    p.add_argument("--pull", action="store_true", help="Force git pull for remote project before scan")
    p.set_defaults(func=cmd_project_scan)

    # sync
    p = sub_p.add_parser("sync", help="Git pull latest from remote + re-scan (remote project)")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_sync)

    # diagram
    p = sub_p.add_parser("diagram", help="Regenerate diagrams from existing scan")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_diagram)

    # info
    p = sub_p.add_parser("info", help="Show project details")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_info)

    # remove
    p = sub_p.add_parser("remove", help="Remove project from registry")
    p.add_argument("name", help="Project name")
    p.add_argument("--purge", action="store_true", help="Also delete scan & diagram files")
    p.set_defaults(func=cmd_project_remove)

    # open
    p = sub_p.add_parser("open", help="Open diagram in browser")
    p.add_argument("name", help="Project name")
    p.add_argument("-m", "--mode", choices=["business", "developer", "both"], default="both", help="Diagram mode to open (default: both)")
    p.set_defaults(func=cmd_project_open)

    # dashboard
    p = sub_p.add_parser("dashboard", help="Open unified project dashboard")
    p.set_defaults(func=cmd_project_dashboard)

    # scan-all
    p = sub_p.add_parser("scan-all", help="Re-scan all registered projects")
    p.set_defaults(func=cmd_project_scan_all)
