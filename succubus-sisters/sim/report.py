# sim/result.json から、バランス調査のレポート（balance.html）と CSV を作る
#   python3 sim/report.py
import json, math, csv, collections, html, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
EYEBROW = '260717基本ルール・120枚Ver ＋ 能力調整案 第2版（ミロク・ジャスイ・ボタン・ツバキ・クルル）・3〜6人'
ROOT = os.path.dirname(HERE)
d = json.load(open(os.path.join(HERE, 'result.json')))
games = d['games']
COUNTS = sorted({g['n'] for g in games})
N = len(games)
esc = html.escape

# ---------------------------------------------------------------- サキュバス能力
CHAR_TIERS = [('S', 20), ('A', 10), ('B', 5), ('C', 2), ('D', -999)]   # 能力なしとの勝率差（ポイント）
by = collections.defaultdict(list)
for g in games: by[g['sc']].append(g)
info = {c['key']: c for c in d['chars']}
rate = lambda gs, f: sum(1 for g in gs if f(g)) / len(gs) if gs else 0
ctl = rate(by['control'], lambda g: g['reason'] == 'last')
chars = []
for key, gs in by.items():
    n = len(gs)
    w = rate(gs, lambda g: g['reason'] == 'last')
    man = [g for g in gs if g['manifested']]
    row = dict(key=key, name=info[key]['name'], text=info[key]['text'], common=info[key]['common'], n=n,
               win=w, lose=rate(gs, lambda g: g['reason'] == 'succubus'), draw=rate(gs, lambda g: g['reason'] in ('deck', 'none')),
               ci=1.96 * math.sqrt(w * (1 - w) / n), diff=w - ctl, manifest=len(man) / n,
               win_man=rate(man, lambda g: g['reason'] == 'last'), vp=sum(g['vp'] for g in gs) / n,
               by_n={k: rate([g for g in gs if g['n'] == k], lambda g: g['reason'] == 'last') for k in COUNTS})
    row['tier'] = '基準' if key == 'control' else next(t for t, th in CHAR_TIERS if row['diff'] * 100 >= th)
    chars.append(row)
chars.sort(key=lambda r: -r['win'])

# ---------------------------------------------------------------- カード
CARD_TIERS = [('S', 18), ('A', 13), ('B', 8), ('C', 4), ('D', -999)]   # 1回あたりのHP価値
EFFECT_ONLY = {'ソーサリーリング', 'ドキドキなみだ', '夜魔のホウキ', '誓いの祈り', '寄進の行い', '許しの告解', '秘密の懺悔', 'にじのカーテン'}
cards = []
for c in d['cards']:
    u = max(1, c['uses'])
    gain = c['dealt'] + c['prevented'] + c['heal'] + c['counter'] + c['reflect']
    row = dict(c)
    row.update(per100=100 * c['uses'] / N, value=(gain - c['cost']) / u, dealt_u=c['dealt'] / u, prev_u=c['prevented'] / u,
               heal_u=c['heal'] / u, cost_u=c['cost'] / u, other_u=(c['counter'] + c['reflect']) / u,
               kill_u=c['kills'] / u, lift=(c['winSum'] - c['expSum']) / u)
    row['effect'] = c['name'] in EFFECT_ONLY
    row['tier'] = '効果' if row['effect'] else next(t for t, th in CARD_TIERS if row['value'] >= th)
    cards.append(row)
cards.sort(key=lambda r: (r['effect'], -r['value']))

# ---------------------------------------------------------------- CSV
with open(os.path.join(HERE, 'chars.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Tier', 'キャラ', '試合数', 'サキュバス陣営の勝率', '能力なしとの差', '95%信頼区間±', '顕現率', '顕現したときの勝率', 'サキュバスの平均勝利点'] + [f'{k}人戦の勝率' for k in COUNTS])
    for r in chars:
        w.writerow([r['tier'], r['name'], r['n'], f"{r['win']:.3f}", f"{r['diff']:+.3f}", f"{r['ci']:.3f}", f"{r['manifest']:.3f}", f"{r['win_man']:.3f}", f"{r['vp']:+.2f}"] + [f"{r['by_n'][k]:.3f}" for k in COUNTS])
with open(os.path.join(HERE, 'cards.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Tier', 'カード', '種類', 'ID', '100戦あたり使用回数', '1回あたりHP価値', '与ダメージ/回', '軽減/回', '回復/回', '反撃・反射/回', 'HPコスト/回', '撃破/回', '使った側の勝率差（参考）'])
    for r in cards:
        w.writerow([r['tier'], r['name'], r['marks'], ' '.join(map(str, r['ids'])), f"{r['per100']:.1f}", f"{r['value']:.1f}", f"{r['dealt_u']:.1f}", f"{r['prev_u']:.1f}",
                    f"{r['heal_u']:.1f}", f"{r['other_u']:.1f}", f"{r['cost_u']:.1f}", f"{r['kill_u']:.2f}", f"{r['lift']:+.3f}"])

# ---------------------------------------------------------------- HTML
FACE = lambda key: f'img/face/{key}_oni.jpg' if key != 'control' else ''
pct = lambda x: f'{x * 100:.1f}%'
pt = lambda x: f'{x * 100:+.1f}'

def face(key, name, size=''):
    if key == 'control': return f'<span class="face ctl {size}" aria-hidden="true">無</span>'
    return f'<img class="face {size}" src="{FACE(key)}" alt="" loading="lazy">'

# Tier表（キャラ）
tier_rows = ''
for t, label in [('S', '能力なしより +20pt以上'), ('A', '+10〜20pt'), ('B', '+5〜10pt'), ('C', '+2〜5pt'), ('D', '+2pt未満（能力なしと差がない・下回る）')]:
    members = [r for r in chars if r['tier'] == t]
    items = ''.join(f'<li class="tchar" data-tip="{esc(r["name"])}｜勝率 {pct(r["win"])}（能力なし比 {pt(r["diff"])}pt）">{face(r["key"], r["name"])}<span><b>{esc(r["name"])}</b><em>{pct(r["win"])}　{pt(r["diff"])}pt</em></span></li>' for r in members) or '<li class="none">該当なし</li>'
    tier_rows += f'<div class="trow"><div class="tlabel t{t}"><b>{t}</b><span>{label}</span></div><ul class="titems">{items}</ul></div>'

# 勝率チャート（点と95%区間）
W, rowh, left, right, top = 660, 30, 150, 90, 28
xs = lambda v: left + (W - left - right) * v / 0.7
H = top + rowh * len(chars) + 26
svg = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="サキュバス能力ごとのサキュバス陣営勝率と95%信頼区間">']
for v in [0, .1, .2, .3, .4, .5, .6, .7]:
    x = xs(v); svg.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 8}" y2="{H - 22}" class="grid"/><text x="{x:.1f}" y="{H - 6}" class="axis" text-anchor="middle">{int(v * 100)}%</text>')
cx = xs(ctl)
svg.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{top - 14}" y2="{H - 22}" class="ref"/><text x="{cx + 4:.1f}" y="{top - 16}" class="reflabel">能力なし {pct(ctl)}</text>')
for i, r in enumerate(chars):
    y = top + rowh * i + rowh / 2
    cls = 'ctl' if r['key'] == 'control' else 'dot'
    tip = f'{r["name"]}｜勝率 {pct(r["win"])}（±{r["ci"] * 100:.1f}）｜能力なし比 {pt(r["diff"])}pt｜顕現率 {pct(r["manifest"])}｜試合数 {r["n"]}'
    svg.append(f'<g class="hit" data-tip="{esc(tip)}"><rect x="0" y="{y - rowh / 2:.1f}" width="{W}" height="{rowh}" class="band"/>'
               f'<text x="{left - 10}" y="{y + 4:.1f}" class="label" text-anchor="end">{esc(r["name"])}</text>'
               f'<line x1="{xs(r["win"] - r["ci"]):.1f}" x2="{xs(r["win"] + r["ci"]):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="ci {cls}"/>'
               f'<circle cx="{xs(r["win"]):.1f}" cy="{y:.1f}" r="6" class="{cls}"/>'
               f'<text x="{xs(r["win"] + r["ci"]) + 8:.1f}" y="{y + 4:.1f}" class="val">{pct(r["win"])}</text></g>')
svg.append('</svg>')
chart = ''.join(svg)

# 人数別の表
def heat(v):
    a = min(1, max(0, v / 0.75))
    return f'style="--h:{a:.2f}"'
count_rows = ''.join(
    f'<tr><td class="nm">{face(r["key"], r["name"], "sm")}{esc(r["name"])}</td><td><span class="tier t{r["tier"] if r["tier"] != "基準" else "X"}">{r["tier"]}</span></td>'
    + ''.join(f'<td class="num heat" {heat(r["by_n"][k])}>{r["by_n"][k] * 100:.0f}%</td>' for k in COUNTS)
    + f'<td class="num">{pct(r["manifest"])}</td><td class="num">{pct(r["win_man"])}</td><td class="num">{r["vp"]:+.2f}</td></tr>' for r in chars)
avg_by_n = {k: rate([g for g in games if g['n'] == k], lambda g: g['reason'] == 'last') for k in COUNTS}

# カード表
def card_row(r):
    t = r['tier']
    ids = ' '.join(map(str, r['ids']))
    tcls = 'tE' if t == '効果' else f't{t}'
    valtxt = '—' if r['effect'] else '{:.1f}'.format(r['value'])
    dash = lambda v, fmt='{:.1f}': '—' if abs(v) < 0.05 else fmt.format(v)
    return (f'<tr data-tier="{t}"><td><span class="tier {tcls}">{t}</span></td>'
            f'<td class="nm"><button type="button" class="cardlink" data-img="img/cards/{r["ids"][0]:03d}.jpg">{esc(r["name"])}</button></td><td>{esc(r["marks"])}</td><td class="ids">{ids}</td>'
            f'<td class="num" data-v="{r["per100"]:.3f}">{r["per100"]:.0f}</td>'
            f'<td class="num strong" data-v="{-99 if r["effect"] else r["value"]:.3f}">{valtxt}</td>'
            f'<td class="num" data-v="{r["dealt_u"]:.3f}">{dash(r["dealt_u"])}</td><td class="num" data-v="{r["prev_u"]:.3f}">{dash(r["prev_u"])}</td>'
            f'<td class="num" data-v="{r["heal_u"]:.3f}">{dash(r["heal_u"])}</td><td class="num" data-v="{r["other_u"]:.3f}">{dash(r["other_u"])}</td>'
            f'<td class="num" data-v="{r["cost_u"]:.3f}">{dash(r["cost_u"])}</td><td class="num" data-v="{r["kill_u"]:.3f}">{dash(r["kill_u"], "{:.2f}")}</td>'
            f'<td class="num" data-v="{r["lift"]:.4f}">{r["lift"] * 100:+.1f}</td></tr>')
card_rows = ''.join(card_row(r) for r in cards)
tier_count = collections.Counter(r['tier'] for r in cards)

top = chars[0]
byname = {r['key']: r for r in chars}
tiers_of = lambda t: [r for r in chars if r['tier'] == t]
prev_path = os.path.join(HERE, 'prev_summary.json')
prev = json.load(open(prev_path)) if os.path.exists(prev_path) else None
def win_in(key, counts):
    gs = [g for g in by[key] if g['n'] in counts]
    return rate(gs, lambda g: g['reason'] == 'last'), len(gs)
compare_html = ''
notes = []
if prev:
    cs = prev['counts']
    CHANGED = prev.get('changed', [])
    rows = ''
    for r in sorted(chars, key=lambda r: (r['key'] not in CHANGED, -r['win'])):
        if r['key'] not in prev['win']: continue
        now_w, n_now = win_in(r['key'], cs)
        dlt = now_w - prev['win'][r['key']]
        mark = '<span class="tier tA">変更</span>' if r['key'] in CHANGED else ''
        rows += (f'<tr><td class="nm">{face(r["key"], r["name"], "sm")}{esc(r["name"])}</td><td>{mark}</td>'
                 f'<td class="num">{pct(prev["win"][r["key"]])}</td><td class="num">{pct(now_w)}</td><td class="num strong">{dlt * 100:+.1f}</td></tr>')
    compare_html = f"""<section>
  <h2>前回との比較</h2>
  <p>{esc(prev['label'])}と比べた（{'・'.join(f'{c}人' for c in cs)}戦）。{esc(prev.get('note', ''))}</p>
  <div class="tbl"><table><thead><tr><th>キャラ</th><th></th><th class="num">前回</th><th class="num">今回</th><th class="num">差（pt）</th></tr></thead><tbody>{rows}</tbody></table></div>
</section>"""
    if CHANGED:
        moves = [(byname[k], prev['win'][k], win_in(k, cs)[0]) for k in CHANGED if k in byname and k in prev['win']]
        notes.append(('変更したキャラの勝率', '、'.join(f"{esc(r['name'])} {pct(a)} → {pct(b2)}（{(b2 - a) * 100:+.1f}pt）" for r, a, b2 in moves) + '。'))
upper = tiers_of('S') + tiers_of('A')
lower = tiers_of('D')
bl = d['baseline']
gap = bl['sister'] - bl['succubus']
notes.insert(0, ('陣営の勝率はほぼ五分' if abs(gap) < 0.05 else ('シスター陣営が有利' if gap > 0 else 'サキュバス陣営が有利'),
                 f"サキュバス陣営 {pct(bl['succubus'])}・シスター陣営 {pct(bl['sister'])}（全人数・全キャラ平均）。"))
if upper: notes.append(('上位は' + '・'.join(esc(r['name']) for r in upper), '、'.join(f"{esc(r['name'])} {pt(r['diff'])}pt" for r in upper) + '（能力なしとの差）。'))
if lower: notes.append(('下位は' + '・'.join(esc(r['name']) for r in lower), '、'.join(f"{esc(r['name'])} {pt(r['diff'])}pt" for r in lower) + '。能力なしとほぼ同じ。'))
best_n = max(COUNTS, key=lambda k: avg_by_n[k]); worst_n = min(COUNTS, key=lambda k: avg_by_n[k])
notes.append(('人数ごとの有利不利', '全キャラ平均のサキュバス陣営勝率は ' + '・'.join(f"{k}人 {pct(avg_by_n[k])}" for k in COUNTS) + f"。サキュバス側が最も有利なのは{best_n}人戦、最も不利なのは{worst_n}人戦。" + ('4人戦はシスター2人に対してサキュバス＋堕天使の2対2になる。' if best_n == 4 else '')))
findings = ''.join(f'<li><b>{t}</b>{body}</li>' for t, body in notes)
reasons = collections.Counter(g['reason'] for g in games)
avg_rounds = sum(g['rounds'] for g in games) / N
now = datetime.date.today().isoformat()
b = d['baseline']

page = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>サキュバスシスターズ バランス調査</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap">
<style>
:root{{
  --bg:#faf6f8; --surface:#ffffff; --ink:#1f1522; --ink2:#4f4252; --muted:#7a6c7d; --line:#eadfe7; --band:#f6eef3;
  --accent:#b8306a; --accent-soft:#f6dbe7; --ref:#8b8290;
  --tS:#8f1d4f; --tA:#b8306a; --tB:#d9699a; --tC:#eba9c6; --tD:#d9d2d8; --tX:#ffffff; --tE:#e9e3ea;
  --onS:#ffffff; --onA:#ffffff; --onB:#1f1522; --onC:#1f1522; --onD:#1f1522; --onE:#4f4252;
  --heat:184,48,106;
  --display:"Dela Gothic One","Hiragino Sans","Yu Gothic",sans-serif;
  --body:"Zen Kaku Gothic New","Hiragino Sans","Yu Gothic",system-ui,sans-serif;
}}
@media (prefers-color-scheme: dark){{ :root:not([data-theme="light"]){{
  color-scheme:dark; --bg:#141015; --surface:#1d171f; --ink:#f6ecf2; --ink2:#d3c4cf; --muted:#a896a6; --line:#382c3a; --band:#241c26;
  --accent:#ff74aa; --accent-soft:#44202f; --ref:#a39ba8;
  --tS:#ff74aa; --tA:#e0558f; --tB:#b04a78; --tC:#7a3a57; --tD:#3a323c; --tX:#1d171f; --tE:#2b242d;
  --onS:#1f0a14; --onA:#1f0a14; --onB:#ffffff; --onC:#ffffff; --onD:#d3c4cf; --onE:#d3c4cf; --heat:255,116,170;
}}}}
:root[data-theme="dark"]{{
  color-scheme:dark; --bg:#141015; --surface:#1d171f; --ink:#f6ecf2; --ink2:#d3c4cf; --muted:#a896a6; --line:#382c3a; --band:#241c26;
  --accent:#ff74aa; --accent-soft:#44202f; --ref:#a39ba8;
  --tS:#ff74aa; --tA:#e0558f; --tB:#b04a78; --tC:#7a3a57; --tD:#3a323c; --tX:#1d171f; --tE:#2b242d;
  --onS:#1f0a14; --onA:#1f0a14; --onB:#ffffff; --onC:#ffffff; --onD:#d3c4cf; --onE:#d3c4cf; --heat:255,116,170;
}}
*{{box-sizing:border-box}}
[hidden]{{display:none!important}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.7}}
main{{max-width:1040px;margin:0 auto;padding:28px 16px 64px;display:flex;flex-direction:column;gap:40px}}
header .eyebrow{{font-size:12px;letter-spacing:.25em;color:var(--accent);font-weight:700}}
h1{{font-family:var(--display);font-weight:400;font-size:clamp(28px,6vw,44px);line-height:1.15;margin:6px 0 10px;text-wrap:balance}}
h2{{font-family:var(--display);font-weight:400;font-size:24px;margin:0 0 6px;text-wrap:balance}}
h3{{font-size:15px;margin:18px 0 8px}}
p{{margin:0 0 10px;max-width:68ch;color:var(--ink2)}}
.lede{{font-size:16px;color:var(--ink2)}}
.meta{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin-top:12px;font-variant-numeric:tabular-nums}}
.meta b{{color:var(--ink);font-size:18px;font-variant-numeric:tabular-nums;display:block}}
.findings{{margin:0;padding:0;list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}}
.findings li{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:14px;color:var(--ink2)}}
.findings li b{{color:var(--ink);display:block;font-size:15px;margin-bottom:2px}}
section{{display:flex;flex-direction:column;gap:12px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px}}
/* tier list */
.tiers{{display:flex;flex-direction:column;gap:6px}}
.trow{{display:grid;grid-template-columns:120px 1fr;gap:8px;align-items:stretch}}
.tlabel{{border-radius:10px;padding:8px 10px;display:flex;flex-direction:column;justify-content:center;background:var(--tX)}}
.tlabel b{{font-family:var(--display);font-weight:400;font-size:28px;line-height:1}}
.tlabel span{{font-size:11px;line-height:1.4;margin-top:4px}}
.tS{{background:var(--tS);color:var(--onS)}} .tA{{background:var(--tA);color:var(--onA)}} .tB{{background:var(--tB);color:var(--onB)}}
.tC{{background:var(--tC);color:var(--onC)}} .tD{{background:var(--tD);color:var(--onD)}} .tE{{background:var(--tE);color:var(--onE)}}
.tX{{background:var(--surface);color:var(--muted);border:1px solid var(--line)}}
.titems{{list-style:none;margin:0;padding:8px;display:flex;flex-wrap:wrap;gap:8px;background:var(--surface);border:1px solid var(--line);border-radius:10px;min-height:64px}}
.tchar{{display:flex;align-items:center;gap:8px;padding:4px 10px 4px 4px;border-radius:10px;background:var(--band)}}
.tchar b{{display:block;font-size:13px;line-height:1.3}}
.tchar em{{font-style:normal;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}}
.titems .none{{color:var(--muted);font-size:13px;align-self:center;padding-left:6px}}
.face{{width:44px;height:44px;border-radius:9px;object-fit:cover;flex:none;display:inline-grid;place-items:center;background:var(--band);color:var(--muted);font-family:var(--display)}}
.face.sm{{width:26px;height:26px;border-radius:6px;vertical-align:middle;margin-right:8px;font-size:12px}}
/* chart */
.chartwrap{{overflow-x:auto}}
.chart{{width:100%;min-width:520px;height:auto;display:block}}
.chart .grid{{stroke:var(--line);stroke-width:1}}
.chart .axis{{fill:var(--muted);font-size:11px;font-family:var(--body)}}
.chart .label{{fill:var(--ink);font-size:13px;font-family:var(--body)}}
.chart .val{{fill:var(--ink2);font-size:12px;font-family:var(--body);font-variant-numeric:tabular-nums}}
.chart .ref{{stroke:var(--ref);stroke-width:2;stroke-dasharray:4 4}}
.chart .reflabel{{fill:var(--muted);font-size:11px;font-family:var(--body)}}
.chart .ci{{stroke-width:2;stroke-linecap:round}}
.chart .ci.dot{{stroke:var(--accent)}} .chart .ci.ctl{{stroke:var(--ref)}}
.chart circle.dot{{fill:var(--accent);stroke:var(--surface);stroke-width:2}}
.chart circle.ctl{{fill:var(--ref);stroke:var(--surface);stroke-width:2}}
.chart .band{{fill:transparent}}
.chart .hit:hover .band{{fill:var(--band)}}
/* tables */
.tbl{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface)}}
table{{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}}
th,td{{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}
th{{font-weight:700;color:var(--muted);font-size:12px;background:var(--surface);position:sticky;top:0}}
th.sort{{cursor:pointer;user-select:none}} th.sort:hover{{color:var(--ink)}}
th.sort[aria-sort="descending"]::after{{content:" ▼"}} th.sort[aria-sort="ascending"]::after{{content:" ▲"}}
td.num,th.num{{text-align:right}}
td.strong{{font-weight:700;color:var(--ink)}}
td.nm{{font-weight:700}}
td.ids{{color:var(--muted);font-size:12px;white-space:normal;min-width:4em}}
td.heat{{background:rgba(var(--heat),calc(var(--h) * .55))}}
tbody tr:hover td{{background:var(--band)}}
.tier{{display:inline-block;min-width:34px;text-align:center;border-radius:6px;padding:0 6px;font-weight:700;font-size:12px}}
.cardlink{{font:inherit;font-weight:700;color:var(--ink);background:none;border:0;padding:0;cursor:zoom-in;text-decoration:underline dotted;text-underline-offset:3px}}
.filters{{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--muted)}}
.filters button{{font:inherit;border:1px solid var(--line);background:var(--surface);color:var(--ink2);border-radius:999px;padding:3px 12px;cursor:pointer}}
.filters button[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:var(--surface)}}
.note{{font-size:13px;color:var(--muted)}}
ul.plain{{margin:0;padding-left:1.2em;color:var(--ink2);max-width:72ch}} ul.plain li{{margin-bottom:6px}}
#tip{{position:fixed;z-index:50;pointer-events:none;background:var(--ink);color:var(--bg);font-size:12px;padding:6px 10px;border-radius:8px;max-width:320px;line-height:1.5}}
#zoom{{position:fixed;inset:0;z-index:60;background:rgba(10,6,12,.72);display:grid;place-items:center;padding:16px}}
#zoom img{{max-height:86vh;max-width:100%;border-radius:12px;background:#fff}}
@media (max-width:640px){{ .trow{{grid-template-columns:1fr}} .tlabel{{flex-direction:row;align-items:center;gap:10px}} .tlabel span{{margin:0}} }}
</style>
</head>
<body>
<main>
<header>
  <div class="eyebrow">{esc(EYEBROW)}</div>
  <h1>サキュバスシスターズ バランス調査</h1>
  <p class="lede">デジタル版のCPU同士で {N:,} 戦を回し、サキュバス能力ごとの勝率と、カード1枚ごとの働きを集計した。バランス調整の叩き台として使うための資料。</p>
  <div class="meta">
    <span><b>{N:,}</b>総試合数</span>
    <span><b>{d['per']:,}戦</b>キャラ×人数ごと</span>
    <span><b>{pct(b['succubus'])}</b>サキュバス陣営の平均勝率</span>
    <span><b>{pct(b['sister'])}</b>シスター陣営の平均勝率</span>
    <span><b>{avg_rounds:.1f}巡</b>1試合の平均</span>
  </div>
</header>

<section>
  <h2>要点</h2>
  <ul class="findings">{findings}</ul>
</section>

<section>
  <h2>サキュバス能力 Tier表</h2>
  <p>そのキャラがサキュバスになった試合で、サキュバス陣営が勝った割合。比較用に、共通能力（手札上限＋1・《吸収》）だけの「能力なし」も同じ条件で回した。Tierは能力なしとの差で決めている。</p>
  <div class="tiers">{tier_rows}</div>
  <p class="note">試合数は各キャラ {len(by['control']):,} 戦。勝率の誤差（95%信頼区間）は約±{chars[0]['ci'] * 100:.1f}pt、能力なしとの差の誤差はその約1.4倍。隣り合うキャラの差が数pt以内なら、順位は入れ替わりうる。</p>
</section>

{compare_html}

<section>
  <h2>勝率と誤差の幅</h2>
  <p>点がサキュバス陣営の勝率、横線が95%信頼区間。点線が能力なし。行にカーソルを合わせると詳細が出る。</p>
  <div class="card chartwrap">{chart}</div>
</section>

<section>
  <h2>人数別の勝率</h2>
  <p>人数ごとに各 {d['per']:,} 戦。3人戦は堕天使なし、4〜6人戦は堕天使が1人。「顕現したときの勝率」は、サキュバスが顕現できた試合だけの勝率。</p>
  <div class="tbl"><table>
    <thead><tr><th>キャラ</th><th>Tier</th>{''.join(f'<th class="num">{k}人</th>' for k in COUNTS)}<th class="num">顕現率</th><th class="num">顕現時の勝率</th><th class="num">平均勝利点</th></tr></thead>
    <tbody>{count_rows}</tbody>
  </table></div>
</section>

<section>
  <h2>カードの強さ</h2>
  <p><b>1回あたりHP価値</b>＝そのカードを1回使ったときに動いたHPの量。与えたダメージ、防いだダメージ、回復量、反撃・反射で与えたダメージを足し、☆魔法で払ったHPを引いた。与ダメージ・軽減・回復はどれも「HP1点＝1」として同じ重さで数えている。</p>
  <p>Tier：S 18以上／A 13〜18／B 8〜13／C 4〜8／D 4未満。HPを動かさないカード（引き直し・交換・神託確認など）は「効果」として別枠。カード名をタップすると実物カードを表示する。見出しをタップすると並べ替えられる。</p>
  <div class="filters" role="group" aria-label="Tierで絞り込む"><span>絞り込み</span>{''.join(f'<button type="button" data-filter="{t}" aria-pressed="false">{t}（{tier_count.get(t, 0)}）</button>' for t in ['S', 'A', 'B', 'C', 'D', '効果'])}<button type="button" data-filter="" aria-pressed="true">すべて</button></div>
  <div class="tbl"><table id="cards">
    <thead><tr><th>Tier</th><th>カード</th><th>種類</th><th>ID</th>
      <th class="num sort" data-col="4">使用/100戦</th><th class="num sort" data-col="5" aria-sort="descending">HP価値/回</th>
      <th class="num sort" data-col="6">与ダメ/回</th><th class="num sort" data-col="7">軽減/回</th><th class="num sort" data-col="8">回復/回</th>
      <th class="num sort" data-col="9">反撃・反射/回</th><th class="num sort" data-col="10">HPコスト/回</th><th class="num sort" data-col="11">撃破/回</th><th class="num sort" data-col="12">勝率差（参考）</th></tr></thead>
    <tbody>{card_rows}</tbody>
  </table></div>
</section>

<section>
  <h2>読み方と限界</h2>
  <ul class="plain">
    <li>すべてCPU同士の結果。CPUはカードの使い方や能力の使いどころが人間より単純なので、「人が使えばもっと強い」カード・能力は低めに出る（例：寄進の行い、秘密の懺悔、ジャスイ・紅刃の能力）。</li>
    <li>ルールの解釈はデジタル版の実装どおり（☆魔法は場に残る、反撃は防御後のダメージ、など。ゲーム内の「ルール」画面を参照）。解釈が変わると結果も変わる。</li>
    <li>「勝率差（参考）」は、そのカードを使ったプレイヤーの陣営が、役職の平均よりどれだけ勝ったか。使う場面の有利不利（回復は負けている側が使う、♥カードは顕現したサキュバスが使う、など）がそのまま混ざるので、強さの指標ではなく傾向の参考。</li>
    <li>同じ名前のカードは合算している。♥カードは上の面と下の面を別々に数えた。</li>
    <li>集計中に、昇天弓で倒された直後に《反撃》の相手がいなくなるとゲームが止まる不具合が見つかり、修正してから集計し直した。</li>
    <li>再集計：<code>node sim/run.js 1000</code> → <code>python3 sim/report.py</code>。CSV（sim/chars.csv・sim/cards.csv）も同時に出力する。</li>
  </ul>
  <p class="note">集計日 {now}</p>
</section>
</main>
<div id="tip" hidden></div>
<div id="zoom" hidden><img alt=""></div>
<script>
(() => {{
  const tip = document.getElementById('tip');
  document.addEventListener('mousemove', e => {{
    const t = e.target.closest('[data-tip]');
    if (!t){{ tip.hidden = true; return; }}
    tip.textContent = t.dataset.tip; tip.hidden = false;
    const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8), y = e.clientY + 16;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }});
  const tbody = document.querySelector('#cards tbody');
  document.querySelectorAll('#cards th.sort').forEach(th => th.addEventListener('click', () => {{
    const col = +th.dataset.col, desc = th.getAttribute('aria-sort') !== 'descending';
    document.querySelectorAll('#cards th.sort').forEach(h => h.removeAttribute('aria-sort'));
    th.setAttribute('aria-sort', desc ? 'descending' : 'ascending');
    const rows = [...tbody.rows].sort((a, b) => (+b.cells[col].dataset.v - +a.cells[col].dataset.v) * (desc ? 1 : -1));
    rows.forEach(r => tbody.appendChild(r));
  }}));
  document.querySelectorAll('[data-filter]').forEach(bt => bt.addEventListener('click', () => {{
    document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', b === bt));
    [...tbody.rows].forEach(r => r.hidden = !!bt.dataset.filter && r.dataset.tier !== bt.dataset.filter);
  }}));
  const zoom = document.getElementById('zoom');
  document.addEventListener('click', e => {{
    const c = e.target.closest('.cardlink');
    if (c){{ zoom.querySelector('img').src = c.dataset.img; zoom.hidden = false; return; }}
    if (e.target.closest('#zoom')) zoom.hidden = true;
  }});
}})();
</script>
</body>
</html>
'''
open(os.path.join(ROOT, 'balance.html'), 'w').write(page)
print('chars', [(r['name'], r['tier']) for r in chars])
print('card tiers', dict(tier_count))
