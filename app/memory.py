import json
import os
from config import MEMORY_PATH

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {}

    with open(MEMORY_PATH, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_PATH, "w") as f:
        json.dump(memory, f, indent=4)

def add_item(topic, item):
    memory = load_memory()
    memory.setdefault(topic, [])

    if item not in memory[topic]:
        memory[topic].append(item)

    save_memory(memory)

def remove_item(topic, item):
    memory = load_memory()

    if topic in memory and item in memory[topic]:
        memory[topic].remove(item)
        save_memory(memory)
        return True

    return False

def get_topic(topic):
    memory = load_memory()
    return memory.get(topic, [])