#!/usr/bin/env python3
"""CodeMap Project Manager — registry for managing multiple project scans & diagrams.

Stores project metadata in ~/.codemap/projects.json
Each project tracks: source path, scan JSON, diagram HTML, last scan date, stats.

Usage:
  codemap project add <name> <source-path> [--title TITLE]
  codemap project list
  codemap project scan <name>           # re-scan + regenerate diagram
  codemap project diagram <name>        # regenerate diagram from existing scan
  codemap project info <name>           # show project details
  codemap project remove <name>
  codemap project open <name>           # open diagram in browser
  codemap project scan-all              # re-scan all projects
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

REGISTRY_DIR = Path.home() / ".codemap"
REGISTRY_FILE = REGISTRY_DIR / "projects.json"
OUTPUT_DIR = REGISTRY_DIR / "output"


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
        "diagram_file": None,
        "last_scan": None,
        "stats": None,
        "created": datetime.now().isoformat(),
        "exclude": args.exclude or ["node_modules", ".git", "vendor", "dist"],
    }
    _save_registry(reg)
    print(f"Project '{name}' added.")
    print(f"  Source: {source}")
    print(f"  Title:  {title}")
    print(f"  Run 'codemap project scan {name}' to generate scan + diagram.")


def cmd_project_list(args):
    """List all registered projects."""
    reg = _load_registry()
    projects = reg["projects"]
    if not projects:
        print("No projects registered. Use 'codemap project add <name> <path>' to add one.")
        return

    print(f"{'Name':<20} {'Title':<25} {'Menus':>5} {'APIs':>5} {'Nodes':>6} {'Last Scan':<20}")
    print("-" * 85)
    for name, p in sorted(projects.items()):
        stats = p.get("stats") or {}
        last = p.get("last_scan", "—")
        if last and last != "—":
            last = last[:19].replace("T", " ")
        menus = stats.get("menus", "—")
        apis = stats.get("apis", "—")
        nodes = stats.get("nodes", "—")
        print(f"{name:<20} {p.get('title','—'):<25} {str(menus):>5} {str(apis):>5} {str(nodes):>6} {last:<20}")


def cmd_project_scan(args):
    """Re-scan project source and regenerate diagram."""
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
    diagram_file = str(d / "diagram.html")

    # Import scanner + diagram builder
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from codemap.scanner import CodeScanner
    from codemap.diagram import DiagramBuilder

    print(f"Scanning {source} ...")
    scanner = CodeScanner(root=source, exclude=exclude)
    result = scanner.scan()

    with open(scan_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  Scan: {scan_file} ({os.path.getsize(scan_file)} bytes)")

    builder = DiagramBuilder()
    html = builder.build(result, title=p.get("title", name))
    with open(diagram_file, "w") as f:
        f.write(html)
    print(f"  Diagram: {diagram_file} ({os.path.getsize(diagram_file)} bytes)")

    # Update stats
    eps = result.get("endpoints", [])
    menus = set()
    for ep in eps:
        path = ep.get("path", "")
        parts = [x for x in path.split("/") if x and x not in ("api", "v1", "v2")]
        if parts:
            menus.add(parts[0])

    reg["projects"][name]["scan_file"] = scan_file
    reg["projects"][name]["diagram_file"] = diagram_file
    reg["projects"][name]["last_scan"] = datetime.now().isoformat()
    reg["projects"][name]["stats"] = {
        "endpoints": len(eps),
        "menus": len(menus),
        "apis": len(eps),
        "nodes": len(result.get("nodes", [])) if "nodes" in result else (
            len(eps) + len(result.get("business_logic", [])) +
            len(result.get("validations", [])) + len(result.get("forms", [])) + 1
        ),
        "validations": len(result.get("validations", [])),
        "bizlogic": len(result.get("business_logic", [])),
        "languages": list(set(ep.get("language", "") for ep in eps)) if eps else [],
    }
    _save_registry(reg)

    s = reg["projects"][name]["stats"]
    print(f"  Stats: {s['nodes']} nodes, {s['menus']} menus, {s['apis']} APIs, {s['validations']} validations")


def cmd_project_diagram(args):
    """Regenerate diagram from existing scan (no re-scan)."""
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
    diagram_file = str(d / "diagram.html")
    builder = DiagramBuilder()
    html = builder.build(result, title=p.get("title", name))
    with open(diagram_file, "w") as f:
        f.write(html)

    reg["projects"][name]["diagram_file"] = diagram_file
    _save_registry(reg)
    print(f"Diagram regenerated: {diagram_file} ({os.path.getsize(diagram_file)} bytes)")


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
    print(f"  Diagram:     {p.get('diagram_file', '—')}")
    print(f"  Last scan:   {p.get('last_scan', '—')}")
    print(f"  Created:     {p.get('created', '—')}")
    stats = p.get("stats")
    if stats:
        print(f"  Stats:")
        print(f"    Nodes:       {stats.get('nodes', '—')}")
        print(f"    Menus:       {stats.get('menus', '—')}")
        print(f"    APIs:        {stats.get('apis', '—')}")
        print(f"    Validations: {stats.get('validations', '—')}")
        print(f"    Biz logic:   {stats.get('bizlogic', '—')}")
        print(f"    Languages:   {', '.join(stats.get('languages', [])) or '—'}")


def cmd_project_remove(args):
    """Remove a project from registry (and optionally its files)."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    p = reg["projects"][name]
    del reg["projects"][name]
    _save_registry(reg)

    # Optionally delete files
    if args.purge:
        d = _project_dir(name)
        if d.exists():
            import shutil
            shutil.rmtree(d)
            print(f"Project '{name}' removed + files purged.")
        else:
            print(f"Project '{name}' removed.")
    else:
        print(f"Project '{name}' removed from registry. Files kept at {OUTPUT_DIR / name}")


def cmd_project_open(args):
    """Open diagram in default browser."""
    reg = _load_registry()
    name = args.name
    if name not in reg["projects"]:
        print(f"Error: project '{name}' not found.")
        sys.exit(1)

    diagram_file = reg["projects"][name].get("diagram_file")
    if not diagram_file or not os.path.isfile(diagram_file):
        print(f"Error: no diagram for project '{name}'. Run 'codemap project scan {name}' first.")
        sys.exit(1)

    # Convert to file:// URL
    url = f"file://{os.path.abspath(diagram_file)}"
    print(f"Opening: {url}")
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
            # Create a dummy args object
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
    sp = sub.add_parser("project", help="Manage multiple projects (registry)")
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
    p = sub_p.add_parser("scan", help="Re-scan project + regenerate diagram")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_scan)

    # diagram
    p = sub_p.add_parser("diagram", help="Regenerate diagram from existing scan")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_diagram)

    # info
    p = sub_p.add_parser("info", help="Show project details")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_info)

    # remove
    p = sub_p.add_parser("remove", help="Remove project from registry")
    p.add_argument("name", help="Project name")
    p.add_argument("--purge", action="store_true", help="Also delete scan + diagram files")
    p.set_defaults(func=cmd_project_remove)

    # open
    p = sub_p.add_parser("open", help="Open diagram in browser")
    p.add_argument("name", help="Project name")
    p.set_defaults(func=cmd_project_open)

    # scan-all
    p = sub_p.add_parser("scan-all", help="Re-scan all registered projects")
    p.set_defaults(func=cmd_project_scan_all)