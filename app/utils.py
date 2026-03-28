import re
import unicodedata


def clean_text(text: str, math_mode: bool = False) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    if math_mode:
        # preserve math symbols — only strip punctuation that has no math meaning
        text = re.sub(r"[^\w\s\+\-\*\/\^\(\)\=\.\,]", "", text)
    else:
        text = re.sub(r"[^\w\s]", "", text)

    text = re.sub(r"\s+", " ", text)
    return text


def clean_value(text: str) -> str:
    text = text.strip()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[?!.,]+$", "", text).strip()
    return text


def split_values(text: str):
    text = text.lower().strip()
    text = text.replace(" and ", ",")
    text = text.replace(";", ",")
    parts = [p.strip() for p in text.split(",") if p.strip()]

    result = []
    seen = set()
    for part in parts:
        value = clean_value(part)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def title_name(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split())