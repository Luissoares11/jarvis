import httpx
from .cache import read_cache, write_cache

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
    cached = read_cache(cache_key, max_age_minutes=60 * 24)  # 24h cache
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

    write_cache(cache_key, {"lat": lat, "lon": lon, "name": name})
    return lat, lon, name


def get_weather_data(location: str, forecast_days: int = 1) -> dict:
    """
    Returns raw structured weather data — used by the REST endpoint
    and by get_weather() below for the chat-friendly string version.
    """
    lat, lon, name = _geocode(location)

    cache_key = f"weather_raw_{name}_{forecast_days}"
    cached = read_cache(cache_key, max_age_minutes=30)
    if cached:
        return cached

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":      lat,
        "longitude":     lon,
        "current":       "temperature_2m,weathercode,windspeed_10m,relativehumidity_2m",
        "daily":         "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone":      "auto",
        "forecast_days": min(forecast_days, 7),
    }

    with httpx.Client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    result = {
        "location": name,
        "current": data["current"],
        "daily": data["daily"],
    }

    write_cache(cache_key, result)
    return result


def get_weather(location: str, forecast_days: int = 1) -> str:
    """Chat-friendly string version, used by core.py's handler."""
    try:
        data = get_weather_data(location, forecast_days)
        name = data["location"]
        current = data["current"]

        temp     = current["temperature_2m"]
        code     = current["weathercode"]
        wind     = current["windspeed_10m"]
        humidity = current["relativehumidity_2m"]
        condition = WEATHER_CODES.get(code, "unknown conditions")

        if forecast_days <= 1:
            return (
                f"Currently in {name}: {temp}°C, {condition}. "
                f"Wind {wind} km/h, humidity {humidity}%."
            )

        daily = data["daily"]
        lines = [f"Weather forecast for {name}:"]
        for i in range(min(forecast_days, len(daily["time"]))):
            date     = daily["time"][i]
            max_t    = daily["temperature_2m_max"][i]
            min_t    = daily["temperature_2m_min"][i]
            day_code = daily["weathercode"][i]
            rain     = daily["precipitation_sum"][i]
            day_cond = WEATHER_CODES.get(day_code, "unknown")
            lines.append(
                f"  {date}: {day_cond}, {min_t}°C – {max_t}°C"
                + (f", {rain}mm rain" if rain > 0 else "")
            )
        return "\n".join(lines)

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"I couldn't fetch the weather: {e}"