import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path

from config import FOOTBALL_KEY

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


# ── football-data.org ────────────────────────────────────────

FD_BASE_URL = "https://api.football-data.org/v4"

FD_HEADERS = {
    "X-Auth-Token": FOOTBALL_KEY
}

LEAGUE_CODES = {
    "primeira liga": "PPL",
    "portuguese liga": "PPL",
    "liga portugal": "PPL",
    "champions league": "CL",
    "ucl": "CL",
    "premier league": "PL",
    "epl": "PL",
    "la liga": "PD",
}


def _resolve_league_code(league_str: str) -> tuple[str, str]:
    key = league_str.lower().strip()

    for name, code in LEAGUE_CODES.items():
        if key == name or key in name or name in key:
            return code, name.title()

    raise ValueError(f"I don't follow that league: {league_str}")


def _fd_get(path: str, params: dict | None = None):
    url = f"{FD_BASE_URL}{path}"

    with httpx.Client(timeout=15) as client:
        r = client.get(url, headers=FD_HEADERS, params=params)
        r.raise_for_status()
        data = r.json()

    # football-data sometimes returns error info in JSON
    if isinstance(data, dict) and data.get("message") and "matches" not in data and "standings" not in data:
        raise RuntimeError(data["message"])

    return data


def get_fixtures(league_str: str, next_n: int = 5) -> str:
    try:
        code, league_name = _resolve_league_code(league_str)

        today = datetime.now().date()
        future = today + timedelta(days=45)

        cache_key = f"fd_fixtures_{code}_next{next_n}"
        cached = _read_cache(cache_key, max_age_minutes=60)
        if cached:
            return cached

        data = _fd_get(
            f"/competitions/{code}/matches",
            {
                "dateFrom": today.isoformat(),
                "dateTo": future.isoformat(),
                "status": "SCHEDULED",
            }
        )

        matches = data.get("matches", [])[:next_n]

        if not matches:
            result = f"No upcoming fixtures found for {league_name}."
        else:
            lines = [f"Next {len(matches)} fixtures — {league_name}:"]
            for match in matches:
                utc_date = match.get("utcDate", "")
                date_str = utc_date[:10] if utc_date else "Unknown date"
                time_str = utc_date[11:16] if utc_date else "??:??"

                home = match.get("homeTeam", {}).get("name", "Unknown")
                away = match.get("awayTeam", {}).get("name", "Unknown")
                matchday = match.get("matchday")

                extra = f" (Matchday {matchday})" if matchday else ""
                lines.append(f"  {date_str} {time_str} — {home} vs {away}{extra}")

            result = "\n".join(lines)

        _write_cache(cache_key, result)
        return result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch fixtures: {e}"


def get_results(league_str: str, last_n: int = 5) -> str:
    try:
        code, league_name = _resolve_league_code(league_str)

        today = datetime.now().date()
        past = today - timedelta(days=45)

        cache_key = f"fd_results_{code}_last{last_n}"
        cached = _read_cache(cache_key, max_age_minutes=60)
        if cached:
            return cached

        data = _fd_get(
            f"/competitions/{code}/matches",
            {
                "dateFrom": past.isoformat(),
                "dateTo": today.isoformat(),
                "status": "FINISHED",
            }
        )

        matches = data.get("matches", [])
        matches = matches[-last_n:]

        if not matches:
            result = f"No recent results found for {league_name}."
        else:
            lines = [f"Last {len(matches)} results — {league_name}:"]
            for match in matches:
                utc_date = match.get("utcDate", "")
                date_str = utc_date[:10] if utc_date else "Unknown date"

                home = match.get("homeTeam", {}).get("name", "Unknown")
                away = match.get("awayTeam", {}).get("name", "Unknown")

                full_time = match.get("score", {}).get("fullTime", {})
                hg = full_time.get("home", "?")
                ag = full_time.get("away", "?")

                lines.append(f"  {date_str} — {home} {hg} – {ag} {away}")

            result = "\n".join(lines)

        _write_cache(cache_key, result)
        return result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch results: {e}"


def get_standings(league_str: str) -> str:
    try:
        code, league_name = _resolve_league_code(league_str)

        cache_key = f"fd_standings_{code}"
        cached = _read_cache(cache_key, max_age_minutes=120)
        if cached:
            return cached

        data = _fd_get(f"/competitions/{code}/standings")

        standings = data.get("standings", [])
        table = None

        for section in standings:
            if section.get("type") == "TOTAL":
                table = section.get("table", [])
                break

        if not table:
            result = f"No standings found for {league_name}."
        else:
            lines = [f"Standings — {league_name}:"]
            for team in table[:10]:
                pos = team.get("position", "?")
                name = team.get("team", {}).get("name", "Unknown")
                pts = team.get("points", "?")
                played = team.get("playedGames", "?")
                won = team.get("won", "?")
                draw = team.get("draw", "?")
                lost = team.get("lost", "?")
                gd = team.get("goalDifference", 0)

                lines.append(
                    f"  {pos:2}. {name:<25} {pts}pts  "
                    f"{played}P {won}W {draw}D {lost}L  GD{gd:+}"
                )

            result = "\n".join(lines)

        _write_cache(cache_key, result)
        return result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch standings: {e}"
    
