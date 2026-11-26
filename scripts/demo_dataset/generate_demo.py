#!/usr/bin/env python3
"""CLI entry: load a deterministic demo dataset into a tenant database.

Example:
  CLINIC_ENV=preview \\
  CLINIC_PII_AES_KEY_HEX=$(python -c '...') \\
  python scripts/demo_dataset/generate_demo.py \\
    --dsn postgresql://tp_migrator_login:...@127.0.0.1:5432/tenant_app \\
    --tenant-id <uuid> --receptionist-person-id <uuid> --profile demo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

import asyncpg  # noqa: E402

from clinic_ecosystem.infrastructure.demo.crypto_hooks import preview_demo_pii_env  # noqa: E402
from clinic_ecosystem.infrastructure.demo.loader import load_demo_dataset  # noqa: E402
from clinic_ecosystem.infrastructure.demo.profiles import DEMO_SEED  # noqa: E402


async def _run(args: argparse.Namespace) -> int:
    if args.ensure_preview_keys:
        import os

        for key, value in preview_demo_pii_env(args.seed).items():
            os.environ.setdefault(key, value)

    conn = await asyncpg.connect(args.dsn)
    try:
        result = await load_demo_dataset(
            conn,
            tenant_id=UUID(args.tenant_id),
            receptionist_person_id=UUID(args.receptionist_person_id),
            receptionist_account_id=(
                UUID(args.receptionist_account_id) if args.receptionist_account_id else None
            ),
            profile=args.profile,
            seed=args.seed,
        )
    finally:
        await conn.close()

    out = Path(args.manifest_out) if args.manifest_out else None
    payload = json.dumps(result.manifest, indent=2, ensure_ascii=False)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        print(f"manifest={out}")
    else:
        print(payload)
    print(
        f"profile={result.profile} crypto={result.crypto_seeded} "
        f"patients={result.counts['patients']} appointments={result.counts['appointments']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="asyncpg DSN (migrator role preferred)")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--receptionist-person-id", required=True)
    parser.add_argument("--receptionist-account-id", default=None)
    parser.add_argument("--profile", default="demo", choices=("minimal", "demo", "performance"))
    parser.add_argument("--seed", type=int, default=DEMO_SEED)
    parser.add_argument("--manifest-out", default=None)
    parser.add_argument(
        "--ensure-preview-keys",
        action="store_true",
        help="Set deterministic CLINIC_PII_* keys when missing (non-prod only)",
    )
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
