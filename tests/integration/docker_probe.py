"""Agent-environment Docker availability probe for integration tests."""

from __future__ import annotations

import shutil
import subprocess


def docker_available() -> bool:
    """Return True only if the Docker CLI exists and the daemon responds."""
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


DOCKER_AVAILABLE = docker_available()

SKIP_REASON = (
    "Docker is not available in the Agent execution environment; "
    "PostgreSQL Testcontainers integration tests are NOT RUN."
)
