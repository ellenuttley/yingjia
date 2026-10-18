"""Temporary: time Chinese text at new font sizes on Windows."""
import time
import tkinter as tk
from tkinter import font as tkfont

root = tk.Tk()
fams = sorted(f for f in tkfont.families(root) if "YaHei" in f or "Sim" in f or "Hei" in f)
print("CJK families:", fams, "total families:", len(tkfont.families(root)))
for family in ("Segoe UI", "Microsoft YaHei UI"):
    f = tkfont.Font(root, family=family, size=-40, weight="bold")
    lbl = tk.Label(root, font=f, text="王小明")
    lbl.pack()
    for px in (41, 53, 67, 79):
        t = time.monotonic()
        f.configure(size=-px)
        w = f.measure("王小明")
        root.update()
        print(f"{family} {px}px: {time.monotonic() - t:.2f}s width {w}", flush=True)
