import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path

from config import RAPIDAPI_KEY

# ── simple file cache ─────────────────────────────────────────
# avoids burning API requests for repeated queries

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(key: str) -> Path:
    safe = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.json"


def _read_cache(key: str, max_age_minutes: int = 30):
    path = _cache_path(key)
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


def _write_cache(key: str, payload):
    path = _cache_path(key)
    path.write_text(json.dumps({
        "cached_at": datetime.now().isoformat(),
        "payload":   payload,
    }))


# ── weather ───────────────────────────────────────────────────

WEATHER_CODES = {
    0:  "clear sky",
    1:  "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "icy fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "light showers", 81: "showers", 82: "heavy showers",
    95: "thunderstorm", 96: "thunderstorm with hail",
}


def _geocode(location: str) -> tuple[float, float, str]:
    """Convert a location name to coordinates using Open-Meteo geocoding."""
    cache_key = f"geo_{location.lower()}"
    cached = _read_cache(cache_key, max_age_minutes=60 * 24)  # 24h cache
    if cached:
        return cached["lat"], cached["lon"], cached["name"]

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location, "count": 1, "language": "en", "format": "json"}

    with httpx.Client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    if not data.get("results"):
        raise ValueError(f"Location not found: {location}")

    result = data["results"][0]
    lat  = result["latitude"]
    lon  = result["longitude"]
    name = result.get("name", location)

    _write_cache(cache_key, {"lat": lat, "lon": lon, "name": name})
    return lat, lon, name


def get_weather(location: str, forecast_days: int = 1) -> str:
    try:
        lat, lon, name = _geocode(location)

        cache_key = f"weather_{name}_{forecast_days}"
        cached = _read_cache(cache_key, max_age_minutes=30)
        if cached:
            return cached

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude":        lat,
            "longitude":       lon,
            "current":         "temperature_2m,weathercode,windspeed_10m,relativehumidity_2m",
            "daily":           "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone":        "auto",
            "forecast_days":   min(forecast_days, 7),
        }

        with httpx.Client(timeout=10) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        current = data["current"]
        temp    = current["temperature_2m"]
        code    = current["weathercode"]
        wind    = current["windspeed_10m"]
        humidity = current["relativehumidity_2m"]
        condition = WEATHER_CODES.get(code, "unknown conditions")

        if forecast_days <= 1:
            result = (
                f"Currently in {name}: {temp}°C, {condition}. "
                f"Wind {wind} km/h, humidity {humidity}%."
            )
        else:
            daily  = data["daily"]
            lines  = [f"Weather forecast for {name}:"]
            for i in range(min(forecast_days, len(daily["time"]))):
                date      = daily["time"][i]
                max_t     = daily["temperature_2m_max"][i]
                min_t     = daily["temperature_2m_min"][i]
                day_code  = daily["weathercode"][i]
                rain      = daily["precipitation_sum"][i]
                day_cond  = WEATHER_CODES.get(day_code, "unknown")
                lines.append(
                    f"  {date}: {day_cond}, {min_t}°C – {max_t}°C"
                    + (f", {rain}mm rain" if rain > 0 else "")
                )
            result = "\n".join(lines)

        _write_cache(cache_key, result)
        return result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch the weather: {e}"


# ── football ──────────────────────────────────────────────────

LEAGUE_IDS = {
    "primeira liga":      94,
    "portuguese liga":    94,
    "liga portugal":      94,
    "champions league":   2,
    "ucl":                2,
    "premier league":     39,
    "epl":                39,
    "la liga":            140,
}

HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
}

BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"


def _current_season() -> int:
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def _resolve_league(league_str: str) -> tuple[int, str]:
    key = league_str.lower().strip()
    for name, lid in LEAGUE_IDS.items():
        if name in key or key in name:
            return lid, name.title()
    raise ValueError(f"I don't follow that league: {league_str}")


def get_fixtures(league_str: str, next_n: int = 5) -> str:
    try:
        league_id, league_name = _resolve_league(league_str)
        season = _current_season()

        cache_key = f"fixtures_{league_id}_{season}_next{next_n}"
        cached = _read_cache(cache_key, max_age_minutes=60)
        if cached:
            return cached

        url = f"{BASE_URL}/fixtures"
        params = {
            "league": league_id,
            "season": season,
            "next":   next_n,
        }

        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers=HEADERS, params=params)
            r.raise_for_status()
            data = r.json()

        fixtures = data.get("response", [])
        if not fixtures:
            result = f"No upcoming fixtures found for {league_name}."
        else:
            lines = [f"Next {len(fixtures)} fixtures — {league_name}:"]
            for f in fixtures:
                fixture  = f["fixture"]
                teams    = f["teams"]
                date_str = fixture["date"][:10]
                time_str = fixture["date"][11:16]
                home     = teams["home"]["name"]
                away     = teams["away"]["name"]
                venue    = fixture.get("venue", {}).get("name", "")
                lines.append(f"  {date_str} {time_str} — {home} vs {away}" +
                             (f" ({venue})" if venue else ""))
            result = "\n".join(lines)

        _write_cache(cache_key, result)
        return result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch fixtures: {e}"


def get_results(league_str: str, last_n: int = 5) -> str:
    try:
        league_id, league_name = _resolve_league(league_str)
        season = _current_season()

        cache_key = f"results_{league_id}_{season}_last{last_n}"
        cached = _read_cache(cache_key, max_age_minutes=60)
        if cached:
            return cached

        url = f"{BASE_URL}/fixtures"
        params = {
            "league": league_id,
            "season": season,
            "last":   last_n,
            "status": "FT",
        }

        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers=HEADERS, params=params)
            r.raise_for_status()
            data = r.json()

        fixtures = data.get("response", [])
        if not fixtures:
            result = f"No recent results found for {league_name}."
        else:
            lines = [f"Last {len(fixtures)} results — {league_name}:"]
            for f in reversed(fixtures):
                teams  = f["teams"]
                goals  = f["goals"]
                date   = f["fixture"]["date"][:10]
                home   = teams["home"]["name"]
                away   = teams["away"]["name"]
                hg     = goals["home"]
                ag     = goals["away"]
                lines.append(f"  {date} — {home} {hg} – {ag} {away}")
            result = "\n".join(lines)

        _write_cache(cache_key, result)
        return result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch results: {e}"


def get_standings(league_str: str) -> str:
    try:
        league_id, league_name = _resolve_league(league_str)
        season = _current_season()

        cache_key = f"standings_{league_id}_{season}"
        cached = _read_cache(cache_key, max_age_minutes=120)
        if cached:
            return cached

        url = f"{BASE_URL}/standings"
        params = {"league": league_id, "season": season}

        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers=HEADERS, params=params)
            r.raise_for_status()
            data = r.json()

        standings = data.get("response", [{}])[0].get("league", {}).get("standings", [[]])[0]

        if not standings:
            result = f"No standings found for {league_name}."
        else:
            lines = [f"Standings — {league_name} {season}/{season+1}:"]
            for team in standings[:10]:
                pos   = team["rank"]
                name  = team["team"]["name"]
                pts   = team["points"]
                played = team["all"]["played"]
                w, d, l = team["all"]["win"], team["all"]["draw"], team["all"]["lose"]
                gd    = team["goalsDiff"]
                lines.append(
                    f"  {pos:2}. {name:<25} {pts}pts  "
                    f"{played}P {w}W {d}D {l}L  GD{gd:+}"
                )
            result = "\n".join(lines)

        _write_cache(cache_key, result)
        return result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch standings: {e}"