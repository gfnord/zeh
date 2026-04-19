import os
import ssl
import socket
import time
import re
import threading
import requests

IRC_SERVER = os.environ.get("IRC_SERVER", "irc.the14.xyz")
IRC_PORT = int(os.environ.get("IRC_PORT", 6697))
IRC_CHANNEL = os.environ.get("IRC_CHANNEL", "#itmimimi")
IRC_NICK = os.environ.get("IRC_NICK", "WeatherBot")
DEFAULT_LOCATION = os.environ.get("WEATHER_DEFAULT_LOCATION", "Vancouver, BC, Canada")

# WMO weather interpretation codes
WMO_CODES: dict[int, tuple[str, str]] = {
    0:  ("☀️",  "Clear sky"),
    1:  ("🌤️", "Mainly clear"),
    2:  ("⛅",  "Partly cloudy"),
    3:  ("☁️",  "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Icy fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Moderate drizzle"),
    55: ("🌦️", "Dense drizzle"),
    61: ("🌧️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    71: ("🌨️", "Slight snow"),
    73: ("🌨️", "Moderate snow"),
    75: ("❄️",  "Heavy snow"),
    77: ("🌨️", "Snow grains"),
    80: ("🌦️", "Slight showers"),
    81: ("🌧️", "Moderate showers"),
    82: ("⛈️",  "Violent showers"),
    85: ("🌨️", "Slight snow showers"),
    86: ("❄️",  "Heavy snow showers"),
    95: ("⛈️",  "Thunderstorm"),
    96: ("⛈️",  "Thunderstorm w/ hail"),
    99: ("⛈️",  "Thunderstorm w/ heavy hail"),
}

# Matches: "!weather", "!weather for {loc}", "get (the) weather (forecast) for {loc}"
TRIGGER_RE = re.compile(
    r"!weather(?:\s+for\s+(.+))?$"
    r"|get\s+(?:the\s+)?weather(?:\s+forecast)?\s+for\s+(.+)",
    re.IGNORECASE,
)


def geocode(location: str) -> tuple[float, float, str] | None:
    segments = [s.strip() for s in location.split(",")]
    city = segments[0]
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 10, "language": "en", "format": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        return None

    r = results[0]
    if len(segments) > 1:
        hints = [s.lower() for s in segments[1:]]
        for candidate in results:
            admin1 = (candidate.get("admin1") or "").lower()
            country = (candidate.get("country") or "").lower()
            country_code = (candidate.get("country_code") or "").lower()
            if any(h in admin1 or h in country or h == country_code for h in hints):
                r = candidate
                break

    display = [r.get("name", city)]
    if r.get("admin1"):
        display.append(r["admin1"])
    if r.get("country"):
        display.append(r["country"])
    return r["latitude"], r["longitude"], ", ".join(display)


def fetch_current(lat: float, lon: float) -> dict:
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["current"]


def format_weather(display_name: str, current: dict) -> str:
    code = current.get("weather_code", 0)
    emoji, desc = WMO_CODES.get(code, ("🌡️", "Unknown"))
    temp = current.get("temperature_2m", "?")
    feels = current.get("apparent_temperature", "?")
    wind = current.get("wind_speed_10m", "?")
    humidity = current.get("relative_humidity_2m", "?")
    return (
        f"{emoji}  {display_name} — {desc}"
        f" | 🌡️ {temp}°C (feels like {feels}°C)"
        f" | 💨 {wind} km/h"
        f" | 💧 {humidity}%"
    )


def weather_line(location: str) -> str:
    result = geocode(location)
    if result is None:
        return f"❌ Location not found: {location}"
    lat, lon, display_name = result
    current = fetch_current(lat, lon)
    return format_weather(display_name, current)


def send_line(sock: ssl.SSLSocket, line: str):
    sock.sendall(f"{line}\r\n".encode("utf-8"))


def main():
    raw = socket.create_connection((IRC_SERVER, IRC_PORT), timeout=30)
    raw.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
    raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
    raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    ctx = ssl.create_default_context()
    sock = ctx.wrap_socket(raw, server_hostname=IRC_SERVER)
    sock.settimeout(None)

    send_line(sock, f"NICK {IRC_NICK}")
    send_line(sock, f"USER {IRC_NICK} 0 * :{IRC_NICK}")

    buffer = ""
    last_location = DEFAULT_LOCATION

    while True:
        data = sock.recv(4096).decode("utf-8", errors="replace")
        if not data:
            break
        buffer += data
        while "\r\n" in buffer:
            line, buffer = buffer.split("\r\n", 1)
            print(f"<< {line}")

            if line.startswith("PING"):
                send_line(sock, "PONG" + line[4:])
                continue

            parts = line.split(" ", 3)
            if len(parts) >= 2 and parts[1] == "001":
                send_line(sock, f"JOIN {IRC_CHANNEL}")
                continue

            if len(parts) < 4 or parts[1] != "PRIVMSG":
                continue

            target = parts[2]
            message = parts[3].lstrip(":")

            if not target.startswith("#"):
                continue  # channel only

            nick_lower = IRC_NICK.lower()
            msg_lower = message.lower()
            addressed = msg_lower.startswith(nick_lower) and (
                len(message) == len(IRC_NICK) or not message[len(IRC_NICK)].isalnum()
            )

            if addressed and re.search(r"\bhelp\b", message, re.IGNORECASE):
                send_line(sock, f"PRIVMSG {target} :🌤️  WeatherBot commands:")
                send_line(sock, f"PRIVMSG {target} :  !weather                              → current weather for the last used location ({last_location})")
                send_line(sock, f"PRIVMSG {target} :  !weather for {{City, State, Country}}  → weather for a specific location")
                send_line(sock, f"PRIVMSG {target} :  get the weather forecast for {{City}}  → same, natural language")
                continue

            m = TRIGGER_RE.search(message)
            if not m:
                continue

            requested = (m.group(1) or m.group(2) or "").strip()
            if requested:
                last_location = requested
            location = last_location

            def respond(loc: str = location, tgt: str = target):
                try:
                    reply = weather_line(loc)
                except Exception as e:
                    reply = f"❌ Error fetching weather: {e}"
                send_line(sock, f"PRIVMSG {tgt} :{reply}")

            threading.Thread(target=respond, daemon=True).start()


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Reconnecting after error: {e}")
        time.sleep(10)
