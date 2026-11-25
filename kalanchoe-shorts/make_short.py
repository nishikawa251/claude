#!/usr/bin/env python3
"""KALANCHOE RECORDS ショート動画ジェネレーター v3（ジャケット＋音源型・冒頭アニメーション付き）
  python3 make_short.py potd.json --frames 0,0.5,1.2     # テストフレームPNGを work/ に出す
  python3 make_short.py potd.json --render               # 本番書き出し（1080x1920 / 30fps）
フォントは既定でこのスクリプトと同じ階層の fonts/ から読む（環境変数 KAL_FONTS で変更可）。
"""
import json, os, subprocess, sys
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
# 冒頭ロゴ（中央・大）
LOGO0_H, LOGO0_CY = 430, 850


def ease_out(p):
    p = min(1.0, max(0.0, p)); return 1 - (1 - p) ** 3


def ease_out5(p):
    p = min(1.0, max(0.0, p)); return 1 - (1 - p) ** 4


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


class Short:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dur = cfg['duration']
        self.n = int(round(self.dur * FPS))
        self.lead = cfg['lead']                 # サビ頭までの秒数
        self.t_slide0 = cfg['slide_start']      # ジャケットが動き出す時刻
        self.t_slide1 = self.lead               # サビ頭で着地
        self.t_focus = cfg.get('focus_time', 1.15)
        self.build_static()

    # ---------- 静的パーツ ----------
    def build_static(self):
        cfg = self.cfg
        jk = Image.open(cfg['jacket']).convert('RGB')
        bg = jk.resize((H, H), Image.LANCZOS).crop(((H - W) // 2, 0, (H - W) // 2 + W, H))
        bg = bg.filter(ImageFilter.GaussianBlur(52))
        bg = ImageEnhance.Brightness(bg).enhance(0.50)
        bg = ImageEnhance.Color(bg).enhance(1.12)
        yy = np.arange(H, dtype=np.float32)
        g = np.clip((yy - 1020) / (H - 1020), 0, 1) ** 1.2 * 0.66
        g = np.maximum(g, np.clip((230 - yy) / 230, 0, 1) ** 1.5 * 0.32)
        a = np.asarray(bg, dtype=np.float32) * (1 - g[:, None, None])
        self.bg = Image.fromarray(a.astype(np.uint8))

        # ジャケット（影つきカード）
        pad = 70
        card = Image.new('RGBA', (JS + pad * 2, JS + pad * 2), (0, 0, 0, 0))
        sh = Image.new('RGBA', card.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad - 4, pad + 14, pad + JS + 4, pad + JS + 30), 18, fill=(0, 0, 0, 175))
        card = Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(26)))
        j = jk.resize((JS, JS), Image.LANCZOS).convert('RGBA')
        m = Image.new('L', (JS * 2, JS * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, JS * 2 - 1, JS * 2 - 1), 20, fill=255)
        j.putalpha(m.resize((JS, JS), Image.LANCZOS))
        card.alpha_composite(j, (pad, pad))
        ImageDraw.Draw(card).rounded_rectangle((pad, pad, pad + JS - 1, pad + JS - 1), 10, outline=(255, 255, 255, 44), width=1)
        self.card, self.card_pad = card, pad

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
        # 2) 曲名
        size = 68
        while True:
            f_title = font(fonts['title'], size)
            if text_w(cfg['title'], f_title, 0.03, jp) <= TXR - TX or size <= 40:
                break
            size -= 1
        row = Image.new('RGBA', (W, size + 44), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
        draw_text(d, TX - 3, round(6 + 1.16 * size), cfg['title'], f_title, INK + (255,), track=0.03, feats=jp)
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

        row = Image.new('RGBA', (W, 44 * len(cfg['originals_lines']) + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
        tag(d, TX, 7, '原曲')
        for i, line in enumerate(cfg['originals_lines']):
            draw_text(d, colx, 44 * i + 31, line, f_body, INK + (255,), track=0.0, feats=['kern'])
        self.rows.append((with_shadow(row), y))
        y += 44 * len(cfg['originals_lines']) + 14
        row = Image.new('RGBA', (W, 54), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
        x = TX
        for lab, val in cfg['credits']:
            tag(d, x, 7, lab)
            x = draw_text(d, x + 82, 31, val, f_body, INK + (255,), track=0.0, feats=['kern']) + 40
        self.rows.append((with_shadow(row), y))
        self.text_bottom = y + 44
        self.text_right = max(text_w(l, f_body, 0.0, ['kern']) for l in cfg['originals_lines']) + colx
        # タイマー
        self.f_time = font(fonts['time'], 23)
        self.tot_s = f"{int(self.dur) // 60}:{int(self.dur) % 60:02d}"
        self.time_cache = {}
        # 最終状態の静止ベース（冒頭アニメ後の高速パス用）
        base = self.bg.convert('RGBA')
        base.alpha_composite(self.card, (JX - pad, JY - pad))
        base.alpha_composite(self.logo_img(LOGO_H, 0), ((W - round(LOGO_H * self.logo_ar)) // 2, LOGO_Y))
        for img, ry in self.rows:
            base.alpha_composite(img, (0, ry))
        self.base = base.convert('RGB')
        self.sbox = (SPX, SPY, SPX + SPW, SPY + SPH)
        self.tbox = (TXR - 200, self.y_eye, TXR + 4, self.y_eye + 40)
        self.base_s = self.base.crop(self.sbox)
        self.base_t = self.base.crop(self.tbox)

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
        af = f"volume=-2dB,afade=t=in:st=0:d={c.get('fade_in', 0.2)},afade=t=out:st={self.dur - fo}:d={fo}"
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
    def frame(self, i):
        t = i / FPS
        t_text_end = self.t_slide1 + 1.0
        if t >= t_text_end:                                   # 高速パス
            fr = self.base.copy()
            s = self.base_s.convert('RGBA'); s.alpha_composite(self.spectrum_layer(i))
            fr.paste(s.convert('RGB'), self.sbox[:2])
            tm = self.base_t.convert('RGBA'); tm.alpha_composite(self.time_layer(int(t)))
            fr.paste(tm.convert('RGB'), self.tbox[:2])
            return fr
        # 冒頭アニメーション
        k = 0.45 + 0.55 * ease_out(t / 0.9)
        fr = ImageEnhance.Brightness(self.bg).enhance(k).convert('RGBA')
        ps = ease_out5((t - self.t_slide0) / (self.t_slide1 - self.t_slide0)) if t >= self.t_slide0 else 0.0
        # ジャケット：下からスライド
        if ps > 0:
            y = JY + (1 - ps) * (H - JY + 40)
            fr.alpha_composite(self.card, (JX - self.card_pad, int(round(y)) - self.card_pad))
        # ロゴ：ボケ→ピント、のち上へ
        pf = ease_out(t / self.t_focus)
        blur = (1 - pf) * 46
        breath = 1.0 + (1 - pf) * 0.09
        h = (LOGO0_H + (LOGO_H - LOGO0_H) * ps) * breath
        cy = LOGO0_CY + ((LOGO_Y + LOGO_H / 2) - LOGO0_CY) * ps
        la = 0.35 + 0.65 * min(1.0, t / 0.3)
        lg = self.logo_img(h, blur, la)
        fr.alpha_composite(lg, (int(round(W / 2 - lg.width / 2)), int(round(cy - lg.height / 2))))
        # スペクトラムと文字：サビ頭から順に出す
        order = [('spec', None)] + [('row', r) for r in self.rows]
        for n, (kind, r) in enumerate(order):
            p = ease_out((t - self.t_slide1 - 0.07 * n) / 0.42)
            if p <= 0:
                continue
            dy = int(round((1 - p) * 20))
            if kind == 'spec':
                fr.alpha_composite(self.fade(self.spectrum_layer(i), p), (SPX, SPY + dy))
            else:
                img, ry = r
                fr.alpha_composite(self.fade(img, p), (0, ry + dy))
                if n == 1:
                    fr.alpha_composite(self.fade(self.time_layer(int(t)), p), (self.tbox[0], self.tbox[1] + dy))
        return fr.convert('RGB')


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
    for i in range(sh.n):
        enc.stdin.write(sh.frame(i).tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit('encode failed')
    tmp2 = os.path.join(work, 'final2_tmp.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-i', clip, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '320k', '-shortest', '-movflags', '+faststart', tmp2], check=True)
    os.replace(tmp2, out)
    print('wrote', out)


if __name__ == '__main__':
    main()
