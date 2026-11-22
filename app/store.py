import json
import sqlite3
from contextlib import closing, contextmanager

from app.config import db_path
from app.errors import DomainError
from app.manifest import canonical


@contextmanager
def connection():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, record TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS recoveries (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, event TEXT NOT NULL, record TEXT NOT NULL)""")
        yield conn


def fetch(run_id):
    with connection() as conn:
        row = conn.execute("SELECT source, record FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise DomainError("RUN_NOT_FOUND", "找不到该批次", 404)
    return json.loads(row[0]), json.loads(row[1])


def save(source, record):
    with connection() as conn:
        inserted = conn.execute(
            "INSERT INTO runs VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING",
            (record["id"], canonical(source), canonical(record)),
        ).rowcount
        kept = conn.execute("SELECT record FROM runs WHERE id = ?", (record["id"],)).fetchone()[0]
    return {**json.loads(kept), "reused": not bool(inserted)}


def fetch_recovery(recovery_id):
    with connection() as conn:
        row = conn.execute(
            "SELECT source, event, record FROM recoveries WHERE id = ?", (recovery_id,)).fetchone()
    if row is None:
        raise DomainError("RECOVERY_NOT_FOUND", "找不到该停场恢复单", 404)
    return json.loads(row[0]), json.loads(row[1]), json.loads(row[2])


def save_recovery(source, event, record):
    with connection() as conn:
        inserted = conn.execute(
            "INSERT INTO recoveries VALUES (?, ?, ?, ?) ON CONFLICT(id) DO NOTHING",
            (record["id"], canonical(source), canonical(event), canonical(record)),
        ).rowcount
        kept = conn.execute(
            "SELECT record FROM recoveries WHERE id = ?", (record["id"],)).fetchone()[0]
    return {**json.loads(kept), "reused": not bool(inserted)}
