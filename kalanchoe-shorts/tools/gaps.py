"""a〜b 秒の歌の音量と音の高さを細かく出し、歌の切れ目（息つぎ）を一覧にする。usage: gaps.py <曲ID> a b [step] [show]
show を付けると細かい表も出す。拍の時刻も出す。"""
import sys, os, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # kalanchoe-shorts/
VOC, ANA = os.path.join(ROOT, 'work', 'voc'), os.path.join(ROOT, 'work', 'ana')   # 分離したボーカルと解析結果の置き場
sid, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
step = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
show = len(sys.argv) > 5
v, sr = sf.read(f'{VOC}/voc_{sid}.wav', start=int(a * 44100), frames=int((b - a) * 44100)); m = v.mean(1)
midi = np.load(f'{ANA}/{sid}/midi.npy'); bt = np.load(f'{ANA}/{sid}/beats.npy')
xs = np.arange(a, b - step / 2, step); rows = []
for x in xs:
    s = m[int((x - a) * sr):int((x - a + step) * sr)]; d = 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9)
    p = midi[int(x / 0.01):int((x + step) / 0.01)]; p = p[~np.isnan(p)]
    rows.append((x, d, np.median(p) if len(p) else None))
    if show: print(f"{x:7.2f} {d:6.1f}dB {('%5.1f' % np.median(p)) if len(p) else '   - '} " + '#' * int(max(0, d + 50)))
print('beats:', ' '.join(f'{t:.2f}' for t in bt[(bt >= a) & (bt <= b)]))
print('gaps (vocal < -28dB):'); g = None
for x, d, p in rows:
    if d < -28 and g is None: g = x
    if d >= -28 and g is not None: print(f'  {g:.2f}〜{x:.2f} ({x - g:.2f}s)'); g = None
if g is not None: print(f'  {g:.2f}〜{b:.2f} (end)')
