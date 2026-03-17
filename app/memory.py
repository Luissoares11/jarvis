import json
import re
from pathlib import Path

from config import MEMORY_FILE
from .utils import clean_text
from .semantic import build_embeddings, find_best_match
from .personality import say


def load_memory():
    if Path(MEMORY_FILE).exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


user_memory = load_memory()

context = {
    "last_topic": None,
    "last_item": None,
}

memory_embeddings = build_embeddings(user_memory.keys())


def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(user_memory, f, indent=4, ensure_ascii=False)


def refresh_embeddings():
    global memory_embeddings
    memory_embeddings = build_embeddings(user_memory.keys())


def list_memories():
    return list(user_memory.keys())


def remember(text: str):
    patterns = [
        r"remember that (.+?) is (.+)",
        r"remember that (.+?) are (.+)",
        r"remember that (.+?)\s*=\s*(.+)",
        r"remember: (.+?) is (.+)",
        r"remember: (.+?) are (.+)",
        r"remember: (.+?)\s*=\s*(.+)",
        r"remember (.+?) as (.+)",
        r"remember (.+?) -> (.+)",
        r"remember (.+?): (.+)",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            key = clean_text(match.group(1))
            value = match.group(2)

            values = [v.strip() for v in value.split(",") if v.strip()]

            if key not in user_memory:
                user_memory[key] = []

            for v in values:
                if v not in user_memory[key]:
                    user_memory[key].append(v)
                    context["last_item"] = v

            context["last_topic"] = key
            save_memory()
            refresh_embeddings()

            return f"{say('confirm')} I will remember '{key}'."

    return say("unknown")


def recall(query: str):
    key_clean = clean_text(query)

    if key_clean in user_memory:
        context["last_topic"] = key_clean
        if user_memory[key_clean]:
            context["last_item"] = user_memory[key_clean][-1]
        return user_memory[key_clean]

    best_key = find_best_match(key_clean, memory_embeddings)
    if best_key:
        context["last_topic"] = best_key
        if user_memory[best_key]:
            context["last_item"] = user_memory[best_key][-1]
        return user_memory[best_key]

    return None


def update_memory(key: str, new_value: str):
    key = clean_text(key)
    new_value = new_value.strip()

    if key not in user_memory:
        user_memory[key] = []

    if new_value not in user_memory[key]:
        user_memory[key].append(new_value)
        context["last_item"] = new_value

    context["last_topic"] = key
    save_memory()
    refresh_embeddings()

    return f"{say('confirm')} Updated '{key}'."


def update_last_topic(new_value: str):
    if not context["last_topic"]:
        return say("unknown")

    return update_memory(context["last_topic"], new_value)


def remove_from_last_topic(value: str):
    if not context["last_topic"]:
        return say("unknown")

    value = value.strip()

    if value in user_memory[context["last_topic"]]:
        user_memory[context["last_topic"]].remove(value)
        save_memory()
        refresh_embeddings()
        return f"{say('confirm')} Removed '{value}' from '{context['last_topic']}'."

    return "That item isn't stored."


def delete_memory(key: str):
    key = clean_text(key)

    if key in user_memory:
        del user_memory[key]
        save_memory()
        refresh_embeddings()
        return f"{say('confirm')} I forgot '{key}'."

    return say("unknown")