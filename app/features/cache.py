import json
from datetime import datetime, timedelta
from pathlib import Path

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_path(key: str) -> Path:
    safe = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.json"


def read_cache(key: str, max_age_minutes: int = 30):
    path = cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at < timedelta(minutes=max_age_minutes):
            return data["payload"]
    except Exception:
        pass
    return None


def write_cache(key: str, payload):
    path = cache_path(key)
    path.write_text(json.dumps({
        "cached_at": datetime.now().isoformat(),
        "payload":   payload,
    }))