from .utils import clean_text


def detect_intent(text: str):
    text = text.lower().strip()

    if any(greet in text for greet in ["hello", "hi", "hey", "yo"]):
        return "greeting"

    if any(word in text for word in ["remember", "remmeber", "remeber", "rember"]):
        return "remember"

    if text in [
        "what do you know",
        "what do you know?",
        "who do you know",
        "who do you know?",
        "jarvis status",
        "jarvis memory",
    ]:
        return "system"

    if any(text.startswith(x) for x in ["forget ", "delete "]):
        return "delete_topic"

    if any(text.startswith(x) for x in ["remove ", "delete item "]):
        return "remove_item"

    if text.startswith("replace "):
        return "replace_item"

    if text.startswith("move "):
        return "move_item"

    if text.startswith("add ") or text.startswith("append ") or text.startswith("and "):
        return "add"

    recall_starters = [
        "what is",
        "whats",
        "who is",
        "tell me",
        "what are",
        "what do",
        "how old",
        "do you know",
        "who am i",
    ]
    if any(text.startswith(x) for x in recall_starters):
        return "recall"

    cmd_starters = ["time", "open google", "open youtube"]
    if any(text.startswith(x) for x in cmd_starters):
        return "command"

    return "unknown"