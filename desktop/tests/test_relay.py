import json
import secrets
import threading
import unittest
from websockets.sync.client import connect
from protocol import check_url, validate_event
from relay import make_server


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"ws://127.0.0.1:{self.server.socket.getsockname()[1]}"
        self.code = secrets.token_urlsafe(24)
        self.clients = []

    def tearDown(self):
        for ws in self.clients:
            ws.close()
        self.server.shutdown()
        self.thread.join(timeout=3)

    def peer(self, role, code=None):
        ws = connect(self.url, proxy=None)
        self.clients.append(ws)
        ws.send(json.dumps(dict(type="hello", role=role, code=code or self.code)))
        self.assertEqual(self.recv(ws)["type"], "welcome")
        self.assertEqual(self.recv(ws)["type"], "status")
        return ws

    @staticmethod
    def recv(ws):
        return json.loads(ws.recv(timeout=2))

    def paired(self):
        sender = self.peer("sender")
        receiver = self.peer("receiver")
        self.assertTrue(self.recv(sender)["paired"])
        return sender, receiver

    def arm(self, sender, receiver, value=True):
        receiver.send(json.dumps(dict(type="arm", value=value)))
        self.assertEqual(self.recv(sender)["armed"], value)
        self.assertEqual(self.recv(receiver)["armed"], value)

    def test_consent_key_mouse_reset_disconnect(self):
        sender, receiver = self.paired()
        key = dict(type="key", vk=87, down=True)
        sender.send(json.dumps(dict(type="event", event=key)))
        with self.assertRaises(TimeoutError):
            receiver.recv(timeout=.1)  # No events before explicit receiver consent.
        self.arm(sender, receiver)
        for event in (key, dict(type="move", x=.4, y=.8),
                      dict(type="button", button="left", down=True, x=.4, y=.8),
                      dict(type="scroll", dx=0, dy=1, x=.4, y=.8),
                      dict(type="key", vk=87, down=False)):
            sender.send(json.dumps(dict(type="event", event=event)))
            self.assertEqual(self.recv(receiver), dict(type="event", event=event))
        sender.send('{"type":"reset"}')
        self.assertEqual(self.recv(receiver)["type"], "reset")
        sender.close()
        status = self.recv(receiver)
        self.assertFalse(status["paired"])
        self.assertFalse(status["armed"])

    def test_room_isolation_and_duplicate_role(self):
        sender = self.peer("sender")
        receiver = self.peer("receiver", secrets.token_urlsafe(24))
        receiver.send('{"type":"arm","value":true}')
        self.assertFalse(self.recv(receiver)["paired"])
        duplicate = connect(self.url, proxy=None)
        self.clients.append(duplicate)
        duplicate.send(json.dumps(dict(type="hello", code=self.code, role="sender")))
        self.assertEqual(self.recv(duplicate)["type"], "error")
        sender.send('{"type":"ping"}')
        self.assertEqual(self.recv(sender)["type"], "pong")

    def test_disarm_and_reconnect_require_new_consent(self):
        sender, receiver = self.paired()
        self.arm(sender, receiver)
        self.arm(sender, receiver, False)
        sender.send(json.dumps(dict(type="event", event=dict(type="key", vk=65, down=True))))
        with self.assertRaises(TimeoutError):
            receiver.recv(timeout=.1)
        receiver.close()
        self.assertFalse(self.recv(sender)["armed"])
        replacement = self.peer("receiver")
        self.assertFalse(self.recv(sender)["armed"])
        replacement.send('{"type":"ping"}')
        self.assertEqual(self.recv(replacement)["type"], "pong")

    def test_invalid_events_close_sender_and_disarm_receiver(self):
        sender, receiver = self.paired()
        self.arm(sender, receiver)
        sender.send(json.dumps(dict(type="event", event=dict(type="key", vk=123, down=True))))
        self.assertEqual(self.recv(sender)["type"], "error")
        self.assertFalse(self.recv(receiver)["armed"])


class ProtocolTests(unittest.TestCase):
    def test_url_requires_tls_for_remote(self):
        for url in ("ws://example.com:8765", "http://example.com", "wss://user:pass@example.com"):
            with self.assertRaises(ValueError):
                check_url(url)
        for url in ("ws://127.0.0.1:8765", "ws://localhost:8765", "wss://relay.example.com"):
            self.assertEqual(check_url(url), url)

    def test_malformed_inputs_rejected(self):
        for event in (None, {}, {"type": "move", "x": float("nan"), "y": 0},
                      {"type": "key", "vk": 65, "down": "yes"},
                      {"type": "button", "button": "left", "down": True, "x": 2, "y": 0},
                      {"type": "scroll", "x": 0, "y": 0, "dx": 100, "dy": 0}):
            with self.assertRaises(ValueError):
                validate_event(event)


if __name__ == "__main__":
    unittest.main()
