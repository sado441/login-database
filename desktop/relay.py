"""Room relay. Internet deployments require a TLS reverse proxy (wss)."""
import argparse
import json
import re
import threading
import time
from websockets.sync.server import serve
from protocol import MAX_MESSAGE, validate_event


class Relay:
    def __init__(self):
        self.lock = threading.RLock()
        self.rooms = {}

    @staticmethod
    def send(ws, data):
        ws.send(json.dumps(data))

    def status(self, room):
        state = {"type": "status", "paired": "sender" in room and "receiver" in room,
                 "armed": room.get("armed", False)}
        for role in ("sender", "receiver"):
            if role in room:
                try:
                    self.send(room[role], state)
                except Exception:
                    pass

    def handle(self, ws):
        code = role = None
        registered = False
        try:
            hello = json.loads(ws.recv(timeout=5))
            code, role = hello.get("code"), hello.get("role")
            if (hello.get("type") != "hello" or role not in {"sender", "receiver"}
                    or not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{24,100}", code)):
                raise ValueError("Geçersiz oturum bilgisi; uygulamanın ürettiği kodu kullanın.")
            with self.lock:
                if code not in self.rooms and len(self.rooms) >= 100:
                    raise ValueError("Sunucu dolu.")
                room = self.rooms.setdefault(code, {"armed": False})
                if role in room:
                    raise ValueError("Bu oturumda bu rol zaten bağlı.")
                room[role] = ws
                registered = True
                self.send(ws, {"type": "welcome", "role": role})
                self.status(room)
            window, count = time.monotonic(), 0
            for raw in ws:
                message = json.loads(raw)
                if not isinstance(message, dict):
                    raise ValueError("Geçersiz mesaj.")
                if time.monotonic() - window >= 1:
                    window, count = time.monotonic(), 0
                count += 1
                if count > 500:
                    raise ValueError("Olay sınırı aşıldı.")
                with self.lock:
                    if message.get("type") == "ping":
                        self.send(ws, {"type": "pong"})
                    elif role == "receiver" and message.get("type") == "arm":
                        if type(message.get("value")) is not bool:
                            raise ValueError("Geçersiz onay.")
                        room["armed"] = message["value"] and "sender" in room
                        self.status(room)
                    elif role == "sender" and message.get("type") == "reset":
                        if "receiver" in room:
                            self.send(room["receiver"], {"type": "reset"})
                    elif role == "sender" and message.get("type") == "event":
                        event = validate_event(message.get("event"))
                        if room["armed"] and "receiver" in room:
                            self.send(room["receiver"], {"type": "event", "event": event})
                    else:
                        raise ValueError("Bu rol bu mesajı gönderemez.")
        except Exception as exc:
            try:
                # Don't echo input, codes or credentials into errors/logs.
                self.send(ws, {"type": "error", "message": str(exc) if isinstance(exc, ValueError) else "Bağlantı kapandı."})
            except Exception:
                pass
        finally:
            if registered:
                with self.lock:
                    room = self.rooms.get(code, {})
                    if room.get(role) is ws:
                        del room[role]
                        room["armed"] = False
                        self.status(room)
                    if not any(r in room for r in ("sender", "receiver")):
                        self.rooms.pop(code, None)
            ws.close()


def make_server(host="127.0.0.1", port=8765):
    relay = Relay()
    return serve(relay.handle, host, port, max_size=MAX_MESSAGE,
                 ping_interval=2, ping_timeout=3, compression=None, open_timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with make_server(args.host, args.port) as server:
        print(f"SADO Link relay: {args.host}:{args.port} (Internet için TLS proxy gerekir)")
        server.serve_forever()
