#!/usr/bin/env python3
"""Install and build the preview inputs only when they changed.

Stamps live in `.preview-cache/stamps.json` (git-ignored). A step is skipped when the hash of its
inputs matches the stamp and its output still exists, so repeated starts do not reinstall or rebuild.
Works on Windows, macOS and Linux; `npm` is resolved with `shutil.which` so `npm.cmd` is found.

Usage: python scripts/prepare_preview.py [--check] [--force]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PANEL = REPO / "beta-panel"
STAMP_FILE = REPO / ".preview-cache" / "stamps.json"

PANEL_SOURCE_DIRS = ("app", "components", "config", "design-system", "features", "lib", "public")
PANEL_SOURCE_FILES = (
    "package.json",
    "package-lock.json",
    "next.config.ts",
    "next.config.mjs",
    "next.config.js",
    "tsconfig.json",
    "postcss.config.mjs",
)
IGNORED_PARTS = {"node_modules", ".next", "__pycache__"}


def _hash_files(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(REPO).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _panel_files(directories: tuple[str, ...], names: tuple[str, ...]) -> list[Path]:
    files = [PANEL / name for name in names if (PANEL / name).is_file()]
    for directory in directories:
        root = PANEL / directory
        if root.is_dir():
            files.extend(
                path for path in root.rglob("*") if path.is_file() and not IGNORED_PARTS & set(path.parts)
            )
    return files


def _load() -> dict[str, str]:
    try:
        return json.loads(STAMP_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(stamps: dict[str, str]) -> None:
    STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAMP_FILE.write_text(json.dumps(stamps, indent=2, sort_keys=True), encoding="utf-8")


def _run(command: list[str], cwd: Path) -> None:
    print(f"  $ {' '.join(command)}  (in {cwd.relative_to(REPO) if cwd != REPO else '.'})", flush=True)
    subprocess.run(command, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only report what would run")
    parser.add_argument("--force", action="store_true", help="ignore stamps and run every step")
    args = parser.parse_args()

    npm = shutil.which("npm")
    if not npm:
        print("npm was not found on PATH. Install Node.js 22 and reopen the terminal.", file=sys.stderr)
        return 2

    stamps = _load()
    python_deps_digest = _hash_files([REPO / "pyproject.toml"])
    # Do not skip python-deps solely because an old stamp exists: verify the
    # installed environment can resolve Asia/Tehran (Windows needs tzdata).
    tehran_ok = False
    try:
        sys.path.insert(0, str(REPO / "src"))
        from clinic_ecosystem.infrastructure.timezones import tehran_zoneinfo_preflight

        tehran_ok = bool(tehran_zoneinfo_preflight().get("ok"))
    except Exception:  # noqa: BLE001 — treat any import/runtime failure as rebuild
        tehran_ok = False

    steps = [
        (
            "python-deps",
            python_deps_digest,
            tehran_ok,
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            REPO,
        ),
        (
            "npm-ci",
            _hash_files(_panel_files((), ("package.json", "package-lock.json"))),
            (PANEL / "node_modules").is_dir(),
            [npm, "ci"],
            PANEL,
        ),
        (
            "next-build",
            _hash_files(_panel_files(PANEL_SOURCE_DIRS, PANEL_SOURCE_FILES)),
            (PANEL / ".next" / "BUILD_ID").is_file(),
            [npm, "run", "build"],
            PANEL,
        ),
    ]

    for name, digest, output_exists, command, cwd in steps:
        current = stamps.get(name) == digest and output_exists and not args.force
        if current:
            print(f"[skip] {name}: inputs unchanged")
            continue
        print(f"[run ] {name}")
        if args.check:
            continue
        _run(command, cwd)
        stamps[name] = digest
        _save(stamps)
        # a dependency install changes the build inputs' environment
        if name == "npm-ci":
            stamps.pop("next-build", None)
            _save(stamps)
        if name == "python-deps":
            # Re-verify timezone data after install; fail loudly if still missing.
            from clinic_ecosystem.infrastructure.timezones import require_tehran_zoneinfo

            require_tehran_zoneinfo()
            print("[ok  ] python-deps: Asia/Tehran ZoneInfo resolved")
    print("Preview inputs are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
