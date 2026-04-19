import os
import ssl
import socket
import time
import threading

IRC_SERVER = os.environ.get("IRC_SERVER", "irc.the14.xyz")
IRC_PORT = int(os.environ.get("IRC_PORT", 6697))
IRC_CHANNEL = os.environ.get("IRC_CHANNEL", "#itmimimi")
IRC_NICK = os.environ.get("IRC_NICK", "HoraBot")

def send_line(sock, line):
    sock.send(f"{line}\r\n".encode())

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

    joined = False
    buffer = ""

    def time_announcer():
        while True:
            time.sleep(900)
            if joined:
                t = time.localtime()
                send_line(sock, f"PRIVMSG {IRC_CHANNEL} :{t.tm_hour:02d}:{t.tm_min:02d}")

    threading.Thread(target=time_announcer, daemon=True).start()

    while True:
        data = sock.recv(4096).decode("utf-8", errors="replace")
        if not data:
            break
        buffer += data
        while "\r\n" in buffer:
            line, buffer = buffer.split("\r\n", 1)
            if line.startswith("PING"):
                send_line(sock, "PONG" + line[4:])
            parts = line.split(" ", 2)
            if len(parts) >= 2 and parts[1] == "001" and not joined:
                send_line(sock, f"JOIN {IRC_CHANNEL}")
                joined = True

if __name__ == "__main__":
    main()
