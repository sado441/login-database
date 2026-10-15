import ctypes
from pathlib import Path
import tempfile
import unittest
from interception_output import (InterceptionOutput, KeyStroke, MouseStroke,
                                 absolute_point, key_packet, select_device)
from prepare_interception import prepare


class NativeFake:
    def __init__(self, devices=(1, 4, 11, 13)):
        self.present = devices
        self.sent = []
        self.closed = False
        self.fail = None

    def devices(self):
        return self.present

    def send(self, device, stroke):
        if self.fail and self.fail(device, stroke):
            raise RuntimeError("send failed")
        self.sent.append((device, {name: getattr(stroke, name) for name, _ in stroke._fields_}))

    def close(self):
        self.closed = True


class InterceptionTests(unittest.TestCase):
    def setUp(self):
        self.native = NativeFake()
        self.output = InterceptionOutput(native=self.native, mapper=lambda vk: {87: 0x11, 37: 0xe04b}[vk],
                                         desktop=lambda: (-1000, 0, 2000, 1000))
        self.rect = (-1000, 0, 1000, 1000)

    def tearDown(self):
        self.native.fail = None
        self.output.close()

    def test_official_c_abi_sizes_and_scan_states(self):
        self.assertEqual(ctypes.sizeof(KeyStroke), 8)
        self.assertEqual(ctypes.sizeof(MouseStroke), 20)
        self.assertEqual(MouseStroke.x.offset, 8)
        self.assertEqual(key_packet(0xe04b, True).state, 2)
        self.assertEqual(key_packet(0xe04b, False).state, 3)

    def test_selection_uses_official_one_based_ids(self):
        self.assertEqual(self.output.keyboard_id, 1)
        self.assertEqual(self.output.mouse_id, 11)
        self.assertEqual(select_device('4', self.native.present, True), 4)
        for value, keyboard in [('0', True), ('11', True), ('1', False), ('20', False)]:
            with self.assertRaises(ValueError):
                select_device(value, self.native.present, keyboard)

    def test_missing_device_closes_context(self):
        native = NativeFake(devices=(1,))
        with self.assertRaises(RuntimeError):
            InterceptionOutput(native=native, mapper=lambda _: 1, desktop=lambda: (0, 0, 100, 100))
        self.assertTrue(native.closed)

    def test_key_up_preserves_original_scan_even_if_layout_changes(self):
        self.output.apply(dict(type='key', vk=37, down=True), self.rect)
        self.output.mapper = lambda _: 0x2a
        self.output.apply(dict(type='key', vk=37, down=False), self.rect)
        self.assertEqual(self.native.sent[0], (1, dict(code=0x4b, state=2, information=0)))
        self.assertEqual(self.native.sent[1], (1, dict(code=0x4b, state=3, information=0)))
        self.assertFalse(self.output.keys)

    def test_absolute_virtual_desktop_motion_click_and_two_wheels(self):
        self.assertEqual(absolute_point(-1000, 0, (-1000, 0, 2000, 1000)), (0, 0))
        self.assertEqual(absolute_point(999, 999, (-1000, 0, 2000, 1000)), (65535, 65535))
        self.output.apply(dict(type='move', x=0, y=0), self.rect)
        self.assertEqual(self.native.sent[-1], (11, dict(state=0, flags=3, rolling=0, x=0, y=0, information=0)))
        self.output.apply(dict(type='button', button='left', down=True, x=.5, y=.5), self.rect)
        self.output.apply(dict(type='scroll', dx=-1, dy=2, x=.5, y=.5), self.rect)
        packets = [event for _, event in self.native.sent]
        self.assertEqual([p['state'] for p in packets], [0, 1, 0x400, 0x800])
        self.assertEqual([p['rolling'] for p in packets], [0, 0, 240, -120])

    def test_emergency_release_all_does_not_move_cursor(self):
        self.output.apply(dict(type='key', vk=87, down=True), self.rect)
        self.output.apply(dict(type='button', button='right', down=True, x=.5, y=.5), self.rect)
        self.output.release_all()
        self.assertFalse(self.output.keys or self.output.buttons)
        key, mouse = [event for _, event in self.native.sent[-2:]]
        self.assertEqual(key['state'], 1)
        self.assertEqual((mouse['state'], mouse['flags'], mouse['x'], mouse['y']), (8, 0, 0, 0))

    def test_one_failed_release_does_not_skip_other_releases_and_close(self):
        self.output.apply(dict(type='key', vk=87, down=True), self.rect)
        self.output.apply(dict(type='button', button='left', down=True, x=.5, y=.5), self.rect)
        self.native.fail = lambda device, stroke: device == 1
        with self.assertRaises(RuntimeError):
            self.output.close()
        self.assertTrue(self.native.closed)
        self.assertTrue(self.output.closed)
        self.assertFalse(self.output.buttons)
        self.assertEqual(self.native.sent[-1][1]['state'], 2)

    def test_invalid_event_is_not_sent(self):
        for event in [dict(type='key', vk=123, down=True), dict(type='move', x=2, y=0)]:
            with self.assertRaises(ValueError):
                self.output.apply(event, self.rect)
        self.assertFalse(self.native.sent)

    def test_corrupt_upstream_archive_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'drivers'
            with self.assertRaises(ValueError):
                prepare(b'untrusted content', destination)
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
