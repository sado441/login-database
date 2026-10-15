"""End-to-end Tk test. Skipped when no desktop/display is available."""
import secrets
import threading
import time
from types import SimpleNamespace
import tkinter as tk
import unittest
import gc
from app import App
from relay import make_server


class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.sender_root = tk.Tk()
        except tk.TclError:
            self.skipTest("No graphical display")
        self.receiver_root = tk.Tk()
        self.server = make_server(port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        url = f"ws://127.0.0.1:{self.server.socket.getsockname()[1]}"
        code = secrets.token_urlsafe(24)
        self.sender = App(self.sender_root, SimpleNamespace(role="sender", url=url, code=code, auto=False, test_only=True))
        self.receiver = App(self.receiver_root, SimpleNamespace(role="receiver", url=url, code=code, auto=False, test_only=True))

    def tearDown(self):
        if hasattr(self, "sender"):
            self.sender.close()
            self.receiver.close()
            self.server.shutdown()
            self.thread.join(timeout=3)
            self.sender = self.receiver = None
            self.sender_root = self.receiver_root = None
            gc.collect()  # Tcl resources must be finalized on the UI thread.

    def pump(self, predicate, seconds=3):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.sender_root.update()
            self.receiver_root.update()
            if predicate():
                return
            time.sleep(.01)
        self.fail("GUI condition timed out")

    def test_two_windows_input_emergency_and_disconnect(self):
        self.sender.connect()
        self.receiver.connect()
        self.pump(lambda: self.sender.paired and self.receiver.paired)
        self.assertFalse(self.receiver.armed)
        self.assertIn("disabled", self.sender.live_check.state())
        self.receiver.toggle()
        self.pump(lambda: self.sender.armed and self.receiver.armed)
        self.sender.toggle()
        self.sender.canvas.focus_force()
        self.sender_root.update()
        self.sender.canvas.event_generate("<KeyPress-w>")
        self.pump(lambda: 87 in self.receiver.received_keys)
        self.sender.canvas.event_generate("<KeyRelease-w>")
        self.pump(lambda: 87 not in self.receiver.received_keys)
        self.sender.canvas.event_generate("<Motion>", x=100, y=80)
        self.sender.canvas.event_generate("<ButtonPress-1>", x=100, y=80)
        self.pump(lambda: "left" in self.receiver.received_buttons)
        self.sender.canvas.event_generate("<ButtonRelease-1>", x=100, y=80)
        self.pump(lambda: not self.receiver.received_buttons)
        self.sender.canvas.event_generate("<KeyPress-w>")
        self.pump(lambda: 87 in self.receiver.received_keys)
        self.sender.canvas.event_generate("<KeyPress-F12>")
        self.pump(lambda: not self.sender.active and not self.receiver.received_keys)
        self.assertGreaterEqual(self.receiver.total, 6)
        self.sender.toggle()
        self.sender.disconnect()
        self.pump(lambda: not self.receiver.paired and not self.receiver.consent)


if __name__ == "__main__":
    unittest.main()
