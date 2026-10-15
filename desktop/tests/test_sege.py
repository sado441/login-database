from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from sege_compat import SegeCapture, FollowControl
from local_router import LocalRouter


class CaptureTests(unittest.TestCase):
    def test_scan_code_repeat_focus_release_and_f12(self):
        saved = {}
        backend = SimpleNamespace(hook=lambda callback, **kw: saved.setdefault('callback', callback), unhook=Mock())
        mouse = Mock()
        region = [None]
        events, halt = [], Mock()
        capture = SegeCapture('', events.append, halt, lambda: region[0],
                              keyboard_backend=backend, motion_factory=Mock(return_value=mouse), mapper=lambda _: 87)
        key = lambda kind: SimpleNamespace(event_type=kind, scan_code=0x11, name='w', is_keypad=False)
        saved['callback'](key('down'))
        self.assertEqual(events, [])
        region[0] = (0, 0, 100, 100)
        saved['callback'](key('down'))
        saved['callback'](key('down'))
        region[0] = None
        saved['callback'](key('up'))
        self.assertEqual([e['down'] for e in events], [True, True, False])
        self.assertTrue(all(e['scan_code'] == 0x11 for e in events))
        saved['callback'](SimpleNamespace(event_type='down', scan_code=0x58, name='f12'))
        halt.assert_called_once()
        capture.stop()
        backend.unhook.assert_called_once()
        mouse.stop.assert_called_once()
        saved['callback'](key('down'))
        self.assertEqual(len(events), 3)

    def test_extended_arrow_and_keypad_are_distinct(self):
        saved = {}
        backend = SimpleNamespace(hook=lambda callback, **kw: saved.setdefault('callback', callback), unhook=Mock())
        events = []
        capture = SegeCapture('', events.append, Mock(), lambda: (0, 0, 100, 100),
                              keyboard_backend=backend, motion_factory=Mock(return_value=Mock()), mapper=lambda _: 100)
        for keypad in (False, True):
            saved['callback'](SimpleNamespace(event_type='down', scan_code=0x4b, name='left', is_keypad=keypad))
        self.assertEqual([(e['vk'], e['scan_code']) for e in events], [(37, 0xe04b), (100, 0x4b)])
        capture.stop()

    def test_mouse_listener_failure_removes_keyboard_hook(self):
        backend = SimpleNamespace(hook=Mock(return_value='hook'), unhook=Mock())
        with self.assertRaises(RuntimeError):
            SegeCapture('', Mock(), Mock(), lambda: None, keyboard_backend=backend,
                        motion_factory=Mock(side_effect=RuntimeError('mouse failed')), mapper=lambda _: 87)
        backend.unhook.assert_called_once_with('hook')

    def test_router_preserves_valid_scan_and_rejects_invalid(self):
        output = Mock()
        router = LocalRouter('a', {'b': output}, lambda: True, lambda _: True)
        router.start()
        event = dict(type='key', vk=87, down=True, scan_code=0x11)
        router.route(event)
        output.apply.assert_called_with(event)
        for scan in (0, -1, True, 0x2222, '17'):
            with self.assertRaises(ValueError):
                router.route(dict(event, scan_code=scan))


class FollowTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.events = []
        self.follow = FollowControl(self.events.append, clock=lambda: self.now)

    def test_left_click_x_pulse_w_hold_refresh_right_click_stop(self):
        self.follow.click('left', True)
        self.follow.tick()
        self.assertEqual([(e['vk'], e['down']) for e in self.events], [(88, True)])
        self.now = .03
        self.follow.tick()
        self.assertEqual([(e['vk'], e['down']) for e in self.events], [(88, True), (88, False), (87, True)])
        self.now = 1.6
        self.follow.tick()
        self.assertTrue(self.follow.x_down)
        self.now = 1.63
        self.follow.tick()
        self.now = 2.1
        self.follow.tick()
        self.assertEqual(sum(e['vk'] == 87 and e['down'] for e in self.events), 2)
        self.follow.click('right', True)
        self.assertFalse(self.follow.w_down or self.follow.x_down or self.follow.following)
        self.assertEqual(self.events[-1]['down'], False)

    def test_manual_keys_pause_follow_until_all_released(self):
        self.follow.click('left', True)
        self.follow.tick()
        self.now = .03
        self.follow.tick()
        self.follow.physical(dict(vk=49, down=True))
        self.assertFalse(self.follow.w_down)
        self.follow.physical(dict(vk=50, down=True))
        self.follow.physical(dict(vk=49, down=False))
        count = len(self.events)
        self.follow.tick()
        self.assertEqual(len(self.events), count)
        self.follow.physical(dict(vk=50, down=False))
        self.follow.tick()
        self.assertTrue(self.follow.w_down)
        self.follow.stop()
        self.assertFalse(self.follow.w_down or self.follow.x_down)


if __name__ == '__main__':
    unittest.main()
