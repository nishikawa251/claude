#!/usr/bin/env python3
"""MV から縦型ショートを作る（MV を縦の画面いっぱいに中央で切り抜き、文字は重ねない）。
  python3 make_mv_short.py mv/potd.json

設定（mv/*.json）
  song    ジャケット版ショートの設定（区間の終わりと、音の処理 gain_db / fade_out を使う）
  start   始まり（曲の秒）。省くとジャケット版と同じ。MV 版は約1分にするので、サビの約1分前の間奏の小節頭にしている
  mv      MV の動画ファイル（1920x1080）
  offset  曲の時刻 = MV の時刻 + offset（tools/mv_align.py で測る）
  crop_x  切り抜きの左端（元の映像の px）。省くと中央
  crop    "track" にすると、tools/mv_track.py が作った mv/<name>.track.json のコマごとの位置で切り抜く（自動追従）
  track   自動追従の位置のファイル（crop が "track" のとき）
  out     書き出し先

音は MV の音声ではなく、ジャケット版と同じ CD 音源から同じ処理で切り出す。
映像の fps は MV のまま（24 / 23.976 / 59.94）。頭は 0.25秒、終わりは音のフェードアウトと同じ長さで暗転する。
"""
import json, os, subprocess, sys
import numpy as np

W, H = 1080, 1920


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
    """コマごとに切り抜き位置を変えて書き出す（自動追従）。位置は小数のまま使い、ゆっくりしたパンでも段がつかないようにする"""
    import cv2
    tr = json.load(open(m['track'], encoding='utf-8')); xs = tr['x']; fps = tr['fps']
    s = H / sh
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{st - m["offset"]:.3f}', '-t', f'{dur:.3f}', '-i', m['mv'],
                            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    tmp = out + '.video.mp4'
    num, den = (24, 1) if abs(fps - 24) < 1e-3 else (round(fps * 1001), 1001)
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', f'{num}/{den}',
                            '-i', '-', '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', tmp], stdin=subprocess.PIPE)
    fsz = sw * sh * 3; i = 0
    while True:
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz: break
        f = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
        x = xs[min(i, len(xs) - 1)]
        M = np.float32([[s, 0, -s * x], [0, s, 0]])
        img = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        t = i / fps; k = min(1.0, t / 0.25, max(0.0, (dur - t) / fo))
        if k < 1: img = (img.astype(np.float32) * k).astype(np.uint8)
        enc.stdin.write(img.tobytes()); i += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    af = f"volume={c.get('gain_db', -2.0)}dB,afade=t=in:st=0:d={fi},afade=t=out:st={dur - fo:.3f}:d={fo}"
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-ss', f'{st:.3f}', '-t', f'{dur:.3f}', '-i', c['audio'],
                    '-map', '0:v', '-map', '1:a', '-af', af, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k',
                    '-movflags', '+faststart', '-t', f'{dur:.3f}', out], check=True)
    os.remove(tmp); print('wrote', out, 'frames', i)


if __name__ == '__main__':
    main()
