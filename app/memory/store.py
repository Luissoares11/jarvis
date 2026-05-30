import json as _json
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
    con.execute("PRAGMA journal_mode=WAL")
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
            CREATE INDEX IF NOT EXISTS idx_facts_subject
                ON facts(subject);
            CREATE INDEX IF NOT EXISTS idx_facts_relation
                ON facts(relation);
            CREATE INDEX IF NOT EXISTS idx_facts_subject_relation
                ON facts(subject, relation);

            CREATE TABLE IF NOT EXISTS collections (
                id    TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                name  TEXT NOT NULL,
                UNIQUE(owner, name)
            );
            CREATE INDEX IF NOT EXISTS idx_collections_owner
                ON collections(owner);

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
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                start_time TEXT,
                end_time   TEXT,
                notes      TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS computations (
                id         TEXT PRIMARY KEY,
                input      TEXT NOT NULL,
                result     TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS learned_patterns (
                id          TEXT PRIMARY KEY,
                phrase      TEXT NOT NULL UNIQUE,
                action_json TEXT NOT NULL,
                use_count   INTEGER DEFAULT 1,
                confirmed   INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now')),
                last_used   TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_patterns_phrase
                ON learned_patterns(phrase);
            CREATE INDEX IF NOT EXISTS idx_patterns_confirmed
                ON learned_patterns(confirmed);
            
            CREATE TABLE IF NOT EXISTS todos (
                id         TEXT PRIMARY KEY,
                task       TEXT NOT NULL,
                priority   TEXT DEFAULT 'normal',
                done       INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id         TEXT PRIMARY KEY,
                message    TEXT NOT NULL,
                remind_at  TEXT NOT NULL,
                fired      INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
                          
            CREATE TABLE IF NOT EXISTS notifications (
                id         TEXT PRIMARY KEY,
                message    TEXT NOT NULL,
                read       INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
                          
            """)


# ── facts ─────────────────────────────────────────────────────

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
            "SELECT value FROM collection_items "
            "WHERE collection_id = ? ORDER BY position",
            (row["id"],)
        ).fetchall()
    return {
        "id":    row["id"],
        "owner": row["owner"],
        "name":  row["name"],
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
            con.execute(
                "DELETE FROM collection_items WHERE collection_id = ?",
                (col_id,)
            )
        else:
            col_id = str(uuid.uuid4())
            con.execute(
                "INSERT INTO collections (id, owner, name) VALUES (?, ?, ?)",
                (col_id, owner, name)
            )

        for pos, value in enumerate(items):
            con.execute(
                "INSERT INTO collection_items "
                "(id, collection_id, value, position) VALUES (?, ?, ?, ?)",
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
                "SELECT value FROM collection_items "
                "WHERE collection_id = ? ORDER BY position",
                (row["id"],)
            ).fetchall()
            result.append({
                "id":    row["id"],
                "owner": row["owner"],
                "name":  row["name"],
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


# ── learned patterns ──────────────────────────────────────────

def db_save_pattern(phrase: str, action: dict, confirmed: bool = False):
    with _conn() as con:
        existing = con.execute(
            "SELECT id, use_count FROM learned_patterns WHERE phrase = ?",
            (phrase,)
        ).fetchone()

        if existing:
            con.execute(
                "UPDATE learned_patterns "
                "SET use_count = ?, last_used = datetime('now'), confirmed = ? "
                "WHERE phrase = ?",
                (existing["use_count"] + 1, int(confirmed), phrase)
            )
        else:
            con.execute(
                "INSERT INTO learned_patterns "
                "(id, phrase, action_json, confirmed) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), phrase, _json.dumps(action), int(confirmed))
            )


def db_get_exact_pattern(phrase: str):
    with _conn() as con:
        row = con.execute(
            "SELECT action_json FROM learned_patterns "
            "WHERE phrase = ? AND confirmed = 1",
            (phrase,)
        ).fetchone()
    return _json.loads(row["action_json"]) if row else None


def db_get_all_confirmed_patterns():
    with _conn() as con:
        rows = con.execute(
            "SELECT phrase, action_json FROM learned_patterns WHERE confirmed = 1"
        ).fetchall()
    return [(r["phrase"], _json.loads(r["action_json"])) for r in rows]


def db_confirm_pattern(phrase: str):
    with _conn() as con:
        con.execute(
            "UPDATE learned_patterns SET confirmed = 1 WHERE phrase = ?",
            (phrase,)
        )


def db_delete_pattern(phrase: str):
    with _conn() as con:
        con.execute(
            "DELETE FROM learned_patterns WHERE phrase = ?",
            (phrase,)
        )

def db_save_computation(input_str: str, result_str: str):
    with _conn() as con:
        con.execute(
            "INSERT INTO computations (id, input, result) VALUES (?, ?, ?)",
            (str(uuid.uuid4()), input_str, result_str)
        )