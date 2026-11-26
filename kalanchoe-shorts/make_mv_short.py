#!/usr/bin/env python3
"""MV から縦型ショートを作る（MV を縦の画面いっぱいに中央で切り抜き、文字は重ねない）。
  python3 make_mv_short.py mv/potd.json

設定（mv/*.json）
  song    ジャケット版ショートの設定（区間の終わりと、音の処理 gain_db / fade_out を使う）
  start   始まり（曲の秒）。省くとジャケット版と同じ。MV 版は約1分にするので、サビの約1分前の間奏の小節頭にしている
  mv      MV の動画ファイル（1920x1080）
  offset  曲の時刻 = MV の時刻 + offset（tools/mv_align.py で測る）
  crop_x  切り抜きの左端（元の映像の px）。省くと中央
  layout  "fit" にすると横幅いっぱい（MV を削らずに幅 1080 に置き、上下は同じ映像のぼかしで埋める）
  fit_src_w / fit_cx  fit のとき、元の映像の幅 fit_src_w（中心 fit_cx）だけを切り抜いて幅いっぱいに置く（省くと全体）
  fit_y   fit のときの MV の上端（省くと、曲情報ありは 300、なしは真ん中）
  info    true にすると、fit のとき上にロゴ、MV の下に曲情報（小見出し・曲名・原曲・作詞編曲）を載せる。MV の上端は y=300
          layout "stack" では常に載せる
  layout  "stack" にすると、同じ MV を2つ上下に並べる（幅 940、角丸と影はジャケット版のカードと同じ）。上にロゴ、下に曲情報
  crop    "track" にすると、tools/mv_track.py が作った mv/<name>.track.json のコマごとの位置で切り抜く（自動追従）
  track   自動追従の位置のファイル（crop が "track" のとき）
  out     書き出し先

音は MV の音声ではなく、ジャケット版と同じ CD 音源から同じ処理で切り出す。
映像の fps は MV のまま（24 / 23.976 / 59.94）。頭は 0.25秒、終わりは音のフェードアウトと同じ長さで暗転する。
"""
import json, os, subprocess, sys
import numpy as np

W, H = 1080, 1920
FIT_Y_INFO = 300          # 曲情報を載せるときの MV の上端（ロゴの下）


def info_overlay(m, c, mv_bottom):
    """ロゴ（上）と曲情報（MV の下）を1枚の透明な画像にする。文字の組み方はジャケット版（make_short.py）と同じ"""
    from PIL import Image
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import make_short as ms
    cfg = dict(c); cfg['work'] = 'work/mvfit'; os.makedirs('work/mvfit', exist_ok=True)
    sh = ms.Short(cfg)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    img.alpha_composite(sh.shade)                                        # 上下を少し暗く（文字を読みやすく）
    lg = sh.logo_rest
    img.alpha_composite(lg, (round(W / 2 - lg.width / 2), round(ms.LOGO_Y + ms.LOGO_H / 2 - lg.height / 2)))
    dy = (mv_bottom + 36) - sh.y_eye                                     # 小見出しを MV のすぐ下に
    for row, y in sh.rows:
        img.alpha_composite(row, (0, y + dy))
    out = os.path.join('work/mvfit', os.path.splitext(os.path.basename(m['out']))[0] + '_overlay.png')
    img.save(out); print('info bottom y', sh.text_bottom + dy)
    return out


STACK_W, STACK_Y, STACK_GAP, STACK_R = 940, 212, 16, 14


def stack_layers(m, c, fw, fh, ys):
    """2つ並べる版の下敷き（上下の暗がりとカードの影）、上掛け（ロゴ・曲情報・カードの細い縁）、角丸のマスクを作る"""
    from PIL import Image, ImageDraw, ImageFilter
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import make_short as ms
    cfg = dict(c); cfg['work'] = 'work/mvfit'; os.makedirs('work/mvfit', exist_ok=True)
    sh = ms.Short(cfg)
    x0 = (W - fw) // 2
    under = Image.new('RGBA', (W, H), (0, 0, 0, 0)); under.alpha_composite(sh.shade)
    shd = Image.new('L', (W, H), 0); d = ImageDraw.Draw(shd)
    for y in ys:
        d.rounded_rectangle((x0 - 4, y + 14, x0 + fw + 4, y + fh + 16 + 14), 18, fill=175)
    sl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sl.putalpha(shd.filter(ImageFilter.GaussianBlur(26)))
    under.alpha_composite(sl)
    over = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(over)
    for y in ys:
        d.rounded_rectangle((x0, y, x0 + fw - 1, y + fh - 1), STACK_R, outline=(255, 255, 255, 44), width=1)
    lg = sh.logo_rest
    over.alpha_composite(lg, (round(W / 2 - lg.width / 2), round(ms.LOGO_Y + ms.LOGO_H / 2 - lg.height / 2)))
    dy = (ys[-1] + fh + 34) - sh.y_eye
    for row, y in sh.rows:
        over.alpha_composite(row, (0, y + dy))
    mk = Image.new('L', (fw * 2, fh * 2), 0)
    ImageDraw.Draw(mk).rounded_rectangle((0, 0, fw * 2 - 1, fh * 2 - 1), STACK_R * 2, fill=255)
    mk = mk.resize((fw, fh), Image.LANCZOS)
    base = os.path.join('work/mvfit', os.path.splitext(os.path.basename(m['out']))[0])
    under.save(base + '_under.png'); over.save(base + '_over.png'); mk.save(base + '_mask.png')
    print('info bottom y', sh.text_bottom + dy)
    return base + '_under.png', base + '_over.png', base + '_mask.png'


def render_stack(m, c, st, dur, fi, fo, mv_st, sw, sh, out):
    fw = STACK_W; fh = round(fw * sh / sw / 2) * 2
    ys = [STACK_Y, STACK_Y + fh + STACK_GAP]
    under, over, mask = stack_layers(m, c, fw, fh, ys); x0 = (W - fw) // 2
    fc = (f"[0:v]split=2[a][b];"
          f"[a]scale=-2:{H}:flags=bicubic,crop={W}:{H},scale={W // 8}:{H // 8},gblur=sigma=6,scale={W}:{H}:flags=bicubic,"
          f"eq=brightness=-0.06:saturation=1.05,colorchannelmixer=rr=0.55:gg=0.55:bb=0.55[bg0];"
          f"[bg0][2:v]overlay=0:0[bg];"
          f"[4:v]format=gray,split=2[m1][m2];"
          f"[b]scale={fw}:{fh}:flags=lanczos,format=rgba,split=2[f1][f2];"
          f"[f1][m1]alphamerge[c1];[f2][m2]alphamerge[c2];"
          f"[bg][c1]overlay={x0}:{ys[0]}[t1];[t1][c2]overlay={x0}:{ys[1]}[t2];[t2][3:v]overlay=0:0,setsar=1,format=yuv420p,"
          f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - fo:.3f}:d={fo}[v]")
    af = f"volume={c.get('gain_db', -2.0)}dB,afade=t=in:st=0:d={fi},afade=t=out:st={dur - fo:.3f}:d={fo}"
    loop = lambda p: ['-loop', '1', '-t', f'{dur:.3f}', '-i', p]
    subprocess.run(['ffmpeg', '-y', '-v', 'error',
                    '-ss', f'{mv_st:.3f}', '-t', f'{dur:.3f}', '-i', m['mv'],
                    '-ss', f'{st:.3f}', '-t', f'{dur:.3f}', '-i', c['audio'], *loop(under), *loop(over), *loop(mask),
                    '-filter_complex', fc, '-map', '[v]', '-map', '1:a', '-af', af,
                    '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                    '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', '-t', f'{dur:.3f}', out], check=True)
    print('wrote', out)


def main():
    m = json.load(open(sys.argv[1], encoding='utf-8'))
    c = json.load(open(m['song'], encoding='utf-8'))
    end = c['start'] + c['duration']                 # 終わりはジャケット版と同じ（サビの終わり）
    st = m.get('start', c['start'])                  # 始まりは MV 版だけ前に延ばせる（約1分にする）
    dur = round(end - st, 3)
    fo, fi = c.get('fade_out', 1.2), m.get('fade_in', c.get('fade_in', 0.04))
    mv_st = st - m['offset']
    # 縦いっぱいにするとき、元の映像で使う幅（1080 の高さを 1920 に広げるので 1080*1080/1920 = 608px）
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                            '-of', 'csv=p=0', m['mv']], capture_output=True, text=True).stdout.strip().split(',')
    sw, sh = int(probe[0]), int(probe[1])
    cw = round(sh * W / H / 2) * 2
    x = m.get('crop_x')
    x = (sw - cw) // 2 if x is None else int(x)
    out = m['out']; os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    if m.get('crop') == 'track':
        return render_tracked(m, c, st, dur, fi, fo, sw, sh, cw, out)
    if m.get('layout') == 'stack':
        return render_stack(m, c, st, dur, fi, fo, mv_st, sw, sh, out)
    if m.get('layout') == 'fit':
        # 横幅いっぱい：MV を削らずに幅 1080 に置き（16:9 なら高さ 608）、上下は同じ映像を縦いっぱいに拡大してぼかし、暗くして埋める
        srcw = int(m.get('fit_src_w', sw)); srcx = int(m.get('fit_cx', sw / 2) - srcw / 2)   # 元の映像のどの幅を見せるか
        srcx = max(0, min(sw - srcw, srcx))
        fh = round(W * sh / srcw / 2) * 2
        info = m.get('info', False)
        fy = int(m.get('fit_y', FIT_Y_INFO if info else (H - fh) // 2))
        extra_in, ov = [], ''
        if info:
            png = info_overlay(m, c, fy + fh)
            extra_in = ['-loop', '1', '-t', f'{dur:.3f}', '-i', png]
            ov = '[ov0];[ov0][2:v]overlay=0:0'
        fc = (f"[0:v]split=2[a][b];"
              f"[a]scale=-2:{H}:flags=bicubic,crop={W}:{H},scale={W // 8}:{H // 8},gblur=sigma=6,scale={W}:{H}:flags=bicubic,"
              f"eq=brightness=-0.06:saturation=1.05,colorchannelmixer=rr=0.55:gg=0.55:bb=0.55[bg];"
              f"[b]crop={srcw}:{sh}:{srcx}:0,scale={W}:{fh}:flags=lanczos[fg];[bg][fg]overlay=0:{fy}{ov},setsar=1,"
              f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - fo:.3f}:d={fo}[v]")
        af = f"volume={c.get('gain_db', -2.0)}dB,afade=t=in:st=0:d={fi},afade=t=out:st={dur - fo:.3f}:d={fo}"
        subprocess.run(['ffmpeg', '-y', '-v', 'error',
                        '-ss', f'{mv_st:.3f}', '-t', f'{dur:.3f}', '-i', m['mv'],
                        '-ss', f'{st:.3f}', '-t', f'{dur:.3f}', '-i', c['audio'], *extra_in,
                        '-filter_complex', fc, '-map', '[v]', '-map', '1:a', '-af', af,
                        '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                        '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', '-t', f'{dur:.3f}', out], check=True)
        print('wrote', out); return
    vf = (f"crop={cw}:{sh}:{x}:0,scale={W}:{H}:flags=lanczos,setsar=1,"
          f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - fo:.3f}:d={fo}")
    af = f"volume={c.get('gain_db', -2.0)}dB,afade=t=in:st=0:d={fi},afade=t=out:st={dur - fo:.3f}:d={fo}"
    subprocess.run(['ffmpeg', '-y', '-v', 'error',
                    '-ss', f'{mv_st:.3f}', '-t', f'{dur:.3f}', '-i', m['mv'],
                    '-ss', f'{st:.3f}', '-t', f'{dur:.3f}', '-i', c['audio'],
                    '-map', '0:v', '-map', '1:a', '-vf', vf, '-af', af,
                    '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                    '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', '-t', f'{dur:.3f}', out], check=True)
    print('wrote', out)


def render_tracked(m, c, st, dur, fi, fo, sw, sh, cw, out):
    """コマごとに映す範囲を変えて書き出す（自動追従）。track.json の cx（中心）と vw（映す幅、元の映像の px）を使う。
    vw が縦いっぱいの幅より広いとき（文字が広い場面で引いているとき）は、映像を画面の真ん中に置き、
    上下は同じ映像を拡大してぼかしたもので埋める（境目は少しぼかす）。位置は小数のまま使い、パンに段がつかないようにする"""
    import cv2
    tr = json.load(open(m['track'], encoding='utf-8')); fps = tr['fps']
    if 'cx' in tr: cxs, vws = tr['cx'], tr['vw']
    else: cxs, vws = [x + cw / 2 for x in tr['x']], [cw] * len(tr['x'])
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{st - m["offset"]:.3f}', '-t', f'{dur:.3f}', '-i', m['mv'],
                            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    tmp = out + '.video.mp4'
    num, den = (24, 1) if abs(fps - 24) < 1e-3 else (round(fps * 1001), 1001)
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', f'{num}/{den}',
                            '-i', '-', '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', tmp], stdin=subprocess.PIPE)
    fsz = sw * sh * 3; i = 0; full = H / sh; ones = np.ones((sh, sw), np.float32)
    while True:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz: break
        f = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
        j = min(i, len(cxs) - 1); cx, vw = cxs[j], vws[j]
        if vw <= cw + 1:
            M = np.float32([[full, 0, W / 2 - full * cx], [0, full, 0]])
            img = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        else:
            # 上下を埋める背景：縦いっぱいにしたものを縮めてぼかし、暗くする
            small = cv2.resize(f, (sw // 8, sh // 8), interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), 6)
            Mb = np.float32([[full / 8 * 8 / 8, 0, 0], [0, 1, 0]])
            sb = full * 8 * 1.05
            Mb = np.float32([[sb, 0, W / 2 - sb * cx / 8], [0, sb, H / 2 - sb * sh / 16]])
            bg = cv2.warpAffine(small, Mb, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) * 0.5
            sc = W / vw; y0 = (H - sh * sc) / 2
            M = np.float32([[sc, 0, W / 2 - sc * cx], [0, sc, y0]])
            fg = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
            mk = cv2.warpAffine(ones, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            mk = cv2.GaussianBlur(mk, (0, 0), 6)[..., None]
            img = np.clip(bg * (1 - mk) + fg * mk, 0, 255).astype(np.uint8)
        t = i / fps; kk = min(1.0, t / 0.25, max(0.0, (dur - t) / fo))
        if kk < 1: img = (img.astype(np.float32) * kk).astype(np.uint8)
        enc.stdin.write(img.tobytes()); i += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    af = f"volume={c.get('gain_db', -2.0)}dB,afade=t=in:st=0:d={fi},afade=t=out:st={dur - fo:.3f}:d={fo}"
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-ss', f'{st:.3f}', '-t', f'{dur:.3f}', '-i', c['audio'],
                    '-map', '0:v', '-map', '1:a', '-af', af, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k',
                    '-movflags', '+faststart', '-t', f'{dur:.3f}', out], check=True)
    os.remove(tmp); print('wrote', out, 'frames', i)

if __name__ == '__main__':
    main()
