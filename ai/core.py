# ai/core.py
import re
from .memory import (
    remember, recall, update_memory, update_last_topic,
    remove_from_last_topic, delete_memory, user_memory
)
from .commands import run_command
from .utils import clean_text

def process_input(user_input):
    text = user_input.strip()
    text_clean = clean_text(text)

    # Teach memory
    if "remember" in text_clean:
        return remember(user_input)

    # List all memory
    if any(phrase in text_clean for phrase in ["what do you know", "tell me what you know", "list memories"]):
        if not user_memory:
            return "I don't know anything yet."
        return "\n".join(f"- {k}" for k in user_memory.keys())

    # Delete memory topic
    match = re.search(r"(?:forget|delete) (.+)", text_clean)
    if match:
        return delete_memory(match.group(1))

    # Remove from last topic
    match = re.search(r"(?:remove) (.+)", text_clean)
    if match:
        return remove_from_last_topic(match.group(1))

    # Add value to explicit key
    match = re.search(r"(?:add|append) (.+?) to (.+)", text_clean)
    if match:
        return update_memory(match.group(2), match.group(1))

    # Add value using last topic
    match = re.search(r"(?:add|append) (.+)", text_clean)
    if match:
        return update_last_topic(match.group(1))

    # Recall memory based on query
    if any(word in text_clean for word in ["what", "who", "how", "tell", "list", "show", "know", "commands"]):
        result = recall(text)
        if result:
            return "\n".join(f"- {item}" for item in result)
        return "I don't know about that yet."

    # Run built-in commands
    cmd_result = run_command(text_clean)
    if cmd_result:
        return cmd_result

    return "I don't know about that yet."