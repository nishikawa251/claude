"""サビ頭（head）と、サビの歌が終わる時刻（vend）から、切り出しと冒頭のタイミングを決めて設定に書く。
usage: setcfg.py <曲ID> head vend [pickup_before]
- 開始：サビ頭の3秒前に最も近い息つぎ（ボーカル -28dB 未満が 0.04秒以上、2.2〜4.2秒前の範囲）
- 終わり：歌の終わりの 1.3秒後。それより前に次の歌が始まるなら、その直前
- ロゴのピントは冒頭の55%で合い、サビ頭の0.42秒前に上へ動き、ジャケットはサビ頭から上がって2拍（最大1.1秒）で着地
"""
import sys, os, json, numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # kalanchoe-shorts/
VOC, ANA = os.path.join(ROOT, 'work', 'voc'), os.path.join(ROOT, 'work', 'ana')   # 分離したボーカルと解析結果の置き場
sid, head, vend = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
pick_before = float(sys.argv[4]) if len(sys.argv) > 4 else 0.42
v, sr = sf.read(f'{VOC}/voc_{sid}.wav'); m = v.mean(1)
bt = np.load(f'{ANA}/{sid}/beats.npy'); beat = float(np.median(np.diff(bt)))
def level(a, b):
    s = m[int(a * sr):int(b * sr)]; return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9)
step = 0.02
xs = np.arange(head - 4.2, head - 2.2, step); d = np.array([level(x, x + step) for x in xs])
gaps, g = [], None
for x, v_ in zip(xs, d):
    if v_ < -28 and g is None: g = x
    if v_ >= -28 and g is not None:
        if x - g >= 0.04: gaps.append((g, x))
        g = None
if gaps:
    g0, g1 = min(gaps, key=lambda p: abs((p[0] + p[1]) / 2 - (head - 3.0)))
    start = round((g0 + g1) / 2, 2)
else:
    start = round(head - 3.0, 2)
# 終わり：歌の終わりから 1.3秒。途中で次の歌が始まれば手前で止める
end = vend + 1.3
xs = np.arange(vend + 0.3, vend + 1.3, step); d = np.array([level(x, x + step) for x in xs])
on = np.where(d > -24)[0]
if len(on) and (np.diff(np.r_[on, -9]) == 1).sum() >= 4:
    end = min(end, xs[on[0]] - 0.05)
end = round(end, 2)
lead = round(head - start, 2)
two = 2 * beat if 2 * beat >= 0.8 else 4 * beat
cfg_p = f'{ROOT}/songs/{sid}.json'; c = json.load(open(cfg_p, encoding='utf-8'))
c.update(start=start, duration=round(end - start, 2), lead=lead, land=round(lead + min(1.1, two), 2),
         pickup=round(lead - pick_before, 2), focus=round(max(1.2, 0.55 * lead), 2),
         fade_out=round(min(1.2, max(0.6, end - vend)), 2))
json.dump(c, open(cfg_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'{sid}: head {head:.2f} vend {vend:.2f} beat {beat:.3f} | start {start} (breaths {[(round(a, 2), round(b, 2)) for a, b in gaps]}) end {end} '
      f'dur {end - start:.2f} lead {lead} pickup {c["pickup"]} focus {c["focus"]} land {c["land"]} fade_out {c["fade_out"]}')
