import json
import re
from pathlib import Path

from config import MEMORY_FILE
from .utils import clean_text, clean_value, split_values

from .semantic import (
    build_topic_embeddings,
    build_value_embeddings,
    find_best_topic,
    find_best_value,
)
from .personality import say


def load_memory():
    if Path(MEMORY_FILE).exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def normalize_existing_memory():
    """
    One-time cleanup for old stored values like 'lara?'.
    """
    changed = False

    for topic, values in user_memory.items():
        cleaned = []
        for value in values:
            fixed = clean_value(value)
            if fixed not in cleaned:
                cleaned.append(fixed)

        if cleaned != values:
            user_memory[topic] = cleaned
            changed = True

    if changed:
        save_memory()
        refresh_embeddings()

user_memory = load_memory()

context = {
    "last_topic": None,
    "last_item": None,
    "last_intent": None,
    "history": []
}

topic_embeddings = {}
value_embeddings = []

def resolve_pronoun(value: str):
    """
    Resolve 'it', 'that', 'this' to the last referenced item.
    """
    value_clean = clean_text(value)

    if value_clean in ["it", "that", "this"]:
        if context.get("last_item"):
            return context["last_item"]

    return value

def refresh_embeddings():
    global topic_embeddings, value_embeddings
    topic_embeddings = build_topic_embeddings(user_memory)
    value_embeddings = build_value_embeddings(user_memory)


def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(user_memory, f, indent=4, ensure_ascii=False)


def push_history(intent: str, topic=None, item=None, query=None):
    context["last_intent"] = intent
    if topic is not None:
        context["last_topic"] = topic
    if item is not None:
        context["last_item"] = item

    context["history"].append({
        "intent": intent,
        "topic": topic,
        "item": item,
        "query": query,
    })

    if len(context["history"]) > 20:
        context["history"] = context["history"][-20:]


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
            raw_value = match.group(2)

            values = split_values(raw_value)

            if key not in user_memory:
                user_memory[key] = []

            for value in values:
                if value not in user_memory[key]:
                    user_memory[key].append(value)

            save_memory()
            refresh_embeddings()
            push_history("remember", topic=key, item=values[-1] if values else None, query=text)

            return f"{say('confirm')} I will remember '{key}'."

    return say("unknown")


def recall_topic(query: str):
    key_clean = clean_text(query)

    if key_clean in user_memory:
        values = user_memory[key_clean]
        push_history("recall", topic=key_clean, item=values[-1] if values else None, query=query)
        return {
            "mode": "topic_exact",
            "topic": key_clean,
            "values": values
        }

    from difflib import get_close_matches
    fuzzy = get_close_matches(key_clean, list(user_memory.keys()), n=1, cutoff=0.55)
    if fuzzy:
        topic = fuzzy[0]
        values = user_memory[topic]
        push_history("recall", topic=topic, item=values[-1] if values else None, query=query)
        return {
            "mode": "topic_fuzzy",
            "topic": topic,
            "values": values
        }

    best_topic, topic_score = find_best_topic(key_clean, topic_embeddings)
    best_value_row, value_score = find_best_value(key_clean, value_embeddings)

    if best_topic and (not best_value_row or topic_score >= value_score):
        values = user_memory[best_topic]
        push_history("recall", topic=best_topic, item=values[-1] if values else None, query=query)
        return {
            "mode": "topic_semantic",
            "topic": best_topic,
            "values": values
        }

    if best_value_row:
        topic = best_value_row["topic"]
        value = best_value_row["value"]
        push_history("recall", topic=topic, item=value, query=query)
        return {
            "mode": "value_semantic",
            "topic": topic,
            "values": [value]
        }

    return None


def update_memory(key: str, new_value: str):
    key = clean_text(key)
    values = split_values(new_value)

    if key not in user_memory:
        user_memory[key] = []

    added = []

    for value in values:
        value = clean_value(value)
        if value and value not in user_memory[key]:
            user_memory[key].append(value)
            added.append(value)

    save_memory()
    refresh_embeddings()

    last_item = added[-1] if added else None
    push_history("add", topic=key, item=last_item)

    return f"{say('confirm')} Updated '{key}'."


def update_last_topic(new_value: str):
    topic = context.get("last_topic")
    if not topic:
        return say("unknown")
    return update_memory(topic, new_value)


def _ordinal_to_index(text: str):
    text = clean_text(text)

    mapping = {
        "first": 0,
        "1st": 0,
        "one": 0,

        "second": 1,
        "2nd": 1,
        "two": 1,

        "third": 2,
        "3rd": 2,
        "three": 2,

        "fourth": 3,
        "forth": 3,
        "4th": 3,
        "four": 3,

        "fifth": 4,
        "5th": 4,
        "five": 4,

        "sixth": 5,
        "6th": 5,
        "six": 5,

        "seventh": 6,
        "7th": 6,
        "seven": 6,

        "eighth": 7,
        "8th": 7,
        "eight": 7,

        "ninth": 8,
        "9th": 8,
        "nine": 8,

        "tenth": 9,
        "10th": 9,
        "ten": 9,
    }

    for word, idx in mapping.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            return idx

    match = re.search(r"\b(\d+)\b", text)
    if match:
        num = int(match.group(1))
        if num > 0:
            return num - 1

    return None


def _looks_like_position_request(text: str) -> bool:
    text = clean_text(text)

    keywords = [
        "first", "second", "third", "fourth", "forth", "fifth",
        "sixth", "seventh", "eighth", "ninth", "tenth",
        "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th",
        "last", "position", "number"
    ]

    return any(re.search(rf"\b{re.escape(k)}\b", text) for k in keywords)


def _quantity_from_text(text: str):
    text = clean_text(text)

    mapping = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }

    for word, qty in mapping.items():
        if re.search(rf"\b{word}\b", text):
            return qty

    match = re.search(r"\b(\d+)\b", text)
    if match:
        return int(match.group(1))

    return 1


def _remove_by_index(topic: str, idx: int):
    if topic not in user_memory:
        return None

    values = user_memory[topic]
    if 0 <= idx < len(values):
        removed = values.pop(idx)
        save_memory()
        refresh_embeddings()
        push_history("remove", topic=topic, item=removed)
        return removed

    return None


def _remove_exact(topic: str, value: str):
    if topic not in user_memory:
        return None

    if value in user_memory[topic]:
        user_memory[topic].remove(value)
        save_memory()
        refresh_embeddings()
        push_history("remove", topic=topic, item=value)
        return value

    return None


def _remove_semantic_from_topic(topic: str, query: str):
    if topic not in user_memory or not user_memory[topic]:
        return None

    topic_values = user_memory[topic]
    q = clean_text(query)

    # partial direct fallback first
    for value in topic_values:
        if q in clean_text(value) or clean_text(value) in q:
            user_memory[topic].remove(value)
            save_memory()
            refresh_embeddings()
            push_history("remove", topic=topic, item=value)
            return value

    # semantic fallback
    best_row, best_score = find_best_value(f"{topic} :: {query}", value_embeddings, threshold=0.0)
    if best_row and best_row["topic"] == topic and best_score >= 0.45:
        value = best_row["value"]
        if value in user_memory[topic]:
            user_memory[topic].remove(value)
            save_memory()
            refresh_embeddings()
            push_history("remove", topic=topic, item=value)
            return value

    return None


def remove_from_last_topic(value: str):
    topic = context.get("last_topic")
    if not topic:
        return say("unknown")

    raw_value = resolve_pronoun(value.strip())
    value_clean = clean_text(raw_value)

    if re.search(r"\blast\b", value_clean):
        qty = _quantity_from_text(value_clean)

        if topic not in user_memory or not user_memory[topic]:
            return "There is nothing to remove."

        removed = []
        for _ in range(min(qty, len(user_memory[topic]))):
            removed_item = user_memory[topic].pop(-1)
            removed.append(removed_item)

        save_memory()
        refresh_embeddings()
        push_history("remove", topic=topic, item=removed[-1] if removed else None)

        if len(removed) == 1:
            return f"{say('confirm')} Removed '{removed[0]}' from '{topic}'."
        return f"{say('confirm')} Removed {len(removed)} items from '{topic}'."

    # remove first two / first three / etc.
    if re.search(r"\bfirst\b", value_clean):
        qty = _quantity_from_text(value_clean)
        if topic not in user_memory or not user_memory[topic]:
            return "There is nothing to remove."

        removed = []
        for _ in range(min(qty, len(user_memory[topic]))):
            removed.append(user_memory[topic].pop(0))

        save_memory()
        refresh_embeddings()
        push_history("remove", topic=topic, item=removed[-1] if removed else None)

        if len(removed) == 1:
            return f"{say('confirm')} Removed '{removed[0]}' from '{topic}'."
        return f"{say('confirm')} Removed {len(removed)} items from '{topic}'."

    idx = _ordinal_to_index(value_clean)
    if idx is not None:
        removed = _remove_by_index(topic, idx)
        if removed is not None:
            return f"{say('confirm')} Removed '{removed}' from '{topic}'."
        return "That position does not exist."

    removed = _remove_exact(topic, raw_value)
    if removed is not None:
        return f"{say('confirm')} Removed '{removed}' from '{topic}'."

    if _looks_like_position_request(value_clean):
        return "I couldn't identify that position."

    removed = _remove_semantic_from_topic(topic, raw_value)
    if removed is not None:
        return f"{say('confirm')} Removed '{removed}' from '{topic}'."

    return "That item isn't stored."


def get_item_from_last_topic(selector: str):
    topic = context.get("last_topic")
    if not topic or topic not in user_memory:
        return None, "I don't know what you're referring to."

    values = user_memory[topic]
    sel = clean_text(selector)

    if not values:
        return None, "There is nothing stored there."

    if "last" in sel:
        return values[-1], None

    idx = _ordinal_to_index(sel)
    if idx is not None:
        if 0 <= idx < len(values):
            return values[idx], None
        return None, "That position does not exist."

    # semantic fallback
    q = clean_text(selector)
    for value in values:
        if q in clean_text(value) or clean_text(value) in q:
            return value, None

    best_row, best_score = find_best_value(f"{topic} :: {selector}", value_embeddings, threshold=0.0)
    if best_row and best_row["topic"] == topic and best_score >= 0.45:
        return best_row["value"], None

    return None, "I couldn't identify that item."


def replace_in_last_topic(selector: str, new_value: str):
    topic = context.get("last_topic")
    if not topic or topic not in user_memory:
        return say("unknown")

    old_value, error = get_item_from_last_topic(selector)
    if error:
        return error

    idx = user_memory[topic].index(old_value)
    new_value = clean_value(new_value)

    user_memory[topic][idx] = new_value

    save_memory()
    refresh_embeddings()
    push_history("replace", topic=topic, item=new_value)
    context["last_item"] = new_value

    return f"{say('confirm')} Replaced '{old_value}' with '{new_value}' in '{topic}'."


def move_in_last_topic(selector: str, destination: str):
    topic = context.get("last_topic")
    if not topic or topic not in user_memory:
        return say("unknown")

    values = user_memory[topic]
    if not values:
        return "There is nothing to move."

    item, error = get_item_from_last_topic(selector)
    if error:
        return error

    current_idx = values.index(item)
    values.pop(current_idx)

    dest_clean = clean_text(destination)

    if "end" in dest_clean or "last" in dest_clean:
        values.append(item)
    elif "start" in dest_clean or "beginning" in dest_clean or "front" in dest_clean or "first" in dest_clean:
        values.insert(0, item)
    else:
        idx = _ordinal_to_index(dest_clean)
        if idx is None:
            # restore
            values.insert(current_idx, item)
            return "I couldn't identify where to move it."
        if idx < 0:
            idx = 0
        if idx > len(values):
            idx = len(values)
        values.insert(idx, item)

    save_memory()
    refresh_embeddings()
    push_history("move", topic=topic, item=item)

    return f"{say('confirm')} Moved '{item}' in '{topic}'."

def delete_memory(key: str):
    key = clean_text(key)

    if key in user_memory:
        del user_memory[key]
        save_memory()
        refresh_embeddings()
        push_history("delete_topic", topic=key)
        return f"{say('confirm')} I forgot '{key}'."

    return say("unknown")

def system_status():
    return {
        "topics": len(user_memory),
        "items": sum(len(v) for v in user_memory.values()),
        "last_topic": context.get("last_topic"),
        "last_item": context.get("last_item"),
        "last_intent": context.get("last_intent"),
    }


normalize_existing_memory()
refresh_embeddings()