import sqlite3
import uuid
from pathlib import Path
from contextlib import contextmanager

from config import MEMORY_FILE

DB_PATH = Path(MEMORY_FILE).with_suffix(".db")


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # safe concurrent reads
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                id       TEXT PRIMARY KEY,
                subject  TEXT NOT NULL,
                relation TEXT NOT NULL,
                object   TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_facts_subject  ON facts(subject);
            CREATE INDEX IF NOT EXISTS idx_facts_relation ON facts(relation);
            CREATE INDEX IF NOT EXISTS idx_facts_subject_relation ON facts(subject, relation);

            CREATE TABLE IF NOT EXISTS collections (
                id    TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                name  TEXT NOT NULL,
                UNIQUE(owner, name)
            );
            CREATE INDEX IF NOT EXISTS idx_collections_owner ON collections(owner);

            CREATE TABLE IF NOT EXISTS collection_items (
                id            TEXT PRIMARY KEY,
                collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
                value         TEXT NOT NULL,
                position      INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS aliases (
                alias     TEXT PRIMARY KEY,
                canonical TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                start_time  TEXT,
                end_time    TEXT,
                notes       TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS computations (
                id          TEXT PRIMARY KEY,
                input       TEXT NOT NULL,
                result      TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)


# ── low level access — used by api.py ────────────────────────

def db_find_facts(subject=None, relation=None, object_=None):
    query = "SELECT * FROM facts WHERE 1=1"
    params = []

    if subject is not None:
        query += " AND subject = ?"
        params.append(subject)
    if relation is not None:
        query += " AND relation = ?"
        params.append(relation)
    if object_ is not None:
        query += " AND object = ?"
        params.append(object_)

    with _conn() as con:
        rows = con.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def db_add_fact(subject: str, relation: str, object_: str):
    fact_id = str(uuid.uuid4())
    with _conn() as con:
        con.execute(
            "INSERT INTO facts (id, subject, relation, object) VALUES (?, ?, ?, ?)",
            (fact_id, subject, relation, object_)
        )
    return {"id": fact_id, "subject": subject, "relation": relation, "object": object_}


def db_delete_facts(subject=None, relation=None, object_=None):
    query = "DELETE FROM facts WHERE 1=1"
    params = []

    if subject is not None:
        query += " AND subject = ?"
        params.append(subject)
    if relation is not None:
        query += " AND relation = ?"
        params.append(relation)
    if object_ is not None:
        query += " AND object = ?"
        params.append(object_)

    with _conn() as con:
        deleted = con.execute(
            query.replace("DELETE", "SELECT *"), params
        ).fetchall()
        con.execute(query, params)
    return [dict(r) for r in deleted]


def db_get_collection(owner: str, name: str):
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM collections WHERE owner = ? AND name = ?",
            (owner, name)
        ).fetchone()
        if not row:
            return None
        items = con.execute(
            "SELECT value FROM collection_items WHERE collection_id = ? ORDER BY position",
            (row["id"],)
        ).fetchall()
    return {
        "id": row["id"],
        "owner": row["owner"],
        "name": row["name"],
        "items": [i["value"] for i in items],
    }


def db_set_collection(owner: str, name: str, items: list[str]):
    with _conn() as con:
        row = con.execute(
            "SELECT id FROM collections WHERE owner = ? AND name = ?",
            (owner, name)
        ).fetchone()

        if row:
            col_id = row["id"]
            con.execute("DELETE FROM collection_items WHERE collection_id = ?", (col_id,))
        else:
            col_id = str(uuid.uuid4())
            con.execute(
                "INSERT INTO collections (id, owner, name) VALUES (?, ?, ?)",
                (col_id, owner, name)
            )

        for pos, value in enumerate(items):
            con.execute(
                "INSERT INTO collection_items (id, collection_id, value, position) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), col_id, value, pos)
            )

    return db_get_collection(owner, name)


def db_list_collections(owner=None):
    with _conn() as con:
        if owner:
            rows = con.execute(
                "SELECT * FROM collections WHERE owner = ?", (owner,)
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM collections").fetchall()

        result = []
        for row in rows:
            items = con.execute(
                "SELECT value FROM collection_items WHERE collection_id = ? ORDER BY position",
                (row["id"],)
            ).fetchall()
            result.append({
                "id": row["id"],
                "owner": row["owner"],
                "name": row["name"],
                "items": [i["value"] for i in items],
            })
    return result


def db_get_aliases():
    with _conn() as con:
        rows = con.execute("SELECT alias, canonical FROM aliases").fetchall()
    return {r["alias"]: r["canonical"] for r in rows}


def db_set_alias(alias: str, canonical: str):
    with _conn() as con:
        con.execute(
            "INSERT INTO aliases (alias, canonical) VALUES (?, ?) "
            "ON CONFLICT(alias) DO UPDATE SET canonical = excluded.canonical",
            (alias, canonical)
        )
    return {alias: canonical}