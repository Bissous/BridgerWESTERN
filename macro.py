import os
import sys
import threading
import time
import tkinter as tk
import cv2
import numpy as np
import mss
import pydirectinput
import keyboard

# --- Resolve paths (works both as .py and bundled .exe) ---
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# --- Configuration ---
SCREEN_CX, SCREEN_CY = 960, 551  # symbol center on 1920x1080
HALF = 50
SCAN_REGION = {
    "left": SCREEN_CX - HALF,
    "top": SCREEN_CY - HALF,
    "width": HALF * 2,
    "height": HALF * 2,
}
MATCH_THRESHOLD = 0.7
HIGH_CONFIDENCE = 0.9  # skip remaining templates if exceeded
SCAN_INTERVAL = 0.03   # 30ms between scans
COOLDOWN = 0.35

# --- Pre-load and pre-process templates once ---
KEYS = ("F", "G", "R", "T")
templates = []
for key in KEYS:
    path = os.path.join(TEMPLATE_DIR, f"template_{key}.png")
    tmpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if tmpl is None:
        print(f"ERROR: template not found: {path}")
        sys.exit(1)
    # Pre-resize to fit scan region if needed
    th, tw = tmpl.shape
    fh, fw = SCAN_REGION["height"], SCAN_REGION["width"]
    if th > fh or tw > fw:
        scale = min(fh / th, fw / tw) * 0.9  # fix: was fw/fw
        tmpl = cv2.resize(tmpl, (int(tw * scale), int(th * scale)), interpolation=cv2.INTER_AREA)
    templates.append((key, tmpl))


def detect_and_press(stop_event: threading.Event):
    last_press = 0.0
    with mss.mss() as sct:
        while not stop_event.is_set():
            now = time.perf_counter()
            remaining = COOLDOWN - (now - last_press)
            if remaining > 0:
                # Sleep exactly the remaining cooldown instead of busy-looping
                stop_event.wait(remaining)
                continue

            frame = np.asarray(sct.grab(SCAN_REGION))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

            best_key = None
            best_val = 0.0
            for key, tmpl in templates:
                res = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
                _, val, _, _ = cv2.minMaxLoc(res)  # faster than res.max()
                if val > best_val:
                    best_val = val
                    best_key = key
                    if val >= HIGH_CONFIDENCE:
                        break  # confident enough, skip remaining templates

            if best_val >= MATCH_THRESHOLD and best_key:
                pydirectinput.press(best_key.lower())
                last_press = time.perf_counter()

            time.sleep(SCAN_INTERVAL)


# --- Dark theme colors ---
BG = "#1e1e2e"
FG = "#cdd6f4"
GREEN = "#a6e3a1"
RED = "#f38ba8"
ACCENT = "#89b4fa"
SURFACE = "#313244"


class MacroApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RGTF Macro")
        self.root.geometry("300x160")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)

        self.stop_event = threading.Event()
        self.stop_event.set()  # start stopped
        self.thread = None
        self.running = False

        # --- Title ---
        tk.Label(
            root, text="RGTF Macro", font=("Segoe UI", 14, "bold"),
            bg=BG, fg=FG,
        ).pack(pady=(12, 4))

        # --- Buttons ---
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(pady=6)

        self.run_btn = tk.Button(
            btn_frame, text="Run", width=10, font=("Segoe UI", 10),
            bg=GREEN, fg="#1e1e2e", activebackground="#94d89a",
            relief="flat", bd=0, command=self.start,
        )
        self.run_btn.grid(row=0, column=0, padx=6)

        self.stop_btn = tk.Button(
            btn_frame, text="Stop", width=10, font=("Segoe UI", 10),
            bg=SURFACE, fg="#6c7086", activebackground=SURFACE,
            relief="flat", bd=0, state=tk.DISABLED, command=self.stop,
        )
        self.stop_btn.grid(row=0, column=1, padx=6)

        # --- Status ---
        self.status_var = tk.StringVar(value="Stopped  |  F6 to toggle")
        tk.Label(
            root, textvariable=self.status_var, font=("Segoe UI", 9),
            bg=BG, fg="#6c7086",
        ).pack(pady=(6, 0))

        # --- Global hotkey F6 ---
        keyboard.on_press_key("f6", lambda _: self.root.after(0, self.toggle))

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=detect_and_press, args=(self.stop_event,), daemon=True)
        self.thread.start()
        self.status_var.set("Running...  |  F6 to stop")
        self.run_btn.config(state=tk.DISABLED, bg=SURFACE, fg="#6c7086")
        self.stop_btn.config(state=tk.NORMAL, bg=RED, fg="#1e1e2e")

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        self.status_var.set("Stopped  |  F6 to toggle")
        self.run_btn.config(state=tk.NORMAL, bg=GREEN, fg="#1e1e2e")
        self.stop_btn.config(state=tk.DISABLED, bg=SURFACE, fg="#6c7086")

    def on_close(self):
        self.stop()
        keyboard.unhook_all()
        self.root.destroy()


if __name__ == "__main__":
    pydirectinput.PAUSE = 0.02
    root = tk.Tk()
    app = MacroApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
