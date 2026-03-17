# ai/memory.py
import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from .utils import clean_text
from random import choice

MEMORY_FILE = "memory.json"

# Load / Save Memory
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(user_memory, f, indent=4)

# -------------------
# Memory + Context
# -------------------
user_memory = load_memory()
context = {"last_topic": None, "last_item": None}

# -------------------
# Embeddings
# -------------------
model = SentenceTransformer('all-MiniLM-L6-v2')
memory_embeddings = {}

def update_embeddings():
    global memory_embeddings
    memory_embeddings = {k: model.encode(k, convert_to_numpy=True) for k in user_memory.keys()}

def find_best_match(query, threshold=0.6):
    if not memory_embeddings:
        return None
    query_vec = model.encode(query, convert_to_numpy=True)
    best_key, best_score = None, 0
    for key, vec in memory_embeddings.items():
        score = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec))
        if score > best_score:
            best_score, best_key = score, key
    return best_key if best_score >= threshold else None

# -------------------
# Personality responses
# -------------------
RESPONSE_TEMPLATES = {
    "confirm": ["Done, sir.", "Got it.", "Consider it handled."],
    "unknown": ["Hmm… I’m not sure about that yet.", "I don’t know about that, sir."],
    "error": ["Something went wrong.", "I couldn’t complete that, sir."]
}

# -------------------
# Memory Operations
# -------------------
def remember(text):
    import re
    patterns = [
        r"remember that (.+?) is (.+)",
        r"remember that (.+?) are (.+)",
        r"remember that (.+?)\s*=\s*(.+)",
        r"remember: (.+?) is (.+)",
        r"remember: (.+?) are (.+)",
        r"remember: (.+?) = (.+)",
        r"remember (.+?) as (.+)",
        r"remember (.+?) -> (.+)",
        r"remember (.+?): (.+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            key = clean_text(match.group(1))
            value = match.group(2)
            values = [v.strip() for v in value.split(",") if v.strip()]
            if key not in user_memory:
                user_memory[key] = []
            for v in values:
                if v not in user_memory[key]:
                    user_memory[key].append(v)
                    context["last_item"] = v
            context["last_topic"] = key
            save_memory()
            update_embeddings()
            return f"{choice(RESPONSE_TEMPLATES['confirm'])} I will remember '{key}'."
    return choice(RESPONSE_TEMPLATES["unknown"])

def recall(query):
    key_clean = clean_text(query)
    if key_clean in user_memory:
        context["last_topic"] = key_clean
        return user_memory[key_clean]
    best_key = find_best_match(key_clean)
    if best_key:
        context["last_topic"] = best_key
        return user_memory[best_key]
    return None

def update_memory(key, new_value):
    key = clean_text(key)
    new_value = new_value.strip()
    if key not in user_memory:
        user_memory[key] = []
    if new_value not in user_memory[key]:
        user_memory[key].append(new_value)
        context["last_item"] = new_value
    context["last_topic"] = key
    save_memory()
    update_embeddings()
    return f"{choice(RESPONSE_TEMPLATES['confirm'])} Updated '{key}'."

def update_last_topic(new_value):
    if not context["last_topic"]:
        return choice(RESPONSE_TEMPLATES["unknown"])
    return update_memory(context["last_topic"], new_value)

def remove_from_last_topic(value):
    if not context["last_topic"]:
        return choice(RESPONSE_TEMPLATES["unknown"])
    value = value.strip()
    if value in user_memory[context["last_topic"]]:
        user_memory[context["last_topic"]].remove(value)
        save_memory()
        update_embeddings()
        return f"{choice(RESPONSE_TEMPLATES['confirm'])} Removed '{value}' from '{context['last_topic']}'."
    return "That item isn't stored."

def delete_memory(key):
    key = clean_text(key)
    if key in user_memory:
        del user_memory[key]
        save_memory()
        update_embeddings()
        return f"{choice(RESPONSE_TEMPLATES['confirm'])} I forgot '{key}'."
    return choice(RESPONSE_TEMPLATES["unknown"])

# Initialize embeddings
update_embeddings()