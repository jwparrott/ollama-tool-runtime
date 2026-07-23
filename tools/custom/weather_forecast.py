"""Get weather forecasts via Open-Meteo (no API key required)."""

from __future__ import annotations

import json
from urllib import parse, request

TOOL_SPEC = {
    "name": "weather_forecast",
    "description": (
        "Get current weather and short forecast for a city/location using Open-Meteo. "
        "No API key required."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City or place name, e.g. 'New York'."},
            "days": {"type": "integer", "description": "Forecast days (1-7, default 3)."},
            "temperature_unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature unit. Default: celsius.",
            },
        },
        "required": ["location"],
    },
}


def run(args: dict, context: dict) -> dict:
    _ = context
    location = str(args.get("location", "")).strip()
    if not location:
        return {"error": "location must not be empty"}

    days = min(max(1, int(args.get("days", 3))), 7)
    unit = str(args.get("temperature_unit", "celsius")).strip().lower()
    if unit not in {"celsius", "fahrenheit"}:
        return {"error": "temperature_unit must be 'celsius' or 'fahrenheit'."}

    geo = _fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search?"
        + parse.urlencode({"name": location, "count": "1", "language": "en", "format": "json"})
    )
    if "error" in geo:
        return geo
    places = geo.get("results") or []
    if not places:
        return {"error": f"No location match found for '{location}'."}
    place = places[0]

    lat = place.get("latitude")
    lon = place.get("longitude")
    if lat is None or lon is None:
        return {"error": "Geocoding response missing coordinates."}

    forecast_url = "https://api.open-meteo.com/v1/forecast?" + parse.urlencode(
        {
            "latitude": str(lat),
            "longitude": str(lon),
            "current": "temperature_2m,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": str(days),
            "temperature_unit": unit,
        }
    )
    weather = _fetch_json(forecast_url)
    if "error" in weather:
        return weather

    daily = weather.get("daily", {})
    times = daily.get("time") or []
    maxes = daily.get("temperature_2m_max") or []
    mins = daily.get("temperature_2m_min") or []
    pops = daily.get("precipitation_probability_max") or []

    forecast_days = []
    for idx in range(min(len(times), len(maxes), len(mins), len(pops))):
        forecast_days.append(
            {
                "date": times[idx],
                "temp_max": maxes[idx],
                "temp_min": mins[idx],
                "precipitation_probability_max": pops[idx],
            }
        )

    current = weather.get("current", {})
    return {
        "location": {
            "name": place.get("name"),
            "country": place.get("country"),
            "latitude": lat,
            "longitude": lon,
            "timezone": weather.get("timezone"),
        },
        "temperature_unit": unit,
        "current": {
            "temperature_2m": current.get("temperature_2m"),
            "wind_speed_10m": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
        },
        "forecast": forecast_days,
    }


def _fetch_json(url: str) -> dict:
    req = request.Request(url, headers={"User-Agent": "ollama-tool-runtime/1.0"})
    try:
        with request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except TimeoutError:
        return {"error": "Request timed out."}
    except OSError as exc:
        return {"error": f"Request failed: {exc}"}
    except json.JSONDecodeError:
        return {"error": "Remote service returned invalid JSON."}
