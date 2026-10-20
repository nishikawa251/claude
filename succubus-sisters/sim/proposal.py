# カードの強化案を、差し替え前後のシミュレーション結果と並べてページにする
#   python3 sim/proposal.py 差し替えJSON 差し替え前の結果 差し替え後の結果 出力HTML
import json, sys, csv, io, re, os, html, collections, datetime

patch_path, before_path, after_path, out_path = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
esc = html.escape
patch = json.load(open(patch_path))
B = json.load(open(before_path)); A = json.load(open(after_path))

# 元のカードリスト（index.html の CARD_TSV）
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
tsv = src[src.index('const CARD_TSV = `') + len('const CARD_TSV = `'):]
tsv = tsv[:tsv.index('`;')].strip()
faces = {}   # (id, 'top'|'heart') -> dict
for r in csv.reader(io.StringIO(tsv), delimiter='\t', quotechar='"'):
    if not r or r[0].strip().upper() != 'TRUE': continue
    r = r + [''] * (22 - len(r))
    cid = int(r[2])
    faces[(cid, 'top')] = dict(marks=r[3], name=r[4].strip(), range=r[5], el=r[6], atk=r[7], def_=r[8], cost=r[11], text=r[12])
    if len(r) > 14 and '♥' in r[14]:
        faces[(cid, 'heart')] = dict(marks=r[14], name=r[15].strip(), range=r[16], el=r[17], atk=r[18], def_=r[19], cost=r[20], text=r[21] if len(r) > 21 else '')

TIERS = [('S', 18), ('A', 13), ('B', 8), ('C', 4), ('D', -999)]
EFFECT_ONLY = {'ソーサリーリング', 'ドキドキなみだ', '夜魔のホウキ', '誓いの祈り', '寄進の行い', '許しの告解', '秘密の懺悔', 'にじのカーテン'}
def stats(d):
    n = len(d['games']); out = {}
    for c in d['cards']:
        u = max(1, c['uses'])
        v = (c['dealt'] + c['prevented'] + c['heal'] + c['counter'] + c['reflect'] - c['cost']) / u
        eff = c['name'] in EFFECT_ONLY
        out[c['name']] = dict(v=v, per100=100 * c['uses'] / n, tier='効果' if eff else next(t for t, th in TIERS if v >= th), eff=eff, marks=c['marks'])
    return out
sb, sa = stats(B), stats(A)
def team(d):
    g = d['games']; n = len(g)
    return dict(succ=d['baseline']['succubus'], sister=d['baseline']['sister'], rounds=sum(x['rounds'] for x in g) / n,
                deck=sum(x['reason'] == 'deck' for x in g) / n)
tb, ta = team(B), team(A)
def char_rates(d):
    by = collections.defaultdict(list)
    for g in d['games']: by[g['sc']].append(g['reason'] == 'last')
    ctl = sum(by['control']) / len(by['control'])
    return {k: (sum(v) / len(v), sum(v) / len(v) - ctl) for k, v in by.items()}
cb, ca = char_rates(B), char_rates(A)
names = {c['key']: c['name'] for c in B['chars']}

def fmt_face(f, override=None):
    o = override or {}
    atk = str(o.get('atk', f['atk'])); de = str(o.get('def', f['def_'])); cost = o.get('cost', f['cost']).replace('✕', '×')
    parts = []
    if atk not in ('', '-', 'None'): parts.append(f'攻{atk}')
    if de not in ('', '-', 'None'): parts.append(f'防{de}')
    if cost not in ('', '-'): parts.append(cost)
    text = o.get('text', f['text'])
    return '・'.join(parts) + (f'<br><span class="tx">{esc(text)}</span>' if text and text != '-' else '')

rows = []
touched = set()
for pt in patch:
    face = pt.get('face', 'top')
    f = faces[(pt['ids'][0], face)]
    name = f['name']; touched.add(name)
    b, a = sb.get(name), sa.get(name)
    changed = {k: v for k, v in pt['set'].items()}
    rows.append(dict(name=name, marks=f['marks'], ids=pt['ids'], face=face, before=fmt_face(f), after=fmt_face(f, changed), why=pt.get('why', ''),
                     vb=b['v'] if b else 0, va=a['v'] if a else 0, tb=b['tier'] if b else '—', ta=a['tier'] if a else '—',
                     ub=b['per100'] if b else 0, ua=a['per100'] if a else 0))
rows.sort(key=lambda r: r['vb'])

# 変えていないカードで大きく動いたもの（副作用）
side = []
for nm, b in sb.items():
    if nm in touched or b['eff'] or nm not in sa: continue
    dv = sa[nm]['v'] - b['v']
    if abs(dv) >= 1.5 or b['tier'] != sa[nm]['tier']: side.append((nm, b, sa[nm], dv))
side.sort(key=lambda x: x[3])

cnt_b = collections.Counter(s['tier'] for s in sb.values()); cnt_a = collections.Counter(s['tier'] for s in sa.values())
pct = lambda x: f'{x * 100:.1f}%'
tier_span = lambda t: f'<span class="tier t{t if t in "SABCD" else "E"}">{t}</span>'
body_rows = ''.join(
    f'<tr><td class="nm">{esc(r["name"])}<small>{esc(r["marks"])}{"・♥面" if r["face"] == "heart" else ""}　ID {" ".join(map(str, r["ids"]))}</small></td>'
    f'<td>{r["before"]}</td><td class="new">{r["after"]}</td><td class="why">{esc(r["why"])}</td>'
    f'<td class="num">{r["vb"]:.1f} → <b>{r["va"]:.1f}</b></td><td class="num">{tier_span(r["tb"])} → {tier_span(r["ta"])}</td>'
    f'<td class="num">{r["ub"]:.0f} → {r["ua"]:.0f}</td></tr>' for r in rows)
side_rows = ''.join(f'<tr><td class="nm">{esc(nm)}<small>{esc(b["marks"])}</small></td><td class="num">{b["v"]:.1f} → <b>{a["v"]:.1f}</b></td><td class="num">{tier_span(b["tier"])} → {tier_span(a["tier"])}</td><td class="num">{dv:+.1f}</td></tr>' for nm, b, a, dv in side) or '<tr><td colspan="4">大きく動いたカードはない</td></tr>'
char_rows = ''.join(f'<tr><td class="nm">{esc(names[k])}</td><td class="num">{pct(cb[k][0])} → <b>{pct(ca[k][0])}</b></td><td class="num">{(ca[k][0] - cb[k][0]) * 100:+.1f}</td></tr>'
                    for k in sorted(cb, key=lambda k: -ca[k][0]))
tier_line = lambda c: ' '.join(f'<u style="text-decoration:none;white-space:nowrap;margin-right:.35em">{t} {c.get(t, 0)}</u>' for t in ['S', 'A', 'B', 'C', 'D'])
d_before = sorted([n for n, s in sb.items() if s['tier'] == 'D']); d_after = sorted([n for n, s in sa.items() if s['tier'] == 'D'])

page = f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>弱いカードの強化案</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap">
<style>
:root{{--bg:#faf6f8;--surface:#fff;--ink:#1f1522;--ink2:#4f4252;--muted:#7a6c7d;--line:#eadfe7;--band:#f6eef3;--accent:#b8306a;--good:#1f7a4d;
  --tS:#8f1d4f;--tA:#b8306a;--tB:#d9699a;--tC:#eba9c6;--tD:#d9d2d8;--tE:#e9e3ea;--onS:#fff;--onA:#fff;--onB:#1f1522;--onC:#1f1522;--onD:#1f1522;--onE:#4f4252;
  --display:"Dela Gothic One","Hiragino Sans","Yu Gothic",sans-serif;--body:"Zen Kaku Gothic New","Hiragino Sans","Yu Gothic",system-ui,sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#141015;--surface:#1d171f;--ink:#f6ecf2;--ink2:#d3c4cf;--muted:#a896a6;--line:#382c3a;--band:#241c26;--accent:#ff74aa;--good:#7fdcaa;
  --tS:#ff74aa;--tA:#e0558f;--tB:#b04a78;--tC:#7a3a57;--tD:#3a323c;--tE:#2b242d;--onS:#1f0a14;--onA:#1f0a14;--onB:#fff;--onC:#fff;--onD:#d3c4cf;--onE:#d3c4cf}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#141015;--surface:#1d171f;--ink:#f6ecf2;--ink2:#d3c4cf;--muted:#a896a6;--line:#382c3a;--band:#241c26;--accent:#ff74aa;--good:#7fdcaa;
  --tS:#ff74aa;--tA:#e0558f;--tB:#b04a78;--tC:#7a3a57;--tD:#3a323c;--tE:#2b242d;--onS:#1f0a14;--onA:#1f0a14;--onB:#fff;--onC:#fff;--onD:#d3c4cf;--onE:#d3c4cf}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.7}}
main{{max-width:1080px;margin:0 auto;padding:28px 16px 64px;display:flex;flex-direction:column;gap:36px}}
.eyebrow{{font-size:12px;letter-spacing:.25em;color:var(--accent);font-weight:700}}
h1{{font-family:var(--display);font-weight:400;font-size:clamp(28px,6vw,42px);line-height:1.15;margin:6px 0 10px;text-wrap:balance}}
h2{{font-family:var(--display);font-weight:400;font-size:22px;margin:0 0 6px}}
p{{margin:0 0 10px;max-width:70ch;color:var(--ink2)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}}
.kpi{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px}}
.kpi span{{display:block;font-size:12px;color:var(--muted)}} .kpi b{{font-size:20px;font-variant-numeric:tabular-nums}} .kpi em{{display:block;margin-top:2px;font-style:normal;font-size:13px;color:var(--ink2)}}
section{{display:flex;flex-direction:column;gap:10px}}
.tbl{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface)}}
table{{border-collapse:collapse;width:100%;min-width:560px;font-size:13px;font-variant-numeric:tabular-nums}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{color:var(--muted);font-size:12px;white-space:nowrap}}
td.num{{text-align:right;white-space:nowrap}} td.nm{{font-weight:700;white-space:nowrap}} td.nm small{{display:block;font-weight:400;color:var(--muted);font-size:11px}}
td.new{{color:var(--good);font-weight:700}} td.why{{min-width:14em;color:var(--ink2)}} .tx{{font-weight:400;font-size:12px;color:var(--muted)}} td.new .tx{{color:var(--good)}}
.tier{{display:inline-block;min-width:30px;text-align:center;border-radius:6px;padding:0 6px;font-weight:700;font-size:12px}}
.tS{{background:var(--tS);color:var(--onS)}} .tA{{background:var(--tA);color:var(--onA)}} .tB{{background:var(--tB);color:var(--onB)}} .tC{{background:var(--tC);color:var(--onC)}} .tD{{background:var(--tD);color:var(--onD)}} .tE{{background:var(--tE);color:var(--onE)}}
ul{{margin:0;padding-left:1.2em;color:var(--ink2);max-width:72ch}} li{{margin-bottom:6px}}
.note{{font-size:13px;color:var(--muted)}}
</style></head><body><main>
<header>
  <div class="eyebrow">バランス調整案・{esc(os.path.basename(patch_path))}</div>
  <h1>弱いカードの強化案</h1>
  <p>1回あたりのHP価値が低いカードを中心に、{len(rows)}か所の変更を提案する。どれも数値の調整かキーワードの追加だけで、カードの役割は変えていない。提案を入れた状態でCPU同士を{len(A['games']):,}戦回し、効果と副作用を確かめた。</p>
</header>
<section>
  <h2>全体への影響</h2>
  <div class="kpis">
    <div class="kpi"><span>Dのカード（HP価値/回 4未満）</span><b>{len(d_before)} → {len(d_after)}枚</b><em>{esc('・'.join(d_after)) or 'なし'}</em></div>
    <div class="kpi"><span>Tierの分布（効果カードを除く）</span><b style="font-size:15px">{tier_line(cnt_b)}<br>→ {tier_line(cnt_a)}</b></div>
    <div class="kpi"><span>サキュバス陣営の勝率</span><b>{pct(tb['succ'])} → {pct(ta['succ'])}</b><em>シスター陣営 {pct(tb['sister'])} → {pct(ta['sister'])}</em></div>
    <div class="kpi"><span>1試合の平均</span><b>{tb['rounds']:.2f} → {ta['rounds']:.2f}巡</b><em>山札切れで終わる割合 {pct(tb['deck'])} → {pct(ta['deck'])}</em></div>
  </div>
</section>
<section>
  <h2>提案</h2>
  <p>現状の値が低い順。「HP価値/回」は1回使ったときに動いたHP（与ダメージ＋軽減＋回復−払ったHP）、「使用」は100戦あたりの使用回数。</p>
  <div class="tbl"><table style="min-width:900px"><thead><tr><th>カード</th><th>現状</th><th>提案</th><th>理由</th><th class="num">HP価値/回</th><th class="num">Tier</th><th class="num">使用</th></tr></thead><tbody>{body_rows}</tbody></table></div>
</section>
<section>
  <h2>変えていないカードへの影響</h2>
  <p>攻撃カードが強くなると盾の出番が増え、盾1枚あたりの軽減量も変わる。HP価値/回が1.5以上動いたか、Tierが変わったカード。</p>
  <div class="tbl"><table><thead><tr><th>カード</th><th class="num">HP価値/回</th><th class="num">Tier</th><th class="num">差</th></tr></thead><tbody>{side_rows}</tbody></table></div>
</section>
<section>
  <h2>サキュバス能力の勝率への影響</h2>
  <p>カードの変更は全員に効くので、能力の順位はほぼ変わらないはず。差が±2pt程度なら誤差。</p>
  <div class="tbl"><table><thead><tr><th>キャラ</th><th class="num">サキュバス陣営の勝率</th><th class="num">差（pt）</th></tr></thead><tbody>{char_rows}</tbody></table></div>
</section>
<section>
  <h2>補足</h2>
  <ul>
    <li>効果系のカード（誓いの祈り・寄進の行い・秘密の懺悔・夜魔のホウキなど）はHPを動かさないので、この指標では強さを測れない。CPUが使いこなせていない面もあるため、今回は対象外にした。</li>
    <li>《追撃》の組み合わせで出たダメージは、重ねたカードの攻撃力の比で分けて数えている。起点になる小さいカード（ふきや・つえ）は、組み合わせの一部として実際より低く出やすい。</li>
    <li>なべのふたの「1枚引く」はHPを動かさないので、HP価値/回には入っていない。Dに残っていても、盾としての役割は上がっている。</li>
    <li>すべてCPU同士の結果。数値は叩き台として使い、最終的には人の試遊で確かめてほしい。</li>
    <li>再現：<code>node sim/run.js 1000 結果.json {esc(os.path.relpath(patch_path, ROOT))}</code> → <code>python3 sim/proposal.py …</code></li>
  </ul>
  <p class="note">作成日 {datetime.date.today().isoformat()}</p>
</section>
</main></body></html>'''
open(out_path, 'w').write(page)
print('rows', len(rows), 'D', len(d_before), '->', len(d_after), 'side', len(side))
