"""Trilha de ambiente do mangue + batidas de asa sincronizadas com a animação."""
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000
T = 21.7
N = int(SR * T)
rng = np.random.default_rng(7)
t = np.arange(N) / SR


def bp(x, lo, hi, order=4):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, f, order=4):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=4):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def slow_noise(rate, n=N, seed=None):
    """Ruído suave (interpolado) entre 0 e 1, para variar volumes devagar."""
    r = np.random.default_rng(seed)
    k = int(T * rate) + 3
    pts = r.random(k)
    x = np.linspace(0, k - 3, n)
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    return pts[i] * (1 - f) + pts[i + 1] * f


def pan(mono, p):
    """p de -1 (esquerda) a 1 (direita); aceita vetor."""
    a = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


mix = np.zeros((N, 2))

# --- água do mangue batendo devagar ---
for ch, seed in ((0, 1), (1, 2)):
    w = lp(rng.standard_normal(N), 500)
    w = w * (0.35 + 0.65 * slow_noise(0.6, seed=seed) ** 2)
    w += 0.4 * bp(rng.standard_normal(N), 900, 2500) * slow_noise(1.3, seed=seed + 10) ** 4
    mix[:, ch] += 0.16 * w / np.abs(w).max()

# gotinhas / peixinhos na água
for _ in range(14):
    t0 = rng.uniform(0, T - 0.3)
    f0 = rng.uniform(700, 1400)
    d = int(0.09 * SR)
    tt = np.arange(d) / SR
    s = np.sin(2 * np.pi * (f0 * tt + 2500 * tt ** 2 * -1)) * np.exp(-tt * 45)
    i = int(t0 * SR)
    mix[i:i + d] += pan(s * 0.035, rng.uniform(-0.8, 0.8))

# --- vento nas folhas do mangue ---
for ch, seed in ((0, 3), (1, 4)):
    lv = bp(rng.standard_normal(N), 1500, 7000, 2) * (0.25 + 0.75 * slow_noise(0.35, seed=seed) ** 2)
    mix[:, ch] += 0.03 * lv / np.abs(lv).max()

# --- insetos do fim de tarde (cigarra ao longe) ---
ins = bp(rng.standard_normal(N), 4200, 5200)
pulse = (0.5 + 0.5 * np.sin(2 * np.pi * 38 * t)) ** 3
phr = np.clip(np.sin(2 * np.pi * t / 6.5 + 1.0) * 1.4, 0, 1)
ins = ins * pulse * phr
mix += pan(0.022 * ins / np.abs(ins).max(), 0.55)

# --- passarinhos ao longe ---
def chirp(dur, f0, f1, vib=0.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = np.linspace(f0, f1, n) * (1 + vib * np.sin(2 * np.pi * 28 * tt))
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.sin(np.pi * np.arange(n) / n) ** 2
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * env


def add_at(sig, t0, gain, p):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    mix[i:i + len(sig)] += pan(sig * gain, p)


songs = []
tcur = 0.4
while tcur < T - 1:
    kind = rng.integers(0, 3)
    p = rng.uniform(-0.9, 0.9)
    g = rng.uniform(0.02, 0.045)
    if kind == 0:  # tsi-tsi-tsi descendo
        for k in range(rng.integers(3, 6)):
            add_at(chirp(0.07, 4200 - k * 150, 3000 - k * 150), tcur + k * 0.11, g, p)
    elif kind == 1:  # assobio sobe e desce
        add_at(chirp(0.22, 2100, 2900, 0.02), tcur, g, p)
        add_at(chirp(0.3, 2900, 1900, 0.02), tcur + 0.25, g, p)
    else:  # trinado
        add_at(chirp(0.45, 3600, 3400, 0.12), tcur, g * 0.8, p)
    tcur += rng.uniform(1.2, 2.6)

# som ambiente mais baixo enquanto os guarás falam
FALAS = [(5.7, 19.7)]
duck = np.ones(N)
for a, b in FALAS:
    duck -= 0.45 * np.clip(np.minimum((t - (a - 0.4)) / 0.4, ((b + 0.4) - t) / 0.4), 0, 1)
mix *= duck[:, None]

# --- batidas de# --- batidas de asa do guará (mesmo ritmo da animação) ---
def whoosh(strength, dur=0.32):
    d = int(dur * SR); tt = np.arange(d) / SR
    env = (1 - np.exp(-tt / 0.025)) * np.exp(-tt / 0.09)
    body = bp(rng.standard_normal(d), 180, 1400, 2) * env
    air = bp(rng.standard_normal(d), 1500, 5000, 2) * env * 0.35
    thump = np.sin(2 * np.pi * 85 * tt) * np.exp(-tt / 0.04) * 0.6
    x = body + air + thump
    return x / np.abs(x).max() * strength
beats = []
w = 2 * np.pi * 3.1
for k in range(40):   # batidas fortes até 2,0 s: descida quando sin(w t) cruza para baixo
    tt = (np.pi / 2 + 2 * np.pi * k) / w
    if tt < 2.0: beats.append((tt, 0.18 + 0.2 * min(1, tt / 1.5)))
for k in range(10):   # freada antes do pouso
    tt = 2.8 + (np.pi / 2 + 2 * np.pi * k) / (2 * np.pi * 2.2)
    if tt < 4.4: beats.append((tt, 0.42))
for k in range(6):    # gesto ao começar a falar
    tt = 5.6 + (np.pi / 2 + 2 * np.pi * k) / (2 * np.pi * 2.5)
    if tt < 6.8: beats.append((tt, 0.18))
for tt, g in beats:
    add_at(whoosh(g * rng.uniform(0.85, 1.1)), tt - 0.03, 1.0, rng.uniform(-0.2, 0.2))
# pouso na água: respingo
d = int(0.6 * SR); tt = np.arange(d) / SR
spl = bp(rng.standard_normal(d), 600, 6000, 2) * np.exp(-tt / 0.12) + 0.5 * lp(rng.standard_normal(d), 400) * np.exp(-tt / 0.08)
add_at(spl / np.abs(spl).max() * 0.35, 4.05, 1.0, 0.0)
for k in range(4):
    d2 = int(0.15 * SR); t2 = np.arange(d2) / SR
    add_at(np.sin(2 * np.pi * (900 + 300 * k) * t2 * (1 - t2 * 3)) * np.exp(-t2 * 30) * 0.05, 4.2 + k * 0.13, 1.0, 0.1)

mix = hp(mix.T, 40).T
mix *= 0.89 / np.abs(mix).max()
wavfile.write("real/trilha_noticia.wav", SR, (mix * 32767).astype(np.int16))
print("ok", mix.shape)
