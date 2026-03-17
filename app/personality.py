from random import choice

RESPONSE_TEMPLATES = {
    "confirm": [
        "Done, sir.",
        "Got it.",
        "Consider it handled."
    ],
    "unknown": [
        "Hmm… I’m not sure about that yet.",
        "I don’t know about that, sir."
    ],
    "error": [
        "Something went wrong.",
        "I couldn’t complete that, sir."
    ]
}

def say(kind: str) -> str:
    return choice(RESPONSE_TEMPLATES.get(kind, ["..."]))