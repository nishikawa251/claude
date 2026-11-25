"""サビ探し用の図を作る。usage: scan.py <曲ID>
  1) 曲全体のボーカルの音量（灰色）、ミックスの音量（黒線）、音の高さ（赤点）を40秒ずつの段で描く
  2) 歌の音の高さの並びの繰り返し（右上がりの線＝同じ旋律が時間をずらして繰り返される）を描く
  3) テンポと拍の時刻を保存する
"""
import sys, os, numpy as np, soundfile as sf, librosa, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sid = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # kalanchoe-shorts/
VOC, ANA = os.path.join(ROOT, 'work', 'voc'), os.path.join(ROOT, 'work', 'ana')   # 分離したボーカルと解析結果の置き場
mix_p = f'{ROOT}/src/{sid}.wav'; voc_p = f'{VOC}/voc_{sid}.wav'; out = f'{ANA}/{sid}'
os.makedirs(out, exist_ok=True)
x, sr = sf.read(mix_p, dtype='float32'); v, _ = sf.read(voc_p, dtype='float32')
xm = x.mean(1); vm = v.mean(1)
# 拍
_, beats = librosa.beat.beat_track(y=xm, sr=sr, hop_length=256, tightness=300)
bt = librosa.frames_to_time(beats, sr=sr, hop_length=256); beat = float(np.median(np.diff(bt)))
np.save(f'{out}/beats.npy', bt)
# ボーカルの音の高さ（10ms ごと）
y16 = librosa.resample(vm, orig_sr=sr, target_sr=16000)
f0, _, _ = librosa.pyin(y16, fmin=140, fmax=1100, sr=16000, frame_length=1024, hop_length=160)
midi = 69 + 12 * np.log2(f0 / 440); np.save(f'{out}/midi.npy', midi)
def db(sig, hop):
    r = librosa.feature.rms(y=sig, frame_length=hop * 4, hop_length=hop)[0]; return 20 * np.log10(r + 1e-9)
dv = db(y16, 160); dm = db(librosa.resample(xm, orig_sr=sr, target_sr=16000), 160)
t = np.arange(len(dv)) * 0.01; tm = np.arange(len(dm)) * 0.01; tf = np.arange(len(midi)) * 0.01
dur = len(xm) / sr; rs = 40; rows = int(np.ceil(dur / rs))
fig, axs = plt.subplots(rows, 1, figsize=(22, 2.4 * rows))
for r, ax in enumerate(np.atleast_1d(axs)):
    a, b = r * rs, (r + 1) * rs; s = (t >= a) & (t < b); sm = (tm >= a) & (tm < b); sf_ = (tf >= a) & (tf < b)
    ax.fill_between(t[s], -60, dv[s], color='#9ab', lw=0); ax.plot(tm[sm], dm[sm], color='#333', lw=0.4)
    ax2 = ax.twinx(); ax2.plot(tf[sf_], midi[sf_], '.', ms=1.8, color='#c30'); ax2.set_ylim(48, 88)
    ax.set_xlim(a, b); ax.set_ylim(-60, -3); ax.set_xticks(np.arange(a, b + 0.01, 2)); ax.grid(alpha=0.35)
plt.tight_layout(); plt.savefig(f'{out}/full.png', dpi=50); plt.close()
# 旋律の繰り返し：0.25秒ごとの音の高さで、4秒の窓が一致する割合
st = 25; P = np.array([np.nanmedian(midi[i:i + st]) if np.isfinite(midi[i:i + st]).sum() > 5 else np.nan for i in range(0, len(midi), st)])
N = len(P); M = np.zeros((N, N), np.float32); win = np.ones(16) / 16
for d in range(8, N - 16):
    a, b = P[:-d], P[d:]; ok = np.isfinite(a) & np.isfinite(b)
    eq = (ok & (np.abs(np.nan_to_num(a) - np.nan_to_num(b)) < 1.0)).astype(np.float32)
    cnt = np.convolve(ok.astype(np.float32), win, 'same'); s_ = np.convolve(eq, win, 'same') / np.maximum(cnt, 1e-3)
    s_[cnt < 0.4] = 0
    idx = np.arange(N - d); M[idx, idx + d] = s_; M[idx + d, idx] = s_
plt.figure(figsize=(12, 12)); plt.imshow(M, origin='lower', cmap='magma', vmin=0.3, vmax=1, extent=[0, N * 0.25, 0, N * 0.25])
plt.xticks(np.arange(0, N * 0.25, 10)); plt.yticks(np.arange(0, N * 0.25, 10)); plt.grid(alpha=0.25)
plt.title(f'{sid}  beat {beat:.4f}s ({60 / beat:.1f} BPM)'); plt.savefig(f'{out}/rep.png', dpi=55); plt.close()
print(sid, f'dur {dur:.1f}s beat {beat:.4f}s bpm {60 / beat:.1f}')
