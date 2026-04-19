# zeh

This repo contains three IRC bots for the `#itmimimi` channel on `irc.the14.xyz`:

- **zeh** (`bot.py`) — forwards messages to a local [Ollama](https://ollama.com) instance and replies with AI-generated responses.
- **HoraBot** (`timebot.py`) — announces the current time every 15 minutes.
- **WeatherBot** (`weatherbot.py`) — fetches live weather forecasts from Open-Meteo and posts them with emojis.

## zeh (bot.py)

### Features

- Connects to IRC over TLS
- Responds in channel when mentioned as `zeh: <message>`
- Responds to everything in private messages
- Maintains per-user conversation history
- `!reset` command to clear your conversation history
- Long responses are split to respect the IRC 512-byte line limit

### Requirements

- Docker and Docker Compose
- An Ollama instance running locally with the `dolphin3:latest` model pulled

### Quick Start

**1. Pull the model in Ollama (on the host machine):**

```bash
ollama pull dolphin3:latest
```

**2. Clone the repo and configure:**

```bash
git clone <repo-url>
cd zeh
cp .env.example .env   # edit if needed
```

**3. Build and run:**

```bash
docker compose up --build -d
```

**4. Check logs:**

```bash
docker compose logs -f
```

### Configuration

All configuration is done via environment variables in the `.env` file:

| Variable | Default | Description |
|---|---|---|
| `IRC_SERVER` | `irc.the14.xyz` | IRC server hostname |
| `IRC_PORT` | `6697` | IRC server port (TLS) |
| `IRC_CHANNEL` | `#itmimimi` | Channel to join |
| `IRC_NICK` | `zeh` | Bot nickname |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `dolphin3:latest` | Ollama model to use |

The `.env` file is excluded from git. An `.env.example` with safe defaults is provided as a template.

### Usage

**In channel:**

```
<you> zeh: what is the capital of France?
<zeh> you: Paris.
```

**In private message:**

```
<you> what is the capital of France?
<zeh> Paris.
```

**Reset conversation history:**

```
<you> !reset
<zeh> you: conversation history cleared.
```

### Stopping

```bash
docker compose down
```

### Notes

- The container uses `extra_hosts: host-gateway` so that `host.docker.internal` resolves to the Docker host, where Ollama is expected to be running.
- The bot auto-reconnects with a 10-second backoff if the connection drops.
- Restart policy is `unless-stopped`, so it comes back up automatically after a reboot.

## HoraBot (timebot.py)

A minimal bot that joins `#itmimimi` and announces the current time every 15 minutes.

### Features

- Connects to IRC over TLS
- Announces the current time (`HH:MM`) in the channel every 15 minutes
- No external dependencies beyond the Python standard library

### Running

```bash
python timebot.py
```

Configuration is read from the same environment variables as `bot.py` (`IRC_SERVER`, `IRC_PORT`, `IRC_CHANNEL`, `IRC_NICK`), with `HoraBot` as the default nick.

## WeatherBot (weatherbot.py)

Fetches live weather from [Open-Meteo](https://open-meteo.com/) (free, no API key required) and posts a formatted line with emojis.

### Features

- Connects to IRC over TLS
- Responds to weather requests in the channel
- Geocodes any city/state/country string automatically
- Falls back to a configurable default location
- No API key needed

### Triggers

```
!weather                                        → default location
!weather for Porto Alegre, RS, Brazil           → specific location
get the weather forecast for London, UK         → specific location
```

**Example output:**

```
⛅  São Paulo, São Paulo, Brazil — Partly cloudy | 🌡️ 24°C (feels like 26°C) | 💨 18 km/h | 💧 72%
```

### Running

```bash
python weatherbot.py
```

### Configuration

| Variable | Default | Description |
|---|---|---|
| `IRC_SERVER` | `irc.the14.xyz` | IRC server hostname |
| `IRC_PORT` | `6697` | IRC server port (TLS) |
| `IRC_CHANNEL` | `#itmimimi` | Channel to join |
| `IRC_NICK` | `WeatherBot` | Bot nickname |
| `WEATHER_DEFAULT_LOCATION` | `São Paulo, SP, Brazil` | Fallback location for `!weather` |
