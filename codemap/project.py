#!/usr/bin/env python3
"""CodeMap Project Manager — registry for managing multiple project scans & diagrams.

Stores project metadata in ~/.codemap/projects.json
Each project tracks: source path, scan JSON, business diagram, developer diagram, last scan date, stats.

Usage:
  codemap project add <name> <source-path> [--title TITLE]
  codemap project list
  codemap project scan <name>           # re-scan + generate business & dev diagrams
  codemap project diagram <name>        # regenerate diagrams from existing scan
  codemap project info <name>           # show project details
  codemap project remove <name>
  codemap project open <name> [--mode business|developer]
  codemap project dashboard             # open unified dashboard in browser
  codemap project scan-all              # re-scan all projects
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

REGISTRY_DIR = Path.home() / ".codemap"
REGISTRY_FILE = REGISTRY_DIR / "projects.json"
OUTPUT_DIR = REGISTRY_DIR / "output"
DASHBOARD_FILE = REGISTRY_DIR / "dashboard.html"


def _load_registry():
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {"projects": {}}


def _save_registry(reg):
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
    _generate_dashboard(reg)


def _generate_dashboard(reg):
    """Generate global dashboard.html."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from codemap.dashboard import DashboardBuilder

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
        "created": datetime.now().isoformat(),
        "exclude": args.exclude or ["node_modules", ".git", "vendor", "dist"],
    }
    _save_registry(reg)
    print(f"Project '{name}' added.")
    print(f"  Source: {source}")
    print(f"  Title:  {title}")
    print(f"  Run 'codemap project scan {name}' to generate dual-mode diagrams.")


def cmd_project_list(args):
    """List all registered projects."""
    reg = _load_registry()
    projects = reg["projects"]
    if not projects:
        print("No projects registered. Use 'codemap project add <name> <path>' to add one.")
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
        print(f"{name:<18} {p.get('title','—'):<22} {str(menus):>5} {str(apis):>5} {str(nodes):>6} {last:<19}")


def cmd_project_scan(args):
    """Re-scan project source and regenerate dual-mode diagrams."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    p = reg["projects"][name]
    source = p["source"]
    exclude = p.get("exclude", ["node_modules", ".git", "vendor", "dist"])
    d = _ensure_project_dir(name)
    scan_file = str(d / "scan.json")
    biz_file = str(d / "business.html")
    dev_file = str(d / "developer.html")

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from codemap.scanner import CodeScanner
    from codemap.diagram import DiagramBuilder

    print(f"Scanning {source} ...")
    scanner = CodeScanner(root=source, exclude=exclude)
    result = scanner.scan()

    with open(scan_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  Scan JSON:   {scan_file} ({os.path.getsize(scan_file)} bytes)")

    builder = DiagramBuilder()
    biz_html, dev_html = builder.build_both(result, title=p.get("title", name))

    with open(biz_file, "w") as f:
        f.write(biz_html)
    print(f"  Business:    {biz_file} ({os.path.getsize(biz_file)} bytes)")

    with open(dev_file, "w") as f:
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
    reg["projects"][name]["last_scan"] = datetime.now().isoformat()
    reg["projects"][name]["stats"] = {
        "endpoints": len(eps),
        "menus": len(menus),
        "apis": len(eps),
        "nodes": len(eps) + len(result.get("business_logic", [])) + len(result.get("validations", [])) + 1,
        "validations": len(result.get("validations", [])),
        "bizlogic": len(result.get("business_logic", [])),
        "languages": list(set(ep.get("language", "") for ep in eps)) if eps else [],
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
        print(f"Error: no scan file for project '{name}'. Run 'codemap project scan {name}' first.")
        sys.exit(1)

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from codemap.diagram import DiagramBuilder

    with open(scan_file) as f:
        result = json.load(f)

    d = _project_dir(name)
    biz_file = str(d / "business.html")
    dev_file = str(d / "developer.html")

    builder = DiagramBuilder()
    biz_html, dev_html = builder.build_both(result, title=p.get("title", name))

    with open(biz_file, "w") as f:
        f.write(biz_html)
    with open(dev_file, "w") as f:
        f.write(dev_html)

    reg["projects"][name]["business_diagram"] = biz_file
    reg["projects"][name]["developer_diagram"] = dev_file
    _save_registry(reg)
    print(f"Diagrams regenerated:")
    print(f"  Business:  {biz_file}")
    print(f"  Developer: {dev_file}")


def cmd_project_info(args):
    """Show project details."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    p = reg["projects"][name]
    print(f"Project: {name}")
    print(f"  Title:       {p.get('title', '—')}")
    print(f"  Source:      {p.get('source', '—')}")
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

    del reg["projects"][name]
    _save_registry(reg)

    if args.purge:
        d = _project_dir(name)
        if d.exists():
            import shutil
            shutil.rmtree(d)
            print(f"Project '{name}' removed + files purged.")
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
    mode = getattr(args, "mode", "business") or "business"
    target_key = "business_diagram" if mode == "business" else "developer_diagram"
    file_path = p.get(target_key) or p.get("diagram_file")

    if not file_path or not os.path.isfile(file_path):
        print(f"Error: no {mode} diagram for '{name}'. Run 'codemap project scan {name}' first.")
        sys.exit(1)

    url = f"file://{os.path.abspath(file_path)}"
    print(f"Opening {mode} diagram: {url}")
    subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cmd_project_dashboard(args):
    """Open unified dashboard in browser."""
    reg = _load_registry()
    _generate_dashboard(reg)

    if not DASHBOARD_FILE.exists():
        print("Error: failed to generate dashboard.")
        sys.exit(1)

    url = f"file://{os.path.abspath(DASHBOARD_FILE)}"
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
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone: {success}/{total} projects scanned successfully.")


def setup_project_subparser(sub):
    """Add 'project' subcommand to argparse."""
    sp = sub.add_parser("project", help="Manage multiple projects (registry & dashboard)")
    sub_p = sp.add_subparsers(dest="project_command", required=True)

    # add
    p = sub_p.add_parser("add", help="Register a new project")
    p.add_argument("name", help="Project name (unique identifier)")
    p.add_argument("source", help="Path to source directory")
    p.add_argument("-t", "--title", help="Display title for diagram")
    p.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor", "dist"])
    p.add_argument("--force", action="store_true", help="Overwrite existing project")
    p.set_defaults(func=cmd_project_add)

    # list
    p = sub_p.add_parser("list", help="List all registered projects")
    p.set_defaults(func=cmd_project_list)

    # scan
    p = sub_p.add_parser("scan", help="Re-scan project + regenerate dual diagrams")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_scan)

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
    p.add_argument("-m", "--mode", choices=["business", "developer"], default="business", help="Diagram mode to open")
    p.set_defaults(func=cmd_project_open)

    # dashboard
    p = sub_p.add_parser("dashboard", help="Open unified project dashboard")
    p.set_defaults(func=cmd_project_dashboard)

    # scan-all
    p = sub_p.add_parser("scan-all", help="Re-scan all registered projects")
    p.set_defaults(func=cmd_project_scan_all)
