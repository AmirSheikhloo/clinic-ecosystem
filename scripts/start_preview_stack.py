#!/usr/bin/env python3
"""Start disposable PG15 + API + Next preview for Product Owner inspection.

Non-production only. Writes connection info to artifact_dir/preview.env (mode 0600).
Keeps processes running until terminated.
"""
from __future__ import annotations

import signal
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from tests.e2e.beta01b.stack import start_browser_stack  # noqa: E402
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON  # noqa: E402


def docker_ready() -> bool:
    """Fail fast with an actionable message before expensive stack start."""
    if DOCKER_AVAILABLE:
        return True
    print(
        "Docker is not available or not ready.\n"
        f"Detail: {SKIP_REASON}\n"
        "On Windows: start Docker Desktop, wait until it is healthy, then re-run\n"
        "  powershell -ExecutionPolicy Bypass -File scripts\\start_preview.ps1\n"
        "Do not bypass security settings or kill unrelated containers.",
        file=sys.stderr,
    )
    return False


def main() -> int:
    if not docker_ready():
        return 2
    artifact = REPO / "P03_HANDOFF" / "beta_panel_preview"
    runtime = artifact / "runtime"
    artifact.mkdir(parents=True, exist_ok=True)
    runtime.mkdir(parents=True, exist_ok=True)
    stack = start_browser_stack(artifact_dir=artifact)
    env_path = runtime / "preview.env"
    stack.write_env_file(env_path)
    # Also write legacy path as gitignored runtime copy for older docs.
    summary = runtime / "PREVIEW_URL.txt"
    legacy = artifact / "PREVIEW_URL.txt"
    summary.write_text(
        "\n".join(
            [
                f"PANEL_URL={stack.panel_base_url}/login",
                f"API_URL={stack.api_base_url}/health",
                f"RECEPTIONIST_LOGIN={stack.receptionist_login}",
                f"OWNER_LOGIN={stack.owner_login}",
                f"MANAGER_LOGIN={stack.manager_login}",
                f"DEPUTY_LOGIN={stack.deputy_login}",
                "PASSWORD=see preview.env (chmod 600)",
                f"SERVICE={stack.service_name}",
                f"RESOURCE={stack.resource_name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    legacy.write_text(summary.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"PANEL_URL={stack.panel_base_url}/login")
    print(f"API_HEALTH={stack.api_base_url}/health")
    print(f"CREDENTIALS_FILE={env_path}")

    def _stop(*_args: object) -> None:
        stack.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while True:
        time.sleep(5)
        if stack._api_proc.poll() is not None or stack._panel_proc.poll() is not None:
            print("A preview process exited; shutting down.", file=sys.stderr)
            stack.stop()
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
