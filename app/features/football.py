import httpx
from datetime import datetime, timedelta
from config import FOOTBALL_KEY
from .cache import read_cache, write_cache

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
    if isinstance(data, dict) and data.get("message") and "matches" not in data and "standings" not in data:
        raise RuntimeError(data["message"])
    return data


def get_fixtures(league_str: str, next_n: int = 5) -> str:
    try:
        code, league_name = _resolve_league_code(league_str)
        today = datetime.now().date()
        future = today + timedelta(days=45)

        cache_key = f"fd_fixtures_{code}_next{next_n}"
        cached = read_cache(cache_key, max_age_minutes=60)
        if cached:
            return cached

        data = _fd_get(
            f"/competitions/{code}/matches",
            {"dateFrom": today.isoformat(), "dateTo": future.isoformat(), "status": "SCHEDULED"}
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

        write_cache(cache_key, result)
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
        cached = read_cache(cache_key, max_age_minutes=60)
        if cached:
            return cached

        data = _fd_get(
            f"/competitions/{code}/matches",
            {"dateFrom": past.isoformat(), "dateTo": today.isoformat(), "status": "FINISHED"}
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

        write_cache(cache_key, result)
        return result
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch results: {e}"


def get_standings(league_str: str) -> str:
    try:
        code, league_name = _resolve_league_code(league_str)

        cache_key = f"fd_standings_{code}"
        cached = read_cache(cache_key, max_age_minutes=120)
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

        write_cache(cache_key, result)
        return result
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch standings: {e}"