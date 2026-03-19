import json
from pathlib import Path

from config import MEMORY_FILE


DEFAULT_MEMORY = {
    "facts": [],
    "collections": [],
    "aliases": {}
}


def load_store():
    path = Path(MEMORY_FILE)

    if not path.exists():
        return DEFAULT_MEMORY.copy()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "facts" not in data:
        data["facts"] = []

    if "collections" not in data:
        data["collections"] = []

    if "aliases" not in data:
        data["aliases"] = {}

    return data


def save_store(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)