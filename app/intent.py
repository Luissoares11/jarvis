from .utils import clean_text


def detect_intent(text: str) -> str:
    text = clean_text(text)

    if not text:
        return "empty"

    if any(phrase in text for phrase in [
        "what do you know",
        "tell me what you know",
        "list memories",
        "show memories",
        "show what you know",
    ]):
        return "list_memories"

    # typo-tolerant remember
    if "remember" in text or "rembember" in text or "remeber" in text:
        return "remember"

    if text.startswith("replace "):
        return "replace_item"

    if text.startswith("move "):
        return "move_item"

    if any(text.startswith(prefix) for prefix in ["forget ", "delete "]):
        return "delete_topic"

    if any(text.startswith(prefix) for prefix in ["remove ", "delete item "]):
        return "remove_item"

    if (
        any(text.startswith(prefix) for prefix in ["add ", "append "])
        or " add " in f" {text} "
        or text.startswith("and ")
    ):
        return "add"

    if any(word in text for word in [
        "what", "who", "how", "tell", "show", "list", "know", "commands", "name"
    ]):
        return "recall"

    if text.startswith("jarvis "):
        return "system"

    if text.startswith("git ") or text.startswith("npm "):
        return "command"

    # more flexible greetings
    if any(greet in text for greet in ["hello", "hi", "hey"]):
        return "greeting"

    return "unknown"