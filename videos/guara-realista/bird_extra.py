# Ajustes do guará executados logo depois de montar cada pássaro (vale para o macho e para a fêmea).
# 1) asa fechada: origem no centro da própria asa, para ela encolher no lugar (antes encolhia em direção aos pés)
# 2) olhos expressivos: globo claro, íris e pupila que olham em volta, pálpebras que piscam e "regalam"
for _o, _s in wing_cover:
    _vs = _o.data.vertices
    _c = sum((v.co for v in _vs), Vector()) / len(_vs)
    for v in _vs: v.co -= _c
    _o.data.update()
    _o.location = _o.location + _c
    for _ch in [c for c in bpy.data.objects if c.parent == _o]:
        _ch.matrix_parent_inverse = Matrix.Translation(-_c) @ _ch.matrix_parent_inverse

tronco = bpy.data.objects.new('tronco', None); col.objects.link(tronco); tronco.parent = bird; tronco.location = (0, 0, -0.09)
for o in list(bpy.data.objects):
    if o.parent == bird and o is not tronco and o.name.split('.')[0] != 'perna':
        o.parent = tronco

SCLERA, _ = principled('olho_claro', 0xf3ede0, 0.4, **{'Coat Weight': 0.25})
IRIS_M, _ = principled('iris', 0x3a1f0e, 0.3, **{'Coat Weight': 0.5})
PUPIL_M, _ = principled('pupila', 0x030202, 0.05, **{'Coat Weight': 1.0})

def _sphere(name, r, mat, parent, keep=None):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=r)
    if keep:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if keep * v.co.z < -1e-6], context='VERTS')
    o = obj_from_bm(name, bm, mat, parent)
    for p in o.data.polygons: p.use_smooth = True
    return o

for _o in [c for c in bpy.data.objects if c.parent == head and c.name.split('.')[0] == 'olho']:
    _o.hide_render = True; _o.hide_viewport = True
EYES = []
for s in (-1, 1):
    piv = bpy.data.objects.new('olho_piv', None); col.objects.link(piv); piv.parent = head
    piv.location = (0.012, 0.0155 * s, 0.0075)
    _E = float(os.environ.get('EYE_SCALE', '1.6')); piv.scale = (_E, _E, _E)
    ball = _sphere('olho_globo', 0.0068, SCLERA, piv)
    gaze = bpy.data.objects.new('olhar', None); col.objects.link(gaze); gaze.parent = piv
    iris = _sphere('iris', 1.0, IRIS_M, gaze); iris.scale = (0.0048, 0.0014, 0.0048); iris.location = (0.0008, 0.0058 * s, 0)
    pup = _sphere('pupila', 1.0, PUPIL_M, gaze); pup.scale = (0.0024, 0.0008, 0.0024); pup.location = (0.0009, 0.0064 * s, 0)
    lid_u = bpy.data.objects.new('palp_cima', None); col.objects.link(lid_u); lid_u.parent = piv
    _sphere('palpebra', 0.0084, FACE, lid_u, keep=1)
    lid_l = bpy.data.objects.new('palp_baixo', None); col.objects.link(lid_l); lid_l.parent = piv
    _sphere('palpebra', 0.0082, FACE, lid_l, keep=-1)
    EYES.append((s, piv, ball, gaze, lid_u, lid_l))

def set_eyes(openness=1.0, gaze_yaw=0.0, gaze_pitch=0.0):
    """openness: 0 fechado (piscada), 1 normal, 1.3+ arregalado. Olhar em radianos."""
    for s, piv, ball, gaze, lid_u, lid_l in EYES:
        o = max(0.0, openness)
        lid_u.rotation_euler = (math.radians(s * (-90 + 105 * min(o, 1.0) + 45 * max(0.0, o - 1.0))), 0, 0)
        lid_l.rotation_euler = (math.radians(-s * (30 + 30 * max(0.0, o - 1.0))), 0, 0)
        k = 1.0 + 0.18 * max(0.0, o - 1.0)
        ball.scale = (k, k, k); gaze.scale = (k, k, k)
        gaze.rotation_euler = (0, gaze_pitch, -s * (math.radians(30) + gaze_yaw))
