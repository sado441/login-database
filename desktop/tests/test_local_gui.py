import tkinter as tk
import time
import unittest
import gc
from unittest.mock import Mock
from local_gui import LocalApp


class LocalGuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("No graphical display")
        self.app = LocalApp(self.root)

    def tearDown(self):
        if hasattr(self, 'app'):
            self.app.close()
            self.app = None
            self.root = None
            gc.collect()

    def pump(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            self.root.update()
            if predicate():
                return
            time.sleep(.01)
        self.fail("GUI condition timed out")

    def test_three_panels_fanout_mouse_and_f12(self):
        self.app.start_demo()
        canvas = self.app.demo_source
        self.pump(lambda: self.root.focus_get() == canvas)
        canvas.event_generate('<KeyPress-w>')
        self.pump(lambda: all(87 in sink.keys for sink in self.app.demo_outputs))
        canvas.event_generate('<KeyRelease-w>')
        self.pump(lambda: all(not sink.keys for sink in self.app.demo_outputs))
        canvas.event_generate('<ButtonPress-1>', x=50, y=60)
        self.pump(lambda: all('left' in sink.buttons for sink in self.app.demo_outputs))
        canvas.event_generate('<KeyPress-F12>')
        self.pump(lambda: not self.app.router.running)
        self.assertTrue(all(not sink.keys and not sink.buttons for sink in self.app.demo_outputs))
        self.assertIn('Yönlendirilen: 3', self.app.diagnostics.get())
        self.assertIn('Ana odak görüldü: evet', self.app.diagnostics.get())

    def test_focus_loss_and_closed_demo_release_both_receivers(self):
        self.app.start_demo()
        canvas = self.app.demo_source
        self.pump(lambda: self.root.focus_get() == canvas)
        canvas.event_generate('<KeyPress-w>')
        self.pump(lambda: all(87 in sink.keys for sink in self.app.demo_outputs))
        self.root.focus_force()
        self.pump(lambda: not self.app.router.running)
        self.assertTrue(all(not sink.keys for sink in self.app.demo_outputs))
        self.assertIn('Yakalanan: 1', self.app.diagnostics.get())
        self.assertIn('Yönlendirilen: 1', self.app.diagnostics.get())
        self.assertIn('Son olay: VK 87 bas', self.app.diagnostics.get())
        self.app.close_demo()
        self.assertEqual(self.app.demo_windows, [])

    def test_sege_follow_left_click_starts_w_right_click_releases_both(self):
        self.app.follow_var.set(True)
        self.app.start_demo()
        canvas = self.app.demo_source
        self.pump(lambda: self.root.focus_get() == canvas)
        canvas.event_generate('<ButtonPress-1>', x=50, y=60)
        self.pump(lambda: all(87 in sink.keys for sink in self.app.demo_outputs))
        canvas.event_generate('<ButtonRelease-1>', x=50, y=60)
        canvas.event_generate('<ButtonPress-3>', x=50, y=60)
        self.pump(lambda: all(not sink.keys for sink in self.app.demo_outputs))
        self.assertFalse(self.app.follow.following)
        self.app.stop()

    def test_listener_stop_error_still_releases_both_receivers(self):
        self.app.start_demo()
        canvas = self.app.demo_source
        self.pump(lambda: self.root.focus_get() == canvas)
        canvas.event_generate('<KeyPress-w>')
        self.pump(lambda: all(87 in sink.keys for sink in self.app.demo_outputs))
        self.app.capture = Mock()
        self.app.capture.stop.side_effect = RuntimeError('hook failed')
        self.app.stop()
        self.assertTrue(all(not sink.keys for sink in self.app.demo_outputs))
        self.assertIn('hook failed', self.app.status.get())
        self.assertIsNone(self.app.capture)


if __name__ == '__main__':
    unittest.main()
