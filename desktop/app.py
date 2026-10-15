"""SADO Link: consent-based keyboard/mouse mirroring and offline demo."""
import argparse
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from client import Connection
from protocol import validate_event


def tk_vk(event):
    if sys.platform == "win32":
        return event.keycode
    name = event.keysym.lower()
    named = {"space": 32, "return": 13, "escape": 27, "tab": 9,
             "backspace": 8, "shift_l": 16, "shift_r": 16,
             "control_l": 17, "control_r": 17, "alt_l": 18, "alt_r": 18,
             "left": 37, "up": 38, "right": 39, "down": 40}
    if name in named:
        return named[name]
    if len(name) == 1 and name.isascii() and name.isalnum():
        return ord(name.upper())
    if name.startswith("f") and name[1:].isdigit():
        return 111 + int(name[1:])
    return None


class App:
    def __init__(self, root, args):
        self.root, self.args = root, args
        self.connection = self.capture = self.output = self.emergency_hook = None
        self.incoming = queue.Queue(maxsize=1000)
        self.generation = 0
        self.paired = self.armed = self.active = self.consent = False
        self.live = False
        self.session_backend = "Interception"
        self.seen_target = False
        self.target = ""
        self.pressed = set()
        self.received_keys, self.received_buttons = set(), set()
        self.last_move = 0
        self.total = 0
        self.role = tk.StringVar(value=args.role)
        self.url = tk.StringVar(value=args.url)
        self.code = tk.StringVar(value=args.code or secrets.token_urlsafe(24))
        self.live_var = tk.BooleanVar(value=False)
        self.backend_var = tk.StringVar(value="Interception")
        self.keyboard_id = tk.StringVar(value="Otomatik")
        self.mouse_id = tk.StringVar(value="Otomatik")
        self.target_var = tk.StringVar(value="Knight")
        self.status = tk.StringVar(value="Bağlı değil — test modu; sisteme girdi gönderilmez.")
        self.info = tk.StringVar(value="Bekleniyor. F12 veya DURDUR ile aktarımı kes.")
        root.title("SADO Link | " + ("GÖNDERİCİ" if args.role == "sender" else "ALICI"))
        root.geometry("850x850")
        root.configure(bg="#101923")
        style = ttk.Style()
        style.theme_use("clam")
        frame = ttk.Frame(root, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="SADO LINK · Klavye / Fare", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Button(frame, text="YEREL ÇOKLU PENCERE · aynı bilgisayarda 3 client", command=self.open_local).pack(anchor="w", pady=5)
        ttk.Label(frame, text="İlk denemede iki pencerede de Test modu açık kalsın.").pack(anchor="w", pady=(0, 10))
        form = ttk.Frame(frame)
        form.pack(fill="x")
        ttk.Label(form, text="Rol").grid(row=0, column=0, sticky="w")
        self.role_box = ttk.Combobox(form, textvariable=self.role, values=["sender", "receiver"], state="readonly", width=12)
        self.role_box.grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="sender = gönderici / receiver = alıcı").grid(row=0, column=2)
        for row, (label, var) in enumerate((("Sunucu", self.url), ("Oturum kodu", self.code), ("Oyun başlığında", self.target_var)), 1):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=6)
        form.columnconfigure(2, weight=1)
        ttk.Button(frame, text="Yeni oturum kodu", command=lambda: self.code.set(secrets.token_urlsafe(24))).pack(anchor="w", pady=4)
        self.live_check = ttk.Checkbutton(frame, variable=self.live_var, text="GERÇEK GİRDİ: oyun penceresinde yakala / uygula (yalnız Windows)")
        self.live_check.pack(anchor="w", pady=6)
        if args.test_only:
            self.live_check.configure(state="disabled")
        driver = ttk.Frame(frame)
        driver.pack(fill="x", pady=4)
        ttk.Label(driver, text="Alıcı girdi yöntemi:").pack(side="left")
        self.backend_box = ttk.Combobox(driver, textvariable=self.backend_var, state="readonly", values=["Interception", "Standart Windows"], width=19)
        self.backend_box.pack(side="left", padx=5)
        self.find_devices = ttk.Button(driver, text="CİHAZLARI BUL", command=self.detect_devices)
        self.find_devices.pack(side="left", padx=4)
        ttk.Label(driver, text="Klavye:").pack(side="left")
        self.kb_box = ttk.Combobox(driver, textvariable=self.keyboard_id, state="readonly", values=["Otomatik"], width=9)
        self.kb_box.pack(side="left", padx=3)
        ttk.Label(driver, text="Fare:").pack(side="left")
        self.ms_box = ttk.Combobox(driver, textvariable=self.mouse_id, state="readonly", values=["Otomatik"], width=9)
        self.ms_box.pack(side="left", padx=3)
        ttk.Label(frame, text="Interception yalnız gerçek girdiyi uygulayan alıcıda gerekir. Gönderici fiziksel girdileri dinler.", wraplength=800).pack(anchor="w")
        ttk.Label(frame, text="Fare konumu oyun penceresine orantılanır. Aynı arayüz / beceri düzenini kullanın.", wraplength=650).pack(anchor="w")
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="BAĞLAN", command=self.connect).pack(side="left", padx=3)
        ttk.Button(actions, text="BAĞLANTIYI KES", command=self.disconnect).pack(side="left", padx=3)
        self.activate = ttk.Button(actions, text="AKTARIMI ETKİNLEŞTİR", command=self.toggle)
        self.activate.pack(side="left", padx=3)
        ttk.Button(actions, text="DURDUR (F12)", command=self.stop).pack(side="right", padx=3)
        ttk.Label(frame, textvariable=self.status, wraplength=650, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=5)
        ttk.Label(frame, text="TEST ALANI — Göndericide buraya tıkla; W/A/S/D, beceri tuşları ve fareyi dene.", wraplength=650).pack(anchor="w")
        self.canvas = tk.Canvas(frame, height=220, bg="#122838", highlightthickness=2, highlightbackground="#36c9a0", takefocus=True)
        self.canvas.pack(fill="both", expand=True, pady=7)
        self.canvas.create_text(320, 60, text="TEST MODU\nGerçek tuş / fare gönderimi kapalı", fill="#bcdfef", font=("Segoe UI", 14), tags="hint", justify="center")
        self.canvas.bind("<KeyPress>", lambda e: self.test_key(e, True))
        self.canvas.bind("<KeyRelease>", lambda e: self.test_key(e, False))
        self.canvas.bind("<Motion>", self.test_move)
        for number, name in ((1, "left"), (2, "middle"), (3, "right")):
            self.canvas.bind(f"<ButtonPress-{number}>", lambda e, n=name: self.test_button(e, n, True))
            self.canvas.bind(f"<ButtonRelease-{number}>", lambda e, n=name: self.test_button(e, n, False))
        self.canvas.bind("<MouseWheel>", self.test_scroll)
        self.canvas.bind("<FocusOut>", lambda e: self.reset_sender())
        ttk.Label(frame, textvariable=self.info, wraplength=650).pack(anchor="w")
        self.logbox = tk.Text(frame, height=7, state="disabled", bg="#101923", fg="#dce8ef")
        self.logbox.pack(fill="x", pady=6)
        root.bind_all("<F12>", lambda e: self.stop())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.tick_timer = root.after(20, self.tick)
        self.auto_timer = None
        if args.auto:
            self.auto_timer = root.after(300, self.connect)

    def log(self, text):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", text + "\n")
        if int(self.logbox.index("end-1c").split(".")[0]) > 150:
            self.logbox.delete("1.0", "30.0")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def open_local(self):
        self.disconnect()
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--local"])

    def detect_devices(self):
        if self.connection:
            messagebox.showinfo("Cihaz seçimi", "Önce bağlantıyı kes.")
            return
        native = None
        try:
            from interception_output import Native
            native = Native()
            devices = native.devices()
            keyboards = [str(d) for d in devices if 1 <= d <= 10]
            mice = [str(d) for d in devices if 11 <= d <= 20]
            self.kb_box.configure(values=["Otomatik", *keyboards])
            self.ms_box.configure(values=["Otomatik", *mice])
            self.keyboard_id.set("Otomatik")
            self.mouse_id.set("Otomatik")
            self.log(f"Interception: klavye cihazları {keyboards}, fare cihazları {mice}. Otomatik ilk bağlı cihazı seçer.")
            if not keyboards or not mice:
                messagebox.showwarning("Cihaz bulunamadı", "Klavye ve fare birlikte bulunamadı. Sürücüyü ve yeniden başlatmayı kontrol et.")
        except Exception as exc:
            messagebox.showerror("Interception hazır değil", str(exc))
        finally:
            if native:
                native.close()

    def driver_controls(self, enabled):
        for widget in (self.backend_box, self.kb_box, self.ms_box):
            widget.configure(state="readonly" if enabled else "disabled")
        self.find_devices.configure(state="normal" if enabled else "disabled")

    def enqueue(self, generation, message):
        try:
            self.incoming.put_nowait((generation, message))
        except queue.Full:
            if self.connection:
                self.connection.close()

    def connect(self):
        self.disconnect()
        try:
            self.live = self.live_var.get()
            self.target = self.target_var.get().strip()
            if self.live:
                if sys.platform != "win32":
                    raise ValueError("Gerçek girdi yalnızca Windows'ta kullanılabilir.")
                if not self.target or self.target.casefold() in "sado link":
                    raise ValueError("Ayrı bir oyun penceresinin başlığını belirt.")
                if not messagebox.askyesno("Gerçek girdi", "Bu oturumda oyun penceresinin tuş/fare girdileri aktarılacak. F12 ile durdurabilirsin. Devam edilsin mi?"):
                    return
                from pynput import keyboard
                self.emergency_hook = keyboard.Listener(on_press=lambda k: self.enqueue(self.generation, {"type": "emergency"}) if k == keyboard.Key.f12 else None)
                self.emergency_hook.start()
                if self.role.get() == "receiver":
                    self.session_backend = self.backend_var.get()
                    if self.backend_var.get() == "Interception":
                        from interception_output import InterceptionOutput
                        self.output = InterceptionOutput(self.keyboard_id.get(), self.mouse_id.get())
                        self.log(f"Alıcı Interception kullanıyor | Klavye {self.output.keyboard_id} | Fare {self.output.mouse_id}")
                    else:
                        from windows_input import Output
                        self.output = Output()
                        self.log("Alıcı Standart Windows girdisi kullanıyor.")
            generation = self.generation
            self.connection = Connection(self.url.get().strip(), self.code.get().strip(), self.role.get(),
                                         lambda m: self.enqueue(generation, m))
            self.session_role = self.role.get()
            self.root.title("SADO Link | " + ("GÖNDERİCİ" if self.session_role == "sender" else "ALICI"))
            self.canvas.delete("hint")
            hint = ("GERÇEK GİRDİ · " + (self.session_backend if self.session_role == "receiver" else "FİZİKSEL GİRDİ YAKALAMA")) if self.live else "TEST MODU · Sisteme girdi uygulanmaz"
            self.canvas.create_text(max(300, self.canvas.winfo_width()//2), 60, text=hint, fill="#bcdfef", font=("Segoe UI", 12), tags="hint", justify="center")
            self.role_box.configure(state="disabled")
            self.live_check.configure(state="disabled")
            self.driver_controls(False)
            self.connection.thread.start()
            self.status.set("Bağlanıyor…")
        except Exception as exc:
            self.disconnect()
            messagebox.showerror("Bağlantı kurulamadı", str(exc))

    def send(self, message):
        if self.connection:
            self.connection.send(message)

    def emit(self, event):
        if self.active and self.paired and self.armed:
            self.send({"type": "event", "event": event})

    def toggle(self):
        if not self.connection or not self.paired:
            messagebox.showinfo("Bekleniyor", "Önce iki pencere aynı sunucu ve kodla bağlanmalı.")
            return
        if self.session_role == "receiver":
            self.consent = not self.consent
            self.send({"type": "arm", "value": self.consent})
            if not self.consent:
                self.release()
            self.log("Alıcı onayı açıldı." if self.consent else "Alıcı onayı kapatıldı.")
        elif self.active:
            self.stop()
        elif not self.armed:
            messagebox.showinfo("Alıcı onayı", "Önce alıcı penceresinde AKTARIMI ETKİNLEŞTİR düğmesine bas.")
        else:
            self.active = True
            self.seen_target = False
            if self.live:
                from windows_input import Capture
                try:
                    generation = self.generation
                    self.capture = Capture(self.target, self.emit, lambda: self.enqueue(generation, {"type": "emergency"}))
                except Exception as exc:
                    self.stop()
                    messagebox.showerror("Girdi yakalanamadı", str(exc))
                    return
            self.log("Gönderim açık. " + ("Oyun penceresine geç." if self.live else "TEST ALANINA tıkla."))
        self.update_status()

    def reset_sender(self):
        self.pressed.clear()
        if self.capture:
            self.capture.reset()
        if self.connection and getattr(self, "session_role", None) == "sender":
            self.send({"type": "reset"})

    def stop(self):
        had_consent = self.consent
        self.active = self.consent = False
        if self.capture:
            self.capture.stop()
            self.capture = None
        self.reset_sender()
        self.release()
        if getattr(self, "session_role", None) == "receiver":
            self.armed = False
            if had_consent:
                self.send({"type": "arm", "value": False})
        self.update_status()

    def release(self):
        error = None
        try:
            if self.output:
                self.output.release_all()
        except Exception as exc:
            error = str(exc)
            self.log("Girdi bırakma hatası: " + error)
        self.received_keys.clear()
        self.received_buttons.clear()
        self.info.set("Bırakma hatası: " + error if error else "Tuşlar ve fare düğmeleri bırakıldı.")

    def disconnect(self):
        self.stop()
        self.generation += 1
        connection, self.connection = self.connection, None
        if connection:
            connection.close()
            if connection.thread.ident is not None and connection.thread is not threading.current_thread():
                connection.thread.join(timeout=2)
        if self.emergency_hook:
            self.emergency_hook.stop()
            self.emergency_hook = None
        if self.output and hasattr(self.output, "close"):
            try:
                self.output.close()
            except Exception as exc:
                self.log("Sürücü kapatma hatası: " + str(exc))
        self.output = None
        self.paired = self.armed = False
        self.role_box.configure(state="readonly")
        self.live_check.configure(state="disabled" if self.args.test_only else "normal")
        self.driver_controls(True)
        self.status.set("Bağlı değil.")

    def update_status(self):
        if not self.connection:
            return
        mode = "GERÇEK GİRDİ" if self.live else "TEST"
        if self.live and self.session_role == "receiver":
            mode += " / " + self.session_backend
        self.status.set(f"{mode} | Eşleşme: {'var' if self.paired else 'bekleniyor'} | Alıcı onayı: {'açık' if self.armed else 'kapalı'} | Gönderim: {'açık' if self.active else 'kapalı'}")

    def receive_event(self, event):
        if not self.consent or not self.armed or self.session_role != "receiver":
            return
        event = validate_event(event)
        if self.live:
            from windows_input import target_rect
            rect = target_rect(self.target)
            if not rect:
                self.stop()
                self.log("Alıcı oyun penceresi önde değil; aktarım durdu.")
                return
            self.seen_target = True
            self.output.apply(event, rect)
        self.total += 1
        kind = event["type"]
        if kind == "key":
            if event["down"]:
                self.received_keys.add(event["vk"])
            else:
                self.received_keys.discard(event["vk"])
            self.log(f"Tuş VK={event['vk']} {'BASILDI' if event['down'] else 'BIRAKILDI'}")
        else:
            x, y = event["x"] * self.canvas.winfo_width(), event["y"] * self.canvas.winfo_height()
            self.canvas.delete("pointer")
            color = "#ffcc55" if kind == "button" else "#36c9a0"
            self.canvas.create_oval(x-8, y-8, x+8, y+8, outline=color, width=3, tags="pointer")
            if kind == "button":
                if event["down"]:
                    self.received_buttons.add(event["button"])
                else:
                    self.received_buttons.discard(event["button"])
                self.log(f"Fare {event['button']} {'BASILDI' if event['down'] else 'BIRAKILDI'}")
            elif kind == "scroll":
                self.log(f"Tekerlek: {event['dx']}, {event['dy']}")
        self.canvas.delete("hint")
        self.info.set(f"Alınan olay: {self.total} | Basılı VK: {sorted(self.received_keys)} | Fare: {', '.join(sorted(self.received_buttons)) or 'yok'}")

    def test_key(self, event, down):
        if self.live:
            return
        vk = tk_vk(event)
        if vk == 123:
            self.stop()
        elif vk is not None and 8 <= vk <= 254:
            if down and vk not in self.pressed:
                self.pressed.add(vk)
                self.emit({"type": "key", "vk": vk, "down": True})
            elif not down and vk in self.pressed:
                self.pressed.discard(vk)
                self.emit({"type": "key", "vk": vk, "down": False})
        return "break"

    def coords(self, event):
        return {"x": max(0, min(1, event.x / max(1, self.canvas.winfo_width() - 1))),
                "y": max(0, min(1, event.y / max(1, self.canvas.winfo_height() - 1)))}

    def test_move(self, event):
        if not self.live and time.monotonic() - self.last_move >= 1 / 30:
            self.last_move = time.monotonic()
            self.emit(dict(type="move", **self.coords(event)))

    def test_button(self, event, name, down):
        self.canvas.focus_set()
        if not self.live:
            self.emit(dict(type="button", button=name, down=down, **self.coords(event)))

    def test_scroll(self, event):
        if not self.live:
            self.emit(dict(type="scroll", dx=0, dy=max(-10, min(10, int(event.delta / 120))), **self.coords(event)))

    def tick(self):
        try:
            for _ in range(100):
                try:
                    generation, msg = self.incoming.get_nowait()
                except queue.Empty:
                    break
                if generation != self.generation:
                    continue
                kind = msg.get("type")
                if kind == "status":
                    self.paired = msg["paired"]
                    self.armed = msg["armed"] and (self.session_role == "sender" or self.consent)
                    if not self.paired or not self.armed:
                        self.stop()
                    self.update_status()
                elif kind == "event":
                    self.receive_event(msg["event"])
                elif kind == "reset":
                    self.release()
                elif kind in {"disconnected", "emergency"}:
                    self.disconnect() if kind == "disconnected" else self.stop()
                    self.log("Bağlantı kapandı." if kind == "disconnected" else "F12: aktarım durduruldu.")
                elif kind == "error":
                    self.log("Hata: " + msg.get("message", "Bilinmeyen hata"))
            if self.connection and self.connection.closed.is_set():
                self.disconnect()
            if self.live and (self.active or self.consent):
                from windows_input import target_rect
                if target_rect(self.target):
                    self.seen_target = True
                elif self.seen_target:
                    self.seen_target = False
                    if self.session_role == "sender":
                        self.reset_sender()
                    else:
                        self.stop()
                    self.log("Oyun odağı kayboldu; basılı girdiler bırakıldı.")
        except Exception as exc:
            self.stop()
            self.log("İşlem durduruldu: " + str(exc)[:120])
        self.tick_timer = self.root.after(20, self.tick)

    def close(self):
        self.root.after_cancel(self.tick_timer)
        if self.auto_timer:
            self.root.after_cancel(self.auto_timer)
        self.disconnect()
        self.root.destroy()


def demo():
    from relay import make_server
    code = secrets.token_urlsafe(24)
    with make_server(port=0) as server:
        port = server.socket.getsockname()[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        children = []
        try:
            for role in ("sender", "receiver"):
                children.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                    "--role", role, "--code", code, "--url", f"ws://127.0.0.1:{port}", "--auto", "--test-only"]))
            print("İki test penceresi açıldı. Önce ALICI, sonra GÖNDERİCİ üzerinde aktarımı etkinleştir.")
            while any(p.poll() is None for p in children):
                time.sleep(0.3)
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
            server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--local", action="store_true", help="Same-PC multi-window forwarding")
    parser.add_argument('--background-probe', action='store_true')
    parser.add_argument('--probe-targets', default='[]')
    parser.add_argument("--prepare-interception", action="store_true")
    parser.add_argument("--role", choices=["sender", "receiver"], default="sender")
    parser.add_argument("--url", default="wss://sado-link.onrender.com")
    parser.add_argument("--code", default="")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--test-only", action="store_true", help="Disable live injection for the offline demo")
    options = parser.parse_args()
    if options.prepare_interception:
        from prepare_interception import main as prepare_driver
        prepare_driver()
    elif options.demo:
        demo()
    else:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass
        window = tk.Tk()
        if options.background_probe:
            try:
                if sys.platform != 'win32':
                    raise ValueError('Bu test gerçek Windows pencereleri gerektirir.')
                from local_windows import Window
                from background_probe import ProbeApp
                data = json.loads(options.probe_targets)
                if not isinstance(data, list) or not 1 <= len(data) <= 10:
                    raise ValueError('Geçersiz hedef listesi.')
                windows = []
                for item in data:
                    if type(item.get('hwnd')) is not int or item['hwnd'] <= 0 or type(item.get('pid')) is not int or item['pid'] <= 0:
                        raise ValueError('Geçersiz pencere kimliği.')
                    windows.append(Window(item['hwnd'], item['pid'], str(item.get('title', ''))[:512]))
                app = ProbeApp(window, windows)
            except Exception as exc:
                messagebox.showerror('SEGE Arka Plan Testi', str(exc))
                window.destroy()
                sys.exit(1)
        elif options.local:
            from local_gui import LocalApp
            app = LocalApp(window)
        else:
            app = App(window, options)
        window.mainloop()
