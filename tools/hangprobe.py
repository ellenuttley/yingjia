"""Temporary: find what freezes autopick on Windows. Runs each variant in its own process."""
import subprocess
import sys
import time

VARIANTS = ["base", "ascii", "nofit", "norender", "nosave", "notop", "short"]


def child(variant):
    from yingjia import app, selftest
    if variant == "ascii":
        orig = app.AutoPick._render
        def render(self):
            orig(self)
            t = str(self.play_btn.cget("text"))
            self.play_btn.config(text="Pause" if "Pause" in t else "Play")
        app.AutoPick._render = render
        app.AutoPick.__init__.__globals__  # keep
    if variant == "nofit":
        app.Widget._fit_name = lambda self: None
    if variant == "norender":
        app.AutoPick._update = lambda self: None
    if variant == "nosave":
        selftest.Store.save = lambda self, data: None
    if variant == "notop":
        app.Widget._keep_on_top = lambda self: setattr(self, "_top_job", self.root.after(999999, lambda: None))
    t = selftest.SelfTest()
    t.start_hang_detector()
    steps = [t.first_run, t.classes_and_students]
    if variant != "short":
        steps += [t.picking, t.absences, t.import_export, t.no_resize_loop]
    for s in steps:
        s()
    t.log("start autopick")
    t.autopick()
    t.log(f"done {t.passed} passed, failures {t.failures}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        child(sys.argv[1])
        sys.exit(0)
    for v in VARIANTS:
        start = time.monotonic()
        try:
            r = subprocess.run([sys.executable, __file__, v], capture_output=True, text=True, timeout=60,
                               errors="backslashreplace")
            out = (r.stdout + r.stderr).strip().splitlines()
            print(f"== {v}: exit {r.returncode} in {time.monotonic()-start:.0f}s :: {out[-1] if out else ''}")
        except subprocess.TimeoutExpired as e:
            out = ((e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
            print(f"== {v}: HUNG :: {out.strip().splitlines()[-2:]}")
        sys.stdout.flush()
