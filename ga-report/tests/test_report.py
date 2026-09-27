import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import fetch_ga4  # noqa: E402
import report  # noqa: E402

SUFFIX = " | 東方我楽多叢誌 〜strange article of the outer world〜"
EN_SUFFIX = " | Touhou Garakuta Magazine 〜strange article of the outer world〜"


def metrics(users, eng=40.0):
    return {"screenPageViews": users * 2, "activeUsers": users, "userEngagementDuration": users * eng,
            "eventCount": users * 3, "keyEvents": 0}


def sample_pages(scale=1.0, extra=None):
    raw = [("HOME" + SUFFIX, metrics(50000 * scale, 50))]
    for i in range(6):
        raw.append((f"聖地{i}を歩く――聖地巡礼手引き" + SUFFIX, metrics(3000 * scale, 55)))
    for i in range(40):
        raw.append((f"第{i}回イベント開催のお知らせ" + SUFFIX, metrics(150 * scale, 30)))
    for i in range(20):
        raw.append((f"連載 第{i}話【東方外來韋編】" + SUFFIX, metrics(1200 * scale, 70)))
    for i in range(20):
        raw.append((f"「話題{i}」など、今週の東方ニュースまとめ" + SUFFIX, metrics(700 * scale, 15)))
    raw.append(("Where to Play the Official Touhou Project Video Games" + EN_SUFFIX, metrics(9000 * scale, 30)))
    raw.append(("Some English column" + EN_SUFFIX, metrics(300 * scale, 30)))
    raw.extend(extra or [])
    return raw


def sample_acq(scale=1.0):
    return [("organic", {"totalUsers": 60000 * scale, "newUsers": 55000 * scale, "activeUsers": 60000 * scale,
                         "userEngagementDuration": 60000 * scale * 45, "eventCount": 1, "keyEvents": 0}),
            ("(none)", {"totalUsers": 30000 * scale, "newUsers": 28000 * scale, "activeUsers": 30000 * scale,
                        "userEngagementDuration": 30000 * scale * 40, "eventCount": 1, "keyEvents": 0})]


def write_month(root: Path, month: str, scale=1.0, extra=None):
    start, end = fetch_ga4.month_range(month)
    d = root / month
    fetch_ga4.write_ga_csv(d / "pages.csv", "pages", start, end, fetch_ga4.PAGE_HEADER,
                           fetch_ga4.page_rows(sample_pages(scale, extra)))
    fetch_ga4.write_ga_csv(d / "acquisition.csv", "acq", start, end, fetch_ga4.ACQ_HEADER,
                           fetch_ga4.acq_rows(sample_acq(scale)))
    return d


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.clf = report.Classifier(json.loads((HERE / "config.json").read_text(encoding="utf-8")))

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_written_csv(self):
        d = write_month(self.root, "2026-08")
        period = report.load_period(d / "pages.csv", d / "acquisition.csv", self.clf)
        self.assertEqual(period.meta["start"], "20260801")
        self.assertEqual(period.meta["end"], "20260831")
        home = next(p for p in period.pages if p.name == "HOME")
        self.assertTrue(home.is_hub)
        self.assertEqual(home.users, 50000)
        self.assertAlmostEqual(home.eng, 50)
        guide = next(p for p in period.pages if p.name.startswith("Where to Play"))
        self.assertEqual(guide.lang, "en")
        self.assertEqual(guide.category, "原作の遊び方・攻略")

    def test_advice_single_period(self):
        d = write_month(self.root, "2026-08")
        a = report.analyze(report.load_period(d / "pages.csv", d / "acquisition.csv", self.clf), None, self.clf)
        titles = [ad["title"] for ad in a.advice]
        self.assertIn("「聖地巡礼」の記事を増やす", titles)
        self.assertIn("「イベント情報」は細かく分けず、1ページにまとめて更新する", titles)
        self.assertIn("英語版は実用ガイドを増やす", titles)
        self.assertAlmostEqual(a.kpi["organic_share"], 60000 / 90000)
        html = report.render_html(a)
        self.assertIn("次に書く記事のアドバイス", html)
        self.assertNotIn("<h2>伸びた記事・落ちた記事", html)
        self.assertEqual(len(titles), len(set(titles)))

    def test_month_over_month(self):
        write_month(self.root, "2026-07")
        new = [("新しい話題の記事" + report.__name__ + SUFFIX, metrics(5000))]
        d = write_month(self.root, "2026-08", scale=1.0, extra=new)
        out = self.root / "out.html"
        self.assertEqual(report.main([str(d), "--out", str(out)]), 0)
        html = out.read_text(encoding="utf-8")
        self.assertIn("<h2>伸びた記事・落ちた記事", html)
        self.assertIn("新しい話題の記事", html)

    def test_english_export_headers(self):
        p = self.root / "en.csv"
        p.write_text("# Start date: 20260101\n# End date: 20260131\n"
                     "Page title and screen class,Views,Active users,Views per active user,"
                     "Average engagement time per active user,Event count,Key events,Total revenue\n"
                     "Hello | Touhou Garakuta Magazine,10,5,2,30,20,0,0\n", encoding="utf-8")
        meta, pages = report.load_pages(p, self.clf)
        self.assertEqual(meta["start"], "20260101")
        self.assertEqual((pages[0].views, pages[0].users, pages[0].eng), (10, 5, 30))

    def test_last_month(self):
        self.assertEqual(fetch_ga4.last_month(dt.date(2026, 1, 15)), "2025-12")
        self.assertEqual(fetch_ga4.month_range("2024-02"), (dt.date(2024, 2, 1), dt.date(2024, 2, 29)))


if __name__ == "__main__":
    unittest.main()
