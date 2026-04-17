import os
import ssl
import socket
import threading
import requests
import time

IRC_SERVER = os.environ.get("IRC_SERVER", "irc.the14.xyz")
IRC_PORT = int(os.environ.get("IRC_PORT", 6697))
IRC_CHANNEL = os.environ.get("IRC_CHANNEL", "#itmimimi")
IRC_NICK = os.environ.get("IRC_NICK", "ollama")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "dolphin3:latest")

SYSTEM_PROMPT = "You are a helpful IRC bot. Keep responses concise, under 3 lines when possible."
IRC_MAX_BYTES = 400  # conservative limit leaving room for prefix/command overhead

conversation_histories: dict[str, list[dict]] = {}
history_lock = threading.Lock()


def get_history(user: str) -> list[dict]:
    with history_lock:
        if user not in conversation_histories:
            conversation_histories[user] = []
        return conversation_histories[user]


def reset_history(user: str) -> None:
    with history_lock:
        conversation_histories[user] = []


def query_ollama(user: str, message: str) -> str:
    with history_lock:
        if user not in conversation_histories:
            conversation_histories[user] = []
        conversation_histories[user].append({"role": "user", "content": message})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_histories[user]

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        reply = response.json()["message"]["content"].strip()
    except Exception as e:
        reply = f"Error contacting Ollama: {e}"

    with history_lock:
        conversation_histories[user].append({"role": "assistant", "content": reply})

    return reply


def split_message(text: str, max_bytes: int = IRC_MAX_BYTES) -> list[str]:
    lines = []
    for paragraph in text.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while paragraph:
            encoded = paragraph.encode("utf-8")
            if len(encoded) <= max_bytes:
                lines.append(paragraph)
                break
            # binary-search safe split point
            cut = max_bytes
            while len(paragraph[:cut].encode("utf-8")) > max_bytes:
                cut -= 1
            lines.append(paragraph[:cut])
            paragraph = paragraph[cut:].strip()
    return lines or [""]


class IRCBot:
    def __init__(self):
        self.sock: ssl.SSLSocket | None = None
        self._stop = threading.Event()

    def connect(self):
        raw = socket.create_connection((IRC_SERVER, IRC_PORT), timeout=30)
        ctx = ssl.create_default_context()
        self.sock = ctx.wrap_socket(raw, server_hostname=IRC_SERVER)
        self.send(f"NICK {IRC_NICK}")
        self.send(f"USER {IRC_NICK} 0 * :Ollama IRC Bot")

    def send(self, text: str):
        self.sock.sendall((text + "\r\n").encode("utf-8"))

    def privmsg(self, target: str, text: str):
        for line in split_message(text):
            self.send(f"PRIVMSG {target} :{line}")
            time.sleep(0.3)  # basic flood protection

    def handle_line(self, line: str):
        print(f"<< {line}")

        if line.startswith("PING"):
            self.send("PONG" + line[4:])
            return

        parts = line.split(" ", 3)
        if len(parts) < 2:
            return

        # numeric 001 = welcome
        if parts[1] == "001":
            self.send(f"JOIN {IRC_CHANNEL}")
            return

        if parts[1] != "PRIVMSG" or len(parts) < 4:
            return

        prefix = parts[0].lstrip(":")
        nick = prefix.split("!")[0]
        target = parts[2]
        message = parts[3].lstrip(":")

        if nick.lower() == IRC_NICK.lower():
            return

        is_channel = target.startswith("#")
        reply_target = target if is_channel else nick

        if message.strip() == "!reset":
            reset_history(nick)
            self.privmsg(reply_target, f"{nick}: conversation history cleared.")
            return

        if is_channel:
            trigger = f"{IRC_NICK}:"
            if not message.lower().startswith(trigger.lower()):
                return
            message = message[len(trigger):].strip()

        threading.Thread(
            target=self._respond,
            args=(nick, reply_target, message),
            daemon=True,
        ).start()

    def _respond(self, nick: str, reply_target: str, message: str):
        reply = query_ollama(nick, message)
        is_channel = reply_target.startswith("#")
        prefix = f"{nick}: " if is_channel else ""
        for line in split_message(reply):
            self.privmsg(reply_target, f"{prefix}{line}")

    def run(self):
        self.connect()
        buffer = ""
        while not self._stop.is_set():
            try:
                data = self.sock.recv(4096).decode("utf-8", errors="replace")
                if not data:
                    break
                buffer += data
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    self.handle_line(line)
            except ssl.SSLError:
                break
            except Exception as e:
                print(f"Error: {e}")
                break
        print("Disconnected.")


if __name__ == "__main__":
    while True:
        try:
            bot = IRCBot()
            bot.run()
        except Exception as e:
            print(f"Reconnecting after error: {e}")
        time.sleep(10)
