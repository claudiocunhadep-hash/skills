"""Trilha de ambiente do mangue + batidas de asa sincronizadas com a animação."""
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000
T = 21.5
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
FALAS = [(7.75, 13.2), (14.35, 18.6)]
duck = np.ones(N)
for a, b in FALAS:
    duck -= 0.45 * np.clip(np.minimum((t - (a - 0.4)) / 0.4, ((b + 0.4) - t) / 0.4), 0, 1)
mix *= duck[:, None]

# --- batidas de asa (mesma conta da animação) ---
T_STAND = 7.2
END_FLAP = 19.2


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def open_amount(tt, fala_inicio):
    o = 1 - smooth((tt - (T_STAND - 0.45)) / 0.45)
    a = fala_inicio
    g = smooth((tt - (a - 0.2)) / 0.25) * smooth((a + 1.1 - tt) / 0.3)
    g = np.where((tt > a - 0.2) & (tt < a + 1.1), g, 0)
    e = np.where(tt > END_FLAP, smooth((tt - END_FLAP) / 0.3), 0)
    return np.maximum(np.maximum(o, g), e)


def whoosh(strength):
    d = int(0.32 * SR)
    tt = np.arange(d) / SR
    env = (1 - np.exp(-tt / 0.025)) * np.exp(-tt / 0.09)
    n = rng.standard_normal(d)
    body = bp(n, 180, 1400, 2) * env
    air = bp(rng.standard_normal(d), 1500, 5000, 2) * env * 0.35
    thump = np.sin(2 * np.pi * 85 * tt) * np.exp(-tt / 0.04) * 0.6
    s = body + air + thump
    return s / np.abs(s).max() * strength


for key, off, fala, p_fly, p_stand in (("m", 0.0, 7.75, 0.4, -0.35), ("f", 0.4, 14.35, -0.4, 0.35)):
    # instantes da batida para baixo: fase (t+off)*13 = π (mod 2π)
    k = np.arange(0, 200)
    tb = (np.pi + 2 * np.pi * k) / 13 - off
    tb = tb[(tb > 0) & (tb < T)]
    for tt in tb:
        o = float(open_amount(np.array([tt]), fala)[0])
        if o < 0.25:
            continue
        voando = tt < T_STAND
        # durante a chegada o som cresce (eles vêm de fora da tela)
        perto = smooth(tt / 1.2) if voando else 1.0
        forca = (0.25 if voando else 0.22) * o * (0.6 + 0.4 * perto) * rng.uniform(0.85, 1.1)
        pp = p_fly * (1 - tt / T_STAND) if voando else p_stand
        add_at(whoosh(forca), tt - 0.03, 1.0, pp)

# pousos na areia
for tt, pp in ((7.12, -0.35), (7.2, 0.35)):
    d = int(0.12 * SR)
    x = lp(rng.standard_normal(d), 900) * np.exp(-np.arange(d) / SR / 0.025)
    add_at(x / np.abs(x).max() * 0.12, tt, 1.0, pp)

# brilho suave quando o coração se completa
for f, g in ((1568, 0.03), (2093, 0.022), (2637, 0.016), (3136, 0.01)):
    d = int(2.2 * SR)
    tt = np.arange(d) / SR
    add_at(np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.6) * g, 5.55, 1.0, 0.0)

mix = hp(mix.T, 40).T
mix *= 0.89 / np.abs(mix).max()
wavfile.write("trilha.wav", SR, (mix * 32767).astype(np.int16))
print("ok", mix.shape)
