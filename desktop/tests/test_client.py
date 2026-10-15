import threading
import time
import unittest
from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed
from client import Connection


class ClientTests(unittest.TestCase):
    def test_unresponsive_application_disconnects(self):
        # TCP and WebSocket ping remain healthy, but application pongs stop.
        def silent_peer(ws):
            try:
                for _ in ws:
                    pass
            except ConnectionClosed:
                pass  # Expected: the client times out and closes this socket.

        server = serve(silent_peer, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        messages = []
        client = Connection(f"ws://127.0.0.1:{server.socket.getsockname()[1]}",
                            "a" * 32, "sender", messages.append)
        try:
            started = time.monotonic()
            client.thread.start()
            client.thread.join(timeout=6)
            self.assertFalse(client.thread.is_alive())
            self.assertTrue(client.closed.is_set())
            self.assertLess(time.monotonic() - started, 6)
            self.assertTrue(any(m["type"] == "disconnected" for m in messages))
        finally:
            client.close()
            server.shutdown()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
