"""End-to-end self-test: drives the real windows the way a teacher would.

Run from source with ``python -m yingjia.selftest``, or on a built exe with
``Yingjia.exe --self-test RESULT_FILE`` (the windowed exe has no console, so
the result goes to a file). Uses a throwaway data folder, never the
teacher's real class lists. Exit code 0 means every check passed.
"""
from __future__ import annotations

import faulthandler
import os
import shutil
import sys
import tempfile
import threading
import time
import tkinter as tk
import traceback
from collections import Counter, deque
from typing import Callable, List

from . import app, guide
from .storage import Store, today


class SelfTest:
    def __init__(self):
        self.failures: List[str] = []
        self.passed = 0
        self.tmp = tempfile.mkdtemp(prefix="yingjia-selftest-")
        self.answers: List[str] = []
        self.infos: List[str] = []
        self.open_path = ""
        self.save_path = ""
        # Replace modal dialogs with scripted answers.
        app.simpledialog.askstring = lambda *a, **k: self.answers.pop(0) if self.answers else None
        app.messagebox.askyesno = lambda *a, **k: True
        app.messagebox.showinfo = lambda title, msg, **k: self.infos.append(msg)
        app.filedialog.askopenfilename = lambda **k: self.open_path
        app.filedialog.asksaveasfilename = lambda **k: self.save_path

    # -- helpers -----------------------------------------------------------
    log_file = None

    def log(self, line: str):
        stream = self.log_file or sys.stdout
        if stream is not None:
            stream.write(line + "\n")
            stream.flush()

    def check(self, ok: bool, what: str):
        if ok:
            self.passed += 1
        else:
            self.failures.append(what)

    def wait(self, seconds: float):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.in_update = time.monotonic()
            self.root.update()
            self.in_update = None
            time.sleep(0.01)

    # -- hang detector -----------------------------------------------------
    # One root.update() should take milliseconds. If it runs for 10s, log
    # which of our functions keep being called inside it, so a hang on the
    # Windows build machine says what caused it.
    in_update = None
    calls: deque = deque(maxlen=2000)

    def _profile(self, frame, event, arg):
        if event == "call":
            code = frame.f_code
            if "yingjia" in code.co_filename and "selftest" not in code.co_filename:
                self.calls.append(code.co_name)

    def start_hang_detector(self):
        sys.setprofile(self._profile)
        threading.setprofile(None)

        def watch():
            reported = False
            while True:
                time.sleep(1)
                began = self.in_update
                if began is not None and time.monotonic() - began > 10 and not reported:
                    reported = True
                    recent = list(self.calls)
                    self.log("HANG: one update() has run for 10s. Most called recently: " +
                             ", ".join(f"{n} x{c}" for n, c in Counter(recent[-1000:]).most_common(12)))
                    self.log("HANG: last calls: " + " > ".join(recent[-40:]))
                elif began is None:
                    reported = False
        threading.Thread(target=watch, daemon=True).start()

    def start(self) -> app.Widget:
        self.root = tk.Tk()
        self.root.iconphoto(True, tk.PhotoImage(master=self.root, data=app.APP_ICON))
        self.store = Store(os.path.join(self.tmp, "data"))
        self.widget = app.Widget(self.root, self.store, self.store.load())
        self.wait(0.8)
        return self.widget

    def stop(self):
        self.widget.quit()
        self.root = None

    def find(self, parent: tk.Misc, cls: str, text: str = None):
        for child in parent.winfo_children():
            if child.winfo_class() == cls and (text is None or str(child.cget("text")) == text):
                return child
            found = self.find(child, cls, text)
            if found is not None:
                return found
        return None

    def toplevels(self, parent: tk.Misc):
        return [w for w in parent.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]

    def tab(self, widget: tk.Misc):
        widget.focus_force()
        self.wait(0.05)
        widget.event_generate("<KeyPress>", keysym="Tab", when="now")
        self.wait(1.0)  # let the shuffle animation finish

    # -- scenario ----------------------------------------------------------
    def run(self) -> List[str]:
        steps: List[Callable[[], None]] = [
            self.first_run, self.classes_and_students, self.picking, self.absences,
            self.import_export, self.no_resize_loop, self.autopick, self.lock_and_resize, self.themes_and_help,
            self.reopen_keeps_everything,
        ]
        for step in steps:
            self.log(f"running {step.__name__}")
            try:
                step()
            except Exception:
                self.failures.append(f"{step.__name__} crashed:\n{traceback.format_exc()}")
                break
        try:
            if self.root is not None:
                self.root.destroy()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        return self.failures

    def first_run(self):
        w = self.start()
        self.check(w.manager is not None and w.manager.win.winfo_exists(),
                   "first run opens Manage classes")
        helps = [t for t in self.toplevels(w.manager.win) if "使用说明" in t.title()]
        self.check(len(helps) == 1, "first run shows the Help guide")
        if helps:
            nb = self.find(helps[0], "TNotebook")
            self.check(nb is not None and len(nb.tabs()) == 2, "Help has English and 中文 tabs")
            helps[0].destroy()
        self.check(str(w.name_label.cget("text")) == "Press Tab", "widget starts with 'Press Tab'")
        self.check(self.find(self.root, "TMenubutton") is None, "no class drop-down on the widget")

    def classes_and_students(self):
        m = self.widget.manager
        self.answers = ["7B Maths"]
        m.new_class()
        self.check([c.name for c in self.widget.data.classes] == ["7B Maths"], "new class")
        for name in ["Amelia", "Ben", "王小明"]:
            m.new_name.set(name)
            m.add_student()
        m.new_name.set("ben")  # duplicate, different case
        m.add_student()
        c = self.widget.data.classes[0]
        self.check([s.name for s in c.students] == ["Amelia", "Ben", "王小明"], "add students, no duplicates")
        self.check(any("already" in i for i in self.infos), "duplicate student is refused with a message")

        m.paste_names()
        self.wait(0.2)
        dlg = [t for t in self.toplevels(m.win) if t.title() == "Paste many names"][0]
        self.find(dlg, "Text").insert("1.0", "Chen Wei\n\nDev\nAmelia\nElla\n")
        self.find(dlg, "TButton", "Add names").invoke()
        self.wait(0.1)
        self.check([s.name for s in c.students] == ["Amelia", "Ben", "王小明", "Chen Wei", "Dev", "Ella"],
                   "paste names adds new ones only")

        m.tree.selection_set("1")
        self.answers = ["Benjamin"]
        m.rename_student()
        self.check(c.students[1].name == "Benjamin", "rename student")
        m.tree.selection_set("5")
        m.remove_student()
        self.check("Ella" not in [s.name for s in c.students], "remove student")

        self.answers = ["7B Maths (spare)"]
        m.duplicate_class()
        self.check(len(self.widget.data.classes) == 2 and
                   len(self.widget.data.classes[1].students) == len(c.students), "duplicate class")
        self.answers = ["Spare"]
        m.rename_class()
        self.check(self.widget.data.classes[1].name == "Spare", "rename class")
        m.delete_class()
        self.check([x.name for x in self.widget.data.classes] == ["7B Maths"], "delete class")
        m.class_list.selection_clear(0, "end")
        m.class_list.selection_set(0)
        m.use_class()
        self.check(self.widget.data.current().name == "7B Maths", "use this class")

    def picking(self):
        w, m = self.widget, self.widget.manager
        names = {s.name for s in w.data.current().students}
        self.tab(w.name_label)
        picked = [w.picker.last]
        self.check(picked[0] is not None and str(w.name_label.cget("text")) == picked[0],
                   f"Tab on the widget picks a name (picked {picked[0]!r}, showing "
                   f"{w.name_label.cget('text')!r}, focus {self.root.focus_get()!r})")
        m.tree.focus_set()
        self.tab(m.tree)
        picked.append(w.picker.last)
        self.check(picked[1] is not None and picked[1] != picked[0],
                   f"Tab in Manage classes picks a new name (got {picked[1]!r}, focus {self.root.focus_get()!r})")
        before = w.picker.last
        entry = self.find(m.win, "TEntry")
        self.tab(entry)
        self.check(w.picker.last == before, "Tab while typing in a text box does not pick")
        for _ in range(len(names) * 2 - 2):
            w.pick()
            picked.append(w.picker.last)
        self.wait(0.7)
        first_round = picked[:len(names)]
        self.check(sorted(first_round) == sorted(names), "everyone picked once before any repeats")
        self.check(all(a != b for a, b in zip(picked, picked[1:])), "never the same name twice in a row")
        w.pick_btn.invoke()
        self.wait(0.7)
        self.check(w.picker.last in names, "dice button picks a name")

    def absences(self):
        w, m = self.widget, self.widget.manager
        c = w.data.current()
        m.tree.selection_set("0")  # Amelia
        m.toggle_absent()
        self.check(c.students[0].absent_on == today(), "click marks a student absent")
        self.check("absent" in m.tree.item("0", "tags"), "absent student shows grey")
        picks = set()
        for _ in range(30):
            w.pick()
            picks.add(w.picker.last)
        self.check("Amelia" not in picks, "absent student is never picked")
        self.check(len(c.students) == 5, "absent student stays on the list")
        c.students[0].absent_on = "2000-01-01"
        self.check(len(w.data.present_students(c)) == 5, "absence clears the next day")
        c.students[0].absent_on = today()
        c.students[1].absent_on = today()
        m.all_present()
        self.check(all(not s.absent_on for s in c.students), "Everyone's here clears absences")
        for s in c.students:
            s.absent_on = today()
        w.pick()
        self.wait(0.2)
        self.check(str(w.name_label.cget("text")) == "No one present", "everyone absent shows 'No one present'")
        m.all_present()

    def import_export(self):
        m = self.widget.manager
        gbk = os.path.join(self.tmp, "九年级.txt")
        with open(gbk, "wb") as f:
            f.write("李华\r\n张伟\r\n\r\nTom\r\n".encode("gbk"))
        self.open_path = gbk
        self.answers = ["九年级"]
        m.import_txt()
        imported = self.widget.data.classes[-1]
        self.check(imported.name == "九年级" and [s.name for s in imported.students] == ["李华", "张伟", "Tom"],
                   "import a GBK (Chinese Notepad) .txt list")
        self.save_path = os.path.join(self.tmp, "export.txt")
        m.export_txt()
        with open(self.save_path, encoding="utf-8") as f:
            self.check(f.read().split() == ["李华", "张伟", "Tom"], "export a class to .txt")
        m.class_list.selection_clear(0, "end")
        m.class_list.selection_set(0)
        m.show_students()

    def no_resize_loop(self):
        # Changing the name's font size must not trigger another resize forever
        # (this hung on Windows once).
        w = self.widget
        calls = []
        original = w._fit_name
        w._fit_name = lambda: (calls.append(1), original())
        w.pick()
        self.wait(1.0)
        w._fit_name = original
        self.check(len(calls) < 40, f"no endless resizing after a pick ({len(calls)} refits in 1s)")

    def autopick(self):
        w, m = self.widget, self.widget.manager
        self.find(m.win, "TButton", "Autopick").invoke()
        self.wait(0.2)
        a = m.autopick
        self.check(a is not None and a.win.winfo_exists(), "Autopick button opens its window")
        self.check(a.stop_btn.instate(["disabled"]), "Stop is disabled before starting")
        a.seconds.set(1)
        a.play_btn.invoke()
        first = w.picker.last
        self.check(w.auto_state == "running", "Play starts autopick")
        self.wait(1.3)
        self.check(w.picker.last != first, "autopick picks a new name every interval")
        a.play_btn.invoke()
        self.check(w.auto_state == "paused", "Pause pauses")
        left = w.auto_time_left()
        paused_on = w.picker.last
        self.wait(1.5)
        self.check(w.picker.last == paused_on, "no names while paused")
        self.check(abs(w.auto_time_left() - left) < 0.01, "pause keeps the time left")
        a.play_btn.invoke()
        self.check(w.auto_state == "running", "Play resumes")
        a.stop_btn.invoke()
        self.check(w.auto_state == "stopped", "Stop stops")
        a.play_btn.invoke()
        self.find(a.win, "TButton", "Close").invoke()
        self.wait(0.1)
        self.check(w.auto_state == "stopped" and not a.win.winfo_exists(), "closing Autopick stops it")
        m.open_autopick()
        m.autopick.play_btn.invoke()
        m.close()
        self.wait(0.1)
        self.check(w.auto_state == "stopped", "closing Manage classes stops autopick")
        w.open_manager()
        self.wait(0.3)

    def lock_and_resize(self):
        w = self.widget
        w.toggle_lock()
        self.wait(0.1)
        self.check(not w.close_btn.winfo_ismapped() and not w.manage_btn.winfo_ismapped(),
                   "locking hides close and settings")
        self.check(not w.grip.winfo_ismapped(), "locking hides the resize corner")
        w.lock_btn.invoke()
        self.check(w.data.settings.widget_locked, "clicking the lock can't unlock it")
        x0 = self.root.winfo_x()
        ev = type("E", (), {"x_root": 500, "y_root": 500})
        w._start_drag(ev)
        w._on_drag(type("E", (), {"x_root": 600, "y_root": 600}))
        self.wait(0.1)
        self.check(self.root.winfo_x() == x0, "locked widget can't be dragged")
        w.name_label.focus_force()
        w.name_label.event_generate("<Control-l>", when="now")
        self.wait(0.1)
        self.check(not w.data.settings.widget_locked and w.close_btn.winfo_ismapped()
                   and w.grip.winfo_ismapped(), "Ctrl+L unlocks")
        gx, gy = w.grip.winfo_rootx(), w.grip.winfo_rooty()
        w._start_resize(type("E", (), {"x_root": gx, "y_root": gy}))
        w._on_resize(type("E", (), {"x_root": gx + 200, "y_root": gy + 80}))
        w._end_resize(None)
        self.wait(0.3)
        self.check(w.data.settings.widget_w >= 600, "dragging the corner resizes the widget")
        small = w.name_font.cget("size")
        self.check(abs(small) > 40, "the name grows with the widget")
        w.name_label.config(text="Maximilian Featherstonehaugh-Smythe")
        w._fit_name()
        self.wait(0.1)
        self.check(w.name_font.measure(w.name_label.cget("text")) <= w.name_label.winfo_width(),
                   "long names shrink to fit")

    def themes_and_help(self):
        w, m = self.widget, self.widget.manager
        m.dark.set(True)
        m.toggle_dark()
        self.check(w.data.settings.theme == "dark", "dark mode switches on")
        m.dark.set(False)
        m.toggle_dark()
        self.check(w.data.settings.theme == "light", "dark mode switches off")
        self.find(m.win, "TButton", "Help").invoke()
        self.wait(0.3)
        helps = [t for t in self.toplevels(m.win) if "使用说明" in t.title()]
        self.check(len(helps) == 1, "Help button opens the guide")
        for h in helps:
            texts = []

            def collect(widget):
                for ch in widget.winfo_children():
                    if ch.winfo_class() == "Text":
                        texts.append(ch.get("1.0", "end"))
                    collect(ch)
            collect(h)
            self.check(len(texts) == 2 and "Tab" in texts[0] and "随机点名" in texts[1],
                       "Help shows the full English and Chinese guides")
            h.destroy()
        self.check(len(guide.steps("en")) == len(guide.steps("zh")), "guides have the same steps")

    def reopen_keeps_everything(self):
        data = self.widget.data
        expected = [(c.name, [s.name for s in c.students]) for c in data.classes]
        size = (data.settings.widget_w, data.settings.widget_h)
        self.stop()
        w = self.start()
        got = [(c.name, [s.name for s in c.students]) for c in w.data.classes]
        self.check(got == expected, "class lists are still there after closing and reopening")
        self.check((w.data.settings.widget_w, w.data.settings.widget_h) == size, "widget size is remembered")
        self.check(w.manager is not None and w.manager.win.winfo_exists(), "Manage classes opens with the widget")
        self.check(not [t for t in self.toplevels(w.manager.win) if "使用说明" in t.title()],
                   "the Help guide only pops up on the first run")
        self.tab(w.name_label)
        self.check(w.picker.last is not None, "picking works after reopening")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out = argv[0] if argv else None
    test = SelfTest()
    # If anything hangs, write where every thread is stuck and quit after 3 minutes.
    log = open(out + ".log", "w", encoding="utf-8") if out else None
    test.log_file = log
    faulthandler.dump_traceback_later(180, exit=True, file=log or sys.stderr)
    test.start_hang_detector()
    try:
        failures = test.run()
    except Exception:
        failures = ["self-test crashed:\n" + traceback.format_exc()]
    report = (f"{test.passed} checks passed, {len(failures)} failed\n" +
              "".join(f"FAIL: {f}\n" for f in failures))
    faulthandler.cancel_dump_traceback_later()
    if out:
        log.close()
        with open(out, "w", encoding="utf-8") as f:
            f.write(report)
    else:
        try:
            sys.stdout.reconfigure(errors="backslashreplace")  # Chinese names on a non-UTF-8 console
        except AttributeError:
            pass
        print(report, end="")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
