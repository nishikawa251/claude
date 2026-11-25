"""MV の縦切り抜きの位置を自動で決める（歌詞の文字を追う）。usage: mv_track.py mv/potd.json
文字の検出には rapidocr_onnxruntime の検出モデル（PP-OCRv3 det、縦書きの日本語も拾える）を使う（pip install rapidocr_onnxruntime）。
結果は mv/<name>.track.json（コマごとの切り抜きの左端 x、元の映像の px）と、確認用の図 work/mvtrack/<name>_*.png。

決め方
  1. MV を幅 960 に縮め、3コマごとに文字の枠を検出する（左右の端 6% の飾りの文字は除く）。
  2. 列ごとの重み = 文字の面積。新しく現れた文字（0.5秒前のどの枠とも重ならない）は 1.5秒のあいだ3倍に重くする。
     文字を見落とすコマがあるので、検出した枠は 0.6秒覚えておく。
  3. 画面の中央にも弱い重みを置く（文字がない場面は中央に寄る）。
  4. 幅 608px（縦いっぱいにしたときに映る幅）の窓で重みの合計が最大の位置を目標にする。
  5. 場面の切り替わり（色の分布が大きく変わる所）では一気に移ってよい。同じ場面の中は、目標の窓が今の窓より
     30% 以上よいときだけ動き、ゆっくり加速して追う（元の映像で最大 1100px/秒）。動いたあと 0.4秒は止まる。
"""
import json, os, subprocess, sys
import numpy as np, cv2
from rapidocr_onnxruntime import RapidOCR

m = json.load(open(sys.argv[1], encoding='utf-8'))
c = json.load(open(m['song'], encoding='utf-8'))
name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
end = c['start'] + c['duration']; st = m.get('start', c['start']); dur = end - st
probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                        '-of', 'csv=p=0', m['mv']], capture_output=True, text=True).stdout.strip().split(',')
SW, SH = int(probe[0]), int(probe[1]); num, den = map(int, probe[2].split('/')); fps = num / den
CW = round(SH * 1080 / 1920 / 2) * 2
A = 960; k = SW / A; AH = round(SH / k); cwa = CW / k
eng = RapidOCR()
proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{st - m["offset"]:.3f}', '-t', f'{dur:.3f}', '-i', m['mv'],
                         '-vf', f'scale={A}:{AH}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
fsz = A * AH * 3; border = 0.06 * A
boxes, hists, thumbs = [], [], {}
i = 0; STEP = 3
while True:
    buf = proc.stdout.read(fsz)
    if len(buf) < fsz: break
    f = np.frombuffer(buf, np.uint8).reshape(AH, A, 3)
    h = cv2.calcHist([f[::4, ::4]], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3).ravel(); hists.append(h / h.sum())
    if i % STEP == 0:
        res, _ = eng(cv2.cvtColor(f, cv2.COLOR_RGB2BGR), use_det=True, use_cls=False, use_rec=False)
        bb = []
        for r in (res or []):
            p = np.array(r[0], np.float32).reshape(-1, 2); x0, x1, y0, y1 = p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()
            if x1 < border or x0 > A - border: continue          # 端の飾りの文字
            if (x1 - x0) * (y1 - y0) < 60: continue
            bb.append((float(x0), float(x1), float(y0), float(y1)))
        boxes.append(bb)
    else:
        boxes.append(None)
    if i % round(0.5 * fps) == 0: thumbs[i] = cv2.resize(f, (240, round(240 * AH / A)))
    i += 1
n = i
print(name, 'frames', n, 'fps', round(fps, 3), 'crop', CW)
cut = [False] + [0.5 * np.abs(hists[j] - hists[j - 1]).sum() > 0.45 for j in range(1, n)]


def iou1d(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[2], b[2]))


# 検出のあるコマの枠に「現れた時刻」を付ける（0.5秒前のどの枠とも重ならなければ新しい）
lag = round(0.5 * fps); born = {}
det_idx = [j for j in range(n) if boxes[j] is not None]
tracked = []   # (j, [(box, born_j)])
for j in det_idx:
    prev = [tb for (jj, tbs) in tracked if j - lag <= jj < j for tb in tbs]
    cur = []
    for b in boxes[j]:
        old = [bj for (pb, bj) in prev if iou1d(pb, b) > 0.3 * (b[1] - b[0]) * (b[3] - b[2])]
        cur.append((b, min(old) if old else j))
    tracked.append((j, cur))
xs = np.arange(A) + 0.5
center = np.exp(-0.5 * ((xs - A / 2) / (0.18 * A)) ** 2) * 0.35
mem = round(0.6 * fps); newdur = 1.5 * fps
score = np.zeros((n, A)); shot_start = 0
ti = 0
for j in range(n):
    if cut[j]: shot_start = j
    prof = np.zeros(A)
    for (jj, tbs) in tracked:
        if jj > j or jj < j - mem or jj < shot_start: continue
        for (b, bj) in tbs:
            wgt = 3.0 if (j - bj) < newdur else 1.0
            area = (b[3] - b[2])
            prof[int(b[0]):int(np.ceil(b[1]))] += wgt * area
    if prof.max() > 0: prof = prof / prof.max()
    score[j] = prof + center
w = int(round(cwa)); csum = np.cumsum(np.pad(score, ((0, 0), (1, 0))), axis=1)
win = csum[:, w:] - csum[:, :-w]; best = win.argmax(1) + w / 2
shots = [0] + [j for j in range(1, n) if cut[j]] + [n]
cx = np.zeros(n); lo, hi = w / 2, A - w / 2
vmax = 1100 / k / fps; acc = vmax / (0.25 * fps)
for a, b in zip(shots[:-1], shots[1:]):
    pos = float(np.clip(np.median(best[a:min(b, a + max(1, round(0.3 * fps)))]), lo, hi)); vel = 0.0; goal = pos; hold = 0
    for j in range(a, b):
        cur = int(np.clip(round(pos - w / 2), 0, win.shape[1] - 1))
        if hold <= 0 and win[j].max() > 1.3 * win[j, cur]:
            goal = float(np.clip(best[j], lo, hi))
        d = goal - pos
        # 止まれる距離を見ながら加速・減速する（台形の速さ）
        stop = vel * vel / (2 * acc) if acc > 0 else 0
        if abs(d) < 0.5 and abs(vel) < acc: pos, vel = goal, 0.0
        else:
            want = np.sign(d) * (vmax if abs(d) > stop else 0)
            vel = vel + np.clip(want - vel, -acc, acc); pos = pos + vel
            if abs(goal - pos) < 0.5 and abs(vel) <= acc: hold = round(0.4 * fps)
        hold -= 1
        cx[j] = np.clip(pos, lo, hi)
x_left = np.clip(cx * k - CW / 2, 0, SW - CW)
json.dump({'fps': fps, 'crop_w': CW, 'x': [round(float(v), 2) for v in x_left], 'cuts': [j for j in range(n) if cut[j]]},
          open(f'mv/{name}.track.json', 'w'))
os.makedirs('work/mvtrack', exist_ok=True)
idx = sorted(thumbs); cols = 8; tw = 240; thh = thumbs[idx[0]].shape[0]
sheet = np.full((((len(idx) + cols - 1) // cols) * (thh + 4), cols * (tw + 4), 3), 20, np.uint8)
for q, j in enumerate(idx):
    im = thumbs[j].copy(); s = tw / A
    for (jj, tbs) in tracked:
        if j - STEP < jj <= j:
            for (b, bj) in tbs: cv2.rectangle(im, (int(b[0] * s), int(b[2] * s)), (int(b[1] * s), int(b[3] * s)), (255, 60, 60), 1)
    x0 = int(x_left[j] / SW * tw); x1 = int((x_left[j] + CW) / SW * tw)
    cv2.rectangle(im, (x0, 0), (x1, thh - 1), (255, 220, 0), 2)
    cv2.putText(im, f'{st + j / fps:.1f}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    yy, xx = (q // cols) * (thh + 4), (q % cols) * (tw + 4); sheet[yy:yy + thh, xx:xx + tw] = im
cv2.imwrite(f'work/mvtrack/{name}_sheet.png', cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
print('cuts', sum(cut), 'saved')
