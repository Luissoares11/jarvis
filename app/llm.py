import json
import re
from difflib import get_close_matches
from dotenv import load_dotenv

load_dotenv()

from .memory.store import (
    db_save_pattern,
    db_get_exact_pattern,
    db_get_all_confirmed_patterns,
)


SYSTEM_PROMPT = """You are the intent parser for Jarvis, a personal AI assistant.

Your job is to interpret user input and return a JSON action object.

Available actions and their required fields:

Memory:
{"action": "store_fact", "subject": "user|name", "relation": "name|age|birthday|occupation|location|nationality", "object": "value", "replace": true}
{"action": "query_fact", "subject": "user|name", "relation": "name|age|birthday|occupation|location|nationality"}
{"action": "query_entity", "subject": "name"}
{"action": "delete_fact", "subject": "user|name", "relation": "relation_name"}
{"action": "store_person_relation", "subject": "name", "relation_value": "girlfriend|boyfriend|brother|sister|friend|partner"}
{"action": "query_by_relation_value", "relation": "relationship", "object": "girlfriend|..."}
{"action": "list_entities"}
{"action": "list_knowledge"}
{"action": "set_collection", "owner": "user", "name": "collection name", "items": ["item1", "item2"]}
{"action": "query_collection", "owner": "user", "name": "collection name"}
{"action": "delete_collection", "owner": "user", "name": "collection name"}
{"action": "add_to_last_collection", "item": "new item"}
{"action": "remove_from_last_collection_by_position", "position": "first|second|third|last"}
{"action": "replace_in_last_collection", "old": "old item", "new": "new item"}
{"action": "delete_entity", "subject": "name"}
{"action": "batch_store", "items": [{"action": "store_fact", ...}, ...]}

Computation:
{"action": "compute_calculate", "expr": "math expression"}
{"action": "compute_derivative", "expr": "expression", "var": "x", "order": 1}
{"action": "compute_integral", "expr": "expression", "var": "x", "lower": null, "upper": null}
{"action": "compute_limit", "expr": "expression", "var": "x", "point": "0", "direction": "+"}
{"action": "compute_solve", "expr": "equation or expression", "var": "x"}
{"action": "compute_convert", "value": 100, "from_unit": "km", "to_unit": "miles"}
{"action": "compute_plot", "expr": "expression", "var": "x", "x_min": "-10", "x_max": "10"}
{"action": "compute_plot_implicit", "expr": "expression in x and y already rewritten as lhs - (rhs)", "x_min": "-2", "x_max": "2", "y_min": "-2", "y_max": "2"}

External data:
{"action": "external_weather", "location": "city name", "days": 1}
{"action": "external_fixtures", "league": "league name", "count": 5}
{"action": "external_results", "league": "league name", "count": 5}
{"action": "external_standings", "league": "league name"}

Boards & tasks:
{"action": "action_add_board", "title": "board title"}
{"action": "action_list_boards"}
{"action": "action_delete_board", "title": "board title"}
{"action": "action_add_task", "board": "board name", "task": "task description", "time": "HH:MM in 24h format, omit field entirely if no time mentioned"}
{"action": "action_list_tasks", "board": "board name"}
{"action": "action_complete_task", "board": "board name", "ref": "task name"}
{"action": "action_delete_task", "board": "board name", "ref": "task name"}

Timers & alarms:
{"action": "action_set_timer", "duration": "10 minutes", "label": "optional label"}
{"action": "action_set_alarm", "time": "07:30"}

Calendar:
{"action": "action_add_event", "title": "descriptive event title extracted from input", "event_type": "exam|appointment|anniversary|birthday|meeting|deadline|alarm|other", "date": "DD/MM/YYYY or today or tomorrow", "time": "HH:MM in 24h format, default 09:00 if not specified", "notes": "optional"}
{"action": "action_delete_event", "title": "event title to delete"}
{"action": "action_edit_event", "title": "existing event title", "new_title": "optional", "new_date": "optional DD/MM/YYYY", "new_time": "optional HH:MM", "new_notes": "optional"}
{"action": "action_list_events", "days": 30}
{"action": "action_list_events", "days": 0, "include_past": true}
{"action": "action_list_events", "all_events": true}

General:
{"action": "greeting"}
{"action": "social"}
{"action": "farewell"}
{"action": "unknown"}

---

Math expression rules:
- Always convert ^ to ** (e.g. x^2 → x**2)
- Always expand implicit multiplication (e.g. 2x → 2*x, xy → x*y, 3sin(x) → 3*sin(x))
- For implicit plots, rewrite "f(x,y) = g(x,y)" as "(f(x,y)) - (g(x,y))" in the expr field
- For solve, rewrite "lhs = rhs" as "lhs - (rhs)" in the expr field
- For derivatives, always include the var field — infer it from the expression if not stated
- For integrals, always include the var field — default to x if not stated
- For limits, always include the point field — default to 0 if not stated
- For unit conversions, normalize unit names: kilometres → km, metres → m, celsius → c, fahrenheit → f, pounds → lbs
- For plot ranges, keep as expressions — pi, 2*pi, e are valid
- If the expression contains log, assume natural log (ln) unless the user specifies otherwise
- If the expression is ambiguous or unparseable, return {"action": "unknown"}

Weather rules:
- If the user does not mention a location, default location to "Castelo de Paiva".
- If the user says "forecast", "next N days", or "this week", set days=5. Otherwise set days=1.

Task/board rules:
- Tasks always belong to a board. Extract the board name from phrases like "on my X board", "for X", "to the X tasks/list", "in X".
- If the user wants to add a task but gives no board at all, return {"action": "unknown"} — do not guess a board.
- Treat "todo", "to-do", and "task" as the same thing — always use the action_*_task action names regardless of which word the user uses.
- Extract the board name as literally as the user said it (preserve capitalization and wording) — do not normalize, pluralize, or singularize it. The backend handles matching.
- For action_add_task: only include the "time" field if the user actually mentioned a time. Never invent or default a time.
- For action_complete_task / action_delete_task: "ref" should be the task text as closely as the user said it, not the board name.

Calendar rules:
- For events (exam, meeting, etc.): if no date is given, return {"action": "unknown"} — do not guess.
- For events, extract a meaningful title from the input. Never use just the event type as the title.

Memory vs. action disambiguation:
- "Remember that X" (a statement of fact, no time attached) is always a memory store, e.g. "remember that my sister's birthday is in June" → store_fact, not an event.
- If input names a specific date/time AND an action to take, it's an action (event or task) — not memory.
- If input describes a static fact about a person or the user with no date/time/action attached, it's memory.

General rules:
- Always return valid JSON only. No explanation, no markdown, no extra text.
- If the user greets in Portuguese (e.g. "olá", "bom dia"), respond with {"action": "greeting"}
- If the user says "obrigado" or "obrigada", respond with {"action": "social"}
- For alarms: if a time is given but no date, default date to "today"

---

Examples:

Input: "what's the weather like"
Output: {"action": "external_weather", "location": "Castelo de Paiva", "days": 1}

Input: "weather forecast for this week in Porto"
Output: {"action": "external_weather", "location": "Porto", "days": 5}

Input: "add buy milk to my groceries board"
Output: {"action": "action_add_task", "board": "groceries", "task": "buy milk"}

Input: "add finish the report to Work at 14:00"
Output: {"action": "action_add_task", "board": "Work", "task": "finish the report", "time": "14:00"}

Input: "add a task: water the plants"
Output: {"action": "unknown"}
(No board was named — never guess one.)

Input: "show me my todos on the Jarvis board"
Output: {"action": "action_list_tasks", "board": "Jarvis"}

Input: "mark buy milk as done on groceries"
Output: {"action": "action_complete_task", "board": "groceries", "ref": "buy milk"}

Input: "remember that my sister's birthday is in June"
Output: {"action": "store_fact", "subject": "sister", "relation": "birthday", "object": "June", "replace": true}

Input: "I have an exam next Tuesday"
Output: {"action": "unknown"}
(An event type and rough timeframe were given but no concrete date — do not guess a specific date from "next Tuesday".)

Input: "exam on 14/07/2026 called Physics Final"
Output: {"action": "action_add_event", "title": "Physics Final", "event_type": "exam", "date": "14/07/2026", "time": "09:00"}

Input: "olá jarvis"
Output: {"action": "greeting"}
"""

# ── fast-path: social/greeting inputs that never need the LLM ──

_GREETINGS = {
    "hello", "hi", "hey", "yo", "sup", "wassup",
}

_SOCIAL = {
    "how are you", "how are you?", "how are u", "how r u",
    "what's up", "whats up", "not bad", "fine thanks",
    "doing well", "all good",
}

_FAREWELLS = {
    "bye", "goodbye", "see you", "later", "cya",
}

_TIME_OF_DAY = {
    "good morning", "good afternoon", "good evening",
    "good night", "morning", "evening",
}


def _check_hardcoded(text: str) -> dict | None:
    """Return an action for simple social inputs without calling the LLM."""
    t = text.lower().strip().rstrip("?!")
    if t in _GREETINGS or t in _TIME_OF_DAY:
        return {"action": "greeting"}
    if t in _SOCIAL:
        return {"action": "social"}
    if t in _FAREWELLS:
        return {"action": "farewell"}
    return None


# ── LLM call ──────────────────────────────────────────────────

def _call_llm(user_input: str) -> dict:
    try:
        import anthropic
        import re
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_input}]
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()


        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)

        return json.loads(raw)

    except Exception as e:
        return {"action": "unknown", "error": str(e)}


# ── pattern cache ─────────────────────────────────────────────

def _fuzzy_match(phrase: str, confirmed_patterns: list) -> dict | None:
    """Find a close match among confirmed cached patterns."""
    known_phrases = [p[0] for p in confirmed_patterns]
    matches = get_close_matches(phrase, known_phrases, n=1, cutoff=0.82)

    if matches:
        matched_phrase = matches[0]
        action = next(a for p, a in confirmed_patterns if p == matched_phrase)
        return action

    return None


# ── main entry point ──────────────────────────────────────────

def interpret(user_input: str) -> dict:
    phrase = user_input.lower().strip()

    hardcoded = _check_hardcoded(phrase)
    if hardcoded:
        return hardcoded

    exact = db_get_exact_pattern(phrase)
    if exact:
        return exact

    all_patterns = db_get_all_confirmed_patterns()
    fuzzy = _fuzzy_match(phrase, all_patterns)
    if fuzzy:
        action = _call_llm(user_input)
        if action.get("action") not in ("unknown", None):
            db_save_pattern(phrase, action, confirmed=True)
        return action

    action = _call_llm(user_input)

    if action.get("action") not in ("unknown", None):
        db_save_pattern(phrase, action, confirmed=True)

    return action