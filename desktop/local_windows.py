"""Explicitly selected HWNDs only. Background messages, no focus switching."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from functools import lru_cache


@dataclass(frozen=True)
class Window:
    hwnd: int
    pid: int
    title: str

    @property
    def identity(self):
        return self.hwnd, self.pid

    @property
    def label(self):
        return f"{self.title} | PID {self.pid} | HWND {self.hwnd:#x}"


@lru_cache(maxsize=1)
def api():
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    for name in ("IsWindow", "IsWindowVisible", "IsIconic"):
        getattr(user, name).argtypes = [wintypes.HWND]
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.PostMessageW.restype = wintypes.BOOL
    user.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    return user


def enumerate_windows():
    user = api()
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def collect(hwnd, _):
        if user.IsWindowVisible(hwnd) and not user.IsIconic(hwnd):
            title = ctypes.create_unicode_buffer(512)
            user.GetWindowTextW(hwnd, title, len(title))
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if title.value.strip() and pid.value != os.getpid():
                result.append(Window(int(hwnd), pid.value, title.value))
        return True

    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows(collect, 0)
    return sorted(result, key=lambda w: (w.title.casefold(), w.hwnd))


def valid(window, cleanup=False):
    user = api()
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(window.hwnd, ctypes.byref(pid))
    return (bool(user.IsWindow(window.hwnd)) and pid.value == window.pid
            and (cleanup or (bool(user.IsWindowVisible(window.hwnd)) and not user.IsIconic(window.hwnd))))


def foreground(window):
    return valid(window) and api().GetForegroundWindow() == window.hwnd


def rect(window, foreground_only=False):
    if not valid(window) or (foreground_only and not foreground(window)):
        return None
    user, client, point = api(), wintypes.RECT(), wintypes.POINT()
    if not user.GetClientRect(window.hwnd, ctypes.byref(client)) or not user.ClientToScreen(window.hwnd, ctypes.byref(point)):
        return None
    if client.right <= 0 or client.bottom <= 0:
        return None
    return point.x, point.y, client.right, client.bottom


def key_lparam(vk, down, scan):
    # MapVirtualKeyW(MAPVK_VK_TO_VSC_EX) returns E0/E1 in the high byte.
    value = 1 | ((scan & 0xff) << 16)
    if scan & 0xff00:
        value |= 1 << 24
    if not down:
        value |= (1 << 30) | (1 << 31)
    return value


def coordinates(event, width, height):
    return round(event["x"] * (width - 1)), round(event["y"] * (height - 1))


def packed_point(x, y):
    return (int(x) & 0xffff) | ((int(y) & 0xffff) << 16)


class BackgroundOutput:
    BUTTONS = {"left": (0x201, 0x202, 1), "right": (0x204, 0x205, 2), "middle": (0x207, 0x208, 0x10)}

    def __init__(self, window, sege_compatible=False):
        self.window = window
        self.user = api()
        self.keys, self.buttons = set(), set()
        self.point = (0, 0)
        self.sege_compatible = sege_compatible
        self.scans = {}

    def post(self, message, wp, lp, cleanup=False):
        if not valid(self.window, cleanup=cleanup):
            raise RuntimeError("Alıcı pencere kapandı veya küçültüldü.")
        ctypes.set_last_error(0)
        if not self.user.PostMessageW(self.window.hwnd, message, wp, lp):
            raise ctypes.WinError(ctypes.get_last_error())

    def key(self, vk, down, scan=None, repeat=False):
        scan = scan if scan is not None else self.user.MapVirtualKeyW(vk, 4)
        if getattr(self, 'sege_compatible', False):
            # Matches SEGE multi.py: WM_ACTIVATE / WA_ACTIVE before each key.
            # This is an application message, not SetForegroundWindow.
            self.post(0x006, 1, 0, cleanup=not down)
        lp = key_lparam(vk, down, scan)
        if down and repeat:
            lp |= 1 << 30
        self.post(0x100 if down else 0x101, vk, lp, cleanup=not down)

    def flags(self):
        flags = sum(self.BUTTONS[name][2] for name in self.buttons)
        if self.keys & {16, 160, 161}:
            flags |= 4
        if self.keys & {17, 162, 163}:
            flags |= 8
        return flags

    def apply(self, event):
        if event["type"] == "key":
            vk, down = event["vk"], event["down"]
            scans = getattr(self, 'scans', None)
            if scans is None:
                self.scans = scans = {}
            scan = scans.get(vk, event.get('scan_code'))
            if scan is None:
                scan = self.user.MapVirtualKeyW(vk, 4)
            repeated = vk in self.keys
            if down and (not repeated or getattr(self, 'sege_compatible', False)):
                self.keys.add(vk)
                scans[vk] = scan
                self.key(vk, True, scan, repeat=repeated)
            elif not down and vk in self.keys:
                self.key(vk, False, scan)
                self.keys.discard(vk)
                scans.pop(vk, None)
            return
        geometry = rect(self.window)
        if not geometry:
            raise RuntimeError("Alıcı pencere boyutu okunamadı.")
        left, top, width, height = geometry
        self.point = coordinates(event, width, height)
        point = packed_point(*self.point)
        if event["type"] == "move":
            self.post(0x200, self.flags(), point)
        elif event["type"] == "button":
            name, down = event["button"], event["down"]
            if down:
                self.buttons.add(name)
            else:
                self.buttons.discard(name)
            self.post(self.BUTTONS[name][0 if down else 1], self.flags(), point)
        elif event["type"] == "scroll":
            for delta, message in ((event["dy"], 0x20A), (event["dx"], 0x20E)):
                if delta:
                    self.post(message, self.flags() | ((delta * 120 & 0xffff) << 16),
                              packed_point(left + self.point[0], top + self.point[1]))

    def release_all(self):
        # Closing/minimizing a window must not prevent releases to other windows.
        errors = []
        for vk in list(self.keys):
            try:
                self.key(vk, False, getattr(self, 'scans', {}).get(vk))
                self.keys.discard(vk)
                getattr(self, 'scans', {}).pop(vk, None)
            except Exception as exc:
                errors.append(str(exc))
        for name in list(self.buttons):
            try:
                remaining = self.buttons - {name}
                flags = sum(self.BUTTONS[n][2] for n in remaining)
                self.post(self.BUTTONS[name][1], flags, packed_point(*self.point), cleanup=True)
                self.buttons.discard(name)
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError("; ".join(errors))
