"""Small, explicitly validated input protocol; no remote commands or files."""
import ipaddress
from urllib.parse import urlsplit

MAX_MESSAGE = 4096
BUTTONS = {"left", "right", "middle"}


def check_url(url):
    parsed = urlsplit(url)
    if parsed.username or parsed.password or not parsed.hostname or parsed.fragment:
        raise ValueError("Geçersiz sunucu adresi.")
    local = parsed.hostname.lower() == "localhost"
    try:
        local = local or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        pass
    if parsed.scheme != "wss" and not (parsed.scheme == "ws" and local):
        raise ValueError("İnternet bağlantısında wss:// gerekir; ws:// sadece yerel test içindir.")
    return url


def validate_event(event):
    if not isinstance(event, dict):
        raise ValueError("Olay nesne olmalı.")
    kind = event.get("type")
    if kind == "key":
        if type(event.get("vk")) is not int or not 8 <= event["vk"] <= 254:
            raise ValueError("Geçersiz tuş.")
        if event["vk"] == 123:  # F12 is always local emergency stop.
            raise ValueError("F12 aktarılamaz.")
        if type(event.get("down")) is not bool:
            raise ValueError("Geçersiz tuş durumu.")
        return {"type": kind, "vk": event["vk"], "down": event["down"]}
    if kind in {"move", "button", "scroll"}:
        for axis in ("x", "y"):
            if type(event.get(axis)) not in (float, int) or not 0 <= event[axis] <= 1:
                raise ValueError("Geçersiz konum.")
        result = {"type": kind, "x": event["x"], "y": event["y"]}
        if kind == "button":
            if event.get("button") not in BUTTONS or type(event.get("down")) is not bool:
                raise ValueError("Geçersiz fare düğmesi.")
            result.update(button=event["button"], down=event["down"])
        if kind == "scroll":
            if any(type(event.get(a)) is not int or not -10 <= event[a] <= 10 for a in ("dx", "dy")):
                raise ValueError("Geçersiz tekerlek.")
            result.update(dx=event["dx"], dy=event["dy"])
        return result
    raise ValueError("Bilinmeyen olay türü.")
