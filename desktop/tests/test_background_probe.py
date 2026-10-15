import unittest
from unittest.mock import Mock
from local_windows import Window
from background_probe import PulseTransport


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock()
        self.api.MapVirtualKey.return_value = 87
        self.gui = Mock()
        self.gui.IsWindow.return_value = True
        self.transport = PulseTransport(self.api, self.gui, owner_valid=lambda _: True)
        self.window = Window(100, 200, 'game')
        self.cancel = Mock()
        self.cancel.is_set.return_value = False

    def test_original_pywin32_call_order_lparam_and_10ms_wait(self):
        self.transport.pulse(self.window, 'W', self.cancel)
        calls = [c.args for c in self.api.PostMessage.call_args_list]
        self.assertEqual(calls, [(100, 0x006, 1, 0), (100, 0x100, 87, 1 | (0x11 << 16)),
                                 (100, 0x101, 87, 1 | (0x11 << 16) | (3 << 30))])
        self.api.MapVirtualKey.assert_called_once_with(0x11, 1)
        self.cancel.wait.assert_called_once_with(.01)
        self.assertEqual((self.transport.activations, self.transport.downs, self.transport.ups), (1, 1, 1))

    def test_stop_during_pulse_still_releases_key(self):
        self.cancel.wait.return_value = True
        self.transport.pulse(self.window, 'W', self.cancel)
        self.assertEqual(self.api.PostMessage.call_args_list[-1].args[1], 0x101)
        self.assertEqual(self.transport.ups, 1)

    def test_send_failure_still_attempts_release(self):
        def post(hwnd, msg, wp, lp):
            if msg == 0x100:
                raise OSError('key down failed')
        self.api.PostMessage.side_effect = post
        with self.assertRaises(OSError):
            self.transport.pulse(self.window, 'W', self.cancel)
        self.assertEqual(self.api.PostMessage.call_args_list[-1].args[1], 0x101)

    def test_closed_or_changed_target_is_not_used(self):
        self.transport.owner_valid = lambda _: False
        with self.assertRaises(RuntimeError):
            self.transport.pulse(self.window, 'W', self.cancel)
        self.api.PostMessage.assert_not_called()


if __name__ == '__main__':
    unittest.main()
