const RENDER = location.hash.includes('render');
if (RENDER) document.body.classList.add('render');
const stage = document.getElementById('stage');
const W = RENDER ? 1080 : stage.clientWidth, H = RENDER ? 1920 : stage.clientHeight;

const renderer = new THREE.WebGLRenderer({ antialias:true, preserveDrawingBuffer:true });
renderer.setPixelRatio(RENDER ? 1 : Math.min(2, devicePixelRatio));
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
stage.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, W/H, 0.1, 400);
camera.position.set(0, 3.0, 12.2);
camera.lookAt(0, 2.15, 0);

// ---------- céu de fim de tarde ----------
(function sky(){
  const c = document.createElement('canvas'); c.width = 16; c.height = 512;
  const g = c.getContext('2d'), gr = g.createLinearGradient(0,0,0,512);
  gr.addColorStop(0,'#2a64b0'); gr.addColorStop(0.35,'#6f9fd6'); gr.addColorStop(0.55,'#f7b27a'); gr.addColorStop(0.72,'#ff9a52'); gr.addColorStop(1,'#ffd890');
  g.fillStyle = gr; g.fillRect(0,0,16,512);
  const tex = new THREE.CanvasTexture(c); tex.encoding = THREE.sRGBEncoding;
  const sph = new THREE.Mesh(new THREE.SphereGeometry(200, 32, 32), new THREE.MeshBasicMaterial({ map:tex, side:THREE.BackSide, fog:false }));
  scene.add(sph);
  const sun = new THREE.Mesh(new THREE.CircleGeometry(9, 48), new THREE.MeshBasicMaterial({ color:0xfff1c9, fog:false }));
  sun.position.set(-26, 22, -150); scene.add(sun);
  const glow = new THREE.Mesh(new THREE.CircleGeometry(18, 48), new THREE.MeshBasicMaterial({ color:0xffd79a, transparent:true, opacity:.35, fog:false }));
  glow.position.set(-26, 22, -151); scene.add(glow);
})();
scene.fog = new THREE.Fog(0xf3b98a, 30, 140);

// luzes
scene.add(new THREE.HemisphereLight(0xffe2c4, 0x5a3a2a, 0.75));
const key = new THREE.DirectionalLight(0xfff0dc, 1.35);
key.position.set(-6, 10, 8); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, { left:-6, right:6, top:8, bottom:-4, near:1, far:40 });
key.shadow.bias = -0.0005;
scene.add(key);
const rim = new THREE.DirectionalLight(0xffb07a, 0.9); rim.position.set(5, 5, -8); scene.add(rim);

// ---------- água e mangue ----------
const water = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshStandardMaterial({ color:0x6f8fa0, roughness:0.15, metalness:0.35 }));
water.rotation.x = -Math.PI/2; water.position.y = -0.02; scene.add(water);
const sandMat = new THREE.MeshStandardMaterial({ color:0x8a6a4a, roughness:1 });
const bank = new THREE.Mesh(new THREE.CylinderGeometry(4.2, 4.8, 0.4, 48), sandMat);
bank.scale.z = 0.7; bank.position.set(0, 0.05, 0); bank.receiveShadow = true; scene.add(bank);

const leafMat = new THREE.MeshStandardMaterial({ color:0x2f5a2c, roughness:0.9 });
const leafMat2 = new THREE.MeshStandardMaterial({ color:0x3e6e34, roughness:0.9 });
const rootMat = new THREE.MeshStandardMaterial({ color:0x4a3628, roughness:1 });
function mangrove(x, z, s){
  const g = new THREE.Group();
  for (let i=0;i<7;i++){
    const a = i/7*Math.PI*2 + s;
    const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(Math.cos(a)*1.6, 0, Math.sin(a)*1.6), new THREE.Vector3(Math.cos(a)*1.1, 1.8, Math.sin(a)*1.1), new THREE.Vector3(0, 2.4, 0));
    const m = new THREE.Mesh(new THREE.TubeGeometry(curve, 12, 0.07, 6), rootMat); g.add(m);
  }
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.25, 2.5, 8), rootMat); trunk.position.y = 3.4; g.add(trunk);
  for (let i=0;i<9;i++){
    const r = 1.1 + (i%3)*0.35;
    const b = new THREE.Mesh(new THREE.SphereGeometry(r, 14, 12), i%2 ? leafMat : leafMat2);
    b.position.set(Math.sin(i*2.1+s)*1.6, 4.6 + Math.cos(i*1.3)*0.7, Math.cos(i*2.7+s)*1.2);
    g.add(b);
  }
  g.position.set(x, 0, z); g.scale.setScalar(s*0.35+0.9); scene.add(g);
}
[[-9,-14,1.2],[-15,-22,2.1],[-5,-26,0.7],[7,-16,1.6],[13,-24,2.8],[19,-30,0.4],[-22,-34,3.1],[2,-38,1.9],[26,-40,1.1],[-30,-46,2.2]].forEach(a=>mangrove(...a));

// guarás distantes voando
const flock = [];
const flockMat = new THREE.MeshBasicMaterial({ color:0xd6402c });
for (let i=0;i<6;i++){
  const g = new THREE.Group();
  const b = new THREE.Mesh(new THREE.SphereGeometry(0.18, 8, 6), flockMat); b.scale.set(1,0.6,2); g.add(b);
  const wl = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.22), new THREE.MeshBasicMaterial({ color:0xd6402c, side:THREE.DoubleSide })); wl.geometry.translate(0.45,0,0);
  const wr = wl.clone(); wr.rotation.y = Math.PI;
  g.add(wl); g.add(wr); g.userData = { wl, wr, off:i*1.7, y:9+i%3*1.6, z:-30-i*4 };
  scene.add(g); flock.push(g);
}

