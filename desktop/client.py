import json
import queue
import threading
import time
from websockets.sync.client import connect
from protocol import MAX_MESSAGE, check_url


class Connection:
    def __init__(self, url, code, role, notify):
        self.url, self.code, self.role = check_url(url), code, role
        self.notify = notify
        self.outgoing = queue.Queue(maxsize=256)
        self.closed = threading.Event()
        self.ws = None
        self.thread = threading.Thread(target=self.run, daemon=True)

    def send(self, message):
        if self.closed.is_set():
            return
        try:
            self.outgoing.put_nowait(message)
        except queue.Full:
            # Never silently drop key-up: a congested connection must stop.
            self.close()

    def close(self):
        self.closed.set()
        if self.ws:
            self.ws.close()

    def run(self):
        try:
            with connect(self.url, max_size=MAX_MESSAGE, open_timeout=5,
                         close_timeout=1, ping_interval=2, ping_timeout=3,
                         compression=None, proxy=None) as ws:
                self.ws = ws
                ws.send(json.dumps({"type": "hello", "code": self.code, "role": self.role}))
                last_ping, last_pong = 0, time.monotonic()
                while not self.closed.is_set():
                    for _ in range(32):
                        try:
                            message = self.outgoing.get_nowait()
                        except queue.Empty:
                            break
                        ws.send(json.dumps(message))
                    now = time.monotonic()
                    if now - last_ping >= 1:
                        ws.send('{"type":"ping"}')
                        last_ping = now
                    if now - last_pong > 4:
                        raise TimeoutError("Sunucu yanıt vermiyor.")
                    try:
                        data = json.loads(ws.recv(timeout=0.02))
                    except TimeoutError:
                        continue
                    if data.get("type") == "pong":
                        last_pong = time.monotonic()
                    else:
                        self.notify(data)
        except Exception as exc:
            self.notify({"type": "error", "message": str(exc)[:180]})
        finally:
            self.closed.set()
            self.notify({"type": "disconnected"})
