"""The teacher's guide: a full English version and a full Chinese version.

Shown by the Help button in the app and saved as two .txt files next to the
download. Each step keeps its English and Chinese side by side here so the
two versions stay in step when one is edited.
"""

LANGS = ("en", "zh")
TITLES = {"en": "How to use Yingjia", "zh": "赢家 Yingjia 使用说明"}
TAB_NAMES = {"en": "English", "zh": "中文"}
FILES = {"en": "How to use Yingjia (English).txt", "zh": "Yingjia 使用说明 (中文).txt"}

STEPS = [
    ("Open Yingjia: double-click the Yingjia icon on the desktop.\n"
     "A small window appears at the top of the screen.",
     "打开 Yingjia：双击桌面上的 Yingjia 图标。\n"
     "屏幕上方会出现一个小窗口。"),
    ("Click the gear button (⚙) to open \"Manage classes\".",
     "点击齿轮按钮（⚙），打开“Manage classes”（管理班级）。"),
    ("Click \"New class…\". Type the class name. Click OK.",
     "点击“New class…”（新建班级），输入班级名称，点击 OK。"),
    ("Type a student's name in the box. Click \"Add student\".\n"
     "To add many names at once, click \"Paste many names…\". Put one name on each line.",
     "在输入框中输入学生姓名，点击“Add student”（添加学生）。\n"
     "要一次添加很多名字，请点击“Paste many names…”（粘贴名单），每行一个名字。"),
    ("Click your class in the list. Then click \"Use this class ★\".",
     "在列表中点击你的班级，然后点击“Use this class ★”（使用这个班级）。"),
    ("To pick a name: press the Tab key, or click the dice button.",
     "随机点名：按 Tab 键，或点击骰子按钮。"),
    ("A student is absent? Click their name in \"Manage classes\".\n"
     "The name turns grey. Yingjia will not pick them today.\n"
     "Tomorrow they come back by themselves.",
     "学生缺席？在“Manage classes”中点击该学生的名字。\n"
     "名字会变成灰色，今天不会被选中。\n"
     "明天会自动恢复。"),
    ("Autopick: click \"Autopick…\". Choose the seconds. Click Play.\n"
     "Pause stops the timer. Stop starts again from the beginning.\n"
     "Close the Autopick window to stop it.",
     "自动点名：点击“Autopick…”，选择秒数，点击 Play（开始）。\n"
     "Pause（暂停）会暂停计时，Stop（停止）会重新计时。\n"
     "关闭 Autopick 窗口就会停止自动点名。"),
    ("Move the window: drag it.\n"
     "Make it bigger or smaller: drag the bottom-right corner (◢).",
     "移动窗口：拖动它。\n"
     "改变大小：拖动右下角（◢）。"),
    ("Lock the window: press Ctrl + L. Students cannot move or close it.\n"
     "Press Ctrl + L again to unlock.",
     "锁定窗口：按 Ctrl + L，学生就不能移动或关闭它。\n"
     "再按一次 Ctrl + L 解锁。"),
    ("Close Yingjia: click ✕.",
     "关闭 Yingjia：点击 ✕。"),
]

NOTES = {"en": "Your class lists are saved only on this computer. Nothing is sent to the internet.",
         "zh": "名单只保存在这台电脑上，不会上传到网络。"}


def steps(lang: str):
    """The steps in one language, as a list of strings (may contain newlines)."""
    i = LANGS.index(lang)
    return [pair[i] for pair in STEPS]


def as_text(lang: str) -> str:
    lines = [TITLES[lang], "=" * 40, ""]
    for i, step in enumerate(steps(lang), 1):
        first, *rest = step.split("\n")
        lines.append(f"{i}. {first}")
        lines.extend("   " + part for part in rest)
        lines.append("")
    lines.append(NOTES[lang])
    # Windows Notepad shows CRLF line endings best.
    return "\r\n".join(lines) + "\r\n"


if __name__ == "__main__":
    import os
    import sys
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out_dir, exist_ok=True)
    for lang in LANGS:
        # UTF-8 with BOM so old versions of Notepad show the Chinese correctly.
        with open(os.path.join(out_dir, FILES[lang]), "w", encoding="utf-8-sig", newline="") as f:
            f.write(as_text(lang))
