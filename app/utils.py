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
    """
    Clean values without destroying useful symbols like C++, quotes, commands, etc.
    Only removes surrounding whitespace and trailing sentence punctuation.
    """
    text = text.strip()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[?!.,]+$", "", text).strip()
    return text


def split_values(text: str):
    text = text.lower().strip()

    text = text.replace(" and ", ",")
    text = text.replace(";", ",")
    text = text.replace(" ,", ",")
    text = text.replace(", ", ",")

    parts = [clean_value(p) for p in text.split(",")]
    return [p for p in parts if p]