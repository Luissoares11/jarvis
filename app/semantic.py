from difflib import get_close_matches
from .memory import load_memory

def find_best_topic(query):
    memory = load_memory()
    topics = list(memory.keys())

    match = get_close_matches(query, topics, n=1, cutoff=0.4)
    return match[0] if match else None