"""Run: python -m unittest discover -s tests"""
import unittest
from datetime import date, timedelta

from scraper.common import Event, TODAY, detect_type, looks_turkish, parse_en_range_end, parse_tr_date
from scraper.run import is_active, norm_title


class DateParsing(unittest.TestCase):
    def test_tr_with_year(self):
        self.assertEqual(parse_tr_date("05 Aralık 2026"), date(2026, 12, 5))

    def test_tr_range_takes_last_day(self):
        self.assertEqual(parse_tr_date("06 – 07 Kasım 2026"), date(2026, 11, 7))

    def test_tr_numeric(self):
        self.assertEqual(parse_tr_date("Son başvuru: 15.01.2027"), date(2027, 1, 15))

    def test_tr_without_year_is_near_today(self):
        d = parse_tr_date("19 Ekim")
        self.assertIsNotNone(d)
        self.assertLessEqual(abs((d - TODAY).days), 366)

    def test_tr_garbage(self):
        self.assertIsNone(parse_tr_date("yakında"))
        self.assertIsNone(parse_tr_date(None))

    def test_devpost_ranges(self):
        self.assertEqual(parse_en_range_end("Aug 26 - Oct 30, 2026"), date(2026, 10, 30))
        self.assertEqual(parse_en_range_end("Oct 01 - 15, 2026"), date(2026, 10, 15))
        self.assertEqual(parse_en_range_end("Dec 01, 2026 - Jan 10, 2027"), date(2027, 1, 10))


class Classification(unittest.TestCase):
    def test_types(self):
        self.assertEqual(detect_type("Garanti BBVA Datathon"), "datathon")
        self.assertEqual(detect_type("Fikir Maratonu 2026"), "ideathon")
        self.assertEqual(detect_type("İTÜ Hackathonu"), "hackathon")
        self.assertEqual(detect_type("Robot Yarışması"), "yarisma")
        self.assertIsNone(detect_type("Kariyer Zirvesi"))

    def test_turkey_hint(self):
        self.assertTrue(looks_turkish("Kadıköy, İstanbul"))
        self.assertFalse(looks_turkish("Berlin, Germany"))

    def test_norm_title_ignores_year_and_type(self):
        self.assertEqual(norm_title("Akbank Hackathon 2026"), norm_title("akbank hackathon"))


class Activity(unittest.TestCase):
    def ev(self, **kw):
        return Event(title="x", url="https://x", source="t", **kw)

    def test_deadline_decides(self):
        past, future = (TODAY - timedelta(days=1)).isoformat(), (TODAY + timedelta(days=3)).isoformat()
        self.assertTrue(is_active(self.ev(deadline=TODAY.isoformat())))
        self.assertTrue(is_active(self.ev(deadline=future, start=past)))
        self.assertFalse(is_active(self.ev(deadline=past, start=future)))

    def test_started_without_deadline_is_closed(self):
        self.assertFalse(is_active(self.ev(start=(TODAY - timedelta(days=1)).isoformat())))

    def test_undated_expires(self):
        self.assertTrue(is_active(self.ev(first_seen=TODAY.isoformat())))
        self.assertFalse(is_active(self.ev(first_seen=(TODAY - timedelta(days=30)).isoformat())))


if __name__ == "__main__":
    unittest.main()
