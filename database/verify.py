"""Lightweight integrity checks for the seeded demo database."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from seed import seed


def verify() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "demo.db"
        seed(database_path)
        with sqlite3.connect(database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            assert connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 3
            assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 4
            assert connection.execute("SELECT COUNT(*) FROM knowledge_articles").fetchone()[0] == 4
            shipped = connection.execute(
                "SELECT status, estimated_delivery_date FROM orders WHERE order_number = ?", ("CS-1001",)
            ).fetchone()
            assert shipped == ("shipped", "2026-09-24")
            cancellable = connection.execute(
                "SELECT cancellation_eligible FROM orders WHERE order_number = ?", ("CS-1002",)
            ).fetchone()[0]
            assert cancellable == 1
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


if __name__ == "__main__":
    verify()
    print("Database schema and demo seed data verified.")
