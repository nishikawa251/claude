# サキュバスシスターズ：カードリストのページ（cardlist.html）を作る
#
# 使い方：python3 sim/cardlist.py
#   - カードの中身は index.html の CARD_TSV（いまゲームで使っている値）から読む
#   - 強化前の値は git のコミット BASE_COMMIT の index.html から読み、変わったところに印をつける
#   - 評価（Tier・1回あたりHP価値）は sim/cards.csv（最新のバランス調査）から読む
import csv, io, json, os, re, subprocess, datetime, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE_COMMIT = 'afefa62'   # カード強化案を入れる前
BALANCE_URL = 'https://claude.ai/artifact/5WRHC99kT5Htw4fdZg24Ps'
EL = {'〔無〕': 'none', '〔火〕': 'fire', '〔水〕': 'water', '〔雷〕': 'thunder'}

def card_rows(src):
    tsv = re.search(r'const CARD_TSV = `\n(.*?)`;', src, re.S).group(1)
    out = []
    for r in csv.reader(io.StringIO(tsv), delimiter='\t', quotechar='"'):
        if not r or r[0].strip().upper() != 'TRUE': continue
        r = [c.strip() for c in r] + [''] * 22
        out.append(r)
    return out

def num(v):
    v = v.strip()
    return int(v) if re.fullmatch(r'-?\d+', v) else None

def face(marks, name, rng, el, atk, de, cost, text):
    text = '' if text in ('', '-') else text
    return {'marks': [m for m in re.split(r'[,\s]+', marks) if m], 'name': name, 'range': rng or '単体',
            'el': EL.get(el, 'none'), 'atk': num(atk), 'def': num(de), 'cost': '' if cost in ('', '-') else cost, 'text': text}

def cards_from(src):
    cards = {}
    for r in card_rows(src):
        top = face(r[3], r[4], r[5], r[6], r[7], r[8], r[11], r[12])
        heart = face(r[14], r[15], r[16], r[17], r[18], r[19], r[20], r[21]) if '♥' in r[14] else None
        cards[int(r[2])] = {'id': int(r[2]), 'exp': r[9], 'trig': r[10], 'top': top, 'heart': heart}
    return cards

now = cards_from(open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read())
try:
    old_src = subprocess.run(['git', 'show', f'{BASE_COMMIT}:succubus-sisters/index.html'], capture_output=True, text=True, cwd=ROOT, check=True).stdout
    before = cards_from(old_src)
except Exception:
    before = {}

# 評価（最新のバランス調査）
tiers = {}
with open(os.path.join(HERE, 'cards.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        tiers[row['カード']] = {'tier': row['Tier'], 'value': float(row['1回あたりHP価値']), 'uses': float(row['100戦あたり使用回数'])}

LABEL = {'atk': '攻撃', 'def': '防御', 'cost': 'コスト', 'text': '効果', 'range': '範囲'}
def changes(cid):
    b, a = before.get(cid), now[cid]
    if not b: return []
    out = []
    for side in ('top', 'heart'):
        fb, fa = b[side], a[side]
        if not fb or not fa: continue
        for k in ('atk', 'def', 'cost', 'range', 'text'):
            if fb[k] != fa[k]:
                show = lambda v: '—' if v in (None, '') else str(v)
                out.append({'side': side, 'field': LABEL[k], 'from': show(fb[k]) if k != 'text' else ('なし' if not fb[k] else fb[k]),
                            'to': show(fa[k]) if k != 'text' else fa[k]})
    return out

def kind_of(f):
    m = f['marks']
    return 'judge' if '†' in m else 'magic' if '☆' in m else 'atk' if '▲' in m else 'def' if '○' in m else 'sup'

# 同じ中身のカードをまとめる（名前・♥面・トリガー・数値が同じもの）
groups = {}
for cid in sorted(now):
    c = now[cid]
    key = json.dumps([c['top'], c['heart'], c['trig'], c['exp']], ensure_ascii=False, sort_keys=True)
    g = groups.setdefault(key, {**c, 'ids': [], 'kind': kind_of(c['top'])})
    g['ids'].append(cid)
# 同じカードが2枚以上あるときも、1枚ずつ並べる（何枚中の何枚目かを添える）
data = []
for g in groups.values():
    t = tiers.get(g['top']['name'])
    h = tiers.get(g['heart']['name']) if g['heart'] else None
    for k, cid in enumerate(g['ids']):
        data.append({'ids': [cid], 'copy': k + 1, 'copies': len(g['ids']), 'exp': g['exp'], 'trig': g['trig'], 'kind': g['kind'],
                     'top': g['top'], 'heart': g['heart'], 'changes': changes(cid), 'tier': t, 'htier': h})
data.sort(key=lambda d: d['ids'][0])

total = len(now)
counts = {
    'kind': {k: sum(len(d['ids']) for d in data if d['kind'] == k) for k in ('atk', 'def', 'magic', 'sup', 'judge')},
    'el': {e: sum(len(d['ids']) for d in data if d['top']['el'] == e) for e in ('none', 'fire', 'water', 'thunder')},
    'trig': {t: sum(len(d['ids']) for d in data if d['trig'] == t) for t in 'ABCDE'},
    'heart': sum(len(d['ids']) for d in data if d['heart']),
    'changed': sum(len(d['ids']) for d in data if d['changes']),
    'groups': len(groups),
}
# ドット絵の試作（カード名 → img/pixel/*.svg）
PIXEL = {'エクスカリバー': 'excalibur', 'ほのおのやいば': 'flameblade', 'クロスボウ': 'crossbow',
         'なべのふた': 'potlid', 'ミラーシールド': 'mirrorshield', 'うろこのたて': 'scaleshield',
         '＜火の玉＞': 'fireball', '＜氷の柱＞': 'icepillar', '＜稲妻＞': 'lightning',
         'ハートのせいすい': 'heartwater', '太陽のお守り': 'sunamulet', '夜魔のホウキ': 'nightbroom',
         '聖なるわからせ棒': 'holyrod', '聖なるわからせ竿': 'holypole', '聖なるちくりんちょ': 'holyneedle'}
for d in data:
    k = PIXEL.get(d['top']['name'])
    if k: d['art'] = f'img/pixel/{k}.svg'
counts['art'] = sum(1 for d in data if d.get('art'))
images = sorted({f'img/cards/{d["ids"][0]:03d}.jpg' for d in data} | {d['art'] for d in data if d.get('art')})

tpl = open(os.path.join(HERE, 'cardlist_template.html'), encoding='utf-8').read()
page = (tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
           .replace('__COUNTS__', json.dumps(counts))
           .replace('__TOTAL__', str(total))
           .replace('__BALANCE_URL__', html.escape(BALANCE_URL))
           .replace('__DATE__', datetime.date.today().isoformat()))
open(os.path.join(ROOT, 'cardlist.html'), 'w', encoding='utf-8').write(page)
json.dump(images, open(os.path.join(HERE, 'cardlist_images.json'), 'w'), indent=0)
print('cards', total, 'entries', len(data), 'groups', len(groups), 'changed', counts['changed'], 'images', len(images))
