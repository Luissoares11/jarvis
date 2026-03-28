import re

from .utils import clean_text, clean_value, split_values
from .relations import (
    REL_NAME, REL_AGE, REL_RELATIONSHIP, REL_BIRTHDAY,
    REL_OCCUPATION, REL_LOCATION, REL_NATIONALITY, REL_NICKNAME
)

RELATION_MAP = {
    "name":        REL_NAME,
    "age":         REL_AGE,
    "birthday":    REL_BIRTHDAY,
    "occupation":  REL_OCCUPATION,
    "job":         REL_OCCUPATION,
    "location":    REL_LOCATION,
    "nationality": REL_NATIONALITY,
    "nickname":    REL_NICKNAME,
}


def parse_input(text: str):
    raw = text.strip()
    raw_lower = raw.lower().strip()
    t = clean_text(raw)

    if not t:
        return {"action": "empty"}

    # ── conflict confirmation ────────────────────────────────

    if t in ["yes", "yeah", "yep", "correct", "confirm", "sure", "do it", "update it"]:
        return {"action": "confirm_conflict"}

    if t in ["no", "nope", "nah", "cancel", "keep it", "dont", "don't", "leave it"]:
        return {"action": "reject_conflict"}

    # ── debug ────────────────────────────────────────────────

    if t in ["jarvis facts", "jarvis aliases", "jarvis context", "jarvis collections"]:
        return {"action": "debug_command", "name": t}

    m = re.match(r"^jarvis dump (.+)$", t)
    if m:
        return {"action": "debug_dump_subject", "subject": clean_value(m.group(1))}

    # ── multi-fact ───────────────────────────────────────────

    if " and " in t:
        parts = [p.strip() for p in t.split(" and ")]
        parsed = [parse_input(p) for p in parts]
        if all(p.get("action") == "store_fact" for p in parsed):
            return {"action": "batch_store", "items": parsed}

    # ── greeting ─────────────────────────────────────────────

    if re.fullmatch(r"(hello|hi|hey|yo)", t):
        return {"action": "greeting"}

    # ── knowledge ────────────────────────────────────────────

    if t in ["who do you know", "who do you know?"]:
        return {"action": "list_entities"}

    if t in [
        "what do you know",
        "what do you know?",
        "tell me what do you know",
        "tell me what you know",
    ]:
        return {"action": "list_knowledge"}

    # ── self queries ─────────────────────────────────────────

    if t in ["who am i", "who am i?", "what is my name", "whats my name"]:
        return {"action": "query_fact", "subject": "user", "relation": REL_NAME}

    if t in ["how old am i", "tell me my age", "what is my age", "whats my age", "do you know my age"]:
        return {"action": "query_fact", "subject": "user", "relation": REL_AGE}

    if t in ["what do i do", "what is my job", "what is my occupation"]:
        return {"action": "query_fact", "subject": "user", "relation": REL_OCCUPATION}

    if t in ["where do i live", "where am i from", "whats my location"]:
        return {"action": "query_fact", "subject": "user", "relation": REL_LOCATION}

    if t in ["when is my birthday", "whats my birthday"]:
        return {"action": "query_fact", "subject": "user", "relation": REL_BIRTHDAY}

    # ── collection positional delete ─────────────────────────

    m = re.match(r"^(?:remove|delete) (?:the )?(first|second|third|last)$", t)
    if m:
        return {
            "action": "remove_from_last_collection_by_position",
            "position": m.group(1),
        }

    # ── collection replace ───────────────────────────────────

    m = re.match(r"^replace (.+?) with (.+)$", t)
    if m:
        return {
            "action": "replace_in_last_collection",
            "old": clean_value(m.group(1)),
            "new": clean_value(m.group(2)),
        }

    # ── collection add ───────────────────────────────────────

    m = re.match(r"^(?:add|append) (.+)$", t)
    if m:
        return {
            "action": "add_to_last_collection",
            "item": clean_value(m.group(1)),
        }

    # ── self name ────────────────────────────────────────────

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

    # ── self age ─────────────────────────────────────────────

    for pattern in [
        r"^i am (\d+)\s+years?\s+old$",
        r"^im (\d+)\s+years?\s+old$",
        r"^my age is (\d+)$",
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

    # ── self occupation ──────────────────────────────────────

    for pattern in [
        r"^i work as (?:a |an )?(.+)$",
        r"^my occupation is (.+)$",
        r"^my job is (.+)$",
    ]:
        m = re.match(pattern, t)
        if m:
            return {
                "action": "store_fact",
                "subject": "user",
                "relation": REL_OCCUPATION,
                "object": clean_value(m.group(1)),
                "replace": True,
            }

    # ── self location ────────────────────────────────────────

    for pattern in [
        r"^i live in (.+)$",
        r"^my location is (.+)$",
    ]:
        m = re.match(pattern, t)
        if m:
            return {
                "action": "store_fact",
                "subject": "user",
                "relation": REL_LOCATION,
                "object": clean_value(m.group(1)),
                "replace": True,
            }

    # ── self birthday ────────────────────────────────────────

    m = re.match(r"^my birthday is (.+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": "user",
            "relation": REL_BIRTHDAY,
            "object": clean_value(m.group(1)),
            "replace": True,
        }

    # ── generic "change my X to Y" ───────────────────────────

    m = re.match(r"^(?:change|update) my (.+?) to (.+)$", t)
    if m:
        relation_str = clean_text(m.group(1))
        value = clean_value(m.group(2))
        relation = RELATION_MAP.get(relation_str)
        if relation:
            return {
                "action": "store_fact",
                "subject": "user",
                "relation": relation,
                "object": value,
                "replace": True,
            }

    # ── generic "change X's Y to Z" ──────────────────────────

    m = re.match(r"^(?:change|update) (.+?)s? (.+?) to (.+)$", t)
    if m:
        subject = clean_value(m.group(1))
        relation_str = clean_text(m.group(2))
        value = clean_value(m.group(3))
        relation = RELATION_MAP.get(relation_str)
        if relation:
            return {
                "action": "store_fact",
                "subject": subject,
                "relation": relation,
                "object": value,
                "replace": True,
            }

    # ── remember that my X's name is Y ──────────────────────

    m = re.match(r"^remember that my (.+?)s name is (.+)$", t)
    if m:
        relation = clean_text(m.group(1))
        name = clean_value(m.group(2))
        return {
            "action": "store_person_relation",
            "subject": name,
            "relation_value": relation,
        }

    # ── IMPORTANT: "who is my X" before "X is my Y" ─────────

    m = re.match(r"^who is my (.+)$", t)
    if m:
        return {
            "action": "query_by_relation_value",
            "relation": REL_RELATIONSHIP,
            "object": clean_value(m.group(1)),
        }

    # ── X is my girlfriend ───────────────────────────────────

    m = re.match(r"^(.+?) is my (.+)$", t)
    if m:
        name = clean_value(m.group(1))
        relation = clean_text(m.group(2))
        return {
            "action": "store_person_relation",
            "subject": name,
            "relation_value": relation,
        }

    # ── X is 21 ─────────────────────────────────────────────

    m = re.match(r"^(.+?) is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── X age is 21 ─────────────────────────────────────────

    m = re.match(r"^(.+?) age is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── her/his age is 21 ────────────────────────────────────

    m = re.match(r"^(her|his|their) age is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": m.group(1),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── she/he is 21 ─────────────────────────────────────────

    m = re.match(r"^(she|he) is (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": m.group(1),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── change her age to 22 ─────────────────────────────────

    m = re.match(r"^(?:change|update) (.+?) age to (\d+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_AGE,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── X works as Y ─────────────────────────────────────────

    m = re.match(r"^(.+?) works as (?:a |an )?(.+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_OCCUPATION,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── X lives in Y ─────────────────────────────────────────

    m = re.match(r"^(.+?) lives in (.+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_LOCATION,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── X's birthday is Y ────────────────────────────────────

    m = re.match(r"^(.+?)s? birthday is (.+)$", t)
    if m:
        return {
            "action": "store_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_BIRTHDAY,
            "object": clean_value(m.group(2)),
            "replace": True,
        }

    # ── remember collections ─────────────────────────────────

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

    # ── who is X ─────────────────────────────────────────────

    m = re.match(r"^who is (.+)$", t)
    if m:
        return {
            "action": "query_entity",
            "subject": clean_value(m.group(1)),
        }

    # ── age queries ──────────────────────────────────────────

    for pattern in [
        r"^(?:what is|whats) the age of (.+)$",
        r"^how old is (.+)$",
        r"^(?:what is|whats) (?!my\b)(.+?) age$",
        r"^tell me (.+?) age$",
        r"^tell me the age of (.+)$",
    ]:
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

    # ── birthday queries ─────────────────────────────────────

    m = re.match(r"^when is (.+?)s? birthday\??$", t)
    if m:
        return {
            "action": "query_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_BIRTHDAY,
        }

    # ── occupation queries ───────────────────────────────────

    m = re.match(r"^what does (.+?) do\??$", t)
    if m:
        return {
            "action": "query_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_OCCUPATION,
        }

    # ── location queries ─────────────────────────────────────

    m = re.match(r"^where does (.+?) live\??$", t)
    if m:
        return {
            "action": "query_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_LOCATION,
        }

    m = re.match(r"^where is (.+?) from\??$", t)
    if m:
        return {
            "action": "query_fact",
            "subject": clean_value(m.group(1)),
            "relation": REL_NATIONALITY,
        }

    # ── collection queries ───────────────────────────────────

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

    # ── deletes ──────────────────────────────────────────────

    m = re.match(r"^(?:forget|remove|delete) my name$", t)
    if m:
        return {"action": "delete_fact", "subject": "user", "relation": REL_NAME}

    m = re.match(r"^(?:forget|remove|delete) my age$", t)
    if m:
        return {"action": "delete_fact", "subject": "user", "relation": REL_AGE}

    m = re.match(r"^(?:forget|remove|delete) my birthday$", t)
    if m:
        return {"action": "delete_fact", "subject": "user", "relation": REL_BIRTHDAY}

    m = re.match(r"^(?:forget|remove|delete) my occupation$", t)
    if m:
        return {"action": "delete_fact", "subject": "user", "relation": REL_OCCUPATION}

    m = re.match(r"^(?:forget|remove|delete) my location$", t)
    if m:
        return {"action": "delete_fact", "subject": "user", "relation": REL_LOCATION}

    m = re.match(r"^(?:forget|remove|delete) (.+?) age$", t)
    if m:
        subject = clean_value(m.group(1))
        if subject == "my":
            subject = "user"
        return {"action": "delete_fact", "subject": subject, "relation": REL_AGE}

    m = re.match(r"^(?:forget|remove|delete) the (.+)$", t)
    if m:
        return {
            "action": "delete_collection",
            "owner": "user",
            "name": clean_text(m.group(1)),
        }

    m = re.match(r"^(?:forget|remove|delete) (.+)$", t)
    if m:
        return {
            "action": "delete_entity",
            "subject": clean_value(m.group(1)),
        }

    return {"action": "unknown"}