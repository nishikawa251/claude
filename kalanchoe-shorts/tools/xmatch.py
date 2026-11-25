"""区間 a〜b の歌の旋律が、曲のほかの場所のどこで繰り返されるか。usage: xmatch.py <曲ID> a b
一致の高いずらし量（秒）と、そのずらしで1秒ごとにどれだけ一致したか（0〜9）を出す。"""
import sys, os, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # kalanchoe-shorts/
VOC, ANA = os.path.join(ROOT, 'work', 'voc'), os.path.join(ROOT, 'work', 'ana')   # 分離したボーカルと解析結果の置き場
sid, a0, a1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
midi = np.load(f'{ANA}/{sid}/midi.npy'); hop = 0.01
def seg(a, b): return midi[int(a / hop):int(b / hop)]
A = seg(a0, a1); res = []
for off in np.arange(-a0 + 1, len(midi) * hop - a1, 0.05):
    if abs(off) < 4: continue
    B = seg(a0 + off, a1 + off); n = min(len(A), len(B)); a, b = A[:n], B[:n]; ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 200: continue
    res.append(((np.abs(a[ok] - b[ok]) < 1.0).mean() * min(1, ok.sum() / (0.5 * n)), off))
res.sort(reverse=True); seen = []
for s, off in res:
    if all(abs(off - o) > 3 for o in seen): seen.append(off); print(f'offset {off:+7.2f}s  score {s:.2f}  -> {a0 + off:.1f}〜{a1 + off:.1f}s')
    if len(seen) >= 5: break
for off in seen[:3]:
    B = seg(a0 + off, a1 + off); row = ''
    for k in range(int(a1 - a0)):
        a, b = A[k * 100:(k + 1) * 100], B[k * 100:(k + 1) * 100]; ok = ~np.isnan(a) & ~np.isnan(b)
        row += ' .' if ok.sum() < 20 else f'{int(9 * (np.abs(a[ok] - b[ok]) < 1.0).mean()):2d}'
    print(f'off {off:+7.2f}: t={a0:.0f}.. per 1s ->', row)
