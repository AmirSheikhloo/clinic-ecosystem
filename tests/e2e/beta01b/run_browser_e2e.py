#!/usr/bin/env python3
"""Orchestrate disposable stack + Playwright Chromium for BETA-01B.

Exit codes:
  0 — browser E2E passed
  2 — skipped because Docker unavailable (only when not required)
  1 — failure
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.e2e.beta01b.stack import (
    REPO_ROOT,
    PANEL_DIR,
    start_browser_stack,
)

_raw_artifact = os.environ.get("BETA01B_E2E_ARTIFACT_DIR", str(REPO_ROOT / "artifacts" / "beta01b-e2e"))
# Absolute path required: Playwright loads the env file with cwd=beta-panel/.
ARTIFACT_DIR = Path(_raw_artifact).expanduser().resolve()
ENV_FILE = ARTIFACT_DIR / "playwright.env"


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stack = None
    try:
        try:
            stack = start_browser_stack(artifact_dir=ARTIFACT_DIR)
        except RuntimeError as exc:
            msg = str(exc)
            if msg.startswith("SKIP_BROWSER_E2E:"):
                print(msg, file=sys.stderr)
                return 2
            raise

        stack.write_env_file(ENV_FILE)
        # Load env for child without printing secrets.
        # playwright.env values are shell-quoted for `source`; strip quotes for Node.
        def _unquote(raw: str) -> str:
            text = raw.strip()
            if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
                return text[1:-1]
            return text

        env = os.environ.copy()
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key] = _unquote(value)
        env["BETA01B_E2E_ENV_FILE"] = str(ENV_FILE)

        print(
            "BETA-01B browser E2E: starting Playwright Chromium against real panel/BFF/API/PG15",
            flush=True,
        )
        result = subprocess.run(
            ["npx", "playwright", "test", "--config=e2e/playwright.config.ts"],
            cwd=str(PANEL_DIR),
            env=env,
            check=False,
        )
        if result.returncode != 0:
            print("BETA-01B browser E2E FAILED", file=sys.stderr)
            return 1
        print("BETA-01B browser E2E PASSED", flush=True)
        return 0
    finally:
        if stack is not None:
            stack.stop()
        # Never leave credentials on disk after the run in CI artifacts.
        if ENV_FILE.exists():
            try:
                ENV_FILE.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
