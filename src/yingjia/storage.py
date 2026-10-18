"""Local-only storage for class lists.

Everything lives in one JSON file on the teacher's PC. Nothing is ever sent
over the network.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import random
import sys
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional

APP_NAME = "Yingjia"
DATA_VERSION = 1


def data_dir() -> str:
    """Where the data file lives.

    If a file called ``portable.txt`` sits next to the program, data is kept
    in a ``data`` folder beside it (handy for running from a USB stick).
    Otherwise it goes in the user's AppData folder.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0] or __file__))
    if os.path.exists(os.path.join(exe_dir, "portable.txt")):
        return os.path.join(exe_dir, "data")
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_NAME)


def today() -> str:
    return _dt.date.today().isoformat()


@dataclass
class Student:
    name: str
    # Date (YYYY-MM-DD) the student was marked absent, or "" if present.
    absent_on: str = ""

    def is_absent(self, auto_reset: bool) -> bool:
        if not self.absent_on:
            return False
        return self.absent_on == today() if auto_reset else True


@dataclass
class ClassList:
    name: str
    students: List[Student] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    # Names still to be picked in this round (see Picker).
    bag: List[str] = field(default_factory=list)


@dataclass
class Settings:
    # Absent marks only last for the day they were set.
    auto_reset_absences: bool = True
    # Everyone gets picked once before anyone is picked again.
    no_repeats: bool = True
    widget_x: Optional[int] = None
    widget_y: Optional[int] = None
    widget_locked: bool = False
    font_size: int = 28  # no longer used: the name now scales with the widget
    widget_w: int = 440
    widget_h: int = 170
    theme: str = "light"
    auto_seconds: int = 10


@dataclass
class AppData:
    classes: List[ClassList] = field(default_factory=list)
    current_class_id: Optional[str] = None
    settings: Settings = field(default_factory=Settings)

    # -- class helpers -----------------------------------------------------
    def current(self) -> Optional[ClassList]:
        for c in self.classes:
            if c.id == self.current_class_id:
                return c
        return self.classes[0] if self.classes else None

    def get(self, class_id: str) -> Optional[ClassList]:
        return next((c for c in self.classes if c.id == class_id), None)

    def add_class(self, name: str) -> ClassList:
        c = ClassList(name=name.strip())
        self.classes.append(c)
        if self.current_class_id is None:
            self.current_class_id = c.id
        return c

    def delete_class(self, class_id: str) -> None:
        self.classes = [c for c in self.classes if c.id != class_id]
        if self.current_class_id == class_id:
            self.current_class_id = self.classes[0].id if self.classes else None

    def duplicate_class(self, class_id: str, new_name: str) -> Optional[ClassList]:
        src = self.get(class_id)
        if not src:
            return None
        c = ClassList(name=new_name.strip(), students=[Student(s.name) for s in src.students])
        self.classes.append(c)
        return c

    def present_students(self, c: ClassList) -> List[Student]:
        auto = self.settings.auto_reset_absences
        return [s for s in c.students if not s.is_absent(auto)]


def parse_names(text: str) -> List[str]:
    """One name per line; blank lines and duplicate names are ignored."""
    seen, out = set(), []
    for line in text.splitlines():
        name = line.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return out


class Picker:
    """Random picking with an optional 'no repeats until everyone has gone' bag."""

    def __init__(self, data: AppData, rng: Optional[random.Random] = None):
        self.data = data
        self.rng = rng or random.SystemRandom()
        self.last: Optional[str] = None

    def pick(self) -> Optional[str]:
        c = self.data.current()
        if not c:
            return None
        present = [s.name for s in self.data.present_students(c)]
        if not present:
            return None
        if not self.data.settings.no_repeats:
            choices = present if len(present) == 1 else [n for n in present if n != self.last]
            name = self.rng.choice(choices)
        else:
            c.bag = [n for n in c.bag if n in present]
            if not c.bag:
                c.bag = list(present)
                # Avoid the same name twice in a row across a new round.
                if len(c.bag) > 1 and self.last in c.bag:
                    c.bag.remove(self.last)
                    self.rng.shuffle(c.bag)
                    c.bag.append(self.last)
                else:
                    self.rng.shuffle(c.bag)
            name = c.bag.pop(0)
        self.last = name
        return name


class Store:
    def __init__(self, directory: Optional[str] = None):
        self.directory = directory or data_dir()
        self.path = os.path.join(self.directory, "classes.json")

    def load(self) -> AppData:
        if not os.path.exists(self.path):
            return AppData()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            # Keep the damaged file for recovery, start fresh.
            try:
                os.replace(self.path, self.path + ".corrupt")
            except OSError:
                pass
            backup = self.path + ".bak"
            if os.path.exists(backup):
                with open(backup, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            else:
                return AppData()
        return self._from_dict(raw)

    def save(self, data: AppData) -> None:
        os.makedirs(self.directory, exist_ok=True)
        payload = {"version": DATA_VERSION, **asdict(data)}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(self.path):
            try:
                os.replace(self.path, self.path + ".bak")
            except OSError:
                pass
        os.replace(tmp, self.path)

    @staticmethod
    def _from_dict(raw: dict) -> AppData:
        settings_keys = Settings.__dataclass_fields__.keys()
        settings = Settings(**{k: v for k, v in raw.get("settings", {}).items() if k in settings_keys})
        classes = []
        for c in raw.get("classes", []):
            students = [Student(name=s.get("name", ""), absent_on=s.get("absent_on", ""))
                        for s in c.get("students", []) if s.get("name")]
            classes.append(ClassList(name=c.get("name", "Class"), students=students,
                                     id=c.get("id") or uuid.uuid4().hex, bag=list(c.get("bag", []))))
        return AppData(classes=classes, current_class_id=raw.get("current_class_id"), settings=settings)
