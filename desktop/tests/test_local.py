import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from local_router import LocalRouter
from local_windows import BackgroundOutput, Window, coordinates, key_lparam, packed_point


class Sink:
    def __init__(self):
        self.events, self.keys = [], set()
        self.released = 0

    def apply(self, event):
        self.events.append(event.copy())
        if event["type"] == "key":
            (self.keys.add if event["down"] else self.keys.discard)(event["vk"])

    def release_all(self):
        self.keys.clear()
        self.released += 1


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.focus = False
        self.valid = {"master", "one", "two"}
        self.one, self.two = Sink(), Sink()
        self.router = LocalRouter("master", {"one": self.one, "two": self.two},
                                  lambda: self.focus, lambda w: w in self.valid)
        self.router.start()

    def test_two_targets_receive_keys_mouse_wheel_but_source_is_excluded(self):
        self.assertFalse(self.router.route(dict(type="key", vk=87, down=True)))
        self.focus = True
        events = [dict(type="key", vk=87, down=True), dict(type="move", x=.5, y=.8),
                  dict(type="button", x=.5, y=.8, button="left", down=True),
                  dict(type="scroll", x=.5, y=.8, dx=0, dy=1),
                  dict(type="key", vk=87, down=False)]
        for event in events:
            self.assertTrue(self.router.route(event))
        self.assertEqual(self.one.events, events)
        self.assertEqual(self.two.events, events)
        self.assertNotIn("master", self.router.outputs)
        self.assertEqual(self.router.total, 5)

    def test_focus_loss_releases_both_and_does_not_auto_resume(self):
        self.focus = True
        self.router.route(dict(type="key", vk=87, down=True))
        self.focus = False
        self.assertFalse(self.router.poll())
        self.assertFalse(self.router.running)
        self.assertFalse(self.one.keys or self.two.keys)
        self.focus = True
        self.assertFalse(self.router.route(dict(type="key", vk=65, down=True)))

    def test_target_closed_stops_all_targets(self):
        self.focus = True
        self.router.route(dict(type="key", vk=87, down=True))
        self.valid.remove("one")
        self.router.poll()
        self.assertFalse(self.router.running)
        self.assertEqual(self.two.released, 1)

    def test_failed_output_releases_every_other_output(self):
        self.focus = True
        self.two.apply = Mock(side_effect=OSError("Target rejected input"))
        with self.assertRaises(OSError):
            self.router.route(dict(type="key", vk=87, down=True))
        self.assertFalse(self.router.running)
        self.assertFalse(self.one.keys)
        self.assertEqual(self.one.released, 1)
        self.assertEqual(self.two.released, 1)

    def test_release_failure_does_not_skip_other_targets(self):
        self.one.release_all = Mock(side_effect=OSError("Closed"))
        self.router.stop()
        self.assertEqual(self.two.released, 1)
        self.assertIn("Closed", self.router.reason)

    def test_source_cannot_be_selected_as_target(self):
        with self.assertRaises(ValueError):
            LocalRouter("master", {"master": Sink()}, lambda: True, lambda _: True)


class MessageTests(unittest.TestCase):
    def sink(self):
        output = BackgroundOutput.__new__(BackgroundOutput)
        output.user = Mock()
        output.user.MapVirtualKeyW.return_value = 0x1e
        output.window = Window(100, 200, "game")
        output.keys, output.buttons = set(), set()
        output.point = (0, 0)
        output.post = Mock()
        return output

    def test_win32_key_up_extended_and_mouse_scaling(self):
        self.assertEqual(key_lparam(37, True, 0xe04b), 1 | (0x4b << 16) | (1 << 24))
        self.assertEqual(key_lparam(65, False, 0x1e), 1 | (0x1e << 16) | (3 << 30))
        self.assertEqual(coordinates({"x": 1, "y": .5}, 1920, 1080), (1919, 540))
        self.assertEqual(packed_point(-5, 10), 65531 | (10 << 16))

    def test_tracked_keys_and_buttons_get_released(self):
        sink = self.sink()
        sink.apply(dict(type="key", vk=65, down=True))
        with patch('local_windows.rect', return_value=(50, 60, 1000, 500)):
            sink.apply(dict(type="button", button="left", down=True, x=.5, y=.5))
        self.assertEqual(sink.keys, {65})
        self.assertEqual(sink.buttons, {"left"})
        sink.release_all()
        self.assertFalse(sink.keys or sink.buttons)
        messages = [call.args[0] for call in sink.post.call_args_list]
        self.assertEqual(messages, [0x100, 0x201, 0x101, 0x202])
        self.assertTrue(sink.post.call_args_list[-1].kwargs['cleanup'])

    def test_sege_activation_raw_scan_repeat_and_cleanup_order(self):
        sink = self.sink()
        sink.sege_compatible = True
        event = dict(type='key', vk=87, down=True, scan_code=0x11)
        sink.apply(event)
        sink.apply(event)
        sink.release_all()
        calls = sink.post.call_args_list
        self.assertEqual([c.args[0] for c in calls], [0x006, 0x100, 0x006, 0x100, 0x006, 0x101])
        self.assertEqual(calls[0].args, (0x006, 1, 0))
        self.assertEqual(calls[1].args[2], 1 | (0x11 << 16))
        self.assertEqual(calls[3].args[2], 1 | (0x11 << 16) | (1 << 30))
        self.assertEqual(calls[5].args[2], 1 | (0x11 << 16) | (3 << 30))
        self.assertFalse(sink.keys or sink.scans)


class CaptureTests(unittest.TestCase):
    def test_exact_window_provider_focus_gate_and_emergency(self):
        from windows_input import Capture
        listeners = []

        def listener(**callbacks):
            instance = SimpleNamespace(callbacks=callbacks, start=Mock(), stop=Mock())
            listeners.append(instance)
            return instance

        fake = SimpleNamespace(keyboard=SimpleNamespace(Listener=listener), mouse=SimpleNamespace(Listener=listener))
        events, emergency = [], Mock()
        region = [None]
        with patch.dict('sys.modules', {'pynput': fake}):
            capture = Capture('unused', events.append, emergency, rect_provider=lambda: region[0])
            keys, mouse = [item.callbacks for item in listeners]
            keys['on_press'](SimpleNamespace(vk=87))
            self.assertEqual(events, [])
            region[0] = (50, 60, 101, 101)
            keys['on_press'](SimpleNamespace(vk=87))
            mouse['on_move'](100, 110)
            self.assertEqual(events[0], dict(type='key', vk=87, down=True))
            self.assertEqual(events[1], dict(type='move', x=.5, y=.5))
            region[0] = None
            keys['on_release'](SimpleNamespace(vk=87))
            self.assertFalse(events[-1]['down'])
            keys['on_press'](SimpleNamespace(vk=123))
            emergency.assert_called_once()
            self.assertFalse(keys['win32_event_filter'](0, SimpleNamespace(flags=0x10)))
            capture.stop()
            self.assertTrue(all(item.stop.called for item in listeners))


if __name__ == "__main__":
    unittest.main()
