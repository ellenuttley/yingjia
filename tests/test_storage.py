import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from yingjia.storage import AppData, Picker, Store, Student, parse_names, today  # noqa: E402


def make_class(names):
    data = AppData()
    c = data.add_class("7B")
    c.students = [Student(n) for n in names]
    return data, c


class PickerTests(unittest.TestCase):
    def test_everyone_once_before_repeat(self):
        names = ["Ana", "Ben", "Chen", "Dev", "Eli"]
        data, _ = make_class(names)
        p = Picker(data, random.Random(1))
        for _ in range(4):
            self.assertEqual(sorted(p.pick() for _ in names), sorted(names))

    def test_no_back_to_back_across_rounds(self):
        data, _ = make_class(["A", "B", "C"])
        p = Picker(data, random.Random(3))
        picks = [p.pick() for _ in range(60)]
        self.assertTrue(all(a != b for a, b in zip(picks, picks[1:])))

    def test_absent_never_picked_and_stays_on_list(self):
        data, c = make_class(["Ana", "Ben", "Chen"])
        c.students[1].absent_on = today()
        p = Picker(data, random.Random(2))
        self.assertNotIn("Ben", {p.pick() for _ in range(30)})
        self.assertEqual(len(c.students), 3)

    def test_absence_from_yesterday_clears(self):
        data, c = make_class(["Ana"])
        c.students[0].absent_on = "2000-01-01"
        self.assertEqual(len(data.present_students(c)), 1)
        data.settings.auto_reset_absences = False
        self.assertEqual(len(data.present_students(c)), 0)

    def test_everyone_absent(self):
        data, c = make_class(["Ana"])
        c.students[0].absent_on = today()
        self.assertIsNone(Picker(data).pick())

    def test_random_mode(self):
        data, _ = make_class(["A", "B"])
        data.settings.no_repeats = False
        p = Picker(data, random.Random(0))
        picks = [p.pick() for _ in range(20)]
        self.assertTrue(all(a != b for a, b in zip(picks, picks[1:])))


class StoreTests(unittest.TestCase):
    def test_round_trip_unicode(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(d)
            data, c = make_class(["王小明", "Zoë"])
            c.students[0].absent_on = today()
            data.settings.font_size = 40
            store.save(data)
            store.save(data)  # second save creates a .bak
            loaded = store.load()
            self.assertEqual([s.name for s in loaded.classes[0].students], ["王小明", "Zoë"])
            self.assertEqual(loaded.classes[0].students[0].absent_on, today())
            self.assertEqual(loaded.settings.font_size, 40)
            self.assertTrue(os.path.exists(store.path + ".bak"))

    def test_corrupt_file_falls_back_to_backup(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(d)
            data, _ = make_class(["Ana"])
            store.save(data)
            store.save(data)
            with open(store.path, "w") as f:
                f.write("{not json")
            self.assertEqual(store.load().classes[0].students[0].name, "Ana")

    def test_crud(self):
        data = AppData()
        a = data.add_class("A")
        b = data.duplicate_class(a.id, "B")
        self.assertEqual(len(data.classes), 2)
        data.delete_class(a.id)
        self.assertEqual(data.current().id, b.id)

    def test_parse_names(self):
        self.assertEqual(parse_names(" Ana \n\nben\nBen\nChen\r\n"), ["Ana", "ben", "Chen"])


class GuideTests(unittest.TestCase):
    def test_guide_has_both_languages(self):
        from yingjia import guide
        text = guide.as_text()
        self.assertIn("Tab", text)
        self.assertIn("使用说明", text)
        self.assertEqual(len(guide.STEPS), text.count("\r\n\r\n") - 1)


if __name__ == "__main__":
    unittest.main()
