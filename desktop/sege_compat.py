"""SEGE-style keyboard.hook capture and optional left/right W/X following.

Behavior reference: s3rc4nn1/SEGE-MACRO, macros/multi.py.
See THIRD_PARTY_NOTICES.md for upstream license and behavior differences.
"""
import time


# keyboard.hook exposes a scan code; distinguish E0 navigation from keypad.
EXTENDED = {'left': 37, 'up': 38, 'right': 39, 'down': 40, 'home': 36,
            'end': 35, 'page up': 33, 'page down': 34, 'insert': 45, 'delete': 46,
            'right ctrl': 163, 'right alt': 165, 'left windows': 91, 'right windows': 92}


class SegeCapture:
    def __init__(self, target, emit, emergency, rect_provider, *, keyboard_backend=None, motion_factory=None, mapper=None):
        if keyboard_backend is None:
            import keyboard as keyboard_backend
        if motion_factory is None:
            from windows_input import Capture as motion_factory
        if mapper is None:
            from local_windows import api
            mapper = lambda scan: api().MapVirtualKeyW(scan, 1)
        self.backend = keyboard_backend
        self.held = set()
        self.stopped = False
        self.motion = None

        def event_callback(event):
            if self.stopped:
                return
            down = event.event_type == 'down'
            scan = event.scan_code
            if scan == 0x58 or getattr(event, 'name', '') == 'f12':
                if down:
                    emergency()
                return
            if type(scan) is not int or not 0 < scan <= 255:
                return
            name = (getattr(event, 'name', '') or '').lower()
            vk = EXTENDED.get(name) if not getattr(event, 'is_keypad', False) else None
            extended = vk is not None
            vk = vk or mapper(scan)
            if not 8 <= vk <= 254 or vk == 123:
                return
            if down and rect_provider():
                self.held.add(vk)
                emit(dict(type='key', vk=vk, down=True, scan_code=scan | (0xe000 if extended else 0)))
            elif not down and vk in self.held:
                self.held.discard(vk)
                emit(dict(type='key', vk=vk, down=False, scan_code=scan | (0xe000 if extended else 0)))

        self.hook = self.backend.hook(event_callback, suppress=False)
        try:
            self.motion = motion_factory(target, emit, emergency, rect_provider=rect_provider, capture_keyboard=False)
        except Exception:
            self.backend.unhook(self.hook)
            raise

    def reset(self):
        self.held.clear()
        if self.motion:
            self.motion.reset()

    def stop(self):
        self.stopped = True
        try:
            self.backend.unhook(self.hook)
        finally:
            if self.motion:
                self.motion.stop()
            self.reset()


class FollowControl:
    """Source's W hold, periodic X pulse; paused while manual keys are held."""
    def __init__(self, emit, clock=time.monotonic):
        self.emit, self.clock = emit, clock
        self.following = self.w_down = self.x_down = False
        self.manual = set()
        self.last_x = self.last_w = float('-inf')
        self.x_until = 0

    def key(self, vk, down):
        self.emit(dict(type='key', vk=vk, down=down, scan_code=0x11 if vk == 87 else 0x2d))

    def release(self):
        if self.x_down:
            self.key(88, False)
            self.x_down = False
        if self.w_down:
            self.key(87, False)
            self.w_down = False

    def physical(self, event):
        if event['down']:
            # Release generated keys BEFORE forwarding the user's own key.
            self.release()
            self.manual.add(event['vk'])
        else:
            self.manual.discard(event['vk'])

    def click(self, button, down):
        if not down:
            return
        if button == 'left':
            self.following = True
        elif button == 'right':
            self.following = False
            self.release()

    def tick(self):
        if not self.following or self.manual:
            self.release()
            return
        now = self.clock()
        if self.x_down:
            if now < self.x_until:
                return
            self.key(88, False)
            self.x_down = False
        elif now - self.last_x >= 1.5:
            self.key(88, True)
            self.x_down = True
            self.x_until, self.last_x = now + .02, now
            return
        if not self.w_down or now - self.last_w >= 2:
            self.key(87, True)
            self.w_down = True
            self.last_w = now

    def stop(self):
        self.following = False
        self.manual.clear()
        self.release()
