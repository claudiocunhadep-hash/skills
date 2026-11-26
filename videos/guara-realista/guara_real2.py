import random
"""Guará realista em Blender/Cycles.

Uso:  python3 guara_real.py <saida_dir> <frame_ini> <frame_fim> [larg alt amostras]
Gera PNGs numerados. A animação é procedural: o esqueleto do corpo (modificador Skin)
e cada pena são reposicionados a cada quadro.
"""
import bpy, bmesh, math, sys, json, os, random
from mathutils import Vector, Matrix, Quaternion

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
OUT = args[0]
F0, F1 = int(args[1]), int(args[2])
RX = int(args[3]) if len(args) > 3 else 720
RY = int(args[4]) if len(args) > 4 else 1280
SAMPLES = int(args[5]) if len(args) > 5 else 32
FPS = 30
HERE = os.path.dirname(os.path.abspath(__file__))
MOUTH = json.load(open(os.path.join(HERE, 'mouth_real.json'))) if os.path.exists(os.path.join(HERE, 'mouth_real.json')) else []

random.seed(3)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, k): return a + (b - a) * k
def vlerp(a, b, k): return a.lerp(b, k)
def clamp(x, a, b): return max(a, min(b, x))

def srgb(h):
    c = [(h >> 16 & 255) / 255, (h >> 8 & 255) / 255, (h & 255) / 255]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

# ---------------------------------------------------------------- materiais
def principled(name, color, rough=0.5, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(color) if isinstance(color, int) else color
    b.inputs['Roughness'].default_value = rough
    for k, v in kw.items(): b.inputs[k].default_value = v
    return m, b

def plumage_mat(S=16.0):
    """Plumagem em escamas de penas sobrepostas (cada pena aponta para trás/baixo)."""
    m, b = principled('plumagem', 0xd8301a, 0.72, **{'Sheen Weight': 0.12, 'Sheen Roughness': 0.35,
                     'Subsurface Weight': 0.0})
    b.inputs['Sheen Tint'].default_value = srgb(0xff5a50)
    try: b.inputs['Specular IOR Level'].default_value = 0.15
    except Exception: pass
    nt = m.node_tree; N = nt.nodes; L = nt.links
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (S, S * 1.5, S * 1.3)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'F1'; vor.inputs['Randomness'].default_value = 0.7
    L.new(mp.outputs['Vector'], vor.inputs['Vector'])
    ved = N.new('ShaderNodeTexVoronoi'); ved.feature = 'DISTANCE_TO_EDGE'; ved.inputs['Randomness'].default_value = 0.7
    L.new(mp.outputs['Vector'], ved.inputs['Vector'])
    vs = N.new('ShaderNodeVectorMath'); vs.operation = 'SUBTRACT'
    L.new(mp.outputs['Vector'], vs.inputs[0]); L.new(vor.outputs['Position'], vs.inputs[1])
    vd = N.new('ShaderNodeVectorMath'); vd.operation = 'DOT_PRODUCT'; vd.inputs[1].default_value = (-0.85, 0.0, -0.5)
    L.new(vs.outputs['Vector'], vd.inputs[0])
    sh = N.new('ShaderNodeMapRange'); sh.inputs['From Min'].default_value = -0.55; sh.inputs['From Max'].default_value = 0.6
    L.new(vd.outputs['Value'], sh.inputs['Value'])
    ed = N.new('ShaderNodeMapRange'); ed.inputs['From Min'].default_value = 0.0; ed.inputs['From Max'].default_value = 0.3
    L.new(ved.outputs['Distance'], ed.inputs['Value'])
    # barbas finas
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
    wv.inputs['Scale'].default_value = 9.0; wv.inputs['Distortion'].default_value = 6; wv.inputs['Detail'].default_value = 4
    L.new(mp.outputs['Vector'], wv.inputs['Vector'])
    h1 = N.new('ShaderNodeMath'); h1.operation = 'MULTIPLY_ADD'; h1.inputs[1].default_value = 0.7
    L.new(sh.outputs['Result'], h1.inputs[0])
    e3 = N.new('ShaderNodeMath'); e3.operation = 'MULTIPLY'; e3.inputs[1].default_value = 0.3
    L.new(ed.outputs['Result'], e3.inputs[0]); L.new(e3.outputs[0], h1.inputs[2])
    h2 = N.new('ShaderNodeMath'); h2.operation = 'MULTIPLY_ADD'; h2.inputs[1].default_value = 0.0
    L.new(wv.outputs['Fac'], h2.inputs[0]); L.new(h1.outputs[0], h2.inputs[2])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.18; bump.inputs['Distance'].default_value = 0.006
    L.new(h2.outputs[0], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], b.inputs['Normal'])
    # cor: ruído largo + pena a pena + borda mais escura (sombra da pena de cima)
    noi = N.new('ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = 14; noi.inputs['Detail'].default_value = 5
    L.new(tc.outputs['Object'], noi.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = srgb(0xa0081a); ramp.color_ramp.elements[1].color = srgb(0xe2242a)
    L.new(noi.outputs['Fac'], ramp.inputs['Fac'])
    cr = N.new('ShaderNodeMath'); cr.operation = 'MULTIPLY_ADD'; cr.inputs[1].default_value = 0.22; cr.inputs[2].default_value = 0.86
    L.new(vor.outputs['Color'], cr.inputs[0])
    ef = N.new('ShaderNodeMapRange'); ef.inputs['To Min'].default_value = 0.88; ef.inputs['To Max'].default_value = 1.0
    L.new(ed.outputs['Result'], ef.inputs['Value'])
    sf = N.new('ShaderNodeMapRange'); sf.inputs['To Min'].default_value = 0.8; sf.inputs['To Max'].default_value = 1.05
    L.new(sh.outputs['Result'], sf.inputs['Value'])
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(cr.outputs[0], m1.inputs[0]); L.new(ef.outputs['Result'], m1.inputs[1])
    m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(sf.outputs['Result'], m2.inputs[1])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    L.new(ramp.outputs['Color'], mx.inputs[6]); L.new(m2.outputs[0], mx.inputs[7])
    L.new(mx.outputs[2], b.inputs['Base Color'])
    return m

def feather_mat(name, black_tip):
    m, b = principled(name, 0xd8301a, 0.55, **{'Sheen Weight': 0.15, 'Sheen Roughness': 0.3})
    nt = m.node_tree; N = nt.nodes; L = nt.links
    uv = N.new('ShaderNodeUVMap')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(uv.outputs['UV'], sep.inputs['Vector'])
    # barbas da pena: listras diagonais
    wave = N.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'DIAGONAL'
    wave.inputs['Scale'].default_value = 60; wave.inputs['Distortion'].default_value = 2; wave.inputs['Detail'].default_value = 3
    L.new(uv.outputs['UV'], wave.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    if black_tip:
        ramp.color_ramp.elements[0].position = 0.62; ramp.color_ramp.elements[0].color = srgb(0xc01018)
        ramp.color_ramp.elements[1].position = 0.74; ramp.color_ramp.elements[1].color = srgb(0x161212)
    else:
        ramp.color_ramp.elements[0].color = srgb(0xa80a14); ramp.color_ramp.elements[1].color = srgb(0xe01e26)
    L.new(sep.outputs['Y'], ramp.inputs['Fac'])
    # raque (eixo central) mais claro
    rq = N.new('ShaderNodeMath'); rq.operation = 'SUBTRACT'; rq.inputs[1].default_value = 0.5
    L.new(sep.outputs['X'], rq.inputs[0])
    ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L.new(rq.outputs[0], ab.inputs[0])
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.018; L.new(ab.outputs[0], lt.inputs[0])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    L.new(lt.outputs[0], mix.inputs[0]); L.new(ramp.outputs['Color'], mix.inputs[6])
    mix.inputs[7].default_value = srgb(0xc8262a)
    L.new(mix.outputs[2], b.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25; bump.inputs['Distance'].default_value = 0.001
    L.new(wave.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

PLUM = plumage_mat()
PLUM.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.12
FEATH = feather_mat('pena', False)
FEATH_TIP = feather_mat('pena_ponta', True)
for _m in (FEATH, FEATH_TIP): _m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.15
BEAK, _ = principled('bico', 0x24100f, 0.5, **{'Specular IOR Level': 0.2})
FACE, _ = principled('face', 0xa8231c, 0.45)
LEG, _ = principled('perna', 0xc83c48, 0.4, **{'Subsurface Weight': 0.15})
EYE, _ = principled('olho', 0x120a08, 0.05, **{'Coat Weight': 1.0})

# ---------------------------------------------------------------- utilidades de malha
def obj_from_bm(name, bm, mat, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    me.materials.append(mat)
    if parent: o.parent = parent
    return o

def tube(points, radii, sides=14, squash=1.0):
    """Tubo afinado ao longo de pontos (com tampa na ponta)."""
    bm = bmesh.new(); rings = []
    n = len(points)
    for i, p in enumerate(points):
        t = (points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        sx = t.cross(up).normalized(); sy = sx.cross(t).normalized()
        ring = []
        for j in range(sides):
            a = 2 * math.pi * j / sides
            ring.append(bm.verts.new(p + sx * math.cos(a) * radii[i] * squash + sy * math.sin(a) * radii[i]))
        rings.append(ring)
    for i in range(n - 1):
        for j in range(sides):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % sides], rings[i + 1][(j + 1) % sides], rings[i + 1][j]))
    tipv = bm.verts.new(points[-1] + (points[-1] - points[-2]).normalized() * radii[-1])
    for j in range(sides): bm.faces.new((rings[-1][j], rings[-1][(j + 1) % sides], tipv))
    bm.faces.new(list(reversed(rings[0])))
    return bm

def bez(p0, p1, p2, p3, n):
    out = []
    for i in range(n):
        u = i / (n - 1)
        out.append(p0 * (1 - u) ** 3 + p1 * 3 * u * (1 - u) ** 2 + p2 * 3 * u * u * (1 - u) + p3 * u ** 3)
    return out

def feather_mesh(name, L, W, curve=0.08, mat=FEATH, shape='normal'):
    """Pena: ao longo de +X, largura em Y, face para +Z. UV: x atravessa, y ao longo."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new()
    nl, nw = 10, 5
    grid = []
    for i in range(nl + 1):
        u = i / nl
        if shape == 'primary':   # ponta estreita e assimétrica
            w = W * (0.55 + 0.45 * math.sin(math.pi * min(1, u * 1.15)) ** 0.6) * (1 - u ** 3 * 0.75)
        else:
            w = W * (math.sin(math.pi * (0.15 + 0.85 * u)) ** 0.5) * (1 - u ** 4 * 0.6)
        row = []
        for j in range(nw + 1):
            v = j / nw - 0.5
            x = u * L
            y = v * w
            z = -curve * L * u * u + 0.12 * W * (0.25 - v * v)  # curva para baixo e raque elevada
            vt = bm.verts.new((x, y, z))
            row.append((vt, (j / nw, u)))
        grid.append(row)
    for i in range(nl):
        for j in range(nw):
            f = bm.faces.new((grid[i][j][0], grid[i][j + 1][0], grid[i + 1][j + 1][0], grid[i + 1][j][0]))
            for lp, (vt, uvv) in zip(f.loops, (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])):
                lp[uvl].uv = uvv
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    return me

# ---------------------------------------------------------------- guará
bird = bpy.data.objects.new('guara', None); col.objects.link(bird)

# esqueleto do corpo (índices fixos)
BODY_KEYS = ['cauda_ponta', 'cauda', 'anca', 'meio', 'peito', 'pesc0', 'pesc1', 'pesc2', 'pesc3', 'cab_tras', 'cab_frente']
STAND = {
    'cauda_ponta': (-0.215, 0, 0.415), 'cauda': (-0.15, 0, 0.43), 'anca': (-0.075, 0, 0.445), 'meio': (0.0, 0, 0.455),
    'peito': (0.075, 0, 0.47), 'pesc0': (0.115, 0, 0.51), 'pesc1': (0.14, 0, 0.565), 'pesc2': (0.135, 0, 0.62),
    'pesc3': (0.15, 0, 0.665), 'cab_tras': (0.165, 0, 0.695), 'cab_frente': (0.205, 0, 0.7)}
FLY = {
    'cauda_ponta': (-0.23, 0, 0.45), 'cauda': (-0.16, 0, 0.452), 'anca': (-0.08, 0, 0.455), 'meio': (0.0, 0, 0.458),
    'peito': (0.075, 0, 0.462), 'pesc0': (0.125, 0, 0.47), 'pesc1': (0.18, 0, 0.478), 'pesc2': (0.235, 0, 0.484),
    'pesc3': (0.285, 0, 0.49), 'cab_tras': (0.315, 0, 0.494), 'cab_frente': (0.355, 0, 0.496)}
RAD = {'cauda_ponta': 0.012, 'cauda': 0.045, 'anca': 0.078, 'meio': 0.088, 'peito': 0.075, 'pesc0': 0.042,
       'pesc1': 0.024, 'pesc2': 0.021, 'pesc3': 0.021, 'cab_tras': 0.03, 'cab_frente': 0.026}

# corpo: malha "loft" com seções ovais ao longo da coluna (refeita a cada quadro)
PROF = [(0.0, 0.010, 0.006), (0.08, 0.028, 0.014), (0.2, 0.055, 0.05), (0.33, 0.066, 0.07), (0.45, 0.062, 0.07),
        (0.53, 0.045, 0.052), (0.6, 0.026, 0.03), (0.68, 0.0175, 0.02), (0.86, 0.017, 0.019), (0.91, 0.023, 0.026),
        (0.955, 0.024, 0.026), (1.0, 0.013, 0.015)]
NR, NS = 90, 24
def prof(u):
    for (a, w0, h0), (b, w1, h1) in zip(PROF, PROF[1:]):
        if a <= u <= b:
            k = (u - a) / (b - a); return lerp(w0, w1, k), lerp(h0, h1, k)
    return PROF[-1][1], PROF[-1][2]
def spine_curve(keys):
    pts = [Vector(keys[k]) for k in BODY_KEYS]
    dense = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
        for j in range(20):
            t = j / 20
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    dense.append(pts[-1])
    L = [0.0]
    for a, b in zip(dense, dense[1:]): L.append(L[-1] + (b - a).length)
    out = []; j = 0
    for i in range(NR):
        target = L[-1] * i / (NR - 1)
        while j < len(L) - 2 and L[j + 1] < target: j += 1
        k = (target - L[j]) / max(1e-9, L[j + 1] - L[j]); out.append(dense[j].lerp(dense[j + 1], k))
    return out
def loft_coords(keys):
    sp = spine_curve(keys); co = []
    for i, p in enumerate(sp):
        t = (sp[min(i + 1, NR - 1)] - sp[max(i - 1, 0)]).normalized()
        side = Vector((0, 1, 0)); up = side.cross(t).normalized()
        w, h = prof(i / (NR - 1))
        for j in range(NS):
            a = 2 * math.pi * j / NS
            hh = h * (1.12 if math.sin(a) < 0 and i / NR < 0.55 else 1.0)
            co.append(p + side * math.cos(a) * w + up * math.sin(a) * hh)
    co.append(sp[0] + (sp[0] - sp[1]).normalized() * 0.004); co.append(sp[-1] + (sp[-1] - sp[-2]).normalized() * 0.006)
    return co, sp
bm = bmesh.new()
co0, _ = loft_coords(STAND)
vs = [bm.verts.new(c) for c in co0]
for i in range(NR - 1):
    for j in range(NS):
        bm.faces.new((vs[i * NS + j], vs[i * NS + (j + 1) % NS], vs[(i + 1) * NS + (j + 1) % NS], vs[(i + 1) * NS + j]))
for j in range(NS):
    bm.faces.new((vs[(j + 1) % NS], vs[j], vs[NR * NS]))
    bm.faces.new((vs[(NR - 1) * NS + j], vs[(NR - 1) * NS + (j + 1) % NS], vs[NR * NS + 1]))
body = obj_from_bm('corpo', bm, PLUM, bird)
sub = body.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
COVER = plumage_mat(16.0); COVER.name = 'asa_fechada'
_n = COVER.node_tree.nodes; _l = COVER.node_tree.links; _b = _n['Principled BSDF']
_tc = _n.new('ShaderNodeTexCoord'); _sx = _n.new('ShaderNodeSeparateXYZ'); _l.new(_tc.outputs['Object'], _sx.inputs['Vector'])
_mr = _n.new('ShaderNodeMapRange'); _mr.inputs['From Min'].default_value = -0.13; _mr.inputs['From Max'].default_value = -0.16
_l.new(_sx.outputs['X'], _mr.inputs['Value'])
_mx = _n.new('ShaderNodeMix'); _mx.data_type = 'RGBA'; _mx.inputs[7].default_value = srgb(0x151010)
_l.new(_b.inputs['Base Color'].links[0].from_socket, _mx.inputs[6]); _l.new(_mr.outputs['Result'], _mx.inputs[0])
_l.new(_mx.outputs[2], _b.inputs['Base Color'])
wing_cover = []
for s_ in (-1, 1):
    pts = bez(Vector((0.075, s_ * 0.045, 0.486)), Vector((0.0, s_ * 0.07, 0.49)), Vector((-0.12, s_ * 0.06, 0.465)), Vector((-0.225, s_ * 0.022, 0.445)), 30)
    rad = [0.006 + 0.04 * math.sin(math.pi * min(1, (i / 29) * 1.25)) ** 0.7 * (1 - (i / 29) ** 2 * 0.85) for i in range(30)]
    bm = tube(pts, rad, 16, squash=0.42)
    o = obj_from_bm('asa_dobrada', bm, COVER, bird)
    wing_cover.append((o, s_))
    # penas sobrepostas por cima da asa fechada (coberteiras, secundárias, primárias)
    rr = random.Random(11 + s_)
    nP = len(pts)
    def surf(ui, a, lift):
        i = min(nP - 2, max(1, int(ui * (nP - 1))))
        p = pts[i]; tt = (pts[i + 1] - pts[i - 1]).normalized()
        upv = Vector((0, 0, 1)); sx = tt.cross(upv).normalized(); sy = sx.cross(tt).normalized()
        if sx.y * s_ < 0: sx = -sx
        r = rad[i]
        pos = p + sx * math.cos(a) * r * 0.42 + sy * math.sin(a) * r
        nrm = (sx * math.cos(a) / 0.42 + sy * math.sin(a)).normalized()
        return pos + nrm * lift, nrm, tt
    rows = [  # (u0, u1, ângulos, comprimento, largura, material)
        (0.04, 0.42, (0.8, 0.45, 0.1, -0.25), 0.05, 0.036, FEATH, 11),
        (0.30, 0.64, (0.65, 0.25, -0.15, -0.55), 0.08, 0.042, FEATH, 9),
        (0.52, 0.80, (0.5, 0.1, -0.35), 0.11, 0.045, FEATH, 7),
        (0.70, 0.86, (0.3, -0.1), 0.15, 0.034, FEATH_TIP, 5),
    ]
    for ri, (u0, u1, angs, Lf, Wf, mat_, n_) in enumerate(rows):
        for ai, a in enumerate(angs):
            for k in range(n_):
                ui = u0 + (u1 - u0) * (k + 0.5 * (ai % 2)) / n_
                lift = 0.0015 + 0.0012 * (3 - ri) + 0.0008 * a + 0.0008 * (1 - ui)
                pos, nrm, tt = surf(ui, a + rr.uniform(-0.06, 0.06), lift)
                xa = (tt + Vector((0, 0, -0.18 - 0.1 * ri))).normalized()
                xa = (xa - nrm * xa.dot(nrm)).normalized()
                xa = (Matrix.Rotation(rr.uniform(-0.12, 0.12), 3, nrm) @ xa).normalized()
                ya = nrm.cross(xa)
                Mf = Matrix((xa, ya, nrm)).transposed().to_4x4(); Mf.translation = pos
                sc = rr.uniform(0.85, 1.15)
                me = feather_mesh('pc', Lf * sc, Wf * sc, 0.22, mat_, 'primary' if ri == 3 else 'normal')
                fo = bpy.data.objects.new('pena_cob', me); col.objects.link(fo)
                fo.parent = o; fo.matrix_basis = Mf

# pernas (esqueleto com dedos)
def leg_points(side, fly, land):
    s = side
    hip = Vector((0.0, 0.035 * s, 0.31))
    if fly > 0.5 and land < 0.5:   # voando: pernas esticadas para trás
        knee = Vector((-0.1, 0.03 * s, 0.3)); ank = Vector((-0.24, 0.028 * s, 0.33)); toe = Vector((-0.3, 0.025 * s, 0.34))
        return [hip, knee, ank, toe, toe + Vector((-0.02, 0.012 * s, 0)), toe + Vector((-0.02, -0.012 * s, 0))]
    knee = Vector((-0.025, 0.036 * s, 0.19)); ank = Vector((0.0, 0.036 * s, 0.018)); toe = Vector((0.075, 0.04 * s, 0.008))
    return [hip, knee, ank, toe, Vector((0.06, 0.036 * s + 0.03 * s, 0.008)), Vector((0.065, 0.036 * s - 0.028 * s, 0.008)), Vector((-0.03, 0.036 * s, 0.01))]

legs = []
for s in (-1, 1):
    pts = leg_points(s, 0, 0)
    lm = bpy.data.meshes.new('perna')
    lm.from_pydata([tuple(p) for p in pts], [(0, 1), (1, 2), (2, 3), (2, 4), (2, 5), (2, 6)], [])
    lo = bpy.data.objects.new('perna', lm); col.objects.link(lo); lo.parent = bird
    sk = lo.modifiers.new('skin', 'SKIN')
    radii = [0.016, 0.0085, 0.0065, 0.003, 0.003, 0.003, 0.0028]
    for i, r in enumerate(radii): lo.data.skin_vertices[0].data[i].radius = (r, r)
    lo.data.skin_vertices[0].data[0].use_root = True
    ss = lo.modifiers.new('sub', 'SUBSURF'); ss.levels = 1; ss.render_levels = 2
    sk.use_smooth_shade = True
    lm.materials.append(LEG)
    legs.append((lo, s))

def set_leg(lo, s, k_fly):
    """k_fly 0 = em pé, 1 = esticada para trás (voo)."""
    st = leg_points(s, 0, 0); fl = leg_points(s, 1, 0)
    fl = fl + [fl[-1]]
    for i, v in enumerate(lo.data.vertices):
        v.co = vlerp(st[i], fl[min(i, len(fl) - 1)], k_fly)
    lo.data.update()

# cabeça: um "empty" que acompanha o fim do pescoço
head = bpy.data.objects.new('cabeca', None); col.objects.link(head); head.parent = bird
# bico: tubo curvo em duas partes
def beak_part(upper):
    p0 = Vector((0.0, 0, 0.0)); p3 = Vector((0.165, 0, -0.085))
    pts = bez(p0, Vector((0.06, 0, 0.004)), Vector((0.12, 0, -0.025)), p3, 26)
    off = Vector((0, 0, 0.0035 if upper else -0.0035))
    pts = [p + off * (1 - i / 25) for i, p in enumerate(pts)]
    r0 = 0.0135 if upper else 0.011
    radii = [r0 * (1 - 0.82 * (i / 25) ** 0.85) for i in range(26)]
    return tube(pts, radii, 12, squash=0.72)
beak_root = bpy.data.objects.new('bico_raiz', None); col.objects.link(beak_root); beak_root.parent = head
beak_root.location = (0.028, 0, -0.006)
up_b = obj_from_bm('bico_cima', beak_part(True), BEAK, beak_root)
low_pivot = bpy.data.objects.new('bico_baixo_piv', None); col.objects.link(low_pivot); low_pivot.parent = beak_root
low_b = obj_from_bm('bico_baixo', beak_part(False), BEAK, low_pivot)
# pele nua do rosto e olhos
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1.0)
face = obj_from_bm('face', bm, FACE, head); face.scale = (0.03, 0.0215, 0.018); face.location = (0.016, 0, 0.001)
for s in (-1, 1):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=0.0052)
    e = obj_from_bm('olho', bm, EYE, head); e.location = (0.012, 0.0195 * s, 0.006)

# ---------------------------------------------------------------- asas (penas individuais)
FEATHERS = []   # (obj, lado, bone, t_ao_longo, alpha_graus, camada, dobrada_dict)
SH = {s: Vector((0.07, 0.06 * s, 0.49)) for s in (-1, 1)}
BONE_LEN = (0.085, 0.105, 0.085)

def add_feather(s, bone, t, alpha, L, W, layer, tip, fold_x, fold_z, fold_layer, shape='normal', curve=0.08):
    m = feather_mesh('pena', L, W, curve, FEATH_TIP if tip else FEATH, shape)
    o = bpy.data.objects.new('pena', m); col.objects.link(o); o.parent = bird
    FEATHERS.append(dict(o=o, s=s, bone=bone, t=t, a=alpha, layer=layer, fx=fold_x, fz=fold_z, fl=fold_layer, L=L))

for s in (-1, 1):
    # primárias (mão): 10, as 4 de fora com ponta preta
    for i in range(10):
        k = i / 9
        add_feather(s, 2, 0.15 + 0.85 * k, lerp(12, 78, k ** 1.2), lerp(0.16, 0.235, k ** 0.7), lerp(0.034, 0.026, k), 0 + i * 0.12,
                    i >= 6, lerp(-0.01, -0.03, k), lerp(0.462, 0.474, k), 0.0, 'primary', 0.03)
    # secundárias (antebraço): 12
    for i in range(12):
        k = i / 11
        add_feather(s, 1, 1 - k, lerp(-2, 10, 1 - k), 0.15 - 0.01 * k, 0.04, 1.4 + i * 0.03,
                    False, lerp(0.02, 0.055, k), lerp(0.47, 0.485, k), 1.0, 'normal', 0.07)
    # terciárias (úmero)
    for i in range(6):
        k = i / 5
        add_feather(s, 0, 1 - k * 0.9, lerp(-8, -22, k), 0.13 - 0.02 * k, 0.042, 2.2 + i * 0.03,
                    False, lerp(0.06, 0.075, k), lerp(0.485, 0.5, k), 1.6, 'normal', 0.08)
    # coberteiras grandes e pequenas
    for row, (Ls, layer0, fl) in enumerate(((0.075, 3.0, 2.2), (0.045, 4.0, 2.8))):
        for b, nb in ((0, 4), (1, 7), (2, 6)):
            for i in range(nb):
                k = (i + 0.5) / nb
                a = {0: lerp(-15, -5, k), 1: lerp(10, -2, k), 2: lerp(15, 70, k)}[b]
                add_feather(s, b, k, a, Ls * (1.15 if b == 2 else 1.0), 0.03 if row == 0 else 0.025, layer0 + i * 0.02,
                            False, lerp(0.075, 0.035, (b + k) / 3) + 0.01 * row, lerp(0.488, 0.475, (b + k) / 3) + 0.006 * row, fl, 'normal', 0.12)

# cauda
for i in range(10):
    k = i / 9 - 0.5
    m = feather_mesh('cauda', 0.1, 0.032, 0.05, FEATH)
    o = bpy.data.objects.new('cauda', m); col.objects.link(o); o.parent = bird
    rot = Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Rotation(-k * 0.7, 4, 'Z') @ Matrix.Rotation(0.12 + abs(k) * 0.08, 4, 'Y')
    o.matrix_basis = Matrix.Translation((-0.15, k * 0.02, 0.442 + abs(k) * 0.004)) @ rot
    o['tail'] = k

def frame_from(xa, za, pos):
    xa = xa.normalized(); ya = za.cross(xa).normalized(); za = xa.cross(ya)
    M = Matrix((xa, ya, za)).transposed().to_4x4(); M.translation = pos
    return M

def wing_pose(s, phi, psi, hand_phi, hand_psi, flare=0.0):
    """Devolve matrizes de base de cada osso e posições das juntas (espaço do pássaro)."""
    e_out = Vector((0, s, 0)); e_back = Vector((-1, 0, 0)); e_up = Vector((0, 0, 1))
    mats, joints = [], [SH[s].copy()]
    phis = (phi, phi * 0.95, hand_phi); psis = (psi[0], psi[1], hand_psi)
    p = SH[s].copy()
    for b in range(3):
        R = Matrix.Rotation(s * math.radians(phis[b]), 3, 'X') @ Matrix.Rotation(math.radians(flare), 3, 'Y') @ Matrix.Rotation(s * math.radians(psis[b]), 3, 'Z')
        mats.append(R)
        p = p + (R @ e_out) * BONE_LEN[b]
        joints.append(p.copy())
    return mats, joints

def place_feathers(fold, phi, psi, hand_phi, hand_psi, flare=0.0):
    poses = {s: wing_pose(s, phi, psi, hand_phi, hand_psi, flare) for s in (-1, 1)}
    e_out0 = lambda s: Vector((0, s, 0))
    for f in FEATHERS:
        s = f['s']; mats, joints = poses[s]; R = mats[f['bone']]
        a = math.radians(f['a'])
        root = joints[f['bone']].lerp(joints[f['bone'] + 1], f['t'])
        xa = R @ (Vector((-1, 0, 0)) * math.cos(a) + e_out0(s) * math.sin(a))
        za = R @ Vector((0, 0, 1))
        root = root + za * (0.0016 * f['layer'])
        Ms = frame_from(xa, za, root)
        # dobrada: ao longo do flanco, apontando para trás
        xf = Vector((-1, 0, -0.12 - 0.05 * f['fl'] * 0)); zf = Vector((0, s, 0.32))
        rootf = Vector((f['fx'], s * (0.086 + 0.0012 * f['fl'] + 0.0004 * f['layer']), f['fz']))
        Mf = frame_from(xf, zf, rootf)
        if fold <= 0.001: M = Ms
        elif fold >= 0.999: M = Mf
        else:
            q = Ms.to_quaternion().slerp(Mf.to_quaternion(), fold)
            M = q.to_matrix().to_4x4(); M.translation = Ms.translation.lerp(Mf.translation, fold)
        if s < 0:   # espelhar a largura para a face de cima continuar para cima
            M = M @ Matrix.Diagonal((1, -1, 1, 1))
        if True:   # com a asa fechada, a casca lisa toma o lugar das penas
            sc = 1 - smooth((fold - 0.7) / 0.3)
            M = M @ Matrix.Diagonal((max(sc, 1e-3), max(sc, 1e-3), max(sc, 1e-3), 1))
        f['o'].matrix_basis = M

# ---------------------------------------------------------------- cenário: mangue ao amanhecer
world = bpy.data.worlds.new('ceu'); scene.world = world; world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
sky = wn.new('ShaderNodeTexSky')
types = [e.identifier for e in sky.bl_rna.properties['sky_type'].enum_items]
sky.sky_type = 'NISHITA' if 'NISHITA' in types else types[0]
SUN_EL, SUN_AZ = math.radians(14), math.radians(135)
for attr, val in (('sun_elevation', SUN_EL), ('sun_rotation', SUN_AZ), ('altitude', 10), ('air_density', 1.0), ('dust_density', 0.6), ('ozone_density', 1.0)):
    if hasattr(sky, attr): setattr(sky, attr, val)
bg = wn['Background']; bg.inputs['Strength'].default_value = 0.28
wl.new(sky.outputs['Color'], bg.inputs['Color'])

sun_d = bpy.data.lights.new('sol', 'SUN'); sun_d.energy = 4.5; sun_d.angle = math.radians(1.2)
sun_d.color = (1.0, 0.8, 0.62)
sun = bpy.data.objects.new('sol', sun_d); col.objects.link(sun)
sun.rotation_euler = (math.pi / 2 - SUN_EL, 0, SUN_AZ + math.pi / 2)

# água lamacenta e espelhada
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=120)
WATER, wb = principled('agua', 0x24251c, 0.035, **{'IOR': 1.33})
nt = WATER.node_tree
n1 = nt.nodes.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 1.6; n1.inputs['Detail'].default_value = 8
mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 3.5, 1)
tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], n1.inputs['Vector'])
wbump = nt.nodes.new('ShaderNodeBump'); wbump.inputs['Strength'].default_value = 0.12; wbump.inputs['Distance'].default_value = 0.02
nt.links.new(n1.outputs['Fac'], wbump.inputs['Height']); nt.links.new(wbump.outputs['Normal'], wb.inputs['Normal'])
water = obj_from_bm('agua', bm, WATER); water.location.z = 0.03

# lama aparecendo (bancos) e pneumatóforos
MUD, mb = principled('lama', 0x3a2f24, 0.75)
for (x, y, sx, sy) in ((-2.5, 3.5, 3.5, 1.2), (3.5, 6, 4, 1.5), (-0.6, -0.2, 0.9, 0.5)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=12, radius=1)
    o = obj_from_bm('banco', bm, MUD); o.scale = (sx, sy, 0.06); o.location = (x, y, 0.0)
ROOTM, _ = principled('raiz', 0x4a3a2c, 0.8)
for i in range(160):
    x = random.uniform(-3.5, 3.5); y = random.uniform(-0.5, 9)
    if abs(x) < 0.45 and -0.4 < y < 0.5: continue
    h = random.uniform(0.04, 0.16)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.008, radius2=0.004, depth=h)
    o = obj_from_bm('pneumatoforo', bm, ROOTM); o.location = (x, y, h / 2); o.rotation_euler = (random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), 0)

# árvores do mangue (raízes-escora + copa)
LEAF, lb = principled('folha', 0x1f3a18, 0.7, **{'Subsurface Weight': 0.2})
nt = LEAF.node_tree
ln = nt.nodes.new('ShaderNodeTexNoise'); ln.inputs['Scale'].default_value = 3; ln.inputs['Detail'].default_value = 10
lr = nt.nodes.new('ShaderNodeValToRGB'); lr.color_ramp.elements[0].color = srgb(0x10220c); lr.color_ramp.elements[1].color = srgb(0x3f5a26)
nt.links.new(ln.outputs['Fac'], lr.inputs['Fac']); nt.links.new(lr.outputs['Color'], lb.inputs['Base Color'])
tex = bpy.data.textures.new('nuvem', 'CLOUDS'); tex.noise_scale = 0.18

def mangrove(x, y, sc):
    for k in range(9):
        a = k / 9 * 2 * math.pi + random.uniform(-0.3, 0.3)
        r = random.uniform(1.1, 1.8) * sc
        p0 = Vector((x + math.cos(a) * r, y + math.sin(a) * r, 0)); p3 = Vector((x, y, 1.6 * sc))
        pts = bez(p0, p0 + Vector((0, 0, 0.9 * sc)), Vector((x + math.cos(a) * r * 0.4, y + math.sin(a) * r * 0.4, 1.5 * sc)), p3, 10)
        obj_from_bm('raiz', tube(pts, [0.035 * sc] * 10, 7), ROOTM)
    obj_from_bm('tronco', tube([Vector((x, y, 1.4 * sc)), Vector((x + 0.1, y, 3.2 * sc))], [0.09 * sc, 0.07 * sc], 8), ROOTM)
    for k in range(45):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=random.uniform(0.35, 0.7) * sc)
        o = obj_from_bm('copa', bm, LEAF)
        a = random.uniform(0, 2 * math.pi); rr = random.uniform(0, 2.2) * sc
        o.location = (x + math.cos(a) * rr, y + math.sin(a) * rr * 0.7, random.uniform(2.6, 4.8) * sc - rr * 0.25)
        d = o.modifiers.new('d', 'DISPLACE'); d.texture = tex; d.strength = 0.6 * sc
for (x, y, sc) in ((-5, 14, 1.1), (1.5, 17, 1.3), (7, 13, 1.0), (-11, 20, 1.4), (11, 22, 1.5), (-2, 26, 1.6), (16, 28, 1.4), (-17, 27, 1.5), (5, 32, 1.8), (-8, 36, 1.7)):
    mangrove(x * 1.5, y * 1.7, sc * 1.1)
# ---------------------------------------------------------------- câmera
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d); col.objects.link(cam); scene.camera = cam
cam_d.sensor_fit = 'AUTO'; cam_d.sensor_width = 36
cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.2
focus = bpy.data.objects.new('foco', None); col.objects.link(focus); cam_d.dof.focus_object = focus
CAM_POS = Vector((0.35, -4.4, 0.42))
cam.location = CAM_POS

r = scene.render
r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = RX, RY; r.resolution_percentage = 100
r.image_settings.file_format = 'PNG'; r.film_transparent = False
scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = True; scene.cycles.device = 'CPU'
scene.cycles.use_adaptive_sampling = True; scene.cycles.adaptive_threshold = 0.03
scene.cycles.max_bounces = 6; scene.cycles.diffuse_bounces = 3; scene.cycles.glossy_bounces = 3; scene.cycles.transparent_max_bounces = 4
scene.view_settings.view_transform = 'Standard' if 'AgX' in [i.identifier for i in scene.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
scene.view_settings.exposure = -0.2
scene.render.use_motion_blur = False

# ---------------------------------------------------------------- linha do tempo
T_FLY_END, T_LAND, T_FOLD = 3.3, 4.1, 5.0
LAND = Vector((0.0, 0.0, 0.0))
P0 = Vector((3.6, 9.0, 1.7)); P1 = Vector((2.2, 4.5, 1.1)); P2 = Vector((0.7, 1.0, 0.35))
YAW_STAND = math.radians(-128)    # de frente para a câmera, em 3/4

def path(u):
    return bez(P0, P1, P2, LAND, 2)[0] if u <= 0 else (P0 * (1 - u) ** 3 + P1 * 3 * u * (1 - u) ** 2 + P2 * 3 * u * u * (1 - u) + LAND * u ** 3)

def pose(t):
    mouth = MOUTH[int(t * FPS)] if int(t * FPS) < len(MOUTH) else 0.0
    # ---- trajetória
    if t < T_LAND:
        u = 1 - (1 - t / T_LAND) ** 1.7
        pos = path(u); vel = (path(min(1, u + 0.01)) - path(max(0, u - 0.01)))
        yaw = math.atan2(vel.y, vel.x)
        yaw = lerp(yaw, YAW_STAND, smooth((t - (T_LAND - 0.9)) / 0.9))
    else:
        pos = LAND.copy(); yaw = YAW_STAND
    fly = 1 - smooth((t - (T_FLY_END - 0.2)) / 0.6)              # pescoço e pernas
    legs_down = smooth((t - (T_FLY_END - 0.3)) / 0.6)
    pitch = 0.0
    if T_FLY_END - 0.3 < t < T_LAND + 0.4:                      # freada antes do pouso
        pitch = -math.radians(32) * math.sin(math.pi * clamp((t - (T_FLY_END - 0.3)) / (T_LAND + 0.4 - (T_FLY_END - 0.3)), 0, 1))
    bob = 0.0
    # ---- asas
    fold = smooth((t - T_LAND) / (T_FOLD - T_LAND))
    w = 2 * math.pi * 3.1
    if t < 2.0:          # batidas fortes
        ph = w * t; phi = 22 + 48 * math.sin(ph); hphi = phi + 18 * math.sin(ph - 0.9)
        psi = (12 + 18 * max(0, math.cos(ph)), 6 + 22 * max(0, math.cos(ph))); hpsi = 14 + 30 * max(0, math.cos(ph))
        bob = -0.025 * math.sin(ph)
    elif t < 2.8:        # planeio
        k = smooth((t - 2.0) / 0.3); ph = w * t
        phi = lerp(22 + 48 * math.sin(ph), 6, k); hphi = phi - 4 * k; psi = (12, 8); hpsi = 16; bob = 0
    else:                # freada: asas grandes, devagar
        ph = 2 * math.pi * 2.2 * (t - 2.8)
        a = 1 - fold
        phi = (20 + 42 * math.sin(ph)) * a + 0; hphi = phi + 14 * math.sin(ph - 0.8) * a
        psi = (10, 10); hpsi = 10 + 15 * max(0, math.cos(ph)) * a
    flare = 18 * (1 - fold) if t > 2.8 else 0
    # gesto de asas ao começar a falar
    gest = 0.0
    if 5.6 < t < 6.9:
        gest = math.sin(math.pi * (t - 5.6) / 1.3)
    fold_eff = fold * (1 - 0.55 * gest)
    if gest > 0: phi, hphi, psi, hpsi = 35 + 25 * math.sin(2 * math.pi * 2.5 * (t - 5.6)), 30, (14, 12), 20

    bird.location = pos + Vector((0, 0, bob))
    bird.rotation_euler = (0, pitch, yaw)

    # ---- corpo (esqueleto)
    breathe = 0.004 * math.sin(t * 2.4) * (1 - fly)
    keys = {}
    for k in BODY_KEYS:
        p = vlerp(Vector(STAND[k]), Vector(FLY[k]), fly)
        if k.startswith('pesc') or k.startswith('cab'): p.z += breathe * 2
        keys[k] = tuple(p)
    co, sp = loft_coords(keys)
    for v, c in zip(body.data.vertices, co): v.co = c
    body.data.update()
    cov = smooth((fold_eff - 0.55) / 0.4)
    for o, s_ in wing_cover:
        o.scale = (1, max(cov, 1e-3), max(cov, 1e-3)); o.location = (0, 0, 0.0)
    for lo, s in legs: set_leg(lo, s, 1 - legs_down)
    # ---- cabeça
    hb = Vector(keys['cab_tras']); hf = Vector(keys['cab_frente'])
    fwd = (hf - hb).normalized()
    look = 0.0; nod = 0.0
    if t > T_FOLD:
        k = smooth((t - T_FOLD) / 0.5)
        look = math.radians(38) * k + math.radians(6) * math.sin(t * 1.3)   # vira a cabeça para a câmera
        nod = math.radians(4) * math.sin(t * 2.0) + mouth * math.radians(5)
    Rh = Matrix.Rotation(look, 3, 'Z') @ Matrix.Rotation(nod, 3, 'Y')
    xa = Rh @ fwd; za = Rh @ Vector((0, 0, 1))
    head.matrix_basis = frame_from(xa, za, hb.lerp(hf, 0.55))
    low_pivot.rotation_euler = (0, math.radians(14) * mouth, 0)
    # ---- penas
    place_feathers(fold_eff, phi, psi, hphi, hpsi, flare)
    for o in bpy.data.objects:
        if 'tail' in o.keys():
            k = o['tail']; spread = 1 + 0.9 * (1 - fold)
            rot = Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Rotation(-k * 0.7 * spread, 4, 'Z') @ Matrix.Rotation(0.12 + abs(k) * 0.08, 4, 'Y')
            o.matrix_basis = Matrix.Translation((-0.15, k * 0.02, 0.442 + abs(k) * 0.004)) @ rot
    # ---- câmera acompanha
    bird_center = bird.matrix_basis @ Vector((0.05, 0, 0.42))
    focus.location = bird_center
    aim = bird_center.lerp(Vector((0.02, 0, 0.3)), smooth((t - 3.0) / 2.0))
    d = (aim - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam_d.lens = lerp(80, 160, smooth((t - 2.2) / 2.6))

tronco = bpy.data.objects.new('tronco', None); col.objects.link(tronco); tronco.parent = bird; tronco.location = (0, 0, -0.09)
for o in list(bpy.data.objects):
    if o.parent == bird and o is not tronco and o.name.split('.')[0] != 'perna':
        o.parent = tronco
os.makedirs(OUT, exist_ok=True)
for f in range(F0, F1 + 1):
    pose(f / FPS)
    scene.render.filepath = os.path.join(OUT, f'{f:04d}.png')
    bpy.ops.render.render(write_still=True)
    print('QUADRO', f, flush=True)
