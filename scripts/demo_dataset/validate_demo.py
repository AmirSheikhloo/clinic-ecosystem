#!/usr/bin/env python3
"""Validate demo dataset counts; exit 1 when below thresholds for implemented modules."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

import asyncpg  # noqa: E402

from clinic_ecosystem.infrastructure.demo.validate import (  # noqa: E402
    format_report,
    validate_demo_counts,
)


async def _run(args: argparse.Namespace) -> int:
    conn = await asyncpg.connect(args.dsn)
    try:
        report = await validate_demo_counts(
            conn,
            tenant_id=UUID(args.tenant_id),
            profile=args.profile,
            crypto_expected=args.require_crypto,
        )
    finally:
        await conn.close()
    print(format_report(report))
    return 0 if report.ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--profile", default="demo", choices=("minimal", "demo", "performance"))
    parser.add_argument(
        "--require-crypto",
        action="store_true",
        help="Fail when national-id / shared-phone crypto rows are below targets",
    )
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
