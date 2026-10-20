"""メスガキ・クー 物理版（52枚）の印刷データを作る。

usage: python3 -I print_cards.py --out <dir> [--art <元立ち絵dir>] [--size 91x55] [--bleed 1.5] [--dpi 350]
                                [--chars shiro,momoko,emera,oren,aqua,asagi] [--index ../index.html] [--lion]

--size は仕上がりの「長辺x短辺」でも「幅x高さ」でもよい。文字もののカードは短辺を幅にした縦型、メスガキカードは横型で作る。
--lion を付けると、ライオン名刺「異種（21面テンプレート）」用に、テンプレートへ貼る向きに回転した各面の画像
（lion/T<n>_<A-U>_front/back.png）と、参考の面付けシート（lion/T<n>_front.png / _back.png、A3・3列×7行・裏面は鏡合わせ）を出す。
  ・縦型のカード：表は左へ90度、裏は右へ90度回転（マニュアル「表裏共に縦型」）
  ・横型（メスガキカード）：回転なし
  ・裁ち落としは塗り足し1.5mm、文字は仕上がりから3mm内側

出力（<dir>/）
  cards/NN_<種別>_<名前>_front.png / _back.png  … 1枚ずつ、塗り足し込みのサイズ（既定 69×94mm @350dpi = 950×1295px）
  mesugaki-coup_cards.pdf                         … 1ページ1面、表→裏の順に104ページ（ページサイズも塗り足し込み）
  preview.png                                     … 全カードの表裏一覧
  README.txt                                      … 仕様とカード一覧

・ガキカード15（表5種×3、裏共通）、メスガキカード12（6キャラ×上下。表＝通常絵、裏＝ボロ絵の両面）、
  トリガー18（基本12＋おすすめデッキの新カード6。裏共通）、早見表6（表裏別）、タイトル1（表裏別）
・カード文言と枚数は index.html の定義（ROLES / ACTIONS / TRIGGERS / DECK_PRESETS）から読む。
・メスガキカードは横長（63×88 を横に使う）。元立ち絵（--art）が無いときはゲーム用 img/*.webp から作る（低解像度）。
"""
import sys, os, re, json, math, argparse, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--art', default=None, help='Bombergirl 立ち絵（<name>000.png 通常 / <name>001.jpg ボロ）のフォルダ')
ap.add_argument('--index', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html'))
ap.add_argument('--size', default='91x55', help='仕上がり mm（長辺x短辺）')
ap.add_argument('--bleed', type=float, default=1.5, help='塗り足し mm（各辺）')
ap.add_argument('--lion', action='store_true', help='ライオン名刺 異種テンプレート向けの回転済み画像と面付けシートも出す')
ap.add_argument('--dpi', type=int, default=350)
ap.add_argument('--chars', default='shiro,momoko,emera,oren,aqua,asagi', help='印刷するキャラ id を6つ')
ap.add_argument('--font', default=None, help='日本語フォント（TTF/OTF）。省略時は IPA ゴシックを探す')
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
# 横向きカード（メスガキカード）
LW, LH = PH, PW


def find_font():
    if args.font:
        return args.font
    for c in ['/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf', '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf',
              '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
              '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']:
        if os.path.exists(c):
            return c
    raise SystemExit('日本語フォントが見つからない。--font で指定してください')


FONT_PATH = find_font()
_fonts = {}


def font(pt):
    """pt はポイント指定。dpi に合わせて px に換算"""
    px = max(6, round(pt * args.dpi / 72))
    if px not in _fonts:
        _fonts[px] = ImageFont.truetype(FONT_PATH, px)
    return _fonts[px]


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
    TRIGGERS[m.group(1)] = dict(name=m.group(2), text=text, persistent='persistent:true' in m.group(5))
PRESETS = {}
for m in re.finditer(r"(basic|fresh|mix):\s*\[([^\]]*)\]", js_block('const DECK_PRESETS', 'const DECK_SIZE')):
    PRESETS[m.group(1)] = re.findall(r"'(t\d+)'", m.group(2))
CHARS = [(m.group(1), m.group(2)) for m in re.finditer(r"\{ id:'([a-z]+)',\s*name:'([^']+)' \}", js_block('const CHARS = [', '];'))]
CHAR_NAME = dict(CHARS)
PRINT_CHARS = [c for c in args.chars.split(',') if c]
assert all(c in CHAR_NAME for c in PRINT_CHARS), f'知らないキャラ id: {PRINT_CHARS}'
TRIG18 = []
for i in PRESETS['basic'] + PRESETS['mix']:
    if i not in TRIG18:
        TRIG18.append(i)

# ---------------------------------------------------------------- 描画ユーティリティ
INK = (40, 22, 48)
DIM = (120, 100, 125)
PAPER = (252, 247, 250)


def hexrgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def wrap(text, f, width):
    """日本語向けの文字単位折り返し（句読点の行頭は避ける）"""
    lines, cur = [], ''
    for ch in text:
        if ch == '\n':
            lines.append(cur); cur = ''; continue
        if f.getlength(cur + ch) > width and cur:
            if ch in '。、）」♥）':
                cur += ch; lines.append(cur); cur = ''; continue
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


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
    text_center(d, PW / 2, inner[1] + int(2.2 * MM), R['name'], font(15), fill=(255, 255, 255))
    text_center(d, PW / 2, inner[1] + int(8.6 * MM), 'GAKI CARD', font(6), fill=mix(col, (255, 255, 255), 0.75))
    # 大きなマーク（頭文字）
    text_center(d, PW / 2, inner[1] + hb + int(4 * MM), R['name'][0], font(60), fill=mix(col, PAPER, 0.78))
    y = inner[1] + hb + int(31 * MM)
    x0, wdt = inner[0] + int(3 * MM), inner[2] - inner[0] - int(6 * MM)
    # できる
    d.rounded_rectangle((inner[0] + int(2 * MM), y - int(1.5 * MM), inner[2] - int(2 * MM), y + int(15 * MM)), radius=int(1.5 * MM), fill=mix(col, (255, 255, 255), 0.9))
    d.text((x0, y), 'できる', font=font(7), fill=col)
    if R['action']:
        A = ACTIONS[R['action']]
        d.text((x0, y + int(3.4 * MM)), A['name'], font=font(11), fill=INK)
        draw_text_block(d, (x0, y + int(8.6 * MM)), A['desc'], font(6.5), wdt, fill=DIM)
    else:
        d.text((x0, y + int(3.4 * MM)), 'なし', font=font(11), fill=INK)
        draw_text_block(d, (x0, y + int(8.6 * MM)), 'アクションは持たない。ブロック専門', font(6.5), wdt, fill=DIM)
    y += int(17.5 * MM)
    # ブロック
    d.rounded_rectangle((inner[0] + int(2 * MM), y - int(1.5 * MM), inner[2] - int(2 * MM), y + int(13 * MM)), radius=int(1.5 * MM), fill=mix(col, (255, 255, 255), 0.9))
    d.text((x0, y), '「は？」ブロック', font=font(7), fill=col)
    blocks = '・'.join(ACTIONS[b]['name'] for b in R['blocks']) or 'なし'
    d.text((x0, y + int(3.4 * MM)), blocks, font=font(11 if len(blocks) < 12 else 9), fill=INK)
    draw_text_block(d, (x0, y + int(8.6 * MM)), f'「{R["line"]}」', font(6.5), wdt, fill=DIM)
    # 公開のひとこと
    text_center(d, PW / 2, inner[3] - int(7 * MM), f'公開：「{R["phrase"]}」', font(6), fill=DIM)
    text_center(d, PW / 2, inner[3] - int(3.6 * MM), 'メスガキ・クー', font(5), fill=mix(col, PAPER, 0.3))
    return im


def role_back():
    im = stripes(PW, PH, (76, 42, 94), (59, 31, 75), step=int(2.2 * MM)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE), radius=int(3 * MM), outline=(122, 74, 142), width=int(0.8 * MM))
    text_center(d, PW / 2, PH / 2 - int(14 * MM), '♥', font(44), fill=(217, 184, 230))
    text_center(d, PW / 2, PH / 2 + int(4 * MM), 'GAKI', font(14), fill=(217, 184, 230))
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
    name = T['name']; fs = 15 if len(name) <= 6 else 12 if len(name) <= 8 else 10
    text_center(d, PW / 2, inner[1] + int(8 * MM), name, font(fs), fill=(255, 255, 255))
    d.line((inner[0] + int(4 * MM), inner[1] + int(17 * MM), inner[2] - int(4 * MM), inner[1] + int(17 * MM)), fill=edge, width=int(0.4 * MM))
    # 常時／1回 の帯
    tag = '常時' if T['persistent'] else ('1回' if '（1回）' in T['text'] else '発動時')
    tw = font(6).getlength(tag) + int(4 * MM)
    d.rounded_rectangle((PW / 2 - tw / 2, inner[1] + int(19 * MM), PW / 2 + tw / 2, inner[1] + int(24.5 * MM)), radius=int(1 * MM), fill=(255, 209, 102) if T['persistent'] else edge)
    text_center(d, PW / 2, inner[1] + int(20 * MM), tag, font(6), fill=(58, 42, 0) if T['persistent'] else (255, 255, 255))
    # 効果文
    x0 = inner[0] + int(4 * MM); wdt = inner[2] - inner[0] - int(8 * MM)
    body = T['text'].replace('（1回）', '')
    fs = 8.5 if len(body) <= 40 else 7.5 if len(body) <= 60 else 6.8
    draw_text_block(d, (x0, inner[1] + int(29 * MM)), body, font(fs), wdt, fill=(230, 236, 255), spacing=1.45)
    # セット名
    sets = 'おすすめ' if tid in PRESETS['mix'] else ''
    base = '基本' if tid in PRESETS['basic'] else '新カード'
    text_center(d, PW / 2, inner[3] - int(7 * MM), base + ('／' + sets if sets else ''), font(5.5), fill=(138, 152, 214))
    text_center(d, PW / 2, inner[3] - int(3.6 * MM), 'メスガキ・クー', font(5), fill=(110, 120, 170))
    return im


def trigger_back():
    im = stripes(PW, PH, (43, 49, 72), (35, 40, 66), step=int(2.2 * MM)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE), radius=int(3 * MM), outline=(90, 106, 168), width=int(0.8 * MM))
    text_center(d, PW / 2, PH / 2 - int(6 * MM), 'TRIGGER', font(14), fill=(138, 152, 214))
    text_center(d, PW / 2, PH / 2 + int(3 * MM), 'メスガキ・クー', font(7), fill=(110, 120, 170))
    return im


# ---------------------------------------------------------------- メスガキカード（横長・両面）
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
    if args.art:
        for n in ALIAS.get(cid, [cid]):
            for ext in ('png', 'PNG'):
                p = os.path.join(args.art, f'{n}000.{ext}')
                if os.path.exists(p): src000 = p
            for ext in ('jpg', 'JPG', 'png'):
                p = os.path.join(args.art, f'{n}001.{ext}')
                if os.path.exists(p): src001 = p
    if src000 and src001:
        fc = char_front_canvas(src000, WAIST.get(cid, 0.5)); bc = char_back_canvas(src001, BORO_WAIST.get(cid, 0.5))
        fronts = (fc.crop((0, 0, LW, LH)), fc.crop((0, LH, LW, FH))); backs = (bc.crop((0, 0, LW, LH)), bc.crop((0, LH, LW, FH)))
    else:
        fronts = (char_from_webp(cid, 'top', False), char_from_webp(cid, 'bottom', False))
        backs = (char_from_webp(cid, 'top', True), char_from_webp(cid, 'bottom', True))
    for i, half in enumerate(('top', 'bottom')):
        f = fronts[i].copy(); d = ImageDraw.Draw(f)
        # 上半身の表だけ、隅に名前
        if half == 'top':
            name = CHAR_NAME[cid]; fnt = font(7); tw = fnt.getlength(name) + int(3 * MM)
            d.rounded_rectangle((BL + SAFE, BL + SAFE, BL + SAFE + tw, BL + SAFE + int(5.2 * MM)), radius=int(1 * MM), fill=(255, 255, 255))
            d.text((BL + SAFE + int(1.5 * MM), BL + SAFE + int(0.9 * MM)), name, font=fnt, fill=INK)
        out[half] = (f, backs[i])
    return out


# ---------------------------------------------------------------- 早見表・タイトル
def quick_front():
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), outline=(255, 95, 168), width=int(0.6 * MM))
    text_center(d, PW / 2, inner[1] + int(2.5 * MM), 'アクション早見表', font(10), fill=(184, 48, 106))
    y = inner[1] + int(9 * MM); x0 = inner[0] + int(2 * MM); wdt = inner[2] - inner[0] - int(4 * MM)
    rows = [
        ('ふ～ん♥', 'なし', '1♥獲得', 'ブロック不可・チャレンジ不可'),
        ('よわ♥', 'なし', '2♥獲得', 'は？：メスガキ'),
        ('ざぁ～こ♥', f'{RULES.get("coupCost", 7)}♥（{RULES.get("forcedCoupAt", 10)}♥以上は必須）', '相手のプライドを1つ奪う', 'ブロック不可・チャレンジ不可'),
        ('よわよわ～♥', 'メスガキ', '3♥獲得', 'チャレンジ可'),
        ('なさけな～い♥', '後輩ガキ', '相手から2♥奪う', 'は？：後輩ガキ・幼馴染ガキ'),
        ('ダサすぎ♥', '幼馴染ガキ', '山札から2枚引き、2枚捨てる', 'チャレンジ可'),
        ('まけちゃえ～♥', 'サキュガキ＋3♥', '相手のプライドを1つ奪う', 'は？：わからせおじさん'),
    ]
    colx = x0 + int(22 * MM); colw = inner[2] - int(2 * MM) - colx; lw = int(21 * MM)
    for i, (n, cond, eff, blk) in enumerate(rows):
        if i % 2 == 0:
            d.rectangle((inner[0] + int(1 * MM), y - int(0.8 * MM), inner[2] - int(1 * MM), y + int(8.6 * MM)), fill=(250, 236, 243))
        d.text((x0, y), n, font=font(7.5), fill=(184, 48, 106))
        draw_text_block(d, (colx, y + int(0.3 * MM)), cond, font(5), colw, fill=DIM, spacing=1.2)
        draw_text_block(d, (x0, y + int(4.2 * MM)), eff, font(5.4), lw, fill=INK, spacing=1.2)
        draw_text_block(d, (colx, y + int(4.4 * MM)), blk, font(4.8), colw, fill=DIM, spacing=1.2)
        y += int(9.8 * MM)
    draw_text_block(d, (x0, y + int(1 * MM)), '役職つきのアクションは持っていなくても宣言できる（ハッタリ）。チャレンジされて持っていなければプライドを1つ失う。本当に持っていればチャレンジした側が失い、公開した札は捨て札にして山札から引き直す。', font(5.2), wdt, fill=DIM, spacing=1.4)
    return im


def quick_back():
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), outline=(90, 106, 168), width=int(0.6 * MM))
    text_center(d, PW / 2, inner[1] + int(2.5 * MM), '手番とプライド', font(10), fill=(60, 70, 130))
    x0 = inner[0] + int(2.5 * MM); wdt = inner[2] - inner[0] - int(5 * MM); y = inner[1] + int(10 * MM)
    secs = [
        ('準備', f'メスガキカードを上下に置き、ガキカード2枚を伏せ、トリガー2枚を上下に1枚ずつ伏せる。全員2♥。'),
        ('手番', '①アクションを1つ宣言 ②ほかの人がチャレンジ／「は？」ブロック ③通れば解決。'),
        ('プライドを失ったら', '①手札のガキカードを1枚捨てる ②失わせた相手が上半身・下半身どちらを脱がせるか選び、裏返してボロ絵に ③その横のトリガーを表にして発動。'),
        ('脱落・勝利', '上下とも裏返ったら脱落。最後の1人が勝ち。♥コレクターを持つ人は9♥集めても勝ち。'),
    ]
    for h, body in secs:
        d.text((x0, y), h, font=font(7.5), fill=(60, 70, 130)); y += int(4.2 * MM)
        y = draw_text_block(d, (x0, y), body, font(6), wdt, fill=INK, spacing=1.4) + int(2.2 * MM)
    return im


def title_front():
    im = stripes(PW, PH, (56, 22, 60), (44, 16, 48), step=int(2.4 * MM)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE), radius=int(3 * MM), outline=(255, 95, 168), width=int(0.8 * MM))
    text_center(d, PW / 2, PH / 2 - int(22 * MM), '♥', font(30), fill=(255, 95, 168))
    text_center(d, PW / 2, PH / 2 - int(9 * MM), 'メスガキ・クー', font(17), fill=(255, 255, 255))
    text_center(d, PW / 2, PH / 2 + int(1 * MM), 'MESUGAKI COUP', font(7), fill=(217, 184, 230))
    text_center(d, PW / 2, PH / 2 + int(12 * MM), '3〜6人 ／ 15〜30分', font(7), fill=(255, 209, 102))
    text_center(d, PW / 2, PH / 2 + int(18 * MM), 'ハッタリと「は？」でわからせ合う', font(6), fill=(217, 184, 230))
    return im


def title_back():
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    inner = (BL + SAFE, BL + SAFE, PW - BL - SAFE, PH - BL - SAFE)
    d.rounded_rectangle(inner, radius=int(3 * MM), outline=(255, 95, 168), width=int(0.6 * MM))
    text_center(d, PW / 2, inner[1] + int(2.5 * MM), '内容物', font(10), fill=(184, 48, 106))
    x0 = inner[0] + int(3 * MM); y = inner[1] + int(11 * MM)
    items = [('ガキカード', f'{len(ROLES) * 3}枚（5種×3）'), ('メスガキカード', f'{len(PRINT_CHARS) * 2}枚（{len(PRINT_CHARS)}キャラ×上下・両面）'),
             ('トリガーカード', f'{len(TRIG18)}枚'), ('早見表', '6枚'), ('タイトルカード', '1枚（この札）'), ('♥トークン', '50個（別途用意）'), ('ルールブック', '別紙')]
    vx = x0 + int(22 * MM); vw = inner[2] - int(3 * MM) - vx
    for n, v in items:
        d.text((x0, y), n, font=font(6.8), fill=INK); y2 = draw_text_block(d, (vx, y + int(0.3 * MM)), v, font(5.6), vw, fill=DIM, spacing=1.25); y = max(y + int(6.2 * MM), y2 + int(1.2 * MM))
    draw_text_block(d, (x0, y + int(3 * MM)), 'トリガーは「基本デッキ」12枚か「おすすめデッキ」12枚のどちらかを使う（組み合わせは早見表の裏とルールブック参照）。', font(5.5), inner[2] - inner[0] - int(6 * MM), fill=DIM, spacing=1.4)
    return im


# ---------------------------------------------------------------- 生成
cards = []   # (番号, 種別, 名前, front, back, 向き)
n = 0
for rid in ROLES:
    for k in range(3):
        n += 1; cards.append((n, 'gaki', f'{ROLES[rid]["name"]}_{k + 1}', role_front(rid), role_back(), 'P'))
for cid in PRINT_CHARS:
    cc = char_cards(cid)
    for half in ('top', 'bottom'):
        n += 1; cards.append((n, 'chara', f'{CHAR_NAME[cid]}_{"上" if half == "top" else "下"}', cc[half][0], cc[half][1], 'L'))
for tid in TRIG18:
    n += 1; cards.append((n, 'trigger', TRIGGERS[tid]['name'], trigger_front(tid), trigger_back(), 'P'))
qf, qb = quick_front(), quick_back()
for k in range(6):
    n += 1; cards.append((n, 'ref', f'早見表_{k + 1}', qf, qb, 'P'))
n += 1; cards.append((n, 'title', 'タイトル', title_front(), title_back(), 'P'))

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
メスガキカード（{len(PRINT_CHARS) * 2}枚）だけ横長。表裏は上下が同じ向き（長辺でめくる想定）。

枚数：ガキカード {len(ROLES) * 3}、メスガキカード {len(PRINT_CHARS) * 2}、トリガー {len(TRIG18)}、早見表 6、タイトル 1 ＝ {len(cards)}枚
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
    readme += f"""
[ライオン名刺 異種テンプレート用] lion/
  T<n>_<A-U>_front.png / _back.png：テンプレートの面 A〜U に貼る画像。縦型のカードは表を左90度・裏を右90度に回転済み、横型（メスガキカード）はそのまま。
  いずれも塗り足し{B_MM:g}mm込みの {TH_MM + 2 * B_MM:g}×{TW_MM + 2 * B_MM:g}mm（横）。仕上がり線の内側3mmに文字を収めてある。
  T<n>_front.png / T<n>_back.png（lion_sheets.pdf）：参考の面付け（A3・3列×7行・ピッチ {TH_MM + 2 * B_MM:g}×{TW_MM + 2 * B_MM:g}mm・裏面は中央で鏡合わせ）。
  公式テンプレートの面の位置とは一致しない可能性があるので、入稿は公式テンプレートに T<n>_<面>_front/back.png を貼る形が確実。
  slots.csv：カード番号→テンプレート番号・面の対応表。{len(cards)}枚を {len(sheets)} 枚のテンプレート（21面ずつ）に割り当て。
"""
open(os.path.join(OUT, 'README.txt'), 'w', encoding='utf-8').write(readme)
print(f'{len(cards)} cards -> {OUT}  ({PW}x{PH}px portrait, {LW}x{LH}px landscape)', 'pdf ok' if pdf else 'no pdf (reportlab missing)')
