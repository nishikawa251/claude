#!/usr/bin/env python3
"""GA4 のエクスポート CSV から「次に書く記事」のアドバイス付きレポート (HTML) を作る。

使い方:
  # 月ごとのフォルダ (data/2026-09/pages.csv, acquisition.csv) から作る。
  # 前月のフォルダがあれば自動で比較する。
  python report.py data/2026-09

  # ファイルを直接指定する
  python report.py --pages pages.csv --acquisition acquisition.csv \
      [--prev-pages prev_pages.csv --prev-acquisition prev_acq.csv] --out report.html

標準ライブラリだけで動く。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent

# GA4 のエクスポートは UI の言語で列名が変わるので、日本語と英語の両方を探す。
# 見つからないときは既定のエクスポートの列順で読む。
PAGE_COLS = {
    "views": (["表示回数", "Views"], 1),
    "users": (["アクティブ ユーザー", "Active users"], 2),
    "eng": (["アクティブ ユーザーあたりの平均エンゲージメント時間", "Average engagement time per active user"], 4),
    "key_events": (["キーイベント", "Key events"], 6),
}
ACQ_COLS = {
    "users": (["総ユーザー数", "Total users"], 1),
    "eng": (["アクティブ ユーザーあたりの平均エンゲージメント時間", "Average engagement time per active user"], 4),
    "key_events": (["キーイベント", "Key events"], 7),
}
MEDIUM_LABELS = {
    "organic": "検索 (organic)",
    "(none)": "直接・アプリ内など (none)",
    "referral": "他サイトのリンク (referral)",
    "ai-assistant": "AIアシスタント",
    "social": "SNS (social)",
    "email": "メール",
    "cpc": "広告 (cpc)",
    "(not set)": "不明 (not set)",
}


# ---------------------------------------------------------------- 読み込み

def read_ga_csv(path: Path) -> tuple[dict, list[str], list[list[str]]]:
    """GA4 の CSV を読む。先頭の # 行から期間を取り出す。"""
    meta: dict = {}
    lines: list[str] = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            if line.startswith("#"):
                m = re.search(r"(開始日|Start date)\s*:\s*(\d{8})", line)
                if m:
                    meta["start"] = m.group(2)
                m = re.search(r"(終了日|End date)\s*:\s*(\d{8})", line)
                if m:
                    meta["end"] = m.group(2)
                m = re.search(r"(プロパティ|Property)\s*:\s*(.+)", line)
                if m:
                    meta["property"] = m.group(2).strip()
                continue
            if line.strip():
                lines.append(line)
    rows = list(csv.reader(lines))
    if not rows:
        raise ValueError(f"{path}: データ行がありません")
    return meta, rows[0], rows[1:]


def _col_index(header: list[str], names: list[str], fallback: int) -> int:
    for i, h in enumerate(header):
        if any(h.strip() == n or h.strip().startswith(n) for n in names):
            return i
    return fallback


def _num(s: str) -> float:
    try:
        return float(s.replace(",", "")) if s.strip() else 0.0
    except ValueError:
        return 0.0


@dataclass
class Page:
    title: str
    name: str
    lang: str
    views: float
    users: float
    eng: float
    key_events: float
    category: str = ""
    is_hub: bool = False


@dataclass
class Period:
    meta: dict
    pages: list[Page]
    acquisition: list[dict]


class Classifier:
    def __init__(self, config: dict):
        self.config = config
        self.langs = [(l["code"], re.compile(l["match"])) for l in config["languages"]]
        self.primary = config["primary_language"]
        self.hub = re.compile(config["hub_pattern"])
        self.cats = [(c["name"], re.compile(c["pattern"])) for c in config["categories"]]
        self.other = config.get("other_category", "その他")
        self.evergreen = {c["name"] for c in config["categories"] if c.get("evergreen")}

    def lang_of(self, title: str) -> str:
        for code, pat in self.langs:
            if pat.search(title):
                return code
        return self.primary

    def strip_site(self, title: str) -> str:
        head, sep, tail = title.rpartition(" | ")
        if sep and any(p.search(tail) for _, p in self.langs):
            return head.strip()
        return title.strip()

    def category_of(self, name: str) -> tuple[str, bool]:
        if self.hub.search(name):
            return "ハブページ", True
        for cname, pat in self.cats:
            if pat.search(name):
                return cname, False
        return self.other, False


def load_pages(path: Path, clf: Classifier) -> tuple[dict, list[Page]]:
    meta, header, rows = read_ga_csv(path)
    idx = {k: _col_index(header, names, fb) for k, (names, fb) in PAGE_COLS.items()}
    pages = []
    for r in rows:
        if not r or len(r) <= max(idx.values()):
            continue
        title = r[0].strip()
        if not title:
            continue
        name = clf.strip_site(title)
        cat, hub = clf.category_of(name)
        pages.append(Page(
            title=title, name=name, lang=clf.lang_of(title),
            views=_num(r[idx["views"]]), users=_num(r[idx["users"]]),
            eng=_num(r[idx["eng"]]), key_events=_num(r[idx["key_events"]]),
            category=cat, is_hub=hub,
        ))
    return meta, pages


def load_acquisition(path: Path) -> list[dict]:
    _, header, rows = read_ga_csv(path)
    idx = {k: _col_index(header, names, fb) for k, (names, fb) in ACQ_COLS.items()}
    out = []
    for r in rows:
        if not r or len(r) <= max(idx["users"], idx["eng"]):
            continue
        medium = r[0].strip() or "(空欄)"
        ke = _num(r[idx["key_events"]]) if len(r) > idx["key_events"] else 0.0
        out.append({"medium": medium, "users": _num(r[idx["users"]]),
                    "eng": _num(r[idx["eng"]]), "key_events": ke})
    return out


def load_period(pages_path: Path, acq_path: Path | None, clf: Classifier) -> Period:
    meta, pages = load_pages(pages_path, clf)
    acq = load_acquisition(acq_path) if acq_path and acq_path.exists() else []
    return Period(meta, pages, acq)


# ---------------------------------------------------------------- 集計

def _median(xs: list[float]) -> float:
    return statistics.median(xs) if xs else 0.0


def _weighted_eng(pages: list[Page]) -> float:
    u = sum(p.users for p in pages)
    return sum(p.users * p.eng for p in pages) / u if u else 0.0


def auto_min_users(pages: list[Page]) -> int:
    """記事として数える最低ユーザー数。期間の規模に合わせて 3〜50 人にする。"""
    total = sum(p.users for p in pages)
    return int(min(50, max(3, round(total / 200000))))


@dataclass
class CatStat:
    name: str
    n: int
    users: float
    median: float
    eng: float
    share: float
    top: list[Page]
    top_all: list[Page]
    evergreen: bool
    verdict: str = ""
    prev_users: float | None = None


@dataclass
class Analysis:
    site: str
    meta: dict
    prev_meta: dict | None
    min_users: int
    kpi: dict
    prev_kpi: dict | None
    sources: list[dict]
    langs: list[dict]
    cats: list[CatStat]
    ref: dict
    top_articles: list[Page]
    prev_users_by_title: dict
    rising: list[tuple[Page, float]]
    falling: list[tuple[Page, float]]
    advice: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def compute_kpi(period: Period) -> dict:
    acq = period.acquisition
    users = sum(a["users"] for a in acq) if acq else sum(p.users for p in period.pages)
    organic = sum(a["users"] for a in acq if a["medium"] == "organic")
    eng = (sum(a["users"] * a["eng"] for a in acq) / users) if acq and users else _weighted_eng(period.pages)
    return {
        "users": users,
        "views": sum(p.views for p in period.pages),
        "organic_share": organic / users if acq and users else None,
        "eng": eng,
        "key_events": sum(a["key_events"] for a in acq) + sum(p.key_events for p in period.pages),
    }


def analyze(cur: Period, prev: Period | None, clf: Classifier, min_users: int | None = None) -> Analysis:
    cfg = clf.config
    min_users = min_users or auto_min_users(cur.pages)
    articles = [p for p in cur.pages if not p.is_hub and p.users >= min_users]
    primary = [p for p in articles if p.lang == clf.primary]

    prev_by_title: dict[str, float] = {}
    prev_cat_users: dict[str, float] = {}
    if prev:
        for p in prev.pages:
            prev_by_title[p.title] = prev_by_title.get(p.title, 0) + p.users
            if not p.is_hub and p.lang == clf.primary:
                prev_cat_users[p.category] = prev_cat_users.get(p.category, 0) + p.users

    # 記事の種類ごと (主言語のみ)
    total_primary = sum(p.users for p in primary) or 1
    by_cat: dict[str, list[Page]] = {}
    for p in primary:
        by_cat.setdefault(p.category, []).append(p)
    cats = []
    for name, ps in by_cat.items():
        ps.sort(key=lambda p: p.users, reverse=True)
        cats.append(CatStat(
            name=name, n=len(ps), users=sum(p.users for p in ps),
            median=_median([p.users for p in ps]), eng=_weighted_eng(ps),
            share=sum(p.users for p in ps) / total_primary, top=ps[:5], top_all=ps[:30],
            evergreen=name in clf.evergreen,
            prev_users=prev_cat_users.get(name) if prev else None,
        ))
    cats.sort(key=lambda c: c.median, reverse=True)
    core = [c for c in cats if c.name != clf.other and c.n >= 3]
    ref = {
        "median": _median([c.median for c in core]),
        "n": _median([c.n for c in core]),
        "eng": _median([c.eng for c in core]),
    }

    # 言語別
    langs = []
    labels = {l["code"]: l["label"] for l in cfg["languages"]}
    for code in labels:
        ps = sorted((p for p in cur.pages if p.lang == code and not p.is_hub),
                    key=lambda p: p.users, reverse=True)
        users = sum(p.users for p in ps)
        if not users:
            continue
        langs.append({"code": code, "label": labels[code], "users": users,
                      "pages": len([p for p in ps if p.users >= min_users]),
                      "top": ps[:5], "top_share": ps[0].users / users if ps else 0})

    # 流入元
    acq_total = sum(a["users"] for a in cur.acquisition) or 1
    sources = sorted(({**a, "share": a["users"] / acq_total,
                       "label": MEDIUM_LABELS.get(a["medium"], a["medium"])}
                      for a in cur.acquisition if a["users"] > 0),
                     key=lambda a: a["users"], reverse=True)

    # 前の期間との比較
    rising: list[tuple[Page, float]] = []
    falling: list[tuple[Page, float]] = []
    if prev:
        for p in articles:
            before = prev_by_title.get(p.title, 0.0)
            if p.users - before >= max(min_users * 5, 50) and p.users >= before * 1.5:
                rising.append((p, before))
        rising.sort(key=lambda t: t[0].users - t[1], reverse=True)
        cur_by_title = {p.title: p for p in cur.pages}
        for p in prev.pages:
            if p.is_hub or p.users < max(min_users * 20, 200):
                continue
            now = cur_by_title.get(p.title)
            now_users = now.users if now else 0.0
            if now_users <= p.users * 0.6:
                falling.append((now or Page(p.title, p.name, p.lang, 0, 0, 0, 0, p.category), p.users))
        falling.sort(key=lambda t: t[1] - t[0].users, reverse=True)

    a = Analysis(
        site=cfg.get("site_name", ""), meta=cur.meta, prev_meta=prev.meta if prev else None,
        min_users=min_users, kpi=compute_kpi(cur), prev_kpi=compute_kpi(prev) if prev else None,
        sources=sources, langs=langs, cats=cats, ref=ref,
        top_articles=sorted(articles, key=lambda p: p.users, reverse=True)[:15],
        prev_users_by_title=prev_by_title, rising=rising[:8], falling=falling[:8],
    )
    a.advice = build_advice(a, clf)
    a.notes = build_notes(a, cur)
    return a


# ---------------------------------------------------------------- アドバイス

def fmt_n(x: float) -> str:
    x = round(x)
    if x >= 100000:
        return f"{x / 10000:.0f}万"
    if x >= 10000:
        return f"{x / 10000:.1f}万"
    return f"{x:,}"


def fmt_sec(s: float) -> str:
    s = round(s)
    return f"{s // 60}分{s % 60}秒" if s >= 60 else f"{s}秒"


def fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def build_advice(a: Analysis, clf: Classifier) -> list[dict]:
    ref = a.ref
    out: list[dict] = []
    other = clf.other

    def examples(ps: list[Page], k: int = 3) -> list[dict]:
        return [{"name": p.name, "users": p.users} for p in ps[:k]]

    share = a.kpi.get("organic_share")
    search_heavy = share is not None and share >= 0.4

    # 本数が少ないのに 1 本あたりがよく読まれている種類 → 増やす
    for c in a.cats:
        if c.name == other or c.n < 3 or not ref["median"]:
            continue
        ratio = c.median / ref["median"]
        if ratio >= 1.3 and c.n <= ref["n"]:
            c.verdict = "増やす"
            extra = ""
            if c.evergreen and search_heavy:
                extra = (f"読者の{fmt_pct(share)}が検索から来るサイトなので、何年たっても調べられるこの種類は"
                         f"効果が長続きします。")
            out.append({
                "kind": "増やす", "priority": 60 + min(ratio, 5) * 6,
                "title": f"「{c.name}」の記事を増やす",
                "body": f"1本あたりの読者は{fmt_n(c.median)}人で、種類ごとの中央値の{ratio:.1f}倍です。"
                        f"それなのに本数は{c.n}本しかありません。{extra}"
                        f"まだ扱っていないテーマで同じ形の記事を作りましょう。",
                "examples": examples(c.top),
            })

    # 検索で長く読まれる種類で、すでに本数がある → 扱っていないテーマで続ける
    if search_heavy:
        for c in a.cats:
            if not c.evergreen or c.verdict or c.n < 3 or c.median < ref["median"]:
                continue
            c.verdict = "続ける"
            out.append({
                "kind": "検索向け", "priority": 55 + min(c.median / max(ref["median"], 1), 5) * 4,
                "title": f"「{c.name}」は、まだ扱っていないテーマで続ける",
                "body": f"1本あたり{fmt_n(c.median)}人と安定して読まれ、検索で長く読まれる種類です。"
                        f"まだ取り上げていないテーマや、新しく出てきたテーマを早めに記事にしましょう。"
                        f"毎年ある話題は、新しい記事を作るより同じ記事を更新するほうが検索での評価が積み上がります。",
                "examples": examples(c.top),
            })

    # 主言語以外で 1 本に読者が集中している → 同じ型の実用記事を増やす
    for l in a.langs:
        if l["code"] == clf.primary or l["users"] < a.kpi["users"] * 0.01 or not l["top"]:
            continue
        if l["top_share"] >= 0.4:
            top = l["top"][0]
            out.append({
                "kind": f"{l['label']}版", "priority": 70 + l["top_share"] * 20,
                "title": f"{l['label']}版は実用ガイドを増やす",
                "body": f"{l['label']}の読者の{fmt_pct(l['top_share'])}が「{top.name}」1本から来ています。"
                        f"海外の読者はニュースより「どう遊ぶか・どう買うか・どう参加するか」を探しています。"
                        f"日本語でよく読まれているガイドの翻訳から始めるのが効率的です。",
                "examples": examples(l["top"][1:4]),
            })

    # サイトの柱 (読者の大きな割合を占め、じっくり読まれている)
    for c in a.cats:
        if c.name == other:
            continue
        if c.share >= 0.15 and c.eng >= ref["eng"] and not c.verdict:
            c.verdict = "柱"
            episodes = sum(1 for p in c.top_all if re.search(r"第[0-9０-９一二三四五六七八九十]+[話回章]|[0-9０-９]+食目", p.name))
            series_tip = ("シリーズの1話目や目次ページに読者が集まりやすいので、新しいシリーズは1話目を重点的に告知しましょう。"
                          if episodes >= len(c.top_all) * 0.3 else "")
            out.append({
                "kind": "続ける", "priority": 50 + c.share * 100,
                "title": f"「{c.name}」はサイトの柱。ペースを落とさず続ける",
                "body": f"記事の読者の{fmt_pct(c.share)}を占め、平均{fmt_sec(c.eng)}とじっくり読まれています。"
                        f"{series_tip}",
                "examples": examples(c.top),
            })

    # 本数が多いのに 1 本あたりが少ない → まとめページに寄せる
    for c in a.cats:
        if c.name == other or not ref["median"]:
            continue
        if c.n >= ref["n"] * 1.5 and c.median <= ref["median"] * 0.7:
            c.verdict = c.verdict or "まとめる"
            hubs = [p for p in c.top_all if p.users >= c.median * 5 and re.search(r"まとめ|随時更新|情報", p.name)]
            tip = "特によく読まれているのは、情報を1ページに集めて更新し続けた記事です。" if hubs else ""
            out.append({
                "kind": "まとめる", "priority": 45 + min(c.n / max(ref["n"], 1), 6) * 3,
                "title": f"「{c.name}」は細かく分けず、1ページにまとめて更新する",
                "body": f"{c.n}本と本数が多いわりに、1本あたりの読者は{fmt_n(c.median)}人にとどまります。{tip}"
                        f"小さな告知を何本も出すより、話題ごとのまとめページを育てるほうが読まれます。",
                "examples": examples(hubs or c.top),
            })

    # 読者は来るのにすぐ離れる → 関連記事への導線
    for c in a.cats:
        if c.name == other or not ref["eng"] or c.verdict in ("まとめる",):
            continue
        if c.eng <= ref["eng"] * 0.6 and c.median >= ref["median"] * 0.8:
            c.verdict = c.verdict or "導線"
            out.append({
                "kind": "回遊", "priority": 40 + c.share * 50,
                "title": f"「{c.name}」に関連記事への導線を足す",
                "body": f"読者は集まっていますが、平均{fmt_sec(c.eng)}で離れています"
                        f"（種類ごとの中央値は{fmt_sec(ref['eng'])}）。"
                        f"記事の最後に、関連する連載やガイドへのリンクを置いて次の1本につなげましょう。",
                "examples": examples(c.top, 2),
            })

    # 種類の中で 1 本だけ突出している話題
    spikes = []
    for c in a.cats:
        if c.n < 10 or not c.top or not c.median:
            continue
        p = c.top[0]
        if p.users >= c.median * 8 and p.users >= a.kpi["users"] * 0.003:
            spikes.append((p, c))
    if spikes:
        spikes.sort(key=lambda t: t[0].users, reverse=True)
        p, c = spikes[0]
        out.append({
            "kind": "話題", "priority": 42,
            "title": "突出して読まれた話題は、単独記事や続報で追いかける",
            "body": f"たとえば「{p.name[:50]}」は、{c.name}の中央値の{p.users / c.median:.0f}倍読まれました。"
                    f"同じような話題が出たら、まとめ記事の中だけでなく単独の記事も出しましょう。",
            "examples": [{"name": q.name, "users": q.users} for q, _ in spikes[:3]],
        })

    # 前の期間との比較
    if a.prev_kpi:
        for c in a.cats:
            if c.name == other or not c.prev_users or c.share < 0.02:
                continue
            growth = c.users / c.prev_users - 1
            if growth >= 0.3:
                out.append({
                    "kind": "伸び", "priority": 55 + min(growth, 2) * 10,
                    "title": f"「{c.name}」が伸びている。今のうちに本数を増やす",
                    "body": f"前の期間より読者が{fmt_pct(growth)}増えました（{fmt_n(c.prev_users)}人 → {fmt_n(c.users)}人）。",
                    "examples": examples(c.top),
                })
        if a.falling:
            out.append({
                "kind": "リライト", "priority": 44,
                "title": "読者が減った定番記事を書き直す",
                "body": "前の期間によく読まれていたのに、今回は大きく減った記事があります。"
                        "情報を最新にする、タイトルを検索されやすい言葉に変える、などで回復が見込めます。",
                "examples": [{"name": p.name, "users": p.users, "before": before} for p, before in a.falling[:3]],
            })

    out.sort(key=lambda x: x["priority"], reverse=True)
    return out[:8]


def build_notes(a: Analysis, cur: Period) -> list[str]:
    notes = []
    if a.prev_kpi is None:
        notes.append("前の期間のデータがないため、伸びた記事・落ちた記事は出していません。"
                     "毎月データを保存しておくと、次の月から比較が表示されます。")
    s, e = a.meta.get("start"), a.meta.get("end")
    if s and e:
        days = (dt.date(int(e[:4]), int(e[4:6]), int(e[6:])) - dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))).days
        if days > 120:
            notes.append("集計期間が長いため、古い記事ほど読者数が多く出ています。最近の傾向を見るには1か月単位のデータを使ってください。")
    if a.kpi["key_events"] == 0:
        notes.append("キーイベント（成果）が0件です。GA4で「目次から次の話へ進んだ」などを成果として設定すると、"
                     "どの記事が熱心な読者を増やしているかまで分析できます。")
    notes.append(f"記事の種類はタイトルのキーワードで自動で分けています（config.json で変更できます）。"
                 f"読者が{a.min_users}人未満のページと、トップや一覧などのハブページは記事の集計から除いています。")
    return notes


# ---------------------------------------------------------------- HTML

CSS = """
:root{
  --bg:#f5f6f8;--surface:#ffffff;--ink:#16181d;--ink-2:#474c58;--muted:#767b88;
  --line:#e1e3e9;--bar:#2a78d6;--bar-2:#1baf7a;--track:#eef0f4;--accent:#1f5fbf;
  --chip:#e8effb;--chip-ink:#1d4f9c;--up:#006300;--down:#b42525;--warn-bg:#fff6e0;--warn-ink:#6b4a00;
  --shadow:0 1px 2px rgba(20,24,33,.06);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --bg:#0f1115;--surface:#171a20;--ink:#f1f2f5;--ink-2:#c4c8d1;--muted:#8d92a0;
    --line:#2a2e37;--bar:#3987e5;--bar-2:#199e70;--track:#222731;--accent:#7fb0f5;
    --chip:#1c2a44;--chip-ink:#a9c8f7;--up:#3fbf5a;--down:#f08080;--warn-bg:#2b2412;--warn-ink:#f1d18a;
    --shadow:none;
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#0f1115;--surface:#171a20;--ink:#f1f2f5;--ink-2:#c4c8d1;--muted:#8d92a0;
  --line:#2a2e37;--bar:#3987e5;--bar-2:#199e70;--track:#222731;--accent:#7fb0f5;
  --chip:#1c2a44;--chip-ink:#a9c8f7;--up:#3fbf5a;--down:#f08080;--warn-bg:#2b2412;--warn-ink:#f1d18a;
  --shadow:none;
}
body{background:var(--bg);color:var(--ink);margin:0;
  font-family:"BIZ UDPGothic","Hiragino Sans","Noto Sans JP",system-ui,sans-serif;font-size:15px;line-height:1.75}
.wrap{max-width:980px;margin:0 auto;padding-inline:20px;padding-block:32px 64px;display:flex;flex-direction:column;gap:40px}
h1,h2,h3{text-wrap:balance;margin:0;line-height:1.4}
h1{font-size:26px;font-weight:700}
h2{font-size:19px;font-weight:700;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
h2 small{font-size:13px;font-weight:400;color:var(--muted)}
p{margin:0}
.eyebrow{font-size:12px;letter-spacing:.08em;color:var(--muted)}
header{display:flex;flex-direction:column;gap:10px}
.period{color:var(--ink-2);font-size:14px}
.lead{font-size:16px;color:var(--ink);max-width:62ch}
section{display:flex;flex-direction:column;gap:16px}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:2px}
.kpi .label{font-size:13px;color:var(--ink-2)}
.kpi .value{font-size:28px;font-weight:700;line-height:1.3}
.kpi .delta{font-size:13px;color:var(--muted)}
.delta.up{color:var(--up)}.delta.down{color:var(--down)}
.advice{display:flex;flex-direction:column;gap:12px;counter-reset:adv}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px;
  display:grid;grid-template-columns:36px minmax(0,1fr);gap:4px 14px;box-shadow:var(--shadow)}
.card > *,.wrap > *,section > *{min-width:0}
.card .rank{grid-row:1 / span 3;width:32px;height:32px;border-radius:50%;background:var(--ink);color:var(--bg);
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:15px}
.card h3{font-size:17px;display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.chip{display:inline-block;font-size:12px;font-weight:700;padding:1px 9px;border-radius:999px;background:var(--chip);color:var(--chip-ink);letter-spacing:.04em;white-space:nowrap}
.card p{color:var(--ink-2);max-width:66ch}
.ex{list-style:none;margin:6px 0 0;padding:0;display:flex;flex-direction:column;gap:2px;font-size:13.5px}
.ex li{display:flex;gap:10px;align-items:baseline;min-width:0}
.ex .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink)}
.ex .n{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.more{padding:4px 4px 0;display:flex;flex-direction:column;gap:8px}
.more h3{font-size:14px;color:var(--ink-2)}
.more ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px}
.more li{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px;align-items:start;font-size:14px}
.more li p{color:var(--ink-2);font-size:13.5px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:8px 20px 14px}
.cat-head,.cat-row{display:grid;grid-template-columns:minmax(150px,1.2fr) 56px minmax(0,1.5fr) minmax(0,1.1fr);gap:14px;align-items:center}
.cat-head{font-size:12px;color:var(--muted);padding:10px 0 6px;border-bottom:1px solid var(--line)}
.cat-row{padding:9px 0;border-bottom:1px solid var(--line)}
.cat-row:last-child{border-bottom:0}
.cat-name{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-weight:700;font-size:14px}
.cat-n{font-variant-numeric:tabular-nums;color:var(--ink-2);text-align:right;font-size:14px}
.barcell{display:flex;align-items:center;gap:8px;min-width:0;container-type:inline-size}
.bar{height:12px;border-radius:0 4px 4px 0;background:var(--bar);min-width:2px;flex:none;width:calc(var(--w) * (100cqw - 76px))}
.bar.b2{background:var(--bar-2)}
.barcell .v{font-size:13px;color:var(--ink-2);font-variant-numeric:tabular-nums;white-space:nowrap}
.refline{font-size:12.5px;color:var(--muted)}
.chip.v-増やす{background:#dff3e4;color:#0b5a23}
.chip.v-まとめる{background:var(--warn-bg);color:var(--warn-ink)}
:root[data-theme="dark"] .chip.v-増やす{background:#133321;color:#8fdca6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .chip.v-増やす{background:#133321;color:#8fdca6}}
.two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}
.src-row{display:grid;grid-template-columns:minmax(0,15em) minmax(0,1fr);gap:12px;align-items:center;padding:7px 0;font-size:14px}
.src-row .l{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tbl-wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th{font-size:12px;color:var(--muted);font-weight:400;text-align:left;padding:10px 8px 6px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.title{min-width:260px}
.cat-tag{font-size:12px;color:var(--muted);white-space:nowrap}
.notes{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 20px}
.notes ul{margin:0;padding-left:1.2em;color:var(--ink-2);font-size:14px;display:flex;flex-direction:column;gap:6px}
footer{font-size:12.5px;color:var(--muted)}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);font-size:12.5px;padding:6px 10px;border-radius:6px;
  max-width:280px;line-height:1.5;z-index:10;opacity:0;transition:opacity .08s}
[data-tip]{cursor:default}
[data-tip]:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:720px){
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .two{grid-template-columns:minmax(0,1fr)}
  .cat-head{display:none}
  .cat-row{grid-template-columns:minmax(0,1fr) auto;gap:4px 10px}
  .cat-row .barcell{grid-column:1 / -1}
  .card{grid-template-columns:minmax(0,1fr)}
  .card .rank{grid-row:auto}
}
@media (prefers-reduced-motion:reduce){#tip{transition:none}}
"""

JS = """
(function(){
  var tip=document.getElementById('tip');
  function show(e){var t=e.currentTarget.getAttribute('data-tip');if(!t)return;tip.textContent=t;tip.style.opacity=1;move(e);}
  function move(e){var r=e.currentTarget.getBoundingClientRect();var x=(e.clientX||r.left+r.width/2)+14,y=(e.clientY||r.top)+14;
    var w=tip.offsetWidth,h=tip.offsetHeight;if(x+w>innerWidth-8)x=innerWidth-w-8;if(y+h>innerHeight-8)y=y-h-28;tip.style.left=x+'px';tip.style.top=y+'px';}
  function hide(){tip.style.opacity=0;}
  document.querySelectorAll('[data-tip]').forEach(function(el){
    el.addEventListener('mouseenter',show);el.addEventListener('mousemove',move);el.addEventListener('mouseleave',hide);
    el.addEventListener('focus',show);el.addEventListener('blur',hide);
  });
})();
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def _date(s: str | None) -> str:
    if not s or len(s) != 8:
        return "?"
    return f"{int(s[:4])}年{int(s[4:6])}月{int(s[6:])}日"


def _delta(cur: float | None, prev: float | None, pct_points: bool = False) -> str:
    if cur is None or prev is None or not prev:
        return ""
    if pct_points:
        d = (cur - prev) * 100
        cls = "up" if d > 0 else "down" if d < 0 else ""
        return f'<span class="delta {cls}">前の期間より {d:+.1f}ポイント</span>'
    d = cur / prev - 1
    cls = "up" if d > 0 else "down" if d < 0 else ""
    return f'<span class="delta {cls}">前の期間より {d * 100:+.0f}%</span>'


def render_html(a: Analysis, embed: bool = False) -> str:
    k, pk = a.kpi, a.prev_kpi or {}
    period = f"{_date(a.meta.get('start'))} 〜 {_date(a.meta.get('end'))}"
    cmp = ""
    if a.prev_meta:
        cmp = f"（比較: {_date(a.prev_meta.get('start'))} 〜 {_date(a.prev_meta.get('end'))}）"

    best = next((c for c in a.cats if c.n >= 3 and c.name != "その他"), None)
    lead_parts = [f"期間中の読者は{fmt_n(k['users'])}人"]
    if k.get("organic_share") is not None:
        lead_parts.append(f"そのうち{fmt_pct(k['organic_share'])}が検索から来ています")
    lead = "、".join(lead_parts) + "。"
    if best:
        lead += f"1本あたりいちばん読まれている記事の種類は「{_e(best.name)}」（中央値{fmt_n(best.median)}人）です。"
    if a.advice:
        lead += f"来月はまず『{_e(a.advice[0]['title'])}』から取りかかるのがおすすめです。"

    kpis = [
        ("読者数", fmt_n(k["users"]), _delta(k["users"], pk.get("users"))),
        ("表示回数", fmt_n(k["views"]), _delta(k["views"], pk.get("views"))),
        ("検索から来た割合", fmt_pct(k["organic_share"]) if k.get("organic_share") is not None else "—",
         _delta(k.get("organic_share"), pk.get("organic_share"), pct_points=True)),
        ("1人あたりの閲読時間", fmt_sec(k["eng"]), _delta(k["eng"], pk.get("eng"))),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><span class="label">{_e(l)}</span><span class="value">{v}</span>{d}</div>'
        for l, v, d in kpis)

    # アドバイス
    cards = []
    for i, ad in enumerate(a.advice, 1):
        exs = []
        for ex in ad.get("examples", []):
            n = f"{fmt_n(ex['users'])}人"
            if "before" in ex:
                n = f"{fmt_n(ex['before'])}人 → {fmt_n(ex['users'])}人"
            exs.append(f'<li><span class="t" title="{_e(ex["name"])}">{_e(ex["name"])}</span><span class="n">{n}</span></li>')
        ex_html = f'<ul class="ex" aria-label="参考になる記事">{"".join(exs)}</ul>' if exs else ""
        cards.append(
            f'<article class="card"><span class="rank" aria-label="優先度{i}">{i}</span>'
            f'<h3><span class="chip">{_e(ad["kind"])}</span>{_e(ad["title"])}</h3>'
            f'<p>{_e(ad["body"])}</p>{ex_html}</article>')
    main_cards, rest = cards[:5], a.advice[5:]
    advice_html = "".join(main_cards) or "<p>十分なデータがなく、アドバイスを出せませんでした。</p>"
    if rest:
        lis = "".join(f'<li><span class="chip">{_e(ad["kind"])}</span><div><strong>{_e(ad["title"])}</strong>'
                      f'<p>{_e(ad["body"])}</p></div></li>' for ad in rest)
        advice_html += f'<div class="more"><h3>そのほかの気づき</h3><ul>{lis}</ul></div>'

    # 記事の種類
    max_med = max((c.median for c in a.cats), default=1) or 1
    max_eng = max((c.eng for c in a.cats), default=1) or 1
    rows = []
    for c in a.cats:
        verdict = f'<span class="chip v-{_e(c.verdict)}">{_e(c.verdict)}</span>' if c.verdict else ""
        tops = " / ".join(p.name[:28] for p in c.top[:2])
        chg = ""
        if c.prev_users:
            chg = f"・前の期間比 {(c.users / c.prev_users - 1) * 100:+.0f}%"
        tip1 = f"{c.name}：1本あたりの読者（中央値）{c.median:,.0f}人・合計{c.users:,.0f}人（記事の読者の{c.share * 100:.1f}%）{chg}。よく読まれた記事: {tops}"
        tip2 = f"{c.name}：1人あたりの平均閲読時間 {fmt_sec(c.eng)}"
        w1 = c.median / max_med * 100
        w2 = c.eng / max_eng * 100
        rows.append(
            f'<div class="cat-row"><div class="cat-name">{_e(c.name)}{verdict}</div>'
            f'<div class="cat-n">{c.n}本</div>'
            f'<div class="barcell" tabindex="0" data-tip="{_e(tip1)}"><div class="bar" style="--w:{w1 / 100:.4f}"></div><span class="v">{fmt_n(c.median)}人</span></div>'
            f'<div class="barcell" tabindex="0" data-tip="{_e(tip2)}"><div class="bar b2" style="--w:{w2 / 100:.4f}"></div><span class="v">{fmt_sec(c.eng)}</span></div></div>')
    primary_label = next((l["label"] for l in a.langs if l["code"] == "ja"), "")
    cat_html = (
        f'<div class="panel"><div class="cat-head"><span>記事の種類</span><span style="text-align:right">本数</span>'
        f'<span>1本あたりの読者数（中央値）</span><span>1人あたりの閲読時間</span></div>{"".join(rows)}</div>'
        f'<p class="refline">種類ごとの中央値は、1本あたり{fmt_n(a.ref["median"])}人・本数{a.ref["n"]:.0f}本・閲読時間{fmt_sec(a.ref["eng"])}。'
        f'これと比べて「増やす」「まとめる」などの判定をしています。{_e(primary_label)}の記事のみ。</p>')

    # 流入元
    max_src = max((s["users"] for s in a.sources), default=1) or 1
    src_rows = "".join(
        f'<div class="src-row"><span class="l" title="{_e(s["medium"])}">{_e(s["label"])}</span>'
        f'<div class="barcell" tabindex="0" data-tip="{_e(s["label"])}：{s["users"]:,.0f}人（{s["share"] * 100:.1f}%）・閲読時間{fmt_sec(s["eng"])}">'
        f'<div class="bar" style="--w:{s["users"] / max_src:.4f}"></div><span class="v">{s["share"] * 100:.1f}%</span></div></div>'
        for s in a.sources[:7])
    src_html = f'<div class="panel">{src_rows or "<p>流入元のデータがありません。</p>"}</div>'

    # 言語
    lang_rows = "".join(
        f'<tr><td>{_e(l["label"])}</td><td class="num">{l["users"]:,.0f}</td><td class="num">{l["pages"]:,}</td>'
        f'<td class="title">{_e(l["top"][0].name) if l["top"] else ""}</td><td class="num">{l["top_share"] * 100:.0f}%</td></tr>'
        for l in a.langs)
    lang_html = (f'<div class="panel tbl-wrap"><table><thead><tr><th>言語</th><th class="num">記事の読者</th>'
                 f'<th class="num">記事数</th><th>いちばん読まれた記事</th><th class="num">その1本の割合</th></tr></thead>'
                 f'<tbody>{lang_rows}</tbody></table></div>')

    # 上位記事
    def top_row(i: int, p: Page) -> str:
        before = a.prev_users_by_title.get(p.title) if a.prev_kpi else None
        chg = ""
        if a.prev_kpi:
            chg = "新" if not before else f"{(p.users / before - 1) * 100:+.0f}%"
            chg = f'<td class="num">{chg}</td>'
        return (f'<tr><td class="num">{i}</td><td class="title">{_e(p.name)}<br><span class="cat-tag">{_e(p.category)}</span></td>'
                f'<td class="num">{p.users:,.0f}</td><td class="num">{fmt_sec(p.eng)}</td>{chg}</tr>')
    chg_head = '<th class="num">前の期間比</th>' if a.prev_kpi else ""
    top_html = (f'<div class="panel tbl-wrap"><table><thead><tr><th class="num">#</th><th>記事</th><th class="num">読者</th>'
                f'<th class="num">閲読時間</th>{chg_head}</tr></thead><tbody>'
                + "".join(top_row(i, p) for i, p in enumerate(a.top_articles, 1)) + "</tbody></table></div>")

    # 伸びた / 落ちた
    move_html = ""
    if a.prev_kpi:
        def mlist(items: list[tuple[Page, float]], empty: str) -> str:
            if not items:
                return f"<p class='refline'>{empty}</p>"
            lis = "".join(
                f'<li><span class="t" title="{_e(p.name)}">{_e(p.name)}</span>'
                f'<span class="n">{fmt_n(b)} → {fmt_n(p.users)}人</span></li>' for p, b in items)
            return f'<ul class="ex">{lis}</ul>'
        move_html = (
            '<section><h2>伸びた記事・落ちた記事<small>前の期間との比較</small></h2><div class="two">'
            f'<div class="panel"><h3 style="font-size:15px;padding-top:10px">伸びた記事</h3>{mlist(a.rising, "大きく伸びた記事はありません。")}</div>'
            f'<div class="panel"><h3 style="font-size:15px;padding-top:10px">落ちた記事（書き直し候補）</h3>{mlist(a.falling, "大きく落ちた記事はありません。")}</div>'
            '</div></section>')

    notes_html = "".join(f"<li>{_e(n)}</li>" for n in a.notes)
    t = dt.date.today()
    generated = f"{t.year}年{t.month}月{t.day}日"

    body = f"""
<div class="wrap">
<header>
  <span class="eyebrow">月次アクセスレポート</span>
  <h1>{_e(a.site)} 読まれ方と次の一手</h1>
  <span class="period">{period} {cmp}</span>
  <p class="lead">{lead}</p>
</header>
<section aria-label="主な数字"><div class="kpis">{kpi_html}</div></section>
<section><h2>次に書く記事のアドバイス<small>優先度の高い順</small></h2><div class="advice">{advice_html}</div></section>
<section><h2>記事の種類ごとの成績<small>1本あたりの読者数が多い順</small></h2>{cat_html}</section>
{move_html}
<section><h2>よく読まれた記事<small>トップ・一覧ページを除く</small></h2>{top_html}</section>
<section><h2>読者がどこから来たか<small>最初に訪れたときの経路</small></h2>{src_html}</section>
<section><h2>言語別</h2>{lang_html}</section>
<section class="notes" aria-label="このレポートについて"><h2 style="font-size:15px">このレポートについて</h2><ul>{notes_html}</ul></section>
<footer>{generated} 作成 ・ GA4 のエクスポートデータから自動で作成</footer>
</div>
<div id="tip" role="tooltip"></div>
"""
    title = f"{a.site} 月次レポート"
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700&display=swap">')
    head = f"<title>{_e(title)}</title>{fonts}<style>{CSS}</style>"
    if embed:
        return f"{head}\n{body}\n<script>{JS}</script>\n"
    return (f'<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">{head}</head>'
            f"<body>{body}<script>{JS}</script></body></html>\n")


# ---------------------------------------------------------------- CLI

def _prev_month_dir(month_dir: Path) -> Path | None:
    m = re.fullmatch(r"(\d{4})-(\d{2})", month_dir.name)
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    y, mo = (y - 1, 12) if mo == 1 else (y, mo - 1)
    d = month_dir.parent / f"{y:04d}-{mo:02d}"
    return d if (d / "pages.csv").exists() else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GA4 の CSV から記事アドバイス付きレポートを作る")
    ap.add_argument("month_dir", nargs="?", help="pages.csv と acquisition.csv が入ったフォルダ (例: data/2026-09)")
    ap.add_argument("--pages", help="ページとスクリーンのレポート CSV")
    ap.add_argument("--acquisition", help="ユーザー獲得のレポート CSV")
    ap.add_argument("--prev-pages", help="比較する前の期間のページ CSV")
    ap.add_argument("--prev-acquisition", help="比較する前の期間のユーザー獲得 CSV")
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--out", help="出力する HTML (既定: reports/<フォルダ名>.html)")
    ap.add_argument("--json", help="集計結果を JSON でも書き出す")
    ap.add_argument("--min-users", type=int, help="記事として数える最低ユーザー数 (既定: 自動)")
    ap.add_argument("--embed", action="store_true", help="<html> などの外枠を付けずに書き出す")
    args = ap.parse_args(argv)

    if args.month_dir:
        d = Path(args.month_dir)
        pages, acq = d / "pages.csv", d / "acquisition.csv"
        prev_dir = _prev_month_dir(d)
        prev_pages = prev_dir / "pages.csv" if prev_dir else None
        prev_acq = prev_dir / "acquisition.csv" if prev_dir else None
        out = Path(args.out) if args.out else HERE / "reports" / f"{d.name}.html"
    elif args.pages:
        pages = Path(args.pages)
        acq = Path(args.acquisition) if args.acquisition else None
        prev_pages = Path(args.prev_pages) if args.prev_pages else None
        prev_acq = Path(args.prev_acquisition) if args.prev_acquisition else None
        out = Path(args.out) if args.out else HERE / "reports" / "report.html"
    else:
        ap.error("フォルダか --pages を指定してください")
        return 2

    if not pages.exists():
        print(f"見つかりません: {pages}", file=sys.stderr)
        return 1
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    clf = Classifier(config)
    cur = load_period(pages, acq, clf)
    prev = load_period(prev_pages, prev_acq, clf) if prev_pages and prev_pages.exists() else None
    a = analyze(cur, prev, clf, args.min_users)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(a, embed=args.embed), encoding="utf-8")
    print(f"レポートを書き出しました: {out}")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "meta": a.meta, "kpi": a.kpi, "prev_kpi": a.prev_kpi, "advice": a.advice,
            "categories": [{"name": c.name, "n": c.n, "users": c.users, "median": c.median,
                            "eng": c.eng, "share": c.share, "verdict": c.verdict} for c in a.cats],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
