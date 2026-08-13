"""CodeMap Scanner — AST-based domain extraction.

Extracts: endpoints, controllers, validation rules, DB relations, business logic.
Outputs structured JSON with full context.
"""

import ast
import os
import re
import json
import hashlib
import bisect
from pathlib import Path
from fnmatch import fnmatch


def _line_of(content, pos):
    """Return 1-based line number for byte position `pos` in `content`.
    O(log n) binary search over precomputed newline offsets — much faster than
    content[:pos].count('\\n') + 1 which is O(n) per call."""
    # Build newline index per unique content id (cheap cache — avoids rebuilding per match)
    offsets = _line_of._cache.get(id(content))
    if offsets is None:
        offsets = [i for i, c in enumerate(content) if c == '\n']
        _line_of._cache[id(content)] = offsets
        _line_of._refs[id(content)] = content  # prevent GC from reusing the id
    return bisect.bisect_left(offsets, pos) + 1


_line_of._cache = {}
_line_of._refs = {}


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
        # NestJS decorators
        (r"@(Get|Post|Put|Patch|Delete|All|Head|Options)\s*\(\s*['\"]?([^'\"]*)['\"]?\)", "nestjs"),
        # Next.js pages
        (r"(?:pages/|app/|router\s*\.\s*(?:get|post))", "nextjs"),
        # Vue Router — path: '/login' inside routes array
        (r"path:\s*['\"]([^'\"]+)['\"]", "vue_router"),
        # React Router — <Route path="/login"
        (r"<Route\s+path=['\"]([^'\"]+)['\"]", "react_router"),
    ],
    "python": [
        # Flask & FastAPI route decorators (captures HTTP method + path)
        (r"@(?:app|router|blueprint)\s*\.\s*(get|post|put|patch|delete|head|options)\s*\(\s*['\"]([^'\"]+)['\"]", "decorator_method"),
        (r"@(?:app|blueprint)\s*\.\s*route\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*methods\s*=\s*\[(.*?)\])?", "flask_route"),
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
    "java": [
        (r"@(Get|Post|Put|Patch|Delete)Mapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]?([^'\"]*)['\"]?", "springboot"),
        (r"@RequestMapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]([^'\"]+)['\"]", "springboot_request_mapping"),
    ],
    "kotlin": [
        (r"@(Get|Post|Put|Patch|Delete)Mapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]?([^'\"]*)['\"]?", "springboot_kt"),
        (r"@RequestMapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]([^'\"]+)['\"]", "springboot_kt_request_mapping"),
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


# ─── Pre-compiled pattern tables (built once at import time) ─────────────────

_JS_VALIDATORS_C = [(re.compile(p, re.IGNORECASE), t) for p, t in JS_VALIDATORS]
_PY_VALIDATORS_C = [(re.compile(p, re.IGNORECASE), t) for p, t in PY_VALIDATORS]
_PHP_VALIDATORS_C = [(re.compile(p, re.IGNORECASE), t) for p, t in PHP_VALIDATORS]

_DB_PATTERNS_C = {
    lang: {
        "table_ref": [(re.compile(p, re.IGNORECASE), t) for p, t in rules["table_ref"]]
    }
    for lang, rules in DB_PATTERNS.items()
}

_ROUTE_PATTERNS_C = {
    lang: [(re.compile(p, re.IGNORECASE), t) for p, t in patterns]
    for lang, patterns in ROUTE_PATTERNS.items()
}

_FORM_PATTERNS_C = [(re.compile(p, re.IGNORECASE), t) for p, t in FORM_PATTERNS]

_GO_ROUTE_C = re.compile(r"(?:HandleFunc|Handle)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
_SERVICE_CALL_C = re.compile(
    r"(?:fetch|axios|request|http|got|node-fetch)\s*\(.*?['\"]([^'\"]+)['\"]",
    re.IGNORECASE
)


# ─── Scanner ─────────────────────────────────────────────────────────────────

class CodeScanner:
    """AST-based source code scanner for corporate applications."""

    def __init__(self, root, languages=None, exclude=None, project_name=None):
        self.root = Path(root).resolve()
        self.project_name = project_name or self.root.name
        self.prefix = re.sub(r"[^a-zA-Z0-9]", "_", self.project_name).strip("_").lower()
        self._node_counter = 0
        self.languages = languages or []
        self.exclude = set(exclude or [])
        self.stats = {"files": 0, "skipped": 0, "errors": 0}

        self.result = {
            "meta": {
                "root": str(self.root),
                "project_name": self.project_name,
                "version": "1.1.0",
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
            "prerequisites": [],
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
        if lang in ("javascript", "typescript", "vue", "svelte"):
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
                elif len(groups) == 1 and groups[0]:
                    # Single-group patterns (Vue Router, React Router, Django)
                    path = groups[0]
                    self.result["endpoints"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:match.start()].count("\n") + 1,
                        "method": "GET",
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
        self._extract_validators(content, rel, lang, _JS_VALIDATORS_C)

        # Services/API calls
        self._extract_services(content, rel, lang)

        # Business logic functions
        self._extract_business_functions(content, rel, lang)

        # Framework specific scans
        self._scan_nextjs_app_router(content, rel)
        self._scan_nestjs(content, rel)

    def _scan_py(self, content, rel):
        """Scan Python: routes, DB, validation, classes."""
        # Routes
        seen_ep_keys = set()
        for pattern, ptype in ROUTE_PATTERNS["python"]:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                line = content[:match.start()].count("\n") + 1
                if ptype == "decorator_method" and len(groups) >= 2:
                    method, path = groups[0].upper(), groups[1]
                    key = (rel, line, path, method)
                    if key not in seen_ep_keys:
                        seen_ep_keys.add(key)
                        self.result["endpoints"].append({
                            "id": self._node_id(),
                            "file": rel,
                            "line": line,
                            "method": method,
                            "path": path,
                            "type": "python",
                        })
                elif ptype == "flask_route" and groups:
                    path = groups[0]
                    raw_methods = groups[1] if len(groups) > 1 and groups[1] else "GET"
                    methods = [m.strip(" '\"").upper() for m in raw_methods.split(",") if m.strip(" '\"")]
                    for method in methods or ["GET"]:
                        key = (rel, line, path, method)
                        if key not in seen_ep_keys:
                            seen_ep_keys.add(key)
                            self.result["endpoints"].append({
                                "id": self._node_id(),
                                "file": rel,
                                "line": line,
                                "method": method,
                                "path": path,
                                "type": "flask",
                            })
                else:
                    path = next((g for g in groups if g), "")
                    if path:
                        key = (rel, line, path, "GET")
                        if key not in seen_ep_keys:
                            seen_ep_keys.add(key)
                            self.result["endpoints"].append({
                                "id": self._node_id(),
                                "file": rel,
                                "line": line,
                                "method": "GET",
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

        # Pydantic & SQLAlchemy
        self._scan_pydantic(content, rel)
        self._scan_sqlalchemy(content, rel)

        # Validators
        self._extract_validators(content, rel, "python", _PY_VALIDATORS_C)

    def _scan_php(self, content, rel):
        """Scan PHP: routes, DB, validation."""
        # Track controllers
        if "Controllers" in rel and "class " in content:
            class_match = re.search(r"class\s+(\w+Controller)", content)
            if class_match:
                ctrl_name = class_match.group(1)
                methods = re.findall(r"public\s+function\s+(\w+)\s*\(", content)
                self.result["controllers"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "name": ctrl_name,
                    "methods": methods,
                })

        # Laravel Route scanning with prefix & apiResource expansion
        if "routes/" in rel or "Route::" in content:
            # Detect active prefix if present
            prefix_match = re.search(r"Route::prefix\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content)
            path_prefix = (prefix_match.group(1).strip('/') + '/') if prefix_match else ""
            
            # 1. Expand apiResource / resource
            for res_match in re.finditer(r"Route::(?:apiResource|resource)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*([^,\)]+)", content):
                res_name = res_match.group(1).strip('/')
                ctrl_raw = res_match.group(2).strip()
                ctrl_name = ctrl_raw.split('\\')[-1].replace('::class', '').strip('\'" ')
                full_base = f"{path_prefix}{res_name}".strip('/')
                
                singular = res_name[:-1] if res_name.endswith('s') and not res_name.endswith('ss') else res_name
                # Standard 5 API Resource routes
                resource_routes = [
                    ("get", full_base, "index"),
                    ("post", full_base, "store"),
                    ("get", f"{full_base}/{{{singular}}}", "show"),
                    ("put", f"{full_base}/{{{singular}}}", "update"),
                    ("delete", f"{full_base}/{{{singular}}}", "destroy"),
                ]
                for m, p, act in resource_routes:
                    self.result["endpoints"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": content[:res_match.start()].count("\n") + 1,
                        "method": m.lower(),
                        "path": p,
                        "controller": ctrl_name,
                        "action": act,
                        "type": "laravel",
                    })

            # 2. Detailed Controller-linked routes [Controller::class, 'method']
            ctrl_route_pattern = r"Route::(get|post|put|patch|delete|options|head|any)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*\[?\s*\\?([\w\\]+)::class\s*,\s*['\"](\w+)['\"]"
            for c_match in re.finditer(ctrl_route_pattern, content):
                method, subpath, ctrl_cls, act = c_match.groups()
                subpath_clean = subpath.strip('/')
                full_path = f"{path_prefix}{subpath_clean}".strip('/') if not subpath_clean.startswith(path_prefix) else subpath_clean
                ctrl_name = ctrl_cls.split('\\')[-1]
                self.result["endpoints"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": content[:c_match.start()].count("\n") + 1,
                    "method": method.lower(),
                    "path": full_path,
                    "controller": ctrl_name,
                    "action": act,
                    "type": "laravel",
                })

        for pattern, ptype in _ROUTE_PATTERNS_C["php"]:
            for match in pattern.finditer(content):
                groups = match.groups()
                if not groups:
                    continue
                method = (groups[0] or "").lower()
                path = groups[1] if len(groups) > 1 else ""
                # Skip if already captured
                if any(e["path"] == path and e["method"] == method for e in self.result["endpoints"]):
                    continue
                if path or method:
                    self.result["endpoints"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": _line_of(content, match.start()),
                        "method": method if method else "ANY",
                        "path": path or method,
                        "type": ptype,
                    })

        for pattern, ptype in _DB_PATTERNS_C["php"]["table_ref"]:
            for match in pattern.finditer(content):
                table = next((g for g in match.groups() if g), "")
                if table:
                    self.result["database"]["queries"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": _line_of(content, match.start()),
                        "table": table,
                        "operation": ptype,
                        "raw": match.group(0)[:100],
                    })

        self._extract_validators(content, rel, "php", _PHP_VALIDATORS_C)
        self._extract_business_functions(content, rel, "php")

        # Filter out seeders & migrations from form validations (to prevent dummy data noise)
        is_seeder_or_migration = any(k in rel.lower() for k in ["seeder", "migration", "database/"])
        if not is_seeder_or_migration:
            for val_match in re.finditer(r"['\"](\w+)['\"]\s*=>\s*['\"]([^'\"]+)['\"]", content):
                field, rule = val_match.groups()
                if any(kw in rule.lower() for kw in ["required", "nullable", "string", "min", "max", "email", "integer", "numeric", "boolean", "array", "date", "in:", "exists", "unique", "sometimes"]):
                    self.result["validations"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": _line_of(content, val_match.start()),
                        "field": field,
                        "rule": rule,
                        "kind": "laravel_validation",
                    })
                    
                    # Detect prerequisite constraint (e.g., exists:certificate_templates,id)
                    fk_match = re.search(r"exists:([a-zA-Z0-9_]+)", rule)
                    if fk_match:
                        ref_table = fk_match.group(1)
                        self.result["prerequisites"].append({
                            "file": rel,
                            "field": field,
                            "prerequisite_table": ref_table,
                        })

    def _scan_cs(self, content, rel):
        for pattern, ptype in _ROUTE_PATTERNS_C["csharp"]:
            for match in pattern.finditer(content):
                groups = match.groups()
                method = (groups[0] or "").lower().replace("http", "")
                path = groups[1] or ""
                self.result["endpoints"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": _line_of(content, match.start()),
                    "method": method,
                    "path": path,
                    "type": ptype,
                })

    def _scan_go(self, content, rel):
        for match in _GO_ROUTE_C.finditer(content):
            self.result["endpoints"].append({
                "id": self._node_id(),
                "file": rel,
                "line": _line_of(content, match.start()),
                "method": "MIXED",
                "path": match.group(1),
                "type": "go",
            })

    def _scan_oo(self, content, rel, lang):
        """Scan OOP languages: extract classes, methods."""
        self._extract_business_functions(content, rel, lang)
        if lang in ("java", "kotlin"):
            self._scan_springboot(content, rel, lang)

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
        """Extract forms/pages and form input fields from content."""
        for pattern, ptype in _FORM_PATTERNS_C:
            for match in pattern.finditer(content):
                groups = match.groups()
                if not groups:
                    continue
                if ptype == "html_form":
                    self.result["forms"].append({
                        "id": self._node_id(),
                        "file": rel,
                        "line": _line_of(content, match.start()),
                        "action": groups[0],
                        "type": "html_form",
                    })
                elif ptype in ("input_field", "textarea_field", "select_field", "vue_model", "react_state"):
                    field = groups[0].replace("form.", "").replace("this.", "")
                    if field:
                        self.result["forms"].append({
                            "id": self._node_id(),
                            "file": rel,
                            "line": _line_of(content, match.start()),
                            "field": field,
                            "type": ptype,
                        })

    def _extract_validators(self, content, rel, lang, patterns):
        """Extract validation rules from code. `patterns` must be pre-compiled (pattern, vtype) tuples."""
        for pattern, vtype in patterns:
            for match in pattern.finditer(content):
                groups = match.groups()
                field = ""
                for g in groups:
                    if g and g not in ("include", "includes", "test", "filter"):
                        field = g
                        break
                self.result["validations"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": _line_of(content, match.start()),
                    "rule": vtype,
                    "field": field,
                    "kind": lang,
                    "raw": match.group(0)[:80],
                })

    def _extract_services(self, content, rel, lang):
        """Extract service/API calls."""
        for match in _SERVICE_CALL_C.finditer(content):
            self.result["services"].append({
                "id": self._node_id(),
                "file": rel,
                "line": _line_of(content, match.start()),
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
        """Detect auth on endpoint. Uses a narrow 100-char window to avoid false positives."""
        ctx = content[max(0, pos - 100):pos + 80]
        if "auth" in ctx.lower() or "token" in ctx.lower() or "jwt" in ctx.lower():
            return "auth_required"
        return "public"

    def _file_id(self, rel):
        return rel.replace("/", "_").replace("\\", "_").replace(".", "_")

    def _node_id(self):
        self._node_counter += 1
        return f"{self.prefix}_n{self._node_counter:04d}"

    def _scan_nextjs_app_router(self, content, rel):
        """Scan Next.js App Router (app/**/route.ts and app/**/page.tsx)."""
        rel_norm = rel.replace("\\", "/")
        if "app/" in rel_norm and (rel_norm.endswith("/route.ts") or rel_norm.endswith("/route.js")):
            parts = rel_norm.split("app/")[-1].split("/")[:-1]
            clean_parts = []
            for p in parts:
                if p.startswith("(") and p.endswith(")"):
                    continue
                p_clean = re.sub(r"^\[\.\.\.(\w+)\]$", r"{\1}", p)
                p_clean = re.sub(r"^\[(\w+)\]$", r"{\1}", p_clean)
                clean_parts.append(p_clean)
            clean_path = "/" + "/".join(clean_parts)

            for m in re.finditer(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)", content):
                method = m.group(1).upper()
                self.result["endpoints"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": content[:m.start()].count("\n") + 1,
                    "method": method,
                    "path": clean_path or "/",
                    "type": "nextjs_app_route",
                    "auth": self._detect_auth(content, m.start()),
                })
        elif "app/" in rel_norm and re.search(r"/page\.(tsx|jsx|ts|js)$", rel_norm):
            parts = rel_norm.split("app/")[-1].split("/")[:-1]
            clean_parts = [re.sub(r"^\[(\w+)\]$", r"{\1}", p) for p in parts if not (p.startswith("(") and p.endswith(")"))]
            clean_path = "/" + "/".join(clean_parts) if clean_parts else "/"
            if "export default" in content:
                self.result["endpoints"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": 1,
                    "method": "GET",
                    "path": clean_path,
                    "type": "nextjs_app_page",
                    "auth": self._detect_auth(content, 0),
                })

    def _scan_nestjs(self, content, rel):
        """Scan NestJS controller and method decorators."""
        if "@Controller" not in content:
            return
        ctrl_match = re.search(r"@Controller\s*\(\s*['\"]?([^'\"]*)['\"]?\s*\)", content)
        base_path = ctrl_match.group(1).strip("/") if ctrl_match else ""

        for m in re.finditer(r"@(Get|Post|Put|Patch|Delete|All)\s*\(\s*['\"]?([^'\"]*)['\"]?\s*\)", content):
            method = m.group(1).upper()
            sub_path = m.group(2).strip("/")
            full_path = "/" + "/".join(p for p in [base_path, sub_path] if p)
            self.result["endpoints"].append({
                "id": self._node_id(),
                "file": rel,
                "line": content[:m.start()].count("\n") + 1,
                "method": method if method != "ALL" else "ANY",
                "path": full_path or "/",
                "type": "nestjs",
                "auth": self._detect_auth(content, m.start()),
            })

    def _scan_springboot(self, content, rel, lang):
        """Scan Spring Boot RestController & RequestMapping annotations."""
        if "@Controller" not in content and "@RestController" not in content:
            return
        base_match = re.search(r"@RequestMapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]([^'\"]+)['\"]", content)
        base_path = base_match.group(1).strip("/") if base_match else ""

        for m in re.finditer(r"@(Get|Post|Put|Patch|Delete)Mapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]?([^'\"]*)['\"]?\s*\)", content):
            method = m.group(1).upper()
            sub_path = m.group(2).strip("/")
            full_path = "/" + "/".join(p for p in [base_path, sub_path] if p)
            self.result["endpoints"].append({
                "id": self._node_id(),
                "file": rel,
                "line": content[:m.start()].count("\n") + 1,
                "method": method,
                "path": full_path or "/",
                "type": f"springboot_{lang}",
                "auth": self._detect_auth(content, m.start()),
            })

    def _scan_pydantic(self, content, rel):
        """Extract Pydantic schema validation models."""
        for class_match in re.finditer(r"class\s+(\w+)\s*\(\s*(?:BaseModel|Schema)\s*\):([\s\S]*?)(?=\nclass\s|\ndef\s|\Z)", content):
            class_name = class_match.group(1)
            body = class_match.group(2)
            for field_match in re.finditer(r"^\s*(\w+)\s*:\s*([\w\[\]\s,|]+)(?:=\s*Field\((.*?)\))?", body, re.MULTILINE):
                field_name = field_match.group(1)
                field_type = field_match.group(2).strip()
                field_kwargs = field_match.group(3) or ""

                rules = [f"type:{field_type}"]
                if "gt=" in field_kwargs or "ge=" in field_kwargs: rules.append("min")
                if "lt=" in field_kwargs or "le=" in field_kwargs: rules.append("max")
                if "min_length=" in field_kwargs: rules.append("minLength")
                if "max_length=" in field_kwargs: rules.append("maxLength")
                if "regex=" in field_kwargs or "pattern=" in field_kwargs: rules.append("pattern")

                self.result["validations"].append({
                    "id": self._node_id(),
                    "file": rel,
                    "line": content[:class_match.start() + field_match.start()].count("\n") + 1,
                    "field": f"{class_name}.{field_name}",
                    "rule": "|".join(rules),
                    "type": "pydantic",
                })

    def _scan_sqlalchemy(self, content, rel):
        """Extract SQLAlchemy ForeignKeys and Relationships."""
        for fk_match in re.finditer(r"ForeignKey\s*\(\s*['\"](\w+)\.(\w+)['\"]", content):
            target_table = fk_match.group(1)
            target_col = fk_match.group(2)
            self.result["database"]["relations"].append({
                "file": rel,
                "line": content[:fk_match.start()].count("\n") + 1,
                "target_table": target_table,
                "target_column": target_col,
                "type": "foreign_key",
            })

        for rel_match in re.finditer(r"relationship\s*\(\s*['\"](\w+)['\"]", content):
            target_model = rel_match.group(1)
            self.result["database"]["relations"].append({
                "file": rel,
                "line": content[:rel_match.start()].count("\n") + 1,
                "target_table": target_model.lower(),
                "type": "relationship",
            })

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
