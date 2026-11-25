#!/usr/bin/env python3
"""ショートの画面に、YouTube ショートと TikTok の UI を重ねた見え方の画像を作る（配置は目安）。
  python3 preview_ui.py frame.png out_prefix --title "動画タイトル" --sound "音源の表記"
frame.png は 1080×1920 の動画の1コマ。out_prefix_youtube.png と out_prefix_tiktok.png を書き出す。
各社のロゴは使わず、ボタンは簡単な図形で描く。位置と大きさは 1080×1920 の画面に合わせた一般的な配置の目安。
"""
import argparse, math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, NAV = 1080, 1920, 180          # 動画の大きさと、下のナビゲーションバーの高さ
FD = os.environ.get('KAL_FONTS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts'))
WHITE = (255, 255, 255, 255)


def font(size, bold=False):
    return ImageFont.truetype(os.path.join(FD, 'axisstd-bold.otf' if bold else 'axisstd-regular.otf'), size)


# ---------- アイコン（白の塗り。中心 cx, cy、大きさ s） ----------
def ic_search(d, cx, cy, s):
    r = s * 0.32
    d.ellipse((cx - s * 0.12 - r, cy - s * 0.12 - r, cx - s * 0.12 + r, cy - s * 0.12 + r), outline=WHITE, width=max(3, int(s * 0.09)))
    d.line((cx + s * 0.12, cy + s * 0.12, cx + s * 0.42, cy + s * 0.42), fill=WHITE, width=max(3, int(s * 0.1)))


def ic_more(d, cx, cy, s):
    for k in (-1, 0, 1):
        r = s * 0.07
        d.ellipse((cx - r, cy + k * s * 0.28 - r, cx + r, cy + k * s * 0.28 + r), fill=WHITE)


def ic_thumb(d, cx, cy, s, down=False):
    sg = -1 if down else 1
    d.rounded_rectangle((cx - s * 0.42, cy - sg * s * 0.02 - (s * 0.36 if not down else 0), cx - s * 0.24, cy + (s * 0.36 if not down else 0) - sg * s * 0.02 + (s * 0.36 if down else 0)), 4, fill=WHITE)
    pts = [(-0.18, 0.0), (0.02, -0.12), (0.06, -0.42), (0.18, -0.40), (0.16, -0.08), (0.40, -0.06), (0.38, 0.34), (-0.18, 0.34)]
    d.polygon([(cx + x * s, cy + sg * y * s) for x, y in pts], fill=WHITE)


def ic_bubble(d, cx, cy, s):
    d.rounded_rectangle((cx - s * 0.42, cy - s * 0.34, cx + s * 0.42, cy + s * 0.24), s * 0.18, fill=WHITE)
    d.polygon([(cx - s * 0.05, cy + s * 0.22), (cx + s * 0.18, cy + s * 0.22), (cx + s * 0.22, cy + s * 0.44)], fill=WHITE)


def ic_share(d, cx, cy, s):
    d.polygon([(cx + s * 0.42, cy - s * 0.06), (cx + s * 0.02, cy - s * 0.42), (cx + s * 0.02, cy - s * 0.22),
               (cx - s * 0.40, cy - s * 0.10), (cx - s * 0.40, cy + s * 0.36), (cx - s * 0.18, cy + s * 0.10),
               (cx + s * 0.02, cy + s * 0.08), (cx + s * 0.02, cy + s * 0.30)], fill=WHITE)


def ic_remix(d, cx, cy, s):
    r = s * 0.34; w = max(3, int(s * 0.1))
    d.arc((cx - r, cy - r, cx + r, cy + r), 200, 340, fill=WHITE, width=w)
    d.arc((cx - r, cy - r, cx + r, cy + r), 20, 160, fill=WHITE, width=w)
    d.polygon([(cx + r - s * 0.12, cy - s * 0.26), (cx + r + s * 0.12, cy - s * 0.18), (cx + r - s * 0.02, cy - s * 0.02)], fill=WHITE)
    d.polygon([(cx - r + s * 0.12, cy + s * 0.26), (cx - r - s * 0.12, cy + s * 0.18), (cx - r + s * 0.02, cy + s * 0.02)], fill=WHITE)


def ic_heart(d, cx, cy, s):
    r = s * 0.24
    d.ellipse((cx - 2 * r + s * 0.02, cy - s * 0.30, cx + s * 0.02, cy - s * 0.30 + 2 * r), fill=WHITE)
    d.ellipse((cx - s * 0.02, cy - s * 0.30, cx + 2 * r - s * 0.02, cy - s * 0.30 + 2 * r), fill=WHITE)
    d.polygon([(cx - s * 0.46, cy - s * 0.04), (cx + s * 0.46, cy - s * 0.04), (cx, cy + s * 0.42)], fill=WHITE)


def ic_bookmark(d, cx, cy, s):
    d.polygon([(cx - s * 0.30, cy - s * 0.40), (cx + s * 0.30, cy - s * 0.40), (cx + s * 0.30, cy + s * 0.42),
               (cx, cy + s * 0.18), (cx - s * 0.30, cy + s * 0.42)], fill=WHITE)


def ic_home(d, cx, cy, s, fill=WHITE):
    d.polygon([(cx, cy - s * 0.42), (cx + s * 0.42, cy - s * 0.02), (cx + s * 0.30, cy - s * 0.02), (cx + s * 0.30, cy + s * 0.38),
               (cx - s * 0.30, cy + s * 0.38), (cx - s * 0.30, cy - s * 0.02), (cx - s * 0.42, cy - s * 0.02)], fill=fill)


def ic_person(d, cx, cy, s, fill=WHITE):
    d.ellipse((cx - s * 0.18, cy - s * 0.42, cx + s * 0.18, cy - s * 0.06), outline=fill, width=max(2, int(s * 0.08)))
    d.arc((cx - s * 0.36, cy - s * 0.02, cx + s * 0.36, cy + s * 0.70), 180, 360, fill=fill, width=max(2, int(s * 0.08)))


def ic_people(d, cx, cy, s, fill=WHITE):
    ic_person(d, cx - s * 0.16, cy, s * 0.85, fill); ic_person(d, cx + s * 0.22, cy + s * 0.04, s * 0.7, fill)


def ic_inbox(d, cx, cy, s, fill=WHITE):
    d.rounded_rectangle((cx - s * 0.40, cy - s * 0.30, cx + s * 0.40, cy + s * 0.22), s * 0.12, outline=fill, width=max(2, int(s * 0.08)))
    d.polygon([(cx - s * 0.06, cy + s * 0.20), (cx + s * 0.14, cy + s * 0.20), (cx + s * 0.04, cy + s * 0.38)], fill=fill)


def ic_shorts(d, cx, cy, s, fill=WHITE):
    d.rounded_rectangle((cx - s * 0.30, cy - s * 0.42, cx + s * 0.30, cy + s * 0.42), s * 0.18, outline=fill, width=max(2, int(s * 0.08)))
    d.polygon([(cx - s * 0.08, cy - s * 0.14), (cx + s * 0.14, cy), (cx - s * 0.08, cy + s * 0.14)], fill=fill)


def ic_subs(d, cx, cy, s, fill=WHITE):
    d.rounded_rectangle((cx - s * 0.40, cy - s * 0.22, cx + s * 0.40, cy + s * 0.36), s * 0.08, outline=fill, width=max(2, int(s * 0.08)))
    d.line((cx - s * 0.30, cy - s * 0.34, cx + s * 0.30, cy - s * 0.34), fill=fill, width=max(2, int(s * 0.07)))
    d.polygon([(cx - s * 0.08, cy - s * 0.06), (cx + s * 0.14, cy + s * 0.07), (cx - s * 0.08, cy + s * 0.20)], fill=fill)


def ic_plus(d, cx, cy, s, fill=WHITE, box=False):
    if box:
        d.rounded_rectangle((cx - s * 0.55, cy - s * 0.36, cx + s * 0.55, cy + s * 0.36), s * 0.14, fill=fill)
        fill = (0, 0, 0, 255)
    w = max(3, int(s * 0.09))
    d.line((cx - s * 0.20, cy, cx + s * 0.20, cy), fill=fill, width=w); d.line((cx, cy - s * 0.20, cx, cy + s * 0.20), fill=fill, width=w)


def text_c(d, cx, y, s, f, fill=WHITE):
    w = d.textlength(s, font=f); d.text((cx - w / 2, y), s, font=f, fill=fill)


def with_shadow(layer, blur=4, strength=0.55):
    a = layer.getchannel('A').filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * strength))
    sh = Image.new('RGBA', layer.size, (0, 0, 0, 0)); sh.putalpha(a)
    return Image.alpha_composite(sh, layer)


def gradients(base, top=260, bottom=480):
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for y in range(top):
        d.line((0, y, W, y), fill=(0, 0, 0, int(95 * (1 - y / top) ** 1.5)))
    for y in range(bottom):
        d.line((0, H - 1 - y, W, H - 1 - y), fill=(0, 0, 0, int(140 * (1 - y / bottom) ** 1.5)))
    base.alpha_composite(g)


def status_bar(d):
    d.text((60, 28), '12:34', font=font(36, True), fill=WHITE)
    d.rounded_rectangle((W - 120, 34, W - 64, 62), 7, outline=WHITE, width=3); d.rectangle((W - 116, 38, W - 80, 58), fill=WHITE)
    d.rectangle((W - 62, 42, W - 58, 54), fill=WHITE)


def avatar(logo, size):
    a = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(a)
    d.ellipse((0, 0, size - 1, size - 1), fill=(28, 36, 38, 255))
    lg = logo.copy(); lg.thumbnail((int(size * 0.72), int(size * 0.72)), Image.LANCZOS)
    a.alpha_composite(lg, ((size - lg.width) // 2, (size - lg.height) // 2))
    return a


def white_logo(path):
    lg = Image.open(path).convert('RGBA'); a = lg.getchannel('A'); a = a.crop(a.getbbox())
    out = Image.new('RGBA', a.size, (255, 255, 255, 0)); out.putalpha(a)
    return out


def wrap(d, s, f, width, lines=2):
    out, cur = [], ''
    for ch in s:
        if d.textlength(cur + ch, font=f) > width:
            out.append(cur); cur = ch
            if len(out) == lines:
                break
        else:
            cur += ch
    if len(out) < lines and cur:
        out.append(cur)
    if len(out) == lines and ''.join(out) != s:
        while d.textlength(out[-1] + '…', font=f) > width:
            out[-1] = out[-1][:-1]
        out[-1] += '…'
    return out


def youtube(frame, logo, title, sound, handle):
    canvas = Image.new('RGBA', (W, H + NAV), (15, 15, 15, 255))
    canvas.alpha_composite(frame, (0, 0)); base = canvas.crop((0, 0, W, H)); gradients(base)
    ui = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ui)
    status_bar(d)
    ic_search(d, 880, 150, 60); ic_more(d, 1010, 150, 64)
    fc = font(27)
    col = [(ic_thumb, '1.2万', 1000, {}), (ic_thumb, '低評価', 1160, {'down': True}), (ic_bubble, '128', 1320, {}),
           (ic_share, '共有', 1480, {}), (ic_remix, 'リミックス', 1640, {})]
    for fn, lab, y, kw in col:
        fn(d, 1000, y, 66, **kw); text_c(d, 1000, y + 46, lab, fc)
    d.rounded_rectangle((966, 1758, 1034, 1826), 12, fill=(40, 40, 40, 255), outline=WHITE, width=3)
    ui.alpha_composite(avatar(logo, 66).resize((60, 60)), (970, 1762))
    ui.alpha_composite(avatar(logo, 72), (36, 1612))
    fh = font(32, True); d.text((124, 1628), handle, font=fh, fill=WHITE)
    x = 124 + d.textlength(handle, font=fh) + 24
    d.rounded_rectangle((x, 1620, x + 112, 1676), 28, fill=WHITE); text_c(d, x + 56, 1630, '登録', font(30, True), fill=(15, 15, 15, 255))
    ft = font(34)
    for k, line in enumerate(wrap(d, title, ft, 820)):
        d.text((36, 1712 + k * 48), line, font=ft, fill=WHITE)
    d.text((36, 1820), '♪', font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30), fill=WHITE)
    d.text((76, 1820), wrap(d, sound, font(28), 800, 1)[0], font=font(28), fill=WHITE)
    base.alpha_composite(with_shadow(ui))
    pb = ImageDraw.Draw(base); pb.rectangle((0, H - 6, W, H), fill=(255, 255, 255, 70)); pb.rectangle((0, H - 6, int(W * 0.36), H), fill=(255, 0, 51, 255))
    canvas.paste(base, (0, 0))
    nav = ImageDraw.Draw(canvas); fn_ = font(24)
    items = [(ic_home, 'ホーム'), (ic_shorts, 'ショート'), (None, ''), (ic_subs, '登録チャンネル'), (ic_person, 'マイページ')]
    for k, (fn, lab) in enumerate(items):
        cx = W * (k + 0.5) / 5
        if fn is None:
            nav.ellipse((cx - 44, H + 30, cx + 44, H + 118), fill=(60, 60, 60, 255)); ic_plus(nav, cx, H + 74, 70)
        else:
            fn(nav, cx, H + 62, 52); text_c(nav, cx, H + 100, lab, fn_)
    return canvas


def tiktok(frame, logo, title, sound, handle):
    canvas = Image.new('RGBA', (W, H + NAV), (0, 0, 0, 255))
    canvas.alpha_composite(frame, (0, 0)); base = canvas.crop((0, 0, W, H)); gradients(base, 300, 520)
    ui = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ui)
    status_bar(d)
    d.text((44, 128), 'LIVE', font=font(30, True), fill=WHITE)
    ftab = font(36, True)
    text_c(d, 420, 124, 'フォロー中', ftab, fill=(255, 255, 255, 170)); text_c(d, 650, 124, 'おすすめ', ftab)
    d.rectangle((650 - 34, 178, 650 + 34, 183), fill=WHITE)
    ic_search(d, 1010, 146, 60)
    ui.alpha_composite(avatar(logo, 100), (950, 900))
    d.ellipse((980, 978, 1020, 1018), fill=(254, 44, 85, 255)); ic_plus(d, 1000, 998, 40)
    fc = font(27, True)
    for fn, lab, y in [(ic_heart, '1.2万', 1120), (ic_bubble, '345', 1270), (ic_bookmark, '678', 1420), (ic_share, '90', 1570)]:
        fn(d, 1000, y, 74); text_c(d, 1000, y + 50, lab, fc)
    disc = Image.new('RGBA', (96, 96), (0, 0, 0, 0)); dd = ImageDraw.Draw(disc)
    dd.ellipse((0, 0, 95, 95), fill=(30, 30, 30, 255)); dd.ellipse((10, 10, 85, 85), outline=(80, 80, 80, 255), width=2)
    disc.alpha_composite(avatar(logo, 56), (20, 20)); ui.alpha_composite(disc, (952, 1700))
    d.text((36, 1600), handle.lstrip('@'), font=font(34, True), fill=WHITE)
    ft = font(32)
    for k, line in enumerate(wrap(d, title, ft, 820)):
        d.text((36, 1658 + k * 46), line, font=ft, fill=WHITE)
    d.text((36, 1770), '♪', font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30), fill=WHITE)
    d.text((76, 1770), wrap(d, sound, font(30), 780, 1)[0], font=font(30), fill=WHITE)
    base.alpha_composite(with_shadow(ui))
    pb = ImageDraw.Draw(base); pb.rectangle((0, H - 5, W, H), fill=(255, 255, 255, 60)); pb.rectangle((0, H - 5, int(W * 0.36), H), fill=(255, 255, 255, 230))
    canvas.paste(base, (0, 0))
    nav = ImageDraw.Draw(canvas); fn_ = font(24)
    items = [(ic_home, 'ホーム'), (ic_people, '友達'), (None, ''), (ic_inbox, '受信箱'), (ic_person, 'プロフィール')]
    for k, (fn, lab) in enumerate(items):
        cx = W * (k + 0.5) / 5
        if fn is None:
            ic_plus(nav, cx, H + 74, 90, box=True)
        else:
            fn(nav, cx, H + 62, 52); text_c(nav, cx, H + 100, lab, fn_)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('frame'); ap.add_argument('out_prefix')
    ap.add_argument('--title', required=True); ap.add_argument('--sound', required=True)
    ap.add_argument('--handle', default='@kalanchoerecords'); ap.add_argument('--logo', default='src/logo_black.png')
    a = ap.parse_args()
    frame = Image.open(a.frame).convert('RGBA').resize((W, H))
    logo = white_logo(a.logo)
    youtube(frame, logo, a.title, a.sound, a.handle).convert('RGB').save(a.out_prefix + '_youtube.png')
    tiktok(frame, logo, a.title, a.sound, a.handle).convert('RGB').save(a.out_prefix + '_tiktok.png')
    print('wrote', a.out_prefix + '_youtube.png', a.out_prefix + '_tiktok.png')


if __name__ == '__main__':
    main()
