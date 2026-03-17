import re

def clean_text(text: str) -> str:
    """Normalize text for comparisons and semantic lookup."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text