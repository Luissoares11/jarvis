import json
import re
from difflib import get_close_matches
from dotenv import load_dotenv

load_dotenv()

from .memory.store import (
    db_save_pattern,
    db_get_exact_pattern,
    db_get_all_confirmed_patterns,
    db_confirm_pattern,
    db_delete_pattern,
)
from .memory.context import context


SYSTEM_PROMPT = """You are the intent parser for Jarvis, a personal AI assistant.

Your job is to interpret user input and return a JSON action object.

Available actions and their required fields:

Memory:
{"action": "store_fact", "subject": "user|name", "relation": "name|age|birthday|occupation|location|nationality", "object": "value", "replace": true}
{"action": "query_fact", "subject": "user|name", "relation": "name|age|birthday|occupation|location|nationality"}
{"action": "query_entity", "subject": "name"}
{"action": "delete_fact", "subject": "user|name", "relation": "relation_name"}

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

General:
{"action": "greeting"}
{"action": "unknown"}

Rules:
- Always return valid JSON only. No explanation, no markdown, no extra text.
- For math expressions, preserve all symbols: +, -, *, /, ^, (, ), =
- For plot ranges, support: pi, e, tau, inf and arithmetic like 2*pi
- If you cannot determine the intent, return {"action": "unknown"}
"""


def _call_llm(user_input: str) -> dict:
    """Call Claude Haiku to interpret unknown input."""
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

        # strip markdown code blocks if present
        raw = re.sub(r"```json|```", "", raw).strip()

        return json.loads(raw)
    except Exception as e:
        return {"action": "unknown", "error": str(e)}


def _fuzzy_match(phrase: str, confirmed_patterns: list) -> dict | None:
    """
    Try to find a close match among confirmed patterns.
    Returns the action of the closest match if confidence is high enough.
    """
    known_phrases = [p[0] for p in confirmed_patterns]
    matches = get_close_matches(phrase, known_phrases, n=1, cutoff=0.75)

    if matches:
        matched_phrase = matches[0]
        action = next(a for p, a in confirmed_patterns if p == matched_phrase)
        return action, matched_phrase

    return None, None


_FILLER = re.compile(
    r"^(can you|could you|please|jarvis|hey|would you|i want you to|i need you to)\s+",
    re.IGNORECASE
)

def _strip_filler(text: str) -> str:
    """Remove conversational filler so 'can you plot x' matches 'plot x'."""
    return _FILLER.sub("", text).strip()


def interpret(user_input: str) -> dict:
    phrase = user_input.lower().strip()
    stripped = _strip_filler(phrase)

    # 1 — exact match (try both original and stripped)
    exact = db_get_exact_pattern(phrase) or db_get_exact_pattern(stripped)
    if exact:
        return exact

    # 2 — fuzzy match on stripped phrase
    all_patterns = db_get_all_confirmed_patterns()
    fuzzy_action, matched_phrase = _fuzzy_match(stripped, all_patterns)
    if fuzzy_action:
        action = _call_llm(user_input)
        if action.get("action") != "unknown":
            db_save_pattern(phrase, action, confirmed=True)
            db_save_pattern(stripped, action, confirmed=True)
            return action

    # 3 — LLM fallback with confirmation
    action = _call_llm(user_input)

    if action.get("action") != "unknown":
        db_save_pattern(phrase, action, confirmed=False)
        db_save_pattern(stripped, action, confirmed=False)
        context["pending_learning"] = {
            "phrase": phrase,
            "action": action,
        }
        action["_needs_confirmation"] = True

    return action

def confirm_learning():
    """User confirmed — store the pending pattern permanently."""
    pending = context.get("pending_learning")
    if not pending:
        return False
    db_confirm_pattern(pending["phrase"])
    context["pending_learning"] = None
    return True


def reject_learning():
    """User rejected — delete the pending pattern."""
    pending = context.get("pending_learning")
    if not pending:
        return False
    db_delete_pattern(pending["phrase"])
    context["pending_learning"] = None
    return True


def has_pending_learning():
    return bool(context.get("pending_learning"))