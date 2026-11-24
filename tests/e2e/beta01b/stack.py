"""Disposable PG15 + FastAPI + Next.js stack for BETA-01B browser E2E.

Uses Testcontainers PostgreSQL 15 and the existing BETA-01B seed.
Never connects to production. Credentials are kept out of stdout.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

import asyncpg

from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.beta01b_seed import (
    TEST_RECEPTIONIST_PASSWORD,
    TEST_UNAUTHORIZED_PASSWORD,
    seed_beta01b_reception,
)
from tests.integration.conftest import (
    DbEndpoint,
    _bootstrap_cloud,
)
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

REPO_ROOT = Path(__file__).resolve().parents[3]
PANEL_DIR = REPO_ROOT / "beta-panel"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_http(url: str, *, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001 — probe only
            last_err = exc
        time.sleep(0.4)
    raise TimeoutError(f"service not ready at {url}: {last_err}")


@dataclass
class BrowserStack:
    panel_base_url: str
    api_base_url: str
    receptionist_login: str
    receptionist_password: str
    unauthorized_login: str
    unauthorized_password: str
    service_name: str
    resource_name: str
    tenant_a_id: str
    artifact_dir: Path
    _cloud: object
    _api_proc: subprocess.Popen[str]
    _panel_proc: subprocess.Popen[str]
    _signing_secret: str

    def write_env_file(self, path: Path) -> None:
        # Playwright reads this; do not print contents.
        path.write_text(
            "\n".join(
                [
                    f"BETA01B_PANEL_BASE_URL={self.panel_base_url}",
                    f"BETA01B_API_BASE_URL={self.api_base_url}",
                    f"BETA01B_RECEPTIONIST_LOGIN={self.receptionist_login}",
                    f"BETA01B_RECEPTIONIST_PASSWORD={self.receptionist_password}",
                    f"BETA01B_UNAUTHORIZED_LOGIN={self.unauthorized_login}",
                    f"BETA01B_UNAUTHORIZED_PASSWORD={self.unauthorized_password}",
                    f"BETA01B_SERVICE_NAME={self.service_name}",
                    f"BETA01B_RESOURCE_NAME={self.resource_name}",
                    f"BETA01B_TENANT_A_ID={self.tenant_a_id}",
                    f"BETA01B_ARTIFACT_DIR={self.artifact_dir}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        path.chmod(0o600)

    def stop(self) -> None:
        for proc in (self._panel_proc, self._api_proc):
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
        cloud = self._cloud
        try:
            cloud.stop()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass


def require_docker_for_browser_e2e() -> None:
    require = os.environ.get("BETA01B_REQUIRE_BROWSER_E2E", "").strip().lower() in {
        "1",
        "true",
        "yes",
    } or os.environ.get("M0_REQUIRE_DOCKER", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not DOCKER_AVAILABLE:
        if require:
            raise RuntimeError(
                "BETA-01B browser E2E requires Docker/PostgreSQL 15 Testcontainers, "
                "but Docker is unavailable."
            )
        raise RuntimeError(f"SKIP_BROWSER_E2E: {SKIP_REASON}")


def start_browser_stack(*, artifact_dir: Path) -> BrowserStack:
    require_docker_for_browser_e2e()

    from testcontainers.postgres import PostgresContainer

    artifact_dir.mkdir(parents=True, exist_ok=True)
    passwords = {
        "tp_migrator_login": secrets.token_urlsafe(24),
        "tp_app_login": secrets.token_urlsafe(24),
        "cp_migrator_login": secrets.token_urlsafe(24),
        "cp_app_login": secrets.token_urlsafe(24),
    }
    signing_secret = secrets.token_urlsafe(48)

    cloud = PostgresContainer("postgres:15")
    cloud.start()

    cloud_admin = DbEndpoint(
        host=cloud.get_container_host_ip(),
        port=int(cloud.get_exposed_port(5432)),
        user=cloud.username,
        password=cloud.password,
        database=cloud.dbname,
    )
    asyncio.run(_bootstrap_cloud(cloud_admin, passwords))

    migrator = DbEndpoint(
        host=cloud_admin.host,
        port=cloud_admin.port,
        user="tp_migrator_login",
        password=passwords["tp_migrator_login"],
        database="tenant_app",
    )

    async def _migrate_and_seed():
        await upgrade_tenant_plane_async(migrator.sqlalchemy_async_url())
        conn = await asyncpg.connect(migrator.asyncpg_dsn())
        try:
            return await seed_beta01b_reception(conn)
        finally:
            await conn.close()

    seed = asyncio.run(_migrate_and_seed())

    app_url = (
        f"postgresql+asyncpg://{quote_plus('tp_app_login')}:"
        f"{quote_plus(passwords['tp_app_login'])}"
        f"@{cloud_admin.host}:{cloud_admin.port}/tenant_app"
    )

    api_port = _free_port()
    panel_port = _free_port()
    api_base = f"http://127.0.0.1:{api_port}"
    panel_base = f"http://127.0.0.1:{panel_port}"

    api_env = os.environ.copy()
    api_env.update(
        {
            "CLINIC_ENV": "test",
            "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
            "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(seed.tenant_a_id),
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": signing_secret,
            "CLINIC_DATABASE_URL": app_url,
            "CLINIC_ACCESS_TOKEN_TTL_SECONDS": "900",
            "PYTHONUNBUFFERED": "1",
        }
    )
    api_log = (artifact_dir / "api.log").open("w", encoding="utf-8")
    api_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "clinic_ecosystem.presentation.http.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
            "--log-level",
            "warning",
        ],
        cwd=str(REPO_ROOT),
        env=api_env,
        stdout=api_log,
        stderr=subprocess.STDOUT,
        text=True,
    )

    panel_env = os.environ.copy()
    panel_env.update(
        {
            "CLINIC_ENV": "test",
            "CLINIC_BETA_PANEL_ENABLED": "1",
            "CLINIC_API_BASE_URL": api_base,
            "PORT": str(panel_port),
            "HOSTNAME": "127.0.0.1",
        }
    )
    panel_log = (artifact_dir / "panel.log").open("w", encoding="utf-8")
    panel_proc = subprocess.Popen(
        ["npm", "run", "start", "--", "--port", str(panel_port), "--hostname", "127.0.0.1"],
        cwd=str(PANEL_DIR),
        env=panel_env,
        stdout=panel_log,
        stderr=subprocess.STDOUT,
        text=True,
    )

    stack = BrowserStack(
        panel_base_url=panel_base,
        api_base_url=api_base,
        receptionist_login=seed.receptionist_login,
        receptionist_password=TEST_RECEPTIONIST_PASSWORD,
        unauthorized_login=seed.unauthorized_login,
        unauthorized_password=TEST_UNAUTHORIZED_PASSWORD,
        service_name="Tenant A Consultation",
        resource_name="Room Alpha",
        tenant_a_id=str(seed.tenant_a_id),
        artifact_dir=artifact_dir,
        _cloud=cloud,
        _api_proc=api_proc,
        _panel_proc=panel_proc,
        _signing_secret=signing_secret,
    )
    try:
        _wait_http(f"{api_base}/health", timeout_s=90)
        _wait_http(f"{panel_base}/login", timeout_s=120)
        # Sanity: API login works before browser work.
        payload = json.dumps(
            {
                "login_identifier": seed.receptionist_login,
                "password": TEST_RECEPTIONIST_PASSWORD,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{api_base}/api/v1/auth/login",
            data=payload,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("tenant_id") != str(seed.tenant_a_id):
            raise RuntimeError("stack login returned unexpected tenant")
        if "access_token" not in body:
            raise RuntimeError("stack login missing access_token")
    except Exception:
        stack.stop()
        raise
    return stack
