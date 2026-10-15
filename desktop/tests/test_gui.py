"""End-to-end Tk test. Skipped when no desktop/display is available."""
import secrets
import threading
import time
from types import SimpleNamespace
import tkinter as tk
import unittest
import gc
from unittest.mock import Mock, patch
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

    def test_live_receiver_selects_interception_and_closes_it(self):
        output = Mock(keyboard_id=1, mouse_id=11)
        self.sender.connect()
        self.receiver.live_var.set(True)
        listener = Mock()
        pynput = SimpleNamespace(keyboard=SimpleNamespace(Listener=lambda **kwargs: listener))
        with patch('app.sys', SimpleNamespace(platform='win32')), \
                patch.dict('sys.modules', {'pynput': pynput}), \
                patch('app.messagebox.askyesno', return_value=True), \
                patch('interception_output.InterceptionOutput', return_value=output) as factory:
            self.receiver.connect()
        factory.assert_called_once_with('Otomatik', 'Otomatik')
        with patch('windows_input.target_rect', return_value=(0, 0, 1000, 500)):
            self.pump(lambda: self.sender.paired and self.receiver.paired)
            self.receiver.toggle()
            self.pump(lambda: self.sender.armed and self.receiver.armed)
            self.sender.toggle()
            self.sender.canvas.focus_force()
            self.sender_root.update()
            self.sender.canvas.event_generate('<KeyPress-w>')
            self.pump(lambda: output.apply.called)
            output.apply.assert_called_with(dict(type='key', vk=87, down=True), (0, 0, 1000, 500))
            self.receiver.disconnect()
        self.assertTrue(output.release_all.called)
        output.close.assert_called_once()
        listener.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
