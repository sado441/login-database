import gc
import time
import tkinter as tk
import unittest
from unittest.mock import Mock
from local_windows import Window
from background_probe import ProbeApp, PulseTransport


class ProbeGuiTests(unittest.TestCase):
    def test_20_rounds_two_targets_without_keyboard_input(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest('No graphical display')
        api, gui = Mock(), Mock()
        api.MapVirtualKey.return_value = 87
        gui.IsWindow.return_value = True
        transport = PulseTransport(api, gui, owner_valid=lambda _: True)
        app = ProbeApp(root, [Window(100, 1, 'one'), Window(101, 2, 'two')], transport)
        try:
            # Skip real waits in this GUI test; pulse duration is checked separately.
            app.cancel = Mock()
            app.cancel.is_set.return_value = False
            app.cancel.wait.return_value = False
            app.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                root.update()
                if transport.ups == 40 and not app.worker.is_alive() and 'Test bitti' in app.status.get():
                    break
                time.sleep(.01)
            self.assertEqual((transport.activations, transport.downs, transport.ups), (40, 40, 40))
            self.assertIn('Test bitti', app.status.get())
            self.assertEqual({call.args[0] for call in api.PostMessage.call_args_list}, {100, 101})
        finally:
            app.close()
            app = root = None
            gc.collect()
