import re
import unicodedata


def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def clean_value(text: str) -> str:
    text = text.strip()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[?!.,]+$", "", text).strip()
    return text


def split_values(raw: str) -> list[str]:
    raw = raw.strip()
    parts = re.split(r"\s*,\s*|\s+and\s+", raw, flags=re.IGNORECASE)
    return [clean_value(p) for p in parts if clean_value(p)]