import json
import re
from pathlib import Path

from config import MEMORY_FILE
from .utils import clean_text, split_csv_values
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


user_memory = load_memory()

context = {
    "last_topic": None,
    "last_item": None,
    "last_intent": None,
    "history": []
}

topic_embeddings = {}
value_embeddings = []


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

            values = split_csv_values(raw_value)

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


def list_memories():
    return list(user_memory.keys())


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
    new_value = new_value.strip()

    if key not in user_memory:
        user_memory[key] = []

    if new_value not in user_memory[key]:
        user_memory[key].append(new_value)

    save_memory()
    refresh_embeddings()
    push_history("add", topic=key, item=new_value)

    return f"{say('confirm')} Updated '{key}'."


def update_last_topic(new_value: str):
    topic = context.get("last_topic")
    if not topic:
        return say("unknown")
    return update_memory(topic, new_value)


def remove_from_last_topic(value: str):
    topic = context.get("last_topic")
    if not topic:
        return say("unknown")

    value = value.strip()

    if topic in user_memory and value in user_memory[topic]:
        user_memory[topic].remove(value)
        save_memory()
        refresh_embeddings()
        push_history("remove", topic=topic, item=value)
        return f"{say('confirm')} Removed '{value}' from '{topic}'."

    return "That item isn't stored."


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


refresh_embeddings()