#!/usr/bin/env python3
"""CodeMap CLI — Corporate AI Agent for source code scanning.

Modes:
  scan    Non-AI: AST-based extraction of endpoints, controllers, validation, DB relations
  ai      AI mode: natural language documentation + architecture overview
  diagram Interactive HTML/SVG diagram with click-to-highlight
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

VERSION = "1.0.0"

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
    # First run scan
    scanner = CodeScanner(
        root=args.source,
        languages=args.languages,
        exclude=args.exclude,
    )
    scan_result = scanner.scan()
    
    # Then generate AI docs
    documenter = AIDocumenter(
        api_url=args.api_url,
        api_key=args.api_key,
        model=args.model,
    )
    
    if args.scan_only:
        # Use existing scan JSON
        with open(args.scan_only) as f:
            scan_result = json.load(f)
    
    docs = documenter.generate(scan_result, context=args.context)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(docs)
        print(f"AI documentation written: {args.output} ({len(docs)} bytes)")
    else:
        print(docs)

def cmd_diagram(args):
    """Generate interactive HTML diagram from scan or graph.json."""
    if args.scan:
        scanner = CodeScanner(
            root=args.source,
            languages=args.languages,
            exclude=args.exclude,
        )
        scan_result = scanner.scan()
    elif args.graph:
        with open(args.graph) as f:
            scan_result = json.load(f)
    else:
        print("Error: --scan or --graph required")
        sys.exit(1)
    
    builder = DiagramBuilder()
    html = builder.build(scan_result, title=args.title or "CodeMap")
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(html)
        print(f"Diagram written: {args.output} ({len(html)} bytes)")
    else:
        print(html)

def cmd_full(args):
    """Full pipeline: scan → AI docs → diagram in one shot."""
    scanner = CodeScanner(
        root=args.source,
        languages=args.languages,
        exclude=args.exclude,
    )
    scan_result = scanner.scan()
    
    base = args.output or "codemap"
    json_path = f"{base}.json"
    md_path = f"{base}.md"
    html_path = f"{base}.html"
    
    # JSON
    with open(json_path, "w") as f:
        json.dump(scan_result, f, indent=2, ensure_ascii=False)
    
    # Markdown (non-AI)
    with open(md_path, "w") as f:
        f.write(scanner.to_markdown(scan_result))
    
    # Diagram
    builder = DiagramBuilder()
    html = builder.build(scan_result, title=args.title or "CodeMap")
    with open(html_path, "w") as f:
        f.write(html)
    
    print(f"JSON: {json_path} ({os.path.getsize(json_path)} bytes)")
    print(f"Markdown: {md_path} ({os.path.getsize(md_path)} bytes)")
    print(f"Diagram: {html_path} ({os.path.getsize(html_path)} bytes)")
    
    # AI docs (optional)
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
        print(f"AI Docs: {ai_path} ({os.path.getsize(ai_path)} bytes)")

def main():
    p = argparse.ArgumentParser(
        prog="codemap",
        description="Corporate AI Agent — Source Code Scanner & Diagram Builder",
    )
    p.add_argument("--version", action="version", version=f"CodeMap v{VERSION}")
    sub = p.add_subparsers(dest="command", required=True)
    
    # scan
    sp = sub.add_parser("scan", help="Non-AI: AST scan → JSON/Markdown")
    sp.add_argument("source", help="Source directory to scan")
    sp.add_argument("-o", "--output", help="Output file path")
    sp.add_argument("-f", "--format", choices=["json", "markdown", "both"], default="json")
    sp.add_argument("-l", "--languages", nargs="*", help="Restrict to languages (js,ts,php,py,cs,go)")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"], help="Exclude dirs")
    sp.set_defaults(func=cmd_scan)
    
    # ai
    sp = sub.add_parser("ai", help="AI mode: natural documentation")
    sp.add_argument("source", help="Source directory to scan")
    sp.add_argument("-o", "--output", help="Output file path")
    sp.add_argument("--scan-only", help="Use existing scan JSON instead of re-scanning")
    sp.add_argument("--api-url", default=os.environ.get("AI_API_URL", ""), help="LLM API endpoint")
    sp.add_argument("--api-key", default=os.environ.get("AI_API_KEY", ""), help="LLM API key")
    sp.add_argument("--model", default=os.environ.get("AI_MODEL", "default"), help="LLM model name")
    sp.add_argument("--context", help="Business context description for AI")
    sp.add_argument("-l", "--languages", nargs="*", help="Restrict to languages")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"])
    sp.set_defaults(func=cmd_ai)
    
    # diagram
    sp = sub.add_parser("diagram", help="Interactive HTML/SVG diagram")
    sp.add_argument("--scan", action="store_true", help="Run fresh scan")
    sp.add_argument("--graph", help="Use existing graph.json or codemap.json")
    sp.add_argument("source", nargs="?", help="Source directory (if --scan)")
    sp.add_argument("-o", "--output", help="Output HTML file")
    sp.add_argument("-t", "--title", help="Diagram title")
    sp.add_argument("-l", "--languages", nargs="*")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"])
    sp.set_defaults(func=cmd_diagram)
    
    # full pipeline
    sp = sub.add_parser("full", help="Full pipeline: scan → md → diagram (+ optional AI)")
    sp.add_argument("source", help="Source directory")
    sp.add_argument("-o", "--output", help="Output base name (no extension)")
    sp.add_argument("-t", "--title", help="Diagram title")
    sp.add_argument("--ai", action="store_true", help="Also generate AI docs")
    sp.add_argument("--api-url", default=os.environ.get("AI_API_URL", ""))
    sp.add_argument("--api-key", default=os.environ.get("AI_API_KEY", ""))
    sp.add_argument("--model", default=os.environ.get("AI_MODEL", "default"))
    sp.add_argument("--context", help="Business context")
    sp.add_argument("-l", "--languages", nargs="*")
    sp.add_argument("-e", "--exclude", nargs="*", default=["node_modules", ".git", "vendor"])
    sp.set_defaults(func=cmd_full)
    
    # project management
    setup_project_subparser(sub)
    
    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()