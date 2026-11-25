"""MV の音と曲の音源を照らし合わせて、時刻のずれを測る。usage: mv_align.py mv.mp4 song.wav
出力の offset は「曲の時刻 = MV の時刻 + offset」。曲の途中でずれていないかも、60秒と150秒あたりで確かめる。"""
import sys, subprocess, numpy as np
from scipy.signal import fftconvolve

SR = 4000


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


a, b = load(sys.argv[1]), load(sys.argv[2])
c = fftconvolve(b, a[::-1], mode='full'); lag = int(np.argmax(c)) - (len(a) - 1); off = lag / SR
s, o = max(0, lag), max(0, -lag); n = min(len(b) - s, len(a) - o)
r = np.corrcoef(a[o:o + n], b[s:s + n])[0, 1]


def local(t0):
    seg = b[int(t0 * SR):int((t0 + 20) * SR)]; i0 = int((t0 - off) * SR)
    win = a[max(0, i0 - SR):i0 + len(seg) + SR]; cc = fftconvolve(win, seg[::-1], mode='valid')
    return round((int(np.argmax(cc)) + max(0, i0 - SR)) / SR - (t0 - off), 3)


print(f'offset {off:.3f}  (corr {r:.3f})  drift@60s {local(60)}  drift@150s {local(150)}')
