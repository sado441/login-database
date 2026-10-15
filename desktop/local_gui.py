"""Local multibox control and a portable three-panel routing demonstration."""
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from local_router import LocalRouter


class DemoOutput:
    def __init__(self, canvas, label):
        self.canvas, self.label = canvas, label
        self.keys, self.buttons = set(), set()
        self.total = 0

    def apply(self, event):
        self.total += 1
        if event["type"] == "key":
            (self.keys.add if event["down"] else self.keys.discard)(event["vk"])
        elif event["type"] == "button":
            (self.buttons.add if event["down"] else self.buttons.discard)(event["button"])
        if event["type"] != "key":
            x, y = event["x"] * self.canvas.winfo_width(), event["y"] * self.canvas.winfo_height()
            self.canvas.delete("cursor")
            self.canvas.create_oval(x-8, y-8, x+8, y+8, outline="#00dca5", width=3, tags="cursor")
        self.label.configure(text=f"Olay: {self.total} | Basılı VK: {sorted(self.keys)} | Fare: {', '.join(sorted(self.buttons)) or 'yok'}")

    def release_all(self):
        self.keys.clear()
        self.buttons.clear()
        if self.label.winfo_exists():
            self.label.configure(text=f"Olay: {self.total} | Bütün tuşlar / düğmeler bırakıldı.")


class LocalApp:
    def __init__(self, root):
        self.root = root
        self.router = self.capture = None
        self.windows = []
        self.demo_windows = []
        self.demo_outputs = []
        self.demo_source = None
        self.demo_mode = False
        self.events = queue.Queue(maxsize=256)
        self.halt = threading.Event()
        self.generation = 0
        self.last_move = 0
        self.selection_timer = None
        self.test_keys = set()
        self.mouse_var = tk.BooleanVar(value=True)
        self.filter_var = tk.StringVar(value="Knight")
        self.status = tk.StringVar(value="Durduruldu. Ana pencereyi ve iki alıcıyı seç.")
        root.title("SADO Link | YEREL ÇOKLU PENCERE")
        root.geometry("920x780")
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="YEREL ÇOKLU PENCERE · 1 ana + 2 alıcı", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(frame, text="İnternet ve oturum kodu gerekmez. Sen ana pencerede oynarsın; seçilen alıcılara girdi gönderilir.", wraplength=820).pack(anchor="w", pady=8)
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=5)
        ttk.Label(row, text="Başlık filtresi:").pack(side="left")
        ttk.Entry(row, textvariable=self.filter_var, width=25).pack(side="left", padx=7)
        ttk.Button(row, text="PENCERELERİ YENİLE", command=self.refresh).pack(side="left")
        ttk.Label(frame, text="Ana pencere — elle oynayacağın karakter:").pack(anchor="w")
        self.source = ttk.Combobox(frame, state="readonly")
        self.source.pack(fill="x", pady=(3, 10))
        ttk.Button(frame, text="ÖNDEKİ PENCEREYİ ANA SEÇ (3 sn)", command=lambda: self.pick_foreground(True)).pack(anchor="w", pady=(0, 5))
        ttk.Label(frame, text="Alıcılar — Ctrl ile diğer iki karakterin penceresini seç:").pack(anchor="w")
        self.targets = tk.Listbox(frame, selectmode="extended", exportselection=False, height=9)
        self.targets.pack(fill="both", expand=True, pady=5)
        ttk.Button(frame, text="ÖNDEKİ PENCEREYİ ALICIYA EKLE (3 sn)", command=lambda: self.pick_foreground(False)).pack(anchor="w", pady=4)
        ttk.Checkbutton(frame, text="Fare hareketi, tıklamalar ve tekerleği de aktar", variable=self.mouse_var).pack(anchor="w", pady=5)
        ttk.Label(frame, text="Tuşlar yalnız seçilen ANA pencere öndeyken aktarılır. Alıcıları küçültme. F12 her zaman durdurur.", wraplength=820).pack(anchor="w", pady=5)
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="YEREL AKTARIMI BAŞLAT", command=self.start_live).pack(side="left", padx=3)
        ttk.Button(actions, text="DURDUR (F12)", command=self.stop).pack(side="left", padx=3)
        ttk.Button(actions, text="3 PENCERELİ TEST", command=self.start_demo).pack(side="right", padx=3)
        ttk.Label(frame, textvariable=self.status, wraplength=820, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=8)
        ttk.Label(frame, text="Arka plan girdileri Windows pencere mesajlarıyla gönderilir. Oyunun bunları kabul etmesi ayrıca denenmelidir. Kamera / hedefleme iki karakterde aynı sonucu vermeyebilir.", wraplength=820).pack(anchor="w")
        root.bind_all("<F12>", lambda e: self.stop())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.tick_timer = root.after(20, self.tick)
        if sys.platform == "win32":
            self.refresh()

    def refresh(self):
        self.stop()
        if sys.platform != "win32":
            self.status.set("Oyun pencereleri Windows gerektirir. 3 PENCERELİ TEST ile yönlendirmeyi deneyebilirsin.")
            return
        try:
            from local_windows import enumerate_windows
            word = self.filter_var.get().strip().casefold()
            self.windows = [w for w in enumerate_windows() if word in w.title.casefold()]
            self.source.configure(values=[w.label for w in self.windows])
            self.source.set("")
            self.targets.delete(0, "end")
            for window in self.windows:
                self.targets.insert("end", window.label)
            self.status.set(f"{len(self.windows)} pencere bulundu. Aynı başlıklar PID / HWND ile ayrılır.")
        except Exception as exc:
            messagebox.showerror("Pencere listesi alınamadı", str(exc))

    def start_live(self):
        self.stop()
        self.close_demo()
        self.demo_mode = False
        if sys.platform != "win32":
            messagebox.showinfo("Windows gerekli", "Gerçek çoklu pencere modu Windows'ta çalışır.")
            return
        try:
            from local_windows import BackgroundOutput, valid, foreground, rect
            from windows_input import Capture
            index = self.source.current()
            if index < 0:
                raise ValueError("Önce ana pencereyi seç.")
            source = self.windows[index]
            targets = [self.windows[i] for i in self.targets.curselection()]
            if source in targets:
                raise ValueError("Ana pencere alıcılar arasında olmamalı; yalnız diğer iki pencereyi seç.")
            if not targets:
                raise ValueError("En az bir alıcı seç; üç karakter için iki alıcı seçmelisin.")
            if not messagebox.askyesno("Yerel aktarım", f"Ana: {source.label}\n\n{len(targets)} seçili alıcıya tuş/fare gönderilecek. F12 durdurur. Başlatılsın mı?"):
                return
            self.router = LocalRouter(source, {w: BackgroundOutput(w) for w in targets}, lambda: foreground(source), valid)
            self.router.start()
            self.halt.clear()
            generation = self.generation
            self.forward_mouse = self.mouse_var.get()

            def emit(event):
                if event["type"] != "key" and not self.forward_mouse:
                    return
                try:
                    self.events.put_nowait((generation, event))
                except queue.Full:
                    self.halt.set()

            self.capture = Capture("", emit, self.halt.set, rect_provider=lambda: rect(source, foreground_only=True))
            self.status.set("Yerel aktarım hazır. Seçtiğin ana oyun penceresine geç.")
        except Exception as exc:
            self.stop()
            messagebox.showerror("Yerel aktarım başlatılamadı", str(exc))

    def pick_foreground(self, source):
        self.stop()
        if sys.platform != "win32":
            self.status.set("Pencere seçimi Windows'ta kullanılabilir.")
            return
        generation = self.generation
        self.status.set("3 saniye içinde seçmek istediğin oyun penceresine geç / tıkla.")

        def select():
            if generation != self.generation:
                return
            from local_windows import api
            hwnd = api().GetForegroundWindow()
            for index, window in enumerate(self.windows):
                if window.hwnd == hwnd:
                    if source:
                        self.source.current(index)
                        self.targets.selection_clear(index)
                    elif index != self.source.current():
                        self.targets.selection_set(index)
                    else:
                        self.status.set("Ana pencere alıcı olamaz. Diğer karakterin penceresini seç.")
                        return
                    self.status.set(("Ana pencere seçildi: " if source else "Alıcı eklendi: ") + window.label)
                    return
            self.status.set("Öndeki pencere listede yok; filtreyi kontrol edip PENCERELERİ YENİLE ile tekrar dene.")

        self.selection_timer = self.root.after(3000, select)

    def start_demo(self):
        self.stop()
        self.close_demo()
        self.demo_mode = True
        self.demo_outputs = []
        canvases = []
        for index, title in enumerate(("ANA — burada tuş/fare dene", "ALICI 1", "ALICI 2")):
            window = tk.Toplevel(self.root)
            window.title("SADO Yerel Test | " + title)
            window.geometry(f"420x320+{30 + index * 440}+80")
            ttk.Label(window, text=title, font=("Segoe UI", 12, "bold")).pack(pady=8)
            canvas = tk.Canvas(window, bg="#102b38", highlightthickness=2, highlightbackground="#00dca5", takefocus=True)
            canvas.pack(fill="both", expand=True, padx=8)
            label = ttk.Label(window, text="Bekleniyor", wraplength=400)
            label.pack(padx=8, pady=8)
            self.demo_windows.append(window)
            canvases.append(canvas)
            if index:
                self.demo_outputs.append(DemoOutput(canvas, label))
            window.protocol("WM_DELETE_WINDOW", self.close_demo)
        self.demo_source = canvases[0]
        self.router = LocalRouter("source", dict(zip(("one", "two"), self.demo_outputs)),
                                  lambda: self.root.focus_get() == self.demo_source,
                                  lambda _: all(w.winfo_exists() and w.state() != "iconic" for w in self.demo_windows))
        self.router.start()
        self.halt.clear()
        source = self.demo_source
        source.bind("<ButtonPress-1>", lambda e: self.demo_button(e, "left", True))
        source.bind("<ButtonRelease-1>", lambda e: self.demo_button(e, "left", False))
        source.bind("<ButtonPress-3>", lambda e: self.demo_button(e, "right", True))
        source.bind("<ButtonRelease-3>", lambda e: self.demo_button(e, "right", False))
        source.bind("<ButtonPress-2>", lambda e: self.demo_button(e, "middle", True))
        source.bind("<ButtonRelease-2>", lambda e: self.demo_button(e, "middle", False))
        source.bind("<KeyPress>", lambda e: self.demo_key(e, True))
        source.bind("<KeyRelease>", lambda e: self.demo_key(e, False))
        source.bind("<Motion>", self.demo_move)
        source.bind("<MouseWheel>", self.demo_scroll)
        self.root.update_idletasks()
        source.focus_force()
        self.status.set("3 pencere testi açık: ANA alanında W ve tıklama dene. İki alıcıda da aynı olay görünmeli. Bu test oyuna girdi göndermez.")

    def demo_route(self, event):
        if self.demo_mode and self.router:
            self.router.route(event)

    def demo_key(self, event, down):
        from app import tk_vk
        vk = tk_vk(event)
        if vk == 123:
            self.stop()
        elif vk is not None and 8 <= vk <= 254:
            if down and vk not in self.test_keys:
                self.test_keys.add(vk)
                self.demo_route({"type": "key", "vk": vk, "down": True})
            elif not down and vk in self.test_keys:
                self.test_keys.discard(vk)
                self.demo_route({"type": "key", "vk": vk, "down": False})
        return "break"

    def demo_coords(self, event):
        return {"x": max(0, min(1, event.x / max(1, self.demo_source.winfo_width()-1))),
                "y": max(0, min(1, event.y / max(1, self.demo_source.winfo_height()-1)))}

    def demo_button(self, event, button, down):
        self.demo_source.focus_force()
        self.demo_route(dict(type="button", button=button, down=down, **self.demo_coords(event)))

    def demo_move(self, event):
        if time.monotonic() - self.last_move >= 1/30:
            self.last_move = time.monotonic()
            self.demo_route(dict(type="move", **self.demo_coords(event)))

    def demo_scroll(self, event):
        self.demo_route(dict(type="scroll", dx=0, dy=max(-10, min(10, int(event.delta/120))), **self.demo_coords(event)))

    def stop(self):
        self.generation += 1
        if self.capture:
            self.capture.stop()
            self.capture = None
        if self.router:
            self.router.stop()
            self.status.set(self.router.reason)
        self.test_keys.clear()
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                break
        self.halt.clear()

    def close_demo(self):
        self.stop()
        for window in self.demo_windows:
            if window.winfo_exists():
                window.destroy()
        self.demo_windows = []
        self.demo_source = None
        if self.demo_mode:
            self.router = None
        self.demo_outputs = []
        self.demo_mode = False

    def tick(self):
        try:
            if self.halt.is_set():
                self.stop()
            if self.router and self.router.running:
                self.router.poll()
                if not self.router.running:
                    reason = self.router.reason
                    self.stop()
                    self.status.set(reason)
                else:
                    for _ in range(100):
                        try:
                            generation, event = self.events.get_nowait()
                        except queue.Empty:
                            break
                        if generation == self.generation:
                            self.router.route(event)
                    if not self.router.running:
                        reason = self.router.reason
                        self.stop()
                        self.status.set(reason)
                    elif not self.demo_mode:
                        self.status.set(f"YEREL AKTARIM AÇIK | {len(self.router.outputs)} alıcı | Olay: {self.router.total} | F12 durdurur")
        except Exception as exc:
            self.stop()
            self.status.set("Aktarım durduruldu: " + str(exc)[:180])
        self.tick_timer = self.root.after(20, self.tick)

    def close(self):
        self.root.after_cancel(self.tick_timer)
        if self.selection_timer:
            self.root.after_cancel(self.selection_timer)
        self.close_demo()
        self.root.destroy()
