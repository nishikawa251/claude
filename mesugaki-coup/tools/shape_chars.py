# -*- coding: utf-8 -*-
"""キャラカードの図形版：立ち絵を使わず、丸と四角だけで組んだ「紙人形」を描く。

full(cid, W, H, boro) -> 全身（上半身・下半身の2枚ぶん、縦に並べた）キャンバス。
腰の位置がちょうど H/2 に来るので、上下に切ればキャラカードの上半身・下半身になる。
boro=True はボロ絵（服が破れて、顔が泣き顔、背景が暗い）。
"""
import math, random
from PIL import Image, ImageDraw, ImageFilter

SKIN = (255, 226, 205)
SKIN_LINE = (214, 160, 140)
EYE = (60, 40, 70)
WHITE = (255, 255, 255)

# id -> 色と髪型。hair: short / twin / long / buns / pony。acc: 飾り
CHARS = {
    'shiro':    dict(hair=(246, 246, 252), hair2=(214, 214, 230), style='short', acc='ahoge',  top=(78, 116, 206),  top2=(240, 244, 255), skirt=(78, 116, 206),  sock=(250, 250, 255), shoe=(70, 70, 90),   accent=(255, 120, 170), bg=(222, 234, 252)),
    'momoko':   dict(hair=(255, 150, 190), hair2=(236, 110, 160), style='twin',  acc='ribbon', top=(255, 112, 152), top2=(255, 236, 244), skirt=(255, 140, 175), sock=(255, 255, 255), shoe=(220, 60, 100),  accent=(224, 40, 90),   bg=(255, 230, 240)),
    'emera':    dict(hair=(176, 230, 156), hair2=(132, 200, 120), style='long',  acc='leaf',   top=(72, 182, 128),  top2=(240, 255, 246), skirt=(60, 160, 110),  sock=(250, 255, 250), shoe=(50, 110, 80),   accent=(255, 210, 90),  bg=(226, 246, 232)),
    'oren':     dict(hair=(214, 122, 60),  hair2=(170, 90, 40),   style='pony',  acc='scar',   top=(255, 150, 60),  top2=(255, 238, 205), skirt=(230, 120, 40),  sock=(255, 240, 220), shoe=(120, 70, 40),   accent=(255, 80, 60),   bg=(255, 236, 216)),
    'aqua':     dict(hair=(84, 122, 232),  hair2=(60, 90, 200),   style='long',  acc='crown',  top=(44, 84, 204),   top2=(222, 236, 255), skirt=(60, 100, 220),  sock=(240, 246, 255), shoe=(40, 50, 120),   accent=(255, 212, 80),  bg=(220, 232, 255)),
    'asagi':    dict(hair=(70, 146, 166),  hair2=(50, 110, 130),  style='short', acc='cap',    top=(44, 62, 112),   top2=(232, 236, 246), skirt=(44, 62, 112),   sock=(30, 40, 70),    shoe=(60, 40, 30),    accent=(230, 190, 90),  bg=(222, 236, 242)),
    'grimaloe': dict(hair=(242, 242, 248), hair2=(200, 200, 215), style='long',  acc='horns',  top=(44, 34, 50),    top2=(60, 48, 70),    skirt=(44, 34, 50),    sock=(40, 32, 44),    shoe=(200, 40, 60),   accent=(206, 40, 64),   bg=(236, 226, 236)),
    'papuru':   dict(hair=(192, 142, 232), hair2=(150, 100, 200), style='twin',  acc='star',   top=(152, 92, 212),  top2=(242, 232, 255), skirt=(130, 70, 190),  sock=(250, 245, 255), shoe=(90, 50, 140),   accent=(255, 200, 80),  bg=(238, 228, 250)),
    'pin':      dict(hair=(255, 222, 92),  hair2=(236, 190, 60),  style='buns',  acc='bell',   top=(255, 202, 64),  top2=(255, 250, 232), skirt=(255, 180, 50),  sock=(255, 252, 240), shoe=(190, 120, 40),  accent=(255, 110, 90),  bg=(255, 246, 216)),
    'kuro':     dict(hair=(54, 54, 76),    hair2=(34, 34, 52),    style='pony',  acc='moon',   top=(42, 42, 62),    top2=(226, 226, 240), skirt=(42, 42, 62),    sock=(40, 40, 56),    shoe=(30, 30, 40),    accent=(120, 164, 255), bg=(226, 226, 236)),
}


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def desat(c, t=0.35):
    g = int(0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
    return mix(c, (g, g, g), t)


def rr(d, box, r, **kw):
    d.rounded_rectangle(box, radius=r, **kw)


def ell(d, cx, cy, rx, ry, **kw):
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), **kw)


def jag_poly(pts, amp, rnd, n=3):
    """多角形の各辺に、ギザギザ（破れ）を足す"""
    out = []
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        out.append((x0, y0))
        for k in range(1, n + 1):
            t = k / (n + 1)
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            nx, ny = -(y1 - y0), (x1 - x0)
            L = math.hypot(nx, ny) or 1
            a = rnd.uniform(-amp, amp * 0.3)
            out.append((x + nx / L * a, y + ny / L * a))
    return out


def full(cid, W, H, boro=False, ss=2, seed=7):
    """全身キャンバス（W×H、腰＝H/2）。ss は描画の倍率（アンチエイリアス用）"""
    P = CHARS.get(cid, CHARS['shiro'])
    rnd = random.Random(seed + sum(map(ord, cid)))
    w, h = W * ss, H * ss
    u = w / 100.0                      # 1u = 幅の1%
    img = Image.new('RGB', (w, h), P['bg']); d = ImageDraw.Draw(img)
    # ---- 背景：淡い縦グラデ＋後光の輪
    bg = P['bg']; bg2 = mix(bg, WHITE, 0.6)
    if boro: bg, bg2 = desat(mix(bg, (60, 50, 70), 0.35), 0.3), desat(mix(bg, (110, 100, 120), 0.2), 0.3)
    for y in range(h):
        d.line((0, y, w, y), fill=mix(bg2, bg, y / h))
    ring = mix(bg, WHITE, 0.35) if not boro else mix(bg, (40, 30, 50), 0.25)
    for k, rad in enumerate((46, 38, 30)):
        ell(d, w / 2, h * 0.44, rad * u, rad * u * 1.15, outline=ring, width=int(1.2 * u))
    if boro:  # ひび割れ
        for _ in range(5):
            x, y = rnd.uniform(5, 95) * u, rnd.uniform(5, 95) * u * (h / w)
            pts = [(x, y)]
            for _ in range(5):
                x += rnd.uniform(-9, 9) * u; y += rnd.uniform(-9, 9) * u; pts.append((x, y))
            d.line(pts, fill=mix(bg, WHITE, 0.6), width=int(0.7 * u))

    top, top2, skirt, sock, shoe, hair, hair2, acc = P['top'], P['top2'], P['skirt'], P['sock'], P['shoe'], P['hair'], P['hair2'], P['accent']
    if boro:
        top, top2, skirt, sock, hair, hair2 = desat(top), desat(top2), desat(skirt), desat(sock), desat(hair, 0.2), desat(hair2, 0.2)
    cx = w / 2
    waist = h / 2
    head_r = 17 * u
    head_cy = h * 0.2
    neck_y = head_cy + head_r * 0.92
    sh_y = neck_y + 2 * u                     # 肩
    body_w = 24 * u

    # ---- 下半身（先に描いて、上半身が手前になるように）
    hem = waist + 24 * u
    leg_w = 7 * u
    for sx in (-1, 1):
        lx = cx + sx * 7 * u
        # 脚
        rr(d, (lx - leg_w / 2, waist, lx + leg_w / 2, h * 0.92), int(leg_w / 2), fill=SKIN)
        # 靴下
        sock_top = h * 0.70 if not (boro and sx == 1) else h * 0.80      # ボロ：片方ずり落ち
        rr(d, (lx - leg_w / 2, sock_top, lx + leg_w / 2, h * 0.92), int(leg_w / 2), fill=sock)
        d.line((lx - leg_w / 2, sock_top + 1.2 * u, lx + leg_w / 2, sock_top + 1.2 * u), fill=mix(sock, (0, 0, 0), 0.15), width=int(0.6 * u))
        # 靴
        rr(d, (lx - leg_w / 2 - 1.5 * u, h * 0.90, lx + leg_w / 2 + 2.5 * u * sx if sx > 0 else lx + leg_w / 2 + 1.5 * u, h * 0.965), int(2.5 * u), fill=shoe)
    # スカート（台形＋ひだ）
    sk = [(cx - 13 * u, waist - 1 * u), (cx + 13 * u, waist - 1 * u), (cx + 21 * u, hem), (cx - 21 * u, hem)]
    if boro:
        sk = jag_poly(sk, 2.6 * u, rnd, 4)
    d.polygon(sk, fill=skirt)
    if not boro:
        for k in range(-2, 3):
            x0 = cx + k * 5.2 * u; x1 = cx + k * 8.4 * u
            d.line((x0, waist + 1 * u, x1, hem - 1 * u), fill=mix(skirt, (0, 0, 0), 0.18), width=int(0.7 * u))
    else:
        # 破れ穴
        for _ in range(2):
            x, y = cx + rnd.uniform(-12, 12) * u, waist + rnd.uniform(6, 17) * u
            d.polygon(jag_poly([(x - 2.2 * u, y - 1.5 * u), (x + 2.2 * u, y - 1.8 * u), (x + 1.5 * u, y + 2.2 * u), (x - 1.8 * u, y + 1.5 * u)], 0.8 * u, rnd, 2), fill=SKIN)
    # ベルト
    rr(d, (cx - 13 * u, waist - 2.2 * u, cx + 13 * u, waist + 1.4 * u), int(1 * u), fill=mix(top, (0, 0, 0), 0.25))

    # ---- 髪（後ろ）
    if P['style'] in ('long',):
        for sx in (-1, 1):
            rr(d, (cx + sx * 19 * u - 7 * u, head_cy - 6 * u, cx + sx * 19 * u + 7 * u, waist - 4 * u), int(7 * u), fill=hair2)
            ell(d, cx + sx * 19 * u, waist - 4 * u, 7 * u, 5 * u, fill=hair2)
    if P['style'] == 'twin':
        for sx in (-1, 1):
            ell(d, cx + sx * 24 * u, head_cy + 12 * u, 6 * u, 19 * u, fill=hair2)
            ell(d, cx + sx * 19 * u, head_cy - 4 * u, 4.5 * u, 4.5 * u, fill=hair2)
    if P['style'] == 'pony':
        rr(d, (cx + 10 * u, head_cy - 8 * u, cx + 24 * u, waist - 6 * u), int(6 * u), fill=hair2)
    # ---- 胴体（服）
    body = [(cx - body_w / 2, sh_y), (cx + body_w / 2, sh_y), (cx + body_w / 2 + 2 * u, waist + 1 * u), (cx - body_w / 2 - 2 * u, waist + 1 * u)]
    if boro:
        body = jag_poly(body, 2.2 * u, rnd, 4)
    d.polygon(body, fill=top)
    # 襟（白）
    d.polygon([(cx - 8 * u, sh_y - 1 * u), (cx + 8 * u, sh_y - 1 * u), (cx, sh_y + 9 * u)], fill=top2)
    # リボン／ネクタイ
    d.polygon([(cx, sh_y + 4 * u), (cx - 4 * u, sh_y + 1 * u), (cx - 4 * u, sh_y + 7 * u)], fill=acc)
    d.polygon([(cx, sh_y + 4 * u), (cx + 4 * u, sh_y + 1 * u), (cx + 4 * u, sh_y + 7 * u)], fill=acc)
    ell(d, cx, sh_y + 4 * u, 1.6 * u, 1.6 * u, fill=mix(acc, (0, 0, 0), 0.3))
    # 腕（腰に手を当てた「は？」ポーズ）
    for sx in (-1, 1):
        ax0 = cx + sx * (body_w / 2 - 1 * u); ay0 = sh_y + 2 * u
        ax1 = cx + sx * (body_w / 2 + 11 * u); ay1 = sh_y + 14 * u
        ax2 = cx + sx * (body_w / 2 + 1 * u); ay2 = waist - 2 * u
        d.line((ax0, ay0, ax1, ay1), fill=top, width=int(6.5 * u))
        d.line((ax1, ay1, ax2, ay2), fill=SKIN, width=int(5.5 * u))
        ell(d, ax1, ay1, 3.3 * u, 3.3 * u, fill=top)
        ell(d, ax2, ay2, 3.2 * u, 3.2 * u, fill=SKIN)
    if boro:
        # 破れ穴と汚れ
        for _ in range(2):
            x, y = cx + rnd.uniform(-7, 7) * u, sh_y + rnd.uniform(10, 24) * u
            d.polygon(jag_poly([(x - 2 * u, y - 1.5 * u), (x + 2.2 * u, y - 1.5 * u), (x + 1.5 * u, y + 2 * u), (x - 1.5 * u, y + 1.6 * u)], 0.8 * u, rnd, 2), fill=SKIN)
        for _ in range(6):
            x, y = cx + rnd.uniform(-14, 14) * u, rnd.uniform(sh_y + 2 * u, h * 0.9)
            d.line((x, y, x + rnd.uniform(-3, 3) * u, y + rnd.uniform(1, 3) * u), fill=(90, 70, 80), width=int(0.8 * u))
    # ---- 首と頭
    rr(d, (cx - 3.5 * u, neck_y - 3 * u, cx + 3.5 * u, sh_y + 2 * u), int(2 * u), fill=SKIN)
    ell(d, cx, head_cy, head_r, head_r * 0.96, fill=SKIN)
    # 髪（前）：帽子型＋もみあげ
    d.chord((cx - head_r * 1.08, head_cy - head_r * 1.08, cx + head_r * 1.08, head_cy + head_r * 0.95), 180, 360, fill=hair)
    for sx in (-1, 1):
        rr(d, (cx + sx * head_r * 0.95 - 3.2 * u, head_cy - 4 * u, cx + sx * head_r * 0.95 + 3.2 * u, head_cy + 9 * u), int(3 * u), fill=hair)
    # 前髪の段
    for k in range(-2, 3):
        x = cx + k * 6.2 * u
        d.polygon([(x - 3.2 * u, head_cy - 6 * u), (x + 3.2 * u, head_cy - 6 * u), (x + 0.6 * u * k, head_cy + 0.5 * u)], fill=hair)
    if P['style'] == 'buns':
        for sx in (-1, 1):
            ell(d, cx + sx * 13 * u, head_cy - 13 * u, 6.5 * u, 6.5 * u, fill=hair2)
            ell(d, cx + sx * 13 * u, head_cy - 13 * u, 3 * u, 3 * u, outline=mix(hair2, (0, 0, 0), 0.2), width=int(0.7 * u))
    if boro:  # 寝ぐせ
        for _ in range(4):
            x = cx + rnd.uniform(-14, 14) * u; y = head_cy - head_r * 0.9
            d.polygon([(x - 1.5 * u, y + 2 * u), (x + 1.5 * u, y + 2 * u), (x + rnd.uniform(-4, 4) * u, y - rnd.uniform(5, 9) * u)], fill=hair)
    # 飾り
    a = P['acc']
    if a == 'ahoge':
        d.arc((cx - 2 * u, head_cy - head_r * 1.5, cx + 10 * u, head_cy - head_r * 0.7), 200, 330, fill=hair, width=int(1.4 * u))
    elif a == 'ribbon':
        rx, ry = cx + 11 * u, head_cy - head_r * 0.85
        d.polygon([(rx, ry), (rx - 6 * u, ry - 4 * u), (rx - 5 * u, ry + 3 * u)], fill=acc)
        d.polygon([(rx, ry), (rx + 6 * u, ry - 4 * u), (rx + 5 * u, ry + 3 * u)], fill=acc)
        ell(d, rx, ry, 1.6 * u, 1.6 * u, fill=mix(acc, (0, 0, 0), 0.3))
    elif a == 'crown':
        cy = head_cy - head_r * 1.02
        d.polygon([(cx - 8 * u, cy), (cx - 8 * u, cy - 7 * u), (cx - 4 * u, cy - 3 * u), (cx, cy - 9 * u), (cx + 4 * u, cy - 3 * u), (cx + 8 * u, cy - 7 * u), (cx + 8 * u, cy)], fill=acc)
    elif a == 'horns':
        for sx in (-1, 1):
            x = cx + sx * 9 * u; y = head_cy - head_r * 0.85
            d.polygon([(x - 2.5 * u, y + 1 * u), (x + 2.5 * u, y + 1 * u), (x + sx * 2 * u, y - 7 * u)], fill=acc)
    elif a == 'cap':
        rr(d, (cx - head_r * 1.05, head_cy - head_r * 1.15, cx + head_r * 1.05, head_cy - head_r * 0.45), int(4 * u), fill=top)
        rr(d, (cx - head_r * 1.15, head_cy - head_r * 0.6, cx + head_r * 1.15, head_cy - head_r * 0.35), int(2 * u), fill=mix(top, (0, 0, 0), 0.3))
    elif a == 'star':
        sx_, sy_ = cx - 11 * u, head_cy - head_r * 0.9
        pts = [(sx_ + 4 * u * math.cos(math.radians(-90 + k * 36)) * (1 if k % 2 == 0 else 0.45), sy_ + 4 * u * math.sin(math.radians(-90 + k * 36)) * (1 if k % 2 == 0 else 0.45)) for k in range(10)]
        d.polygon(pts, fill=acc)
    elif a == 'bell':
        ell(d, cx + 12 * u, head_cy - head_r * 0.6, 3 * u, 3 * u, fill=acc)
        ell(d, cx + 12 * u, head_cy - head_r * 0.6 + 1.5 * u, 0.9 * u, 0.9 * u, fill=mix(acc, (0, 0, 0), 0.4))
    elif a == 'leaf':
        d.polygon([(cx + 9 * u, head_cy - head_r * 0.95), (cx + 16 * u, head_cy - head_r * 1.25), (cx + 14 * u, head_cy - head_r * 0.75)], fill=acc)
    elif a == 'moon':
        mx, my = cx + 11 * u, head_cy - head_r * 0.9
        ell(d, mx, my, 3.5 * u, 3.5 * u, fill=acc); ell(d, mx + 1.6 * u, my - 0.6 * u, 3 * u, 3 * u, fill=hair)
    elif a == 'scar':
        d.line((cx + 7 * u, head_cy + 1 * u, cx + 11 * u, head_cy + 5 * u), fill=(220, 120, 120), width=int(0.9 * u))
    # ---- 顔
    ex = 6.5 * u; ey = head_cy + 2.5 * u
    if not boro:
        # 半目のドヤ顔
        for sx in (-1, 1):
            x = cx + sx * ex
            d.chord((x - 3.2 * u, ey - 3.6 * u, x + 3.2 * u, ey + 2.6 * u), 0, 180, fill=EYE)
            d.line((x - 3.4 * u, ey - 0.5 * u, x + 3.4 * u, ey - 0.5 * u), fill=EYE, width=int(1.1 * u))
            ell(d, x + sx * 1.0 * u, ey + 0.6 * u, 0.9 * u, 0.9 * u, fill=WHITE)
        # 眉（下がり気味＝見下す）
        for sx in (-1, 1):
            x = cx + sx * ex
            d.line((x - 3 * u, ey - 6.5 * u + (0 if sx < 0 else 1.2 * u), x + 3 * u, ey - 6.5 * u + (1.2 * u if sx < 0 else 0)), fill=EYE, width=int(1.0 * u))
        # 口：にやり（片側だけ上がる）
        d.line((cx - 3 * u, head_cy + 9 * u, cx + 1 * u, head_cy + 10 * u, cx + 4.5 * u, head_cy + 7.5 * u), fill=EYE, width=int(1.1 * u), joint='curve')
        d.polygon([(cx + 1.5 * u, head_cy + 9.6 * u), (cx + 3.2 * u, head_cy + 9.2 * u), (cx + 2.3 * u, head_cy + 11.2 * u)], fill=WHITE)   # 八重歯
    else:
        # 泣き顔：＞＜
        for sx in (-1, 1):
            x = cx + sx * ex
            d.line((x - sx * 3 * u, ey - 3 * u, x + sx * 2 * u, ey, x - sx * 3 * u, ey + 3 * u), fill=EYE, width=int(1.3 * u), joint='curve')
            ell(d, x + sx * 3.5 * u, ey + 4.5 * u, 1.3 * u, 2.2 * u, fill=(150, 200, 255))
        for sx in (-1, 1):
            x = cx + sx * ex
            d.line((x - 3 * u, ey - 6.5 * u + (1.5 * u if sx < 0 else 0), x + 3 * u, ey - 6.5 * u + (0 if sx < 0 else 1.5 * u)), fill=EYE, width=int(1.0 * u))
        # 口：波
        pts = [(cx - 4 * u + k * 2 * u, head_cy + 9.5 * u + (1.2 * u if k % 2 else -1.2 * u)) for k in range(5)]
        d.line(pts, fill=EYE, width=int(1.1 * u), joint='curve')
        # 絆創膏
        bx, by = cx - 9 * u, head_cy + 7 * u
        rr(d, (bx - 3 * u, by - 1.2 * u, bx + 3 * u, by + 1.2 * u), int(1 * u), fill=(245, 215, 190))
        d.line((bx - 0.8 * u, by - 0.8 * u, bx + 0.8 * u, by + 0.8 * u), fill=(220, 180, 160), width=int(0.5 * u))
    # 頬
    for sx in (-1, 1):
        ell(d, cx + sx * 10 * u, head_cy + 6.5 * u, 2.6 * u, 1.5 * u, fill=mix(SKIN, (255, 120, 150), 0.45 if boro else 0.3))
    if boro:
        # 「ボロ」の印：ひとこと
        for k in range(3):
            x, y = cx + 20 * u + k * 1.5 * u, head_cy - 10 * u - k * 4 * u
            d.line((x, y, x + 2.5 * u, y - 3 * u), fill=mix(bg, WHITE, 0.7), width=int(0.9 * u))

    return img.resize((W, H), Image.LANCZOS)


if __name__ == '__main__':
    import sys
    W, H = 1295, 1598
    cid = sys.argv[1] if len(sys.argv) > 1 else 'momoko'
    full(cid, W, H, False).save(f'/tmp/shape_{cid}_000.png'); full(cid, W, H, True).save(f'/tmp/shape_{cid}_001.png')
    print('ok')
