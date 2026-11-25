import subprocess, sys
from PIL import Image, ImageDraw, ImageFont
W, H, FPS, GAP, START = 1080, 1920, 30, 0.45, 0.3
FD = "/usr/share/fonts/opentype/inter/"
NAVY, NAVY2, YEL, WHITE, PINK = (8,26,66), (18,58,140), (255,204,0), (255,255,255), (255,120,170)
F = lambda n, px: ImageFont.truetype(FD + n, px)
lines = [l.split("\t") for l in open("lines.tsv").read().strip().split("\n")]
files = [f"assets/l{i}_{w}.mp3" for i, (w, _) in enumerate(lines)]
durs = [float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f])) for f in files]
starts, t = [], START
for d in durs: starts.append(t); t += d + GAP
DUR = t + 0.4
# áudio: cada fala no seu tempo
inputs, filt = [], []
for i, (f, s) in enumerate(zip(files, starts)):
    inputs += ["-i", f]; filt.append(f"[{i}]adelay={int(s*1000)}|{int(s*1000)}[a{i}]")
filt.append("".join(f"[a{i}]" for i in range(len(files))) + f"amix=inputs={len(files)}:normalize=0,apad,atrim=0:{DUR:.3f}[out]")
subprocess.run(["ffmpeg","-y","-loglevel","error",*inputs,"-filter_complex",";".join(filt),"-map","[out]","podcast_audio.wav"], check=True)
with open("podcast_audio.srt","w") as f:
    def ts(x): return f"{int(x//3600):02}:{int(x%3600//60):02}:{x%60:06.3f}".replace(".",",")
    for i,((w,txt),s,d) in enumerate(zip(lines,starts,durs)): f.write(f"{i+1}\n{ts(s)} --> {ts(s+d)}\n{txt}\n\n")

def wrap(text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        c = (cur+" "+w).strip()
        if f.getlength(c) <= maxw or not cur: cur = c
        else: out.append(cur); cur = w
    return out+[cur]
def card(tag, text, color, tagfg):
    ft, fb = F("Inter-Bold.otf", 40), F("InterDisplay-Black.otf", 78)
    ls = wrap(text, fb, 820); lh = 92
    w = int(max(fb.getlength(l) for l in ls)) + 80; h = 80 + lh*len(ls) + 50
    im = Image.new("RGBA", (max(w, 420), h)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0,0,im.width-1,h-1], 34, fill=(255,255,255,30), outline=color, width=5)
    tw = ft.getlength(tag); d.rounded_rectangle([40,-2+0,40+tw+40,58], 18, fill=color)
    d.text((60,6), tag, font=ft, fill=tagfg)
    for i,l in enumerate(ls): d.text((40, 82+i*lh), l, font=fb, fill=WHITE)
    return im
def big(text, color, px=130):
    f = F("InterDisplay-Black.otf", px); ls = wrap(text, f, 960)
    lh = int(px*1.12); im = Image.new("RGBA", (1000, lh*len(ls))); d = ImageDraw.Draw(im)
    for i,l in enumerate(ls): d.text(((1000-f.getlength(l))/2, i*lh), l, font=f, fill=color)
    return im
els = [  # (início, fim, imagem, x, y)
    (starts[0], starts[1]-0.1, big("VALEU A PENA VOTAR NELE!", YEL), "c", 760),
    (starts[1], DUR, card("ELEITOR", lines[1][1], YEL, NAVY), 60, 520),
    (starts[2], DUR, card("ELEITORA", lines[2][1], PINK, NAVY), "r", 900),
    (starts[3], DUR, big("VALEU A PENA VOTAR NELE!", YEL, 92), "c", 1330),
]
bg = Image.new("RGB",(W,H)); d = ImageDraw.Draw(bg)
for y in range(H):
    k=y/H; d.line([(0,y),(W,y)], fill=tuple(int(NAVY2[i]*(1-k)+NAVY[i]*k) for i in range(3)))
bg = bg.convert("RGBA")
ease = lambda x: 1-(1-max(0,min(1,x)))**3
ff = subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
    "-i","podcast_audio.wav","-shortest","-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",sys.argv[1]], stdin=subprocess.PIPE)
for n in range(int(DUR*FPS)):
    t = n/FPS; fr = bg.copy()
    for a,b,im,x,y in els:
        if not (a <= t < b+0.25): continue
        p = ease((t-a)/0.4) * (1-ease((t-b)/0.25) if t > b else 1)
        o = im.copy(); o.putalpha(im.getchannel("A").point(lambda v: int(v*p)))
        X = (W-im.width)//2 if x=="c" else (W-im.width-60 if x=="r" else x)
        fr.alpha_composite(o, (int(X), int(y + (1-p)*50)))
    ff.stdin.write(fr.convert("RGB").tobytes())
ff.stdin.close(); ff.wait()
