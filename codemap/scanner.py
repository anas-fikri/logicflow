"""CodeMap Scanner — AST-based domain extraction.

Extracts: endpoints, controllers, validation rules, DB relations, business logic.
Outputs structured JSON with full context.
"""

import ast
import os
import re
import json
import hashlib
from pathlib import Path
from fnmatch import fnmatch


# ─── Language registry ────────────────────────────────────────────────────────

LANG_EXT = {
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".php": "php",
    ".cs": "csharp",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".rs": "rust",
    ".sh": "bash",
    ".sql": "sql",
    ".vue": "vue",
    ".svelte": "svelte",
}


# ─── Validation pattern detectors ────────────────────────────────────────────

# JavaScript validation patterns
JS_VALIDATORS = [
    # Required checks
    (r"\bif\s*\(\s*!\s*(\w+)\s*\)|\bif\s*\(\s*!\s*\[([^\]]+)\].includes", "required"),
    (r"if\s*\(\s*!([\w.\[\]]+)\s*\)", "required"),
    # Length checks
    (r"\.length\s*[<>]=?\s*(\d+)", "length"),
    (r"\.minLength\s*\(\s*(\d+)\s*\)", "minLength"),
    (r"\.maxLength\s*\(\s*(\d+)\s*\)", "maxLength"),
    # Type checks
    (r"typeof\s+(\w+)\s*===?\s*['\"]string['\"]", "type_string"),
    (r"typeof\s+(\w+)\s*===?\s*['\"]number['\"]", "type_number"),
    (r"typeof\s+(\w+)\s*===?\s*['\"]object['\"]", "type_object"),
    (r"Array\.isArray\s*\(\s*(\w+)\s*\)", "type_array"),
    # Email
    (r"email|Email", "format_email"),
    # URL
    (r"url|URL|Uri|uri", "format_url"),
    # Regex
    (r"/([\^$*+?.,;|{}\\[\\]()]+)/", "format_regex"),
    # Min/max
    (r">=\s*(\d+)", "min"),
    (r"<=\s*(\d+)", "max"),
    (r">\s*(\d+)", "minExclusive"),
    (r"<\s*(\d+)", "maxExclusive"),
    # Pattern/regex
    (r"\.test\s*\(\s*([\w.\[\]]+)\s*\)|pattern|regex", "pattern"),
    # Enum/in options
    (r"\.includes\s*\(\s*\[([^\]]+)\]", "enum"),
    # Custom validators
    (r"isValid|validate|check|verify", "custom"),
]

# Python validation patterns
PY_VALIDATORS = [
    (r"if\s+not\s+(\w+)", "required"),
    (r"if\s+(\w+)\s+is\s+None", "required"),
    (r"@validators?\.", "decorator"),
    (r"\.min_value\s*\(\s*(\d+)\s*\)", "min"),
    (r"\.max_value\s*\(\s*(\d+)\s*\)", "max"),
    (r"\.min_length\s*\(\s*(\d+)\s*\)", "minLength"),
    (r"\.max_length\s*\(\s*(\d+)\s*\)", "maxLength"),
    (r"\.regex\s*\(", "pattern"),
    (r"\.email\s*\(", "format_email"),
    (r"\.url\s*\(", "format_url"),
    (r"\.choices\s*\(", "enum"),
    (r"is_valid|validate|check", "custom"),
]

# PHP validation patterns
PHP_VALIDATORS = [
    (r"if\s*\(\s*empty\s*\(\s*\\?\\?\$(\w+)", "required"),
    (r"if\s*\(\s*!\s*\\?\\?\$(\w+)", "required"),
    (r"filter_var\s*\(\s*\\?\\?\$(\w+).*FILTER_VALIDATE", "format"),
    (r"preg_match\s*\(\s*/([^/]+)/", "pattern"),
    (r"in_array\s*\(\s*\\?\\?\$(\w+)", "enum"),
    (r"strlen\s*\(\s*\\?\\?\$(\w+)", "length"),
    (r"count\s*\(\s*\\?\\?\$(\w+)", "length"),
    (r"is_numeric|is_int|is_string|is_array", "type"),
]


# ─── DB pattern detectors ────────────────────────────────────────────────────

DB_PATTERNS = {
    "javascript": {
        "table_ref": [
            (r"from\s+['\"]?(\w+)['\"]?\s*(?:import|require)", "table_alias"),
            (r"FROM\s+([A-Z_][A-Z0-9_]*)", "table"),
            (r"table\s*[:=]\s*['\"]?(\w+)['\"]?", "table_ref"),
            (r"db\.(\w+)\s*\(|knex\.(\w+)\s*\(|prisma\.(\w+)", "orm_method"),
            (r"INSERT\s+INTO\s+([A-Z_][A-Z0-9_]*)", "insert"),
            (r"UPDATE\s+([A-Z_][A-Z0-9_]*)", "update"),
            (r"DELETE\s+FROM\s+([A-Z_][A-Z0-9_]*)", "delete"),
            (r"SELECT\s+.*?\s+FROM\s+([A-Z_][A-Z0-9_]*)", "select"),
        ],
        "query_keywords": [
            "JOIN", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT",
            "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE TABLE",
            "ALTER TABLE", "INDEX", "PRIMARY KEY", "FOREIGN KEY",
        ],
    },
    "python": {
        "table_ref": [
            (r'ORM\.(\w+)\.|Model\.(\w+)\.', "orm"),
            (r"\.objects\.filter\(|\.objects\.all\(|db\.execute\(", "query"),
            (r"CREATE TABLE IF NOT EXISTS\s+([a-z_][a-z0-9_]*)", "create_table"),
            (r"INSERT INTO\s+([a-z_][a-z0-9_]*)", "insert"),
            (r"SELECT\s+.*?\s+FROM\s+([a-z_][a-z0-9_]*)", "select"),
        ],
        "query_keywords": [
            "filter", "annotate", "aggregate", "select_related",
            "prefetch_related", "values", "values_list", "distinct",
        ],
    },
    "php": {
        "table_ref": [
            (r"\$this->db->(\w+)", "ci_query"),
            (r"DB::table\s*\(\s*['\"]?(\w+)['\"]?", "laravel"),
            (r"Schema::create\s*\(\s*['\"]?(\w+)['\"]?", "schema"),
            (r"SELECT.*?FROM\s+[`'\"]?(\w+)[`'\"]?", "select"),
            (r"INSERT INTO\s+[`'\"]?(\w+)[`'\"]?", "insert"),
            (r"UPDATE\s+[`'\"]?(\w+)[`'\"]?", "update"),
            (r"DELETE FROM\s+[`'\"]?(\w+)[`'\"]?", "delete"),
        ],
        "query_keywords": [
            "join", "where", "group_by", "order_by", "having", "limit",
        ],
    },
}


# ─── Route/endpoint detectors ───────────────────────────────────────────────

ROUTE_PATTERNS = {
    "javascript": [
        # Express
        (r"(?:app|router)\s*\.\s*(get|post|put|patch|delete|head|options|any)\s*\(\s*['\"]([^'\"]+)['\"]", "express"),
        (r"(?:app|router)\s*\.\s*(get|post|put|patch|delete)\s*\(\s*`(.*?)`", "express_template"),
        # Next.js
        (r"(?:pages/|app/|router\s*\.\s*(?:get|post))", "nextjs"),
    ],
    "python": [
        # Flask
        (r"@(?:app|blueprint)\s*\.\s*(?:route|get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", "flask"),
        (r"@(?:app|blueprint)\s*\.\s*route\s*\(\s*`(.*?)`", "flask_template"),
        # FastAPI
        (r"@(?:app|router)\s*\.\s*(?:get|post|put|patch|delete|head|options)\s*\(\s*['\"]([^'\"]+)['\"]", "fastapi"),
        # Django
        (r"path\s*\(\s*['\"]([^'\"]+)['\"]", "django"),
        (r"re_path\s*\(\s*['\"]([^'\"]+)['\"]", "django_re"),
    ],
    "php": [
        (r"Route::(get|post|put|patch|delete|any|resource)\s*\(\s*['\"]([^'\"]+)['\"]", "laravel"),
        (r"\$route\s*=\s*['\"]([^'\"]+)['\"]", "generic_route"),
        (r"function\s+(?:index|show|create|store|edit|update|destroy|delete|process)", "rest_method"),
    ],
    "csharp": [
        (r"\[Http(Get|Post|Put|Patch|Delete|Route)\s*\(\s*['\"]([^'\"]+)['\"]", "aspnet"),
        (r"\[Route\s*\(\s*['\"]([^'\"]+)['\"]", "aspnet_route"),
    ],
}


# ─── Form/page detectors ─────────────────────────────────────────────────────

FORM_PATTERNS = [
    # HTML form
    (r"<form[^>]*action=['\"]([^'\"]+)['\"][^>]*>", "html_form"),
    (r"<input[^>]*name=['\"]([^'\"]+)['\"][^>]*type=['\"]([^'\"]+)['\"]", "input_field"),
    (r"<textarea[^>]*name=['\"]([^'\"]+)['\"]", "textarea_field"),
    (r"<select[^>]*name=['\"]([^'\"]+)['\"]", "select_field"),
    # Vue/React form
    (r"v-model=['\"]([^'\"]+)['\"]", "vue_model"),
    (r"useState\s*\(\s*['\"]([^'\"]+)['\"]", "react_state"),
    (r"onSubmit|onChange|onClick|onBlur", "event_handler"),
]


# ─── Scanner ─────────────────────────────────────────────────────────────────

class CodeScanner:
    """AST-based source code scanner for corporate applications."""

    def __init__(self, root, languages=None, exclude=None):
        self.root = Path(root).resolve()
        self.languages = languages or []
        self.exclude = set(exclude or [])
        self.stats = {"files": 0, "skipped": 0, "errors": 0}

        self.result = {
            "meta": {
                "root": str(self.root),
                "version": "1.0.0",
                "languages": [],
            },
            "endpoints": [],
            "controllers": [],
            "validations": [],
            "database": {
                "tables": {},
                "queries": [],
                "relations": [],
            },
            "forms": [],
            "business_logic": [],
            "services": [],
            "files": [],
            "summary": {},
        }

    def scan(self):
        """Walk source tree and extract domain data."""
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirpath = Path(dirpath)

            # Filter excluded dirs
            dirnames[:] = [
                d for d in dirnames
                if d not in self.exclude and not d.startswith(".")
            ]

            for filename in filenames:
                filepath = dirpath / filename
                ext = filepath.suffix.lower()

                if ext not in LANG_EXT:
                    continue
                lang = LANG_EXT[ext]

                if self.languages and lang not in self.languages:
                    continue

                self._scan_file(filepath, lang)

        self._build_summary()
        return self.result

    def _scan_file(self, filepath, lang):
        """Scan single file with language-specific parser."""
        self.stats["files"] += 1
        rel = str(filepath.relative_to(self.root))

        try:
            content = filepath.read_text(errors="ignore")
        except Exception:
            self.stats["skipped"] += 1
            return

        # Extract forms/pages first (plain text scan)
        self._extract_forms(content, rel, lang)

        # Language-specific extraction
        if lang in ("javascript", "typescript"):
            self._scan_js(content, rel, lang)
        elif lang == "python":
            self._scan_py(content, rel)
        elif lang == "php":
            self._scan_php(content, rel)
        elif lang == "csharp":
            self._scan_cs(content, rel)
        elif lang == "go":
            self._scan_go(content, rel)
        elif lang in ("java", "swift", "kotlin", "rust"):
            self._scan_oo(content, rel, lang)
        elif lang == "sql":
            self._scan_sql(content, rel)

        # Record file
        self.result["files"].append({
            "path": rel,
            "lang": lang,
            "size": len(content),
            "lines": content.count("\n") + 1,
            "sha": hashlib.md5(content.encode()).hexdigest()[:8],
        })

        if lang not in self.result["meta"]["languages"]:
            self.result["meta"]["languages"].append(lang)

    def _scan_js(self, content, rel, lang):
        """Scan JS/TS: routes, imports, DB calls, validation."""
        file_id = self._file_id(rel)

        # Routes via text scan
        for pattern, ptype in ROUTE_PATTERNS["javascript"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                if len(groups) >= 2 and groups[0] and groups[1]:
                    method = groups[0].lower()
                    path = groups[1]
                    self.result["endpoints"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "method": method if method not in ("any", "") else "MIXED",
                        "path": path,
                        "type": ptype,
                        "auth": self._detect_auth(content, match.start()),
                    })

        # DB patterns
        for pattern, ptype in DB_PATTERNS["javascript"]["table_ref"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                query_text = match.group(0)
                table = next((g for g in match.groups() if g), "")
                if table:
                    self.result["database"]["queries"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "table": table,
                        "operation": ptype,
                        "raw": query_text[:100],
                    })

        # Validators
        self._extract_validators(content, rel, lang, JS_VALIDATORS)

        # Services/API calls
        self._extract_services(content, rel, lang)

        # Business logic functions
        self._extract_business_functions(content, rel, lang)

        # Import analysis for relations
        self._extract_imports(content, rel)

    def _scan_py(self, content, rel):
        """Scan Python: routes, DB, validation, classes."""
        # Routes
        for pattern, ptype in ROUTE_PATTERNS["python"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                path = next((g for g in groups if g), "")
                if path:
                    self.result["endpoints"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "method": ptype.upper() if hasattr(ptype, "upper") else "GET",
                        "path": path,
                        "type": ptype,
                    })

        # DB queries
        for pattern, ptype in DB_PATTERNS["python"]["table_ref"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                table = next((g for g in match.groups() if g), "")
                if table:
                    self.result["database"]["queries"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "table": table,
                        "operation": ptype,
                        "raw": match.group(0)[:100],
                    })

        # AST-based Python extraction (functions, classes)
        self._extract_py_ast(content, rel)

        # Validators
        self._extract_validators(content, rel, "python", PY_VALIDATORS)

    def _scan_php(self, content, rel):
        """Scan PHP: routes, DB, validation."""
        for pattern, ptype in ROUTE_PATTERNS["php"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                if not groups:
                    continue
                method = (groups[0] or "").lower()
                path = groups[1] if len(groups) > 1 else ""
                if path or method:
                    self.result["endpoints"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "method": method if method else "ANY",
                        "path": path or method,
                        "type": ptype,
                    })

        for pattern, ptype in DB_PATTERNS["php"]["table_ref"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                table = next((g for g in match.groups() if g), "")
                if table:
                    self.result["database"]["queries"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "table": table,
                        "operation": ptype,
                        "raw": match.group(0)[:100],
                    })

        self._extract_validators(content, rel, "php", PHP_VALIDATORS)
        self._extract_business_functions(content, rel, "php")

    def _scan_cs(self, content, rel):
        for pattern, ptype in ROUTE_PATTERNS["csharp"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                method = (groups[0] or "").lower().replace("http", "")
                path = groups[1] or ""
                self.result["endpoints"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": content[:match.start()].count("\n") + 1,
                    "method": method,
                    "path": path,
                    "type": ptype,
                })

    def _scan_go(self, content, rel):
        for match in re.finditer(r"(?:HandleFunc|Handle)\s*\(\s*['\"]([^'\"]+)['\"]", content):
            self.result["endpoints"].append({
                "id": self._node_id(),
                "file": rel,
                "line": content[:match.start()].count("\n") + 1,
                "method": "MIXED",
                "path": match.group(1),
                "type": "go",
            })

    def _scan_oo(self, content, rel, lang):
        """Scan OOP languages: extract classes, methods."""
        self._extract_business_functions(content, rel, lang)

    def _scan_sql(self, content, rel):
        """Scan SQL: tables, columns, relations."""
        for match in re.finditer(
            r"CREATE TABLE IF NOT EXISTS\s+[`\"]?(\w+)[`\"]?\s*\(([\s\S]*?)\)(?:ENGINE|DEFAULT|CHARSET|\)|;|$)",
            content, re.IGNORECASE
        ):
            table_name = match.group(1)
            columns_raw = match.group(2)
            self._parse_sql_table(table_name, columns_raw, rel, content, match.start())

        # Standalone column defs
        for match in re.finditer(
            r"(?:PRIMARY KEY|FOREIGN KEY|UNIQUE|INDEX|KEY)\s*\([`\"]?(\w+)[`\"]?\)",
            content, re.IGNORECASE
        ):
            pass  # FK tracking

    def _parse_sql_table(self, table, columns_raw, rel, content, start):
        cols = []
        for col_match in re.finditer(
            r"[`\"]?(\w+)[`\"]?\s+(\w+(?:\(\d+(?:,\s*\d+)?\))?)(?:\s+(NOT NULL|NULL|DEFAULT|AUTO_INCREMENT|SERIAL|PRIMARY KEY|UNIQUE|KEY))*(?:\s+COMMENT\s+['\"]([^'\"]+)['\"])?",
            columns_raw, re.IGNORECASE
        ):
            col_name = col_match.group(1)
            col_type = col_match.group(2)
            col_flags = " ".join([g for g in col_match.groups()[2:] if g]).upper()
            cols.append({"name": col_name, "type": col_type, "flags": col_flags})

        self.result["database"]["tables"][table] = {
            "id": self._node_id(),
            "file": rel,
            "line": content[:start].count("\n") + 1,
            "columns": cols,
        }

        # FK detection
        for fk_match in re.finditer(
            r"FOREIGN KEY\s*\([`\"]?(\w+)[`\"]?\)\s+REFERENCES\s+[`\"]?(\w+)[`\"]?\s*\([`\"]?(\w+)[`\"]?\)",
            columns_raw, re.IGNORECASE
        ):
            self.result["database"]["relations"].append({
                "id": self._node_id(),
                "from_table": table,
                "from_column": fk_match.group(1),
                "to_table": fk_match.group(2),
                "to_column": fk_match.group(3),
                "type": "FK",
                "file": rel,
            })

    def _extract_forms(self, content, rel, lang):
        """Extract forms/pages from content."""
        for pattern, ptype in FORM_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                if ptype == "html_form":
                    self.result["forms"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "action": groups[0],
                        "type": "html_form",
                    })
                elif ptype == "input_field":
                    self.result["validations"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "field": groups[0],
                        "type": groups[1],
                        "kind": "html_input",
                    })

    def _extract_validators(self, content, rel, lang, patterns):
        """Extract validation rules from code."""
        for pattern, vtype in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                field = ""
                for g in groups:
                    if g and g not in ("include", "includes", "test", "filter"):
                        field = g
                        break
                self.result["validations"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": content[:match.start()].count("\n") + 1,
                    "rule": vtype,
                    "field": field,
                    "kind": lang,
                    "raw": match.group(0)[:80],
                })

    def _extract_services(self, content, rel, lang):
        """Extract service/API calls."""
        for match in re.finditer(
            r"(?:fetch|axios|request|http|got|node-fetch)\s*\(.*?['\"]([^'\"]+)['\"]",
            content, re.IGNORECASE
        ):
            self.result["services"].append({
                "id": self._node_id(),
                "file": rel,
                "line": content[:match.start()].count("\n") + 1,
                "url": match.group(1),
                "type": "http_call",
            })

    def _extract_business_functions(self, content, rel, lang):
        """Extract business logic functions."""
        func_pattern = r"function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:function|\([^)]*\)\s*=>|\w+\s*=>)"
        for match in re.finditer(func_pattern, content):
            name = match.group(1) or match.group(2)
            if not name:
                continue
            # Check if it looks like business logic
            ctx_start = max(0, match.start() - 200)
            ctx = content[ctx_start:match.start()]
            if any(kw in ctx.lower() for kw in ["process", "handle", "manage", "create", "update", "delete", "calculate", "validate"]):
                self.result["business_logic"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": content[:match.start()].count("\n") + 1,
                    "name": name,
                    "kind": lang,
                    "type": "function",
                })

    def _extract_imports(self, content, rel):
        """Track imports for dependency graph."""
        for match in re.finditer(
            r"(?:import|require|require\s*\()\s*['\"]([^'\"]+)['\"]",
            content
        ):
            pass  # Could be used for cross-file relations

    def _extract_py_ast(self, content, rel):
        """AST-based Python extraction for classes/functions."""
        try:
            tree = ast.parse(content)
        except Exception:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.result["business_logic"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": node.lineno,
                    "name": node.name,
                    "kind": "python",
                    "type": "class_method" if node.name[0].isupper() else "function",
                    "decorators": [ast.unparse(d) for d in node.decorator_list if hasattr(ast, "unparse")],
                })
            elif isinstance(node, ast.ClassDef):
                self.result["business_logic"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": node.lineno,
                    "name": node.name,
                    "kind": "python",
                    "type": "class",
                })

    def _detect_auth(self, content, pos):
        """Detect auth on endpoint."""
        ctx = content[max(0, pos - 300):pos + 100]
        if "auth" in ctx.lower() or "token" in ctx.lower() or "jwt" in ctx.lower():
            return "auth_required"
        return "public"

    def _file_id(self, rel):
        return rel.replace("/", "_").replace("\\", "_").replace(".", "_")

    _node_counter = 0

    def _node_id(self):
        CodeScanner._node_counter += 1
        return f"n{CodeScanner._node_counter:04d}"

    def _build_summary(self):
        s = self.result["summary"]
        s["total_files"] = self.stats["files"]
        s["total_endpoints"] = len(self.result["endpoints"])
        s["total_validations"] = len(self.result["validations"])
        s["total_tables"] = len(self.result["database"]["tables"])
        s["total_queries"] = len(self.result["database"]["queries"])
        s["total_relations"] = len(self.result["database"]["relations"])
        s["total_forms"] = len(self.result["forms"])
        s["total_business_logic"] = len(self.result["business_logic"])
        s["languages"] = self.result["meta"]["languages"]

        # Endpoint method breakdown
        methods = {}
        for ep in self.result["endpoints"]:
            m = ep.get("method", "MIXED").upper()
            methods[m] = methods.get(m, 0) + 1
        s["endpoints_by_method"] = methods

    # ─── Markdown export ──────────────────────────────────────────────────────

    def to_markdown(self, result):
        """Convert scan result to readable Markdown."""
        lines = [f"# CodeMap Report — {self.root.name}\n"]
        lines.append(f"**Languages:** {', '.join(result['meta']['languages'])}\n")
        lines.append(f"**Files scanned:** {result['summary']['total_files']}\n")

        # Endpoints
        if result["endpoints"]:
            lines.append("\n## API Endpoints\n")
            lines.append("| Method | Path | File | Line | Auth |")
            lines.append("|--------|------|------|------|------|")
            for ep in result["endpoints"]:
                lines.append(
                    f"| {ep.get('method','MIXED')} | `{ep['path']}` | "
                    f"{ep['file'].split('/')[-1]} | {ep['line']} | "
                    f"{ep.get('auth','?')} |"
                )

        # Database
        if result["database"]["tables"]:
            lines.append("\n## Database Schema\n")
            for tbl, info in result["database"]["tables"].items():
                lines.append(f"### `{tbl}`\n")
                lines.append("| Column | Type | Flags |")
                lines.append("|--------|------|-------|")
                for col in info.get("columns", []):
                    lines.append(
                        f"| `{col['name']}` | {col['type']} | "
                        f"{col.get('flags','') or '—'} |"
                    )
                lines.append("")

        # Validations
        if result["validations"]:
            lines.append("\n## Validation Rules\n")
            seen = {}
            for v in result["validations"]:
                k = (v.get("field") or v.get("rule"), v["file"])
                if k not in seen:
                    seen[k] = v
            for v in list(seen.values())[:50]:
                field = v.get("field") or v.get("rule", "unknown")
                lines.append(
                    f"- `{field}` [{v['kind']}] — "
                    f"{v.get('rule','?')} @ {v['file'].split('/')[-1]}:{v['line']}"
                )

        # Business Logic
        if result["business_logic"]:
            lines.append("\n## Business Logic\n")
            seen_funcs = {}
            for f in result["business_logic"]:
                if f["name"] not in seen_funcs:
                    seen_funcs[f["name"]] = f
                    lines.append(
                        f"- `{f['name']}` [{f['type']}] @ "
                        f"{f['file'].split('/')[-1]}:{f['line']}"
                    )

        # Forms
        if result["forms"]:
            lines.append("\n## Forms / Pages\n")
            for form in result["forms"]:
                lines.append(
                    f"- {form['type']} → `{form.get('action','?')}` "
                    f"@ {form['file'].split('/')[-1]}:{form['line']}"
                )

        lines.append(f"\n---\n*Generated by CodeMap v1.0.0*")
        return "\n".join(lines)
