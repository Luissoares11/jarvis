import re

from .commands import run_command
from .memory import (
    remember,
    recall,
    update_memory,
    update_last_topic,
    remove_from_last_topic,
    delete_memory,
    list_memories,
    user_memory,
)
from .personality import say
from .utils import clean_text


def format_memory_items(items):
    if not items:
        return say("unknown")
    return "\n".join(f"- {item}" for item in items)


def process_input(user_input: str):
    text = user_input.strip()
    text_clean = clean_text(text)

    if not text_clean:
        return "Awaiting your input, sir."

    # personality / greetings
    if text_clean in ["hello", "hi", "hey", "hello jarvis", "hey jarvis"]:
        return "Hello, sir."

    # teach memory
    if "remember" in text_clean:
        return remember(text)

    # list all memory topics
    if any(phrase in text_clean for phrase in [
        "what do you know",
        "tell me what you know",
        "list memories",
        "show memories",
    ]):
        memories = list_memories()
        if not memories:
            return "I don't know anything yet, sir."
        return "\n".join(f"- {k}" for k in memories)

    # delete full topic
    match = re.search(r"(?:forget|delete) (.+)", text_clean)
    if match and "remove " not in text_clean:
        return delete_memory(match.group(1))

    # remove from current topic
    match = re.search(r"(?:remove) (.+)", text_clean)
    if match:
        return remove_from_last_topic(match.group(1))

    # add to explicit topic
    match = re.search(r"(?:add|append) (.+?) to (.+)", text_clean)
    if match:
        value = match.group(1).strip()
        key = match.group(2).strip()
        return update_memory(key, value)

    # add to last topic
    match = re.search(r"(?:add|append) (.+)", text_clean)
    if match:
        return update_last_topic(match.group(1).strip())

    # recall
    if any(word in text_clean for word in [
        "what", "who", "how", "tell", "list", "show", "know", "commands", "name"
    ]):
        result = recall(text)
        if result:
            return format_memory_items(result)
        return say("unknown")

    # built-in commands
    command_result = run_command(text_clean)
    if command_result:
        return command_result

    # fallback: maybe semantic recall anyway
    result = recall(text)
    if result:
        return format_memory_items(result)

    return say("unknown")