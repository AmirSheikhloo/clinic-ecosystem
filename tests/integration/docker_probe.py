"""Agent-environment Docker availability probe for integration tests."""

from __future__ import annotations

import os
import shutil
import subprocess


def _env_requires_docker() -> bool:
    return os.environ.get("M0_REQUIRE_DOCKER", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


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

if _env_requires_docker() and not DOCKER_AVAILABLE:
    raise RuntimeError(
        "M0_REQUIRE_DOCKER is set but the Docker daemon is unavailable. "
        "Required PostgreSQL integration tests cannot run."
    )
