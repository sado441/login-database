"""Windows-only adapters. Imported lazily; test mode never injects input."""
import ctypes
from ctypes import wintypes


def target_rect(title_fragment):
    if not title_fragment.strip():
        return None
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    hwnd = user.GetForegroundWindow()
    title = ctypes.create_unicode_buffer(512)
    user.GetWindowTextW(hwnd, title, len(title))
    if title_fragment.casefold() not in title.value.casefold():
        return None
    rect, origin = wintypes.RECT(), wintypes.POINT()
    if not user.GetClientRect(hwnd, ctypes.byref(rect)) or not user.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    if rect.right <= 0 or rect.bottom <= 0:
        return None
    return origin.x, origin.y, rect.right, rect.bottom


class Output:
    def __init__(self):
        from pynput import keyboard, mouse
        self.keyboard_module, self.mouse_module = keyboard, mouse
        self.kb, self.mouse = keyboard.Controller(), mouse.Controller()
        self.keys, self.buttons = set(), set()

    def apply(self, event, rect):
        kind = event["type"]
        if kind == "key":
            vk = event["vk"]
            key = self.keyboard_module.KeyCode.from_vk(vk)
            if event["down"]:
                if vk not in self.keys:
                    self.keys.add(vk)
                    self.kb.press(key)
            elif vk in self.keys:
                self.kb.release(key)
                self.keys.discard(vk)
        else:
            x, y, width, height = rect
            self.mouse.position = (x + round(event["x"] * (width - 1)),
                                   y + round(event["y"] * (height - 1)))
            if kind == "button":
                name = event["button"]
                button = getattr(self.mouse_module.Button, name)
                if event["down"]:
                    if name not in self.buttons:
                        self.buttons.add(name)
                        self.mouse.press(button)
                elif name in self.buttons:
                    self.mouse.release(button)
                    self.buttons.discard(name)
            elif kind == "scroll":
                self.mouse.scroll(event["dx"], event["dy"])

    def release_all(self):
        # Releases are unconditional, including after focus/connection loss.
        for vk in list(self.keys):
            try:
                self.kb.release(self.keyboard_module.KeyCode.from_vk(vk))
                self.keys.discard(vk)
            except Exception:
                pass
        for name in list(self.buttons):
            try:
                self.mouse.release(getattr(self.mouse_module.Button, name))
                self.buttons.discard(name)
            except Exception:
                pass


class Capture:
    def __init__(self, target, emit, emergency, rect_provider=None, capture_keyboard=True):
        from pynput import keyboard, mouse
        import time
        self.target, self.emit = target, emit
        get_rect = rect_provider or (lambda: target_rect(self.target))
        self.keys, self.buttons = set(), set()
        self.last_move = 0

        def on_key(key, down):
            vk = getattr(key, "vk", None)
            if vk is None:
                vk = getattr(getattr(key, "value", None), "vk", None)
            if vk == 123:
                if down:
                    emergency()
                return
            if vk is None or not 8 <= vk <= 254:
                return
            if down and get_rect() and vk not in self.keys:
                self.keys.add(vk)
                emit({"type": "key", "vk": vk, "down": True})
            elif not down and vk in self.keys:
                self.keys.discard(vk)
                emit({"type": "key", "vk": vk, "down": False})

        def position(x, y):
            rect = get_rect()
            if not rect:
                return None
            left, top, w, h = rect
            if not (left <= x < left + w and top <= y < top + h):
                return None
            return {"x": (x - left) / max(1, w - 1), "y": (y - top) / max(1, h - 1)}

        def move(x, y):
            pos = position(x, y)
            if pos and time.monotonic() - self.last_move >= 1 / 30:
                self.last_move = time.monotonic()
                emit(dict(type="move", **pos))

        def click(x, y, button, down):
            name = button.name
            if name not in {"left", "right", "middle"}:
                return
            pos = position(x, y)
            if down and pos:
                self.buttons.add(name)
                emit(dict(type="button", button=name, down=True, **pos))
            elif not down and name in self.buttons:
                self.buttons.discard(name)
                emit(dict(type="button", button=name, down=False, **(pos or {"x": 0.5, "y": 0.5})))

        def scroll(x, y, dx, dy):
            pos = position(x, y)
            if pos:
                emit(dict(type="scroll", dx=max(-10, min(10, int(dx))),
                          dy=max(-10, min(10, int(dy))), **pos))

        self.kb = keyboard.Listener(on_press=lambda k: on_key(k, True),
                                    on_release=lambda k: on_key(k, False),
                                    win32_event_filter=lambda msg, data: not (data.flags & 0x10)) if capture_keyboard else None
        self.mouse = mouse.Listener(on_move=move, on_click=click, on_scroll=scroll,
                                    win32_event_filter=lambda msg, data: not (data.flags & 0x01))
        if self.kb:
            self.kb.start()
        self.mouse.start()

    def reset(self):
        self.keys.clear()
        self.buttons.clear()

    def stop(self):
        if self.kb:
            self.kb.stop()
        self.mouse.stop()
        self.reset()
