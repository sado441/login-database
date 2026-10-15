"""Interception's official C API, output only. No device filters are installed."""
import ctypes as c
import hashlib
from pathlib import Path
import sys
from protocol import validate_event


class KeyStroke(c.Structure):
    _fields_ = [("code", c.c_uint16), ("state", c.c_uint16), ("information", c.c_uint32)]


class MouseStroke(c.Structure):
    _fields_ = [("state", c.c_uint16), ("flags", c.c_uint16), ("rolling", c.c_int16),
                ("x", c.c_int32), ("y", c.c_int32), ("information", c.c_uint32)]


class Native:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Interception yalnız Windows'ta kullanılabilir.")
        from prepare_interception import DLL_HASHES
        arch = "x64" if c.sizeof(c.c_void_p) == 8 else "x86"
        path = Path(__file__).resolve().parent / "drivers" / "Interception-1.0.1" / arch / "interception.dll"
        if not path.is_file():
            raise RuntimeError("Interception DLL bulunamadı. Önce INTERCEPTION_HAZIRLA.bat çalıştır.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != DLL_HASHES[arch]:
            raise RuntimeError("Interception DLL doğrulaması başarısız. Resmi dosyaları yeniden hazırla.")
        try:
            self.dll = c.CDLL(str(path))  # Official API is cdecl, not stdcall.
        except OSError as exc:
            raise RuntimeError("Interception DLL yüklenemedi: " + str(exc)) from exc
        self.dll.interception_create_context.argtypes = []
        self.dll.interception_create_context.restype = c.c_void_p
        self.dll.interception_destroy_context.argtypes = [c.c_void_p]
        self.dll.interception_destroy_context.restype = None
        self.dll.interception_get_hardware_id.argtypes = [c.c_void_p, c.c_int, c.c_void_p, c.c_uint]
        self.dll.interception_get_hardware_id.restype = c.c_uint
        self.dll.interception_send.argtypes = [c.c_void_p, c.c_int, c.c_void_p, c.c_uint]
        self.dll.interception_send.restype = c.c_int
        self.context = self.dll.interception_create_context()
        if not self.context:
            raise RuntimeError("Interception sürücüsüne erişilemiyor. Sürücüyü kurup Windows'u yeniden başlat.")

    def devices(self):
        result = []
        for device in range(1, 21):
            buffer = c.create_unicode_buffer(512)
            if self.dll.interception_get_hardware_id(self.context, device, buffer, c.sizeof(buffer)):
                result.append(device)
        return result

    def send(self, device, stroke):
        if not self.context:
            raise RuntimeError("Interception bağlantısı kapalı.")
        if self.dll.interception_send(self.context, device, c.byref(stroke), 1) != 1:
            raise RuntimeError(f"Interception cihaz {device} girdiyi kabul etmedi; cihaz seçimini kontrol et.")

    def close(self):
        if self.context:
            self.dll.interception_destroy_context(self.context)
            self.context = None


def select_device(value, present, keyboard):
    candidates = [d for d in present if (1 <= d <= 10 if keyboard else 11 <= d <= 20)]
    if value == "Otomatik":
        if candidates:
            return candidates[0]
        raise RuntimeError("Interception bağlı " + ("klavye" if keyboard else "fare") + " bulamadı. Sürücü/yeniden başlatmayı kontrol et.")
    try:
        device = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Geçersiz Interception cihaz kimliği.") from exc
    if device not in candidates:
        raise ValueError("Seçilen cihaz bulunamadı veya yanlış türde. CİHAZLARI BUL ile yenile.")
    return device


def key_packet(scan, down):
    if not scan or scan >> 8 not in (0, 0xE0, 0xE1):
        raise ValueError("Tuş scan code'a çevrilemedi.")
    prefix = {0: 0, 0xE0: 2, 0xE1: 4}[scan >> 8]
    return KeyStroke(scan & 0xff, prefix | (0 if down else 1), 0)


def absolute_point(x, y, desktop):
    left, top, width, height = desktop
    if width <= 1 or height <= 1:
        raise ValueError("Ekran boyutu okunamadı.")
    return (max(0, min(65535, round((x-left) * 65535 / (width-1)))),
            max(0, min(65535, round((y-top) * 65535 / (height-1)))))


class InterceptionOutput:
    BUTTONS = {"left": (1, 2), "right": (4, 8), "middle": (16, 32)}

    def __init__(self, keyboard_id="Otomatik", mouse_id="Otomatik", *, native=None, mapper=None, desktop=None):
        self.native = native if native is not None else Native()
        self.keys, self.buttons = {}, set()
        self.closed = False
        try:
            present = self.native.devices()
            self.keyboard_id = select_device(keyboard_id, present, True)
            self.mouse_id = select_device(mouse_id, present, False)
            if mapper is None or desktop is None:
                from ctypes import wintypes
                user = c.WinDLL("user32", use_last_error=True)
                user.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
                user.MapVirtualKeyW.restype = wintypes.UINT
                mapper = mapper or (lambda vk: user.MapVirtualKeyW(vk, 4))
                desktop = desktop or (lambda: tuple(user.GetSystemMetrics(i) for i in (76, 77, 78, 79)))
            self.mapper, self.desktop = mapper, desktop
        except Exception:
            self.native.close()
            self.closed = True
            raise

    def apply(self, event, rect):
        if self.closed:
            raise RuntimeError("Interception çıktısı kapalı.")
        event = validate_event(event)
        if event["type"] == "key":
            vk, down = event["vk"], event["down"]
            if vk == 19:
                raise ValueError("Pause/Break tuşu bu sürümde aktarılmıyor.")
            if down and vk not in self.keys:
                packet = key_packet(self.mapper(vk), True)
                self.keys[vk] = (packet.code, packet.state)
                self.native.send(self.keyboard_id, packet)
            elif not down and vk in self.keys:
                code, prefix = self.keys[vk]
                self.native.send(self.keyboard_id, KeyStroke(code, prefix | 1, 0))
                del self.keys[vk]
            return
        left, top, width, height = rect
        x, y = absolute_point(left + round(event["x"] * (width-1)),
                              top + round(event["y"] * (height-1)), self.desktop())
        # ABSOLUTE | VIRTUAL_DESKTOP supports different monitor origins.
        if event["type"] == "move":
            self.native.send(self.mouse_id, MouseStroke(0, 3, 0, x, y, 0))
        elif event["type"] == "button":
            name, down = event["button"], event["down"]
            if down:
                self.buttons.add(name)
            self.native.send(self.mouse_id, MouseStroke(self.BUTTONS[name][0 if down else 1], 3, 0, x, y, 0))
            if not down:
                self.buttons.discard(name)
        elif event["type"] == "scroll":
            for delta, state in ((event["dy"], 0x400), (event["dx"], 0x800)):
                if delta:
                    self.native.send(self.mouse_id, MouseStroke(state, 3, delta*120, x, y, 0))

    def release_all(self):
        if self.closed:
            return
        errors = []
        for vk, (code, prefix) in list(self.keys.items()):
            try:
                self.native.send(self.keyboard_id, KeyStroke(code, prefix | 1, 0))
                del self.keys[vk]
            except Exception as exc:
                errors.append(str(exc))
        for name in list(self.buttons):
            try:
                # Relative zero-motion release: don't jump the user's cursor.
                self.native.send(self.mouse_id, MouseStroke(self.BUTTONS[name][1], 0, 0, 0, 0, 0))
                self.buttons.discard(name)
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError("Bazı girdiler bırakılamadı: " + "; ".join(errors))

    def close(self):
        if not self.closed:
            try:
                self.release_all()
            finally:
                self.native.close()
                self.closed = True
