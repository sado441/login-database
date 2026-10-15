"""Foreground-source fan-out; portable and testable without Windows input."""
from protocol import validate_event


class LocalRouter:
    def __init__(self, source, outputs, source_active, valid):
        if not outputs:
            raise ValueError("En az bir alıcı pencere seç.")
        if source in outputs or len(outputs) != len(set(outputs)):
            raise ValueError("Ana pencere ile alıcı pencereler farklı olmalı.")
        self.source, self.outputs = source, outputs
        self.source_active, self.valid = source_active, valid
        self.running = False
        self.seen_source = False
        self.total = 0
        self.last_event = None
        self.reason = "Hazır"

    def start(self):
        if not all(self.valid(w) for w in [self.source, *self.outputs]):
            raise ValueError("Bir pencere kapalı veya küçültülmüş; listeyi yenile.")
        self.running = True
        self.seen_source = False
        self.reason = "Ana pencereye geç; yalnız onun girdileri aktarılır."

    def poll(self):
        if not self.running:
            return False
        if not all(self.valid(w) for w in [self.source, *self.outputs]):
            self.stop("Pencere kapandı, değişti veya küçültüldü.")
            return False
        if self.source_active():
            self.seen_source = True
            return True
        if self.seen_source:
            self.stop("Ana pencere odağı kayboldu. Yeniden BAŞLAT ile aç.")
        return False

    def route(self, event):
        event = validate_event(event)
        if not self.poll():
            return False
        try:
            for output in self.outputs.values():
                output.apply(event)
            self.total += 1
            self.last_event = event.copy()
            return True
        except Exception:
            self.stop("Girdi gönderilemedi; aktarım durduruldu.")
            raise

    def stop(self, reason="Durduruldu; basılı girdiler bırakıldı."):
        self.running = False
        self.reason = reason
        errors = []
        for output in self.outputs.values():
            try:
                output.release_all()
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            self.reason += " Bazı bırakma mesajları gönderilemedi: " + "; ".join(errors)
