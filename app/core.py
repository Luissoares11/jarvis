import re

from .commands import run_command
from .intent import detect_intent
from .logger import log_event
from .memory import (
    remember,
    recall_topic,
    recall_profile,
    update_memory,
    update_last_topic,
    remove_from_last_topic,
    delete_memory,
    list_memories,
    system_status,
    get_item_from_last_topic,
    replace_in_last_topic,
    move_in_last_topic,
    delete_profile_field,
    infer_profile_update,
    list_profiles,
)
from .personality import say
from .utils import clean_text


def format_items(items):
    if not items:
        return say("unknown")
    return "\n".join(f"- {item}" for item in items)


def format_profile(profile_result):
    if profile_result["type"] == "profile_name":
        return f"- {profile_result['name']}"

    if profile_result["type"] == "profile":
        lines = [f"{profile_result['name']}:"]
        for key, value in profile_result["fields"].items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    if profile_result["type"] == "profile_missing_field":
        return f"I know who {profile_result['name']} is, but I don't know their {profile_result['field']} yet."

    if profile_result["type"] == "ambiguous_profile":
        lines = ["I know more than one match:"]
        for match in profile_result["matches"]:
            lines.append(f"- {match}")
        return "\n".join(lines)

    return say("unknown")


def handle_system_command(text_clean: str):
    if text_clean == "jarvis status":
        status = system_status()
        return (
            f"Topics: {status['topics']}\n"
            f"Profiles: {status['profiles']}\n"
            f"Aliases: {status['aliases']}\n"
            f"Items: {status['items']}\n"
            f"Last topic: {status['last_topic']}\n"
            f"Last item: {status['last_item']}\n"
            f"Last intent: {status['last_intent']}\n"
            f"Last profile: {status['last_profile']}"
        )

    if text_clean == "jarvis memory":
        memories = list_memories()
        if not memories:
            return "I don't know anything yet, sir."
        return "\n".join(f"- {m}" for m in memories)

    if text_clean in ["what do you know", "what do you know?"]:
        memories = list_memories()
        if not memories:
            return "I don't know anything yet, sir."
        return "\n".join(f"- {m}" for m in memories)

    if text_clean in ["who do you know", "who do you know?"]:
        profiles = list_profiles()
        if not profiles:
            return "I don't know anyone yet."
        return "\n".join(f"- {p}" for p in profiles)

    return None


def process_input(user_input: str):
    text = user_input.strip()
    text_clean = clean_text(text)

    if not text_clean:
        response = say("empty")
        log_event("user", user_input)
        log_event("jarvis", response)
        return response

    # 🔥 direct system command handling first
    system_response = handle_system_command(text_clean)
    if system_response:
        log_event("user", user_input)
        log_event("jarvis", system_response)
        return system_response

    intent = detect_intent(text_clean)

    if intent == "greeting":
        response = say("greeting")

    elif intent == "remember":
        response = remember(text) or say("unknown")

    elif intent == "list_memories":
        memories = list_memories()
        response = "\n".join(f"- {m}" for m in memories) if memories else "I don't know anything yet, sir."

    elif intent == "delete_topic":
        match_field = re.search(
            r"(?:forget|delete) (.+?) (age|name|relationship)",
            text,
            re.IGNORECASE
        )

        if match_field:
            name = match_field.group(1)
            field = match_field.group(2)

            result = delete_profile_field(name, field)

            if result:
                response = f"{say('confirm')} I forgot {result}'s {field}."
            else:
                response = "I couldn't find that information."

        else:
            match = re.search(r"(?:forget|delete) (.+)", text, re.IGNORECASE)
            response = delete_memory(match.group(1)) if match else say("unknown")

    elif intent == "remove_item":
        match = re.search(r"(?:remove|delete item) (.+)", text, re.IGNORECASE)
        if match:
            target = match.group(1).strip()

            profile_result = recall_profile(target)
            if profile_result and profile_result["type"] in ["profile", "profile_name"]:
                response = delete_memory(profile_result["name"])
            else:
                topic_result = recall_topic(target)
                if topic_result and topic_result["mode"] in ["topic_exact", "topic_fuzzy", "topic_semantic"]:
                    response = delete_memory(topic_result["topic"])
                else:
                    response = remove_from_last_topic(target)
        else:
            response = say("unknown")

    elif intent == "replace_item":
        match = re.search(r"replace (.+?) with (.+)", text, re.IGNORECASE)
        response = replace_in_last_topic(match.group(1), match.group(2)) if match else say("unknown")

    elif intent == "move_item":
        match = re.search(r"move (.+?) to (.+)", text, re.IGNORECASE)
        response = move_in_last_topic(match.group(1), match.group(2)) if match else say("unknown")

    elif intent == "add":
        match = re.search(r"(?:add|append) (.+?) to (.+)", text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            key = match.group(2).strip()
            response = update_memory(key, value)
        else:
            match = re.search(r"(?:add|append) (.+)", text, re.IGNORECASE)
            if match:
                response = update_last_topic(match.group(1).strip())
            elif text.strip().lower().startswith("and "):
                response = update_last_topic(text.strip()[4:].strip())
            else:
                response = say("unknown")

    elif intent == "recall":
        if text_clean in ["who am i", "whats my name", "what is my name", "do you know who am i", "do you know who i am"]:
            result = recall_topic("my name")
            response = format_items(result["values"]) if result else say("unknown")
        else:
            profile_result = recall_profile(text)
            if profile_result:
                response = format_profile(profile_result)
            else:
                match = re.search(r"what is (.+)", text, re.IGNORECASE)
                if match and any(word in text_clean for word in [
                    "first", "second", "third", "fourth", "forth", "fifth", "last"
                ]):
                    item, error = get_item_from_last_topic(match.group(1))
                    response = item if not error else error
                else:
                    result = recall_topic(text)
                    response = format_items(result["values"]) if result else say("unknown")

    elif intent == "system":
        response = handle_system_command(text_clean) or say("unknown")

    elif intent == "command":
        response = run_command(text_clean) or say("unknown")

    else:
        remembered = remember(text)
        if remembered:
            response = remembered
        else:
            inferred = infer_profile_update(text)
            if inferred:
                response = inferred
            else:
                profile_result = recall_profile(text)
                if profile_result:
                    response = format_profile(profile_result)
                else:
                    result = recall_topic(text)
                    if result:
                        response = format_items(result["values"])
                    else:
                        response = say("unknown")

    log_event("user", user_input)
    log_event("jarvis", response)
    return response