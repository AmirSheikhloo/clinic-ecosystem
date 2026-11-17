"""Full-range git diff allowlist guard (A08)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ALLOWED_PREFIXES = (
    "experiments/m102_f2b_bounded_e03/",
)
ALLOWED_EXACT = {
    ".github/workflows/m102-f2b-bounded-e03.yml",
}

FORBIDDEN_PREFIXES = (
    "migrations/",
    "src/",
    "tests/",
    "ops/",
    "docs/",
    ".github/workflows/",
)

PARENT_ENV = "E03_PARENT_COMMIT_SHA"
DEFAULT_PARENT = "471f88417bfcf69ce864b333114e7fb0f777ede0"


class PathAllowlistError(RuntimeError):
    pass


def _normalize(path: str) -> str:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    while "//" in p:
        p = p.replace("//", "/")
    if p.startswith("../") or "/../" in f"/{p}/":
        raise PathAllowlistError(f"path traversal refused: {path!r}")
    return p


def is_allowed_path(path: str) -> bool:
    p = _normalize(path)
    if p in ALLOWED_EXACT:
        return True
    if any(p.startswith(pref) for pref in ALLOWED_PREFIXES):
        return True
    return False


def classify_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    ok, bad = [], []
    for raw in paths:
        p = _normalize(raw)
        # workflow allowlist is exact; other workflows under .github/workflows are forbidden
        if p.startswith(".github/workflows/") and p not in ALLOWED_EXACT:
            bad.append(p)
            continue
        if is_allowed_path(p):
            ok.append(p)
        else:
            bad.append(p)
    return ok, bad


def parse_name_status(diff_text: str) -> list[str]:
    """Parse git diff --name-status -z / line output into path list (new names for renames)."""
    paths: list[str] = []
    for line in diff_text.splitlines():
        line = line.strip("\0").strip()
        if not line:
            continue
        parts = re.split(r"\t+", line)
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            # rename/copy: take destination
            if len(parts) >= 3:
                paths.append(parts[2])
            elif len(parts) == 2:
                paths.append(parts[1])
        else:
            if len(parts) >= 2:
                paths.append(parts[1])
    return paths


def assert_paths_allowed(paths: list[str]) -> list[str]:
    ok, bad = classify_paths(paths)
    if bad:
        raise PathAllowlistError(
            "STOP_SECURITY: out-of-allowlist paths: " + ", ".join(sorted(set(bad)))
        )
    return ok


def git_full_range_paths(parent: str | None = None, head: str = "HEAD", repo: str | Path = ".") -> list[str]:
    parent = parent or os.environ.get(PARENT_ENV, DEFAULT_PARENT)
    proc = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", "--find-copies", f"{parent}...{head}"],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_name_status(proc.stdout)


def assert_repo_range_allowlisted(parent: str | None = None, head: str = "HEAD", repo: str | Path = ".") -> list[str]:
    paths = git_full_range_paths(parent=parent, head=head, repo=repo)
    # also refuse unsafe symlinks in the working tree for allowlisted paths
    for p in paths:
        fp = Path(repo) / p
        if fp.is_symlink():
            raise PathAllowlistError(f"STOP_SECURITY: symlink refused: {p}")
    return assert_paths_allowed(paths)
