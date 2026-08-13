#!/usr/bin/env python3
"""LogicFlow Remote — clone / sync GitHub & GitLab repos untuk scanning."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# ── Constants ────────────────────────────────────────────────────────────────

REPOS_DIR = Path.home() / ".logicflow" / "repos"

_GITHUB_TREE = re.compile(
    r"https?://github\.com/([^/]+/[^/]+)/tree/([^/]+)(?:/(.+))?"
)
_GITLAB_TREE = re.compile(
    r"https?://gitlab\.com/([^/]+(?:/[^/]+)+)/-/tree/([^/]+)(?:/(.+))?"
)

# ── URL normalization ─────────────────────────────────────────────────────────


def parse_remote_url(url: str) -> dict:
    """Return dict with keys: clone_url, platform, branch, subdir.

    Extracts branch + subdir from GitHub/GitLab tree URLs.
    clone_url is always the bare https://…/.git URL (or ssh original for ssh).
    """
    result = {
        "original_url": url,
        "clone_url": url,
        "platform": "unknown",
        "branch": None,
        "subdir": None,
    }

    # ── GitHub tree URL ───────────────────────────────────────────────
    m = _GITHUB_TREE.match(url)
    if m:
        repo_path, branch, subdir = m.group(1), m.group(2), m.group(3)
        result.update(
            {
                "clone_url": f"https://github.com/{repo_path}.git",
                "platform": "github",
                "branch": branch,
                "subdir": subdir,
            }
        )
        return result

    # ── GitLab tree URL ───────────────────────────────────────────────
    m = _GITLAB_TREE.match(url)
    if m:
        repo_path, branch, subdir = m.group(1), m.group(2), m.group(3)
        result.update(
            {
                "clone_url": f"https://gitlab.com/{repo_path}.git",
                "platform": "gitlab",
                "branch": branch,
                "subdir": subdir,
            }
        )
        return result

    # ── Plain https URL ───────────────────────────────────────────────
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "github.com" in host:
        result["platform"] = "github"
    elif "gitlab.com" in host or "gitlab." in host:
        result["platform"] = "gitlab"
    elif "bitbucket.org" in host:
        result["platform"] = "bitbucket"

    # Normalise to .git
    clone_url = url.rstrip("/")
    if not clone_url.endswith(".git"):
        clone_url += ".git"
    result["clone_url"] = clone_url

    return result


def _inject_token(clone_url: str, token: str) -> str:
    """Inject token sebagai HTTP basic-auth credential ke URL.

    GitHub   → https://<token>@github.com/…
    GitLab   → https://oauth2:<token>@gitlab.com/…
    Bitbucket → https://x-token-auth:<token>@bitbucket.org/…
    """
    parsed = urlparse(clone_url)
    host = parsed.netloc.lower()

    if "github.com" in host:
        netloc = f"{token}@{parsed.hostname}"
    elif "gitlab" in host:
        netloc = f"oauth2:{token}@{parsed.hostname}"
    elif "bitbucket" in host:
        netloc = f"x-token-auth:{token}@{parsed.hostname}"
    else:
        netloc = f"{token}@{parsed.hostname}"

    if parsed.port:
        netloc += f":{parsed.port}"

    return parsed._replace(netloc=netloc).geturl()


# ── Git operations ────────────────────────────────────────────────────────────


def _run_git(args: list[str], cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run git command, raise on error, stream output to stderr."""
    cmd = ["git", *args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=False,
    )


def clone_repo(
    clone_url: str,
    dest: Path,
    branch: str | None = None,
    token: str | None = None,
    depth: int = 1,
) -> None:
    """Shallow-clone `clone_url` into `dest`.

    - depth=1 untuk kecepatan (bisa diubah via --depth)
    - token diinjeksi ke URL, tidak disimpan di disk
    - kalau dest sudah ada, skip clone (gunakan pull)
    """
    auth_url = _inject_token(clone_url, token) if token else clone_url
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # non-interactive

    dest.parent.mkdir(parents=True, exist_ok=True)

    clone_args = ["clone", f"--depth={depth}", "--no-tags"]
    if branch:
        clone_args += ["--branch", branch, "--single-branch"]
    clone_args += [auth_url, str(dest)]

    print(f"  Cloning → {dest} …")
    _run_git(clone_args, env=env)
    print("  Clone complete.")


def pull_repo(
    dest: Path,
    token: str | None = None,
    clone_url: str | None = None,
) -> None:
    """git fetch --depth=1 + reset --hard origin/HEAD di existing clone."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    if token and clone_url:
        auth_url = _inject_token(clone_url, token)
        # Update remote URL sementara (memory only via env, tidak persistent)
        _run_git(["remote", "set-url", "origin", auth_url], cwd=str(dest), env=env)

    print("  Pulling latest from origin …")
    _run_git(["fetch", "--depth=1", "--no-tags", "origin"], cwd=str(dest), env=env)
    _run_git(["reset", "--hard", "FETCH_HEAD"], cwd=str(dest), env=env)

    if token and clone_url:
        # Restore URL tanpa token setelah pull
        _run_git(["remote", "set-url", "origin", clone_url], cwd=str(dest), env=env)

    print("  Pull complete.")


def ensure_local_clone(
    name: str,
    clone_url: str,
    branch: str | None = None,
    token: str | None = None,
    force_clone: bool = False,
    depth: int = 1,
) -> Path:
    """Pastikan repo ter-clone di ~/.logicflow/repos/<name>/.

    Kalau sudah ada dan tidak force → skip clone (bisa pull nanti).
    Returns: path ke repo lokal.
    """
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    dest = REPOS_DIR / name

    if dest.exists() and not force_clone:
        print(f"  Repo sudah ada di {dest} (gunakan 'sync' untuk update).")
        return dest

    if dest.exists() and force_clone:
        print(f"  Menghapus clone lama di {dest} …")
        shutil.rmtree(dest)

    clone_repo(clone_url, dest, branch=branch, token=token, depth=depth)
    return dest


def remove_local_clone(name: str) -> bool:
    """Hapus clone lokal. Returns True kalau ada yang dihapus."""
    dest = REPOS_DIR / name
    if dest.exists():
        shutil.rmtree(dest)
        return True
    return False


# ── Registry helpers ──────────────────────────────────────────────────────────


def is_remote_project(project_entry: dict) -> bool:
    """True kalau project punya remote_url (bukan lokal saja)."""
    return bool(project_entry.get("remote_url"))


def get_scan_root(project_entry: dict, name: str) -> str:
    """Resolve scan root untuk project entry.

    - Remote project → ~/.logicflow/repos/<name>/<subdir>
    - Local project  → project_entry["source"]
    """
    if not is_remote_project(project_entry):
        return project_entry["source"]

    repo_dir = REPOS_DIR / name
    subdir = project_entry.get("remote_subdir") or ""
    scan_root = repo_dir / subdir if subdir else repo_dir
    return str(scan_root)


# ── Validation ────────────────────────────────────────────────────────────────


def validate_git_url(url: str) -> bool:
    """Quick sanity check bahwa URL terlihat seperti git repo URL."""
    if url.startswith("git@"):
        return True
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    path_parts = parsed.path.strip("/").split("/")
    return len(path_parts) >= 2  # minimal owner/repo


def check_git_available() -> None:
    """Exit dengan error message bila git tidak ada di PATH."""
    if shutil.which("git") is None:
        print("Error: git tidak ditemukan di PATH. Install git terlebih dahulu.", file=sys.stderr)
        sys.exit(1)
