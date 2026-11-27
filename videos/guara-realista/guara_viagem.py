"""Guará realista: voa do litoral até Imperatriz e pousa no viaduto da BR-010 para dar a notícia.

Uso:  SHOT=1|2|3 python3 guara_viagem.py <saida_dir> <f_ini> <f_fim> [larg alt amostras]
  1 = litoral (mangue), 2 = viagem pelo alto (rio Tocantins), 3 = viaduto na BR-010 (pouso + fala)
Reaproveita o guará, os materiais e o mangue de guara_real2.py.
"""
import os, sys, math, random, json
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = int(os.environ.get('SHOT', '3'))
SRC = open(os.path.join(HERE, 'guara_real2.py'), encoding='utf-8').read().split('\n')
def lines(a, b): return '\n'.join(SRC[a - 1:b]) + '\n'
exec(lines(1, 465))            # cena, materiais, guará, asas
exec(lines(466, 482))          # céu e sol da manhã
if SHOT == 1:
    exec(lines(483, 574))      # água, lama e mangue
exec(lines(575, 592))          # câmera e render
import numpy as np
from PIL import Image, ImageDraw, ImageFont

tronco = bpy.data.objects.new('tronco', None); col.objects.link(tronco); tronco.parent = bird; tronco.location = (0, 0, -0.09)
for o in list(bpy.data.objects):
    if o.parent == bird and o is not tronco and o.name.split('.')[0] != 'perna':
        o.parent = tronco

# ------------------------------------------------------------------ pose genérica do guará
def wings_flap(t, freq=3.1, amp=48):
    ph = 2 * math.pi * freq * t
    phi = 22 + amp * math.sin(ph); hphi = phi + 18 * math.sin(ph - 0.9)
    psi = (12 + 18 * max(0, math.cos(ph)), 6 + 22 * max(0, math.cos(ph))); hpsi = 14 + 30 * max(0, math.cos(ph))
    return phi, psi, hphi, hpsi, -0.025 * math.sin(ph)

def wings_glide(t):
    return 6 + 3 * math.sin(t * 1.3), (12, 8), 2 + 3 * math.sin(t * 1.3), 16, 0.0

def set_bird(pos, yaw, pitch, fly, legs_down, fold, wing, look=0.0, nod=0.0, mouth=0.0, t=0.0, flare=0.0, roll=0.0):
    phi, psi, hphi, hpsi, bob = wing
    bird.location = pos + Vector((0, 0, bob))
    bird.rotation_euler = (roll, pitch, yaw)
    breathe = 0.004 * math.sin(t * 2.4) * (1 - fly)
    keys = {}
    for k in BODY_KEYS:
        p = vlerp(Vector(STAND[k]), Vector(FLY[k]), fly)
        if k.startswith('pesc') or k.startswith('cab'): p.z += breathe * 2
        keys[k] = tuple(p)
    co, sp = loft_coords(keys)
    for v, c in zip(body.data.vertices, co): v.co = c
    body.data.update()
    cov = smooth((fold - 0.55) / 0.4)
    for o, s_ in wing_cover:
        o.scale = (1, max(cov, 1e-3), max(cov, 1e-3))
    for lo, s in legs: set_leg(lo, s, 1 - legs_down)
    hb = Vector(keys['cab_tras']); hf = Vector(keys['cab_frente'])
    fwd = (hf - hb).normalized()
    Rh = Matrix.Rotation(look, 3, 'Z') @ Matrix.Rotation(nod, 3, 'Y')
    head.matrix_basis = frame_from(Rh @ fwd, Rh @ Vector((0, 0, 1)), hb.lerp(hf, 0.55))
    low_pivot.rotation_euler = (0, math.radians(14) * mouth, 0)
    place_feathers(fold, phi, psi, hphi, hpsi, flare)
    for o in bpy.data.objects:
        if 'tail' in o.keys():
            k = o['tail']; spread = 1 + 0.9 * (1 - fold)
            rot = Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Rotation(-k * 0.7 * spread, 4, 'Z') @ Matrix.Rotation(0.12 + abs(k) * 0.08, 4, 'Y')
            o.matrix_basis = Matrix.Translation((-0.15, k * 0.02, 0.442 + abs(k) * 0.004)) @ rot

def aim_cam(target, lens):
    focus.location = target
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam_d.lens = lens

def mat_color(name, hexc, rough=0.6, **kw):
    m, _ = principled(name, hexc, rough, **kw); return m

def box(name, size, loc, mat, rot=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    o = obj_from_bm(name, bm, mat); o.scale = size; o.location = loc; o.rotation_euler = (0, 0, rot)
    for p in o.data.polygons: p.use_smooth = False
    return o

def noise_mat(name, c0, c1, scale=2.0, rough=0.8, bump=0.0):
    m, b = principled(name, c0, rough); nt = m.node_tree
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = 8
    r_ = nt.nodes.new('ShaderNodeValToRGB'); r_.color_ramp.elements[0].color = srgb(c0); r_.color_ramp.elements[1].color = srgb(c1)
    nt.links.new(n.outputs['Fac'], r_.inputs['Fac']); nt.links.new(r_.outputs['Color'], b.inputs['Base Color'])
    if bump:
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
        nt.links.new(n.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

# babaçu (palmeira da região): tronco + folhas em arco
PALM_TRUNK = noise_mat('tronco_palm', 0x4d4033, 0x6b5a48, 8, 0.9, 0.3)
PALM_LEAF = noise_mat('folha_palm', 0x172a0e, 0x34501c, 4, 0.65)
def palm_mesh():
    bm = bmesh.new()
    def frond(a, el, L):
        pts = []
        for i in range(9):
            u = i / 8
            d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
            p = d * L * u + Vector((0, 0, -0.9 * L * u * u))
            pts.append(p)
        side = Vector((-math.sin(a), math.cos(a), 0))
        prev = None
        for i, p in enumerate(pts):
            w = 0.32 * math.sin(math.pi * min(1, (i / 8) * 1.1 + 0.05))
            a_ = bm.verts.new(p + side * w - Vector((0, 0, 0.08 * w))); b_ = bm.verts.new(p); c_ = bm.verts.new(p - side * w - Vector((0, 0, 0.08 * w)))
            if prev:
                bm.faces.new((prev[0], a_, b_, prev[1])); bm.faces.new((prev[1], b_, c_, prev[2]))
            prev = (a_, b_, c_)
    for k in range(22):
        frond(k / 14 * 2 * math.pi + random.uniform(-0.1, 0.1), math.radians(random.uniform(25, 65)), random.uniform(3.0, 4.2))
    me = bpy.data.meshes.new('palm_folhas'); bm.to_mesh(me); bm.free(); me.materials.append(PALM_LEAF)
    for p in me.polygons: p.use_smooth = True
    return me
PALM_ME = palm_mesh()
def palm(x, y, h=None, sc=1.0):
    h = h or random.uniform(6, 11)
    tr = obj_from_bm('palm_tronco', tube([Vector((x, y, 0)), Vector((x + 0.2, y, h * 0.5)), Vector((x + 0.3, y + 0.1, h))], [0.25 * sc, 0.22 * sc, 0.2 * sc], 8), PALM_TRUNK)
    o = bpy.data.objects.new('palm', PALM_ME); col.objects.link(o)
    o.location = (x + 0.3, y + 0.1, h); o.scale = (sc, sc, sc); o.rotation_euler = (0, 0, random.uniform(0, 6.28))
    return o

# ================================================================== CENA 2: viagem pelo alto
if SHOT == 2:
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.32
    G = noise_mat('cerrado', 0x1e3014, 0x4a5426, 0.02, 0.9)
    nt = G.node_tree; b = nt.nodes['Principled BSDF']
    n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 0.4; n2.inputs['Detail'].default_value = 12
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 0.7
    nt.links.new(b.inputs['Base Color'].links[0].from_socket, mx.inputs[6]); nt.links.new(n2.outputs['Color'], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6000)
    obj_from_bm('chao', bm, G)
    # rio Tocantins: faixa larga e sinuosa
    RIO, rb = principled('rio', 0x2a3a3e, 0.05, **{'IOR': 1.33})
    bm = bmesh.new(); prev = None
    for i in range(121):
        y = -500 + i * 50
        x = 300 + 140 * math.sin(y / 900) + 60 * math.sin(y / 310)
        w = 420 + 60 * math.sin(y / 500)
        a_ = bm.verts.new((x - w / 2, y, 0.3)); b_ = bm.verts.new((x + w / 2, y, 0.3))
        if prev: bm.faces.new((prev[0], prev[1], b_, a_))
        prev = (a_, b_)
    obj_from_bm('rio', bm, RIO)
    AREIA = mat_color('praia_rio', 0xc9b38a, 0.9)
    for (x, y, sx, sy) in ((560, 900, 90, 260), (240, 2100, 70, 200)):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=8, radius=1)
        o = obj_from_bm('banco_areia', bm, AREIA); o.scale = (sx, sy, 1.2); o.location = (x, y, 0.0)
    # mata de babaçu densa (instâncias leves) e manchas de mata escura
    MATA = noise_mat('mata', 0x1c3012, 0x34501e, 0.05, 0.9)
    for i in range(70):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=8, radius=1)
        o = obj_from_bm('mancha', bm, MATA)
        o.scale = (random.uniform(20, 70), random.uniform(20, 90), random.uniform(5, 9)); o.location = (random.uniform(-500, 60), random.uniform(-100, 1500), 0)
    for i in range(3500):
        x = random.uniform(-260, 70); y = random.uniform(-60, 420)
        o = bpy.data.objects.new('palm', PALM_ME); col.objects.link(o)
        s = random.uniform(1.0, 1.6); o.location = (x, y, random.uniform(7, 12)); o.scale = (s, s, s); o.rotation_euler = (0, 0, random.uniform(0, 6.28))
        if i % 3 == 0:
            obj_from_bm('palm_tronco', tube([Vector((x, y, 0)), Vector((x + 0.3, y, o.location.z))], [0.3, 0.22], 5), PALM_TRUNK)
    # morros ao longe, azulados pela distância
    LONGE = mat_color('longe', 0x7d93a0, 0.9)
    for i in range(14):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=10, radius=1)
        o = obj_from_bm('morro', bm, LONGE); o.scale = (random.uniform(400, 900), random.uniform(200, 400), random.uniform(60, 140))
        o.location = (random.uniform(-2500, 2500), random.uniform(3000, 3600), -20)
    def frame(t):
        pos = Vector((0, 14 * t, 30 - 1.5 * t)) + Vector((1.5 * math.sin(t * 0.8), 0, 0.4 * math.sin(t * 1.6)))
        wing = wings_flap(t, 2.6, 42) if (t % 2.4) < 1.4 else wings_glide(t)
        set_bird(pos, math.radians(90), math.radians(-5), 1.0, 0.0, 0.0, wing, t=t, roll=math.radians(5 * math.sin(t * 0.8)))
        cam.location = pos + Vector((-2.2, -4.2, 2.2))
        cam_d.dof.aperture_fstop = 5.6
        aim_cam(pos + Vector((0.3, 1.5, -0.2)), 26)

# ================================================================== CENA 1: litoral
if SHOT == 1:
    def frame(t):
        x = -5.5 + 3.3 * t
        pos = Vector((x, 6.0, 1.5 + 0.35 * t + 0.1 * math.sin(t * 2)))
        set_bird(pos, math.radians(8), math.radians(-4), 1.0, 0.0, 0.0, wings_flap(t, 3.0, 46), t=t)
        cam.location = Vector((x * 0.75 - 0.6, 1.2, 1.25))
        cam_d.dof.aperture_fstop = 2.8
        aim_cam(pos + Vector((0.1, 0, 0.35)), 42)

# ================================================================== CENA 3: viaduto na BR-010
if SHOT == 3:
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.3
    ASF = noise_mat('asfalto', 0x1e1e1f, 0x38383a, 40, 0.85, 0.15)
    CONC = noise_mat('concreto', 0x6a665f, 0x8a857c, 6, 0.85, 0.2)
    CONC2 = noise_mat('concreto_esc', 0x56524c, 0x777269, 5, 0.9, 0.2)
    TERRA = noise_mat('terra', 0x4e5230, 0x7a5c3a, 0.15, 0.95)
    GRAMA = noise_mat('grama', 0x4a5a26, 0x7a8a3a, 1.2, 0.9)
    BRANCO = mat_color('faixa', 0xe8e8e0, 0.6)
    AMAR = mat_color('faixa_am', 0xe0b020, 0.6)
    METAL = mat_color('metal', 0x7a7c80, 0.35, **{'Metallic': 0.9})
    # chão da cidade
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1500)
    obj_from_bm('chao', bm, TERRA).location.z = -0.05
    # BR-010 duplicada ao longo de X: duas pistas de 7,5 m, canteiro central de 4 m
    for yc in (-5.75, 5.75):
        box('pista', (1400, 7.5, 0.1), (0, yc, 0.0), ASF)
        for yl in (yc - 3.6, yc + 3.6):
            box('borda', (1400, 0.15, 0.02), (0, yl, 0.06), BRANCO)
        for xs in range(-700, 700, 12):
            box('tracejado', (4, 0.15, 0.02), (xs, yc, 0.06), BRANCO)
    box('canteiro', (1400, 4.0, 0.25), (0, 0, 0.1), GRAMA)
    for yc in (-10.2, 10.2):
        box('acostamento', (1400, 1.4, 0.1), (0, yc, 0.0), CONC2)
    # postes no canteiro
    for xs in range(-300, 600, 35):
        obj_from_bm('poste', tube([Vector((xs, 0, 0)), Vector((xs, 0, 10))], [0.12, 0.08], 8), METAL)
        for s_ in (-1, 1):
            obj_from_bm('braco', tube([Vector((xs, 0, 9.8)), Vector((xs, s_ * 2.5, 10.3))], [0.06, 0.05], 6), METAL)
            box('luminaria', (0.7, 0.35, 0.15), (xs, s_ * 2.7, 10.25), METAL)
    # viaduto ao longo de Y em x = 0: tabuleiro a 6,5 m, guarda-corpo New Jersey
    DECK_Z = 6.5
    box('tabuleiro', (12, 60, 1.2), (0, 0, DECK_Z - 0.6), CONC)
    box('pista_viaduto', (11.6, 60, 0.06), (0, 0, DECK_Z + 0.03), ASF)
    for s_ in (-1, 1):
        # guarda-corpo (perfil New Jersey simplificado: base larga, topo estreito)
        box('nj_base', (0.6, 60, 0.35), (s_ * 5.75, 0, DECK_Z + 0.175), CONC)
        box('nj_topo', (0.25, 60, 0.6), (s_ * 5.82, 0, DECK_Z + 0.65), CONC)
    for yp in (-13, 0, 13):
        for xp in (-3.5, 3.5):
            box('pilar', (1.0, 1.4 if yp else 1.0, DECK_Z - 1.2), (xp, yp, (DECK_Z - 1.2) / 2), CONC2)
        box('travessa', (10, 1.6, 0.9), (0, yp, DECK_Z - 1.6), CONC2)
    for s_ in (-1, 1):   # rampas de acesso
        box('rampa', (12, 120, 1.0), (0, s_ * 90, DECK_Z - 0.5 - 2.5), CONC)
        for k in range(3):
            box('pilar_r', (8, 1.0, DECK_Z - 2), (0, s_ * (40 + k * 18), (DECK_Z - 2) / 2), CONC2)
    # placa verde "IMPERATRIZ" sobre a pista
    W, H = 1200, 420
    img = Image.new('RGB', (W, H), (14, 102, 56)); d = ImageDraw.Draw(img)
    d.rectangle((14, 14, W - 15, H - 15), outline=(240, 240, 240), width=10)
    fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 150)
    fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 70)
    d.text((W / 2, 170), 'IMPERATRIZ', font=fb, fill=(245, 245, 245), anchor='mm')
    d.rounded_rectangle((W / 2 - 170, 270, W / 2 + 170, 380), 18, fill=(245, 245, 245))
    d.text((W / 2, 326), 'BR-010', font=fs, fill=(14, 60, 40), anchor='mm')
    pth = os.path.join(HERE, 'placa_imperatriz.png'); img.save(pth)
    PL, plb = principled('placa', 0x106038, 0.5)
    tx = PL.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(pth)
    PL.node_tree.links.new(tx.outputs['Color'], plb.inputs['Base Color'])
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    vs_ = [bm.verts.new(v) for v in ((-3.4, 0, -1.2), (3.4, 0, -1.2), (3.4, 0, 1.2), (-3.4, 0, 1.2))]
    f_ = bm.faces.new(vs_)
    for lp, c in zip(f_.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): lp[uv].uv = c
    placa = obj_from_bm('placa', bm, PL); placa.location = (75, -5.75, 7.6); placa.rotation_euler = (0, 0, math.radians(-90))
    for yy in (-9.6, -1.9):
        obj_from_bm('portico', tube([Vector((75.1, yy, 0)), Vector((75.1, yy, 8.9))], [0.18, 0.15], 8), METAL)
    box('portico_viga', (0.3, 8.0, 0.35), (75.15, -5.75, 8.9), METAL)
    # cidade dos dois lados
    CORES = (0xe6dccb, 0xd8c3a0, 0xbfd3d6, 0xe8b7a0, 0xf0ead8, 0xc9c2b4, 0xd6b38a, 0xa8b8a0)
    def casa_mat(i, c):
        m, b_ = principled('casa%d' % i, c, 0.8); nt_ = m.node_tree
        br = nt_.nodes.new('ShaderNodeTexBrick'); br.offset = 0.0
        br.inputs['Color1'].default_value = srgb(0x2a3038); br.inputs['Color2'].default_value = srgb(0x384048)
        br.inputs['Mortar'].default_value = srgb(c); br.inputs['Scale'].default_value = 1.0
        br.inputs['Mortar Size'].default_value = 0.45; br.inputs['Brick Width'].default_value = 3.0; br.inputs['Row Height'].default_value = 3.0
        tc_ = nt_.nodes.new('ShaderNodeNewGeometry'); sp_ = nt_.nodes.new('ShaderNodeSeparateXYZ'); nt_.links.new(tc_.outputs['Position'], sp_.inputs['Vector'])
        ad_ = nt_.nodes.new('ShaderNodeMath'); nt_.links.new(sp_.outputs['X'], ad_.inputs[0]); nt_.links.new(sp_.outputs['Y'], ad_.inputs[1])
        cb_ = nt_.nodes.new('ShaderNodeCombineXYZ'); nt_.links.new(ad_.outputs[0], cb_.inputs['X']); nt_.links.new(sp_.outputs['Z'], cb_.inputs['Y'])
        nt_.links.new(cb_.outputs['Vector'], br.inputs['Vector'])
        nt_.links.new(br.outputs['Color'], b_.inputs['Base Color'])
        return m
    BMAT = [casa_mat(i, c) for i, c in enumerate(CORES)]
    for side in (-1, 1):
        for i in range(340):
            x = random.uniform(-200, 500); y = side * random.uniform(14, 120)
            if abs(x) < 9 and abs(y) < 60: continue
            h = random.choice((3.5, 4, 6, 7, 9, 12, 18, 25)) * random.uniform(0.9, 1.2)
            box('predio', (random.uniform(6, 16), random.uniform(6, 14), h), (x, y, h / 2), random.choice(BMAT), random.uniform(-0.05, 0.05))
        for i in range(45):
            x = random.uniform(-150, 400); y = side * random.uniform(12.5, 60)
            if abs(x) < 8 and abs(y) < 60: continue
            palm(x, y, sc=random.uniform(0.8, 1.1))
    # trânsito: carros e caminhões andando nos dois sentidos
    CAR_COL = (0xe8e8e8, 0x202224, 0x9a9ea4, 0xa01818, 0xd8d8d0, 0x1a3a6a, 0xc0c4c8, 0x5a5a5a)
    PNEU = mat_color('pneu', 0x111111, 0.9); VIDRO = mat_color('vidro', 0x101418, 0.05, **{'Specular IOR Level': 0.8})
    cars = []
    def make_vehicle(kind):
        par = bpy.data.objects.new('veic', None); col.objects.link(par)
        if kind == 'car':
            m = mat_color('car', random.choice(CAR_COL), 0.25, **{'Coat Weight': 0.8})
            for nm, sz, lc, mt in (('carro', (4.3, 1.8, 0.7), (0, 0, 0.65), m), ('cabine', (2.3, 1.6, 0.55), (-0.2, 0, 1.25), VIDRO)):
                o = box(nm, sz, lc, mt); o.parent = par
            for wx in (-1.35, 1.35):
                for wy in (-0.85, 0.85):
                    o = box('roda', (0.65, 0.25, 0.65), (wx, wy, 0.33), PNEU); o.parent = par
            speed = random.uniform(14, 20)
        else:
            m = mat_color('bau', random.choice((0xe8e8e8, 0xd0d0c8, 0x2a5a9a, 0xc8b070)), 0.5)
            cab = mat_color('cab', random.choice((0xd02020, 0xf0f0f0, 0x204080)), 0.3, **{'Coat Weight': 0.6})
            for nm, sz, lc, mt in (('bau', (10, 2.5, 3.0), (-1.5, 0, 2.2), m), ('cavalo', (2.4, 2.4, 2.6), (5.0, 0, 1.7), cab), ('chassi', (14, 2.0, 0.5), (-0.5, 0, 0.7), PNEU)):
                o = box(nm, sz, lc, mt); o.parent = par
            speed = random.uniform(11, 15)
        return par, speed
    for lane_y, direction in ((-7.6, 1), (-3.9, 1), (3.9, -1), (7.6, -1)):
        x = -400.0
        while x < 600:
            kind = 'truck' if random.random() < 0.25 else 'car'
            par, sp = make_vehicle(kind)
            cars.append((par, x, lane_y, direction, sp * (0.75 if lane_y in (-7.6, 7.6) else 1.0)))
            x += random.uniform(25, 70)
    # carros no viaduto também
    for k in range(4):
        par, sp = make_vehicle('car'); cars.append((par, None, (-2.8 if k % 2 else 2.8), (1 if k % 2 else -1), sp * 0.7, k * 30.0))

    # mouth da notícia (começa aos 3,4 s desta cena)
    SPEAK0 = 3.4
    MF = os.path.join(HERE, os.environ.get('MOUTH', 'mouth_viaduto.json'))
    MOUTH3 = json.load(open(MF)) if os.path.exists(MF) else []
    PERCH = Vector((5.82, 0.6, DECK_Z + 0.95))     # em cima do guarda-corpo
    YAW_P = math.radians(160)
    Q0 = Vector((60, 12, 15)); Q1 = Vector((30, 6, 11)); Q2 = Vector((12, 1.8, 8.4))
    T_LAND3, T_FOLD3 = 2.4, 3.2
    cam.location = Vector((3.55, 0.2, DECK_Z + 1.85))
    sun_d.energy = 3.2; scene.view_settings.exposure = -0.45
    def frame(t):
        mouth = MOUTH3[int(t * FPS)] if int(t * FPS) < len(MOUTH3) else 0.0
        for c in cars:
            par = c[0]
            if c[1] is None:       # no viaduto, ao longo de Y
                _, _, xl, dr, sp, off = c
                y = ((off + sp * t * dr) + 60) % 120 - 60
                par.location = (xl, y, DECK_Z + 0.06); par.rotation_euler = (0, 0, math.radians(90 if dr > 0 else -90))
            else:
                _, x0, ly, dr, sp = c
                par.location = (x0 + dr * sp * t, ly, 0.05); par.rotation_euler = (0, 0, 0 if dr > 0 else math.pi)
        if t < T_LAND3:
            u = 1 - (1 - t / T_LAND3) ** 1.6
            P = lambda u: Q0 * (1 - u) ** 3 + Q1 * 3 * u * (1 - u) ** 2 + Q2 * 3 * u * u * (1 - u) + PERCH * u ** 3
            pos = P(u); vel = P(min(1, u + 0.01)) - P(max(0, u - 0.01))
            yaw = math.atan2(vel.y, vel.x); yaw = lerp(yaw, YAW_P, smooth((t - (T_LAND3 - 0.8)) / 0.8))
        else:
            pos = PERCH.copy(); yaw = YAW_P
        fly = 1 - smooth((t - (T_LAND3 - 0.7)) / 0.6)
        legs_down = smooth((t - (T_LAND3 - 0.8)) / 0.6)
        fold = smooth((t - T_LAND3) / (T_FOLD3 - T_LAND3))
        pitch = 0.0
        if T_LAND3 - 0.8 < t < T_LAND3 + 0.3:
            pitch = -math.radians(30) * math.sin(math.pi * clamp((t - (T_LAND3 - 0.8)) / 1.1, 0, 1))
        if t < 1.2: wing = wings_flap(t, 2.8, 44)
        elif t < 1.6: wing = wings_glide(t)
        else:
            ph = 2 * math.pi * 2.2 * (t - 1.6); a = 1 - fold
            phi = (20 + 42 * math.sin(ph)) * a; wing = (phi, (10, 10), phi + 14 * math.sin(ph - 0.8) * a, 10 + 15 * max(0, math.cos(ph)) * a, 0.0)
        flare = 18 * (1 - fold) if t > 1.6 else 0
        gest = math.sin(math.pi * (t - SPEAK0) / 1.3) if SPEAK0 < t < SPEAK0 + 1.3 else 0.0
        fold_eff = fold * (1 - 0.55 * gest)
        if gest > 0: wing = (35 + 25 * math.sin(2 * math.pi * 2.5 * (t - SPEAK0)), (14, 12), 30, 20, 0.0)
        look = nod = 0.0
        if t > T_FOLD3:
            k = smooth((t - T_FOLD3) / 0.5)
            look = math.radians(22) * k + math.radians(6) * math.sin(t * 1.3)
            nod = math.radians(4) * math.sin(t * 2.0) + mouth * math.radians(5)
        set_bird(pos, yaw, pitch, fly, legs_down, fold_eff, wing, look, nod, mouth, t, flare)
        center = bird.matrix_basis @ Vector((0.05, 0, 0.42))
        cam_d.dof.aperture_fstop = 3.5
        tgt = center.lerp(PERCH + Vector((0, 0, 0.75)), smooth((t - 1.5) / 1.5))
        aim_cam(tgt, lerp(24, 42, smooth((t - 1.4) / 2.2)))

os.makedirs(OUT, exist_ok=True)
for f in range(F0, F1 + 1):
    frame(f / FPS)
    scene.render.filepath = os.path.join(OUT, f'{f:04d}.png')
    bpy.ops.render.render(write_still=True)
    print('QUADRO', f, flush=True)
