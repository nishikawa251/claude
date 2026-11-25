"""UVR MDX-Net（ONNX）でボーカルを分離する。usage: sep.py model.onnx in.wav start_s dur_s out.wav"""
import sys, numpy as np, soundfile as sf, librosa, onnxruntime as ort
model, src, st, du, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
N_FFT, HOP, DIM_F, DIM_T = 7680, 1024, 3072, 256
CHUNK = HOP * (DIM_T - 1); TRIM = N_FFT // 2; GEN = CHUNK - 2 * TRIM
y, sr = sf.read(src, start=int(st * 44100), frames=int(du * 44100), dtype='float32'); mix = y.T
n = mix.shape[1]; pad = GEN - (n % GEN)
mp = np.concatenate([np.zeros((2, TRIM), np.float32), mix, np.zeros((2, pad), np.float32), np.zeros((2, TRIM), np.float32)], 1)
sess = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
outs = []
for i in range(0, n + pad, GEN):
    w = mp[:, i:i + CHUNK]
    S = np.stack([librosa.stft(w[c], n_fft=N_FFT, hop_length=HOP, window='hann', center=True, pad_mode='reflect') for c in range(2)])
    x = np.stack([S[0].real, S[0].imag, S[1].real, S[1].imag])[:, :DIM_F][None].astype(np.float32)
    yv = sess.run(None, {'input': x})[0][0]
    full = np.zeros((4, N_FFT // 2 + 1, DIM_T), np.float32); full[:, :DIM_F] = yv
    wav = np.stack([librosa.istft(full[2*c] + 1j * full[2*c+1], n_fft=N_FFT, hop_length=HOP, window='hann', center=True, length=CHUNK) for c in range(2)])
    outs.append(wav[:, TRIM:-TRIM])
voc = np.concatenate(outs, 1)[:, :n]
sf.write(out, voc.T, sr)
print('wrote', out, voc.shape, 'vocal rms dB', 20*np.log10(np.sqrt((voc**2).mean())+1e-9), 'mix rms dB', 20*np.log10(np.sqrt((mix**2).mean())+1e-9))
