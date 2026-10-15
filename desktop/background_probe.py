"""Isolated SEGE background.py pulse test, using its pywin32 call sequence."""
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

SCANS = {'W': 0x11, '1': 0x02, '2': 0x03, 'R': 0x13}


class PulseTransport:
    def __init__(self, api=None, gui=None, owner_valid=None):
        if api is None or gui is None:
            import win32api as api
            import win32gui as gui
        if owner_valid is None:
            from local_windows import valid
            owner_valid = lambda window: valid(window, cleanup=True)
        self.api, self.gui, self.owner_valid = api, gui, owner_valid
        self.downs = self.ups = self.activations = 0

    def pulse(self, window, key, cancel):
        if cancel.is_set():
            return
        if not self.owner_valid(window) or not self.gui.IsWindow(window.hwnd):
            raise RuntimeError(f'Hedef pencere kapandı veya değişti: PID {window.pid}')
        scan = SCANS[key]
        vk = self.api.MapVirtualKey(scan, 1)
        if not vk:
            raise RuntimeError('Tuş dönüşümü başarısız.')
        self.api.PostMessage(window.hwnd, 0x006, 1, 0)  # WM_ACTIVATE, WA_ACTIVE
        self.activations += 1
        try:
            self.api.PostMessage(window.hwnd, 0x100, vk, 1 | (scan << 16))
            self.downs += 1
            cancel.wait(.01)  # Source: time.sleep(0.01); cancellation still releases.
        finally:
            if self.owner_valid(window) and self.gui.IsWindow(window.hwnd):
                self.api.PostMessage(window.hwnd, 0x101, vk, 1 | (scan << 16) | (3 << 30))
                self.ups += 1
            else:
                raise RuntimeError('Tuş bırakılırken hedef pencere kayboldu.')


class ProbeApp:
    def __init__(self, root, windows, transport=None):
        self.root, self.windows = root, windows
        self.transport = transport if transport is not None else PulseTransport()
        self.cancel = threading.Event()
        self.worker = None
        self.error = None
        self.phase = 'Hazır'
        self.listener = None
        self.key = tk.StringVar(value='W')
        self.status = tk.StringVar(value='Hazır. Bu test fiziksel klavyeni dinlemez; seçili alıcılara kısa basışlar üretir.')
        root.title('SADO Link v4.1 | SEGE Arka Plan Testi')
        root.geometry('760x460')
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='SEGE ARKA PLAN TESTİ', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Kaynak background.py sırası: WM_ACTIVATE → tuşa bas → 10 ms → tuşu bırak.\nKlavye yakalama ve ana pencere odak kontrolü bu testte kullanılmaz.', wraplength=720).pack(anchor='w', pady=10)
        for window in windows:
            ttk.Label(frame, text=f'Alıcı: {window.label}', wraplength=720).pack(anchor='w', pady=2)
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=15)
        ttk.Label(row, text='Test tuşu:').pack(side='left')
        self.key_box = ttk.Combobox(row, state='readonly', textvariable=self.key, values=list(SCANS), width=8)
        self.key_box.pack(side='left', padx=8)
        self.start_button = ttk.Button(row, text='3 SANİYE SONRA TESTİ BAŞLAT', command=self.start)
        self.start_button.pack(side='left', padx=6)
        ttk.Button(row, text='DURDUR (F12)', command=self.cancel.set).pack(side='left', padx=6)
        ttk.Label(frame, text='3 saniye hazırlık süresinden sonra 20 tur gönderilir; turlar arasında 50 ms beklenir. Tuşa kendin basma. Alıcı karakterlerde hareket olup olmadığını izle.', wraplength=720).pack(anchor='w', pady=8)
        ttk.Label(frame, textvariable=self.status, wraplength=720, font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=15)
        ttk.Label(frame, text='Sayaçlar Windows mesaj gönderim çağrılarını gösterir; oyunun mesajı işlediğini kanıtlamaz. Sonuç ve hata varsa burada kalır.', wraplength=720).pack(anchor='w')
        root.bind_all('<F12>', lambda e: self.cancel.set())
        root.protocol('WM_DELETE_WINDOW', self.close)
        if sys.platform == 'win32':
            from pynput import keyboard
            self.listener = keyboard.Listener(on_press=lambda key: self.cancel.set() if key == keyboard.Key.f12 else None)
            self.listener.start()
        self.timer = root.after(50, self.tick)

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        self.cancel.clear()
        self.error = None
        self.transport.downs = self.transport.ups = self.transport.activations = 0
        self.phase = '3 saniye hazırlık; tuşa kendin basma'
        self.start_button.configure(state='disabled')
        self.key_box.configure(state='disabled')
        key = self.key.get()
        self.worker = threading.Thread(target=self.run, args=(key,), daemon=True)
        self.worker.start()

    def run(self, key):
        try:
            if self.cancel.wait(3):
                self.phase = 'İptal edildi'
                return
            self.phase = 'Gönderiliyor'
            for _ in range(20):
                if self.cancel.is_set():
                    break
                for window in self.windows:
                    self.transport.pulse(window, key, self.cancel)
                if self.cancel.wait(.05):
                    break
            self.phase = 'Durduruldu' if self.cancel.is_set() else 'Test bitti'
        except Exception as exc:
            self.error = str(exc)
            self.phase = 'Hata ile durdu'

    def tick(self):
        self.status.set(f'{self.phase} | Aktivasyon: {self.transport.activations} | Bas: {self.transport.downs} | Bırak: {self.transport.ups}' + (f' | Hata: {self.error}' if self.error else ''))
        if not self.worker or not self.worker.is_alive():
            self.start_button.configure(state='normal')
            self.key_box.configure(state='readonly')
        self.timer = self.root.after(50, self.tick)

    def close(self):
        self.cancel.set()
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=.2)
            if self.worker.is_alive():
                self.root.after(50, self.close)
                return
        if self.listener:
            self.listener.stop()
        self.root.after_cancel(self.timer)
        self.root.destroy()
