###Parser

import re

from .utils import clean_text, clean_value, split_values
from .relations import REL_NAME, REL_AGE, REL_RELATIONSHIP


def parse_input(text: str):
    raw = text.strip()
    raw_lower = raw.lower().strip()
    t = clean_text(raw)

    if not t:
        return {"action": "empty"}

    # debug
    if t in ["jarvis facts", "jarvis aliases", "jarvis context", "jarvis collections"]:
        return {"action": "debug_command", "name": t}

    m = re.match(r"^jarvis dump (.+)$", t)
    if m:
        return {"action": "debug_dump_subject", "subject": clean_value(m.group(1))}

    # multi-fact support
    if " and " in t:
        parts = [p.strip() for p in t.split(" and ")]
        parsed = [parse_input(p) for p in parts]

        if all(p.get("action") == "store_fact" for p in parsed):
            return {"action": "batch_store", "items": parsed}

    # greeting
    if re.fullmatch(r"(hello|hi|hey|yo)", t):
        return {"action": "greeting"}

    # knowledge
    if t in ["who do you know", "who do you know?"]:
        return {"action": "list_entities"}

    if t in [
        "what do you know",
        "what do you know?",
        "tell me what do you know",
        "tell me what you know",
    ]:
        return {"action": "list_knowledge"}

    # self query
    if t in ["who am i", "who am i?", "what is my name", "whats my name"]:
        return {
            "action": "query_fact",
            "subject": "user",
            "relation": REL_NAME,
        }

    if t in ["how old am i", "tell me my age", "what is my age", "whats my age", "do you know my age"]:
        return {
            "action": "query_fact",
            "subject": "user",
            "relation": REL_AGE,
        }

    # collection positional delete
    m = re.match(r"^(?:remove|delete) (?:the )?(first|second|third|last)$", t)
    if m:
        return {
            "action": "remove_from_last_collection_by_position",
            "position": m.group(1),
        }

    # collection replace
    m = re.match(r"^replace (.+?) with (.+)$", t)
    if m:
        return {
            "action": "replace_in_last_collection",
            "old": clean_value(m.group(1)),
            "new": clean_value(m.group(2)),
        }

    # collection add
    m = re.match(r"^(?:add|append) (.+)$", t)
    if m:
        return {
            "action": "add_to_last_collection",
            "item": clean_value(m.group(1)),
        }

    # self name
    for pattern in [
        r"^i am ([a-zà-ÿ][a-zà-ÿ\s'-]+)$",
        r"^my name is ([a-zà-ÿ][a-zà-ÿ\s'-]+)$",
        r"^im ([a-zà-ÿ][a-zà-ÿ\s'-]+)$",
    ]:
        m = re.match(pattern, t)
        if m:
            value = clean_value(m.group(1))

            blocked = [
                re.fullmatch(r"\d+\s+years?\s+old", value),
                re.fullmatch(r"\d+", value),
            ]
            if any(blocked):
                break

            return {
                "action": "store_fact",
                "subject": "user",
                "relation": REL_NAME,
                "object": value,
                "replace": True,
            }

    # self age
    for pattern in [
        r"^i am (\d+)\s+years?\s+old$",
        r"^im (\d+)\s+years?\s+old$",
        r"^my age is (\d+)$",
        r"^update my age to (\d+)$",
        r"^change my age to (\d+)$",
    ]:
        m = re.match(pattern, t)
        if m:
            return {
                "action": "store_fact",
                "subject": "user",
                "relation": REL_AGE,
                "object": clean_value(m.group(1)),
                "replace": True,
            }

    # remember that my girlfriend's name is Lara Soares
    m = re.match(r"^remember that my (.+?)s name is (.+)$", t)
    if m:
        relation = clean_text(m.group(1))
        name = clean_value(m.group(2))
        return {
            "action": "store_person_relation",
            "subject": name,
            "relation_value": relation,
        }

    # IMPORTANT: query "who is my X" must come BEFORE "X is my Y"
    m = re.match(r"^who is my (.+)$", t)
    if m:
        return {
            "action": "query_by_relation_value",
            "relation": REL_RELATIONSHIP,
            "object": clean_value(m.group(1)),
        }

    # Lara Soares is my girlfriend
    m = re.match(r"^(.+?) is my (.+)$", t)
    if m:
        name = clean_value(m.group(1))
        relation = clean_text(m.group(2))
        return {
            "action": "store_person_relation",
            "subject": name,
            "relation_value": relation,
        }

    # Lara Soares is 21
    m = re.match(r"^(.+?) is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # Lara Soares age is 21
    m = re.match(r"^(.+?) age is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # her age is 21 / his age is 21
    m = re.match(r"^(her|his|their) age is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": m.group(1),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # she is 21 / he is 21
    m = re.match(r"^(she|he) is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": m.group(1),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # change her age to 22 / update lara age to 22
    m = re.match(r"^(?:change|update) (.+?) age to (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # remember collection
    m = re.match(r"^remember that (.+?) are[, ]+(.+)$", raw_lower)
    if m:
        name = clean_text(m.group(1))
        items = split_values(m.group(2))
        return {
            "action": "set_collection",
            "owner": "user",
            "name": name,
            "items": items,
        }

    m = re.match(r"^remember that (.+?) is[, ]+(.+)$", raw_lower)
    if m:
        name = clean_text(m.group(1))
        item = clean_value(m.group(2))
        return {
            "action": "set_collection",
            "owner": "user",
            "name": name,
            "items": [item],
        }

    # who is x
    m = re.match(r"^who is (.+)$", t)
    if m:
        return {
            "action": "query_entity",
            "subject": clean_value(m.group(1)),
        }

    # age queries
    age_patterns = [
        r"^(?:what is|whats) the age of (.+)$",
        r"^how old is (.+)$",
        r"^(?:what is|whats) (?!my\b)(.+?) age$",
        r"^tell me (.+?) age$",
        r"^tell me the age of (.+)$",
    ]
    for pattern in age_patterns:
        m = re.match(pattern, t)
        if m:
            subject = clean_value(m.group(1))
            if subject == "my":
                subject = "user"
            return {
                "action": "query_fact",
                "subject": subject,
                "relation": REL_AGE,
            }

    m = re.match(r"^(?:what is|whats) (.+?)s age$", t)
    if m:
        return {
            "action": "query_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_AGE,
        }

    # collection query
    for pattern in [
        r"^what are (.+)$",
        r"^tell me (.+)$",
    ]:
        m = re.match(pattern, t)
        if m:
            return {
                "action": "query_collection",
                "owner": "user",
                "name": clean_text(m.group(1)),
            }

    # deletes
    m = re.match(r"^(?:forget|remove|delete) my name$", t)
    if m:
        return {
            "action": "delete_fact",
            "subject": "user",
            "relation": REL_NAME,
        }

    m = re.match(r"^(?:forget|remove|delete) my age$", t)
    if m:
        return {
            "action": "delete_fact",
            "subject": "user",
            "relation": REL_AGE,
        }

    m = re.match(r"^(?:forget|remove|delete) (.+?) age$", t)
    if m:
        subject = clean_value(m.group(1))
        if subject == "my":
            subject = "user"
        return {
            "action": "delete_fact",
            "subject": subject,
            "relation": REL_AGE,
        }

    # delete collection by exact name
    m = re.match(r"^(?:forget|remove|delete) the (.+)$", t)
    if m:
        return {
            "action": "delete_collection",
            "owner": "user",
            "name": clean_text(m.group(1)),
        }

    # delete entity
    m = re.match(r"^(?:forget|remove|delete) (.+)$", t)
    if m:
        return {
            "action": "delete_entity",
            "subject": clean_value(m.group(1)),
        }

    return {"action": "unknown"}