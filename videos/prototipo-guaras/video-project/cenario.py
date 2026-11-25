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
        cl = Image.new("RGBA", (W, H)); c = ImageDraw.Draw(cl)
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
