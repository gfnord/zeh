# zeh

An IRC bot that forwards messages to a local [Ollama](https://ollama.com) instance and replies with AI-generated responses.

## Features

- Connects to IRC over TLS
- Responds in channel when mentioned as `zeh: <message>`
- Responds to everything in private messages
- Maintains per-user conversation history
- `!reset` command to clear your conversation history
- Long responses are split to respect the IRC 512-byte line limit

## Requirements

- Docker and Docker Compose
- An Ollama instance running locally with the `dolphin3:latest` model pulled

## Quick Start

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

## Configuration

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

## Usage

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

## Stopping

```bash
docker compose down
```

## Notes

- The container uses `extra_hosts: host-gateway` so that `host.docker.internal` resolves to the Docker host, where Ollama is expected to be running.
- The bot auto-reconnects with a 10-second backoff if the connection drops.
- Restart policy is `unless-stopped`, so it comes back up automatically after a reboot.
