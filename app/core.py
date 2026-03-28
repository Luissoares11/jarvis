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
from .memory.resolver import resolve_entity, infer_entity_from_relation_target, push_entity
from .parser import parse_input
from .personality import say
from .relations import REL_NAME, REL_AGE, REL_RELATIONSHIP, relation_display
from .semantic import normalize, fuzzy_collection_name
from .utils import clean_text, title_name


# ── formatters ───────────────────────────────────────────────

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
    
    display_name = title_name(entity_name)
    
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
        return f"{display_name} is your {relationship} and is {age} years old."

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
    return "\n".join(f"- {f['subject']} | {f['relation']} | {f['object']}" for f in all_facts)


def format_debug_collections():
    collections = list_collections()
    if not collections:
        return "No collections stored."
    return "\n".join(f"- {c['owner']} | {c['name']} | {c['items']}" for c in collections)


def format_debug_aliases():
    aliases = get_aliases()
    if not aliases:
        return "No aliases stored."
    return "\n".join(f"- {alias} -> {canonical}" for alias, canonical in aliases.items())


def format_debug_context():
    return "\n".join(f"- {key}: {value}" for key, value in context.items())


def _position_to_index(position: str, length: int):
    mapping = {"first": 0, "second": 1, "third": 2, "last": length - 1}
    return mapping.get(position)


# ── handlers ─────────────────────────────────────────────────

def _handle_empty(a):
    return say("empty")

def _handle_greeting(a):
    return say("greeting")

def _handle_debug_command(a):
    name = a["name"]
    if name == "jarvis facts":       return format_debug_facts()
    if name == "jarvis aliases":     return format_debug_aliases()
    if name == "jarvis context":     return format_debug_context()
    if name == "jarvis collections": return format_debug_collections()
    return say("unknown")

def _handle_debug_dump_subject(a):
    subject = resolve_entity(a["subject"])
    facts = dump_subject(subject)
    if not facts:
        return "Nothing stored for that subject."
    return format_entity_profile(subject, facts)

def _handle_list_entities(a):
    entities = list_entities()
    if not entities:
        return "I don't know anyone yet."
    return "\n".join(f"- {entity}" for entity in entities)

def _handle_list_knowledge(a):
    return format_knowledge()

def _handle_batch_store(a):
    for item in a["items"]:
        handle_action(item)
    return f"{say('confirm')} I will remember that."

def _handle_store_fact(a):
    subject = resolve_entity(a["subject"])
    relation = a["relation"]
    object_ = a["object"]
    replace = a.get("replace", False)

    if replace:
        replace_fact(subject, relation, object_)
    else:
        add_fact(subject, relation, object_)

    if subject == "user":
        return f"{say('confirm')} I will remember your {relation_display(relation)}."
    return f"{say('confirm')} I will remember {subject}'s {relation_display(relation)}."

def _handle_store_person_relation(a):
    subject = clean_text(a["subject"])
    relation_value = a["relation_value"]

    replace_fact(subject, REL_RELATIONSHIP, relation_value)

    first_name = subject.split()[0]
    add_alias(first_name, subject)
    add_alias(f"my {relation_value}", subject)

    if relation_value == "girlfriend":
        add_alias("my girl", subject)
        add_alias("gf", subject)

    return f"{say('confirm')} I will remember {subject}."

def _handle_query_entity(a):
    subject = resolve_entity(a["subject"])
    facts = resolve_and_find(subject=subject)

    if not facts:
        return say("unknown")

    push_entity(subject)
    context["last_entity_facts"] = facts
    context["last_question_type"] = "who"
    return format_entity_profile(subject, facts)

def _handle_query_fact(a):
    subject = resolve_entity(a["subject"])
    relation = a["relation"]

    facts = resolve_and_find(subject=subject, relation=relation)

    if not facts:
        if subject == "user" and relation == REL_AGE:
            return "I don't know your age yet."
        if relation == REL_AGE:
            return f"I know who {subject} is, but I don't know their age yet."
        return say("unknown")

    if subject != "user":
        push_entity(subject)

    context["last_question_type"] = "age" if relation == REL_AGE else None

    # clean age response instead of falling into generic profile format
    if relation == REL_AGE:
        age = facts[0]["object"]
        if subject == "user":
            return f"You are {age} years old."
        return f"{subject.title()} is {age} years old."

    return format_entity_profile(subject, facts)

def _handle_query_by_relation_value(a):
    relation = a["relation"]
    object_ = a["object"]

    if relation == REL_RELATIONSHIP:
        entity = infer_entity_from_relation_target(object_)
        if entity:
            facts = resolve_and_find(subject=entity)
            return format_entity_profile(entity, facts)

    return say("unknown")

def _handle_delete_fact(a):
    subject = resolve_entity(a["subject"])
    relation = a["relation"]
    deleted = delete_facts(subject=subject, relation=relation)

    if not deleted:
        return "I couldn't find that information."

    if subject == "user":
        return f"{say('confirm')} I forgot your {relation_display(relation)}."
    return f"{say('confirm')} I forgot {subject}'s {relation_display(relation)}."

def _handle_delete_entity(a):
    subject = resolve_entity(a["subject"])
    deleted = delete_facts(subject=subject)

    if not deleted:
        return say("unknown")

    return f"{say('confirm')} I forgot '{subject}'."

def _handle_set_collection(a):
    set_collection(a["owner"], a["name"], a["items"])
    return f"{say('confirm')} I will remember '{a['name']}'."

def _handle_query_collection(a):
    owner = a["owner"]
    name = a["name"]

    known = [c["name"] for c in list_collections(owner=owner)]
    name = fuzzy_collection_name(name, known)

    collection = get_collection(owner, name)
    if not collection:
        return say("unknown")

    return format_collection(collection)

def _handle_delete_collection(a):
    deleted = delete_collection(a["owner"], a["name"])
    if not deleted:
        return say("unknown")
    return f"{say('confirm')} I forgot '{a['name']}'."

def _handle_add_to_last_collection(a):
    owner = context.get("last_collection_owner")
    name = context.get("last_collection_name")

    if not owner or not name:
        return "I don't know what collection you're referring to."

    add_collection_item(owner, name, a["item"])
    return f"{say('confirm')} Added '{a['item']}'."

def _handle_replace_in_last_collection(a):
    owner = context.get("last_collection_owner")
    name = context.get("last_collection_name")

    if not owner or not name:
        return "I don't know what collection you're referring to."

    updated = replace_collection_item(owner, name, a["old"], a["new"])
    if not updated:
        return "I couldn't find that item."

    return f"{say('confirm')} Replaced '{a['old']}' with '{a['new']}'."

def _handle_remove_from_last_collection_by_position(a):
    owner = context.get("last_collection_owner")
    name = context.get("last_collection_name")

    if not owner or not name:
        return "I don't know what collection you're referring to."

    collection = get_collection(owner, name)
    if not collection or not collection["items"]:
        return "There is nothing to remove."

    idx = _position_to_index(a["position"], len(collection["items"]))
    if idx is None or idx < 0 or idx >= len(collection["items"]):
        return "That position does not exist."

    removed = remove_collection_item(owner, name, index=idx)
    if removed is None:
        return "That position does not exist."

    return f"{say('confirm')} Removed '{removed}'."

def _handle_unknown(a):
    raw = a.get("raw", "")
    command_response = run_command(clean_text(raw))
    return command_response or say("unknown")


# ── registry ─────────────────────────────────────────────────

_HANDLERS = {
    "empty":                                    _handle_empty,
    "greeting":                                 _handle_greeting,
    "debug_command":                            _handle_debug_command,
    "debug_dump_subject":                       _handle_debug_dump_subject,
    "list_entities":                            _handle_list_entities,
    "list_knowledge":                           _handle_list_knowledge,
    "batch_store":                              _handle_batch_store,
    "store_fact":                               _handle_store_fact,
    "store_person_relation":                    _handle_store_person_relation,
    "query_fact":                               _handle_query_fact,
    "query_entity":                             _handle_query_entity,
    "query_by_relation_value":                  _handle_query_by_relation_value,
    "delete_fact":                              _handle_delete_fact,
    "delete_entity":                            _handle_delete_entity,
    "set_collection":                           _handle_set_collection,
    "query_collection":                         _handle_query_collection,
    "delete_collection":                        _handle_delete_collection,
    "add_to_last_collection":                   _handle_add_to_last_collection,
    "replace_in_last_collection":               _handle_replace_in_last_collection,
    "remove_from_last_collection_by_position":  _handle_remove_from_last_collection_by_position,
    "unknown":                                  _handle_unknown,
}


# ── dispatch ─────────────────────────────────────────────────

def handle_action(action_data: dict) -> str:
    action = action_data.get("action", "unknown")
    context["last_action"] = action

    handler = _HANDLERS.get(action, _handle_unknown)
    return handler(action_data)


# ── entry point ──────────────────────────────────────────────

def process_input(user_input: str) -> str:
    text = normalize(user_input.strip())

    action_data = parse_input(text)
    action_data["raw"] = user_input

    response = handle_action(action_data)

    log_event("user", user_input)
    log_event("jarvis", response)

    return response