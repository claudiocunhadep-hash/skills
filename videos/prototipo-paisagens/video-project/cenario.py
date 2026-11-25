"""Cenário mais realista: céu, sol, mangue com raízes-escora, palmeiras, mar com reflexo e areia."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def lerp(a, b, k): return tuple(int(x * (1 - k) + y * k) for x, y in zip(a, b))

def canopy(d, cx, cy, rx, ry, rnd, dark, light, n=420, leaf=(9, 18)):
    """Copa feita de centenas de 'cachos' de folhas, mais claros no alto à esquerda (luz do sol)."""
    pts = []
    for _ in range(n):
        a = rnd.uniform(0, 2 * math.pi); r = math.sqrt(rnd.random())
        x = cx + math.cos(a) * rx * r; y = cy + math.sin(a) * ry * r * (0.8 if math.sin(a) > 0 else 1)
        pts.append((y, x))
    for y, x in sorted(pts):  # de cima para baixo
        lt = max(0, min(1, 0.55 - (y - cy) / (2 * ry) - (x - cx) / (4 * rx) + rnd.uniform(-0.15, 0.15)))
        c = lerp(dark, light, lt); s = rnd.uniform(*leaf)
        d.ellipse([x - s, y - s * 0.7, x + s, y + s * 0.7], fill=c)

def mangrove(d, x, base, h, rnd, scale=1.0, haze=0.0):
    sky = (215, 190, 160)
    trunk = lerp((78, 58, 44), sky, haze)
    for k in range(int(7 * scale) + 3):  # raízes-escora arqueadas até a água
        sx = x + rnd.uniform(-30, 30) * scale; ex = sx + rnd.uniform(-90, 90) * scale
        top = base - h * rnd.uniform(0.25, 0.45)
        pts = [((1-t)**2*sx + 2*(1-t)*t*((sx+ex)/2) + t*t*ex, (1-t)**2*top + 2*(1-t)*t*(top - 30*scale) + t*t*base) for t in np.linspace(0, 1, 20)]
        d.line(pts, fill=trunk, width=max(2, int(5 * scale)), joint="curve")
    d.line([(x, base - h * 0.35), (x + rnd.uniform(-15, 15), base - h * 0.85)], fill=trunk, width=max(3, int(12 * scale)))
    canopy(d, x, base - h * 0.85, 110 * scale, 75 * scale, rnd,
           lerp((22, 62, 38), sky, haze), lerp((96, 160, 80), sky, haze), n=int(380 * scale) + 60, leaf=(7 * scale + 2, 15 * scale + 3))

def palm(d, x, base, h, lean, rnd):
    pts = [(x + lean * (t ** 1.6), base - h * t) for t in np.linspace(0, 1, 30)]
    for i in range(len(pts) - 1):  # tronco em anéis
        w = 26 - 12 * i / len(pts)
        d.line([pts[i], pts[i + 1]], fill=(110, 86, 62) if i % 2 else (92, 70, 50), width=int(w))
    tx, ty = pts[-1]
    for k in range(13):  # folhas: nervura curva + folíolos
        a = math.radians(-180 + k * 15 + rnd.uniform(-6, 6)); L = rnd.uniform(150, 210)
        rach = [(tx + math.cos(a) * L * t, ty + math.sin(a) * L * t * 0.55 + 90 * t * t) for t in np.linspace(0, 1, 18)]
        d.line(rach, fill=(70, 100, 40), width=4)
        for j, (rx, ry) in enumerate(rach[2:], 2):
            ll = 46 * math.sin(math.pi * j / 18) + 8
            for sgn in (-1, 1):
                b = a + sgn * 1.1
                c = (60 + j * 4, 120 + j * 3, 45) if sgn < 0 else (40 + j * 3, 95 + j * 2, 35)
                d.line([(rx, ry), (rx + math.cos(b) * ll, ry + math.sin(b) * ll * 0.6 + ll * 0.5)], fill=c, width=3)
    for c in range(4):  # cocos
        d.ellipse([tx - 18 + c * 9, ty + 4 + (c % 2) * 8, tx + 2 + c * 9, ty + 26 + (c % 2) * 8], fill=(90, 70, 30))

def build(W, H, horizon=1290, shore=1440):
    rnd = random.Random(7)
    sky = Image.new("RGB", (W, H)); d = ImageDraw.Draw(sky)
    for y in range(H):
        k = min(1, y / horizon); d.line([(0, y), (W, y)], fill=lerp((62, 132, 214), (255, 200, 150), k ** 1.3))
    # sol com brilho difuso
    glow = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(glow)
    for r, a in ((260, 40), (190, 70), (140, 120)): g.ellipse([840 - r, 1110 - r, 840 + r, 1110 + r], fill=(255, 236, 170, a))
    g.ellipse([760, 1030, 920, 1190], fill=(255, 240, 190, 255))
    sky = Image.alpha_composite(sky.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(12)))
    for cx, cy, s in ((200, 330, 1.0), (760, 520, 0.8), (480, 820, 0.6)):  # nuvens suaves
        cl = Image.new("RGBA", (W, H), (255, 255, 255, 0)); c = ImageDraw.Draw(cl)
        for _ in range(14):
            dx, dy, r = rnd.uniform(-160, 160) * s, rnd.uniform(-30, 30) * s, rnd.uniform(40, 80) * s
            c.ellipse([cx + dx - r, cy + dy - r * 0.6, cx + dx + r, cy + dy + r * 0.6], fill=(255, 245, 235, 150))
        sky = Image.alpha_composite(sky, cl.filter(ImageFilter.GaussianBlur(14)))
    # mangue distante (névoa) e mangue próximo
    far = Image.new("RGBA", (W, H)); fd = ImageDraw.Draw(far)
    for x in range(-60, W + 120, 70): mangrove(fd, x + rnd.uniform(-20, 20), horizon, rnd.uniform(130, 170), rnd, 0.55, haze=0.45)
    sky = Image.alpha_composite(sky, far.filter(ImageFilter.GaussianBlur(2.2)))
    near = Image.new("RGBA", (W, H)); nd = ImageDraw.Draw(near)
    for x in (-40, 150, 330, 620, 820, 1040): mangrove(nd, x + rnd.uniform(-25, 25), horizon + 8, rnd.uniform(190, 240), rnd, 0.9, haze=0.12)
    sky = Image.alpha_composite(sky, near.filter(ImageFilter.GaussianBlur(0.8)))
    # mar com reflexo do mangue
    top = sky.crop((0, horizon - 300, W, horizon)).transpose(Image.FLIP_TOP_BOTTOM)
    sea = Image.new("RGBA", (W, shore - horizon), (34, 112, 150, 255))
    refl = top.resize((W, shore - horizon)).filter(ImageFilter.GaussianBlur(4))
    sea = Image.blend(sea, refl, 0.45); sd = ImageDraw.Draw(sea)
    for _ in range(120):
        y = rnd.uniform(0, shore - horizon); x = rnd.uniform(0, W); L = rnd.uniform(20, 90)
        sd.line([(x, y), (x + L, y)], fill=(170, 210, 225, 255) if x > 650 else (120, 170, 195, 255), width=2)
    sky.paste(sea, (0, horizon))
    # areia com textura e faixa molhada
    sand = np.zeros((H - shore, W, 3), np.float32)
    yy = np.linspace(0, 1, H - shore)[:, None]
    for i, (a, b) in enumerate(zip((196, 170, 128), (238, 214, 168))): sand[..., i] = a + (b - a) * np.clip(yy * 4, 0, 1)
    sand += np.random.default_rng(3).normal(0, 6, sand.shape)
    sky.paste(Image.fromarray(np.clip(sand, 0, 255).astype(np.uint8)).convert("RGBA"), (0, shore))
    # palmeiras nas bordas (primeiro plano)
    pl = Image.new("RGBA", (W, H)); pd = ImageDraw.Draw(pl)
    palm(pd, -10, 1560, 640, 90, rnd); palm(pd, W + 20, 1580, 600, -110, rnd)
    sh = Image.new("RGBA", (W, H)); ImageDraw.Draw(sh).ellipse([-120, 1530, 220, 1600], fill=(0, 0, 0, 60))
    sky = Image.alpha_composite(sky, sh.filter(ImageFilter.GaussianBlur(10)))
    return Image.alpha_composite(sky, pl)

litoral = build

# ---------- utilidades comuns
def sky_grad(W, H, top, bottom, horizon):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H): d.line([(0, y), (W, y)], fill=lerp(top, bottom, min(1, y / horizon) ** 1.3))
    return im.convert("RGBA")

def clouds(im, rnd, spots, alpha=150):
    W, H = im.size
    for cx, cy, s in spots:
        cl = Image.new("RGBA", (W, H), (255, 255, 255, 0)); c = ImageDraw.Draw(cl)
        for _ in range(26):
            dx, dy, r = rnd.uniform(-170, 170) * s, rnd.uniform(-25, 25) * s, rnd.uniform(30, 70) * s
            c.ellipse([cx + dx - r, cy + dy - r * 0.55, cx + dx + r, cy + dy + r * 0.5], fill=(255, 255, 255, alpha))
        im = Image.alpha_composite(im, cl.filter(ImageFilter.GaussianBlur(10)))
    return im

def ridge(W, base, amp, rnd, freq=(1.5, 3.7, 7.1)):
    ph = [rnd.uniform(0, 6.28) for _ in freq]
    return [(x, base - amp * sum(math.sin(x / W * f * 6.28 + p) / (i + 1) for i, (f, p) in enumerate(zip(freq, ph))))
            for x in range(0, W + 4, 4)]

def noise_fill(im, box, c0, c1, seed, sigma=6, vertical=True):
    x0, y0, x1, y1 = box; h, w = y1 - y0, x1 - x0
    k = np.linspace(0, 1, h)[:, None] if vertical else np.linspace(0, 1, w)[None, :]
    arr = np.zeros((h, w, 3), np.float32)
    for i in range(3): arr[..., i] = c0[i] + (c1[i] - c0[i]) * k
    arr += np.random.default_rng(seed).normal(0, sigma, arr.shape)
    im.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA"), (x0, y0))

def palm_up(d, x, base, h, lean, rnd, spread=(-160, -20), n=11, frond=(130, 180), droop=50):
    """Palmeira de folhas mais eretas (babaçu)."""
    pts = [(x + lean * (t ** 1.6), base - h * t) for t in np.linspace(0, 1, 30)]
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=(98, 82, 64) if i % 2 else (84, 70, 54), width=int(22 - 8 * i / len(pts)))
    tx, ty = pts[-1]
    for k in range(n):
        a = math.radians(spread[0] + (spread[1] - spread[0]) * k / (n - 1) + rnd.uniform(-5, 5)); L = rnd.uniform(*frond)
        rach = [(tx + math.cos(a) * L * t, ty + math.sin(a) * L * t + droop * t * t) for t in np.linspace(0, 1, 16)]
        d.line(rach, fill=(66, 96, 40), width=4)
        for j, (rx, ry) in enumerate(rach[2:], 2):
            ll = 40 * math.sin(math.pi * j / 16) + 6
            for sgn in (-1, 1):
                b = a + sgn * 0.9
                d.line([(rx, ry), (rx + math.cos(b) * ll, ry + math.sin(b) * ll * 0.7 + ll * 0.45)],
                       fill=(70 + j * 4, 125 + j * 3, 50) if sgn < 0 else (45 + j * 3, 98 + j * 2, 38), width=3)

# ---------- Lençóis Maranhenses: dunas brancas e lagoas azul-turquesa
def lencois(W, H):
    rnd = random.Random(11); horizon = 1180
    im = sky_grad(W, H, (40, 120, 220), (190, 225, 250), horizon)
    im = clouds(im, rnd, ((220, 300, 1.0), (820, 470, 0.9), (520, 760, 0.6)), 170)
    layers = [(horizon, 45, (232, 228, 218)), (horizon + 100, 60, (242, 238, 228)), (horizon + 220, 55, (250, 247, 238))]
    for li, (base, amp, lite) in enumerate(layers):
        top = ridge(W, base, amp, rnd, (0.9, 1.7, 2.9))
        lay = Image.new("RGBA", (W, H), (255, 255, 255, 0)); d = ImageDraw.Draw(lay)
        if li > 0:  # lagoa azul-turquesa no vale entre as dunas
            lag = ridge(W, base + 10, 10, rnd, (1.3, 3.1))
            d.polygon(lag + [(W, base + 140), (0, base + 140)], fill=(40, 175, 195, 255) if li == 1 else (25, 150, 185, 255))
            for _ in range(30):
                x = rnd.uniform(0, W); y = base + rnd.uniform(15, 90)
                d.line([(x, y), (x + rnd.uniform(20, 60), y)], fill=(160, 225, 235, 255), width=2)
        d.polygon(top + [(W, H), (0, H)], fill=lite + (255,))
        sh = Image.new("RGBA", (W, H), (180, 170, 150, 0)); sd = ImageDraw.Draw(sh)
        for i in range(len(top) - 1):  # sombra suave nas encostas viradas para longe do sol
            x, y = top[i]; ny = top[i + 1][1]
            if ny > y + 0.4: sd.line([(x, y + 3), (x, y + 30 + (ny - y) * 18)], fill=(170, 160, 140, 120), width=5)
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).polygon(top + [(W, H), (0, H)], fill=255)
        lay = Image.alpha_composite(lay, Image.composite(sh, Image.new("RGBA", (W, H), (0, 0, 0, 0)), mask))
        im = Image.alpha_composite(im, lay)
    shore = 1480
    noise_fill(im, (0, shore, W, H), (240, 234, 218), (250, 246, 236), 5, 4)
    d = ImageDraw.Draw(im)
    for y in range(shore + 20, H, 26):  # ondulações do vento na areia
        d.line([(x, y + 6 * math.sin(x / 55 + y)) for x in range(0, W + 10, 10)], fill=(226, 218, 200), width=3)
    return im

# ---------- Região Tocantina: Rio Tocantins largo, serra, cerrado e babaçu
def cerrado_tree(d, x, base, s, rnd):
    tr = (90, 70, 55); y = base
    pts = [(x, y)]
    for k in range(5): x += rnd.uniform(-14, 14) * s; y -= rnd.uniform(18, 26) * s; pts.append((x, y))
    d.line(pts, fill=tr, width=int(9 * s), joint="curve")
    for k in range(3):
        bx = x + rnd.uniform(-60, 60) * s; by = y - rnd.uniform(10, 40) * s
        d.line([(x, y), (bx, by)], fill=tr, width=int(5 * s))
        canopy(d, bx, by - 8 * s, 55 * s, 26 * s, rnd, (52, 88, 40), (150, 170, 80), n=int(90 * s) + 20, leaf=(5 * s + 2, 10 * s + 3))

def tocantina(W, H):
    rnd = random.Random(23); horizon = 1230
    im = sky_grad(W, H, (70, 140, 215), (250, 215, 165), horizon)
    im = clouds(im, rnd, ((300, 380, 1.1), (800, 620, 0.8)), 160)
    far = Image.new("RGBA", (W, H)); fd = ImageDraw.Draw(far)
    fd.polygon(ridge(W, horizon - 70, 50, rnd, (1.1, 2.9)) + [(W, horizon), (0, horizon)], fill=(130, 150, 170))  # serra azulada
    fd.polygon(ridge(W, horizon - 25, 25, rnd, (2.0, 5.5)) + [(W, horizon), (0, horizon)], fill=(96, 128, 98))
    im = Image.alpha_composite(im, far.filter(ImageFilter.GaussianBlur(2)))
    d = ImageDraw.Draw(im)
    for x in range(-20, W + 40, 60):  # mata ciliar do outro lado do rio
        canopy(d, x + rnd.uniform(-15, 15), horizon - 10, 50, 22, rnd, (40, 80, 45), (110, 150, 80), n=60, leaf=(5, 9))
    # rio largo e calmo, com reflexo do céu
    river_bot = 1430
    noise_fill(im, (0, horizon, W, river_bot), (150, 170, 175), (70, 110, 125), 9, 3)
    for _ in range(140):
        y = rnd.uniform(horizon, river_bot); x = rnd.uniform(0, W); L = rnd.uniform(25, 110)
        d.line([(x, y), (x + L, y)], fill=(200, 210, 205) if rnd.random() < 0.5 else (95, 130, 140), width=2)
    # barranco com capim do cerrado
    bank = ridge(W, river_bot, 10, rnd, (3.0, 7.0))
    d.polygon(bank + [(W, H), (0, H)], fill=(170, 150, 90))
    noise_fill(im, (0, river_bot + 20, W, H), (176, 160, 96), (150, 132, 74), 13, 8)
    for _ in range(1400):  # capim
        x = rnd.uniform(0, W); y = rnd.uniform(river_bot + 10, H); L = rnd.uniform(10, 34) * (0.6 + (y - river_bot) / 600)
        d.line([(x, y), (x + rnd.uniform(-8, 8), y - L)], fill=rnd.choice([(196, 176, 96), (150, 140, 70), (120, 130, 60), (210, 190, 120)]), width=2)
    for x, s in ((360, 0.9), (700, 0.75)): cerrado_tree(d, x, river_bot + 30, s, rnd)
    pl = Image.new("RGBA", (W, H)); pd = ImageDraw.Draw(pl)
    palm_up(pd, 40, 1600, 560, 40, rnd); palm_up(pd, W - 40, 1620, 520, -50, rnd)
    return Image.alpha_composite(im, pl)

# ---------- Baía de São Marcos: mar aberto com o ferry boat
def ferry(d, x, y, s):
    hull = [(x, y), (x + 520 * s, y), (x + 480 * s, y + 70 * s), (x + 30 * s, y + 70 * s)]
    d.polygon(hull, fill=(245, 245, 245)); d.rectangle([x + 30 * s, y + 40 * s, x + 485 * s, y + 70 * s], fill=(30, 70, 150))
    d.rectangle([x + 60 * s, y - 70 * s, x + 380 * s, y], fill=(235, 238, 240))
    d.rectangle([x + 140 * s, y - 130 * s, x + 320 * s, y - 70 * s], fill=(245, 245, 245))
    for k in range(9): d.rectangle([x + (75 + k * 33) * s, y - 55 * s, x + (95 + k * 33) * s, y - 35 * s], fill=(60, 90, 130))
    for k in range(5): d.rectangle([x + (155 + k * 32) * s, y - 115 * s, x + (175 + k * 32) * s, y - 95 * s], fill=(60, 90, 130))
    d.rectangle([x + 250 * s, y - 175 * s, x + 280 * s, y - 130 * s], fill=(200, 40, 40))  # chaminé
    d.line([(x + 20 * s, y + 70 * s), (x + 520 * s, y + 74 * s)], fill=(255, 255, 255), width=3)

def baia(W, H):
    rnd = random.Random(31); horizon = 1210
    im = sky_grad(W, H, (60, 130, 210), (240, 205, 170), horizon)
    im = clouds(im, rnd, ((260, 350, 1.0), (780, 560, 1.0), (430, 900, 0.6)), 165)
    far = Image.new("RGBA", (W, H)); fd = ImageDraw.Draw(far)
    fd.polygon(ridge(W, horizon - 12, 8, rnd, (2.0, 6.0)) + [(W, horizon), (0, horizon)], fill=(90, 120, 110))  # costa distante
    im = Image.alpha_composite(im, far.filter(ImageFilter.GaussianBlur(1.5)))
    shore = 1450
    noise_fill(im, (0, horizon, W, shore), (120, 165, 185), (40, 105, 135), 17, 3)
    d = ImageDraw.Draw(im)
    for _ in range(180):
        y = rnd.uniform(horizon, shore); x = rnd.uniform(0, W); L = rnd.uniform(15, 80) * (0.5 + (y - horizon) / 300)
        d.line([(x, y), (x + L, y)], fill=(185, 215, 225) if rnd.random() < 0.6 else (60, 120, 150), width=2)
    ferry(d, 345, 1262, 0.75)
    for k in range(30):  # esteira do ferry
        d.line([(345 + 390 + k * 10, 1315 + k * 0.6), (345 + 390 + k * 10 + 30, 1315 + k * 0.6)], fill=(235, 245, 250), width=3)
    # espuma da beira e areia molhada
    noise_fill(im, (0, shore, W, H), (200, 180, 140), (236, 214, 170), 19, 5)
    d.line([(x, shore + 4 * math.sin(x / 40)) for x in range(0, W + 10, 10)], fill=(250, 250, 245), width=8)
    pl = Image.new("RGBA", (W, H)); pd = ImageDraw.Draw(pl)
    palm(pd, -10, 1570, 620, 90, rnd)
    return Image.alpha_composite(im, pl)

SCENES = {"lencois": (lencois, "LENÇÓIS MARANHENSES"), "litoral": (litoral, "LITORAL MARANHENSE"),
          "tocantina": (tocantina, "REGIÃO TOCANTINA"), "baia": (baia, "BAÍA DE SÃO MARCOS")}
