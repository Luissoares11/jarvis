from .commands import run_command
from .logger import log_event
from .memory import (
    add_fact,
    find_facts,
    delete_facts,
    replace_fact,
    dump_subject,
    resolve_and_find,
    list_entities,
    set_collection,
    get_collection,
    list_collections,
    add_collection_item,
    remove_collection_item,
    replace_collection_item,
    delete_collection,
    add_alias,
    get_aliases,
)
from .memory.context import context
from .memory.resolver import resolve_entity, infer_entity_from_relation_target
from .parser import parse_input
from .personality import say
from .relations import REL_NAME, REL_AGE, REL_RELATIONSHIP, relation_display
from .utils import clean_text


def format_fact_list(facts):
    if not facts:
        return say("unknown")
    return "\n".join(f"- {fact['object']}" for fact in facts)


def format_collection(collection):
    if not collection or not collection["items"]:
        return say("unknown")
    return "\n".join(f"- {item}" for item in collection["items"])


def format_entity_profile(entity_name, facts):
    if not facts:
        return say("unknown")

    if entity_name == "user":
        lines = []
        for fact in facts:
            if fact["relation"] == REL_NAME:
                lines.append(f"Your name is {fact['object']}.")
            elif fact["relation"] == REL_AGE:
                lines.append(f"You are {fact['object']} years old.")
            else:
                lines.append(f"- {relation_display(fact['relation'])}: {fact['object']}")
        return "\n".join(lines)

    relationship = None
    age = None
    other = []

    for fact in facts:
        if fact["relation"] == REL_RELATIONSHIP:
            relationship = fact["object"]
        elif fact["relation"] == REL_AGE:
            age = fact["object"]
        else:
            other.append(fact)

    if relationship and age and not other:
        return f"{entity_name} is your {relationship} and is {age} years old."

    lines = [f"{entity_name}:"]
    for fact in facts:
        lines.append(f"- {relation_display(fact['relation'])}: {fact['object']}")
    return "\n".join(lines)


def format_knowledge():
    entities = list_entities()
    user_facts = find_facts(subject="user")
    user_collections = list_collections(owner="user")

    fact_names = []
    for fact in user_facts:
        if fact["relation"] == REL_NAME:
            fact_names.append("my name")
        elif fact["relation"] == REL_AGE:
            fact_names.append("my age")

    collection_names = [c["name"] for c in user_collections]

    items = sorted(set(entities + fact_names + collection_names))

    if not items:
        return "I don't know anything yet, sir."

    return "\n".join(f"- {item}" for item in items)


def format_debug_facts():
    all_facts = find_facts()
    if not all_facts:
        return "No facts stored."

    lines = []
    for fact in all_facts:
        lines.append(f"- {fact['subject']} | {fact['relation']} | {fact['object']}")
    return "\n".join(lines)


def format_debug_collections():
    collections = list_collections()
    if not collections:
        return "No collections stored."

    lines = []
    for collection in collections:
        lines.append(f"- {collection['owner']} | {collection['name']} | {collection['items']}")
    return "\n".join(lines)


def format_debug_aliases():
    aliases = get_aliases()
    if not aliases:
        return "No aliases stored."

    lines = []
    for alias, canonical in aliases.items():
        lines.append(f"- {alias} -> {canonical}")
    return "\n".join(lines)


def format_debug_context():
    lines = []
    for key, value in context.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _position_to_index(position: str, length: int):
    mapping = {
        "first": 0,
        "second": 1,
        "third": 2,
        "last": length - 1,
    }
    return mapping.get(position)


def handle_action(action_data):
    action = action_data["action"]
    context["last_action"] = action

    if action == "empty":
        return say("empty")

    if action == "greeting":
        return say("greeting")

    if action == "debug_command":
        name = action_data["name"]

        if name == "jarvis facts":
            return format_debug_facts()
        if name == "jarvis aliases":
            return format_debug_aliases()
        if name == "jarvis context":
            return format_debug_context()
        if name == "jarvis collections":
            return format_debug_collections()

        return say("unknown")

    if action == "debug_dump_subject":
        subject = resolve_entity(action_data["subject"])
        facts = dump_subject(subject)
        if not facts:
            return "Nothing stored for that subject."
        return format_entity_profile(subject, facts)

    if action == "list_entities":
        entities = list_entities()
        if not entities:
            return "I don't know anyone yet."
        return "\n".join(f"- {entity}" for entity in entities)

    if action == "list_knowledge":
        return format_knowledge()

    if action == "batch_store":
        for item in action_data["items"]:
            handle_action(item)
        return f"{say('confirm')} I will remember that."

    # ---------- FACTS ----------

    if action == "store_fact":
        subject = resolve_entity(action_data["subject"])
        relation = action_data["relation"]
        object_ = action_data["object"]
        replace = action_data.get("replace", False)

        if replace:
            replace_fact(subject, relation, object_)
        else:
            add_fact(subject, relation, object_)

        if subject == "user":
            return f"{say('confirm')} I will remember your {relation_display(relation)}."
        return f"{say('confirm')} I will remember {subject}'s {relation_display(relation)}."

    if action == "store_person_relation":
        subject = clean_text(action_data["subject"])
        relation_value = action_data["relation_value"]

        replace_fact(subject, REL_RELATIONSHIP, relation_value)

        first_name = subject.split()[0]
        add_alias(first_name, subject)
        add_alias(f"my {relation_value}", subject)

        if relation_value == "girlfriend":
            add_alias("my girl", subject)
            add_alias("gf", subject)

        return f"{say('confirm')} I will remember {subject}."

    if action == "query_fact":
        subject = resolve_entity(action_data["subject"])
        relation = action_data["relation"]

        facts = resolve_and_find(subject=subject, relation=relation)

        if not facts:
            if subject == "user" and relation == REL_AGE:
                return "I don't know your age yet."
            if relation == REL_AGE:
                return f"I know who {subject} is, but I don't know their age yet."
            return say("unknown")

        return format_entity_profile(subject, facts)

    if action == "query_entity":
        subject = resolve_entity(action_data["subject"])
        facts = resolve_and_find(subject=subject)

        if not facts:
            return say("unknown")

        return format_entity_profile(subject, facts)

    if action == "query_by_relation_value":
        relation = action_data["relation"]
        object_ = action_data["object"]

        if relation == REL_RELATIONSHIP:
            entity = infer_entity_from_relation_target(object_)
            if entity:
                facts = resolve_and_find(subject=entity)
                return format_entity_profile(entity, facts)

        return say("unknown")

    if action == "delete_fact":
        subject = resolve_entity(action_data["subject"])
        relation = action_data["relation"]

        deleted = delete_facts(subject=subject, relation=relation)

        if not deleted:
            return "I couldn't find that information."

        if subject == "user":
            return f"{say('confirm')} I forgot your {relation_display(relation)}."

        return f"{say('confirm')} I forgot {subject}'s {relation_display(relation)}."

    if action == "delete_entity":
        subject = resolve_entity(action_data["subject"])
        deleted = delete_facts(subject=subject)

        if not deleted:
            return say("unknown")

        return f"{say('confirm')} I forgot '{subject}'."

    # ---------- COLLECTIONS ----------

    if action == "set_collection":
        owner = action_data["owner"]
        name = action_data["name"]
        items = action_data["items"]

        set_collection(owner, name, items)
        return f"{say('confirm')} I will remember '{name}'."

    if action == "query_collection":
        owner = action_data["owner"]
        name = action_data["name"]

        collection = get_collection(owner, name)
        if not collection:
            return say("unknown")

        return format_collection(collection)

    if action == "delete_collection":
        owner = action_data["owner"]
        name = action_data["name"]

        deleted = delete_collection(owner, name)
        if not deleted:
            return say("unknown")

        return f"{say('confirm')} I forgot '{name}'."

    if action == "add_to_last_collection":
        owner = context.get("last_collection_owner")
        name = context.get("last_collection_name")

        if not owner or not name:
            return "I don't know what collection you're referring to."

        add_collection_item(owner, name, action_data["item"])
        return f"{say('confirm')} Added '{action_data['item']}'."

    if action == "replace_in_last_collection":
        owner = context.get("last_collection_owner")
        name = context.get("last_collection_name")

        if not owner or not name:
            return "I don't know what collection you're referring to."

        updated = replace_collection_item(owner, name, action_data["old"], action_data["new"])
        if not updated:
            return "I couldn't find that item."

        return f"{say('confirm')} Replaced '{action_data['old']}' with '{action_data['new']}'."

    if action == "remove_from_last_collection_by_position":
        owner = context.get("last_collection_owner")
        name = context.get("last_collection_name")

        if not owner or not name:
            return "I don't know what collection you're referring to."

        collection = get_collection(owner, name)
        if not collection or not collection["items"]:
            return "There is nothing to remove."

        idx = _position_to_index(action_data["position"], len(collection["items"]))
        if idx is None or idx < 0 or idx >= len(collection["items"]):
            return "That position does not exist."

        removed = remove_collection_item(owner, name, index=idx)
        if removed is None:
            return "That position does not exist."

        return f"{say('confirm')} Removed '{removed}'."

    if action == "unknown":
        raw = action_data.get("raw", "")
        command_response = run_command(clean_text(raw))
        return command_response or say("unknown")

    return say("unknown")


def process_input(user_input: str):
    text = user_input.strip()

    action_data = parse_input(text)
    action_data["raw"] = text

    response = handle_action(action_data)

    log_event("user", user_input)
    log_event("jarvis", response)

    return response