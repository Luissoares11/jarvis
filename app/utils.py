import re


def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def split_csv_values(raw: str) -> list[str]:
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values