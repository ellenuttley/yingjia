"""Windows 11 style look, bundled with the app so it works offline.

Uses the Sun Valley ttk theme (sv-ttk) when it is installed and falls back to
the stock Tk look otherwise.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

try:
    import sv_ttk
except ImportError:  # running from source without the theme installed
    sv_ttk = None

PALETTES = {
    "light": {
        "bg": "#fafafa", "surface": "#ffffff", "fg": "#1c1c1c", "muted": "#6b6b6b",
        "accent": "#005fb8", "border": "#005fb8", "select": "#cce4f7", "absent": "#a0a0a0",
    },
    "dark": {
        "bg": "#1c1c1c", "surface": "#2b2b2b", "fg": "#ffffff", "muted": "#a8a8a8",
        "accent": "#57c8ff", "border": "#57c8ff", "select": "#2f4a63", "absent": "#6e6e6e",
    },
}

FONT = "Segoe UI"


def palette(name: str) -> dict:
    return PALETTES.get(name, PALETTES["light"])


def apply(root: tk.Misc, name: str) -> dict:
    """Switch every ttk widget to the light or dark theme; returns the palette."""
    pal = palette(name)
    if sv_ttk is not None:
        sv_ttk.set_theme("dark" if name == "dark" else "light", root)
    style = ttk.Style(root)
    style.configure("Widget.TFrame", background=pal["bg"])
    style.configure("Border.TFrame", background=pal["border"])
    style.configure("Widget.TLabel", background=pal["bg"], foreground=pal["muted"], font=(FONT, 10))
    style.configure("Name.TLabel", background=pal["bg"], foreground=pal["fg"])
    style.configure("Pick.Accent.TButton", padding=(22, 4))
    style.configure("Icon.TButton", padding=(8, 6))
    style.configure("Hint.TLabel", foreground=pal["muted"])
    style.configure("Grip.TLabel", background=pal["bg"], foreground=pal["muted"], font=(FONT, 12))
    if sv_ttk is None:
        # Plain Tk has no Accent style; give the pick button some weight anyway.
        style.configure("Pick.Accent.TButton", foreground=pal["accent"])
    return pal


def style_tk(widget: tk.Misc, pal: dict) -> None:
    """Colour the classic Tk widgets (Listbox, Text, Menu) that ttk themes don't reach."""
    opts = {"background": pal["surface"], "foreground": pal["fg"],
            "selectbackground": pal["select"], "selectforeground": pal["fg"]}
    if isinstance(widget, tk.Listbox):
        widget.configure(highlightthickness=0, borderwidth=0, **opts)
    elif isinstance(widget, tk.Text):
        widget.configure(insertbackground=pal["fg"], highlightthickness=0, borderwidth=0, **opts)
    elif isinstance(widget, tk.Menu):
        widget.configure(background=pal["surface"], foreground=pal["fg"],
                         activebackground=pal["select"], activeforeground=pal["fg"],
                         selectcolor=pal["fg"], borderwidth=0)
