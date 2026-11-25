"""Protótipo: dois guarás (macho e fêmea) narrando, com bico sincronizado ao áudio.

Uso (a partir de videos/prototipo-guaras): python3 video-project/guara.py saida.mp4 [frame_teste_s]
"""
import math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, GAP, START = 1080, 1920, 30, 0.45, 0.4
FD = "/usr/share/fonts/opentype/inter/"
F = lambda n, px: ImageFont.truetype(FD + n, px)
RED, RED_D, RED_L, BEAK, NAVY, YEL = (232, 48, 52), (196, 28, 40), (250, 96, 88), (70, 40, 42), (8, 26, 66), (255, 204, 0)

_rows = [l.split("\t") for l in open("lines.tsv").read().strip().split("\n")]
lines = [(r[0], r[1]) for r in _rows]; places = [r[2] for r in _rows]
files = [f"assets/l{i}_{w}.mp3" for i, (w, _) in enumerate(lines)]
probe = lambda f: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
durs = [probe(f) for f in files]
starts, t = [], START
for d in durs: starts.append(t); t += d + GAP
DUR = t + 0.6
NF = int(DUR * FPS)

# ---- áudio mixado + envelope por personagem (para o bico)
SR = 16000
env = {"M": np.zeros(NF), "F": np.zeros(NF)}
inputs, filt = [], []
for i, ((who, _), f, s) in enumerate(zip(lines, files, starts)):
    inputs += ["-i", f]; ms = int(s * 1000); filt.append(f"[{i}]adelay={ms}|{ms}[a{i}]")
    raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", f, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = SR // FPS
    for k in range(len(x) // hop):
        n = int(s * FPS) + k
        if n < NF: env[who][n] = max(env[who][n], float(np.sqrt(np.mean(x[k*hop:(k+1)*hop] ** 2))))
filt.append("".join(f"[a{i}]" for i in range(len(files))) + f"amix=inputs={len(files)}:normalize=0,apad,atrim=0:{DUR:.3f}[out]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[out]", "podcast_audio.wav"], check=True)
for k in env:  # suaviza e normaliza para 0..1
    e = np.convolve(env[k], [0.25, 0.5, 0.25], "same"); env[k] = np.clip(e / 0.10, 0, 1)
with open("podcast_audio.srt", "w") as fh:
    ts = lambda x: f"{int(x//3600):02}:{int(x%3600//60):02}:{x%60:06.3f}".replace(".", ",")
    for i, ((w, txt), s, d) in enumerate(zip(lines, starts, durs)): fh.write(f"{i+1}\n{ts(s)} --> {ts(s+d)}\n{txt}\n\n")

# ---- desenho do guará (olhando para a direita), supersample 2x
SS, CW, CH = 2, 720, 960
def bez(p0, p1, p2, n=40):
    return [((1-t)**2*p0[0] + 2*(1-t)*t*p1[0] + t*t*p2[0], (1-t)**2*p0[1] + 2*(1-t)*t*p1[1] + t*t*p2[1]) for t in np.linspace(0, 1, n)]
def rot(pts, c, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x-c[0])*ca - (y-c[1])*sa, c[1] + (x-c[0])*sa + (y-c[1])*ca) for x, y in pts]

def guara(open_amt, female, blink=False):
    im = Image.new("RGBA", (CW*SS, CH*SS)); d = ImageDraw.Draw(im)
    S = lambda pts: [(x*SS, y*SS) for x, y in pts]
    box = lambda x0, y0, x1, y1: [x0*SS, y0*SS, x1*SS, y1*SS]
    # pernas
    for x0, x1 in ((290, 270), (345, 360)):
        d.line(S([(x0, 600), (x0 - 6, 720), (x1, 860)]), fill=(214, 70, 80), width=11*SS, joint="curve")
        d.line(S([(x1 - 40, 866), (x1 + 44, 866)]), fill=(214, 70, 80), width=9*SS)
    # cauda e corpo
    d.polygon(S([(170, 500), (70, 560), (110, 575), (180, 565)]), fill=RED_D)
    d.ellipse(box(150, 420, 470, 620), fill=RED)
    # asa com pontas pretas (marca do guará)
    d.ellipse(box(175, 455, 420, 595), fill=RED_D)
    d.polygon(S([(190, 505), (95, 548), (120, 566), (205, 575)]), fill=(25, 20, 30))
    d.ellipse(box(330, 440, 450, 520), fill=RED_L)  # peito
    # pescoço (curva grossa em S)
    for (x, y) in bez((420, 480), (330, 330), (440, 250), 60):
        d.ellipse(box(x-30, y-30, x+30, y+30), fill=RED)
    # cabeça
    hx, hy = 455, 225
    d.ellipse(box(hx-62, hy-58, hx+62, hy+58), fill=RED)
    # bico longo e curvo (superior fixo, inferior gira ao falar)
    base = (hx + 45, hy + 8)
    cl = bez(base, (600, 215), (690, 410), 40)
    th = [26 * (1 - i/39) + 3 for i in range(40)]
    up = [(x, y - t) for (x, y), t in zip(cl, th)] + [(x, y) for (x, y) in reversed(cl)]
    lo = [(x, y) for (x, y) in cl] + [(x + t*0.3, y + t) for (x, y), t in reversed(list(zip(cl, th)))]
    lo = rot(lo, base, math.radians(16 * open_amt))
    d.polygon(S(lo), fill=(52, 30, 34))
    if open_amt > 0.05:
        d.polygon(S([base] + rot([cl[6]], base, math.radians(7*open_amt)) + [cl[3]]), fill=(120, 30, 40))
    d.polygon(S(up), fill=BEAK)
    # olho
    ex, ey = hx + 12, hy - 14
    if blink:
        d.line(S([(ex-14, ey), (ex+14, ey)]), fill=(30, 20, 20), width=5*SS)
    else:
        d.ellipse(box(ex-17, ey-17, ex+17, ey+17), fill="white")
        d.ellipse(box(ex-6, ey-10, ex+12, ey+8), fill=(25, 20, 25))
        d.ellipse(box(ex+2, ey-7, ex+8, ey-1), fill="white")
    if female:
        for a in (-60, -30, 0):  # cílios
            r = math.radians(a - 90)
            d.line(S([(ex + 17*math.cos(r), ey + 17*math.sin(r)), (ex + 30*math.cos(r), ey + 30*math.sin(r))]), fill=(25, 20, 25), width=4*SS)
    else:
        bx, by = hx - 20, hy + 70  # gravatinha-borboleta
        d.polygon(S([(bx, by), (bx-34, by-20), (bx-34, by+20)]), fill=NAVY)
        d.polygon(S([(bx, by), (bx+34, by-20), (bx+34, by+20)]), fill=NAVY)
        d.ellipse(box(bx-9, by-9, bx+9, by+9), fill=YEL)
    # chapéu de palha (fita azul nele; fita rosa com flor nela)
    straw, straw_d = (232, 196, 120), (190, 150, 80)
    d.ellipse(box(hx-110, hy-78, hx+100, hy-36), fill=straw_d)
    d.ellipse(box(hx-106, hy-82, hx+96, hy-42), fill=straw)
    d.rounded_rectangle(box(hx-60, hy-150, hx+50, hy-58), radius=34*SS, fill=straw)
    for k in range(-56, 50, 12):  # trançado da palha
        d.line(S([(hx+k, hy-146), (hx+k+8, hy-62)]), fill=straw_d, width=2*SS)
    for k in range(-100, 92, 14):
        d.line(S([(hx+k, hy-66), (hx+k+10, hy-48)]), fill=straw_d, width=2*SS)
    band = (255, 120, 170) if female else NAVY
    d.rectangle(box(hx-60, hy-84, hx+50, hy-64), fill=band)
    if female:
        fx, fy = hx + 30, hy - 78
        for k in range(5):
            r = math.radians(k * 72)
            d.ellipse(box(fx + 15*math.cos(r) - 12, fy + 15*math.sin(r) - 12, fx + 15*math.cos(r) + 12, fy + 15*math.sin(r) + 12), fill=(255, 236, 120))
        d.ellipse(box(fx-9, fy-9, fx+9, fy+9), fill=(255, 150, 40))
    return im.resize((CW, CH), Image.LANCZOS)

cache = {}
def sprite(who, lvl, blink):
    k = (who, lvl, blink)
    if k not in cache:
        g = guara(lvl / 6, who == "F", blink).resize((int(CW*0.8), int(CH*0.8)), Image.LANCZOS)
        cache[k] = g.transpose(Image.FLIP_LEFT_RIGHT) if who == "F" else g
    return cache[k]

# ---- cenário (ver cenario.py)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent)); import cenario
_bgs = {k: cenario.SCENES[k][0](W, H) for k in dict.fromkeys(places)}
from PIL import ImageFilter
_sh = Image.new("RGBA", (W, H)); _d = ImageDraw.Draw(_sh)
for cx in (200, W - 200): _d.ellipse([cx - 120, 1588, cx + 120, 1622], fill=(60, 40, 20, 90))
_sh = _sh.filter(ImageFilter.GaussianBlur(9))  # sombra dos guarás no chão
_bgs = {k: Image.alpha_composite(v, _sh) for k, v in _bgs.items()}
def _tag(text):
    f = F("Inter-Bold.otf", 38); w = int(f.getlength(text)) + 70
    im = Image.new("RGBA", (w, 64)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, 63], 32, fill=(8, 26, 66, 210))
    d.ellipse([22, 22, 42, 42], fill=YEL); d.text((52, 9), text, font=f, fill="white"); return im
tags = {k: _tag(cenario.SCENES[k][1]) for k in _bgs}


def wrap(text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        c = (cur + " " + w).strip()
        if f.getlength(c) <= maxw or not cur: cur = c
        else: out.append(cur); cur = w
    return out + [cur]
def bubble(text, who):
    f = F("InterDisplay-Black.otf", 60); ls = wrap(text, f, 820); lh = 72
    w = int(max(f.getlength(l) for l in ls)) + 90; h = lh * len(ls) + 70
    im = Image.new("RGBA", (w, h + 40)); d = ImageDraw.Draw(im)
    col = (255, 120, 170) if who == "F" else YEL
    d.rounded_rectangle([0, 0, w - 1, h], 36, fill="white", outline=col, width=8)
    tx = w * (0.75 if who == "F" else 0.25)
    d.polygon([(tx - 26, h - 4), (tx + 26, h - 4), (tx + (24 if who == "F" else -24), h + 38)], fill="white")
    d.line([(tx - 26, h - 2), (tx + (24 if who == "F" else -24), h + 38), (tx + 26, h - 2)], fill=col, width=8)
    for i, l in enumerate(ls): d.text(((w - f.getlength(l)) / 2, 34 + i * lh), l, font=f, fill=NAVY)
    return im
bubbles = [bubble(txt, who) for who, txt in lines]
title_f = F("InterDisplay-Black.otf", 104)
title = Image.new("RGBA", (W, 280)); td = ImageDraw.Draw(title)
for i, l in enumerate(["VALEU A PENA", "VOTAR NELE!"]):
    x = (W - title_f.getlength(l)) / 2; y = 20 + i * 122
    td.text((x + 5, y + 6), l, font=title_f, fill=(120, 10, 20)); td.text((x, y), l, font=title_f, fill="white" if i == 0 else YEL)

ease = lambda x: 1 - (1 - max(0, min(1, x))) ** 3
def fade(im, o):
    if o >= 0.999: return im
    c = im.copy(); c.putalpha(im.getchannel("A").point(lambda v: int(v * o))); return c

def frame(n):
    t = n / FPS
    cur = max([0] + [i for i, s in enumerate(starts) if t >= s - 0.35])
    k = ease((t - (starts[cur] - 0.35)) / 0.5) if cur > 0 else 1.0
    fr = _bgs[places[cur]].copy()
    if k < 1 and places[cur] != places[cur - 1]:
        fr = Image.blend(_bgs[places[cur - 1]], fr, k)
    tg = tags[places[cur]]
    fr.alpha_composite(fade(tg, ease((t - (starts[cur] - 0.35)) / 0.4) if cur > 0 else ease(t / 0.5)), ((W - tg.width) // 2, 450))
    fr.alpha_composite(fade(title, ease(t / 0.5)), (0, int(150 + (1 - ease(t / 0.5)) * -40)))
    for who, x0 in (("M", -55), ("F", W - int(CW*0.8) + 55)):
        talking = env[who][n]
        lvl = int(round(talking * 6))
        blink = (n + (17 if who == "F" else 0)) % 105 < 4
        bob = math.sin(t * 2.2 + (1.3 if who == "F" else 0)) * 8 - talking * 14
        sp = sprite(who, lvl, blink)
        fr.alpha_composite(sp, (x0, int(1690 - sp.height + bob)))
    for i, ((who, _), s, dd) in enumerate(zip(lines, starts, durs)):
        e = s + dd + GAP * 0.8
        if s - 0.1 <= t < e:
            b = bubbles[i]; p = ease((t - s + 0.1) / 0.3)
            x = (W - b.width - 30) if who == "F" else 30
            x = max(20, min(W - b.width - 20, x))
            fr.alpha_composite(fade(b, p), (x, int(640 + (1 - p) * 30)))
    return fr

if len(sys.argv) > 2:
    frame(int(float(sys.argv[2]) * FPS)).convert("RGB").save(sys.argv[1]); sys.exit()
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", "podcast_audio.wav", "-shortest", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart", sys.argv[1]], stdin=subprocess.PIPE)
for n in range(NF): ff.stdin.write(frame(n).convert("RGB").tobytes())
ff.stdin.close(); ff.wait()
