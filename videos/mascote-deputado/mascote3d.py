"""Mascote 3D do deputado (estilo animação). Uso: python3 mascote3d.py <saida.png> [larg alt amostras]"""
import bpy, math, sys
from mathutils import Vector

args = sys.argv[1:]
OUT = args[0]
RX = int(args[1]) if len(args) > 1 else 540
RY = int(args[2]) if len(args) > 2 else 960
SAMPLES = int(args[3]) if len(args) > 3 else 48

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

def srgb(h):
    c = [(h >> 16 & 255) / 255, (h >> 8 & 255) / 255, (h & 255) / 255]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

def mat(name, color, rough=0.5, sss=0.0, metal=0.0, bump=0.0, bscale=200.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(color)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (1.0, 0.45, 0.3)
        b.inputs['Subsurface Scale'].default_value = 0.03
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    if bump:
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = bscale
        n.inputs['Detail'].default_value = 4
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = 0.01
        nt.links.new(n.outputs['Fac'], bp.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

SKIN = mat('pele', 0x956449, 0.45, sss=0.25, bump=0.05, bscale=400)
LIP = mat('labio', 0x9a4f45, 0.4, sss=0.2)
HAIR = mat('cabelo', 0x17110d, 0.55, bump=0.35, bscale=60, coat=0.15)
BEARD = mat('barba', 0x40352e, 0.9, bump=0.8, bscale=350)
WHITE = mat('olho', 0xf4efe8, 0.15)
IRIS = mat('iris', 0x2a170b, 0.35)
PUPIL = mat('pupila', 0x050403, 0.05, coat=1.0)
TEETH = mat('dentes', 0xf2ece2, 0.25)
MOUTH = mat('boca', 0x3a1210, 0.6)
POLO = mat('polo', 0x04309c, 0.8, bump=0.25, bscale=500)
POLO_D = mat('polo_borda', 0x032888, 0.8, bump=0.3, bscale=700)
BTN = mat('botao', 0x10203a, 0.3)
JEANS = mat('jeans', 0x7895b8, 0.85, bump=0.2, bscale=350)
SHOE = mat('sapato', 0x2b1d15, 0.35, coat=0.4)
BELT = mat('cinto', 0x3a2618, 0.4)
STEEL = mat('aco', 0xd7dbe0, 0.18, metal=1.0)
DIAL = mat('mostrador', 0x1c3fa6, 0.15, coat=1.0)
WALL = mat('fundo', 0xeee4d8, 0.9)

def obj_sphere(loc, scale, m, r=1.0, sub=2, name='s'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    if sub:
        md = o.modifiers.new('sub', 'SUBSURF'); md.levels = md.render_levels = 1
    return o

def capsule(p1, p2, r, m, r2=None):
    p1, p2 = Vector(p1), Vector(p2); r2 = r if r2 is None else r2
    d = p2 - p1
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=r, radius2=r2, depth=d.length, location=(p1 + p2) / 2)
    o = bpy.context.object; o.data.materials.append(m); bpy.ops.object.shade_smooth()
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    obj_sphere(p1, (r, r, r), m, sub=0); obj_sphere(p2, (r2, r2, r2), m, sub=0)
    return o

def box(loc, size, m, rot=(0, 0, 0), bevel=0.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; o.data.materials.append(m)
    bm = o.modifiers.new('bv', 'BEVEL'); bm.width = bevel; bm.segments = 4
    bpy.ops.object.shade_smooth()
    return o

def torus(loc, R, r, m, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot,
                                     major_segments=64, minor_segments=16)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o

# ------------------------------------------------------------------ cabeça
HZ = 1.60
SMILE = float(__import__('os').environ.get('SMILE', '-60'))
obj_sphere((0, 0, HZ), (0.29, 0.28, 0.34), SKIN, name='cabeca')
obj_sphere((0, -0.04, HZ - 0.13), (0.25, 0.225, 0.2), SKIN, name='bochechas')
for sx in (-1, 1):
    obj_sphere((sx * 0.285, 0.03, HZ - 0.01), (0.03, 0.065, 0.085), SKIN, name='orelha')
# cabelo: volume penteado para trás, com topete e volume na nuca
obj_sphere((0, 0.05, HZ + 0.075), (0.305, 0.30, 0.305), HAIR, name='cabelo')
obj_sphere((0, -0.08, HZ + 0.25), (0.25, 0.19, 0.12), HAIR, name='topete')
obj_sphere((0, 0.13, HZ - 0.12), (0.27, 0.17, 0.22), HAIR, name='nuca')
for sx in (-1, 1):
    obj_sphere((sx * 0.255, 0.06, HZ + 0.06), (0.07, 0.17, 0.14), HAIR, name='lateral')
# barba curta: casca do rosto cortada por um plano inclinado (das orelhas até o bigode)
import bmesh
def beard_shell():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, location=(0, 0, 0))
    o = bpy.context.object; o.name = 'barba'
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.297, v.co.y * 0.287 - 0.022, v.co.z * 0.345 + HZ - 0.03))
    n = Vector((0, -0.62, 1)).normalized(); p0 = Vector((0, -0.26, HZ - 0.13))
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=p0, plane_no=n, clear_outer=True)
    bm.to_mesh(me); bm.free()
    o.data.materials.append(BEARD); bpy.ops.object.shade_smooth()
    sd = o.modifiers.new('sol', 'SOLIDIFY'); sd.thickness = 0.008
    md = o.modifiers.new('sub', 'SUBSURF'); md.levels = md.render_levels = 1
beard_shell()
obj_sphere((0, -0.19, HZ - 0.33), (0.1, 0.07, 0.05), BEARD, name='queixo')
obj_sphere((0, -0.255, HZ - 0.235), (0.1, 0.05, 0.05), BEARD, name='cavanhaque')
for sx in (-1, 1):
    capsule((sx * 0.012, -0.318, HZ - 0.108), (sx * 0.09, -0.292, HZ - 0.14), 0.024, BEARD, 0.02)
    obj_sphere((sx * 0.12, -0.205, HZ - 0.05), (0.058, 0.04, 0.04), SKIN, name='macas')
# boca: sorriso em crescente, curvado acompanhando o rosto
def crescent(name, w, top, bot, y0, z0, depth, m, N=40):
    me = bpy.data.meshes.new(name); verts = []; faces = []
    for i in range(N + 1):
        u = -1 + 2 * i / N; x = u * w; yc = y0 + x * x / 0.5
        zt, zb = z0 + top(u), z0 + bot(u)
        verts += [(x, yc, zt), (x, yc, zb), (x, yc + depth, zt), (x, yc + depth, zb)]
    for i in range(N):
        a, c = 4 * i, 4 * (i + 1)
        faces += [(a, a + 1, c + 1, c), (a + 2, c + 2, c + 3, a + 3), (a, c, c + 2, a + 2), (a + 1, a + 3, c + 3, c + 1)]
    faces += [(0, 2, 3, 1), (4 * N, 4 * N + 1, 4 * N + 3, 4 * N + 2)]
    me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); col.objects.link(o); o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    return o
K, H = 0.022, 0.05
crescent('labio', 0.1, lambda u: K * u * u + 0.006, lambda u: -(H + 0.012) * (1 - u * u) + K * u * u - 0.004, -0.296, HZ - 0.15, 0.02, LIP)
crescent('boca', 0.092, lambda u: K * u * u, lambda u: -H * (1 - u * u) + K * u * u, -0.303, HZ - 0.15, 0.02, MOUTH)
crescent('dentes', 0.084, lambda u: K * u * u - 0.002, lambda u: max(K * u * u - 0.024, -H * (1 - u * u) + K * u * u), -0.305, HZ - 0.15, 0.006, TEETH)
# nariz
obj_sphere((0, -0.3, HZ - 0.04), (0.035, 0.05, 0.075), SKIN, name='nariz')
obj_sphere((0, -0.31, HZ - 0.085), (0.055, 0.045, 0.035), SKIN, name='narinas')
# olhos (sorridentes, levemente apertados)
for sx in (-1, 1):
    x = sx * 0.1
    obj_sphere((x, -0.232, HZ + 0.04), (0.055, 0.037, 0.05), WHITE, name='olho')
    obj_sphere((x, -0.262, HZ + 0.04), (0.031, 0.013, 0.032), IRIS, name='iris')
    obj_sphere((x, -0.273, HZ + 0.04), (0.015, 0.006, 0.015), PUPIL, name='pupila')
    obj_sphere((x + 0.01, -0.278, HZ + 0.05), (0.006, 0.003, 0.006), WHITE, name='brilho')
    o = obj_sphere((x, -0.226, HZ + 0.07), (0.06, 0.04, 0.03), SKIN, name='palpebra')
    o.rotation_euler = (0, -sx * 0.12, 0)
    obj_sphere((x, -0.229, HZ + 0.008), (0.058, 0.038, 0.017), SKIN, name='palpebra_inf')
    b = capsule((sx * 0.045, -0.262, HZ + 0.128), (sx * 0.155, -0.238, HZ + 0.135), 0.016, HAIR, 0.011)

# ------------------------------------------------------------------ corpo
capsule((0, 0.01, 1.20), (0, 0.01, 1.36), 0.10, SKIN)                       # pescoço
torso = obj_sphere((0, 0, 0.93), (0.37, 0.245, 0.38), POLO, name='torso')
obj_sphere((0, 0.0, 1.12), (0.40, 0.22, 0.16), POLO, name='ombros')
torus((0, 0.0, 1.26), 0.125, 0.032, POLO_D, rot=(math.radians(-15), 0, 0))  # gola
for sx in (-1, 1):                                                         # pontas da gola
    box((sx * 0.085, -0.15, 1.225), (0.13, 0.014, 0.09), POLO_D, rot=(math.radians(62), 0, sx * math.radians(38)))
box((0, -0.228, 1.12), (0.05, 0.012, 0.17), POLO_D, rot=(math.radians(-10), 0, 0))   # carcela
for z in (1.17, 1.09):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.006, location=(0, -0.24, z), rotation=(math.radians(80), 0, 0))
    bpy.context.object.data.materials.append(BTN)
# cintura e jeans
obj_sphere((0, 0, 0.62), (0.30, 0.215, 0.16), JEANS, name='quadril')
for sx in (-1, 1):
    capsule((sx * 0.13, 0, 0.58), (sx * 0.135, -0.01, 0.12), 0.115, JEANS, 0.095)
    obj_sphere((sx * 0.14, -0.06, 0.05), (0.09, 0.16, 0.06), SHOE, name='sapato')

# braços: direito (lado esquerdo da tela) acenando, esquerdo apoiado com o relógio
for sx in (-1, 1):
    obj_sphere((sx * 0.37, 0.0, 1.1), (0.12, 0.125, 0.12), POLO, name='manga')
capsule((-0.36, 0, 1.1), (-0.48, -0.015, 1.1), 0.098, POLO, 0.092)
capsule((0.36, 0, 1.1), (0.46, -0.005, 0.98), 0.098, POLO, 0.092)
# acenando
capsule((-0.42, 0, 1.02), (-0.58, -0.04, 1.2), 0.075, SKIN, 0.068)
capsule((-0.58, -0.04, 1.2), (-0.62, -0.08, 1.46), 0.068, SKIN, 0.06)
obj_sphere((-0.63, -0.09, 1.53), (0.065, 0.035, 0.085), SKIN, name='mao_d')
for i, a in enumerate((-0.35, -0.12, 0.1, 0.3)):
    capsule((-0.63 + 0.04 * math.sin(a), -0.09, 1.58), (-0.63 + 0.12 * math.sin(a), -0.095, 1.58 + 0.07 * math.cos(a)), 0.016, SKIN, 0.014)
capsule((-0.60, -0.1, 1.5), (-0.55, -0.13, 1.55), 0.02, SKIN, 0.017)
# apoiado na cintura
capsule((0.43, 0, 1.0), (0.52, -0.02, 0.8), 0.075, SKIN, 0.068)
capsule((0.52, -0.02, 0.8), (0.34, -0.12, 0.72), 0.066, SKIN, 0.058)
obj_sphere((0.3, -0.14, 0.72), (0.06, 0.05, 0.07), SKIN, name='mao_e')
torus((0.385, -0.1, 0.735), 0.063, 0.018, STEEL, rot=(0, math.radians(90), math.radians(-25)))
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.03, location=(0.39, -0.165, 0.74), rotation=(math.radians(80), 0, math.radians(-25)))
bpy.context.object.data.materials.append(DIAL)
torus((0.39, -0.18, 0.74), 0.042, 0.009, STEEL, rot=(math.radians(80), 0, math.radians(-25)))

# ------------------------------------------------------------------ cenário e luz
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 4, 0)); bpy.context.object.data.materials.append(WALL)
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 1.2, 8), rotation=(math.radians(90), 0, 0))
bpy.context.object.data.materials.append(WALL)
world = bpy.data.worlds.new('w'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = srgb(0xf2eadf)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6

def area(loc, energy, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    L = bpy.context.object; L.data.energy = energy; L.data.size = size; L.data.color = color
    d = Vector((0, 0, 1.1)) - Vector(loc)
    L.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
area((-2.2, -3.0, 2.6), 520, 2.5, (1.0, 0.95, 0.88))
area((2.6, -2.5, 1.4), 180, 3.0, (0.9, 0.95, 1.0))
area((1.5, 2.5, 2.8), 260, 1.5)

bpy.ops.object.camera_add(location=(0, -4.6, 1.08))
cam = bpy.context.object; scene.camera = cam; cam.data.lens = 52
cam.rotation_euler = (Vector((0, 0, 0.98)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 4.35; cam.data.dof.aperture_fstop = 4.0

scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = True
scene.render.resolution_x = RX; scene.render.resolution_y = RY
scene.view_settings.view_transform = 'Standard'
scene.view_settings.exposure = -0.65
import os
if os.environ.get('CLOSE'):
    cam.location=(0,-2.2,1.45); cam.data.lens=70; cam.rotation_euler=(Vector((0,0,1.45))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.dof.focus_distance=1.95
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('OK', OUT)
