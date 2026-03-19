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
            data = json.load(f)

            if "topics" not in data:
                return {
                    "topics": data,
                    "profiles": {},
                    "aliases": {},
                }

            if "profiles" not in data:
                data["profiles"] = {}

            if "aliases" not in data:
                data["aliases"] = {}

            return data

    return {
        "topics": {},
        "profiles": {},
        "aliases": {},
    }


memory_store = load_memory()
user_memory = memory_store["topics"]
profile_memory = memory_store["profiles"]
alias_memory = memory_store["aliases"]


def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "topics": user_memory,
                "profiles": profile_memory,
                "aliases": alias_memory,
            },
            f,
            indent=4,
            ensure_ascii=False,
        )


context = {
    "last_topic": None,
    "last_item": None,
    "last_intent": None,
    "last_profile": None,
    "history": [],
}


def push_history(intent: str, topic=None, item=None, query=None, profile=None):
    context["last_intent"] = intent
    if topic is not None:
        context["last_topic"] = topic
    if item is not None:
        context["last_item"] = item
    if profile is not None:
        context["last_profile"] = profile

    context["history"].append(
        {
            "intent": intent,
            "topic": topic,
            "item": item,
            "query": query,
            "profile": profile,
        }
    )

    if len(context["history"]) > 20:
        context["history"] = context["history"][-20:]


topic_embeddings = {}
value_embeddings = []


def refresh_embeddings():
    global topic_embeddings, value_embeddings
    topic_embeddings = build_topic_embeddings(user_memory)
    value_embeddings = build_value_embeddings(user_memory)


def normalize_existing_memory():
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

    fixed_aliases = {}
    for alias, target in alias_memory.items():
        fixed_aliases[clean_text(alias)] = clean_text(target)

    if fixed_aliases != alias_memory:
        alias_memory.clear()
        alias_memory.update(fixed_aliases)
        changed = True

    fixed_profiles = {}
    for name, fields in profile_memory.items():
        canon = clean_text(name)
        fixed_profiles.setdefault(canon, {})
        for field, value in fields.items():
            fixed_profiles[canon][clean_text(field)] = clean_value(str(value))

    if fixed_profiles != profile_memory:
        profile_memory.clear()
        profile_memory.update(fixed_profiles)
        changed = True

    if changed:
        save_memory()


def ensure_profile(name: str):
    canonical = clean_text(name)
    if canonical not in profile_memory:
        profile_memory[canonical] = {}
    return canonical

def infer_profile_update(text: str):
    t = text.strip()
    lowered = t.lower()

    patterns = [
        (r"(.+?) is (\d+)$", "name_age"),
        (r"(.+?) age is (\d+)", "name_age_alt"),
        (r"(he|she|her|his) is (\d+)$", "pronoun_age"),
        (r"(her|his|their) age is (.+)", "pronoun_age_alt"),
        (r"(?:change|update) (.+?) age to (\d+)", "change_name_age"),
        (r"(?:change|update) (her|his|their) age to (\d+)", "change_pronoun_age"),
    ]

    for pattern, mode in patterns:
        match = re.search(pattern, lowered)
        if not match:
            continue

        if mode == "name_age":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))

            resolved = resolve_profile_reference(name)
            if resolved["status"] == "ok":
                canonical = resolved["name"]
                set_profile_field(canonical, "age", age)
                push_history("infer_profile", profile=canonical, query=text)
                return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "name_age_alt":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))

            resolved = resolve_profile_reference(name)
            if resolved["status"] == "ok":
                canonical = resolved["name"]
                set_profile_field(canonical, "age", age)
                push_history("infer_profile", profile=canonical, query=text)
                return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "pronoun_age":
            age = clean_value(match.group(2))

            if context.get("last_profile"):
                canonical = context["last_profile"]
                set_profile_field(canonical, "age", age)
                push_history("infer_profile", profile=canonical, query=text)
                return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "pronoun_age_alt":
            age = clean_value(match.group(2))

            if context.get("last_profile"):
                canonical = context["last_profile"]
                set_profile_field(canonical, "age", age)
                push_history("infer_profile", profile=canonical, query=text)
                return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "change_name_age":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))

            resolved = resolve_profile_reference(name)
            if resolved["status"] == "ok":
                canonical = resolved["name"]
                set_profile_field(canonical, "age", age)
                push_history("infer_profile", profile=canonical, query=text)
                return f"{say('confirm')} Updated {canonical}'s age."

        if mode == "change_pronoun_age":
            age = clean_value(match.group(2))

            if context.get("last_profile"):
                canonical = context["last_profile"]
                set_profile_field(canonical, "age", age)
                push_history("infer_profile", profile=canonical, query=text)
                return f"{say('confirm')} Updated {canonical}'s age."

    return None

def set_profile_field(name: str, field: str, value: str):
    canonical = ensure_profile(name)
    profile_memory[canonical][clean_text(field)] = clean_value(value)
    save_memory()
    return canonical

def delete_profile_field(name: str, field: str):
    resolved = resolve_profile_reference(name)

    if resolved["status"] != "ok":
        return None

    canonical = resolved["name"]

    if canonical not in profile_memory:
        return None

    field_clean = clean_text(field)

    if field_clean in profile_memory[canonical]:
        del profile_memory[canonical][field_clean]

        # if profile becomes empty → remove it entirely
        if not profile_memory[canonical]:
            del profile_memory[canonical]

            # also clean aliases
            to_delete = [a for a, target in alias_memory.items() if target == canonical]
            for alias in to_delete:
                del alias_memory[alias]

        save_memory()

        push_history("delete_profile_field", profile=canonical)

        return canonical

    return None

def add_alias(alias: str, canonical_name: str):
    alias = clean_text(alias)
    canonical_name = clean_text(canonical_name)

    alias_memory[alias] = canonical_name
    save_memory()


def get_profile(canonical_name: str):
    return profile_memory.get(clean_text(canonical_name))


def list_profiles():
    return list(profile_memory.keys())


def resolve_profile_reference(ref: str):
    ref_clean = clean_text(ref)

    if ref_clean in profile_memory:
        return {"status": "ok", "name": ref_clean}

    if ref_clean in alias_memory:
        target = alias_memory[ref_clean]
        if target in profile_memory:
            return {"status": "ok", "name": target}

    matches = []
    for name in profile_memory.keys():
        if ref_clean == name:
            matches.append(name)
        else:
            parts = name.split()
            if ref_clean in parts:
                matches.append(name)

    matches = sorted(set(matches))

    if len(matches) == 1:
        return {"status": "ok", "name": matches[0]}

    if len(matches) > 1:
        return {"status": "ambiguous", "matches": matches}

    return {"status": "missing"}


def resolve_profile_pronoun(ref: str):
    ref_clean = clean_text(ref)
    if ref_clean in ["her", "his", "their", "them"]:
        if context.get("last_profile"):
            return {"status": "ok", "name": context["last_profile"]}
    return resolve_profile_reference(ref)


def remember_profile(text: str):
    t = text.strip()
    lowered = t.lower()

    patterns = [
        # 🔥 NEW: pronoun-based memory
        (r"(her|his|their) age is (.+)", "pronoun_age"),

        (r"remember that my (.+?)s name is (.+)", "relation_name"),
        (r"remember that (.+?) is my (.+)", "name_relation"),
        (r"remember that (.+?) is (\d+)\s+years old", "name_age_sentence"),
        (r"remember that (.+?)s age is (.+)", "name_age_possessive"),
        (r"remember that my (.+?)s age is (.+)", "relation_age"),
        (r"remember that (.+?) is (\d+)$", "name_age_short"),
    ]

    for pattern, mode in patterns:
        match = re.search(pattern, lowered)
        if not match:
            continue

        # 🔥 NEW: pronoun handler
        if mode == "pronoun_age":
            age = clean_value(match.group(2))

            if context.get("last_profile"):
                canonical = context["last_profile"]
                set_profile_field(canonical, "age", age)

                push_history("remember_profile", profile=canonical, query=text)

                return f"{say('confirm')} I will remember {canonical}'s age."

            return "I don't know who you're referring to."

        if mode == "relation_name":
            relation = clean_text(match.group(1))
            name = clean_value(match.group(2))
            canonical = ensure_profile(name)

            set_profile_field(canonical, "relationship", relation)

            add_alias(f"my {relation}", canonical)

            if relation == "girlfriend":
                add_alias("my girl", canonical)
                add_alias("gf", canonical)

            # 🔥 IMPORTANT: also link simple name alias
            add_alias(name.split()[0], canonical)

            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}."

        if mode == "name_relation":
            name = clean_value(match.group(1))
            relation = clean_text(match.group(2))
            canonical = ensure_profile(name)

            set_profile_field(canonical, "relationship", relation)

            add_alias(f"my {relation}", canonical)

            if relation == "girlfriend":
                add_alias("my girl", canonical)
                add_alias("gf", canonical)

            add_alias(name.split()[0], canonical)

            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}."

        if mode == "name_age_sentence":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))
            canonical = ensure_profile(name)

            set_profile_field(canonical, "age", age)

            add_alias(name.split()[0], canonical)

            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "name_age_possessive":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))
            canonical = ensure_profile(name)

            set_profile_field(canonical, "age", age)

            add_alias(name.split()[0], canonical)

            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "relation_age":
            relation = clean_text(match.group(1))
            age = clean_value(match.group(2))

            resolved = resolve_profile_reference(f"my {relation}")

            if resolved["status"] == "ok":
                canonical = resolved["name"]

                set_profile_field(canonical, "age", age)

                push_history("remember_profile", profile=canonical, query=text)

                return f"{say('confirm')} I will remember {canonical}'s age."

            return "I don't know who that refers to yet."

        if mode == "name_age_short":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))
            canonical = ensure_profile(name)

            set_profile_field(canonical, "age", age)

            add_alias(name.split()[0], canonical)

            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}'s age."

    return None
    t = text.strip()
    lowered = t.lower()

    patterns = [
        (r"remember that my (.+?)s name is (.+)", "relation_name"),
        (r"remember that (.+?) is my (.+)", "name_relation"),
        (r"remember that (.+?) is (\d+)\s+years old", "name_age_sentence"),
        (r"remember that (.+?)s age is (.+)", "name_age_possessive"),
        (r"remember that my (.+?)s age is (.+)", "relation_age"),
        (r"remember that (.+?) is (\d+)$", "name_age_short"),
    ]

    for pattern, mode in patterns:
        match = re.search(pattern, lowered)
        if not match:
            continue

        if mode == "relation_name":
            relation = clean_text(match.group(1))
            name = clean_value(match.group(2))
            canonical = ensure_profile(name)
            set_profile_field(canonical, "relationship", relation)

            add_alias(f"my {relation}", canonical)
            if relation == "girlfriend":
                add_alias("my girl", canonical)
                add_alias("gf", canonical)

            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}."

        if mode == "name_relation":
            name = clean_value(match.group(1))
            relation = clean_text(match.group(2))
            canonical = ensure_profile(name)
            set_profile_field(canonical, "relationship", relation)

            add_alias(f"my {relation}", canonical)
            if relation == "girlfriend":
                add_alias("my girl", canonical)
                add_alias("gf", canonical)

            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}."

        if mode == "name_age_sentence":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))
            canonical = ensure_profile(name)
            set_profile_field(canonical, "age", age)
            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "name_age_possessive":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))
            canonical = ensure_profile(name)
            set_profile_field(canonical, "age", age)
            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}'s age."

        if mode == "relation_age":
            relation = clean_text(match.group(1))
            age = clean_value(match.group(2))
            resolved = resolve_profile_reference(f"my {relation}")
            if resolved["status"] == "ok":
                canonical = resolved["name"]
                set_profile_field(canonical, "age", age)
                push_history("remember_profile", profile=canonical, query=text)
                return f"{say('confirm')} I will remember {canonical}'s age."
            return "I don't know who that refers to yet."

        if mode == "name_age_short":
            name = clean_value(match.group(1))
            age = clean_value(match.group(2))
            canonical = ensure_profile(name)
            set_profile_field(canonical, "age", age)
            push_history("remember_profile", profile=canonical, query=text)
            return f"{say('confirm')} I will remember {canonical}'s age."

    return None


def recall_profile(query: str):
    q = clean_text(query)

    patterns = [
        (r"(?:what do you know about|tell me about|who is) (.+)", "full_profile"),

        # age
        (r"(?:what is|whats) (.+?)s age", "field_age"),
        (r"(?:what is|whats) the age of (.+)", "field_age"),
        (r"how old is (.+)", "field_age"),
        (r"(?:what is|whats) (.+?) age", "field_age"),
        (r"tell me (.+?) age", "field_age"),
        (r"tell me the age of (.+)", "field_age"),
        (r"(.+?) age", "field_age"),

        # name
        (r"(?:what is|whats) (.+?)s name", "field_name"),
        (r"(?:what is|whats) the name of (.+)", "field_name"),
    ]

    for pattern, mode in patterns:
        match = re.search(pattern, q)
        if not match:
            continue

        ref = match.group(1)
        resolved = resolve_profile_pronoun(ref)

        if resolved["status"] == "ambiguous":
            return {
                "type": "ambiguous_profile",
                "matches": resolved["matches"],
            }

        if resolved["status"] != "ok":
            return None

        canonical = resolved["name"]
        profile = profile_memory[canonical]

        push_history("recall_profile", profile=canonical, query=query)

        if mode == "full_profile":
            return {
                "type": "profile",
                "name": canonical,
                "fields": profile,
            }

        if mode == "field_age":
            if "age" in profile:
                return {
                    "type": "profile",
                    "name": canonical,
                    "fields": {"age": profile["age"]},
                }
            return {
                "type": "profile_missing_field",
                "name": canonical,
                "field": "age",
            }

        if mode == "field_name":
            return {
                "type": "profile_name",
                "name": canonical,
            }

    return None


def list_memories():
    all_items = list(user_memory.keys()) + list(profile_memory.keys())
    return sorted(set(all_items))


def remember(text: str):
    text_lower = text.lower().strip()

    # avoid catching age/self-description as a name
    blocked_self_patterns = [
        r"i am \d+\s+years?\s+old",
        r"im \d+\s+years?\s+old",
        r"my age is \d+",
    ]

    for pattern in blocked_self_patterns:
        if re.search(pattern, text_lower):
            return None

    # natural name detection
    self_patterns = [
        r"^i am ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s'-]+)$",
        r"^my name is ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s'-]+)$",
        r"^im ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s'-]+)$",
        r"^remember that i am ([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s'-]+)$",
    ]

    for pattern in self_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = clean_value(match.group(1))

            if "my name" not in user_memory:
                user_memory["my name"] = []

            if name not in user_memory["my name"]:
                user_memory["my name"].append(name)

            save_memory()
            refresh_embeddings()
            push_history("remember", topic="my name", item=name, query=text)

            return f"{say('confirm')} I will remember your name."

    profile_result = remember_profile(text)
    if profile_result:
        return profile_result

    patterns = [
        r"remember that (.+?) is[, ]+(.+)",
        r"remember that (.+?) are[, ]+(.+)",
        r"remember that (.+?)\s*=\s*(.+)",
        r"remember: (.+?) is[, ]+(.+)",
        r"remember: (.+?) are[, ]+(.+)",
        r"remember: (.+?)\s*=\s*(.+)",
        r"remember (.+?) as (.+)",
        r"remember (.+?) -> (.+)",
        r"remember (.+?): (.+)",
    ]

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
            push_history(
                "remember",
                topic=key,
                item=values[-1] if values else None,
                query=text,
            )

            return f"{say('confirm')} I will remember '{key}'."

    return None


def recall_topic(query: str):
    key_clean = clean_text(query)

    if key_clean in user_memory:
        values = user_memory[key_clean]
        push_history("recall", topic=key_clean, item=values[-1] if values else None, query=query)
        return {
            "mode": "topic_exact",
            "topic": key_clean,
            "values": values,
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
            "values": values,
        }

    best_topic, topic_score = find_best_topic(key_clean, topic_embeddings)
    best_value_row, value_score = find_best_value(key_clean, value_embeddings)

    if best_topic and (not best_value_row or topic_score >= value_score):
        values = user_memory[best_topic]
        push_history("recall", topic=best_topic, item=values[-1] if values else None, query=query)
        return {
            "mode": "topic_semantic",
            "topic": best_topic,
            "values": values,
        }

    if best_value_row:
        topic = best_value_row["topic"]
        value = best_value_row["value"]
        push_history("recall", topic=topic, item=value, query=query)
        return {
            "mode": "value_semantic",
            "topic": topic,
            "values": [value],
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
        "first": 0, "1st": 0, "one": 0,
        "second": 1, "2nd": 1, "two": 1,
        "third": 2, "3rd": 2, "three": 2,
        "fourth": 3, "forth": 3, "4th": 3, "four": 3,
        "fifth": 4, "5th": 4, "five": 4,
        "sixth": 5, "6th": 5, "six": 5,
        "seventh": 6, "7th": 6, "seven": 6,
        "eighth": 7, "8th": 7, "eight": 7,
        "ninth": 8, "9th": 8, "nine": 8,
        "tenth": 9, "10th": 9, "ten": 9,
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


def _quantity_from_text(text: str):
    text = clean_text(text)

    mapping = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    for word, qty in mapping.items():
        if re.search(rf"\b{word}\b", text):
            return qty

    match = re.search(r"\b(\d+)\b", text)
    if match:
        return int(match.group(1))

    return 1


def _looks_like_position_request(text: str) -> bool:
    text = clean_text(text)

    keywords = [
        "first", "second", "third", "fourth", "forth", "fifth",
        "sixth", "seventh", "eighth", "ninth", "tenth",
        "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th",
        "last", "position", "number"
    ]

    return any(re.search(rf"\b{re.escape(k)}\b", text) for k in keywords)


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

    for value in topic_values:
        if q in clean_text(value) or clean_text(value) in q:
            user_memory[topic].remove(value)
            save_memory()
            refresh_embeddings()
            push_history("remove", topic=topic, item=value)
            return value

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


def resolve_pronoun(value: str):
    value_clean = clean_text(value)
    if value_clean in ["it", "that", "this"]:
        if context.get("last_item"):
            return context["last_item"]
    return value


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
    key_clean = clean_text(key)
    deleted_any = False
    deleted_name = key_clean

    # 🔥 SPECIAL CASE: my name
    if key_clean in ["my name", "name"]:
        if "my name" in user_memory:
            del user_memory["my name"]
            save_memory()
            refresh_embeddings()
            push_history("delete_memory", topic="my name")
            return f"{say('confirm')} I forgot your name."

    if key_clean in user_memory:
        del user_memory[key_clean]
        deleted_any = True

    resolved = resolve_profile_reference(key_clean)
    if resolved["status"] == "ok":
        canonical = resolved["name"]
        deleted_name = canonical

        if canonical in profile_memory:
            del profile_memory[canonical]
            deleted_any = True

        to_delete = [a for a, target in alias_memory.items() if target == canonical]
        for alias in to_delete:
            del alias_memory[alias]

    if deleted_any:
        save_memory()
        refresh_embeddings()
        push_history("delete_memory", topic=key_clean, profile=deleted_name)
        return f"{say('confirm')} I forgot '{deleted_name}'."

    return say("unknown")


def system_status():
    return {
        "topics": len(user_memory),
        "profiles": len(profile_memory),
        "aliases": len(alias_memory),
        "items": sum(len(v) for v in user_memory.values()),
        "last_topic": context.get("last_topic"),
        "last_item": context.get("last_item"),
        "last_intent": context.get("last_intent"),
        "last_profile": context.get("last_profile"),
    }


normalize_existing_memory()
refresh_embeddings()