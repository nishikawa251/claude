"""MV の縦切り抜きの位置と引き具合を自動で決める。usage: mv_track.py mv/potd.json
結果は mv/<name>.track.json（コマごとの映す範囲の中心 cx と幅 vw、元の映像の px）と、確認用の図 work/mvtrack/<name>_sheet.png。
make_mv_short.py が "crop": "track" のときにこのファイルで書き出す。

見るもの
  顔　：アニメ絵の肌（と白っぽい髪）の色のかたまり。場面の半分以上のコマで、いちばん大きいかたまりが2番目の1.8倍以上
        （キャラクターが1人はっきり映る）なら「顔の場面」とし、かたまりの上半分（頭）を最優先で追う。
        アニメ顔の検出器（lbpcascade_animeface など）はこの MV の斜めの大きな顔を拾えず、新しい検出モデルは
        置き場所（Hugging Face）にこの環境から届かないので、色で代用している。
  歌詞：rapidocr_onnxruntime の文字検出（3コマごと）。新しく出た文字を重く、0.6秒覚えておく。左右の端 6% の飾りの文字は除く。
  中央：弱い重み。何もない場面は中央に寄る。
引き　：0.3秒先まで見て、1つの文字のかたまりが、縦いっぱいの枠（元の映像の幅 608px）より広いときだけ、その文字が収まるまで引く（文字の幅の1.25倍＋130px、最大 1320px）。
        引いているあいだ、上下は同じ映像をぼかして埋める。文字が消えるか場面が変わったら戻る。
動き　：場面（カット）ごとに位置と引き具合を1つに決め、場面の中では動かさない。毎コマ追うとブレて見える（川西さん
        「ずっとブレブレになっちゃうのがダメダメ」）。位置が変わるのは MV のカットの瞬間だけ。0.6秒より短い場面は前にまとめる。
        広い文字が出る場面は、場面のはじめから引いておく。
"""
import json, os, subprocess, sys
import numpy as np, cv2
from rapidocr_onnxruntime import RapidOCR

m = json.load(open(sys.argv[1], encoding='utf-8'))
c = json.load(open(m['song'], encoding='utf-8'))
name = os.path.splitext(os.path.basename(m.get('track', sys.argv[1])))[0].replace('.track', '')
use_face, use_zoom = m.get('track_face', True), m.get('track_zoom', True)
end = c['start'] + c['duration']; st = m.get('start', c['start']); dur = end - st
probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                        '-of', 'csv=p=0', m['mv']], capture_output=True, text=True).stdout.strip().split(',')
SW, SH = int(probe[0]), int(probe[1]); num, den = map(int, probe[2].split('/')); fps = num / den
CW = round(SH * 1080 / 1920 / 2) * 2; VMAX = 1320
A = 960; k = SW / A; AH = round(SH / k)
eng = RapidOCR()
proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{st - m["offset"]:.3f}', '-t', f'{dur:.3f}', '-i', m['mv'],
                         '-vf', f'scale={A}:{AH}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
fsz = A * AH * 3; border = 0.06 * A


def skin_blobs(f):
    hsv = cv2.cvtColor(f[::2, ::2], cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
    h, s, v = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    mk = (((h <= 28) | (h >= 345)) & (s >= 0.07) & (s <= 0.40) & (v >= 0.72)).astype(np.uint8)
    mk = cv2.morphologyEx(mk, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, stt, _ = cv2.connectedComponentsWithStats(mk)
    bl = sorted([(int(stt[i, 4]), i) for i in range(1, n)], reverse=True)[:2]
    out = []
    for a, i in bl:
        ys, xs = np.nonzero(lab == i); top = ys <= np.percentile(ys, 50)     # かたまりの上半分＝頭
        out.append((a * 4, float(xs[top].mean() * 2), float(xs.min() * 2), float(xs.max() * 2)))
    return out


boxes, hists, skins, thumbs = [], [], [], {}
i = 0
while True:
    buf = proc.stdout.read(fsz)
    if len(buf) < fsz: break
    f = np.frombuffer(buf, np.uint8).reshape(AH, A, 3)
    h = cv2.calcHist([f[::4, ::4]], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3).ravel(); hists.append(h / h.sum())
    if i % 3 == 0:
        res, _ = eng(cv2.cvtColor(f, cv2.COLOR_RGB2BGR), use_det=True, use_cls=False, use_rec=False)
        bb = []
        for r in (res or []):
            p = np.array(r[0], np.float32).reshape(-1, 2); x0, x1, y0, y1 = p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()
            if x1 < border or x0 > A - border or (x1 - x0) * (y1 - y0) < 60: continue
            bb.append((float(x0), float(x1), float(y0), float(y1)))
        boxes.append(bb)
    else:
        boxes.append(None)
    skins.append(skin_blobs(f) if i % 2 == 0 else None)
    if i % round(0.5 * fps) == 0: thumbs[i] = cv2.resize(f, (240, round(240 * AH / A)))
    i += 1
n = i
cut = [False] + [0.5 * np.abs(hists[j] - hists[j - 1]).sum() > 0.45 for j in range(1, n)]
shots = [0] + [j for j in range(1, n) if cut[j]] + [n]
print(name, 'frames', n, 'fps', round(fps, 3), 'shots', len(shots) - 1)


def overlap(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[2], b[2]))


lag = round(0.5 * fps); tracked = []
for j in range(n):
    if boxes[j] is None: continue
    prev = [tb for (jj, tbs) in tracked if j - lag <= jj < j for tb in tbs]
    cur = []
    for b in boxes[j]:
        old = [bj for (pb, bj) in prev if overlap(pb, b) > 0.3 * (b[1] - b[0]) * (b[3] - b[2])]
        cur.append((b, min(old) if old else j))
    tracked.append((j, cur))
xs = np.arange(A) + 0.5
center = np.exp(-0.5 * ((xs - A / 2) / (0.18 * A)) ** 2) * 0.35
mem = round(0.6 * fps); newdur = 1.5 * fps; frame_area = A * AH; look = round(0.3 * fps)
# 場面ごとに「顔の場面」かを決める
face_shot = {}
for a, b in zip(shots[:-1], shots[1:]):
    s = [x for x in skins[a:b] if x is not None]
    ok = [x for x in s if x and x[0][0] > 0.02 * frame_area and (len(x) < 2 or x[0][0] > 1.8 * x[1][0])]
    face_shot[a] = use_face and len(s) > 0 and len(ok) >= 0.5 * len(s)
score = np.zeros((n, A)); wide = [None] * n; shot_start = 0; last_head = None
for j in range(n):
    if cut[j]: shot_start = j; last_head = None
    prof = np.zeros(A); wide_best = None
    sh_end = min(x for x in shots if x > j)
    for (jj, tbs) in tracked:
        if jj < shot_start: continue
        for (b, bj) in tbs:
            if j - mem <= jj <= j:
                wgt = 3.0 if (j - bj) < newdur else 1.0
                prof[int(b[0]):int(np.ceil(b[1]))] += wgt * (b[3] - b[2])
            # 広い文字は 0.3秒先まで見て、出てくる前から引き始める（同じ場面の中だけ）
            if j - mem + look <= jj <= min(j + look, sh_end - 1) and (b[1] - b[0]) * k > 0.92 * CW \
                    and (wide_best is None or jj > wide_best[1]): wide_best = (b, jj)
    if prof.max() > 0: prof = prof / prof.max()
    sc = prof + center
    if face_shot[shot_start]:
        sk = skins[j] if skins[j] is not None else (skins[j - 1] if j > 0 else None)
        if sk and sk[0][0] > 0.02 * frame_area: last_head = sk[0][1]
        if last_head is not None:
            sc = sc + 2.0 * np.exp(-0.5 * ((xs - last_head) / (0.12 * A)) ** 2)
    score[j] = sc
    if use_zoom and wide_best is not None: wide[j] = wide_best[0]
# 場面（カット）ごとに、映す位置と引き具合を1つに決めて、場面の中では動かさない（毎コマ追うとブレて見えるため）。
# 0.6秒より短い場面は前の場面にまとめる（フラッシュなどを切り替わりと見誤らないように）
min_len = round(0.6 * fps); cuts2 = [0]
for x in shots[1:-1]:
    if x - cuts2[-1] >= min_len and n - x >= min_len: cuts2.append(x)
cuts2.append(n)
cx = np.zeros(n); vw = np.full(n, float(CW)); face_of = {}
for a, b in zip(cuts2[:-1], cuts2[1:]):
    S = score[a:b].sum(0)                                   # 場面全体で見るべき所を足し合わせる
    wb = [wide[j] for j in range(a, b) if wide[j] is not None]
    if wb:                                                  # 広い文字が出る場面は、場面のはじめから引いておく
        x0 = min(bx[0] for bx in wb); x1 = max(bx[1] for bx in wb)
        V = float(np.clip((x1 - x0) * k * 1.12 + 120, CW, VMAX)); half = V / k / 2
        cen = float(np.clip((x0 + x1) / 2, half, A - half))
    else:
        V = float(CW); wv = int(round(CW / k)); cs = np.cumsum(np.pad(S, (1, 0)))
        cen = float((cs[wv:] - cs[:-wv]).argmax() + wv / 2)
    cx[a:b] = cen; vw[a:b] = V
    face_of[a] = any(face_shot.get(x, False) for x in shots[:-1] if a <= x < b)
cxs = cx * k
json.dump({'fps': fps, 'crop_w': CW, 'cx': [round(float(v), 2) for v in cxs], 'vw': [round(float(v), 2) for v in vw],
           'cuts': [j for j in range(n) if cut[j]], 'face_shots': [a for a in face_shot if face_shot[a]]},
          open(f'mv/{name}.track.json', 'w'))
os.makedirs('work/mvtrack', exist_ok=True)
idx = sorted(thumbs); cols = 8; tw = 240; thh = thumbs[idx[0]].shape[0]
sheet = np.full((((len(idx) + cols - 1) // cols) * (thh + 4), cols * (tw + 4), 3), 20, np.uint8)
for q, j in enumerate(idx):
    im = thumbs[j].copy(); s = tw / A
    x0 = int((cxs[j] - vw[j] / 2) / SW * tw); x1 = int((cxs[j] + vw[j] / 2) / SW * tw)
    col = (255, 220, 0) if vw[j] <= CW + 1 else (0, 255, 120)
    cv2.rectangle(im, (x0, 0), (x1, thh - 1), col, 2)
    sh_a = max(a for a in cuts2[:-1] if a <= j)
    cv2.putText(im, f'{st + j / fps:.1f}' + (' F' if face_of[sh_a] else ''), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    yy, xx = (q // cols) * (thh + 4), (q % cols) * (tw + 4); sheet[yy:yy + thh, xx:xx + tw] = im
cv2.imwrite(f'work/mvtrack/{name}_sheet.png', cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
print('shots', len(cuts2) - 1, 'face shots', sum(face_of.values()), 'zoom frames', int((vw > CW + 1).sum()), 'saved')
