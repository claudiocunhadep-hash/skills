"""Gera o Reels vertical (texto animado + legenda) sincronizado com a narração.

Uso: python3 gen.py <escala> <saida.mp4>
  escala 1 -> 1080x1920 (rascunho); escala 2 -> 2160x3840 (4K vertical)
"""
import math, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
S = float(sys.argv[1]); OUT = sys.argv[2]
W, H, FPS = int(1080 * S), int(1920 * S), 30
FD = "/usr/share/fonts/opentype/inter/"
NAVY, NAVY2 = (8, 26, 66), (18, 58, 140)
YELLOW, WHITE, SOFT = (255, 204, 0), (255, 255, 255), (200, 214, 240)

def font(name, px): return ImageFont.truetype(FD + name, int(px * S))
BLACK = lambda px: font("InterDisplay-Black.otf", px)
BOLD = lambda px: font("Inter-Bold.otf", px)
SEMI = lambda px: font("Inter-SemiBold.otf", px)

def srt_time(t):
    h, m, s = t.replace(",", ".").split(":"); return int(h) * 3600 + int(m) * 60 + float(s)
cues = []
for block in (ROOT / "podcast_audio.srt").read_text().strip().split("\n\n"):
    lines = block.strip().split("\n")
    a, b = lines[1].split(" --> ")
    cues.append((srt_time(a), srt_time(b), " ".join(lines[2:])))
C = [c[0] for c in cues]  # início de cada frase
AUDIO = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "csv=p=0", str(ROOT / "podcast_audio.mp3")]))
DUR = AUDIO + 0.4

def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]

def text_block(text, f, color, maxw=900, align="center", lh=1.12, box=None, pad=(36, 22), minw=0):
    """Renderiza um bloco de texto RGBA (opcionalmente dentro de uma caixa arredondada)."""
    lines = wrap(text, f, maxw * S)
    asc, desc = f.getmetrics(); lhpx = int((asc + desc) * lh)
    tw = max(int(max(f.getlength(l) for l in lines)), int(minw * S)); th = lhpx * len(lines)
    px, py = (int(pad[0] * S), int(pad[1] * S)) if box else (0, 0)
    im = Image.new("RGBA", (tw + 2 * px, th + 2 * py), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if box: d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=int(26 * S), fill=box)
    for i, l in enumerate(lines):
        x = px + ((tw - f.getlength(l)) / 2 if align == "center" else 0)
        d.text((x, py + i * lhpx), l, font=f, fill=color)
    return im

def pill(text, f, fg, bg):
    return text_block(text, f, fg, box=bg, pad=(34, 14))

def bar(w, h, color):
    im = Image.new("RGBA", (int(w * S), int(h * S))); ImageDraw.Draw(im).rounded_rectangle(
        [0, 0, im.width - 1, im.height - 1], radius=int(h * S / 2), fill=color); return im

# ---- cenas: (início, fim, [(aparece_em, imagem, y_centro_em_1080x1920, animação)])
sec = {"hook": (0, C[1]), "intro": (C[1], C[2]), "ferry": (C[2], C[5]),
       "inclusao": (C[5], C[7]), "moradia": (C[7], C[9]), "fim": (C[9], DUR)}

def bullet(txt, sub=None):
    t = text_block(("✓  " + txt), BOLD(52), WHITE, maxw=860, align="left", box=(255, 255, 255, 28), pad=(40, 26), minw=860)
    return t

scenes = [
    (*sec["hook"], [
        (0.05, text_block("VALEU A PENA", BLACK(118), WHITE), 760, "pop"),
        (0.45, text_block("VOTAR NELE!", BLACK(132), YELLOW), 920, "pop")]),
    (*sec["intro"], [
        (C[1], pill("DEPUTADO ESTADUAL", BOLD(44), NAVY, YELLOW), 560, "up"),
        (C[1] + 0.25, text_block("CLÁUDIO", BLACK(150), WHITE), 720, "up"),
        (C[1] + 0.45, text_block("CUNHA", BLACK(170), YELLOW), 890, "up"),
        (C[1] + 2.6, text_block("Trabalho de verdade pelo Maranhão", SEMI(50), SOFT, maxw=960), 1050, "up")]),
    (*sec["ferry"], [
        (C[2], pill("FERRY BOAT", BOLD(48), NAVY, YELLOW), 340, "up"),
        (C[2] + 0.2, text_block("Menos fila para a Baixada", BLACK(76), WHITE, maxw=900), 510, "up"),
        (C[3], bullet("Lei aprovada: prioridade na travessia"), 760, "up"),
        (C[3] + 2.4, text_block("Ponta da Espera  ↔  Cujupe", BOLD(48), YELLOW), 915, "up"),
        (C[4] + 0.2, bullet("Na luta pelo ferry cargueiro"), 1050, "up"),
        (C[4] + 2.6, bullet("Ferry Web: agendamento pelo celular"), 1220, "up")]),
    (*sec["inclusao"], [
        (C[5], pill("INCLUSÃO", BOLD(48), NAVY, YELLOW), 420, "up"),
        (C[5] + 0.2, pill("LEI APROVADA", BOLD(40), WHITE, (255, 255, 255, 40)), 540, "up"),
        (C[5] + 1.4, text_block("Pessoas com autismo no mercado de trabalho", BLACK(84), WHITE, maxw=920), 790, "up"),
        (C[6], text_block("Todo mundo merece uma oportunidade.", BOLD(56), YELLOW, maxw=880), 1080, "up")]),
    (*sec["moradia"], [
        (C[7], pill("MORADIA", BOLD(48), NAVY, YELLOW), 440, "up"),
        (C[7] + 0.3, text_block("Política Estadual de Prevenção às Remoções e Despejos", BLACK(76), WHITE, maxw=920), 700, "up"),
        (C[8], text_block("Ninguém na rua sem ter para onde ir.", BOLD(56), YELLOW, maxw=880), 1010, "up")]),
    (*sec["fim"], [
        (C[9], text_block("TRABALHO", BLACK(96), WHITE), 360, "up"),
        (C[9] + 0.9, text_block("COMPROMISSO", BLACK(96), WHITE), 480, "up"),
        (C[9] + 1.9, text_block("RESULTADO", BLACK(96), YELLOW), 600, "up"),
        (C[10], bar(520, 10, YELLOW), 720, "up"),
        (C[10] + 0.1, text_block("CLÁUDIO CUNHA", BLACK(100), WHITE, maxw=1040), 830, "up"),
        (C[10] + 0.4, text_block("Deputado Estadual", SEMI(54), SOFT), 935, "up"),
        (C[11], text_block("VALEU A PENA VOTAR NELE!", BLACK(78), NAVY, box=YELLOW + (255,), pad=(40, 24), maxw=940), 1130, "pop")]),
]

# legendas pré-renderizadas (faixa inferior, acima da área de botões do Reels)
subs = [(a, b, text_block(t, BOLD(46), WHITE, maxw=900, box=(0, 0, 0, 150), pad=(32, 18))) for a, b, t in cues]

# fundo com degradê vertical + faixa amarela
bg = Image.new("RGB", (W, H)); d = ImageDraw.Draw(bg)
for y in range(H):
    k = y / H; d.line([(0, y), (W, y)], fill=tuple(int(NAVY2[i] * (1 - k) + NAVY[i] * k) for i in range(3)))
d.rectangle([0, int(250 * S), int(16 * S), int(1500 * S)], fill=YELLOW)
bg = bg.convert("RGBA")

def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3

def faded(im, o):
    if o >= 0.999: return im
    a = im.getchannel("A").point(lambda v: int(v * o)); out = im.copy(); out.putalpha(a); return out

def place(frame, im, cy, t, t0, kind, scene_out):
    p = ease((t - t0) / 0.45)
    if p <= 0: return
    o = p * scene_out
    if kind == "pop":
        sc = 0.7 + 0.3 * (1 + 0.12 * math.sin(min(1, p) * math.pi)) if p < 1 else 1.0
        if abs(sc - 1) > 0.01:
            im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
        dy = 0
    else:
        dy = (1 - p) * 60 * S
    x = (W - im.width) // 2; y = int(cy * S - im.height / 2 + dy)
    frame.alpha_composite(faded(im, o), (x, y))

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(ROOT / "podcast_audio.mp3"),
    "-af", "apad", "-t", f"{DUR:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)

for n in range(int(DUR * FPS)):
    t = n / FPS; frame = bg.copy()
    for a, b, els in scenes:
        if not (a - 0.01 <= t < b + 0.3): continue
        out = 1 - ease((t - b) / 0.3) if t > b else 1.0
        for t0, im, cy, kind in els:
            place(frame, im, cy, t, t0, kind, out)
    for a, b, im in subs:
        if a <= t < b + 0.05:
            frame.alpha_composite(im, ((W - im.width) // 2, int(1380 * S)))
            break
    ff.stdin.write(frame.convert("RGB").tobytes())
ff.stdin.close(); ff.wait()
print("ok", OUT, f"{DUR:.2f}s")
