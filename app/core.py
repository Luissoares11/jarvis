import re

from .commands import run_command
from .intent import detect_intent
from .logger import log_event
from .memory import (
    remember,
    recall_topic,
    update_memory,
    update_last_topic,
    remove_from_last_topic,
    delete_memory,
    list_memories,
    system_status,
)
from .personality import say
from .utils import clean_text


def format_items(items):
    if not items:
        return say("unknown")
    return "\n".join(f"- {item}" for item in items)


def handle_system_command(text_clean: str):
    if text_clean == "jarvis status":
        status = system_status()
        return (
            f"Topics: {status['topics']}\n"
            f"Items: {status['items']}\n"
            f"Last topic: {status['last_topic']}\n"
            f"Last item: {status['last_item']}\n"
            f"Last intent: {status['last_intent']}"
        )

    if text_clean == "jarvis memory":
        memories = list_memories()
        if not memories:
            return "I don't know anything yet, sir."
        return "\n".join(f"- {m}" for m in memories)

    return say("unknown")


def process_input(user_input: str):
    text = user_input.strip()
    text_clean = clean_text(text)

    if not text_clean:
        response = say("empty")
        log_event("user", user_input)
        log_event("jarvis", response)
        return response

    intent = detect_intent(text_clean)

    if intent == "greeting":
        response = say("greeting")

    elif intent == "remember":
        response = remember(text)

    elif intent == "list_memories":
        memories = list_memories()
        response = "\n".join(f"- {m}" for m in memories) if memories else "I don't know anything yet, sir."

    elif intent == "delete_topic":
        match = re.search(r"(?:forget|delete) (.+)", text_clean)
        response = delete_memory(match.group(1)) if match else say("unknown")

    elif intent == "remove_item":
        match = re.search(r"(?:remove|delete item) (.+)", text_clean)
        response = remove_from_last_topic(match.group(1)) if match else say("unknown")

    elif intent == "add":
        match = re.search(r"(?:add|append) (.+?) to (.+)", text_clean)
        if match:
            value = match.group(1).strip()
            key = match.group(2).strip()
            response = update_memory(key, value)
        else:
            match = re.search(r"(?:add|append) (.+)", text_clean)
            response = update_last_topic(match.group(1).strip()) if match else say("unknown")

    elif intent == "recall":
        result = recall_topic(text)
        if result:
            response = format_items(result["values"])
        else:
            response = say("unknown")

    elif intent == "system":
        response = handle_system_command(text_clean)

    elif intent == "command":
        response = run_command(text_clean) or say("unknown")

    else:
        # final semantic attempt
        result = recall_topic(text)
        if result:
            response = format_items(result["values"])
        else:
            response = say("unknown")

    log_event("user", user_input)
    log_event("jarvis", response)
    return response