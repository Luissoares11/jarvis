import re
import unicodedata
from difflib import get_close_matches
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/Lisbon"


# ── text helpers ──────────────────────────────────────────────

def clean_text(text: str, math_mode: bool = False) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    if math_mode:
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


def fuzzy_collection_name(name: str, known_names: list[str]) -> str:
    matches = get_close_matches(name, known_names, n=1, cutoff=0.6)
    return matches[0] if matches else name


# ── time helpers ──────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def _parse_datetime(date_str: str, time_str: str = None) -> datetime:
    """Parse flexible date/time strings into a datetime object."""
    date_str = date_str.strip().lower()
    time_str = time_str.strip().lower() if time_str else "09:00"

    now = _now()

    if date_str == "today":
        date = now.date()
    elif date_str == "tomorrow":
        date = (now + timedelta(days=1)).date()
    elif date_str == "next week":
        date = (now + timedelta(weeks=1)).date()
    else:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %B %Y", "%d %b %Y"):
            try:
                date = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"I couldn't understand the date: {date_str}")

    for fmt in ("%H:%M", "%I:%M %p", "%I%p", "%H%M"):
        try:
            t = datetime.strptime(time_str, fmt).time()
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"I couldn't understand the time: {time_str}")

    return datetime.combine(date, t, tzinfo=ZoneInfo(TIMEZONE))