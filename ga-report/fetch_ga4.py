#!/usr/bin/env python3
"""GA4 Data API から 1 か月分のデータを取り、report.py が読める CSV で保存する。

準備:
  pip install -r requirements.txt
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  export GA4_PROPERTY_ID=123456789   # GA4 の「プロパティ ID」(数字)

使い方:
  python fetch_ga4.py                  # 先月分を取得して data/YYYY-MM/ に保存
  python fetch_ga4.py --month 2026-09  # 月を指定
  python fetch_ga4.py --report         # 取得後にレポートも作る

前月のフォルダがなければ前月分も一緒に取得するので、初回から前月比が出る。
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PAGE_HEADER = ["ページ タイトルとスクリーン クラス", "表示回数", "アクティブ ユーザー",
               "アクティブ ユーザーあたりのビュー", "アクティブ ユーザーあたりの平均エンゲージメント時間",
               "イベント数", "キーイベント"]
ACQ_HEADER = ["ユーザーの最初のメディア", "総ユーザー数", "新規ユーザー数", "アクティブ ユーザー",
              "アクティブ ユーザーあたりの平均エンゲージメント時間", "イベント数", "キーイベント"]


def month_range(month: str) -> tuple[dt.date, dt.date]:
    y, m = (int(x) for x in month.split("-"))
    return dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])


def prev_month(month: str) -> str:
    y, m = (int(x) for x in month.split("-"))
    y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return f"{y:04d}-{m:02d}"


def last_month(today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    return prev_month(f"{today.year:04d}-{today.month:02d}")


def write_ga_csv(path: Path, title: str, start: dt.date, end: dt.date,
                 header: list[str], rows: list[list]) -> None:
    """GA4 の画面からエクスポートした CSV と同じ形で書く。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("# ----------------------------------------\n")
        f.write(f"# {title}\n")
        f.write("# ----------------------------------------\n")
        f.write(f"# 開始日: {start:%Y%m%d}\n")
        f.write(f"# 終了日: {end:%Y%m%d}\n")
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def page_rows(raw: list[tuple[str, dict]]) -> list[list]:
    """(ページタイトル, 指標) の列を CSV の行にする。"""
    rows = []
    for title, m in raw:
        users = m["activeUsers"]
        rows.append([title, int(m["screenPageViews"]), int(users),
                     m["screenPageViews"] / users if users else 0,
                     m["userEngagementDuration"] / users if users else 0,
                     int(m["eventCount"]), int(m["keyEvents"])])
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows


def acq_rows(raw: list[tuple[str, dict]]) -> list[list]:
    rows = []
    for medium, m in raw:
        active = m["activeUsers"]
        rows.append([medium, int(m["totalUsers"]), int(m["newUsers"]), int(active),
                     m["userEngagementDuration"] / active if active else 0,
                     int(m["eventCount"]), int(m["keyEvents"])])
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows


def run_report(client, property_id: str, dimension: str, metrics: list[str],
               start: dt.date, end: dt.date) -> list[tuple[str, dict]]:
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    out: list[tuple[str, dict]] = []
    offset, limit = 0, 100000
    while True:
        resp = client.run_report(RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=dimension)],
            metrics=[Metric(name=n) for n in metrics],
            date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
            limit=limit, offset=offset,
        ))
        for row in resp.rows:
            vals = {n: float(v.value or 0) for n, v in zip(metrics, row.metric_values)}
            out.append((row.dimension_values[0].value, vals))
        offset += limit
        if offset >= resp.row_count:
            return out


def fetch_month(client, property_id: str, month: str, data_dir: Path) -> Path:
    start, end = month_range(month)
    today = dt.date.today()
    if end >= today:
        end = today - dt.timedelta(days=1)
    d = data_dir / month
    pages = run_report(client, property_id, "unifiedScreenClass",
                       ["screenPageViews", "activeUsers", "userEngagementDuration", "eventCount", "keyEvents"],
                       start, end)
    write_ga_csv(d / "pages.csv", "ページとスクリーン: ページ タイトルとスクリーン クラス", start, end,
                 PAGE_HEADER, page_rows(pages))
    acq = run_report(client, property_id, "firstUserMedium",
                     ["totalUsers", "newUsers", "activeUsers", "userEngagementDuration", "eventCount", "keyEvents"],
                     start, end)
    write_ga_csv(d / "acquisition.csv", "ユーザー獲得: ユーザーの最初のメディア", start, end,
                 ACQ_HEADER, acq_rows(acq))
    print(f"{month} のデータを保存しました: {d}")
    return d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GA4 から 1 か月分のデータを取得する")
    ap.add_argument("--property", default=os.environ.get("GA4_PROPERTY_ID"), help="GA4 のプロパティ ID")
    ap.add_argument("--month", default=last_month(), help="取得する月 (YYYY-MM)。既定は先月")
    ap.add_argument("--data-dir", default=str(HERE / "data"))
    ap.add_argument("--report", action="store_true", help="取得後にレポートを作る")
    args = ap.parse_args(argv)

    if not args.property:
        ap.error("--property か環境変数 GA4_PROPERTY_ID でプロパティ ID を指定してください")
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
    except ImportError:
        print("google-analytics-data が入っていません。 pip install -r requirements.txt を実行してください。",
              file=sys.stderr)
        return 1

    client = BetaAnalyticsDataClient()
    data_dir = Path(args.data_dir)
    prev = prev_month(args.month)
    if not (data_dir / prev / "pages.csv").exists():
        fetch_month(client, args.property, prev, data_dir)
    d = fetch_month(client, args.property, args.month, data_dir)

    if args.report:
        import report
        return report.main([str(d)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
