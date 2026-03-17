from .utils import clean_text
from .semantic import find_best_topic
from .memory import get_topic
from .commands import handle_add, handle_remove

def process_input(user_input: str) -> str:
    text = clean_text(user_input)

    # ADD
    if "add" in text:
        parts = text.split("add")[-1].strip()
        topic = find_best_topic(parts) or "general"
        return handle_add(topic, parts)

    # REMOVE
    if "remove" in text:
        parts = text.split("remove")[-1].strip()
        topic = find_best_topic(parts)

        if topic:
            return handle_remove(topic, parts)

    # LIST
    if "what do you know" in text or "tell me" in text:
        topic = find_best_topic(text)

        if topic:
            items = get_topic(topic)
            if items:
                return "\n".join([f"- {i}" for i in items])

    return "I don't know about that yet."