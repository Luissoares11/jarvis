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
{"action": "store_person_relation", "subject": "name", "relation_value": "girlfriend|boyfriend|brother|..."}
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
{"action": "compute_plot", "expr": "expression", "x_min": "-10", "x_max": "10"}
{"action": "compute_plot_implicit", "expr": "expression in x and y", "x_min": "-2", "x_max": "2", "y_min": "-2", "y_max": "2"}

External data:
{"action": "external_weather", "location": "city name", "days": 1}
{"action": "external_fixtures", "league": "league name", "count": 5}
{"action": "external_results", "league": "league name", "count": 5}
{"action": "external_standings", "league": "league name"}

Actions:
{"action": "action_add_todo", "task": "task description"}
{"action": "action_list_todos"}
{"action": "action_complete_todo", "ref": "task name or number"}
{"action": "action_delete_todo", "ref": "task name or number"}
{"action": "action_add_reminder", "message": "reminder text", "time": "HH:MM", "date": "today|tomorrow|DD/MM/YYYY"}
{"action": "action_list_reminders"}
{"action": "action_set_timer", "duration": "10 minutes", "label": "optional label"}
{"action": "action_set_alarm", "time": "07:30"}
{"action": "action_add_event", "title": "descriptive event title extracted from input", "event_type": "exam|appointment|anniversary|birthday|meeting|deadline|alarm|other", "date": "DD/MM/YYYY or today or tomorrow", "time": "HH:MM in 24h format, default 09:00 if not specified", "notes": "optional"}
{"action": "action_delete_event", "title": "event title to delete"}
{"action": "action_list_events", "days": 7}

General:
{"action": "greeting"}
{"action": "social"}
{"action": "unknown"}

Rules:
- Always return valid JSON only. No explanation, no markdown, no extra text.
- For math expressions, preserve all symbols: +, -, *, /, ^, (, ), =
- For plot ranges, support: pi, e, tau, inf and arithmetic like 2*pi
- Dates must always be returned as DD/MM/YYYY format.
- Times must always be returned as HH:MM (24h) format.
- If the user says "today", "tomorrow", use those words as-is for the date field.
- If you cannot determine the intent, return {"action": "unknown"}
- For weather: if the user says "forecast", "next N days", or "this week", set days=5. If just "weather" or "what's it like", set days=1.
- For events, extract a meaningful title from the input. "I have a birthday tomorrow" → title="Birthday", but "comunhão Duarte" → title="Comunhão Duarte". Never use just the event type as the title.
- If no time is specified for an event, default to 09:00.
- If no date is given for an event, return {"action": "unknown"} — do not guess.
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
    """Send raw input to Claude Haiku and get back an action dict."""
    try:
        import anthropic
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_input}]
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
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
    """
    Resolve user input to an action dict.

    Order:
      1. Hardcoded social/greeting check (free, instant)
      2. Exact cache hit (free, instant)
      3. Fuzzy cache hit (free, instant)
      4. LLM call (paid, ~300ms) → auto-cache on success
    """
    phrase = user_input.lower().strip()

    # 1 — hardcoded fast path
    hardcoded = _check_hardcoded(phrase)
    if hardcoded:
        return hardcoded

    # 2 — exact cache hit
    exact = db_get_exact_pattern(phrase)
    if exact:
        return exact

    # 3 — fuzzy cache hit
    all_patterns = db_get_all_confirmed_patterns()
    fuzzy = _fuzzy_match(phrase, all_patterns)
    if fuzzy:
        # still run LLM to extract fresh parameters (dates, names, etc.)
        # but use fuzzy hit as a confidence signal — if LLM agrees, cache it
        action = _call_llm(user_input)
        if action.get("action") not in ("unknown", None):
            db_save_pattern(phrase, action, confirmed=True)
        return action

    # 4 — LLM fallback, auto-cache on success
    action = _call_llm(user_input)

    if action.get("action") not in ("unknown", None):
        db_save_pattern(phrase, action, confirmed=True)

    return action