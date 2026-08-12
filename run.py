#!/usr/bin/env python3
"""
apps-diagram CLI — wrapper for render.py
Usage:
  python3 run.py graph.json "My App"
  python3 run.py graph.json --title "My App" --output my-app.html
"""
import sys
import subprocess
from pathlib import Path

script_dir = Path(__file__).parent
render_py = script_dir / "render.py"
graphify_dir = Path.home() / "graphify"

if len(sys.argv) < 2:
    print("Usage: python3 run.py <graph.json> [title] [options]")
    print("  or:   python3 render.py <graph.json> [options]")
    sys.exit(1)

graph_path = sys.argv[1]
title = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
rest = sys.argv[2:] if len(sys.argv) <= 2 else sys.argv[2:]

cmd = [
    sys.executable, str(render_py),
    graph_path,
]
if title:
    cmd.extend(["--title", title])
cmd.extend(rest)

env = {**subprocess.os.environ}
env["PYTHONPATH"] = str(graphify_dir)
result = subprocess.run(cmd, env=env)
sys.exit(result.returncode)
