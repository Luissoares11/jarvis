import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.memory.store import init_db, db_add_fact, db_set_collection, db_set_alias

MEMORY_JSON = Path("data/memory.json")


def migrate():
    print("Initialising database...")
    init_db()

    with open(MEMORY_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Migrating {len(data['facts'])} facts...")
    for fact in data["facts"]:
        db_add_fact(fact["subject"], fact["relation"], fact["object"])

    print(f"Migrating {len(data['collections'])} collections...")
    for col in data["collections"]:
        db_set_collection(col["owner"], col["name"], col["items"])

    print(f"Migrating {len(data['aliases'])} aliases...")
    for alias, canonical in data["aliases"].items():
        db_set_alias(alias, canonical)

    print("Done. Your data is now in data/memory.db")
    print("You can keep memory.json as a backup or delete it.")


if __name__ == "__main__":
    migrate()