"""Trilha do vídeo 'litoral até Imperatriz': mangue -> vento no alto -> trânsito da BR-010, com batidas de asa."""
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 48000; T = 29.4; N = int(SR * T); t = np.arange(N) / SR
rng = np.random.default_rng(5)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], btype='band', fs=SR, output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, btype='low', fs=SR, output='sos'), x)
def env(a, b, fade=0.5):
    return np.clip(np.minimum((t - a) / fade + 1, (b - t) / fade + 1), 0, 1)
def pan(m, p):
    a = (p + 1) * np.pi / 4; return np.stack([m * np.cos(a), m * np.sin(a)], 1)
def slow(rate, seed):
    r = np.random.default_rng(seed); k = int(T * rate) + 3; pts = r.random(k)
    x = np.linspace(0, k - 3, N); i = x.astype(int); f = x - i; f = f * f * (3 - 2 * f)
    return pts[i] * (1 - f) + pts[i + 1] * f
mix = np.zeros((N, 2))
def add(sig, t0, g=1.0, p=0.0):
    i = int(t0 * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i]; mix[i:i + len(sig)] += pan(sig * g, p)
# --- mangue (0 a 3,5 s)
E1 = env(0, 3.3, 0.4)
for ch, sd in ((0, 1), (1, 2)):
    w = lp(rng.standard_normal(N), 500) * (0.4 + 0.6 * slow(0.7, sd) ** 2)
    mix[:, ch] += 0.14 * w / np.abs(w).max() * E1
def chirp(d, f0, f1):
    n = int(d * SR); tt = np.arange(n) / SR; f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.arange(n) / n) ** 2
for k in range(4): add(chirp(0.07, 4200 - k * 150, 3000 - k * 150), 0.5 + k * 0.11, 0.035, -0.6)
add(chirp(0.25, 2100, 2900), 1.9, 0.03, 0.6); add(chirp(0.3, 2900, 1900), 2.17, 0.03, 0.6)
# --- vento no alto (3 a 6 s)
E2 = env(3.0, 6.0, 0.5)
for ch, sd in ((0, 3), (1, 4)):
    w = bp(rng.standard_normal(N), 150, 1800) * (0.5 + 0.5 * slow(1.5, sd))
    mix[:, ch] += 0.12 * w / np.abs(w).max() * E2
# --- cidade / BR-010 (5,5 s em diante)
E3 = env(5.5, T + 1, 0.6)
hum = lp(rng.standard_normal(N), 180, 3); hum = hum / np.abs(hum).max()
for ch in (0, 1): mix[:, ch] += 0.10 * hum * E3
for k in range(40):                       # carros passando lá embaixo
    t0 = rng.uniform(5.2, T - 1); d = rng.uniform(2.0, 3.5); n = int(d * SR); tt = np.arange(n) / SR
    e = np.exp(-((tt - d / 2) / (d / 5)) ** 2)
    f0 = rng.uniform(300, 700); s = bp(rng.standard_normal(n), f0 * 0.5, f0 * 2.5) * e
    s += 0.5 * lp(rng.standard_normal(n), 120) * e * (2 if rng.random() < 0.25 else 1)
    p = np.linspace(-0.8, 0.8, n) * rng.choice((-1, 1))
    i = int(t0 * SR); m = min(n, N - i)
    if m > 0: mix[i:i + m] += pan(s[:m] / (np.abs(s).max() + 1e-9) * rng.uniform(0.04, 0.09), p[:m]) * E3[i:i + m, None]
for t0, f in ((12.5, 410), (19.8, 380), (25.6, 395)):  # buzina ao longe
    n = int(0.35 * SR); tt = np.arange(n) / SR
    s = (np.sign(np.sin(2 * np.pi * f * tt)) + np.sign(np.sin(2 * np.pi * f * 1.26 * tt))) * np.minimum(1, tt / 0.02) * np.minimum(1, (0.35 - tt) / 0.05)
    add(lp(s, 1800) * 0.012, t0, 1, 0.5)
# abaixa o ambiente durante a fala
SP0, SP1 = 8.9, 28.4
duck = 1 - 0.45 * np.clip(np.minimum((t - (SP0 - 0.4)) / 0.4, ((SP1 + 0.4) - t) / 0.4), 0, 1)
mix *= duck[:, None]
# --- batidas de asa
def whoosh(g):
    d = int(0.3 * SR); tt = np.arange(d) / SR; e = (1 - np.exp(-tt / 0.025)) * np.exp(-tt / 0.09)
    s = bp(rng.standard_normal(d), 180, 1400) * e + 0.35 * bp(rng.standard_normal(d), 1500, 5000) * e + 0.6 * np.sin(2 * np.pi * 85 * tt) * np.exp(-tt / 0.04)
    return s / np.abs(s).max() * g
def beats(t0, t1, freq, g, off=0.0, cond=None):
    k = 0
    while True:
        tb = off + (np.pi / 2 + 2 * np.pi * k) / (2 * np.pi * freq)   # pico da descida
        k += 1
        if tb > t1: break
        if tb >= t0 and (cond is None or cond(tb)): add(whoosh(g), tb, 1, 0)
beats(0.0, 3.4, 3.0, 0.16)
beats(3.0, 6.0, 2.6, 0.12, off=3.0, cond=lambda tb: ((tb - 3.0) % 2.4) < 1.4)
beats(5.5, 6.7, 2.8, 0.18, off=5.5)
beats(7.1, 8.7, 2.2, 0.22, off=7.1)
beats(8.9, 10.2, 2.5, 0.15, off=8.9)
n = int(0.12 * SR); x = lp(rng.standard_normal(n), 900) * np.exp(-np.arange(n) / SR / 0.02)
add(x / np.abs(x).max() * 0.1, 7.9)
mix *= 0.89 / np.abs(mix).max()
wavfile.write('trilha_invasao.wav', SR, (mix * 32767).astype(np.int16)); print('ok', mix.shape)
