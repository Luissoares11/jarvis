import re

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
from .reasoning import (
    check_conflict,
    store_pending_conflict,
    resolve_pending_conflict,
    has_pending_conflict,
    infer_implicit_facts,
    resolve_transitive,
)
from .llm import interpret
from .memory.context import make_context
from .memory.resolver import resolve_entity, infer_entity_from_relation_target, push_entity
from .personality import say
from .relations import (
    REL_NAME, REL_AGE, REL_RELATIONSHIP, REL_BIRTHDAY,
    REL_OCCUPATION, REL_LOCATION, REL_NATIONALITY, REL_NICKNAME,
    relation_display,
)
from .utils import clean_text, title_name, fuzzy_collection_name
from .compute import (
    calculate, differentiate, integrate,
    limit, solve_equation, convert_units, plot_function, plot_implicit,
)
from .actions import set_timer, set_alarm, add_reminder, list_reminders, _timer_threads
from .features import (
    get_weather,
    get_fixtures, get_results, get_standings,
    add_task_to_board, list_tasks_on_board, complete_task_on_board, delete_task_on_board,
    add_event, delete_event, edit_event, list_events,
)
from .features.tasks import add_board, list_boards, find_board_by_name, delete_board


# ── formatters ────────────────────────────────────────────────

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
            elif fact["relation"] == REL_BIRTHDAY:
                lines.append(f"Your birthday is {fact['object']}.")
            elif fact["relation"] == REL_OCCUPATION:
                lines.append(f"You are a {fact['object']}.")
            elif fact["relation"] == REL_LOCATION:
                lines.append(f"You live in {fact['object']}.")
            elif fact["relation"] == REL_NATIONALITY:
                lines.append(f"You are from {fact['object']}.")
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

    lines = [f"{display_name}:"]
    for fact in facts:
        lines.append(f"  - {relation_display(fact['relation'])}: {fact['object']}")
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


def format_debug_facts(ctx):
    all_facts = find_facts()
    if not all_facts:
        return "No facts stored."
    return "\n".join(
        f"- {f['subject']} | {f['relation']} | {f['object']}" for f in all_facts
    )


def format_debug_learned(ctx):
    from .memory.store import db_get_all_confirmed_patterns
    patterns = db_get_all_confirmed_patterns()
    if not patterns:
        return "I haven't learned anything yet."
    return "\n".join(f"- \"{p}\" → {a.get('action')}" for p, a in patterns)


def format_debug_collections(ctx):
    collections = list_collections()
    if not collections:
        return "No collections stored."
    return "\n".join(
        f"- {c['owner']} | {c['name']} | {c['items']}" for c in collections
    )


def format_debug_history(ctx):
    from .memory.store import _conn
    with _conn() as con:
        rows = con.execute(
            "SELECT input, result, created_at FROM computations "
            "ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    if not rows:
        return "No computation history yet."
    return "\n".join(
        f"- [{r['created_at'][:16]}] {r['input']} → {r['result']}" for r in rows
    )


def format_debug_aliases(ctx):
    aliases = get_aliases()
    if not aliases:
        return "No aliases stored."
    return "\n".join(f"- {alias} -> {canonical}" for alias, canonical in aliases.items())


def format_debug_context(ctx):
    return "\n".join(f"- {key}: {value}" for key, value in ctx.items())


def _position_to_index(position: str, length: int):
    mapping = {"first": 0, "second": 1, "third": 2, "last": length - 1}
    return mapping.get(position)


# ── handlers ──────────────────────────────────────────────────

def _handle_empty(a, ctx):
    return say("empty")


def _handle_greeting(a, ctx):
    return say("greeting")


def _handle_social(a, ctx):
    return say("social")


def _handle_farewell(a, ctx):
    return say("farewell")


def _handle_debug_command(a, ctx):
    name = a["name"]
    if name == "jarvis facts":       return format_debug_facts(ctx)
    if name == "jarvis aliases":     return format_debug_aliases(ctx)
    if name == "jarvis context":     return format_debug_context(ctx)
    if name == "jarvis collections": return format_debug_collections(ctx)
    if name == "jarvis learned":     return format_debug_learned(ctx)
    if name == "jarvis history":     return format_debug_history(ctx)
    return say("unknown")


def _handle_debug_dump_subject(a, ctx):
    subject = resolve_entity(a["subject"])
    facts = dump_subject(subject)
    if not facts:
        return "Nothing stored for that subject."
    return format_entity_profile(subject, facts)


def _handle_list_entities(a, ctx):
    entities = list_entities()
    if not entities:
        return "I don't know anyone yet."
    return "\n".join(f"- {entity}" for entity in entities)


def _handle_list_knowledge(a, ctx):
    return format_knowledge()


def _handle_batch_store(a, ctx):
    for item in a["items"]:
        handle_action(item, ctx)
    return f"{say('confirm')} I will remember that."


def _handle_store_fact(a, ctx):
    subject  = resolve_entity(a["subject"])
    relation = a["relation"]
    object_  = a["object"]
    replace  = a.get("replace", False)

    if replace:
        conflict = check_conflict(subject, relation, object_)
        if conflict:
            store_pending_conflict(subject, relation, object_, conflict["object"])
            ctx["pending_conflict"] = {
                "subject":  subject,
                "relation": relation,
                "new":      object_,
                "existing": conflict["object"],
            }
            name = "your" if subject == "user" else subject.title() + "'s"
            return (
                f"I already have {name} {relation} as '{conflict['object']}'. "
                f"Do you want me to update it to '{object_}'?"
            )

    if replace:
        replace_fact(subject, relation, object_)
    else:
        add_fact(subject, relation, object_)

    inferred = infer_implicit_facts(subject, relation, object_)
    note = ""
    for inf in inferred:
        if inf["type"] == "implicit_relationship_age":
            note = f" I also know they are {inf['object']} years old."

    if subject == "user":
        return f"{say('confirm')} I will remember your {relation_display(relation)}.{note}"
    return f"{say('confirm')} I will remember {subject.title()}'s {relation_display(relation)}.{note}"


def _handle_store_person_relation(a, ctx):
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


def _handle_query_fact(a, ctx):
    subject  = resolve_entity(a["subject"])
    relation = a["relation"]

    facts = resolve_and_find(subject=subject, relation=relation)

    if not facts:
        transitive = resolve_transitive(subject, relation)
        if transitive:
            age  = transitive["facts"][0]["object"]
            real = transitive["subject"].title()
            via  = transitive["via"]
            return f"{real} ({via}) is {age} years old."

    if not facts:
        if subject == "user" and relation == REL_AGE:
            return "I don't know your age yet."
        if relation == REL_AGE:
            return f"I know who {subject} is, but I don't know their age yet."
        return say("unknown")

    if subject != "user":
        push_entity(subject)

    ctx["last_question_type"] = "age" if relation == REL_AGE else None

    if relation == REL_AGE:
        age = facts[0]["object"]
        if subject == "user":
            return f"You are {age} years old."
        return f"{subject.title()} is {age} years old."

    return format_entity_profile(subject, facts)


def _handle_query_entity(a, ctx):
    subject = resolve_entity(a["subject"])
    facts   = resolve_and_find(subject=subject)

    if not facts:
        return say("unknown")

    push_entity(subject)
    ctx["last_entity_facts"]  = facts
    ctx["last_question_type"] = "who"
    return format_entity_profile(subject, facts)


def _handle_query_by_relation_value(a, ctx):
    relation = a["relation"]
    object_  = a["object"]

    if relation == REL_RELATIONSHIP:
        entity = infer_entity_from_relation_target(object_)
        if entity:
            facts = resolve_and_find(subject=entity)
            return format_entity_profile(entity, facts)

    return say("unknown")


def _handle_delete_fact(a, ctx):
    subject  = resolve_entity(a["subject"])
    relation = a["relation"]
    deleted  = delete_facts(subject=subject, relation=relation)

    if not deleted:
        return "I couldn't find that information."

    if subject == "user":
        return f"{say('confirm')} I forgot your {relation_display(relation)}."
    return f"{say('confirm')} I forgot {subject}'s {relation_display(relation)}."


def _handle_delete_entity(a, ctx):
    subject = resolve_entity(a["subject"])
    deleted = delete_facts(subject=subject)

    if not deleted:
        return say("unknown")

    return f"{say('confirm')} I forgot '{subject}'."


def _handle_set_collection(a, ctx):
    set_collection(a["owner"], a["name"], a["items"])
    ctx["last_collection_owner"] = a["owner"]
    ctx["last_collection_name"]  = a["name"]
    return f"{say('confirm')} I will remember '{a['name']}'."


def _handle_query_collection(a, ctx):
    owner = a["owner"]
    name  = a["name"]

    known = [c["name"] for c in list_collections(owner=owner)]
    name  = fuzzy_collection_name(name, known)

    collection = get_collection(owner, name)
    if not collection:
        return say("not_found")

    ctx["last_collection_owner"] = owner
    ctx["last_collection_name"]  = name
    return format_collection(collection)


def _handle_delete_collection(a, ctx):
    deleted = delete_collection(a["owner"], a["name"])
    if not deleted:
        return say("unknown")
    return f"{say('confirm')} I forgot '{a['name']}'."


def _handle_add_to_last_collection(a, ctx):
    owner = ctx.get("last_collection_owner")
    name  = ctx.get("last_collection_name")

    if not owner or not name:
        return "I don't know what collection you're referring to."

    add_collection_item(owner, name, a["item"])
    return f"{say('confirm')} Added '{a['item']}'."


def _handle_replace_in_last_collection(a, ctx):
    owner = ctx.get("last_collection_owner")
    name  = ctx.get("last_collection_name")

    if not owner or not name:
        return "I don't know what collection you're referring to."

    updated = replace_collection_item(owner, name, a["old"], a["new"])
    if not updated:
        return "I couldn't find that item."

    return f"{say('confirm')} Replaced '{a['old']}' with '{a['new']}'."


def _handle_remove_from_last_collection_by_position(a, ctx):
    owner = ctx.get("last_collection_owner")
    name  = ctx.get("last_collection_name")

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


def _handle_confirm_conflict(a, ctx):
    pending = ctx.get("pending_conflict")
    if pending:
        replace_fact(pending["subject"], pending["relation"], pending["new"])
        ctx["pending_conflict"] = None
        return f"{say('confirm')} Updated."
    return say("unknown")


def _handle_reject_conflict(a, ctx):
    if ctx.get("pending_conflict"):
        ctx["pending_conflict"] = None
        return f"{say('confirm')} Keeping the existing value."
    return say("unknown")


def _handle_compute_calculate(a, ctx):
    return calculate(a["expr"])


def _handle_compute_derivative(a, ctx):
    return differentiate(a["expr"], a.get("var", "x"), a.get("order", 1))


def _handle_compute_integral(a, ctx):
    return integrate(a["expr"], a.get("var", "x"), a.get("lower"), a.get("upper"))


def _handle_compute_limit(a, ctx):
    return limit(a["expr"], a.get("var", "x"), a.get("point", "0"), a.get("direction", "+"))


def _handle_compute_solve(a, ctx):
    return solve_equation(a["expr"], a.get("var", "x"))


def _handle_compute_convert(a, ctx):
    return convert_units(a["value"], a["from_unit"], a["to_unit"])


def _handle_compute_plot(a, ctx):
    return plot_function(a["expr"], x_min=a.get("x_min", "-10"), x_max=a.get("x_max", "10"))


def _handle_compute_plot_implicit(a, ctx):
    x_range = (float(a.get("x_min", -2)), float(a.get("x_max", 2)))
    y_range = (float(a.get("y_min", -2)), float(a.get("y_max", 2)))
    return plot_implicit(a["expr"], x_range=x_range, y_range=y_range)


def _handle_external_weather(a, ctx):
    return get_weather(a["location"], forecast_days=a.get("days", 1))


def _handle_external_fixtures(a, ctx):
    return get_fixtures(a["league"], next_n=a.get("count", 5))


def _handle_external_results(a, ctx):
    return get_results(a["league"], last_n=a.get("count", 5))


def _handle_external_standings(a, ctx):
    return get_standings(a["league"])


def _handle_action_add_board(a, ctx):
    board = add_board(a["title"].strip())
    return f"Created board: '{board['title']}'."


def _handle_action_list_boards(a, ctx):
    boards = list_boards()
    if not boards:
        return "You don't have any boards yet."
    lines = ["Your boards:"]
    for b in boards:
        lines.append(f"  • {b['title']}")
    return "\n".join(lines)


def _handle_action_delete_board(a, ctx):
    board = find_board_by_name(a["title"])
    if not board:
        return f"I couldn't find a '{a['title']}' board."
    delete_board(board["id"])
    return f"Deleted board '{board['title']}' and all its tasks."


def _handle_action_add_task(a, ctx):
    return add_task_to_board(a["board"], a["task"], due_time=a.get("time"))


def _handle_action_list_tasks(a, ctx):
    return list_tasks_on_board(a["board"])


def _handle_action_complete_task(a, ctx):
    return complete_task_on_board(a["board"], a["ref"])


def _handle_action_delete_task(a, ctx):
    return delete_task_on_board(a["board"], a["ref"])


def _handle_action_set_timer(a, ctx):
    return set_timer(a["duration"], a.get("label", "Timer"))


def _handle_action_set_alarm(a, ctx):
    return set_alarm(a["time"])


def _handle_action_add_event(a, ctx):
    return add_event(
        title=a.get("title", a.get("event_type", "Event")),
        date_str=a["date"],
        time_str=a.get("time", "09:00"),
        event_type=a.get("event_type", "other"),
        notes=a.get("notes", ""),
    )


def _handle_action_delete_event(a, ctx):
    return delete_event(a.get("title", ""))


def _handle_action_edit_event(a, ctx):
    return edit_event(
        title=a.get("title", ""),
        new_title=a.get("new_title"),
        new_date_str=a.get("new_date"),
        new_time_str=a.get("new_time"),
        new_notes=a.get("new_notes"),
        new_type=a.get("new_type"),
    )


def _handle_action_list_events(a, ctx):
    return list_events(
        days_ahead=a.get("days", 30),
        include_past=a.get("include_past", False),
        all_events=a.get("all_events", False),
    )


def _handle_unknown(a, ctx):
    raw = a.get("raw", "")
    command_response = run_command(clean_text(raw))
    if command_response:
        return command_response
    return say("unknown")


# ── registry ──────────────────────────────────────────────────

_HANDLERS = {
    "empty":                                    _handle_empty,
    "greeting":                                 _handle_greeting,
    "social":                                   _handle_social,
    "farewell":                                 _handle_farewell,
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
    "confirm_conflict":                         _handle_confirm_conflict,
    "reject_conflict":                          _handle_reject_conflict,
    "compute_calculate":                        _handle_compute_calculate,
    "compute_derivative":                       _handle_compute_derivative,
    "compute_integral":                         _handle_compute_integral,
    "compute_limit":                            _handle_compute_limit,
    "compute_solve":                            _handle_compute_solve,
    "compute_convert":                          _handle_compute_convert,
    "compute_plot":                             _handle_compute_plot,
    "compute_plot_implicit":                    _handle_compute_plot_implicit,
    "external_weather":                         _handle_external_weather,
    "external_fixtures":                        _handle_external_fixtures,
    "external_results":                         _handle_external_results,
    "external_standings":                       _handle_external_standings,
    "action_add_board":                         _handle_action_add_board,
    "action_list_boards":                       _handle_action_list_boards,
    "action_delete_board":                      _handle_action_delete_board,
    "action_add_task":                          _handle_action_add_task,
    "action_list_tasks":                        _handle_action_list_tasks,
    "action_complete_task":                     _handle_action_complete_task,
    "action_delete_task":                       _handle_action_delete_task,
    "action_set_timer":                         _handle_action_set_timer,
    "action_set_alarm":                         _handle_action_set_alarm,
    "action_add_event":                         _handle_action_add_event,
    "action_list_events":                       _handle_action_list_events,
    "action_delete_event":                      _handle_action_delete_event,
    "action_edit_event":                        _handle_action_edit_event,
}


# ── dispatch ──────────────────────────────────────────────────

def handle_action(action_data: dict, ctx: dict) -> str:
    action = action_data.get("action", "unknown")
    ctx["last_action"] = action

    handler = _HANDLERS.get(action, _handle_unknown)
    return handler(action_data, ctx)


# ── entry point ───────────────────────────────────────────────

def process_input(user_input: str, ctx: dict = None) -> str:
    if ctx is None:
        ctx = make_context()

    raw = user_input.strip()

    if not raw:
        return handle_action({"action": "empty"}, ctx)

    _debug_commands = {
        "jarvis facts", "jarvis aliases", "jarvis context",
        "jarvis collections", "jarvis learned", "jarvis history",
    }
    if raw.lower() in _debug_commands:
        return handle_action({"action": "debug_command", "name": raw.lower()}, ctx)

    m = re.match(r"^jarvis dump (.+)$", raw.lower())
    if m:
        return handle_action({"action": "debug_dump_subject", "subject": m.group(1).strip()}, ctx)

    if ctx.get("pending_conflict"):
        t = raw.lower().strip()
        if t in {"yes", "yeah", "yep", "correct", "confirm", "sure", "do it", "update it"}:
            return handle_action({"action": "confirm_conflict"}, ctx)
        if t in {"no", "nope", "nah", "cancel", "keep it", "leave it"}:
            return handle_action({"action": "reject_conflict"}, ctx)

    action_data = interpret(raw)
    action_data["raw"] = raw

    response = handle_action(action_data, ctx)

    log_event("user", raw)
    log_event("jarvis", response)

    return response