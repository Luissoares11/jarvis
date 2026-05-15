from random import choice
from datetime import datetime


def _time_of_day() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


RESPONSE_TEMPLATES = {
    "confirm": [
        "Done, sir.",
        "Got it.",
        "Consider it handled.",
        "Right away.",
        "Noted.",
    ],
    "unknown": [
        "Hmm… I'm not sure about that yet.",
        "I don't know about that, sir.",
        "I don't have that information.",
        "That's outside my knowledge at the moment, sir.",
    ],
    "error": [
        "Something went wrong.",
        "I couldn't complete that, sir.",
        "I ran into a problem with that.",
    ],
    "greeting": [
        "Hello, sir.",
        "At your service.",
        "Good to see you, sir.",
        "Good {time}, sir.",
        "Online and ready, sir.",
    ],
    "empty": [
        "Awaiting your input, sir.",
        "Ready when you are, sir.",
    ],
    "social": [
        "All systems operational, sir.",
        "Running at full capacity.",
        "Never better, sir.",
        "Fully operational and at your service.",
        "Everything is running smoothly.",
    ],
    "farewell": [
        "Goodbye, sir.",
        "Until next time, sir.",
        "Signing off.",
        "Standby mode activated.",
    ],
    "thinking": [
        "Let me check that for you, sir.",
        "One moment, sir.",
        "On it.",
    ],
    "not_found": [
        "I couldn't find that, sir.",
        "Nothing on record for that.",
        "I don't have that stored.",
    ],
    "conflict": [
        "I already have a different value for that, sir.",
        "That conflicts with what I know.",
    ],
    "learned": [
        "Got it, I'll remember that.",
        "Noted for future reference, sir.",
        "I've added that to my knowledge.",
    ],
}


def say(kind: str) -> str:
    templates = RESPONSE_TEMPLATES.get(kind, ["..."])
    chosen = choice(templates)
    # resolve dynamic placeholders
    if "{time}" in chosen:
        chosen = chosen.replace("{time}", _time_of_day())
    return chosen