#!/usr/bin/env python3
"""KALANCHOE RECORDS ショート動画ジェネレーター v4（ジャケット＋音源型・冒頭アニメーション付き）
  python3 make_short.py potd.json --frames 0,0.5,1.2     # テストフレームPNGを work/ に出す
  python3 make_short.py potd.json --render               # 本番書き出し（1080x1920 / 30fps）
フォントは既定でこのスクリプトと同じ階層の fonts/ から読む（環境変数 KAL_FONTS で変更可）。

動きの決まりごと（上品な性格でそろえる）
  イージングは3本だけ使う。画面内の移動は STD、登場は DEC、退場は ACC。
  主動作（ロゴ、ジャケット、文字）、二次動作（ジャケットの影）、アンビエント（背景のゆっくりした動きと
  低音に合わせた明るさ）の3層で組む。どの要素も1回の動きで画面の高さの1/3（640px）を超えて動かさない。
"""
import json, math, multiprocessing, os, subprocess, sys
import numpy as np
import cv2
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

W, H, FPS = 1080, 1920, 30
FD = os.environ.get('KAL_FONTS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts'))
# 役割ごとのフォント。[ファイル名, 可変フォントの wght（静的フォントは null）]
# 設定ファイルの "fonts" で役割ごとに上書きできる。
FONTS = {
    'title':   ['axisstd-bold.otf', None],     # 曲名
    'body':    ['axisstd-regular.otf', None],  # 原曲名とクレジットの本文
    'tag':     ['axisstd-bold.otf', None],     # 「原曲」「作詞」「編曲」のタグ
    'eyebrow': ['axisstd-medium.otf', None],   # 英字の小見出し
    'time':    ['axisstd-regular.otf', None],  # タイマー
}

INK = (246, 243, 236)
GOLD = (233, 210, 154)

# 最終レイアウト
LOGO_H, LOGO_Y = 128, 62
JS, JX, JY = 860, 110, 226
SPX, SPW, SPY, SPH = 110, 860, 1118, 80
TX, TXR = 110, 930
NBARS = 58
# 冒頭ロゴ（大）。中心は YouTube の文字が重ならない範囲（y=0〜1527）の中央
LOGO0_H, LOGO0_CY = 430, 764
JACKET_RISE = 600        # ジャケットが下から上がる距離
TEXT_RISE = 24           # 文字が下から上がる距離
TEXT_DUR, STAGGER = 0.45, 0.07
BG_MARGIN = 1.12         # 背景を動かすための余白（倍率）


def bezier(x1, y1, x2, y2):
    """CSS の cubic-bezier と同じ曲線。進み具合 p（0〜1）を受け取り、0〜1 を返す"""
    def f(p):
        p = min(1.0, max(0.0, p))
        if p in (0.0, 1.0):
            return p
        lo, hi = 0.0, 1.0
        for _ in range(30):
            u = (lo + hi) / 2
            if 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u ** 2 * x2 + u ** 3 < p:
                lo = u
            else:
                hi = u
        u = (lo + hi) / 2
        return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u ** 2 * y2 + u ** 3
    return f


STD = bezier(0.4, 0, 0.2, 1)   # 画面内の移動
DEC = bezier(0, 0, 0.2, 1)     # 登場（減速して止まる）
ACC = bezier(0.4, 0, 1, 1)     # 退場（加速して消える）


def sine_io(p):
    p = min(1.0, max(0.0, p)); return 0.5 - 0.5 * math.cos(math.pi * p)


def font(spec, size):
    path, wght = spec
    f = ImageFont.truetype(os.path.join(FD, path), size)
    if wght is not None:
        f.set_variation_by_axes([wght])
    return f


def adv(ch, f, feats=None, tnum=False):
    """1文字の送り幅。tnum=True なら数字を最も広い数字の幅にそろえる（タイマーの横揺れ防止）"""
    if tnum and ch.isdigit():
        return max(f.getlength(c, features=feats) for c in '0123456789')
    return f.getlength(ch, features=feats)


def text_w(s, f, track=0.0, feats=None, tnum=False):
    return sum(adv(ch, f, feats, tnum) for ch in s) + track * f.size * (len(s) - 1)


def draw_text(d, x, base, s, f, fill, track=0.0, feats=None, tnum=False):
    """1文字ずつ字送りを制御して描く（プロポーショナル詰め＋トラッキング）。base はベースラインの y"""
    for ch in s:
        a = adv(ch, f, feats, tnum)
        d.text((x + (a - f.getlength(ch, features=feats)) / 2, base), ch, font=f, fill=fill, features=feats, anchor='ls')
        x += a + track * f.size
    return x


def with_shadow(layer, blur=7, strength=0.6):
    sh = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * strength)))
    return Image.alpha_composite(sh, layer)


# 前ボケの色（色相 0〜1）。ジャケットの青緑・水色・青・ラベンダーに、少しのピンクと金
BOKEH_PALETTE = [0.50, 0.56, 0.62, 0.70, 0.93, 0.12]


def hsv_to_rgb(h, s, v=1.0):
    """色相の配列 h（0〜1）を RGB（…×3）にする"""
    h6 = h * 6; i = np.floor(h6).astype(int) % 6; f = (h6 - np.floor(h6)).astype(np.float32)
    p = np.full_like(f, v * (1 - s)); q = v * (1 - s * f); t = v * (1 - s * (1 - f)); vv = np.full_like(f, v)
    r = np.choose(i, [vv, q, p, p, t, vv]); g = np.choose(i, [t, vv, vv, q, p, p]); b = np.choose(i, [p, p, t, vv, vv, q])
    return np.stack([r, g, b], -1).astype(np.float32)


def disc_kernel(r):
    n = int(np.ceil(r)) * 2 + 1
    yy, xx = np.mgrid[:n, :n] - n // 2
    k = np.clip(r + 0.5 - np.sqrt(xx ** 2 + yy ** 2), 0, 1).astype(np.float32)
    return k / k.sum()


def lens_blur(img, r):
    """レンズのボケ。線形光で円形カーネルをかけ、ごく明るい点だけ持ち上げて丸い玉に見せる。img は 0〜1 の float RGB"""
    if r < 0.6:
        return img
    lin = img ** 2.2
    lum = lin.mean(2)
    lin = lin * (1 + 2.5 * np.clip((lum - 0.80) / 0.20, 0, 1) ** 3)[..., None]
    out = cv2.filter2D(lin, -1, disc_kernel(r), borderType=cv2.BORDER_REFLECT)
    out = out / (1 + 0.35 * np.clip(out - 1, 0, None))
    return np.clip(out, 0, 1) ** (1 / 2.2)


class Short:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dur = cfg['duration']
        self.n = int(round(self.dur * FPS))
        self.lead = cfg['lead']                 # サビ頭（動画の開始からの秒）。ジャケットがここで上がり始める
        self.land = cfg['land']                 # ジャケットが着地する時刻
        self.t_focus = cfg.get('focus', self.lead)            # ロゴのピントが合いきる時刻
        self.t_logo0 = cfg.get('pickup', self.lead - 0.20)    # ロゴが上へ動き出す（ジャケットより先に道をあける）
        self.t_logo1 = self.t_logo0 + 0.70
        self.t_text = self.lead + 0.55 * (self.land - self.lead)   # ジャケットが9割ほど上がったところ
        self.t_out = self.dur - cfg.get('outro', 1.2)              # 最後に冒頭と同じ暗さまで落とす（ループ用）
        self.build_static()

    # ---------- 静的パーツ ----------
    def build_static(self):
        cfg = self.cfg
        jk = Image.open(cfg['jacket']).convert('RGB')
        # 背景：ジャケットを拡大してぼかす。動かせるように画面より BG_MARGIN 倍大きく作る
        self.bw, self.bh = round(W * BG_MARGIN), round(H * BG_MARGIN)
        bg = jk.resize((self.bh, self.bh), Image.LANCZOS).crop(((self.bh - self.bw) // 2, 0, (self.bh - self.bw) // 2 + self.bw, self.bh))
        bg = bg.filter(ImageFilter.GaussianBlur(52 * BG_MARGIN))
        bg = ImageEnhance.Brightness(bg).enhance(0.50)
        self.bg_big = ImageEnhance.Color(bg).enhance(1.12)
        # 上下を暗くするグラデーション（画面に固定）
        yy = np.arange(H, dtype=np.float32)
        g = np.clip((yy - 1020) / (H - 1020), 0, 1) ** 1.2 * 0.66
        g = np.maximum(g, np.clip((230 - yy) / 230, 0, 1) ** 1.5 * 0.32)
        shade = np.zeros((H, W, 4), np.uint8)
        shade[..., 3] = (np.repeat(g[:, None], W, 1) * 255).astype(np.uint8)
        self.shade = Image.fromarray(shade, 'RGBA')

        # 冒頭の顔のアップ（設定の intro_face があるときだけ）
        self.face = cfg.get('intro_face')
        if self.face:
            self.jk_np = np.asarray(jk, np.float32) / 255
            yy, xx = np.mgrid[:H, :W].astype(np.float32)
            d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2)
            self.vig_q = (np.clip(d - 0.35, 0, 1) ** 1.4)[..., None]
            # 前ボケは設定に "bokeh" があるときだけ使う（v7 で試し、v8 で外した）
            self.bokeh = self.make_bokeh(cfg['bokeh']) if cfg.get('bokeh') else None
            if self.bokeh:
                self.bokeh_hole = (1 - 0.62 * np.exp(-(((xx - W / 2) / 300) ** 2 + ((yy - LOGO0_CY) / 260) ** 2)))[..., None]
        # 冒頭のライトリーク（設定の "leak" があるときだけ）。四隅から差し込む光で、サビ頭までに消える
        self.leak = self.make_leak(cfg['leak']) if cfg.get('leak') else None

        # ジャケットの面（角丸と細い縁）。影は動きに合わせて card_at で付ける
        j = jk.resize((JS, JS), Image.LANCZOS).convert('RGBA')
        m = Image.new('L', (JS * 2, JS * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, JS * 2 - 1, JS * 2 - 1), 20, fill=255)
        j.putalpha(m.resize((JS, JS), Image.LANCZOS))
        ImageDraw.Draw(j).rounded_rectangle((0, 0, JS - 1, JS - 1), 10, outline=(255, 255, 255, 44), width=1)
        self.card_face, self.card_pad = j, 150
        self.card_rest = self.card_at(0.0)

        # ロゴ（アルファだけ取り出して白抜きに使う）
        lg = Image.open(cfg['logo']).convert('RGBA')
        self.logo_a = lg.crop(lg.getchannel('A').getbbox()).getchannel('A')
        self.logo_ar = self.logo_a.width / self.logo_a.height

        # 文字の行レイヤー（y はすべてベースライン。v2 と同じ位置に文字が乗るようにしてある）
        fonts = {**FONTS, **cfg.get('fonts', {})}
        self.rows = []
        lat = ['kern']
        jp = ['palt', 'kern']
        # 1) 英字の小見出し
        f_eye = font(fonts['eyebrow'], 23)
        row = Image.new('RGBA', (W, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
        draw_text(d, TX, 24, cfg['eyebrow'], f_eye, GOLD + (255,), track=0.11, feats=lat)
        self.y_eye = SPY + SPH + 30
        self.rows.append((with_shadow(row), self.y_eye))
        # 2) 曲名。title_sub（「草野華余子ver.」「feat. ○○」など）があれば、曲名のあとに小さく同じ行に並べる
        sub = cfg.get('title_sub', '')
        f_sub = font(fonts['body'], 30)
        sub_w = (text_w(sub, f_sub, 0.02, jp) + 18) if sub else 0
        size = 68
        while True:
            f_title = font(fonts['title'], size)
            if text_w(cfg['title'], f_title, 0.03, jp) + sub_w <= TXR - TX or size <= 40:
                break
            size -= 1
        row = Image.new('RGBA', (W, size + 44), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
        base_y = round(6 + 1.16 * size)
        x_end = draw_text(d, TX - 3, base_y, cfg['title'], f_title, INK + (255,), track=0.03, feats=jp)
        if sub:
            draw_text(d, x_end - 0.03 * size + 18, base_y, sub, f_sub, INK + (225,), track=0.02, feats=jp)
        y = self.y_eye + 42
        self.rows.append((with_shadow(row, 9, 0.65), y))
        y += size + 46
        # 3) 原曲・クレジット（タグ＋本文）
        f_tag = font(fonts['tag'], 19)
        f_body = font(fonts['body'], 27)
        tag_w, tag_h, colx = 62, 30, TX + 82

        def tag(d, x, yy, s):
            d.rounded_rectangle((x, yy, x + tag_w, yy + tag_h), 5, outline=INK + (150,), width=2)
            w = text_w(s, f_tag, 0.12)
            draw_text(d, x + (tag_w - w) / 2 + 1, yy + 23, s, f_tag, INK + (225,), track=0.12)

        # 原曲とクレジットは、設定が空なら行ごと出さない
        originals = cfg.get('originals_lines') or []
        credits = cfg.get('credits') or []
        self.text_right = 0
        if originals:
            row = Image.new('RGBA', (W, 44 * len(originals) + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
            tag(d, TX, 7, '原曲')
            for i, line in enumerate(originals):
                draw_text(d, colx, 44 * i + 31, line, f_body, INK + (255,), track=0.0, feats=['kern'])
                self.text_right = max(self.text_right, colx + text_w(line, f_body, 0.0, ['kern']))
            self.rows.append((with_shadow(row), y))
            y += 44 * len(originals) + 14
        if credits:
            row = Image.new('RGBA', (W, 54), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
            x = TX
            for lab, val in credits:
                tag(d, x, 7, lab)
                x = draw_text(d, x + 82, 31, val, f_body, INK + (255,), track=0.0, feats=['kern']) + 40
            self.text_right = max(self.text_right, x - 40)
            self.rows.append((with_shadow(row), y))
            y += 58
        self.text_bottom = y - 14
        # タイマー
        self.f_time = font(fonts['time'], 23)
        self.tot_s = f"{int(self.dur) // 60}:{int(self.dur) % 60:02d}"
        self.time_cache = {}
        self.tbox = (TXR - 200, self.y_eye, TXR + 4, self.y_eye + 40)
        # 動き終わったあとの文字とロゴは1枚にまとめておく（毎フレームの合成を軽くする）
        rest = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        for img, ry in self.rows:
            rest.alpha_composite(img, (0, ry))
        self.rows_rest = rest
        self.logo_rest = self.logo_img(LOGO_H, 0)

    def card_at(self, lift):
        """影つきのジャケット。lift（0〜1）が大きいほど浮いて見える：影が遠く、大きく、薄くなる"""
        pad = self.card_pad
        size = JS + pad * 2
        sh = Image.new('L', (size, size), 0)
        oy = 14 + 50 * lift
        ImageDraw.Draw(sh).rounded_rectangle((pad - 4, pad + oy, pad + JS + 4, pad + JS + 16 + oy), 18, fill=round(175 * (1 - 0.4 * lift)))
        card = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        card.putalpha(sh.filter(ImageFilter.GaussianBlur(26 + 24 * lift)))
        card.alpha_composite(self.card_face, (pad, pad))
        return card

    def logo_img(self, h, blur_r, alpha=1.0):
        """白抜きロゴ。blur_r>0 ならレンズのボケ（円形ボケ）をかける。余白込みのRGBAを返す。"""
        w = max(2, round(h * self.logo_ar)); h = max(2, round(h))
        a = np.asarray(self.logo_a.resize((w, h), Image.LANCZOS), dtype=np.float32) / 255.0
        if blur_r >= 0.6:
            p = int(np.ceil(blur_r)) + 3
            a = np.pad(a, p)
            r = blur_r
            k = int(np.ceil(r)) * 2 + 1
            yy, xx = np.mgrid[:k, :k] - k // 2
            disc = np.clip(r + 0.5 - np.sqrt(xx ** 2 + yy ** 2), 0, 1).astype(np.float32)
            disc /= disc.sum()
            a = cv2.filter2D(a, -1, disc, borderType=cv2.BORDER_CONSTANT)
            a = cv2.GaussianBlur(a, (0, 0), max(0.6, r * 0.12))
            self._logo_pad = p
        else:
            self._logo_pad = 0
        a = np.clip(a * alpha, 0, 1)
        out = np.empty(a.shape + (4,), dtype=np.uint8)
        out[..., 0], out[..., 1], out[..., 2] = INK
        out[..., 3] = (a * 255).astype(np.uint8)
        return Image.fromarray(out, 'RGBA')

    # ---------- 音 ----------
    def cut_audio(self, out):
        c = self.cfg
        fo = c.get('fade_out', 2.0)
        # gain_db：AAC にしたときのピークが 0dBFS を超えないように下げる量。YouTube は再生時に約 -14 LUFS まで
        # 下げるので、ここで下げても YouTube での聞こえ方の大きさは変わらない
        af = f"volume={c.get('gain_db', -2.0)}dB,afade=t=in:st=0:d={c.get('fade_in', 0.2)},afade=t=out:st={self.dur - fo}:d={fo}"
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(c['start']), '-t', str(self.dur), '-i', c['audio'],
                        '-af', af, '-c:a', 'pcm_s16le', out], check=True)
        self.spec = self.spectrum(out)

    def spectrum(self, wav):
        y, sr = sf.read(wav)
        m = y.mean(axis=1) if y.ndim > 1 else y
        n_fft = 4096
        win = np.hanning(n_fft)
        freqs = np.fft.rfftfreq(n_fft, 1 / sr)
        edges = np.geomspace(45, 13000, NBARS + 1)
        padd = np.concatenate([np.zeros(n_fft // 2), m, np.zeros(n_fft)])
        out = np.zeros((self.n, NBARS), dtype=np.float32)
        for i in range(self.n):
            c = int(i / FPS * sr)
            mag = np.abs(np.fft.rfft(padd[c:c + n_fft] * win))
            for b in range(NBARS):
                sel = (freqs >= edges[b]) & (freqs < edges[b + 1])
                if not sel.any():
                    sel = np.zeros_like(freqs, bool); sel[np.argmin(np.abs(freqs - edges[b]))] = True
                out[i, b] = 20 * np.log10(np.sqrt((mag[sel] ** 2).mean()) + 1e-6)
        ref = out[int(self.lead * FPS):]          # サビ以降を基準に正規化
        lo, hi = np.percentile(ref, 8, axis=0), np.percentile(ref, 99, axis=0)
        v = np.clip((out - lo) / (hi - lo + 1e-6), 0, 1) ** 1.6
        k = np.array([0.2, 0.6, 0.2])
        v = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 1, mode='edge'), k, mode='valid'), 1, v)
        sm = np.zeros_like(v); prev = np.zeros(NBARS)
        for i in range(self.n):
            prev = np.maximum(v[i], prev * 0.84); sm[i] = prev
        rms = np.array([np.sqrt((m[int(i / FPS * sr):int((i + 1) / FPS * sr)] ** 2).mean() + 1e-12) for i in range(self.n)])
        g = np.clip(rms / (np.percentile(rms, 90) + 1e-9), 0, 1) ** 0.5
        # 低音（45〜110Hz、キックとベース）の包絡。背景の明るさをわずかに脈打たせる
        low = out[:, :9].mean(axis=1)
        rl = low[int(self.lead * FPS):]
        pv = np.clip((low - np.percentile(rl, 20)) / (np.percentile(rl, 98) - np.percentile(rl, 20) + 1e-6), 0, 1) ** 2
        self.pulse = np.zeros(self.n, np.float32); prev = 0.0
        for i in range(self.n):
            prev = max(pv[i], prev * 0.80); self.pulse[i] = prev * g[i]
        return np.clip(sm * 1.3, 0, 1) * g[:, None]

    # ---------- 動的パーツ ----------
    def spectrum_layer(self, i):
        S = 2
        layer = Image.new('RGBA', (SPW * S, SPH * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        pitch = SPW / NBARS; bw = pitch * 0.54; cy = SPH / 2 * S
        prog = (i + 1) / self.n
        for b in range(NBARS):
            h = max(5.0, self.spec[i][b] * SPH)
            x0 = (b * pitch + (pitch - bw) / 2) * S
            col = GOLD + (255,) if (b + 0.5) / NBARS <= prog else INK + (105,)
            d.rounded_rectangle((x0, cy - h * S / 2, x0 + bw * S, cy + h * S / 2), bw * S / 2, fill=col)
        return layer.resize((SPW, SPH), Image.LANCZOS)

    def time_layer(self, sec):
        if sec not in self.time_cache:
            w, h = self.tbox[2] - self.tbox[0], self.tbox[3] - self.tbox[1]
            ov = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
            s = f"{sec // 60}:{sec % 60:02d} / {self.tot_s}"
            tw = text_w(s, self.f_time, 0.08, tnum=True)
            draw_text(d, w - 4 - tw, 24, s, self.f_time, INK + (205,), track=0.08, tnum=True)
            self.time_cache[sec] = with_shadow(ov)
        return self.time_cache[sec]

    @staticmethod
    def fade(img, a):
        if a >= 0.999:
            return img
        out = img.copy()
        out.putalpha(img.getchannel('A').point(lambda v: int(v * a)))
        return out

    # ---------- フレーム ----------
    def background(self, i, t):
        """アンビエント層：全編でゆっくり寄りながら少し下がる。ロゴとジャケットが上がるあいだは逆向き（下）に動く"""
        u = sine_io(t / self.dur)
        s = 1 + 0.05 * u
        dy = 60 * STD((t - self.t_logo0) / (self.land - self.t_logo0)) + 30 * u
        a = 1 / s
        img = self.bg_big.transform((W, H), Image.AFFINE,
                                    (a, 0, self.bw / 2 - W / 2 * a, 0, a, self.bh / 2 - H / 2 * a - dy * a), resample=Image.BILINEAR)
        k = 0.45 + 0.15 * DEC(t / self.t_focus)                            # 冒頭はほの暗い
        k += 0.40 * DEC((t - (self.lead - 0.1)) / 0.6)                     # サビ頭で明るくなる
        k *= 1 + 0.05 * self.pulse[i] * DEC((t - self.lead) / 0.5)         # サビに入ってから低音で脈打つ
        img = ImageEnhance.Brightness(img).enhance(k).convert('RGBA')
        img.alpha_composite(self.shade)
        return img

    # ---------- 冒頭の顔のアップ ----------
    def make_bokeh(self, opt):
        """プリズム調の前ボケ。角の丸い6〜8角形（絞りの形）の玉を、左下から右上へ弧を描く帯に並べる。
        玉の中で色が流れ、縁で R/G/B の大きさが少しずつ違うので虹色ににじむ。玉は一度だけ作り、
        フレームごとには位置だけずらす。返すのは (玉の画像, 中心 x, 中心 y, 上へ流れる速さ) の並び"""
        rng = np.random.default_rng(opt.get('seed', 7))
        palette = opt.get('palette', BOKEH_PALETTE)
        strength = opt.get('strength', 0.78)
        out = []
        for _ in range(opt.get('count', 28)):
            u = rng.uniform(0, 1)
            bx = W * (0.10 + 0.85 * u) + rng.normal(0, 120)
            by = H * (0.92 - 0.80 * u) + rng.normal(0, 170)
            r = rng.uniform(70, 260) * (0.75 + 0.5 * np.exp(-((u - 0.5) / 0.3) ** 2))
            h0 = palette[rng.integers(len(palette))]
            span = rng.uniform(0.10, 0.22) * rng.choice([-1, 1])
            n, rot, soft, ca = int(rng.choice([6, 7, 8])), rng.uniform(0, 1), rng.uniform(10, 40), rng.uniform(0.05, 0.11)
            d = rng.uniform(0, 2 * np.pi); a = rng.uniform(0.10, 0.32) * strength
            size = int(r * 2 + soft * 6 + 8)
            yy, xx = np.mgrid[:size, :size].astype(np.float32) - (size - 1) / 2
            g = np.clip((xx * np.cos(d) + yy * np.sin(d)) / (2 * r) + 0.5, 0, 1)
            rgb = hsv_to_rgb((h0 + span * g) % 1, 0.85)
            ang = np.arctan2(yy, xx) - rot; rr = np.sqrt(xx ** 2 + yy ** 2); sector = 2 * np.pi / n
            shape = 0.65 * rr * np.cos(np.mod(ang, sector) - sector / 2) / np.cos(np.pi / n) + 0.35 * rr   # 角を少し丸めた多角形
            spr = np.zeros((size, size, 3), np.float32)
            for c, sc in enumerate((1 + ca, 1.0, 1 - ca)):            # 赤は外、青は内へずらす（色収差）
                m = np.clip((r * sc - shape) / soft + 0.5, 0, 1)
                m *= 0.78 + 0.22 * np.clip(1 - np.abs(r * sc - shape) / (soft * 1.6), 0, 1)   # 縁がわずかに明るい
                spr[..., c] = m * rgb[..., c] * a
            out.append((spr, bx, by, 70 * (0.6 + u)))
        return out

    def bokeh_layer(self, t):
        """前ボケを線形光で足し合わせ、まわりのにじみを足し、ロゴのまわりを弱めたレイヤー"""
        layer = np.zeros((H, W, 3), np.float32)
        for spr, bx, by, vy in self.bokeh:
            s = spr.shape[0]; x0, y0 = int(bx - s / 2), int(by - vy * t - s / 2)
            xs, ys = max(0, -x0), max(0, -y0); xe, ye = min(s, W - x0), min(s, H - y0)
            if xs < xe and ys < ye:
                layer[y0 + ys:y0 + ye, x0 + xs:x0 + xe] += spr[ys:ye, xs:xe]
        small = cv2.resize(layer, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        glow = cv2.resize(cv2.GaussianBlur(small, (0, 0), 15), (W, H), interpolation=cv2.INTER_LINEAR)
        return (layer + 0.6 * glow) * self.bokeh_hole

    def make_leak(self, opt):
        """四隅から差し込む光（案C）。左上は琥珀、右下は青緑、右上に薄いピンク。
        光はなめらかなので 1/4 の解像度で作って拡大し、3枚を別々に持って時刻ごとに重みだけ変える"""
        yy, xx = np.mgrid[:H // 4, :W // 4].astype(np.float32) * 4

        def blob(cx, cy, rx, ry, col, ang=0.0):
            c, s = np.cos(ang), np.sin(ang)
            u, v = ((xx - cx) * c + (yy - cy) * s) / rx, (-(xx - cx) * s + (yy - cy) * c) / ry
            g = np.exp(-(u ** 2 + v ** 2))[..., None] * np.array(col, np.float32)
            return cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
        self.leak_strength = opt.get('strength', 0.8) if isinstance(opt, dict) else 0.8
        return (blob(-80, -60, 640, 520, (1.0, 0.62, 0.25), 0.6),        # 左上：琥珀
                blob(W + 60, H + 40, 700, 560, (0.25, 0.85, 0.80), 0.6),  # 右下：青緑
                blob(W + 40, 200, 360, 300, (0.95, 0.40, 0.55)) * 0.45)   # 右上：ピンク

    def leak_on(self, fr, t):
        """ライトリークをスクリーン合成で重ねる。0.5秒で差し込み、琥珀と青緑がゆっくり入れ替わるように明滅し、
        サビ頭の0.3秒前から0.6秒で消える（最初のコマは光なしなので、ループの継ぎ目も変わらない）"""
        k = self.leak_strength * DEC(t / 0.5) * (1 - DEC((t - (self.lead - 0.3)) / 0.6))
        if k <= 0.001:
            return fr
        f = 0.75 + 0.25 * np.sin(t * 2.1)
        a, b, c = self.leak
        lay = np.clip((a * f + b * (1.6 - f) + c) * k, 0, 1)
        img = np.asarray(fr, np.float32) / 255
        img = 1 - (1 - img) * (1 - lay)
        return Image.fromarray((img * 255 + 0.5).astype(np.uint8))

    def face_plate(self, t):
        """ジャケットのイラストから顔をアップで切り出す。瞳のアップ（from）からゆっくり引き（to）、
        ロゴにピントが移るにつれて顔はぼけて暗くなる。設定に bokeh があれば手前に前ボケを足す"""
        u = STD(t / self.lead)
        cx, cy, cw = [a + (b - a) * u for a, b in zip(self.face['from'], self.face['to'])]
        ch = cw * 16 / 9
        M = np.float32([[cw / W, 0, cx - cw / 2], [0, ch / H, cy - ch / 2]])
        img = np.clip(cv2.warpAffine(self.jk_np, M, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                                     borderMode=cv2.BORDER_REFLECT), 0, 1)
        pf = STD(t / self.t_focus)
        r = 3 + 11 * pf + 4 * STD((t - self.t_focus) / (self.lead - self.t_focus))
        img = lens_blur(img, r)
        bright, vig = 0.54 - 0.14 * pf, 0.50 + 0.15 * pf
        img = np.clip(img * bright * (1 - vig * self.vig_q) * np.array([0.90, 1.0, 1.06], np.float32), 0, 1)
        # 前ボケ（設定にあるときだけ）：ピントがロゴへ移るにつれてふくらむ。背景を少し落とし、光として足す（線形光）
        k = STD((t - 0.3) / max(0.1, self.t_focus - 0.3))
        if self.bokeh and k > 0:
            lin = (img * (1 - 0.30 * k)) ** 2.2 + self.bokeh_layer(t) * k
            img = np.clip(lin / (1 + 0.6 * np.clip(lin - 0.8, 0, None)), 0, 1) ** (1 / 2.2)
        return Image.fromarray((img * 255).astype(np.uint8)).convert('RGBA')

    def frame(self, i):
        t = i / FPS
        fr = self.background(i, t)
        # 冒頭は顔のアップ。サビ頭から 0.6秒でいつもの背景へ切り替える
        if self.face and t < self.lead + 0.6:
            a = DEC((t - self.lead) / 0.6)
            fp = self.face_plate(t)
            fr = fp if a <= 0 else Image.blend(fp, fr, a)
        # ジャケット：サビ頭から下から上がり、land で着地。浮いているあいだは影が遠く大きい（二次動作）
        pt = (t - self.lead) / (self.land - self.lead)
        if pt > 0:
            pj = DEC(pt)
            if pj >= 0.999:
                card = self.card_rest
            else:
                card = self.card_at(1 - pj)
                sc = 0.96 + 0.04 * pj
                sz = round(card.width * sc)
                card = self.fade(card.resize((sz, sz), Image.BICUBIC), DEC(pt / 0.35))
            cy = JY + JS / 2 + JACKET_RISE * (1 - pj)
            fr.alpha_composite(card, (round(JX + JS / 2 - card.width / 2), round(cy - card.height / 2)))
        # ロゴ：ボケからゆっくりピントが合い（focus）、サビ前のピックアップ（pickup）まで少しずつ寄る。
        # ピックアップで上へ移動して縮み、サビ頭で上がってくるジャケットに場所を譲る
        pf = STD(t / self.t_focus)
        pl = STD((t - self.t_logo0) / (self.t_logo1 - self.t_logo0))
        if pf >= 0.999 and pl >= 0.999:
            lg, cy = self.logo_rest, LOGO_Y + LOGO_H / 2
        else:
            breath = 1.0 + (1 - pf) * 0.09
            push = 1 + 0.035 * sine_io((t - self.t_focus) / max(0.01, self.t_logo0 - self.t_focus))
            h0 = LOGO0_H * push
            h = (h0 + (LOGO_H - h0) * pl) * breath
            cy = LOGO0_CY + ((LOGO_Y + LOGO_H / 2) - LOGO0_CY) * pl
            # 顔のアップがあるときは、ピントが顔からロゴへ移るのに合わせてロゴを 0 から出す
            la = DEC((t - 0.2) / 1.4) if self.face else 0.35 + 0.65 * DEC(t / 0.3)
            lg = self.logo_img(h, (1 - pf) * 46, la)
        fr.alpha_composite(lg, (round(W / 2 - lg.width / 2), round(cy - lg.height / 2)))
        # 波形と文字：ジャケットが上がりきる手前から、下から順に出す
        order = [('spec', None)] + [('row', r) for r in self.rows]
        done = (t - self.t_text - STAGGER * (len(order) - 1)) >= TEXT_DUR
        if done:
            fr.alpha_composite(self.rows_rest)
        for n, (kind, r) in enumerate(order):
            ptx = (t - self.t_text - STAGGER * n) / TEXT_DUR
            if ptx <= 0:
                continue
            p = DEC(ptx)
            dy = round((1 - p) * TEXT_RISE)
            if kind == 'spec':
                fr.alpha_composite(self.fade(self.spectrum_layer(i), p), (SPX, SPY + dy))
                continue
            if not done:
                img, ry = r
                fr.alpha_composite(self.fade(img, p), (0, ry + dy))
            if n == 1:
                fr.alpha_composite(self.fade(self.time_layer(int(t)), p), (self.tbox[0], self.tbox[1] + dy))
        fr = fr.convert('RGB')
        if self.leak is not None and t < self.lead + 0.4:
            fr = self.leak_on(fr, t)
        # 退場：最後の outro 秒で冒頭と同じ暗さまで落とす（ショートのループで冒頭へ自然につながる）
        if t > self.t_out:
            fr = ImageEnhance.Brightness(fr).enhance(1 - 0.55 * ACC((t - self.t_out) / (self.dur - self.t_out)))
        return fr


_SH = None   # 書き出し時に fork した子プロセスへ渡す Short


def _frame_bytes(i):
    return _SH.frame(i).tobytes()


def main():
    cfg = json.load(open(sys.argv[1])); mode = sys.argv[2]
    work = cfg.get('work', 'work'); os.makedirs(work, exist_ok=True)
    sh = Short(cfg)
    clip = os.path.join(work, 'clip2.wav')
    sh.cut_audio(clip)
    if mode == '--frames':
        for ts in sys.argv[3].split(','):
            i = min(sh.n - 1, int(round(float(ts) * FPS)))
            p = os.path.join(work, f't2_{float(ts):05.2f}.png'); sh.frame(i).save(p)
        print('text_bottom', sh.text_bottom, 'text_right', round(sh.text_right), 'frames', sh.n)
        return
    out = cfg['out']
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    tmp = os.path.join(work, 'video2_tmp.mp4')
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                            '-i', '-', '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', tmp], stdin=subprocess.PIPE)
    global _SH
    _SH = sh
    with multiprocessing.get_context('fork').Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for buf in pool.imap(_frame_bytes, range(sh.n), chunksize=6):
            enc.stdin.write(buf)
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit('encode failed')
    tmp2 = os.path.join(work, 'final2_tmp.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-i', clip, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', tmp2], check=True)
    os.replace(tmp2, out)
    print('wrote', out)


if __name__ == '__main__':
    main()
