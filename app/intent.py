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

    if "remember" in text:
        return "remember"

    if any(text.startswith(prefix) for prefix in ["forget ", "delete "]):
        return "delete_topic"

    if any(text.startswith(prefix) for prefix in ["remove ", "delete item "]):
        return "remove_item"

    if " add " in f" {text} " or text.startswith("add ") or text.startswith("append "):
        return "add"

    if any(word in text for word in [
        "what", "who", "how", "tell", "show", "list", "know", "commands", "name"
    ]):
        return "recall"

    if text.startswith("jarvis "):
        return "system"

    if text.startswith("git ") or text.startswith("npm "):
        return "command"

    if text in ["hello", "hi", "hey", "hello jarvis", "hey jarvis"]:
        return "greeting"

    return "unknown"