"""赢家 Yingjia ("winner"): a floating random student picker for Windows classrooms."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from . import theme
from .storage import AppData, Picker, Store, Student, parse_names, today

class Widget:
    """The small always-on-top window that shows the picked name."""

    def __init__(self, root: tk.Tk, store: Store, data: AppData):
        self.root = root
        self.store = store
        self.data = data
        self.picker = Picker(data)
        self.manager: Optional[Manager] = None
        self._drag = (0, 0)
        self.pal = theme.apply(root, data.settings.theme)

        root.title("赢家 Yingjia")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.minsize(340, 140)

        s = data.settings
        x = s.widget_x if s.widget_x is not None else (root.winfo_screenwidth() - 440) // 2
        y = s.widget_y if s.widget_y is not None else 10
        root.geometry(f"440x160+{x}+{y}")

        # A thin accent-coloured border keeps the widget visible over any slide.
        border = ttk.Frame(root, style="Border.TFrame", padding=2)
        border.pack(fill="both", expand=True)
        body = ttk.Frame(border, style="Widget.TFrame", padding=(12, 8, 12, 10))
        body.pack(fill="both", expand=True)

        top = ttk.Frame(body, style="Widget.TFrame")
        top.pack(fill="x")
        self.class_var = tk.StringVar()
        self.menu_var = tk.StringVar()
        self.class_menu = ttk.Menubutton(top, textvariable=self.class_var)
        self.class_menu.pack(side="left")
        self.count_label = ttk.Label(top, style="Widget.TLabel")
        self.count_label.pack(side="right")

        self.name_label = ttk.Label(body, text="Press Tab", style="Name.TLabel", anchor="center")
        self.name_label.pack(fill="both", expand=True, pady=2)

        bar = ttk.Frame(body, style="Widget.TFrame")
        bar.pack(fill="x")
        self.pick_btn = ttk.Button(bar, text="Pick a name  (Tab)", command=self.pick,
                                   style="Pick.Accent.TButton", cursor="hand2")
        self.pick_btn.pack(side="left")
        self.close_btn = self._small(bar, "✕", self.quit, "Close")
        self.lock_btn = self._small(bar, "🔓", self.toggle_lock, "Lock in place (Ctrl+L)")
        self.manage_btn = self._small(bar, "⚙", self.open_manager, "Manage classes")

        for w in (root, border, body, top, self.name_label, self.count_label, bar):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._end_drag)
        # Bound on the widget's own toplevel (not "all") so it runs before Tk's
        # built-in Tab-to-next-field handling and doesn't affect the manager.
        root.bind("<Tab>", self._on_tab)
        root.bind_all("<Control-l>", lambda e: self.toggle_lock())
        root.bind_all("<Control-L>", lambda e: self.toggle_lock())
        self.name_label.bind("<Double-Button-1>", lambda e: self.pick())

        self.refresh()
        self._apply_lock()
        self._keep_on_top()
        if not data.classes:
            root.after(300, self.open_manager)

    def _small(self, parent, text, cmd, tip):
        b = ttk.Button(parent, text=text, command=cmd, style="Icon.TButton", cursor="hand2")
        b.pack(side="right", padx=(6, 0))
        _Tooltip(b, tip)
        return b

    def set_theme(self, name: str):
        self.data.settings.theme = name
        self.pal = theme.apply(self.root, name)
        self.name_label.config(foreground=self.pal["fg"])
        self.refresh()

    # -- behaviour ---------------------------------------------------------
    def _on_tab(self, event):
        self.pick()
        return "break"

    def pick(self):
        c = self.data.current()
        if not c:
            self.name_label.config(text="Add a class first", foreground=self.pal["muted"])
            return
        name = self.picker.pick()
        if name is None:
            self.name_label.config(text="No one present", foreground=self.pal["muted"])
        else:
            self._animate(name)
        self.store.save(self.data)
        self.refresh_counts()

    def _animate(self, final: str, steps: int = 8):
        """A brief shuffle effect before landing on the picked name."""
        c = self.data.current()
        pool = [s.name for s in self.data.present_students(c)] if c else [final]
        rng = self.picker.rng

        def step(i):
            if i < steps and len(pool) > 1:
                self.name_label.config(text=rng.choice(pool), foreground=self.pal["muted"])
                self.root.after(35 + i * 10, step, i + 1)
            else:
                self.name_label.config(text=final, foreground=self.pal["fg"])
        step(0)

    def toggle_lock(self):
        self.data.settings.widget_locked = not self.data.settings.widget_locked
        self._apply_lock()
        self.store.save(self.data)

    def _apply_lock(self):
        locked = self.data.settings.widget_locked
        self.lock_btn.config(text="🔒" if locked else "🔓")
        for b in (self.close_btn, self.manage_btn):
            if locked:
                b.pack_forget()
            else:
                b.pack(side="right", padx=(6, 0), before=self.lock_btn)
        self.class_menu.state(["disabled"] if locked else ["!disabled"])
        # When locked, the lock button only responds to Ctrl+L.
        self.lock_btn.state(["disabled"] if locked else ["!disabled"])

    def _keep_on_top(self):
        # Other programs (e.g. a full screen slideshow) can steal top-most;
        # reassert it every couple of seconds.
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.after(2000, self._keep_on_top)

    def _start_drag(self, e):
        self.root.focus_force()
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _on_drag(self, e):
        if self.data.settings.widget_locked:
            return
        self.root.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _end_drag(self, e):
        s = self.data.settings
        if not s.widget_locked and (s.widget_x, s.widget_y) != (self.root.winfo_x(), self.root.winfo_y()):
            s.widget_x, s.widget_y = self.root.winfo_x(), self.root.winfo_y()
            self.store.save(self.data)

    def select_class(self, class_id: str):
        self.data.current_class_id = class_id
        self.picker.last = None
        self.store.save(self.data)
        self.name_label.config(text="Press Tab", foreground=self.pal["fg"])
        self.refresh()

    def refresh(self):
        c = self.data.current()
        self.class_var.set(c.name if c else "No classes yet")
        menu = tk.Menu(self.class_menu, tearoff=False)
        theme.style_tk(menu, self.pal)
        self.menu_var.set(c.id if c else "")
        for cl in self.data.classes:
            menu.add_radiobutton(label=cl.name, value=cl.id, variable=self.menu_var,
                                 command=lambda i=cl.id: self.select_class(i))
        menu.add_separator()
        menu.add_command(label="Manage classes…", command=self.open_manager)
        self.class_menu.config(menu=menu)
        self.name_label.config(font=(theme.FONT, self.data.settings.font_size, "bold"))
        self.refresh_counts()

    def refresh_counts(self):
        c = self.data.current()
        if not c:
            self.count_label.config(text="")
            return
        here = len(self.data.present_students(c))
        self.count_label.config(text=f"{here}/{len(c.students)} here")

    def open_manager(self):
        if self.manager and self.manager.win.winfo_exists():
            self.manager.win.lift()
            self.manager.win.focus_force()
            return
        self.manager = Manager(self)

    def quit(self):
        self.store.save(self.data)
        self.root.destroy()


class Manager:
    """Form window for creating, editing and deleting class lists."""

    def __init__(self, widget: Widget):
        self.widget = widget
        self.data = widget.data
        self.win = tk.Toplevel(widget.root)
        self.win.title("赢家 Yingjia – Manage classes")
        self.win.geometry("860x640")
        self.win.minsize(760, 600)
        self.win.attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self.close)

        pad = {"padx": 8, "pady": 4}
        outer = ttk.Frame(self.win, padding=10)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        # Left: classes
        left = ttk.LabelFrame(outer, text="Classes", padding=8)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        self.class_list = tk.Listbox(left, width=24, height=8, exportselection=False,
                                     font=(theme.FONT, 11), activestyle="none")
        theme.style_tk(self.class_list, widget.pal)
        self.class_list.pack(fill="y", expand=True)
        self.class_list.bind("<<ListboxSelect>>", lambda e: self.show_students())
        self.class_list.bind("<Double-Button-1>", lambda e: self.use_class())
        for text, cmd in (("New class…", self.new_class), ("Rename…", self.rename_class),
                          ("Duplicate…", self.duplicate_class), ("Delete", self.delete_class),
                          ("Import .txt…", self.import_txt), ("Export .txt…", self.export_txt)):
            ttk.Button(left, text=text, command=cmd).pack(fill="x", pady=2)

        # Right: students in selected class
        right = ttk.LabelFrame(outer, text="Students", padding=8)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        hint = ttk.Label(right, text="Click a student to mark them absent / present. "
                                     "Absent students stay on the list but won't be picked.",
                         style="Hint.TLabel", wraplength=480)
        hint.grid(row=0, column=0, columnspan=2, sticky="w")
        self.tree = ttk.Treeview(right, columns=("status", "name"), show="headings",
                                 selectmode="browse")
        self.tree.heading("status", text="Status")
        self.tree.heading("name", text="Name")
        self.tree.column("status", width=90, anchor="center", stretch=False)
        self.tree.column("name", width=300)
        self.tree.tag_configure("absent", foreground=widget.pal["absent"])
        self.tree.grid(row=1, column=0, sticky="nsew", pady=4)
        sb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        sb.grid(row=1, column=1, sticky="ns", pady=4)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<ButtonRelease-1>", self.toggle_absent)
        self.tree.bind("<space>", self.toggle_absent)
        self.tree.bind("<Delete>", lambda e: self.remove_student())

        add_row = ttk.Frame(right)
        add_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        add_row.columnconfigure(0, weight=1)
        self.new_name = tk.StringVar()
        entry = ttk.Entry(add_row, textvariable=self.new_name, font=(theme.FONT, 11))
        entry.grid(row=0, column=0, sticky="ew")
        entry.bind("<Return>", lambda e: self.add_student())
        ttk.Button(add_row, text="Add student", command=self.add_student).grid(row=0, column=1, padx=(6, 0))

        btns = ttk.Frame(right)
        btns.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        for text, cmd in (("Paste many names…", self.paste_names), ("Rename…", self.rename_student),
                          ("Remove", self.remove_student), ("Everyone's here", self.all_present)):
            ttk.Button(btns, text=text, command=cmd).pack(side="left", padx=(0, 6))

        # Bottom: settings
        bottom = ttk.LabelFrame(outer, text="Settings", padding=(8, 4))
        bottom.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        s = self.data.settings
        self.no_repeats = tk.BooleanVar(value=s.no_repeats)
        self.auto_reset = tk.BooleanVar(value=s.auto_reset_absences)
        self.font_size = tk.IntVar(value=s.font_size)
        self.dark = tk.BooleanVar(value=s.theme == "dark")
        ttk.Checkbutton(bottom, text="Pick everyone once before repeating", variable=self.no_repeats,
                        command=self.save_settings).grid(row=0, column=0, sticky="w", **pad)
        ttk.Checkbutton(bottom, text="Absences clear at the end of the day", variable=self.auto_reset,
                        command=self.save_settings).grid(row=1, column=0, sticky="w", **pad)
        ttk.Checkbutton(bottom, text="Dark mode", variable=self.dark,
                        command=self.toggle_dark).grid(row=0, column=1, sticky="w", **pad)
        size_row = ttk.Frame(bottom)
        size_row.grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(size_row, text="Name size").pack(side="left")
        ttk.Spinbox(size_row, from_=14, to=72, width=6, textvariable=self.font_size,
                    command=self.save_settings).pack(side="left", padx=(8, 0))
        ttk.Button(left, text="Use this class ★", command=self.use_class).pack(fill="x", pady=(10, 2))

        self.reload_classes()

    # -- helpers -----------------------------------------------------------
    def save(self):
        self.widget.store.save(self.data)
        self.widget.refresh()

    def selected_class(self):
        sel = self.class_list.curselection()
        return self.data.classes[sel[0]] if sel else None

    def selected_student(self) -> Optional[Student]:
        c = self.selected_class()
        sel = self.tree.selection()
        if not c or not sel:
            return None
        return c.students[int(sel[0])]

    def reload_classes(self, select_id: Optional[str] = None):
        self.class_list.delete(0, "end")
        current = self.data.current()
        target = select_id or (current.id if current else None)
        for i, c in enumerate(self.data.classes):
            mark = "  ★" if current and c.id == current.id else ""
            self.class_list.insert("end", f"{c.name}{mark}")
            if c.id == target:
                self.class_list.selection_set(i)
        self.show_students()

    def show_students(self):
        self.tree.delete(*self.tree.get_children())
        c = self.selected_class()
        if not c:
            return
        auto = self.data.settings.auto_reset_absences
        for i, st in enumerate(c.students):
            absent = st.is_absent(auto)
            self.tree.insert("", "end", iid=str(i), values=("Absent" if absent else "✓ Here", st.name),
                             tags=("absent",) if absent else ())

    def _ask(self, title, prompt, initial=""):
        return simpledialog.askstring(title, prompt, initialvalue=initial, parent=self.win)

    # -- class actions -----------------------------------------------------
    def new_class(self):
        name = self._ask("New class", "Class name (e.g. 7B Maths, Tuesday P3):")
        if name and name.strip():
            c = self.data.add_class(name)
            self.save()
            self.reload_classes(c.id)

    def rename_class(self):
        c = self.selected_class()
        if not c:
            return
        name = self._ask("Rename class", "New name:", c.name)
        if name and name.strip():
            c.name = name.strip()
            self.save()
            self.reload_classes(c.id)

    def duplicate_class(self):
        c = self.selected_class()
        if not c:
            return
        name = self._ask("Duplicate class", "Name for the copy:", c.name + " (copy)")
        if name and name.strip():
            new = self.data.duplicate_class(c.id, name)
            self.save()
            self.reload_classes(new.id)

    def delete_class(self):
        c = self.selected_class()
        if c and messagebox.askyesno("Delete class", f"Delete '{c.name}' and its {len(c.students)} "
                                     "students? This can't be undone.", parent=self.win):
            self.data.delete_class(c.id)
            self.save()
            self.reload_classes()

    def use_class(self):
        c = self.selected_class()
        if c:
            self.widget.select_class(c.id)
            self.reload_classes(c.id)

    def import_txt(self):
        path = filedialog.askopenfilename(parent=self.win, title="Import a class list",
                                          filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        text = _read_text(path)
        names = parse_names(text)
        if not names:
            messagebox.showinfo("Import", "No names found. Put one name per line.", parent=self.win)
            return
        default = os.path.splitext(os.path.basename(path))[0]
        name = self._ask("Import", f"Found {len(names)} names. Class name:", default)
        if name and name.strip():
            c = self.data.add_class(name)
            c.students = [Student(n) for n in names]
            self.save()
            self.reload_classes(c.id)

    def export_txt(self):
        c = self.selected_class()
        if not c:
            return
        path = filedialog.asksaveasfilename(parent=self.win, title="Export class list",
                                            defaultextension=".txt", initialfile=f"{c.name}.txt",
                                            filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(s.name for s in c.students) + "\n")

    # -- student actions ---------------------------------------------------
    def add_student(self):
        c = self.selected_class()
        name = self.new_name.get().strip()
        if not c:
            messagebox.showinfo("Add student", "Create or select a class first.", parent=self.win)
            return
        if not name:
            return
        if any(s.name.lower() == name.lower() for s in c.students):
            messagebox.showinfo("Add student", f"{name} is already in this class.", parent=self.win)
            return
        c.students.append(Student(name))
        self.new_name.set("")
        self.save()
        self.show_students()

    def paste_names(self):
        c = self.selected_class()
        if not c:
            messagebox.showinfo("Paste names", "Create or select a class first.", parent=self.win)
            return
        dlg = tk.Toplevel(self.win)
        dlg.title("Paste names")
        dlg.attributes("-topmost", True)
        dlg.transient(self.win)
        ttk.Label(dlg, text="Paste or type names, one per line:", padding=8).pack(anchor="w")
        txt = tk.Text(dlg, width=40, height=16, font=(theme.FONT, 11))
        theme.style_tk(txt, self.widget.pal)
        txt.pack(fill="both", expand=True, padx=8)
        txt.focus_set()

        def done():
            existing = {s.name.lower() for s in c.students}
            for n in parse_names(txt.get("1.0", "end")):
                if n.lower() not in existing:
                    c.students.append(Student(n))
            self.save()
            self.show_students()
            dlg.destroy()

        ttk.Button(dlg, text="Add names", command=done).pack(pady=8)

    def rename_student(self):
        st = self.selected_student()
        if not st:
            return
        name = self._ask("Rename student", "New name:", st.name)
        if name and name.strip():
            st.name = name.strip()
            self.save()
            self.show_students()

    def remove_student(self):
        c, st = self.selected_class(), self.selected_student()
        if c and st and messagebox.askyesno("Remove student", f"Remove {st.name} from {c.name}?",
                                            parent=self.win):
            c.students.remove(st)
            self.save()
            self.show_students()

    def toggle_absent(self, event=None):
        if event is not None and getattr(event, "type", None) == tk.EventType.ButtonRelease:
            if self.tree.identify_region(event.x, event.y) != "cell":
                return
        st = self.selected_student()
        if not st:
            return
        st.absent_on = "" if st.is_absent(self.data.settings.auto_reset_absences) else today()
        sel = self.tree.selection()
        self.save()
        self.show_students()
        if sel:
            self.tree.selection_set(sel)

    def all_present(self):
        c = self.selected_class()
        if c:
            for st in c.students:
                st.absent_on = ""
            self.save()
            self.show_students()

    def save_settings(self):
        s = self.data.settings
        s.no_repeats = self.no_repeats.get()
        s.auto_reset_absences = self.auto_reset.get()
        try:
            s.font_size = max(14, min(72, int(self.font_size.get())))
        except (tk.TclError, ValueError):
            pass
        self.save()
        self.show_students()

    def toggle_dark(self):
        self.widget.set_theme("dark" if self.dark.get() else "light")
        pal = self.widget.pal
        theme.style_tk(self.class_list, pal)
        self.tree.tag_configure("absent", foreground=pal["absent"])
        self.save()

    def close(self):
        self.save_settings()
        self.win.destroy()


def _read_text(path: str) -> str:
    # Teachers' existing lists may be saved by Notepad in UTF-8, UTF-16 or GBK.
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-16", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


class _Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _):
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        self.tip.geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="#ffffe0", relief="solid", bd=1,
                 font=("Segoe UI", 9)).pack()

    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None


def main():
    store = Store()
    data = store.load()
    try:
        # Crisp text on high-DPI screens / smart boards (must run before Tk starts).
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    Widget(root, store, data)
    root.mainloop()


if __name__ == "__main__":
    main()
