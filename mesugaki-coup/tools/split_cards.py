"""Bombergirl 立ち絵を上下2枚のカードに分割し、表=通常(000)/裏=ボロ(001) のセットを作る。

usage: python3 -I split_cards.py <src_dir> <out_dir>
"""
import sys, os, re, glob, math
from PIL import Image, ImageDraw, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

# カード1枚 = 88×63mm 横向き @300dpi。2枚を縦に重ねると全身の1キャンバス
CW, CH = 1040, 744
FW, FH = CW, CH * 2
MARGIN = 44
BORO_CROP = (20 / 425, 40 / 600, 405 / 425, 560 / 600)  # ロゴと©表記を外す相対クロップ

ALIAS = {'grimaroe': 'grimaloe'}

# 腰の高さ（人物範囲の上端=0, 下端=1）。ここがカードの境目に来るように配置する
WAIST = {'aqua': 0.46, 'asagi': 0.44, 'emera': 0.45, 'grimaloe': 0.46, 'momoko': 0.47, 'oren': 0.48,
         'papuru': 0.50, 'sepia': 0.45, 'shiro': 0.47, 'tsugaru': 0.47, 'urushi': 0.50}
# ボロ絵（クロップ後の高さに対する腰の位置）
BORO_WAIST = {'oren': 0.53, 'tsugaru': 0.53, 'sepia': 0.48, 'shiro': 0.52}


def key_of(fn):
    m = re.match(r'([a-z]+)(\d{3})\.(png|jpg)$', fn, re.I)
    if not m:
        return None
    name = ALIAS.get(m.group(1).lower(), m.group(1).lower())
    return name, m.group(2)


def figure_bbox(im):
    """透過PNGの人物範囲。最下段の©表記（全画像共通で y=741-751, x=221-541）は消してから測る。"""
    a = im.split()[-1]
    w, h = a.size
    if (w, h) == (760, 760):
        band = a.crop((215, 741, 546, 752))
        if band.getbbox():
            a.paste(0, (215, 741, 546, 752))
            im.putalpha(a)
    return a.getbbox()


def tint_of(im, bb):
    sub = im.crop(bb).convert('RGBA').resize((40, 40))
    r = g = b = n = 0
    for p in list(sub.get_flattened_data()) if hasattr(sub, 'get_flattened_data') else sub.getdata():
        if p[3] > 200:
            r += p[0]; g += p[1]; b += p[2]; n += 1
    if not n:
        return (200, 205, 215)
    return (r // n, g // n, b // n)


def radial_bg(w, h, tint):
    """白→淡い色の放射グラデーション（印刷向け）。"""
    small = Image.new('RGB', (w // 8, h // 8))
    px = small.load()
    cx, cy = small.size[0] / 2, small.size[1] / 2
    rmax = math.hypot(cx, cy)
    edge = tuple(int(255 * 0.80 + c * 0.20) for c in tint)
    for y in range(small.size[1]):
        for x in range(small.size[0]):
            t = min(1.0, math.hypot(x - cx, y - cy) / rmax)
            t = t * t
            px[x, y] = tuple(int(255 * (1 - t) + e * t) for e in edge)
    return small.resize((w, h), Image.BICUBIC)


def front_canvas(path, waist=0.5):
    im = Image.open(path).convert('RGBA')
    bb = figure_bbox(im)
    fig = im.crop(bb)
    fw, fh = fig.size
    # 上半分(腰まで)と下半分(腰から)がそれぞれ1枚に収まる倍率
    scale = min((FW - 2 * MARGIN) / fw, (CH - MARGIN) / (fh * waist), (CH - MARGIN) / (fh * (1 - waist)))
    fig = fig.resize((max(1, int(fw * scale)), max(1, int(fh * scale))), Image.LANCZOS)
    bg = radial_bg(FW, FH, tint_of(im, bb)).convert('RGBA')
    # 足元に薄い影
    shadow = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sw = int(fig.size[0] * 0.55)
    sx = (FW - sw) // 2
    sy = int(FH / 2 - fig.size[1] * waist) + fig.size[1] - 18
    sd.ellipse((sx, sy - 22, sx + sw, sy + 22), fill=(40, 30, 50, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    bg.alpha_composite(shadow)
    x = (FW - fig.size[0]) // 2
    y = int(FH / 2 - fig.size[1] * waist)   # 腰を境目に
    bg.alpha_composite(fig, (x, y))
    return bg.convert('RGB')


def back_canvas(path, waist=0.5):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    l, t, r, b = BORO_CROP
    im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
    cw, ch = im.size
    # 腰を中央にしても窓が画像外に出ない倍率まで寄せる
    scale = max(FW / cw, FH / ch, FH / (ch * 2 * min(waist, 1 - waist)))
    im = im.resize((int(cw * scale) + 1, int(ch * scale) + 1), Image.LANCZOS)
    x = (im.size[0] - FW) // 2
    y = int(im.size[1] * waist - FH / 2)
    y = max(0, min(y, im.size[1] - FH))
    return im.crop((x, y, x + FW, y + FH))


def split(canvas):
    return canvas.crop((0, 0, CW, CH)), canvas.crop((0, CH, CW, FH))


files = {}
for f in sorted(os.listdir(SRC)):
    k = key_of(f)
    if k:
        files.setdefault(k[0], {})[k[1]] = os.path.join(SRC, f)

cards = {}   # name -> {'top':{'000':img,'001':img}, 'bottom':{...}}
for name, d in sorted(files.items()):
    cards[name] = {'top': {}, 'bottom': {}}
    if '000' in d:
        top, bot = split(front_canvas(d['000'], WAIST.get(name, 0.5)))
        cards[name]['top']['000'] = top; cards[name]['bottom']['000'] = bot
    if '001' in d:
        top, bot = split(back_canvas(d['001'], BORO_WAIST.get(name, 0.5)))
        cards[name]['top']['001'] = top; cards[name]['bottom']['001'] = bot
    for half in ('top', 'bottom'):
        for side, img in cards[name][half].items():
            img.save(os.path.join(OUT, f'{name}_{half}_{side}.png'), optimize=True)
    print(name, 'ok' if ('000' in d and '001' in d) else f'only {list(d)}')

# ---- プレビュー（1キャラ=表上/表下/裏上/裏下 を並べる）----
names = sorted(cards)
th = 180
tw = int(CW * th / CH)
cols = 4
sheet = Image.new('RGB', (cols * (tw + 10) + 10 + 160, len(names) * (th + 10) + 10), (30, 22, 36))
dr = ImageDraw.Draw(sheet)
for i, name in enumerate(names):
    y = 10 + i * (th + 10)
    dr.text((10, y + th // 2 - 6), name, fill=(240, 230, 240))
    for j, (half, side) in enumerate([('top', '000'), ('bottom', '000'), ('top', '001'), ('bottom', '001')]):
        img = cards[name][half].get(side)
        x = 160 + 10 + j * (tw + 10)
        if img:
            sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, y))
        else:
            dr.rectangle((x, y, x + tw, y + th), outline=(90, 70, 100))
sheet.save(os.path.join(OUT, '_preview.png'))

# ---- 両面印刷用 A4 シート（300dpi, 2列×4行=8枚/面、裏面は左右を入れ替え）----
A4W, A4H = 2480, 3508
GAP = 24
per_sheet = 8
items = []
for name in names:
    for half in ('top', 'bottom'):
        if '000' in cards[name][half] and '001' in cards[name][half]:
            items.append((name, half))
colsN, rowsN = 2, 4
gw = colsN * CW + (colsN - 1) * GAP
gh = rowsN * CH + (rowsN - 1) * GAP
ox, oy = (A4W - gw) // 2, (A4H - gh) // 2
for s in range(0, len(items), per_sheet):
    chunk = items[s:s + per_sheet]
    for side in ('000', '001'):
        page = Image.new('RGB', (A4W, A4H), (255, 255, 255))
        d = ImageDraw.Draw(page)
        for idx, (name, half) in enumerate(chunk):
            r, c = divmod(idx, colsN)
            if side == '001':
                c = colsN - 1 - c   # 裏面は鏡像配置
            x = ox + c * (CW + GAP); y = oy + r * (CH + GAP)
            page.paste(cards[name][half][side], (x, y))
            # トンボ（カット線）
            for (px, py) in [(x, y), (x + CW, y), (x, y + CH), (x + CW, y + CH)]:
                d.line((px - 30, py, px - 8, py), fill=(120, 120, 120), width=2)
                d.line((px + 8, py, px + 30, py), fill=(120, 120, 120), width=2)
                d.line((px, py - 30, px, py - 8), fill=(120, 120, 120), width=2)
                d.line((px, py + 8, px, py + 30), fill=(120, 120, 120), width=2)
        label = f'sheet{s // per_sheet + 1}_{"front" if side == "000" else "back"}'
        d.text((ox, oy - 40), f'{label}  ({"front = normal" if side == "000" else "back = boro, mirrored columns for duplex"})', fill=(100, 100, 100))
        page.save(os.path.join(OUT, f'_print_{label}.png'), dpi=(300, 300))
print('done', len(items), 'cards')
