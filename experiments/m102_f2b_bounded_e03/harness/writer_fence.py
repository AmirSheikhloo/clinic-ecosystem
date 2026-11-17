"""Synthetic stale/offline writer fence (A03)."""

from __future__ import annotations

import psycopg2


class WriterFenceError(RuntimeError):
    pass


def ensure_fence_tables(dsn: str) -> None:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS exp_e03_writer_epoch (
              id INT PRIMARY KEY CHECK (id = 1),
              epoch INT NOT NULL,
              drained BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        cur.execute(
            """
            INSERT INTO exp_e03_writer_epoch(id, epoch, drained)
            VALUES (1, 1, FALSE)
            ON CONFLICT (id) DO NOTHING
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS exp_e03_writer_tokens (
              token TEXT PRIMARY KEY,
              epoch INT NOT NULL,
              offline BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def issue_token(dsn: str, token: str) -> int:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT epoch FROM exp_e03_writer_epoch WHERE id=1")
        epoch = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO exp_e03_writer_tokens(token, epoch, offline)
            VALUES (%s, %s, FALSE)
            ON CONFLICT (token) DO UPDATE SET epoch=EXCLUDED.epoch, offline=FALSE
            """,
            (token, epoch),
        )
        conn.commit()
        return epoch
    finally:
        conn.close()


def advance_epoch_and_drain(dsn: str) -> int:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE exp_e03_writer_epoch SET epoch = epoch + 1, drained = TRUE WHERE id=1 RETURNING epoch"
        )
        epoch = cur.fetchone()[0]
        conn.commit()
        return epoch
    finally:
        conn.close()


def assert_writer_admitted(dsn: str, token: str) -> None:
    """Fail-closed fence: unknown/stale/offline tokens denied before protected write."""
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT epoch, drained FROM exp_e03_writer_epoch WHERE id=1")
        row = cur.fetchone()
        if not row:
            raise WriterFenceError("fence_missing_epoch")
        current_epoch, drained = row
        cur.execute(
            "SELECT epoch, offline FROM exp_e03_writer_tokens WHERE token=%s", (token,)
        )
        tok = cur.fetchone()
        if not tok:
            raise WriterFenceError("DENY_unknown_token")
        tok_epoch, offline = tok
        if offline:
            raise WriterFenceError("DENY_offline_writer")
        if tok_epoch < current_epoch:
            raise WriterFenceError("DENY_stale_writer_epoch")
        if drained and tok_epoch < current_epoch:
            raise WriterFenceError("DENY_pre_drain_writer")
    finally:
        conn.close()
