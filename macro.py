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

# Templates live next to the script, or inside the PyInstaller bundle.
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Symbol appears centered on a 1920x1080 screen; scan a 140x140 box around it.
SCREEN_CX, SCREEN_CY = 960, 551
HALF = 70
SCAN_REGION = {
    "left": SCREEN_CX - HALF,
    "top": SCREEN_CY - HALF,
    "width": HALF * 2,
    "height": HALF * 2,
}
MATCH_THRESHOLD = 0.7
MATCH_MARGIN = 0.08
SCALES = (0.9, 1.0, 1.1)
SCAN_INTERVAL = 0.03
COOLDOWN = 0.35

KEYS = ("F", "G", "R", "T")


def glyph_crop(tmpl, thresh=160, min_area=30, pad=3):
    """Crop a template down to its letter.

    All four buttons share the same circular frame, so matching the full
    image lets the frame dominate the score and any symbol can trigger any
    key. Only the letter is discriminative, so we keep the largest bright
    blob nearest the center.
    """
    _, binary = cv2.threshold(tmpl, thresh, 255, cv2.THRESH_BINARY)
    n, _, stats, centroids = cv2.connectedComponentsWithStats(binary)
    h, w = tmpl.shape
    best, best_score = None, -1.0
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < min_area:
            continue
        dist = ((centroids[i][0] - w / 2) ** 2 + (centroids[i][1] - h / 2) ** 2) ** 0.5
        score = area / (1 + dist)
        if score > best_score:
            best_score, best = score, i
    if best is None:
        return tmpl
    x, y, bw, bh, _ = stats[best]
    return tmpl[max(0, y - pad):y + bh + pad, max(0, x - pad):x + bw + pad]


def load_templates():
    templates = []
    for key in KEYS:
        path = os.path.join(TEMPLATE_DIR, f"template_{key}.png")
        tmpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if tmpl is None:
            print(f"ERROR: template not found: {path}")
            sys.exit(1)
        glyph = glyph_crop(tmpl)
        gh, gw = glyph.shape
        for s in SCALES:
            scaled = glyph if s == 1.0 else cv2.resize(
                glyph, (int(gw * s), int(gh * s)), interpolation=cv2.INTER_AREA)
            templates.append((key, scaled))
    return templates


TEMPLATES = load_templates()


def detect_and_press(stop_event: threading.Event):
    last_press = 0.0
    with mss.mss() as sct:
        while not stop_event.is_set():
            remaining = COOLDOWN - (time.perf_counter() - last_press)
            if remaining > 0:
                stop_event.wait(remaining)
                continue

            frame = np.asarray(sct.grab(SCAN_REGION))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

            scores = dict.fromkeys(KEYS, 0.0)
            for key, tmpl in TEMPLATES:
                res = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
                _, val, _, _ = cv2.minMaxLoc(res)
                if val > scores[key]:
                    scores[key] = val

            ranked = sorted(((v, k) for k, v in scores.items()), reverse=True)
            best_val, best_key = ranked[0]
            runner_up = ranked[1][0]

            # Press only when one letter clearly wins. Scores bunched together
            # mean the glyph wasn't really recognized and we'd hit a wrong key.
            if best_val >= MATCH_THRESHOLD and best_val - runner_up >= MATCH_MARGIN:
                pydirectinput.press(best_key.lower())
                last_press = time.perf_counter()

            time.sleep(SCAN_INTERVAL)


BG = "#1e1e2e"
FG = "#cdd6f4"
GREEN = "#a6e3a1"
RED = "#f38ba8"
SURFACE = "#313244"
MUTED = "#6c7086"


class MacroApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RGTF Macro")
        self.root.geometry("300x160")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)

        self.stop_event = threading.Event()
        self.stop_event.set()
        self.thread = None
        self.running = False

        tk.Label(
            root, text="RGTF Macro", font=("Segoe UI", 14, "bold"),
            bg=BG, fg=FG,
        ).pack(pady=(12, 4))

        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(pady=6)

        self.run_btn = tk.Button(
            btn_frame, text="Run", width=10, font=("Segoe UI", 10),
            bg=GREEN, fg=BG, activebackground="#94d89a",
            relief="flat", bd=0, command=self.start,
        )
        self.run_btn.grid(row=0, column=0, padx=6)

        self.stop_btn = tk.Button(
            btn_frame, text="Stop", width=10, font=("Segoe UI", 10),
            bg=SURFACE, fg=MUTED, activebackground=SURFACE,
            relief="flat", bd=0, state=tk.DISABLED, command=self.stop,
        )
        self.stop_btn.grid(row=0, column=1, padx=6)

        self.status_var = tk.StringVar(value="Stopped  |  F6 to toggle")
        tk.Label(
            root, textvariable=self.status_var, font=("Segoe UI", 9),
            bg=BG, fg=MUTED,
        ).pack(pady=(6, 0))

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
        self.thread = threading.Thread(
            target=detect_and_press, args=(self.stop_event,), daemon=True)
        self.thread.start()
        self.status_var.set("Running...  |  F6 to stop")
        self.run_btn.config(state=tk.DISABLED, bg=SURFACE, fg=MUTED)
        self.stop_btn.config(state=tk.NORMAL, bg=RED, fg=BG)

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        self.status_var.set("Stopped  |  F6 to toggle")
        self.run_btn.config(state=tk.NORMAL, bg=GREEN, fg=BG)
        self.stop_btn.config(state=tk.DISABLED, bg=SURFACE, fg=MUTED)

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
