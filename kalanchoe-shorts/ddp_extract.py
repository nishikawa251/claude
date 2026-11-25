#!/usr/bin/env python3
"""CD マスターの DDP（DDP 2.0）を曲ごとの WAV に分ける。
  python3 ddp_extract.py DDPのフォルダ 出力の頭 [--names a.wav,b.wav,...]
DDPMS から音声データ（IMAGE.DAT）の開始位置、PQDESCR から各曲の index 00／01 の時刻を読む。
曲は index 01 から次の曲の index 00（最後の曲はリードアウト）まで。CHECKSUM.MD5 があれば照合する。
"""
import argparse, glob, hashlib, os, re, sys
import numpy as np
import soundfile as sf

SECTOR_BYTES, SECTOR_SAMPLES = 2352, 588


def msf(s):
    """'MMSSFF' をセクタ数（1秒 = 75セクタ）に"""
    return (int(s[0:2]) * 60 + int(s[2:4])) * 75 + int(s[4:6])


def read_pq(path):
    """PQDESCR の 64 バイトずつの記録から {曲: {index: セクタ}} とリードアウトを返す"""
    data = open(path, 'rb').read().decode('latin1')
    marks, leadout = {}, None
    for i in range(0, len(data), 64):
        rec = data[i:i + 64]
        if not rec.startswith('VVVS'):
            continue
        trk, idx, t = rec[4:6], rec[6:8], rec[10:16]
        if trk == 'AA':
            leadout = msf(t)
        elif trk.isdigit() and int(trk) > 0:
            marks.setdefault(int(trk), {})[int(idx)] = msf(t)
    return marks, leadout


def image_start(ddpms):
    """DDPMS の音声データ（D0）の記録から、IMAGE.DAT の先頭が何セクタ目かを読む"""
    text = open(ddpms, 'rb').read().decode('latin1')
    for i in range(0, len(text), 128):
        rec = text[i:i + 128]
        if rec.startswith('VVVMD0'):
            nums = re.findall(r'\d{8}', rec[6:40])
            return int(nums[1]) if len(nums) > 1 else 0
    return 0


def byte_order(raw_bytes):
    """リトルエンディアンとビッグエンディアンで読み、波形がなめらかなほうを選ぶ"""
    best = None
    for dt in ('<i2', '>i2'):
        x = np.frombuffer(raw_bytes, dtype=dt).astype(np.float32)[0::2]
        rough = np.abs(np.diff(x)).mean() / (np.abs(x).mean() + 1e-9)
        if best is None or rough < best[0]:
            best = (rough, dt)
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ddp_dir'); ap.add_argument('out_prefix')
    ap.add_argument('--names', help='曲ごとの出力ファイル名（カンマ区切り）。省略すると 出力の頭_trNN.wav')
    a = ap.parse_args()
    d = a.ddp_dir
    img = glob.glob(os.path.join(d, 'IMAGE.DAT'))[0]
    md5file = os.path.join(d, 'CHECKSUM.MD5')
    if os.path.exists(md5file):
        want = {l.split()[1].lstrip('*'): l.split()[0] for l in open(md5file) if l.strip()}
        if 'IMAGE.DAT' in want:
            h = hashlib.md5(open(img, 'rb').read()).hexdigest()
            print('IMAGE.DAT md5', 'OK' if h == want['IMAGE.DAT'] else f'MISMATCH {h}')
    marks, leadout = read_pq(os.path.join(d, 'PQDESCR'))
    start = image_start(os.path.join(d, 'DDPMS'))
    raw = open(img, 'rb').read()
    dt = byte_order(raw[SECTOR_BYTES * 75 * 60: SECTOR_BYTES * 75 * 70])
    pcm = np.frombuffer(raw, dtype=dt).reshape(-1, 2)
    if leadout is None:
        leadout = start + len(pcm) // SECTOR_SAMPLES
    names = a.names.split(',') if a.names else None
    tracks = sorted(marks)
    print(f'byte order {dt}, image starts at sector {start}, {len(tracks)} tracks, lead-out {leadout}')
    for k, t in enumerate(tracks):
        s = marks[t].get(1, marks[t].get(0))
        nxt = tracks[k + 1] if k + 1 < len(tracks) else None
        e = (marks[nxt].get(0, marks[nxt].get(1)) if nxt else leadout)
        x = pcm[(s - start) * SECTOR_SAMPLES:(e - start) * SECTOR_SAMPLES]
        out = names[k] if names else f'{a.out_prefix}_tr{t:02d}.wav'
        if names:
            out = os.path.join(os.path.dirname(a.out_prefix) or '.', out)
        sf.write(out, x, 44100, subtype='PCM_16')
        print(f'TR{t:02d} {out}  start {s / 75:8.2f}s  length {len(x) / 44100:7.2f}s  peak {int(np.abs(x).max())}')


if __name__ == '__main__':
    main()
