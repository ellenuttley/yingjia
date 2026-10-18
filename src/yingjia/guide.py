"""The teacher's guide, in short English and Simplified Chinese.

Shown by the Help button in the app and saved as a .txt file next to the
download, so there is one copy to keep up to date.
"""

TITLE = "How to use Yingjia  ·  赢家 使用说明"

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
     "To add many names at once, click \"Paste names…\". Put one name on each line.",
     "在输入框中输入学生姓名，点击“Add student”（添加学生）。\n"
     "要一次添加很多名字，请点击“Paste names…”（粘贴名单），每行一个名字。"),
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

NOTE = ("Your class lists are saved only on this computer. Nothing is sent to the internet.\n"
        "名单只保存在这台电脑上，不会上传到网络。")


def as_text() -> str:
    lines = [TITLE, "=" * 40, ""]
    for i, (en, zh) in enumerate(STEPS, 1):
        first, *rest = en.split("\n")
        lines.append(f"{i}. {first}")
        lines.extend("   " + part for part in rest)
        lines.extend("   " + part for part in zh.split("\n"))
        lines.append("")
    lines.append(NOTE)
    # Windows Notepad shows CRLF line endings best.
    return "\r\n".join(lines) + "\r\n"


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "How to use - 使用说明.txt"
    # UTF-8 with BOM so old versions of Notepad show the Chinese correctly.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(as_text())
