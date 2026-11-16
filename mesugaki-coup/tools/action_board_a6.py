#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A6（105×148mm）のアクションボードと手番マーカーを作る。

  python3 tools/action_board_a6.py --out <dir> [--index index.html] [--chars momoko,aqua,...] [--dpi 350]

出力（<dir>/）：
  board_a6_front.png … 表：7つのアクションを1段ずつ。左端の丸が手番マーカーの置き場
  board_a6_back.png  … 裏：手番の流れ・ダウトの結果・プライドを失ったとき・勝ち
  markers_a6.png     … 手番マーカー（キャラの顔の丸いトークン。切り取って使う）
  action_board_a6.pdf … 上の3枚をA6のページにしたもの（家庭用プリンタで両面印刷→十字に四つ折りで箱に入る）
A6を十字に四つ折りにすると 52.5×74mm。名刺サイズの箱にもトランプの箱にも入る。
"""
import os, re, sys, math, argparse, importlib.util
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--index', default=os.path.join(HERE, '..', 'index.html'))
ap.add_argument('--chars', default='momoko,aqua,grimaloe,shiro,pin,kuro', help='手番マーカーにするキャラ id')
ap.add_argument('--copies', type=int, default=3, help='キャラごとのマーカー枚数')
ap.add_argument('--dpi', type=int, default=350)
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

MM = args.dpi / 25.4
PW, PH = round(105 * MM), round(148 * MM)      # A6 縦
M = round(5 * MM)                                # 余白（家庭用プリンタ想定）
INK = (40, 22, 48); DIM = (120, 100, 125); PAPER = (255, 255, 255); GOLD = (255, 209, 102)
FREE = (120, 90, 130)
FONTS = {'body': os.path.join(HERE, 'fonts', 'MPLUS1p-Bold.ttf'), 'head': os.path.join(HERE, 'fonts', 'DelaGothicOne-Regular.ttf'), 'black': os.path.join(HERE, 'fonts', 'MPLUS1p-Black.ttf')}
_fonts = {}
def font(pt, kind='body'):
    px = max(6, round(pt * args.dpi / 72)); key = (kind, px)
    if key not in _fonts: _fonts[key] = ImageFont.truetype(FONTS[kind], px)
    return _fonts[key]
def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def mix(a, b, t): return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))

# ---- ゲーム定義
src = open(args.index, encoding='utf-8').read()
def js_block(start, end):
    i = src.find(start); j = src.find(end, i); return src[i:j]
ROLES = {}
for m in re.finditer(r"(\w+):\s*\{ id:'(\w+)',\s*name:'([^']+)',\s*action:(?:'(\w+)'|null),\s*blocks:\[([^\]]*)\],\s*line:'([^']+)',\s*phrase:'([^']+)',\s*color:'(#[0-9a-fA-F]{6})'", js_block('const ROLES = {', '};')):
    ROLES[m.group(1)] = dict(name=m.group(3), action=m.group(4), blocks=re.findall(r"'(\w+)'", m.group(5)), line=m.group(6), color=m.group(8))
ACTIONS = {}
for m in re.finditer(r"\{ id:'(\w+)',\s*name:'([^']+)',(?:\s*role:'(\w+)',)?\s*desc:'([^']+)'(.*?)\}", js_block('const ACTIONS = {', '};')):
    rest = m.group(5)
    ACTIONS[m.group(1)] = dict(name=m.group(2), role=m.group(3), desc=m.group(4), cost=int(re.search(r'cost:(\d+)', rest).group(1)) if re.search(r'cost:(\d+)', rest) else 0,
                               blockedBy=re.findall(r"'(\w+)'", re.search(r'blockedBy:\[([^\]]*)\]', rest).group(1)) if 'blockedBy' in rest else [])
RULES = {k: int(v) for k, v in re.findall(r"(\w+):\s*(\d+),", js_block('const RULES = {', '};'))}
CHARS = dict(re.findall(r"\{ id:'([a-z]+)',\s*name:'([^']+)' \}", js_block('const CHARS = [', '];')))
ORDER = ['income', 'aid', 'coup', 'tax', 'steal', 'exchange', 'assassinate']

# ---- 文字
NO_START = '。、，．）」』】〕〉》♥♡～〜ー！？…・)]'; NO_END = '「『（【〔〈《(['; PAIRS = {'「': '」', '（': '）'}
def _tokens(text, f, width):
    words = sorted({v['name'] for v in ACTIONS.values()} | {'止められない', '止められる', 'ダウト：あり', 'ダウトもなし'}, key=len, reverse=True); out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch in PAIRS:
            j = text.find(PAIRS[ch], i)
            if j != -1 and j - i <= 12 and f.getlength(text[i:j + 1]) <= width * 0.8: out.append(text[i:j + 1]); i = j + 1; continue
        w = next((w for w in words if text.startswith(w, i)), None)
        if w and f.getlength(w) <= width * 0.8: out.append(w); i += len(w); continue
        out.append(ch); i += 1
    return out
def wrap(text, f, width):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for t in _tokens(para, f, width):
            if cur and f.getlength(cur + t) > width:
                if len(t) == 1 and t in NO_START:
                    if len(cur) >= 2 and cur[-1] not in NO_START and cur[-1] not in NO_END: lines.append(cur[:-1]); cur = cur[-1] + t
                    else: cur += t
                    continue
                if cur[-1] in NO_END and len(cur) >= 2: lines.append(cur[:-1]); cur = cur[-1] + t; continue
                lines.append(cur); cur = t
            else: cur += t
        lines.append(cur)
    return lines
def block(d, xy, text, f, width, fill=INK, spacing=1.3):
    x, y = xy; lh = int(f.size * spacing)
    for ln in wrap(text, f, width): d.text((x, y), ln, font=f, fill=fill); y += lh
    return y
def center(d, cx, y, text, f, fill=INK): d.text((cx - f.getlength(text) / 2, y), text, font=f, fill=fill)
def blockers(aid):
    A = ACTIONS[aid]
    if aid == 'coup': return '止められない。ダウトもなし'
    if aid == 'aid': return f'「{ROLES["mesugaki"]["name"]}」のカードを持つ人なら誰でも止められる'
    if A['blockedBy']: return '狙われた人が' + 'か'.join(f'「{ROLES[r]["name"]}」' for r in A['blockedBy']) + 'のカードで止められる'
    return '止められない'

# ---- 表：アクションボード
def board_front():
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    pink = (255, 95, 168)
    d.rounded_rectangle((M, M, PW - M, M + int(15 * MM)), radius=int(2 * MM), fill=(56, 22, 60))
    d.text((M + int(3 * MM), M + int(1.5 * MM)), 'ACTION BOARD', font=font(6), fill=GOLD)
    d.text((PW - M - int(3 * MM) - font(5).getlength('メスガキ・クー'), M + int(1.8 * MM)), 'メスガキ・クー', font=font(5), fill=(217, 184, 230))
    d.text((M + int(3 * MM), M + int(4.5 * MM)), 'アクションボード', font=font(13, 'head'), fill=(255, 255, 255))
    d.text((M + int(3 * MM), M + int(10.6 * MM)), '宣言したら、自分の手番マーカーをその段の丸に置く。カードの技は、持っていなくても宣言できる（ハッタリ）', font=font(5.2), fill=(217, 184, 230))
    y = M + int(17.5 * MM); rh = int(16.5 * MM); gap = int(0.8 * MM)
    for aid in ORDER:
        A = ACTIONS[aid]; R = ROLES[A['role']] if A['role'] else None
        col = hexrgb(R['color']) if R else FREE
        d.rounded_rectangle((M, y, PW - M, y + rh), radius=int(2 * MM), fill=mix(col, (255, 255, 255), 0.9), outline=col, width=int(0.4 * MM))
        # マーカー置き場（左の丸）
        cx, cy, r = M + int(10 * MM), y + rh / 2, int(7.2 * MM)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=col, width=int(0.4 * MM))
        for k in range(0, 360, 24):   # 点線風
            a0 = math.radians(k); a1 = math.radians(k + 12)
            d.arc((cx - r + int(0.9 * MM), cy - r + int(0.9 * MM), cx + r - int(0.9 * MM), cy + r - int(0.9 * MM)), k, k + 12, fill=mix(col, (255, 255, 255), 0.4), width=int(0.35 * MM))
        center(d, cx, cy - int(2.6 * MM), '手番', font(5.5, 'black'), fill=mix(col, (255, 255, 255), 0.25))
        center(d, cx, cy + int(0.4 * MM), 'マーカー', font(4), fill=mix(col, (255, 255, 255), 0.35))
        # 名前・コスト
        x0 = M + int(20 * MM); xr = PW - M - int(2 * MM)
        d.rounded_rectangle((x0, y + int(1.2 * MM), x0 + int(34 * MM), y + int(7.6 * MM)), radius=int(1.2 * MM), fill=col)
        nf = font(10 if len(A['name']) <= 6 else 8.5, 'head'); d.text((x0 + int(1.8 * MM), y + int(1.9 * MM)), A['name'], font=nf, fill=(255, 255, 255))
        cost = A['cost'] or (RULES.get('coupCost', 7) if aid == 'coup' else 0)
        tx = x0 + int(36 * MM)
        if cost:
            d.rounded_rectangle((tx, y + int(1.8 * MM), tx + int(11 * MM), y + int(7 * MM)), radius=int(1 * MM), fill=(255, 255, 255), outline=col, width=int(0.3 * MM))
            center(d, tx + int(5.5 * MM), y + int(2.6 * MM), f'{cost}♥', font(7, 'black'), fill=col); tx += int(12.5 * MM)
        need = f'「{R["name"]}」のカード' if R else '誰でも'
        d.text((tx, y + int(2.8 * MM)), need, font=font(5.5, 'black'), fill=col)
        # 効果・は？
        wdt = xr - x0 - (int(18 * MM) if R else 0)
        eff = A['desc'] + (f'。{RULES.get("forcedCoupAt", 10)}♥以上なら必ず' if aid == 'coup' else '')
        yy = block(d, (x0, y + int(8.6 * MM)), eff, font(6), wdt, fill=INK, spacing=1.25)
        block(d, (x0, yy + int(0.2 * MM)), 'は？：' + blockers(aid) + ('　ダウト：あり' if R else ''), font(5), wdt, fill=DIM, spacing=1.25)
        if R:
            art = os.path.join(os.path.dirname(os.path.abspath(args.index)), 'img', 'roles', f'{A["role"]}.png')
            if os.path.exists(art):
                pic = Image.open(art).convert('RGBA'); ph = int(10 * MM); sc_ = min(ph / pic.size[1], int(15 * MM) / pic.size[0]); pic = pic.resize((max(1, int(pic.size[0] * sc_)), max(1, int(pic.size[1] * sc_))), Image.LANCZOS)
                im.paste(pic, (xr - pic.size[0], y + rh - int(0.8 * MM) - pic.size[1]), pic); d = ImageDraw.Draw(im)
        y += rh + gap
    return im

# ---- 裏：手番の流れなど
def board_back():
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    navy = (60, 70, 130)
    d.rounded_rectangle((M, M, PW - M, M + int(10 * MM)), radius=int(2 * MM), fill=navy)
    d.text((M + int(3 * MM), M + int(2.2 * MM)), '手番の流れとプライド', font=font(11, 'head'), fill=(255, 255, 255))
    x0 = M + int(2 * MM); wdt = PW - 2 * M - int(4 * MM); y = M + int(13 * MM)
    secs = [
        ('1', '宣言', 'アクションを1つ宣言する。カードの技は、そのカードを持っていなくても宣言できる（ハッタリ）。'),
        ('2', '割り込み', 'ほかの人は「ダウト！」か「は？」ブロックができる。ブロックにもダウトできる。'),
        ('3', '解決', f"通れば効果。止められたら不発で、払った♥は戻らない。{RULES.get('forcedCoupAt', 10)}♥以上で手番が来たら必ず {ACTIONS['coup']['name']}。"),
        ('？', 'ダウトの結果', '本物：公開して捨て札にし、山札から引き直す。ダウトした人がプライドを1つ失う。アクションは通る。\nハッタリ：宣言した人がプライドを1つ失い、アクション（ブロック）は失敗。'),
        ('♥', 'プライドを失ったら', '手札のアクションカードを1枚捨てる → 失わせた相手が上半身・下半身どちらを脱がせるか選んで裏返す → その横のトリガーを表にして発動。即効はその場で1回、常時は表のまま効き続ける。'),
        ('★', '勝ち', f"上下とも裏返ったら脱落。最後の1人が勝ち。メンヘラを表にしている人は{RULES.get('collectorGoal', 9)}♥集めても勝ち。"),
        ('！', '表のトリガーによるブロック', '「見せないが？」「魔除け」は公開済みなのでダウトできない。'),
    ]
    for no, h, body in secs:
        d.ellipse((x0, y, x0 + int(6 * MM), y + int(6 * MM)), fill=navy)
        center(d, x0 + int(3 * MM), y + int(0.9 * MM), no, font(7, 'black'), fill=(255, 255, 255))
        d.text((x0 + int(8 * MM), y - int(0.2 * MM)), h, font=font(8.5, 'black'), fill=navy)
        y2 = block(d, (x0 + int(8 * MM), y + int(5.2 * MM)), body, font(6.2), wdt - int(8 * MM), fill=INK, spacing=1.3)
        y = y2 + int(2.2 * MM)
    center(d, PW / 2, PH - M - int(3.5 * MM), 'メスガキ・クー', font(5), fill=DIM)
    return im

# ---- 手番マーカー（切り取り）
def markers():
    spec = importlib.util.spec_from_file_location('shape_chars', os.path.join(HERE, 'shape_chars.py'))
    sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
    im = Image.new('RGB', (PW, PH), PAPER); d = ImageDraw.Draw(im)
    d.text((M, M), '手番マーカー（丸く切り取る）', font=font(9, 'head'), fill=INK)
    d.text((M, M + int(5.5 * MM)), '宣言したら、アクションボードのその段の丸に置く。1人1枚、残りは予備。', font=font(5.5), fill=DIM)
    ids = [c for c in args.chars.split(',') if c]
    dia = int(17 * MM); pitch = int(18.5 * MM); cols = 5
    x0 = M + int(2 * MM); y0 = M + int(12 * MM)
    k = 0
    for cid in ids:
        full = sc.full(cid, 1295, 1598, False)
        W, H = full.size; side = int(W * 0.5); cx, cy = W // 2, int(H * 0.19)
        face = full.crop((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2)).resize((dia, dia), Image.LANCZOS)
        mask = Image.new('L', (dia, dia), 0); ImageDraw.Draw(mask).ellipse((0, 0, dia - 1, dia - 1), fill=255)
        for _ in range(args.copies):
            x = x0 + (k % cols) * pitch; y = y0 + (k // cols) * (pitch + int(4.5 * MM))
            im.paste(face, (x, y), mask)
            d.ellipse((x, y, x + dia, y + dia), outline=(40, 22, 48), width=int(0.5 * MM))
            center(d, x + dia / 2, y + dia + int(0.6 * MM), CHARS.get(cid, cid), font(5.5, 'black'), fill=INK)
            k += 1
    center(d, PW / 2, PH - M - int(3.5 * MM), 'メスガキ・クー', font(5), fill=DIM)
    return im

front, back, mk = board_front(), board_back(), markers()
front.save(os.path.join(args.out, 'board_a6_front.png'), dpi=(args.dpi, args.dpi))
back.save(os.path.join(args.out, 'board_a6_back.png'), dpi=(args.dpi, args.dpi))
mk.save(os.path.join(args.out, 'markers_a6.png'), dpi=(args.dpi, args.dpi))
try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader
    pdf = os.path.join(args.out, 'action_board_a6.pdf'); c = rl_canvas.Canvas(pdf, pagesize=(105 / 25.4 * 72, 148 / 25.4 * 72))
    for im in (front, back, mk):
        c.drawImage(ImageReader(im), 0, 0, 105 / 25.4 * 72, 148 / 25.4 * 72); c.showPage()
    c.save(); print('pdf ->', pdf)
except ImportError:
    print('reportlab が無いので PDF は出していない')
print('ok ->', args.out)
