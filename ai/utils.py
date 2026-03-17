# ai/utils.py
import re

def clean_text(text: str) -> str:
    """Normalize text for memory search and comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
    text = re.sub(r"\s+", " ", text)     # normalize spaces
    return text