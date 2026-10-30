"""メスガキ・クー 物理版（52枚）の印刷データを作る。

usage: python3 -I print_cards.py --out <dir> [--art <元立ち絵dir>] [--size 91x55] [--bleed 1.5] [--dpi 350]
                                [--chars shiro,momoko,emera,oren,aqua,asagi] [--index ../index.html] [--lion]

--size は仕上がりの「長辺x短辺」でも「幅x高さ」でもよい。文字もののカードは短辺を幅にした縦型、キャラカードは横型で作る。
--lion を付けると、ライオン名刺「異種（21面テンプレート）」用に、テンプレートへ貼る向きに回転した各面の画像
（lion/T<n>_<A-U>_front/back.png）と、参考の面付けシート（lion/T<n>_front.png / _back.png、A3・3列×7行・裏面は鏡合わせ）を出す。
  ・縦型のカード：表は左へ90度、裏は右へ90度回転（マニュアル「表裏共に縦型」）
  ・横型（キャラカード）：回転なし
  ・裁ち落としは塗り足し1.5mm、文字は仕上がりから3mm内側

出力（<dir>/）
  cards/NN_<種別>_<名前>_front.png / _back.png  … 1枚ずつ、塗り足し込みのサイズ（既定 69×94mm @350dpi = 950×1295px）
  mesugaki-coup_cards.pdf                         … 1ページ1面、表→裏の順に104ページ（ページサイズも塗り足し込み）
  preview.png                                     … 全カードの表裏一覧
  README.txt                                      … 仕様とカード一覧

・ガキカード15（表5種×3、裏共通）、キャラカード12（6キャラ×上下。表＝通常絵、裏＝ボロ絵の両面）、
  トリガー18（基本12＋おすすめデッキの新カード6。裏共通）、早見表6（表裏別）、タイトル1（表裏別）
・カード文言と枚数は index.html の定義（ROLES / ACTIONS / TRIGGERS / DECK_PRESETS）から読む。
・キャラカードは横長（63×88 を横に使う）。元立ち絵（--art）が無いときはゲーム用 img/*.webp から作る（低解像度）。
"""
import sys, os, re, json, math, argparse, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--art', default=None, help='Bombergirl 立ち絵（<name>000.png 通常 / <name>001.jpg ボロ）のフォルダ。"shapes" で図形だけのオリジナル紙人形にする（印刷入稿向け）')
ap.add_argument('--index', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html'))
ap.add_argument('--size', default='91x55', help='仕上がり mm（長辺x短辺）')
ap.add_argument('--bleed', type=float, default=1.5, help='塗り足し mm（各辺）')
ap.add_argument('--all-triggers', action='store_true', help='定義されている全トリガー（2軍も）を入れる')
ap.add_argument('--dud', type=int, default=0, help='ハズレ（効果なし）トリガーの枚数')
ap.add_argument('--ref', type=int, default=6, help='早見表の枚数')
ap.add_argument('--blank', type=int, default=0, help='白紙トリガー（自作用）の枚数')
ap.add_argument('--chara-copies', type=int, default=1, help='キャラカードを何組入れるか（スペア用。2なら各キャラの上下が2枚ずつ）')
ap.add_argument('--template', default=None, help='ライオン名刺 異種の AI/PDF テンプレート。指定すると各面に貼り込んだ入稿 PDF（表・裏の2ページ×テンプレート数）を lion/ に出す')
ap.add_argument('--samples', action='store_true', help='見本（数枚の表裏を1枚の画像に）だけ出す')
ap.add_argument('--lion', action='store_true', help='ライオン名刺 異種テンプレート向けの回転済み画像と面付けシートも出す')
ap.add_argument('--dpi', type=int, default=350)
ap.add_argument('--chars', default='momoko,grimaloe,aqua,pin,shiro,kuro', help='印刷するキャラ id を6つ（既定：モモコ・グリムアロエ・アクア・パイン・シロ・クロ）')
ap.add_argument('--font', default=None, help='本文フォント（太めのTTF/OTF）。省略時は tools/fonts/MPLUS1p-Bold.ttf')
ap.add_argument('--font-head', default=None, help='見出しフォント。省略時は tools/fonts/DelaGothicOne-Regular.ttf')
ap.add_argument('--font-black', default=None, help='大見出し用のさらに太いフォント。省略時は tools/fonts/MPLUS1p-Black.ttf')
args = ap.parse_args()

OUT = args.out
os.makedirs(os.path.join(OUT, 'cards'), exist_ok=True)
MM = args.dpi / 25.4
_a, _b = [float(v) for v in args.size.lower().split('x')]
TW_MM, TH_MM = min(_a, _b), max(_a, _b)   # 縦型（短辺×長辺）
B_MM = args.bleed
# 縦向きカード（塗り足し込み）
PW, PH = round((TW_MM + 2 * B_MM) * MM), round((TH_MM + 2 * B_MM) * MM)
BL = round(B_MM * MM)            # 塗り足し幅 px
SAFE = round(3 * MM)             # 仕上がり線から内側の安全マージン
# 横向きカード（キャラカード）
LW, LH = PH, PW


HERE = os.path.dirname(os.path.abspath(__file__))


def find_font(given, names):
    if given:
        return given
    for n in names:
        for d in [os.path.join(HERE, 'fonts'), '/usr/share/fonts/opentype/ipafont-gothic', '/usr/share/fonts/truetype']:
            c = os.path.join(d, n)
            if os.path.exists(c):
                return c
    raise SystemExit(f'フォントが見つからない: {names}。--font / --font-head で指定してください')


FONT_BODY = find_font(args.font, ['MPLUS1p-Bold.ttf', 'ipagp.ttf', 'fonts-japanese-gothic.ttf'])
FONT_HEAD = find_font(args.font_head, ['DelaGothicOne-Regular.ttf', 'MPLUS1p-Black.ttf', 'ipagp.ttf'])
FONT_BLACK = find_font(args.font_black, ['MPLUS1p-Black.ttf', 'MPLUS1p-Bold.ttf', 'ipagp.ttf'])
_fonts = {}


def font(pt, kind='body'):
    """pt はポイント指定。dpi に合わせて px に換算。kind: body（太ゴシック）/ head（見出し）/ black（極太）"""
    path = {'body': FONT_BODY, 'head': FONT_HEAD, 'black': FONT_BLACK}[kind]
    px = max(6, round(pt * args.dpi / 72))
    key = (path, px)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, px)
    return _fonts[key]


# ---------------------------------------------------------------- ゲーム定義を index.html から読む
src = open(args.index, encoding='utf-8').read()


def js_block(start_marker, end_marker):
    i = src.find(start_marker); j = src.find(end_marker, i)
    return src[i:j]


ROLES = {}
for m in re.finditer(r"\{ id:'(\w+)',\s*name:'([^']+)',\s*action:(?:'(\w+)'|null),\s*blocks:\[([^\]]*)\],\s*line:'([^']*)',\s*phrase:'([^']*)',\s*color:'(#[0-9a-f]+)'", js_block('const ROLES = {', '};')):
    ROLES[m.group(1)] = dict(name=m.group(2), action=m.group(3), blocks=re.findall(r"'(\w+)'", m.group(4)), line=m.group(5), phrase=m.group(6), color=m.group(7))
ACTIONS = {}
for m in re.finditer(r"\{ id:'(\w+)',\s*name:'([^']+)',(?:\s*role:'(\w+)',)?\s*desc:'([^']+)'(.*?)\}", js_block('const ACTIONS = {', '};')):
    rest = m.group(5)
    ACTIONS[m.group(1)] = dict(name=m.group(2), role=m.group(3), desc=m.group(4), target='target:true' in rest,
                               cost=int(re.search(r'cost:(\d+)', rest).group(1)) if re.search(r'cost:(\d+)', rest) else 0,
                               blockedBy=re.findall(r"'(\w+)'", re.search(r'blockedBy:\[([^\]]*)\]', rest).group(1)) if 'blockedBy' in rest else [])
RULES = {k: int(v) for k, v in re.findall(r"(\w+):\s*(\d+),", js_block('const RULES = {', '};'))}
TRIGGERS = {}
for m in re.finditer(r"\{ id:'(t\d+)',\s*name:'([^']+)',\s*text:(?:'([^']*)'|`([^`]*)`)(.*?)\}", js_block('const TRIGGERS = [', '];')):
    text = m.group(3) if m.group(3) is not None else m.group(4)
    text = re.sub(r'\$\{RULES\.(\w+)\}', lambda mm: str(RULES.get(mm.group(1), '?')), text)
    TRIGGERS[m.group(1)] = dict(name=m.group(2), text=text, persistent='persistent:true' in m.group(5), retired='retired:true' in m.group(5))
PRESETS = {}
for m in re.finditer(r"(basic|fresh|mix):\s*\[([^\]]*)\]", js_block('const DECK_PRESETS', 'const DECK_SIZE')):
    PRESETS[m.group(1)] = re.findall(r"'(t\d+)'", m.group(2))
SETS = {}   # カードの系統（基本／新カード。それ以外は2軍）
for m in re.finditer(r"(basic|fresh):\s*\[([^\]]*)\]", js_block('const SETS = {', '};')):
    SETS[m.group(1)] = re.findall(r"'(t\d+)'", m.group(2))
CHARS = [(m.group(1), m.group(2)) for m in re.finditer(r"\{ id:'([a-z]+)',\s*name:'([^']+)' \}", js_block('const CHARS = [', '];'))]
CHAR_NAME = dict(CHARS)
PRINT_CHARS = [c for c, _ in CHARS] if args.chars == 'all' else [c for c in args.chars.split(',') if c]
assert all(c in CHAR_NAME for c in PRINT_CHARS), f'知らないキャラ id: {PRINT_CHARS}'
TRIG18 = list(PRESETS['basic'])   # 52枚版に入れるトリガー＝基本デッキ18枚
if args.all_triggers:   # 基本 → 新カード → 2軍 の順に全部（見送り札は除く）
    TRIG18 = SETS['basic'] + SETS['fresh'] + [i for i in TRIGGERS if i not in SETS['basic'] and i not in SETS['fresh'] and not TRIGGERS[i]['retired']]

# ---------------------------------------------------------------- 描画ユーティリティ
INK = (40, 22, 48)
DIM = (120, 100, 125)
PAPER = (252, 247, 250)


def hexrgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


NO_START = '。、，．）」』】〕〉》♥♡～〜ー！？…・)]'   # 行頭に来てはいけない
NO_END = '「『（【〔〈《(['                             # 行末に来てはいけない
PAIRS = {'「': '」', '（': '）', '(': ')'}


def _tokens(text, f, width):
    """分割しないトークン：アクション名（ばいば～い♥ など）、短い「…」（…）(…)（12文字以内・行幅の8割以内）"""
    words = sorted({v['name'] for v in globals().get('ACTIONS', {}).values()}, key=len, reverse=True)
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch in PAIRS:
            j = text.find(PAIRS[ch], i)
            if j != -1 and j - i <= 12 and f.getlength(text[i:j + 1]) <= width * 0.8:
                out.append(text[i:j + 1]); i = j + 1; continue
        w = next((w for w in words if text.startswith(w, i)), None)
        if w and f.getlength(w) <= width * 0.8:
            out.append(w); i += len(w); continue
        out.append(ch); i += 1
    return out


def wrap(text, f, width):
    """日本語向けの折り返し（禁則つき）"""
    lines = []
    for para in text.split('\n'):
        cur = ''
        for t in _tokens(para, f, width):
            if cur and f.getlength(cur + t) > width:
                if len(t) == 1 and t in NO_START:          # 追い出し：直前の1文字ごと次行へ
                    if len(cur) >= 2 and cur[-1] not in NO_START and cur[-1] not in NO_END:
                        lines.append(cur[:-1]); cur = cur[-1] + t
                    else:
                        cur += t                            # 追い出せなければぶら下げ
                    continue
                if cur[-1] in NO_END and len(cur) >= 2:     # 行末の「 は次行へ
                    lines.append(cur[:-1]); cur = cur[-1] + t; continue
                lines.append(cur); cur = t
            else:
                cur += t
        lines.append(cur)
    return lines


def fit_font(text, max_w, pt, min_pt=5, kind='body', step=0.5):
    """max_w に収まる最大の文字サイズ（pt 刻み）"""
    while pt > min_pt and font(pt, kind).getlength(text) > max_w:
        pt -= step
    return font(pt, kind)


def draw_text_block(d, xy, text, f, width, fill=INK, spacing=1.35, align='left'):
    x, y = xy
    lh = int(f.size * spacing)
    for ln in wrap(text, f, width):
        tx = x
        if align == 'center':
            tx = x + (width - f.getlength(ln)) / 2
        d.text((tx, y), ln, font=f, fill=fill)
        y += lh
    return y


def text_center(d, cx, y, text, f, fill=INK):
    w = f.getlength(text)
    d.text((cx - w / 2, y), text, font=f, fill=fill)


def stripes(w, h, c1, c2, step=28):
    im = Image.new('RGB', (w, h), c1)
    d = ImageDraw.Draw(im)
    for k in range(-h, w + h, step * 2):
        d.polygon([(k, 0), (k + step, 0), (k + step - h, h), (k - h, h)], fill=c2)
    return im


def trim_guides(im):
    """確認用：仕上がり線（印刷データには入れない）。preview だけで使う"""
    im = im.copy(); d = ImageDraw.Draw(im)
    w, h = im.size
    d.rectangle((BL, BL, w - BL - 1, h - BL - 1), outline=(255, 0, 90), width=2)
    return im


# ---------------------------------------------------------------- ガキカード
def role_front(rid):
    R = ROLES[rid]; col = hexrgb(R['color'])
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    # 外周の帯（塗り足しまで色を伸ばす）
    d.rectangle((0, 0, PW, PH), fill=mix(col, (255, 255, 255), 0.82))
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), fill=PAPER, outline=col, width=int(0.6 * MM))
    # 見出し帯
    hb = int(13 * MM)
    d.rounded_rectangle((inner[0], inner[1], inner[2], inner[1] + hb), radius=int(3 * MM), fill=col)
    d.rectangle((inner[0], inner[1] + hb // 2, inner[2], inner[1] + hb), fill=col)
    text_center(d, PW / 2, inner[1] + int(1.8 * MM), R['name'], fit_font(R['name'], inner[2] - inner[0] - int(6 * MM), 16, 10, 'head'), fill=(255, 255, 255))
    text_center(d, PW / 2, inner[1] + int(8.6 * MM), 'GAKI CARD', font(6), fill=mix(col, (255, 255, 255), 0.75))
    # 大きなマーク（頭文字）
    text_center(d, PW / 2, inner[1] + hb + int(4 * MM), R['name'][0], font(56, 'head'), fill=mix(col, PAPER, 0.8))
    y = inner[1] + hb + int(31 * MM)
    x0, wdt = inner[0] + int(3 * MM), inner[2] - inner[0] - int(6 * MM)
    # できる
    d.rounded_rectangle((inner[0] + int(2 * MM), y - int(1.5 * MM), inner[2] - int(2 * MM), y + int(15 * MM)), radius=int(1.5 * MM), fill=mix(col, (255, 255, 255), 0.9))
    d.text((x0, y), 'できる', font=font(7), fill=col)
    if R['action']:
        A = ACTIONS[R['action']]
        d.text((x0, y + int(3.4 * MM)), A['name'], font=font(10.5, 'black'), fill=INK)
        draw_text_block(d, (x0, y + int(8.6 * MM)), A['desc'], font(6.5), wdt, fill=DIM)
    else:
        d.text((x0, y + int(3.4 * MM)), 'なし', font=font(10.5, 'black'), fill=INK)
        draw_text_block(d, (x0, y + int(8.6 * MM)), 'アクションは持たない。ブロック専門', font(6.5), wdt, fill=DIM)
    y += int(17.5 * MM)
    # ブロック
    d.rounded_rectangle((inner[0] + int(2 * MM), y - int(1.5 * MM), inner[2] - int(2 * MM), y + int(13 * MM)), radius=int(1.5 * MM), fill=mix(col, (255, 255, 255), 0.9))
    d.text((x0, y), '「は？」ブロック', font=font(7), fill=col)
    blocks = '・'.join(ACTIONS[b]['name'] for b in R['blocks']) or 'なし'
    d.text((x0, y + int(3.4 * MM)), blocks, font=fit_font(blocks, wdt, 10.5, 7, 'black'), fill=INK)
    draw_text_block(d, (x0, y + int(8.6 * MM)), f'「{R["line"]}」', font(6.5), wdt, fill=DIM)
    # 公開のひとこと
    ph = f'公開：「{R["phrase"]}」'; pw = inner[2] - inner[0] - int(6 * MM)
    if font(6).getlength(ph) <= pw:
        text_center(d, PW / 2, inner[3] - int(7 * MM), ph, font(6), fill=DIM)
    else:                                    # 長いセリフは2行に（下から積む）
        pl = wrap(ph, font(5.5), pw); lh = int(font(5.5).size * 1.3)
        yy = inner[3] - int(7 * MM) - lh * (len(pl) - 1) + int(0.8 * MM)
        for ln in pl:
            text_center(d, PW / 2, yy, ln, font(5.5), fill=DIM); yy += lh
    text_center(d, PW / 2, inner[3] - int(3.6 * MM), 'メスガキ・クー', font(5), fill=mix(col, PAPER, 0.3))
    return im


def role_back():
    im = stripes(PW, PH, (76, 42, 94), (59, 31, 75), step=int(2.2 * MM)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE), radius=int(3 * MM), outline=(122, 74, 142), width=int(0.8 * MM))
    text_center(d, PW / 2, PH / 2 - int(14 * MM), '♥', font(44), fill=(217, 184, 230))
    text_center(d, PW / 2, PH / 2 + int(4 * MM), 'GAKI', font(14, 'head'), fill=(217, 184, 230))
    text_center(d, PW / 2, PH / 2 + int(11 * MM), 'メスガキ・クー', font(7), fill=(180, 150, 200))
    return im


# ---------------------------------------------------------------- トリガーカード
def trigger_front(tid):
    T = TRIGGERS[tid]
    navy = (43, 49, 72); edge = (90, 106, 168)
    im = Image.new('RGB', (PW, PH), navy); d = ImageDraw.Draw(im)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), outline=edge, width=int(0.7 * MM))
    text_center(d, PW / 2, inner[1] + int(3 * MM), 'TRIGGER', font(6), fill=(138, 152, 214))
    # 名前（長いと縮小）
    name = T['name']; nf = fit_font(name, inner[2] - inner[0] - int(8 * MM), 15, 9, 'head')
    text_center(d, PW / 2, inner[1] + int(8 * MM) + (font(15, 'head').size - nf.size) // 2, name, nf, fill=(255, 255, 255))
    d.line((inner[0] + int(4 * MM), inner[1] + int(17 * MM), inner[2] - int(4 * MM), inner[1] + int(17 * MM)), fill=edge, width=int(0.4 * MM))
    # 常時／1回 の帯
    tag = '常時' if T['persistent'] else ('1回' if '（1回）' in T['text'] else '発動時')
    tw = font(6).getlength(tag) + int(4 * MM)
    d.rounded_rectangle((PW / 2 - tw / 2, inner[1] + int(19 * MM), PW / 2 + tw / 2, inner[1] + int(24.5 * MM)), radius=int(1 * MM), fill=(255, 209, 102) if T['persistent'] else edge)
    text_center(d, PW / 2, inner[1] + int(20 * MM), tag, font(6), fill=(58, 42, 0) if T['persistent'] else (255, 255, 255))
    # 効果文
    x0 = inner[0] + int(4 * MM); wdt = inner[2] - inner[0] - int(8 * MM)
    body = T['text'].replace('（1回）', '')
    top, bottom = inner[1] + int(29 * MM), inner[3] - int(11 * MM)
    fs = 12 if len(body) <= 24 else 11 if len(body) <= 40 else 10 if len(body) <= 60 else 9
    while fs > 7:                              # 収まるまで縮める。最終行が2文字以下の孤立も避ける
        f = font(fs); ls = wrap(body, f, wdt); n = len(ls)
        if top + n * int(f.size * 1.5) <= bottom and not (n > 1 and len(ls[-1]) <= 2): break
        fs -= 0.5
    draw_text_block(d, (x0, top), body, font(fs), wdt, fill=(230, 236, 255), spacing=1.5)
    # セット名
    sets = 'おすすめ' if tid in PRESETS['mix'] else ''
    base = '基本' if tid in SETS['basic'] else '新カード' if tid in SETS['fresh'] else '2軍'
    text_center(d, PW / 2, inner[3] - int(7 * MM), base + ('／' + sets if sets else ''), font(5.5), fill=(138, 152, 214))
    text_center(d, PW / 2, inner[3] - int(3.6 * MM), 'メスガキ・クー', font(5), fill=(110, 120, 170))
    return im


def dud_front():
    navy = (42, 42, 54); edge = (74, 74, 92)
    im = Image.new('RGB', (PW, PH), navy); d = ImageDraw.Draw(im)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), outline=edge, width=int(0.7 * MM))
    text_center(d, PW / 2, inner[1] + int(3 * MM), 'TRIGGER', font(6), fill=(120, 120, 140))
    text_center(d, PW / 2, inner[1] + int(8 * MM), 'ハズレ', font(15, 'head'), fill=(200, 200, 215))
    d.line((inner[0] + int(4 * MM), inner[1] + int(17 * MM), inner[2] - int(4 * MM), inner[1] + int(17 * MM)), fill=edge, width=int(0.4 * MM))
    text_center(d, PW / 2, inner[1] + int(30 * MM), '効果なし', font(9, 'black'), fill=(154, 154, 168))
    text_center(d, PW / 2, inner[1] + int(38 * MM), '脱いだのに何も起きない……', font(6), fill=(120, 120, 140))
    text_center(d, PW / 2, inner[3] - int(3.6 * MM), 'メスガキ・クー', font(5), fill=(110, 110, 130))
    return im


def blank_front():
    navy = (43, 49, 72); edge = (90, 106, 168)
    im = Image.new('RGB', (PW, PH), navy); d = ImageDraw.Draw(im)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), outline=edge, width=int(0.7 * MM))
    text_center(d, PW / 2, inner[1] + int(3 * MM), 'TRIGGER', font(6), fill=(138, 152, 214))
    # 名前欄・効果欄（白地に書き込める）
    d.rounded_rectangle((inner[0] + int(4 * MM), inner[1] + int(8 * MM), inner[2] - int(4 * MM), inner[1] + int(16 * MM)), radius=int(1 * MM), fill=(245, 246, 255))
    d.rounded_rectangle((inner[0] + int(4 * MM), inner[1] + int(20 * MM), inner[2] - int(4 * MM), inner[3] - int(9 * MM)), radius=int(1 * MM), fill=(245, 246, 255))
    for k in range(1, 8):
        yy = inner[1] + int(20 * MM) + k * int(7 * MM)
        if yy < inner[3] - int(10 * MM):
            d.line((inner[0] + int(6 * MM), yy, inner[2] - int(6 * MM), yy), fill=(205, 210, 235), width=1)
    text_center(d, PW / 2, inner[1] + int(17 * MM), '自作トリガー', font(5), fill=(138, 152, 214))
    text_center(d, PW / 2, inner[3] - int(3.6 * MM), 'メスガキ・クー', font(5), fill=(110, 120, 170))
    return im


def trigger_back():
    im = stripes(PW, PH, (43, 49, 72), (35, 40, 66), step=int(2.2 * MM)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE), radius=int(3 * MM), outline=(90, 106, 168), width=int(0.8 * MM))
    text_center(d, PW / 2, PH / 2 - int(6 * MM), 'TRIGGER', font(14, 'head'), fill=(138, 152, 214))
    text_center(d, PW / 2, PH / 2 + int(3 * MM), 'メスガキ・クー', font(7), fill=(110, 120, 170))
    return im


# ---------------------------------------------------------------- キャラカード（横長・両面）
# 立ち絵の腰の高さ（人物範囲の上端=0, 下端=1）とボロ絵の腰（クロップ後）。split_cards.py と同じ値
WAIST = {'aqua': 0.46, 'asagi': 0.44, 'emera': 0.45, 'grimaloe': 0.46, 'momoko': 0.47, 'oren': 0.48,
         'papuru': 0.50, 'sepia': 0.45, 'shiro': 0.47, 'tsugaru': 0.47, 'urushi': 0.50, 'pin': 0.43, 'kuro': 0.40}
BORO_WAIST = {'oren': 0.53, 'tsugaru': 0.53, 'sepia': 0.48, 'shiro': 0.52, 'kuro': 0.58}
BORO_CROP = (20 / 425, 40 / 600, 405 / 425, 560 / 600)
ALIAS = {'grimaloe': ['grimaloe', 'grimaroe']}
FW, FH = LW, LH * 2          # 上下2枚ぶんの全身キャンバス（塗り足し込み）
MARGIN = BL + SAFE


def figure_bbox(im):
    a = im.split()[-1]; w, h = a.size
    if (w, h) == (760, 760):
        band = a.crop((215, 741, 546, 752))
        if band.getbbox():
            a.paste(0, (215, 741, 546, 752)); im.putalpha(a)
    return a.getbbox()


def tint_of(im, bb):
    sub = im.crop(bb).convert('RGBA').resize((40, 40)); r = g = b = n = 0
    for p in sub.getdata():
        if p[3] > 200:
            r += p[0]; g += p[1]; b += p[2]; n += 1
    return (r // n, g // n, b // n) if n else (200, 205, 215)


def radial_bg(w, h, tint):
    small = Image.new('RGB', (w // 8, h // 8)); px = small.load()
    cx, cy = small.size[0] / 2, small.size[1] / 2; rmax = math.hypot(cx, cy)
    edge = tuple(int(255 * 0.80 + c * 0.20) for c in tint)
    for y in range(small.size[1]):
        for x in range(small.size[0]):
            t = min(1.0, math.hypot(x - cx, y - cy) / rmax) ** 2
            px[x, y] = tuple(int(255 * (1 - t) + e * t) for e in edge)
    return small.resize((w, h), Image.BICUBIC)


def char_front_canvas(path, waist):
    im = Image.open(path).convert('RGBA'); bb = figure_bbox(im); fig = im.crop(bb); fw, fh = fig.size
    scale = min((FW - 2 * MARGIN) / fw, (LH - MARGIN) / (fh * waist), (LH - MARGIN) / (fh * (1 - waist)))
    fig = fig.resize((max(1, int(fw * scale)), max(1, int(fh * scale))), Image.LANCZOS)
    bg = radial_bg(FW, FH, tint_of(im, bb)).convert('RGBA')
    shadow = Image.new('RGBA', (FW, FH), (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    sw = int(fig.size[0] * 0.55); sx = (FW - sw) // 2; sy = int(FH / 2 - fig.size[1] * waist) + fig.size[1] - 18
    sd.ellipse((sx, sy - 22, sx + sw, sy + 22), fill=(40, 30, 50, 70)); shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    bg.alpha_composite(shadow)
    bg.alpha_composite(fig, ((FW - fig.size[0]) // 2, int(FH / 2 - fig.size[1] * waist)))
    return bg.convert('RGB')


def char_back_canvas(path, waist):
    im = Image.open(path).convert('RGB'); w, h = im.size; l, t, r, b = BORO_CROP
    im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b))); cw, ch = im.size
    scale = max(FW / cw, FH / ch, FH / (ch * 2 * min(waist, 1 - waist)))
    im = im.resize((int(cw * scale) + 1, int(ch * scale) + 1), Image.LANCZOS)
    x = (im.size[0] - FW) // 2; y = int(im.size[1] * waist - FH / 2); y = max(0, min(y, im.size[1] - FH))
    return im.crop((x, y, x + FW, y + FH))


def char_from_webp(cid, half, boro):
    """元立ち絵が無いとき：ゲーム用 416×298 の webp を拡大して使う（印刷には粗い）"""
    p = os.path.join(os.path.dirname(args.index), 'img', f'{cid}_{half}_{"001" if boro else "000"}.webp')
    im = Image.open(p).convert('RGB')
    return im.resize((LW, LH), Image.LANCZOS)


def char_cards(cid):
    """-> {'top': (front, back), 'bottom': (front, back)}"""
    out = {}
    src000 = src001 = None
    if args.art and args.art != 'shapes':
        for n in ALIAS.get(cid, [cid]):
            for ext in ('png', 'PNG'):
                p = os.path.join(args.art, f'{n}000.{ext}')
                if os.path.exists(p): src000 = p
            for ext in ('jpg', 'JPG', 'png'):
                p = os.path.join(args.art, f'{n}001.{ext}')
                if os.path.exists(p): src001 = p
    if args.art == 'shapes':
        # 図形版：立ち絵を使わず、丸と四角で組んだ紙人形（tools/shape_chars.py）
        import importlib.util
        spec = importlib.util.spec_from_file_location('shape_chars', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shape_chars.py'))
        sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
        fc = sc.full(cid, FW, FH, False); bc = sc.full(cid, FW, FH, True)
        fronts = (fc.crop((0, 0, LW, LH)), fc.crop((0, LH, LW, FH))); backs = (bc.crop((0, 0, LW, LH)), bc.crop((0, LH, LW, FH)))
    elif src000 and src001:
        fc = char_front_canvas(src000, WAIST.get(cid, 0.5)); bc = char_back_canvas(src001, BORO_WAIST.get(cid, 0.5))
        fronts = (fc.crop((0, 0, LW, LH)), fc.crop((0, LH, LW, FH))); backs = (bc.crop((0, 0, LW, LH)), bc.crop((0, LH, LW, FH)))
    else:
        fronts = (char_from_webp(cid, 'top', False), char_from_webp(cid, 'bottom', False))
        backs = (char_from_webp(cid, 'top', True), char_from_webp(cid, 'bottom', True))
    for i, half in enumerate(('top', 'bottom')):
        f = fronts[i].copy(); d = ImageDraw.Draw(f)
        # 上半身の表だけ、隅に名前
        if half == 'top':
            name = CHAR_NAME[cid]; fnt = font(7, 'black'); tw = fnt.getlength(name) + int(3 * MM)
            d.rounded_rectangle((BL + SAFE, BL + SAFE, BL + SAFE + tw, BL + SAFE + int(5.2 * MM)), radius=int(1 * MM), fill=(255, 255, 255))
            d.text((BL + SAFE + int(1.5 * MM), BL + SAFE + int(0.9 * MM)), name, font=fnt, fill=INK)
        out[half] = (f, backs[i])
    return out


# ---------------------------------------------------------------- 早見表・タイトル
def quick_front():
    """クーの早見表にならった構成：上＝だれでもできる3アクション、下＝ガキカードごとのアクションと「は？」"""
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    pink = (184, 48, 106)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(2.5 * MM), outline=pink, width=int(0.5 * MM))
    # 見出し帯
    hb = int(6 * MM)
    d.rounded_rectangle((inner[0], inner[1], inner[2], inner[1] + hb), radius=int(2.5 * MM), fill=pink)
    d.rectangle((inner[0], inner[1] + hb // 2, inner[2], inner[1] + hb), fill=pink)
    text_center(d, PW / 2, inner[1] + int(1.2 * MM), 'アクション早見表', font(8.5, 'head'), fill=(255, 255, 255))
    x0 = inner[0] + int(1.6 * MM); x1 = inner[2] - int(1.6 * MM); wdt = x1 - x0
    y = inner[1] + hb + int(1.2 * MM)

    def section(label):
        nonlocal y
        d.text((x0, y), label, font=font(6, 'black'), fill=pink); y += int(3.6 * MM)

    AN = {k: v['name'] for k, v in ACTIONS.items()}
    name_w = max(font(7.5, 'black').getlength(AN[k]) for k in ('income', 'aid', 'coup')) + int(2 * MM)

    def general(name, eff, stop):
        nonlocal y
        cx = x0 + int(name_w); cw = x1 - cx
        el = wrap(eff, font(6), cw); sl = wrap(stop, font(5.5), cw)
        rh = int(0.8 * MM) + len(el) * int(font(6).size * 1.2) + len(sl) * int(font(5.5).size * 1.2) + int(0.8 * MM)
        d.rounded_rectangle((inner[0] + int(0.8 * MM), y - int(0.4 * MM), inner[2] - int(0.8 * MM), y + rh - int(0.5 * MM)), radius=int(0.8 * MM), fill=(250, 236, 243))
        d.text((x0, y + int(0.4 * MM)), name, font=font(7.5, 'black'), fill=INK)
        y2 = draw_text_block(d, (cx, y + int(0.2 * MM)), eff, font(6), cw, fill=INK, spacing=1.2)
        draw_text_block(d, (cx, y2), stop, font(5.5), cw, fill=DIM, spacing=1.2)
        y += rh + int(0.3 * MM)

    section('だれでもできる')
    general(AN['income'], '1♥もらう', '止められない')
    general(AN['aid'], '2♥もらう', 'は？：メスガキ')
    general(AN['coup'], f'{RULES.get("coupCost", 7)}♥で相手のプライドを1つ奪う', f'止められない。{RULES.get("forcedCoupAt", 10)}♥以上は必須')
    y += int(0.4 * MM)
    section('ガキカード（持ってなくても宣言OK＝ハッタリ）')
    rows = [
        ('mesugaki',    AN['tax'],      '3♥もらう',                      '',                           f"{AN['aid']} を止める"),
        ('kouhai',      AN['steal'],    '相手1人から2♥奪う',             'は？：後輩ガキ・幼馴染ガキ', f"{AN['steal']} を止める"),
        ('osananajimi', AN['exchange'], '山札から2枚引き、2枚捨てる',    '',                           f"{AN['steal']} を止める"),
        ('succu',       AN['assassinate'], '3♥払って相手のプライドを1つ奪う', 'は？：わからせおじさん', ''),
        ('ojisan',      '（アクションなし）', '',                           '',                           f"{AN['assassinate']} を止める"),
    ]
    for rid, act, eff, stop, blocks in rows:
        col = hexrgb(ROLES[rid]['color'])
        xr = x0 + int(2.2 * MM)
        line3 = (stop + '　' if stop else '') + ('｜ ' + blocks if stop and blocks else blocks)
        l3 = wrap(line3, font(5.5), x1 - xr)
        top3 = int(6.1 * MM) if eff else int(3.4 * MM)
        rh = top3 + len(l3) * int(font(5.5).size * 1.2) + int(1.3 * MM)
        d.rounded_rectangle((inner[0] + int(0.8 * MM), y - int(0.5 * MM), inner[2] - int(0.8 * MM), y + rh - int(1.2 * MM)), radius=int(0.8 * MM), fill=mix(col, (255, 255, 255), 0.9))
        d.rectangle((inner[0] + int(0.8 * MM), y - int(0.5 * MM), inner[0] + int(2.6 * MM), y + rh - int(1.2 * MM)), fill=col)
        d.text((xr, y), ROLES[rid]['name'], font=font(6.6, 'black'), fill=col)
        nx = xr + font(6.6, 'black').getlength(ROLES[rid]['name']) + int(2 * MM)
        d.text((nx, y - int(0.2 * MM)), act, font=font(7 if rid != 'ojisan' else 5.6, 'black'), fill=INK)
        if eff:
            d.text((xr, y + int(3.3 * MM)), eff, font=font(5.8), fill=INK)
        draw_text_block(d, (xr, y + top3), line3, font(5.5), x1 - xr, fill=DIM, spacing=1.2)
        y += rh
    return im


def quick_back():
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    navy = (60, 70, 130)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(2.5 * MM), outline=navy, width=int(0.5 * MM))
    hb = int(6 * MM)
    d.rounded_rectangle((inner[0], inner[1], inner[2], inner[1] + hb), radius=int(2.5 * MM), fill=navy)
    d.rectangle((inner[0], inner[1] + hb // 2, inner[2], inner[1] + hb), fill=navy)
    text_center(d, PW / 2, inner[1] + int(1.2 * MM), '手番の流れとプライド', font(8.5, 'head'), fill=(255, 255, 255))
    x0 = inner[0] + int(1.6 * MM); x1 = inner[2] - int(1.6 * MM); wdt = x1 - x0 - int(6 * MM); y = inner[1] + hb + int(1.6 * MM)
    secs = [
        ('1', '宣言', 'アクションを1つ宣言する。ガキカードのアクションは持っていなくても宣言できる（ハッタリ）。'),
        ('2', '割り込み', 'ほかの人は「ダウト！」か「は？」ができる。ダウト：ハッタリならその人、本物ならダウトした人がプライドを1つ失う。は？：ガキカードでブロック（これにもダウトできる）。'),
        ('3', '解決', f"通れば効果。止められたら不発。10♥以上なら手番で必ず {ACTIONS['coup']['name']}。"),
        ('♥', 'プライドを失ったら', '手札のガキカードを1枚捨てる → 失わせた相手が上半身・下半身どちらを脱がせるか選んで裏返す → その横のトリガーを表にして発動。'),
        ('★', '勝ち', f"上下とも裏返ったら脱落。最後の1人が勝ち。{TRIGGERS['t9']['name']}を持つ人は{RULES.get('collectorGoal', 9)}♥集めても勝ち。"),
    ]
    for no, h, body in secs:
        d.ellipse((x0, y, x0 + int(4.6 * MM), y + int(4.6 * MM)), fill=navy)
        text_center(d, x0 + int(2.3 * MM), y + int(0.6 * MM), no, font(6, 'black'), fill=(255, 255, 255))
        d.text((x0 + int(6 * MM), y), h, font=font(7, 'black'), fill=navy)
        y2 = draw_text_block(d, (x0 + int(6 * MM), y + int(4 * MM)), body, font(5.5), wdt, fill=INK, spacing=1.3)
        y = y2 + int(1.6 * MM)
    return im


def title_front():
    im = stripes(PW, PH, (56, 22, 60), (44, 16, 48), step=int(2.4 * MM)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE), radius=int(3 * MM), outline=(255, 95, 168), width=int(0.8 * MM))
    text_center(d, PW / 2, PH / 2 - int(26 * MM), '♥', font(26), fill=(255, 95, 168))
    text_center(d, PW / 2, PH / 2 - int(14 * MM), 'メスガキに「は？」', font(10.5, 'head'), fill=(255, 255, 255))
    text_center(d, PW / 2, PH / 2 - int(8 * MM), 'って言うゲーム', font(10.5, 'head'), fill=(255, 255, 255))
    text_center(d, PW / 2, PH / 2 - int(0.5 * MM), '～メスガキ・クー～', font(8.5, 'head'), fill=(255, 209, 102))
    text_center(d, PW / 2, PH / 2 + int(5.5 * MM), 'MESUGAKI COUP', font(6), fill=(217, 184, 230))
    text_center(d, PW / 2, PH / 2 + int(12 * MM), '3〜6人 ／ 15〜30分', font(7, 'black'), fill=(255, 209, 102))
    text_center(d, PW / 2, PH / 2 + int(18 * MM), 'ハッタリと「は？」でわからせ合う', font(6), fill=(217, 184, 230))
    return im


def title_back():
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), outline=(255, 95, 168), width=int(0.6 * MM))
    text_center(d, PW / 2, inner[1] + int(2.5 * MM), '内容物', font(9.5, 'head'), fill=(184, 48, 106))
    x0 = inner[0] + int(3 * MM); y = inner[1] + int(11 * MM)
    items = [('ガキカード', f'{len(ROLES) * 3}枚（5種×3）'), ('キャラカード', f'{len(PRINT_CHARS) * 2 * args.chara_copies}枚（{len(PRINT_CHARS)}キャラ×上下' + (f'×{args.chara_copies}組' if args.chara_copies > 1 else '') + '・両面）'),
             ('トリガーカード', f'{len(TRIG18)}枚' + (f'（ほかにハズレ{args.dud}枚' + (f'・白紙{args.blank}枚' if args.blank else '') + '）' if args.dud or args.blank else (f'（ほかに白紙{args.blank}枚）' if args.blank else ''))), ('早見表', f'{args.ref}枚'), ('タイトルカード', '1枚（この札）'), ('♥トークン', '50個（別途用意）'), ('ルールブック', '別紙')]
    vx = x0 + int(22 * MM); vw = inner[2] - int(3 * MM) - vx
    for n, v in items:
        d.text((x0, y), n, font=font(6.8, 'black'), fill=INK); y2 = draw_text_block(d, (vx, y + int(0.3 * MM)), v, font(5.6), vw, fill=DIM, spacing=1.25); y = max(y + int(6.2 * MM), y2 + int(1.2 * MM))
    draw_text_block(d, (x0, y + int(3 * MM)), 'トリガーは1ゲーム18枚（3〜6人に3枚ずつ配り、2枚を選んで仕込む）。基本・新カード・おすすめの各デッキの組み合わせはルールブック参照。', font(5.5), inner[2] - inner[0] - int(6 * MM), fill=DIM, spacing=1.4)
    return im


# ---------------------------------------------------------------- 生成
cards = []   # (番号, 種別, 名前, front, back, 向き)
n = 0
for rid in ROLES:
    for k in range(3):
        n += 1; cards.append((n, 'gaki', f'{ROLES[rid]["name"]}_{k + 1}', role_front(rid), role_back(), 'P'))
for cid in PRINT_CHARS:
    cc = char_cards(cid)
    for k in range(args.chara_copies):
        for half in ('top', 'bottom'):
            n += 1; cards.append((n, 'chara', f'{CHAR_NAME[cid]}_{"上" if half == "top" else "下"}' + (f'_{k + 1}' if args.chara_copies > 1 else ''), cc[half][0], cc[half][1], 'L'))
for tid in TRIG18:
    n += 1; cards.append((n, 'trigger', TRIGGERS[tid]['name'], trigger_front(tid), trigger_back(), 'P'))
for k in range(args.dud):
    n += 1; cards.append((n, 'trigger', f'ハズレ_{k + 1}', dud_front(), trigger_back(), 'P'))
qf, qb = quick_front(), quick_back()
for k in range(args.ref):
    n += 1; cards.append((n, 'ref', f'早見表_{k + 1}', qf, qb, 'P'))
for k in range(args.blank):
    n += 1; cards.append((n, 'blank', f'白紙トリガー_{k + 1}', blank_front(), trigger_back(), 'P'))
n += 1; cards.append((n, 'title', 'タイトル', title_front(), title_back(), 'P'))

if args.samples:
    picks = [cards[0], cards[12], cards[15], cards[16], next(c for c in cards if c[1] == 'trigger' and c[2] == 'おしおき返し'), next(c for c in cards if c[1] == 'trigger' and c[2] == '復讐の誓い'), next(c for c in cards if c[1] == 'ref'), cards[-1]]
    tiles = []
    for num, kind, name, f, b, ori in picks:
        for im in (f, b):
            t = trim_guides(im); h = 1100; t = t.resize((int(t.size[0] * h / t.size[1]), h)); tiles.append(t)
    W = sum(t.size[0] for t in tiles) + 12 * (len(tiles) + 1)
    sheet = Image.new('RGB', (W, 1100 + 24), (60, 60, 60)); x = 12
    for t in tiles:
        sheet.paste(t, (x, 12)); x += t.size[0] + 12
    sheet.save(os.path.join(OUT, 'samples.png'))
    print('samples ->', os.path.join(OUT, 'samples.png')); sys.exit(0)

for num, kind, name, f, b, ori in cards:
    base = f'{num:02d}_{kind}_{name}'.replace('/', '-')
    f.save(os.path.join(OUT, 'cards', base + '_front.png'), dpi=(args.dpi, args.dpi))
    b.save(os.path.join(OUT, 'cards', base + '_back.png'), dpi=(args.dpi, args.dpi))

# PDF（1ページ1面、表→裏の順）。ページサイズは塗り足し込み
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader
    pdf = os.path.join(OUT, 'mesugaki-coup_cards.pdf')
    c = rl_canvas.Canvas(pdf)
    for num, kind, name, f, b, ori in cards:
        for side, im in (('front', f), ('back', b)):
            w_pt, h_pt = im.size[0] / args.dpi * 72, im.size[1] / args.dpi * 72
            c.setPageSize((w_pt, h_pt))
            c.drawImage(ImageReader(im), 0, 0, w_pt, h_pt)
            c.showPage()
    c.save()
except ImportError:
    pdf = None

# プレビュー（仕上がり線つき）
th = 300
tiles = []
for num, kind, name, f, b, ori in cards:
    for im in (f, b):
        t = trim_guides(im); t.thumbnail((th, th)); tiles.append(t)
cols = 12
tw = th; rows_n = math.ceil(len(tiles) / cols)
sheet = Image.new('RGB', (cols * (tw + 8) + 8, rows_n * (th + 8) + 8), (30, 22, 36))
for i, t in enumerate(tiles):
    x = 8 + (i % cols) * (tw + 8); y = 8 + (i // cols) * (th + 8)
    sheet.paste(t, (x + (tw - t.size[0]) // 2, y + (th - t.size[1]) // 2))
sheet.save(os.path.join(OUT, 'preview.png'))

readme = f"""メスガキ・クー 物理版 印刷データ

仕上がり {TW_MM:g}×{TH_MM:g}mm、塗り足し各{B_MM:g}mm（データは {TW_MM + 2 * B_MM:g}×{TH_MM + 2 * B_MM:g}mm）、{args.dpi}dpi、RGB PNG。
cards/ に1枚ずつ、ファイル名の末尾 _front が表、_back が裏。mesugaki-coup_cards.pdf は同じ内容を1ページ1面で表→裏の順に並べたもの。
仕上がり線から内側 3mm に文字と枠を収めてある。preview.png の赤線が仕上がり線（印刷データには入っていない）。
キャラカード（{len(PRINT_CHARS) * 2 * args.chara_copies}枚）だけ横長。表裏は上下が同じ向き（長辺でめくる想定）。

枚数：ガキカード {len(ROLES) * 3}、キャラカード {len(PRINT_CHARS) * 2 * args.chara_copies}{f'（{len(PRINT_CHARS)}キャラ×上下×{args.chara_copies}組）' if args.chara_copies > 1 else ''}、トリガー {len(TRIG18)}{f'、ハズレ {args.dud}' if args.dud else ''}、早見表 {args.ref}{f'、白紙トリガー {args.blank}' if args.blank else ''}、タイトル 1 ＝ {len(cards)}枚
キャラ：{'・'.join(CHAR_NAME[c] for c in PRINT_CHARS)}
トリガー：{'・'.join(TRIGGERS[t]['name'] for t in TRIG18)}
"""
if args.lion:
    # ---- ライオン名刺 異種（21面）用：各面をテンプレートへ貼る向きに回転し、参考面付けも作る
    ldir = os.path.join(OUT, 'lion'); os.makedirs(ldir, exist_ok=True)
    SLOTS = 'ABCDEFGHIJKLMNOPQRSTU'
    sheets = [cards[i:i + 21] for i in range(0, len(cards), 21)]
    # 参考面付け：A3 縦（297×420mm）に 3列×7行、ピッチ＝仕上がり＋塗り足し2辺ぶん
    A3W, A3H = round(297 * MM), round(420 * MM)
    cell_w, cell_h = LW, LH                   # 横型の塗り足し込みサイズ（= 名刺1面）
    gx = (A3W - 3 * cell_w) // 2; gy = (A3H - 7 * cell_h) // 2
    mapping = ['番号,種別,名前,テンプレート,面(表),面(裏)']
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.utils import ImageReader
        lpdf = rl_canvas.Canvas(os.path.join(ldir, 'lion_sheets.pdf'))
    except ImportError:
        lpdf = None
    for si, sh in enumerate(sheets, 1):
        front = Image.new('RGB', (A3W, A3H), (255, 255, 255)); back = Image.new('RGB', (A3W, A3H), (255, 255, 255))
        for k, (num, kind, name, f, b, ori) in enumerate(sh):
            r, c = divmod(k, 3)
            if ori == 'P':   # 縦型：表は左へ90度、裏は右へ90度
                fi, bi = f.rotate(90, expand=True), b.rotate(-90, expand=True)
            else:            # 横型：そのまま
                fi, bi = f, b
            slot = SLOTS[k]
            fi.save(os.path.join(ldir, f'T{si}_{slot}_front.png'), dpi=(args.dpi, args.dpi))
            bi.save(os.path.join(ldir, f'T{si}_{slot}_back.png'), dpi=(args.dpi, args.dpi))
            front.paste(fi, (gx + c * cell_w, gy + r * cell_h))
            back.paste(bi, (gx + (2 - c) * cell_w, gy + r * cell_h))     # 裏は中央で鏡合わせ（列を反転）
            mapping.append(f'{num},{kind},{name},T{si},{slot},{SLOTS[r * 3 + (2 - c)]}の位置に{slot}')
        # 仕上がり線（参考。赤の点）
        for im in (front, back):
            d = ImageDraw.Draw(im)
            for r in range(8):
                for c in range(4):
                    x = gx + c * cell_w; y = gy + r * cell_h
                    d.rectangle((x - 3, y - 3, x + 3, y + 3), fill=(255, 0, 0))
        front.save(os.path.join(ldir, f'T{si}_front.png'), dpi=(args.dpi, args.dpi))
        back.save(os.path.join(ldir, f'T{si}_back.png'), dpi=(args.dpi, args.dpi))
        if lpdf:
            for im in (front, back):
                w_pt, h_pt = im.size[0] / args.dpi * 72, im.size[1] / args.dpi * 72
                lpdf.setPageSize((w_pt, h_pt)); lpdf.drawImage(ImageReader(im), 0, 0, w_pt, h_pt); lpdf.showPage()
    if lpdf:
        lpdf.save()
    open(os.path.join(ldir, 'slots.csv'), 'w', encoding='utf-8').write('\n'.join(mapping) + '\n')
    # ---- 公式テンプレート（AI = PDF互換）に貼り込む
    if args.template:
        import io
        from pypdf import PdfReader, PdfWriter
        tpl = PdfReader(args.template)
        assert len(tpl.pages) >= 2, 'テンプレートは表・裏の2ページ想定'
        import pdfplumber
        with pdfplumber.open(args.template) as pl:
            slots_pt = []
            for pg in pl.pages[:2]:
                H = pg.height
                rs = [r for r in pg.rects if abs(r['width'] / 72 * 25.4 - (TH_MM + 2 * B_MM)) < 0.8 and abs(r['height'] / 72 * 25.4 - (TW_MM + 2 * B_MM)) < 0.8]
                rs = sorted(rs, key=lambda r: (round(r['top']), r['x0']))      # 上の行から、左から
                assert len(rs) == 21, f'テンプレートに {TH_MM + 2 * B_MM:g}×{TW_MM + 2 * B_MM:g}mm の枠が21個見つからない（{len(rs)}個）'
                slots_pt.append([(r['x0'], H - r['bottom'], r['width'], r['height']) for r in rs])
        tw_pt, th_pt = float(tpl.pages[0].mediabox.width), float(tpl.pages[0].mediabox.height)
        import shutil
        from pypdf.generic import NameObject
        all_writer = PdfWriter()
        for si, sh in enumerate(sheets, 1):
            # テンプレートの文書を丸ごと複製（レイヤー＝OCProperties やページ枠はそのまま）
            writer = PdfWriter(clone_from=args.template)
            for side in (0, 1):
                buf = io.BytesIO(); c = rl_canvas.Canvas(buf, pagesize=(tw_pt, th_pt))
                for k, (num, kind, name, f, b, ori) in enumerate(sh):
                    r, col = divmod(k, 3)
                    if side == 0:
                        im = f.rotate(90, expand=True) if ori == 'P' else f
                        x, y, w, h = slots_pt[0][r * 3 + col]
                    else:
                        im = b.rotate(-90, expand=True) if ori == 'P' else b
                        x, y, w, h = slots_pt[1][r * 3 + (2 - col)]           # 裏は中央で鏡合わせ
                    c.drawImage(ImageReader(im), x, y, w, h)
                c.showPage(); c.save(); buf.seek(0)
                over = PdfReader(buf).pages[0]
                page = writer.pages[side]
                page.merge_page(over)
                # Illustrator の編集用データ（AIPrivateData）はテンプレートのものなので外す。
                # 残っていると Illustrator はそちらを開いてしまい、貼ったカードが出ない
                for key in ('/PieceInfo', '/LastModified'):
                    if key in page: del page[NameObject(key)]
            root = writer._root_object
            for key in ('/Metadata', '/PieceInfo'):
                if key in root: del root[NameObject(key)]
            writer.add_metadata({'/Producer': 'mesugaki-coup print_cards.py', '/Creator': 'mesugaki-coup print_cards.py (PDF-compatible AI, no Illustrator private data)', '/Title': f'mesugaki-coup lion T{si}'})
            pdf_path = os.path.join(ldir, f'template_T{si}.pdf')
            writer.write(pdf_path)
            shutil.copyfile(pdf_path, os.path.join(ldir, f'template_T{si}.ai'))   # PDF互換の .ai（編集データなし）
            # Illustrator は複数ページの PDF を開くとき既定で1ページ目しか読まないので、表・裏を1ページずつの .ai にも分ける
            for side, tag in ((0, 'front'), (1, 'back')):
                src = PdfReader(pdf_path); w1 = PdfWriter()
                w1.add_page(src.pages[side])                                   # そのページが使う画像だけが入る
                w1._root_object[NameObject('/OCProperties')] = src.trailer['/Root']['/OCProperties'].clone(w1)   # レイヤー定義を引き継ぐ
                w1.add_metadata({'/Producer': 'mesugaki-coup print_cards.py', '/Creator': 'mesugaki-coup print_cards.py (PDF-compatible AI, no Illustrator private data)', '/Title': f'mesugaki-coup lion T{si} {tag}'})
                w1.write(os.path.join(ldir, f'template_T{si}_{tag}.ai'))
            all_writer.append(pdf_path)
        all_writer.write(os.path.join(ldir, 'template_all.pdf'))
        readme_tpl = f'''
  template_T<n>.pdf / template_T<n>.ai：公式テンプレート（{os.path.basename(args.template)}）の表・裏ページに、各カードを面A〜Uの枠へ貼り込んだもの（テンプレートのトンボ・ガイド・レイヤーはそのまま）。
    .ai は同じ内容の PDF互換ファイル（Illustrator の編集データは含まない。テンプレート由来の編集データは、残すと Illustrator がそちらを開いてカードが出ないので外してある）。
    Illustrator で開くと PDF として読み込まれる。そのまま「別名で保存」すればネイティブの .ai になる。
  template_T<n>_front.ai / template_T<n>_back.ai：上の表ページ・裏ページを1ページずつに分けたもの。Illustrator は複数ページの PDF を開くとき既定で1ページ目しか読まないので、入稿はこちらが確実。
  template_all.pdf：上を全テンプレートぶん連結（表→裏→表→裏…）。
'''
    readme += f"""
[ライオン名刺 異種テンプレート用] lion/
  T<n>_<A-U>_front.png / _back.png：テンプレートの面 A〜U に貼る画像。縦型のカードは表を左90度・裏を右90度に回転済み、横型（キャラカード）はそのまま。
  いずれも塗り足し{B_MM:g}mm込みの {TH_MM + 2 * B_MM:g}×{TW_MM + 2 * B_MM:g}mm（横）。仕上がり線の内側3mmに文字を収めてある。
  T<n>_front.png / T<n>_back.png（lion_sheets.pdf）：参考の面付け（A3・3列×7行・ピッチ {TH_MM + 2 * B_MM:g}×{TW_MM + 2 * B_MM:g}mm・裏面は中央で鏡合わせ）。
  公式テンプレートの面の位置とは一致しない可能性があるので、入稿は公式テンプレートに T<n>_<面>_front/back.png を貼る形が確実。
  slots.csv：カード番号→テンプレート番号・面の対応表。{len(cards)}枚を {len(sheets)} 枚のテンプレート（21面ずつ）に割り当て。
"""
    if args.template:
        readme += readme_tpl
open(os.path.join(OUT, 'README.txt'), 'w', encoding='utf-8').write(readme)
print(f'{len(cards)} cards -> {OUT}  ({PW}x{PH}px portrait, {LW}x{LH}px landscape)', 'pdf ok' if pdf else 'no pdf (reportlab missing)')
