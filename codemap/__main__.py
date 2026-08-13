#!/usr/bin/env python3
"""CodeMap CLI — Corporate source code scanner & interactive diagram builder.

Modes:
  scan       Extract endpoints, controllers, validation, DB relations (no AI)
  ai         Generate natural language documentation (optional LLM)
  diagram    Generate interactive HTML diagram (business or developer mode)
  full       Full pipeline: scan → diagram (both modes) → optional AI docs
  project    Manage project registry & dashboard
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codemap.scanner import CodeScanner
from codemap.ai import AIDocumenter
from codemap.diagram import DiagramBuilder
from codemap.project import setup_project_subparser

VERSION = "1.1.0"


def cmd_scan(args):
    """Non-AI mode: extract structured data from source code."""
    scanner = CodeScanner(
        root=args.source,
        languages=args.languages,
        exclude=args.exclude,
    )
    result = scanner.scan()

    if args.format == "json":
        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"JSON written: {args.output} ({len(output)} bytes)")
        else:
            print(output)
    elif args.format == "markdown":
        md = scanner.to_markdown(result)
        if args.output:
            with open(args.output, "w") as f:
                f.write(md)
            print(f"Markdown written: {args.output} ({len(md)} bytes)")
        else:
            print(md)
    elif args.format == "both":
        json_path = args.output or "codemap.json"
        md_path = args.output.replace(".json", ".md") if args.output else "codemap.md"
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        with open(md_path, "w") as f:
            f.write(scanner.to_markdown(result))
        print(f"JSON: {json_path} | Markdown: {md_path}")


def cmd_ai(args):
    """AI mode: generate natural documentation from scan data."""
    if args.scan_only:
        with open(args.scan_only) as f:
            scan_result = json.load(f)
    else:
        scanner = CodeScanner(
            root=args.source,
            languages=args.languages,
            exclude=args.exclude,
        )
        scan_result = scanner.scan()

    documenter = AIDocumenter(
        api_url=args.api_url,
        api_key=args.api_key,
        model=args.model,
    )
    docs = documenter.generate(scan_result, context=args.context)

    if args.output:
        with open(args.output, "w") as f:
            f.write(docs)
        print(f"AI documentation written: {args.output} ({len(docs)} bytes)")
    else:
        print(docs)


def cmd_diagram(args):
    """Generate interactive HTML diagram from scan JSON or source directory."""
    if args.scan:
        if not args.source:
            print("Error: source directory required with --scan")
            sys.exit(1)
        scanner = CodeScanner(
            root=args.source,
            languages=args.languages,
            exclude=args.exclude,
        )
        scan_result = scanner.scan()
    elif args.graph:
        with open(args.graph) as f:
            scan_result = json.load(f)
    elif args.source:
        scanner = CodeScanner(
            root=args.source,
            languages=args.languages,
            exclude=args.exclude,
        )
        scan_result = scanner.scan()
    else:
        print("Error: provide source directory or --graph file")
        sys.exit(1)

    builder = DiagramBuilder()
    title = args.title or "CodeMap"

    if args.mode == "both":
        biz_html, dev_html = builder.build_both(scan_result, title=title)
        out_base = args.output or "codemap"
        biz_path = f"{out_base}-business.html"
        dev_path = f"{out_base}-developer.html"
        with open(biz_path, "w") as f:
            f.write(biz_html)
        with open(dev_path, "w") as f:
            f.write(dev_html)
        print(f"Business Diagram:  {biz_path} ({len(biz_html)} bytes)")
        print(f"Developer Diagram: {dev_path} ({len(dev_html)} bytes)")
    else:
        html = builder.build(scan_result, title=title, mode=args.mode)
        out_path = args.output or f"codemap-{args.mode}.html"
        with open(out_path, "w") as f:
            f.write(html)
        print(f"{args.mode.title()} Diagram: {out_path} ({len(html)} bytes)")


def cmd_full(args):
    """Full pipeline: scan → dual diagrams → optional AI docs."""
    scanner = CodeScanner(
        root=args.source,
        languages=args.languages,
        exclude=args.exclude,
    )
    scan_result = scanner.scan()

    base = args.output or "codemap"
    json_path = f"{base}.json"
    biz_path = f"{base}-business.html"
    dev_path = f"{base}-developer.html"

    # Save JSON
    with open(json_path, "w") as f:
        json.dump(scan_result, f, indent=2, ensure_ascii=False)

    # Save dual diagrams
    builder = DiagramBuilder()
    biz_html, dev_html = builder.build_both(scan_result, title=args.title or "CodeMap")
    with open(biz_path, "w") as f:
        f.write(biz_html)
    with open(dev_path, "w") as f:
        f.write(dev_html)

    print(f"JSON:      {json_path} ({os.path.getsize(json_path)} bytes)")
    print(f"Business:  {biz_path} ({len(biz_html)} bytes)")
    print(f"Developer: {dev_path} ({len(dev_html)} bytes)")

    # Optional AI docs
    if args.ai:
        documenter = AIDocumenter(
            api_url=args.api_url,
            api_key=args.api_key,
            model=args.model,
        )
        ai_path = f"{base}-ai.md"
        docs = documenter.generate(scan_result, context=args.context)
        with open(ai_path, "w") as f:
            f.write(docs)
        print(f"AI Docs:   {ai_path} ({len(docs)} bytes)")


def main():
    p = argparse.ArgumentParser(
        prog="codemap",
        description="CodeMap — Source Code Scanner & Dual-Mode Diagram Builder",
    )
    p.add_argument("--version", action="version", version=f"CodeMap v{VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    # scan
    sp = sub.add_parser("scan", help="Non-AI: AST scan → JSON/Markdown")
    sp.add_argument("source", help="Source directory to scan")
    sp.add_argument("-o", "--output", help="Output file path")
    sp.add_argument("-f", "--format", choices=["json", "markdown", "both"], default="json")
    sp.add_argument("-l", "--languages", nargs="*", help="Restrict languages")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"])
    sp.set_defaults(func=cmd_scan)

    # ai
    sp = sub.add_parser("ai", help="AI mode: natural language documentation")
    sp.add_argument("source", nargs="?", help="Source directory to scan")
    sp.add_argument("-o", "--output", help="Output file path")
    sp.add_argument("--scan-only", help="Use existing scan JSON instead of re-scanning")
    sp.add_argument("--api-url", default=os.environ.get("AI_API_URL", ""))
    sp.add_argument("--api-key", default=os.environ.get("AI_API_KEY", ""))
    sp.add_argument("--model", default=os.environ.get("AI_MODEL", "default"))
    sp.add_argument("--context", help="Business context description")
    sp.add_argument("-l", "--languages", nargs="*")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"])
    sp.set_defaults(func=cmd_ai)

    # diagram
    sp = sub.add_parser("diagram", help="Interactive dual-mode HTML diagram")
    sp.add_argument("source", nargs="?", help="Source directory")
    sp.add_argument("--scan", action="store_true", help="Run fresh scan")
    sp.add_argument("--graph", help="Use existing scan JSON")
    sp.add_argument("-m", "--mode", choices=["business", "developer", "both"], default="both", help="Diagram mode")
    sp.add_argument("-o", "--output", help="Output HTML file base name")
    sp.add_argument("-t", "--title", help="Diagram title")
    sp.add_argument("-l", "--languages", nargs="*")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"])
    sp.set_defaults(func=cmd_diagram)

    # full
    sp = sub.add_parser("full", help="Full pipeline: scan → dual diagrams (+ optional AI)")
    sp.add_argument("source", help="Source directory")
    sp.add_argument("-o", "--output", help="Output base name")
    sp.add_argument("-t", "--title", help="Diagram title")
    sp.add_argument("--ai", action="store_true", help="Also generate AI docs")
    sp.add_argument("--api-url", default=os.environ.get("AI_API_URL", ""))
    sp.add_argument("--api-key", default=os.environ.get("AI_API_KEY", ""))
    sp.add_argument("--model", default=os.environ.get("AI_MODEL", "default"))
    sp.add_argument("--context", help="Business context")
    sp.add_argument("-l", "--languages", nargs="*")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"])
    sp.set_defaults(func=cmd_full)

    # project management & dashboard
    setup_project_subparser(sub)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
