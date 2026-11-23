import * as THREE from 'three';
const W = 270, H = 480, OW = 1080, OH = 1920;
const TL = await (await fetch('timeline.json')).json();
await Promise.all([document.fonts.load('46px SilkB'), document.fonts.load('30px Silk'), document.fonts.load('40px PS2')]);

const glc = document.createElement('canvas'); glc.width = W; glc.height = H;
const renderer = new THREE.WebGLRenderer({ canvas: glc, antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false); renderer.localClippingEnabled = true;
const out = document.getElementById('out'); const ctx = out.getContext('2d');
const tmp = document.createElement('canvas'); const tctx = tmp.getContext('2d');
const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 2000);

// ---------- utils ----------
const PI = Math.PI, DS = THREE.DoubleSide;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const ease = t => { t = clamp(t); return t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; };
const eout = t => { t = clamp(t); return 1 - Math.pow(1 - t, 3); };
const sstep = (a, b, x) => ease((x - a) / (b - a));
const hash = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const mod = (a, n) => ((a % n) + n) % n;
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const lin = v => Math.pow(v, 2.2);

const mc = {};
function M(c, o) { if (!o) return mc[c] ??= new THREE.MeshLambertMaterial({ color: c, flatShading: true }); return new THREE.MeshLambertMaterial({ color: c, flatShading: true, ...o }); }
function add(par, geo, mat, p, r) { const m = new THREE.Mesh(geo, typeof mat === 'number' ? M(mat) : mat); if (p) m.position.set(p[0], p[1], p[2]); if (r) m.rotation.set(r[0], r[1], r[2]); par.add(m); return m; }
const BOX = (w, h, d) => new THREE.BoxGeometry(w, h, d);
const CYX = (r, l, s = 10, r2) => { const g = new THREE.CylinderGeometry(r2 ?? r, r, l, s); g.rotateZ(-PI / 2); return g; };
const CYY = (r, h, s = 12, r2) => new THREE.CylinderGeometry(r2 ?? r, r, h, s);
function canvasTex(w, h, draw, rep = [1, 1]) { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); draw(g, w, h); const t = new THREE.CanvasTexture(c); t.magFilter = t.minFilter = THREE.NearestFilter; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep[0], rep[1]); t.colorSpace = THREE.SRGBColorSpace; t.generateMipmaps = false; return t; }
function makePoints(n, color, size = 1, o = {}) { const g = new THREE.BufferGeometry(); const a = new Float32Array(n * 3); g.setAttribute('position', new THREE.BufferAttribute(a, 3)); const m = new THREE.PointsMaterial({ color, size, sizeAttenuation: false, ...o }); const p = new THREE.Points(g, m); p.frustumCulled = false; p.userData.a = a; return p; }
function setPts(p, fn) { const a = p.userData.a, n = a.length / 3; let c = 0; for (let i = 0; i < n; i++) { const v = fn(i); if (v) { a[c * 3] = v[0]; a[c * 3 + 1] = v[1]; a[c * 3 + 2] = v[2]; c++; } } p.geometry.setDrawRange(0, c); p.geometry.attributes.position.needsUpdate = true; }
function lights(s, sky = 0xffffff, gnd = 0x334455, hi = 1.1, di = 2.2, amb = 0.5, dp = [30, 50, 40]) { s.add(new THREE.HemisphereLight(sky, gnd, hi)); const d = new THREE.DirectionalLight(0xffffff, di); d.position.set(...dp); s.add(d); s.add(new THREE.AmbientLight(0xffffff, amb)); }

const tileTex = canvasTex(8, 8, g => { g.fillStyle = '#2b3846'; g.fillRect(0, 0, 8, 8); g.fillStyle = '#212c38'; g.fillRect(0, 0, 8, 1); g.fillRect(0, 0, 1, 8); g.fillStyle = '#334252'; g.fillRect(3, 3, 2, 1); }, [10, 42]);
const gridTex = canvasTex(8, 8, g => { g.fillStyle = '#4a525c'; g.fillRect(0, 0, 8, 8); g.fillStyle = '#6d7782'; g.fillRect(0, 0, 8, 2); g.fillRect(0, 0, 2, 8); g.fillRect(4, 0, 1, 8); g.fillRect(0, 4, 8, 1); }, [160, 22]);
const hazTex = canvasTex(8, 8, g => { g.fillStyle = '#1a1a1a'; g.fillRect(0, 0, 8, 8); g.fillStyle = '#f2c230'; for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) if (((x + y) % 8) < 4) g.fillRect(x, y, 1, 1); }, [6, 1]);
function stripeTex(base, hi) { return canvasTex(16, 8, g => { g.fillStyle = base; g.fillRect(0, 0, 16, 8); g.fillStyle = hi; for (let y = 0; y < 8; y++) { const dx = Math.round(3 - Math.abs(y - 3.5)); g.fillRect(4 + dx, y, 3, 1); } }); }

const pipes = [];
function pipe(par, pts, r, base, hi, speed = 1.6) {
  const path = new THREE.CurvePath();
  for (let i = 0; i < pts.length - 1; i++) path.add(new THREE.LineCurve3(V(...pts[i]), V(...pts[i + 1])));
  const len = path.getLength();
  const geo = new THREE.TubeGeometry(path, Math.max(8, Math.round(len * 5)), r, 6, false);
  const tex = stripeTex(base, hi); tex.repeat.set(Math.max(1, Math.round(len / 0.7)), 1);
  const m = add(par, geo, new THREE.MeshLambertMaterial({ map: tex }));
  m.userData = { tex, speed, len, rep: Math.round(len / 0.7) }; pipes.push(m);
  // elbows
  for (let i = 1; i < pts.length - 1; i++) add(par, new THREE.SphereGeometry(r * 1.05, 6, 4), new THREE.MeshLambertMaterial({ color: base }), pts[i]);
  return m;
}

// ---------- overlays ----------
let LBL = [], HUD = [];
function label(pos, text, o = {}) { LBL.push({ pos, text, ...o }); }
function shadowText(s, x, y, font, color, align = 'left', sh = 4) { ctx.font = font; ctx.textAlign = align; ctx.textBaseline = 'alphabetic'; ctx.fillStyle = 'rgba(0,0,0,0.85)'; ctx.fillText(s, x + sh, y + sh); ctx.fillStyle = color; ctx.fillText(s, x, y); }
function pline(x1, y1, x2, y2, col, w) { ctx.strokeStyle = col; ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(Math.round(x1), Math.round(y1)); ctx.lineTo(Math.round(x2), Math.round(y2)); ctx.stroke(); }
function proj(p) { const v = p.clone().project(camera); return { x: (v.x + 1) / 2 * OW, y: (1 - v.y) / 2 * OH, ok: v.z < 1 && v.z > -1 }; }
function drawLabels() {
  for (const l of LBL) {
    const a = l.a ?? 1; if (a <= 0.01) continue; const P = proj(l.pos); if (!P.ok) continue;
    ctx.globalAlpha = a; const dx = l.dx ?? 80, dy = l.dy ?? -80; const lx = P.x + dx, ly = P.y + dy;
    const font = `${l.size ?? 30}px Silk`; ctx.font = font; const tw = ctx.measureText(l.text).width;
    const ex = dx >= 0 ? lx + tw + 16 : lx - tw - 16; const col = l.color ?? '#ffffff';
    pline(P.x, P.y, lx, ly, 'rgba(0,0,0,0.7)', 7); pline(lx, ly, ex, ly, 'rgba(0,0,0,0.7)', 7);
    pline(P.x, P.y, lx, ly, col, 3); pline(lx, ly, ex, ly, col, 3);
    ctx.fillStyle = '#000'; ctx.fillRect(P.x - 7, P.y - 7, 14, 14); ctx.fillStyle = col; ctx.fillRect(P.x - 5, P.y - 5, 10, 10);
    const n = l.chars ?? l.text.length; shadowText(l.text.slice(0, n), dx >= 0 ? lx + 8 : ex + 8, ly - 10, font, col);
  }
  ctx.globalAlpha = 1;
}
function L_(pos, text, t0, lt, o = {}) { if (lt < t0) return; const a = sstep(t0, t0 + 0.25, lt) * (o.t1 ? 1 - sstep(o.t1, o.t1 + 0.3, lt) : 1); label(pos, text, { a, chars: Math.floor((lt - t0) * 30), ...o }); }
function hudDepth(m) { HUD.push(() => { shadowText('DEPTH', 70, 1300, '28px Silk', '#bfe6ee'); shadowText(Math.round(m) + ' M', 70, 1372, '72px SilkB', '#ffffff'); }); }
function hudCounter(title, val, col = '#ffffff', x = 70, y = 1300) { HUD.push(() => { shadowText(title, x, y, '28px Silk', '#bfe6ee'); shadowText(val, x, y + 72, '72px SilkB', col); }); }
function hudBig(text, col, y = 960, size = 96, a = 1) { HUD.push(() => { ctx.globalAlpha = a; shadowText(text, OW / 2, y, `${size}px SilkB`, col, 'center', 6); ctx.globalAlpha = 1; }); }
function hudArrow(x1, y1, x2, y2, col) { HUD.push(() => { const ang = Math.atan2(y2 - y1, x2 - x1); for (const [c, w] of [['rgba(0,0,0,.6)', 14], [col, 8]]) { pline(x1, y1, x2, y2, c, w); ctx.fillStyle = c; ctx.beginPath(); const s = w * 2.6; ctx.moveTo(x2 + Math.cos(ang) * s * .6, y2 + Math.sin(ang) * s * .6); ctx.lineTo(x2 + Math.cos(ang + 2.4) * s, y2 + Math.sin(ang + 2.4) * s); ctx.lineTo(x2 + Math.cos(ang - 2.4) * s, y2 + Math.sin(ang - 2.4) * s); ctx.fill(); } }); }

// captions
const capFont = '46px SilkB', CAPW = 960, LH = 64;
ctx.font = capFont; const SPW = ctx.measureText(' ').width;
for (const s of TL.segs) {
  const toks = []; let hl = false;
  for (const raw of s.text.split(' ')) { let w = raw, h = hl, end = false; if (w.startsWith('*')) { h = true; w = w.slice(1); } if (w.includes('*')) { end = true; w = w.replace('*', ''); } toks.push({ w: w.toUpperCase(), h }); hl = h && !end; }
  const total = toks.reduce((a, t) => a + t.w.length + 1, 0); let acc = 0;
  for (const t of toks) { t.time = s.start + (acc / total) * (s.speechEnd - s.start) * 0.97; acc += t.w.length + 1; t.wd = ctx.measureText(t.w).width; }
  const lines = []; let cur = [], cw = 0;
  for (const t of toks) { const nw = cw + (cur.length ? SPW : 0) + t.wd; if (nw > CAPW && cur.length) { lines.push(cur); cur = [t]; cw = t.wd; } else { cur.push(t); cw = nw; } }
  if (cur.length) lines.push(cur);
  const pages = []; for (let i = 0; i < lines.length; i += 3) pages.push(lines.slice(i, i + 3));
  s.pages = pages;
}
function drawCaption(t) {
  const s = TL.segs.find(s => t >= s.start - 0.05 && t < s.end); if (!s) return;
  const vis = t < s.speechEnd + 1.6 ? 1 : 1 - clamp((t - s.speechEnd - 1.6) / 0.3); if (vis <= 0) return;
  let page = s.pages[0]; for (const p of s.pages) if (p[0][0].time <= t) page = p;
  ctx.globalAlpha = vis; ctx.font = capFont; ctx.textAlign = 'left';
  const y0 = 300 - (page.length - 1) * LH / 2;
  page.forEach((line, li) => {
    const lw = line.reduce((a, t) => a + t.wd, 0) + SPW * (line.length - 1); let x = (OW - lw) / 2; const y = y0 + li * LH;
    for (const tk of line) { if (tk.time <= t) { ctx.fillStyle = 'rgba(0,0,0,0.9)'; ctx.fillText(tk.w, x + 5, y + 5); ctx.fillStyle = tk.h ? '#ffb43a' : '#ffffff'; ctx.fillText(tk.w, x, y); } x += tk.wd + SPW; }
  });
  ctx.globalAlpha = 1;
}

// camera helpers
function cam(p, t, fov = 50) { camera.position.copy(p); camera.lookAt(t); if (camera.fov !== fov) { camera.fov = fov; camera.updateProjectionMatrix(); } }
function kf(lt, keys) { // keys: [time, [px,py,pz],[tx,ty,tz], fov]
  if (lt <= keys[0][0]) return keys[0]; for (let i = 0; i < keys.length - 1; i++) { const a = keys[i], b = keys[i + 1]; if (lt <= b[0]) { const e = ease((lt - a[0]) / (b[0] - a[0])); return [lt, a[1].map((v, j) => lerp(v, b[1][j], e)), a[2].map((v, j) => lerp(v, b[2][j], e)), lerp(a[3] ?? 50, b[3] ?? 50, e)]; } }
  return keys[keys.length - 1];
}
function camKF(lt, keys, sc = 1) { const k = kf(lt, keys); const tg = V(...k[2]); const p = V(...k[1]).sub(tg).multiplyScalar(sc).add(tg); cam(p, tg, k[3] ?? 50); }

// ---------- submarine ----------
function makeSub(o = {}) {
  const g = new THREE.Group(); const pts = [];
  for (let i = 0; i <= 44; i++) { const y = -21 + i * 42 / 44; let r; if (y > 14) { const u = (y - 14) / 7; r = 2 * Math.sqrt(Math.max(0, 1 - u * u)); } else if (y < -9) { const u = (-9 - y) / 12; r = 0.3 + 1.7 * (1 - Math.pow(u, 1.8)); } else r = 2; pts.push(new THREE.Vector2(Math.max(r, 0.02), y)); }
  const lg = new THREE.LatheGeometry(pts, 16); lg.rotateZ(-PI / 2);
  const hullMat = o.ghost ? new THREE.MeshLambertMaterial({ color: 0x3b5a78, emissive: 0x0d2030, transparent: true, opacity: 0.55, depthWrite: false, side: DS, flatShading: true })
    : new THREE.MeshLambertMaterial({ map: tileTex, color: 0xffffff, transparent: true, opacity: 1, flatShading: true });
  const hull = add(g, lg, hullMat); g.userData.hull = hull; g.userData.hullMat = hullMat;
  const sg = CYY(1, 3.4, 12); sg.scale(2.1, 1, 0.5); add(g, sg, hullMat, [7, 3.3, 0]);
  const finMat = o.ghost ? hullMat : M(0x1c2530);
  g.userData.sailPlanes = add(g, BOX(1.4, 0.12, 4.4), finMat, [7.6, 4.0, 0]);
  g.userData.sternPlanes = add(g, BOX(2.0, 0.12, 6), finMat, [-17.6, 0, 0]);
  add(g, BOX(2.0, 6, 0.12), finMat, [-17.8, 0, 0]);
  const prop = new THREE.Group(); prop.position.set(-21.3, 0, 0); g.add(prop); g.userData.prop = prop;
  const brass = M(0xd4a52c);
  const hg = new THREE.ConeGeometry(0.35, 0.9, 8); hg.rotateZ(PI / 2); add(prop, hg, brass, [-0.3, 0, 0]);
  for (let k = 0; k < 7; k++) { const b = new THREE.Group(); b.rotation.x = k * 2 * PI / 7; prop.add(b); add(b, BOX(0.12, 1.4, 0.55), brass, [0, 0.85, 0], [0, 0.6, 0.15]); }
  return g;
}
function addTanks(sub) {
  const shell = new THREE.MeshLambertMaterial({ color: 0xe6f2f6, transparent: true, opacity: 0.3, depthWrite: false, side: DS });
  const plane = new THREE.Plane(V(0, -1, 0), 0);
  const water = new THREE.MeshLambertMaterial({ color: 0x2f86e0, transparent: true, opacity: 0.9, clippingPlanes: [plane], side: DS, flatShading: true });
  const tanks = [];
  for (const [cx, len] of [[13.2, 5], [-9.5, 5]]) {
    add(sub, CYX(1.75, len, 14), shell, [cx, 0, 0]);
    const w = add(sub, CYX(1.68, len - 0.1, 14), water, [cx, 0, 0]); w.renderOrder = 2;
    add(sub, BOX(0.5, 0.4, 0.5), M(0x9aa6b0), [cx, 1.95, 0]);
    tanks.push({ cx, len });
  }
  sub.userData.tanks = tanks; sub.userData.plane = plane;
  sub.userData.setFill = (f) => { sub.updateMatrixWorld(); const wp = sub.localToWorld(V(0, 0, 0)); plane.constant = wp.y - 1.75 + f * 3.5; };
}

// ---------- SURFACE scene ----------
const SF = (() => {
  const s = new THREE.Scene();
  s.background = canvasTex(1, 48, g => { const gr = g.createLinearGradient(0, 0, 0, 48); gr.addColorStop(0, '#2557a0'); gr.addColorStop(.55, '#5f9fd8'); gr.addColorStop(1, '#c4e6f7'); g.fillStyle = gr; g.fillRect(0, 0, 1, 48); });
  s.fog = new THREE.Fog(0xb8def2, 90, 330);
  lights(s, 0xe8f6ff, 0x1a4a66, 1.2, 2.4, 0.35, [60, 80, 40]);
  const og = new THREE.PlaneGeometry(440, 440, 88, 88); og.rotateX(-PI / 2);
  const col = new Float32Array(og.attributes.position.count * 3); og.setAttribute('color', new THREE.BufferAttribute(col, 3));
  add(s, og, new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true }));
  const base = og.attributes.position.array.slice();
  const r = rng(7); const cm = new THREE.MeshLambertMaterial({ color: 0xffffff, emissive: 0x7d8ea0, fog: false, flatShading: true });
  for (let k = 0; k < 18; k++) { const cx = -300 + r() * 600, cy = 45 + r() * 50, cz = -150 - r() * 140; const n = 5 + Math.floor(r() * 8); for (let j = 0; j < n; j++) add(s, BOX(6 + r() * 14, 3 + r() * 6, 6 + r() * 10), cm, [cx + (r() - .5) * 30, cy + (r() - .3) * 6, cz + (r() - .5) * 10]); }
  add(s, new THREE.CircleGeometry(10, 10), new THREE.MeshBasicMaterial({ color: 0xfff6dc, fog: false }), [120, 130, -310]).lookAt(0, 0, 0);
  const sub = makeSub(); s.add(sub);
  const wake = makePoints(1600, 0xeef9ff, 1); s.add(wake);
  const spray = makePoints(500, 0xffffff, 2); s.add(spray);
  const wave = (x, z, t) => 0.55 * Math.sin(0.13 * x + 1.0 * t) + 0.4 * Math.sin(0.19 * z - 0.8 * t + 0.04 * x) + 0.22 * Math.sin(0.37 * (x + z) + 1.6 * t) + 0.12 * Math.sin(0.8 * x - 0.5 * z + 2.3 * t);
  const cA = [lin(0.06), lin(0.24), lin(0.42)], cB = [lin(0.42), lin(0.74), lin(0.9)];
  function update(t, subXf, subY, pitch, wakeOn = 1) {
    const p = og.attributes.position.array;
    for (let i = 0; i < p.length; i += 3) { const h = wave(base[i], base[i + 2], t); p[i + 1] = h; const c = Math.pow(clamp((h + 1.0) / 2.2), 1.5); col[i] = lerp(cA[0], cB[0], c); col[i + 1] = lerp(cA[1], cB[1], c); col[i + 2] = lerp(cA[2], cB[2], c); }
    og.attributes.position.needsUpdate = true; og.attributes.color.needsUpdate = true;
    const sx = subXf(t); sub.position.set(sx, subY + 0.12 * Math.sin(t * 0.9), 0); sub.rotation.z = pitch + 0.015 * Math.sin(t * 0.7); sub.rotation.x = 0.02 * Math.sin(t * 0.5);
    sub.userData.prop.rotation.x = t * 4;
    const N = 1600, P = 7;
    setPts(wake, i => {
      if (!wakeOn) return null; const age = mod(t + i * P / N, P); const bx = subXf(t - age); const kind = i % 4; const sd = hash(i) - 0.5;
      let x, z;
      if (kind < 2) { x = bx - 19 - age * 1.2 + sd * 2; z = (kind ? 1 : -1) * (0.6 + age * (1.3 + hash(i + 7) * 0.8)) + sd; }
      else if (kind === 2) { x = bx - 20 - age * 1.0; z = sd * (1 + age * 0.9); }
      else { if (age > 2.5) return null; x = bx + 13 + sd * 10 - age * 1.5; z = (hash(i + 3) > .5 ? 1 : -1) * (2.0 + age * 1.6); }
      if (age > P * (0.55 + 0.45 * hash(i + 11))) return null;
      return [x, wave(x, z, t) + 0.12, z];
    });
    return sx;
  }
  function burst(t0, t, origin) {
    setPts(spray, i => { const age = t - t0 - hash(i + 5) * 0.4; if (age < 0 || age > 2.2) return null; const a = hash(i) * 2 * PI, sp = 2 + hash(i + 1) * 6; const vx = (hash(i + 2) - 0.5) * 10; return [origin.x + vx * age + (hash(i + 9) - .5) * 8, origin.y + (4 + hash(i + 3) * 7) * age - 4.9 * age * age, origin.z + Math.sin(a) * sp * age]; });
  }
  return { s, sub, wave, update, burst, spray, wake };
})();

// ---------- UNDERWATER scene ----------
const UW = (() => {
  const s = new THREE.Scene(); const bg = new THREE.Color(0x1d6f80); s.background = bg; s.fog = new THREE.FogExp2(0x1d6f80, 0.02);
  lights(s, 0xa8e8ff, 0x0a1a22, 1.5, 1.4, 0.45, [10, 80, 30]);
  const ctex = canvasTex(32, 32, g => { g.fillStyle = '#86d6dc'; g.fillRect(0, 0, 32, 32); const r = rng(3); g.fillStyle = '#4fa9ba'; for (let i = 0; i < 18; i++) { const x = r() * 32, y = r() * 32, w = 3 + r() * 6; g.fillRect(Math.floor(x), Math.floor(y), Math.floor(w), Math.floor(w * .6)); } g.fillStyle = '#c9f2f2'; for (let i = 0; i < 10; i++) g.fillRect(Math.floor(r() * 32), Math.floor(r() * 32), 2, 1); }, [60, 60]);
  const sg = new THREE.PlaneGeometry(800, 800); sg.rotateX(PI / 2);
  const surf = add(s, sg, new THREE.MeshBasicMaterial({ map: ctex, side: DS }), [0, 0, 0]);
  const rays = new THREE.Group(); s.add(rays); const rr = rng(11);
  const rayMat = new THREE.MeshBasicMaterial({ color: 0xd6fbff, transparent: true, opacity: 0.07, blending: THREE.AdditiveBlending, depthWrite: false, side: DS });
  for (let i = 0; i < 26; i++) { const m = add(rays, new THREE.PlaneGeometry(2 + rr() * 5, 90), rayMat, [-150 + rr() * 300, -45, -70 + rr() * 80], [0, rr() * PI, 0.25 + rr() * 0.1]); }
  const snow = makePoints(2200, 0xa6dbe2, 1); s.add(snow); const sb = []; const r2 = rng(5); for (let i = 0; i < 2200; i++) sb.push([r2() * 90, r2() * 70, r2() * 90]);
  const subA = makeSub(); s.add(subA);
  const subG = makeSub({ ghost: true }); addTanks(subG); s.add(subG);
  // reactor glow inside subA
  const rg = new THREE.Group(); subA.add(rg); rg.position.set(-3, 0, 0);
  const rgm = new THREE.MeshLambertMaterial({ color: 0xff8a2a, emissive: 0xff6a10, emissiveIntensity: 1 });
  add(rg, CYY(1.1, 2.4, 10), rgm); add(rg, CYY(0.6, 2.8, 8), new THREE.MeshBasicMaterial({ color: 0xffd27a }));
  const rgl = new THREE.PointLight(0xff8a30, 0, 30, 1.5); rg.add(rgl);
  // pressure arrows
  const arrows = new THREE.Group(); s.add(arrows); const arM = new THREE.MeshBasicMaterial({ color: 0xffcf4a });
  const arDirs = []; for (let i = 0; i < 5; i++) for (let k = 0; k < 4; k++) { const ang = k * PI / 2 + PI / 4; const d = V(0, Math.sin(ang), Math.cos(ang)); const cg = new THREE.ConeGeometry(0.45, 1.3, 5); const m = add(arrows, cg, arM); m.quaternion.setFromUnitVectors(V(0, 1, 0), d.clone().negate()); arDirs.push({ m, x: -10 + i * 5, d }); }
  // pump jet shroud
  const shroud = add(subA, new THREE.CylinderGeometry(1.75, 1.6, 2.0, 16, 1, true), new THREE.MeshLambertMaterial({ color: 0x27323d, side: DS, flatShading: true }), [-21.2, 0, 0], [0, 0, PI / 2]);
  shroud.visible = false;
  const thrown = makePoints(900, 0xdff8ff, 1); s.add(thrown);
  const bubbles = makePoints(700, 0xe9fbff, 1); s.add(bubbles);
  const bubbles2 = makePoints(500, 0x9fd6ff, 1); s.add(bubbles2);
  // ship
  const ship = new THREE.Group(); s.add(ship); const shm = M(0x223040);
  add(ship, BOX(18, 3, 4), shm, [0, -1, 0]); add(ship, BOX(6, 3, 3), shm, [-2, 1.5, 0]); add(ship, BOX(1, 1.2, 1.4), shm, [-8.6, -2, 0]);
  const shipProp = add(ship, BOX(0.2, 1.6, 0.2), M(0x8a7a4a), [-9.4, -2, 0]);
  // whale
  const whale = new THREE.Group(); s.add(whale); const wm = M(0x4b6478);
  const wb = new THREE.SphereGeometry(1, 10, 6); wb.scale(5, 1.3, 1.5); add(whale, wb, wm);
  const tail = new THREE.Group(); tail.position.set(-5, 0, 0); whale.add(tail); add(tail, BOX(2.2, 0.15, 3), wm, [-1, 0, 0]);
  add(whale, BOX(1.4, 0.12, 0.6), wm, [1.5, -0.8, 1.4], [0.4, 0, 0]); add(whale, BOX(1.4, 0.12, 0.6), wm, [1.5, -0.8, -1.4], [-0.4, 0, 0]);
  const rings = []; const ringMat = new THREE.MeshBasicMaterial({ color: 0x9ff3ff, transparent: true, opacity: 0.6, side: DS, depthWrite: false });
  for (let i = 0; i < 12; i++) { const m = add(s, new THREE.RingGeometry(0.93, 1, 32), ringMat.clone()); rings.push(m); }
  function setDepth(camY, dens = 1) { const d = clamp(-camY / 95); const c = new THREE.Color(0x2f93a3).lerp(new THREE.Color(0x061219), d); bg.copy(c); s.fog.color.copy(c); s.fog.density = lerp(0.016, 0.026, d) * dens; }
  function update(t, o = {}) {
    // snow drifting; wrap around camera
    const cp = camera.position, dx = (o.flow ?? 0.6) * t;
    setPts(snow, i => { const b = sb[i]; return [cp.x - 45 + mod(b[0] - dx - cp.x, 90), cp.y - 35 + mod(b[1] - 0.15 * t - cp.y, 70), cp.z - 45 + mod(b[2] - cp.z, 90)]; });
    rays.children.forEach((m, i) => { m.material.opacity = 0.07; m.rotation.z = 0.28 + 0.04 * Math.sin(t * 0.5 + i); });
    ctex.offset.set(t * 0.01, t * 0.006);
    for (const k of ['subA', 'subG', 'ship', 'whale', 'arrows', 'thrown', 'bubbles', 'bubbles2']) API[k].visible = !!o[k];
    rings.forEach(r => r.visible = false); shroud.visible = !!o.shroud; rgl.intensity = 0; rg.visible = false;
  }
  const API = { s, setDepth, update, subA, subG, ship, whale, arrows, arDirs, thrown, bubbles, bubbles2, rings, shroud, rg, rgl, rgm, tail, shipProp, surf, rays };
  return API;
})();

// ---------- INTERIOR ----------
const IN = (() => {
  const s = new THREE.Scene(); s.background = new THREE.Color(0x0a121a);
  lights(s, 0xffffff, 0x3a4656, 1.0, 2.0, 0.75, [20, 40, 45]);
  const HY = 3.5, HR = 7; // hull axis y, radius
  const X0 = -47, X1 = 35, HL = X1 - X0, XC = (X0 + X1) / 2;
  const hg = new THREE.CylinderGeometry(HR + 0.1, HR + 0.1, HL, 28, 1, true, 20 * PI / 180, 260 * PI / 180); hg.rotateZ(-PI / 2);
  add(s, hg, M(0x5c6672, { side: DS }), [XC, HY, 0]);
  const og2 = new THREE.CylinderGeometry(HR + 0.6, HR + 0.6, HL, 28, 1, true, 20 * PI / 180, 260 * PI / 180); og2.rotateZ(-PI / 2);
  add(s, og2, M(0x1d2733, { side: THREE.FrontSide }), [XC, HY, 0]);
  for (let x = X0 + 1; x < X1; x += 2.2) { const tg = new THREE.TorusGeometry(HR, 0.16, 3, 20, 260 * PI / 180); tg.rotateY(PI / 2); tg.rotateX(200 * PI / 180); add(s, tg, 0x3d4652, [x, HY, 0]); }
  // cut edge rims (front lips) : thin boxes along length at the two cut lines
  for (const phi of [200, 460]) { const a = phi * PI / 180; add(s, BOX(HL, 0.7, 0.7), 0x26303b, [XC, HY + Math.sin(a) * (HR + 0.3), -Math.cos(a) * (HR + 0.3)]); }
  const floor = add(s, BOX(HL, 0.25, 12), new THREE.MeshLambertMaterial({ map: gridTex }), [XC, 0, 0]);
  gridTex.repeat.set(HL * 2, 24);
  // bulkheads
  for (const bx of [X0 + 0.2, -33, -10, 9, X1 - 0.2]) {
    const cg = new THREE.CircleGeometry(HR, 24, 200 * PI / 180, 260 * PI / 180); cg.rotateY(PI / 2);
    const m = add(s, cg, M(0x47505c, { side: DS }), [bx, HY, 0]);
    if (bx > X0 + 1 && bx < X1 - 1) { add(s, BOX(0.5, 2.4, 1.4), 0x1a2028, [bx, 1.3, -1.5]); add(s, BOX(0.55, 0.35, 5), new THREE.MeshLambertMaterial({ map: hazTex }), [bx, 0.3, 2.5]); }
  }
  // ceiling pipes & cable trays (decorative)
  pipe(s, [[X0, 9.1, -3.6], [X1, 9.1, -3.6]], 0.16, '#b8322a', '#d4554a', 0);
  pipe(s, [[X0, 8.6, -4.4], [X1, 8.6, -4.4]], 0.16, '#3f8f6f', '#57ab88', 0);
  pipe(s, [[X0, 9.6, -2.6], [X1, 9.6, -2.6]], 0.13, '#d9dde0', '#ffffff', 0);
  add(s, BOX(HL, 0.12, 1.2), 0x2c333c, [XC, 10.1, -1.2]);
  // wall panels with green screens
  const screenM = new THREE.MeshLambertMaterial({ color: 0x3ad07a, emissive: 0x1c8a4a, emissiveIntensity: 0.9 });
  const panel = (x, w = 2.2) => { add(s, BOX(w, 1.8, 0.4), 0x3a6655, [x, 3.2, -5.2]); add(s, BOX(w * 0.7, 0.6, 0.1), screenM, [x, 3.5, -4.97]); add(s, BOX(w * 0.3, 0.2, 0.1), M(0xd24c3c), [x - w * 0.25, 2.7, -4.97]); add(s, BOX(w * 0.3, 0.2, 0.1), M(0xf2c230), [x + w * 0.2, 2.7, -4.97]); };
  [-44, -41.5, -30, -24, -19, -13, 11.5, 20, 25.5, 30].forEach(x => panel(x));

  // ===== REACTOR (x=0) =====
  const R = {};
  add(s, BOX(4.4, 0.4, 4.4), 0x3a4048, [0, 0.3, 0]);
  add(s, new THREE.CylinderGeometry(1.6, 1.6, 5, 16, 1, true, PI / 4, PI * 1.5), M(0xd8691e, { side: DS }), [0, 3, 0]);
  add(s, new THREE.CylinderGeometry(1.5, 1.5, 4.9, 16, 1, true, PI / 4, PI * 1.5), M(0x2f5fd0, { side: DS }), [0, 3, 0]);
  add(s, new THREE.SphereGeometry(1.6, 16, 6, 0, 2 * PI, PI / 2, PI / 2), 0xd8691e, [0, 0.5, 0]);
  add(s, new THREE.SphereGeometry(1.62, 16, 5, 0, 2 * PI, 0, PI / 2), 0xc85a18, [0, 5.5, 0]);
  add(s, BOX(3.8, 0.3, 0.3), 0xb8501a, [0, 5.5, 0]);
  R.fuelMat = new THREE.MeshLambertMaterial({ color: 0xff8a2a, emissive: 0xff5000, emissiveIntensity: 1 });
  for (let i = 0; i < 5; i++) for (let j = 0; j < 5; j++) { if ((i === 0 || i === 4) && (j === 0 || j === 4)) continue; add(s, BOX(0.17, 2.8, 0.17), R.fuelMat, [-0.76 + i * 0.38, 2.6, -0.76 + j * 0.38]); }
  R.rods = new THREE.Group(); s.add(R.rods);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) add(R.rods, BOX(0.11, 3.0, 0.11), 0x9aa4ae, [-0.57 + i * 0.38, 0, -0.57 + j * 0.38]);
  add(R.rods, BOX(1.4, 0.12, 1.4), 0x7c8690, [0, 1.5, 0]);
  for (let i = 0; i < 4; i++) { const a = i * PI / 2 + PI / 4; add(R.rods, CYY(0.09, 3.6, 6), 0xb7c0c8, [Math.cos(a) * 0.55, 3.2, Math.sin(a) * 0.55]); }
  for (let i = 0; i < 5; i++) add(s, CYY(0.16, 2.0, 6), 0x8a949e, [-0.8 + i * 0.4, 7.4, -0.3]);
  add(s, BOX(2.4, 0.4, 0.8), 0x6a737c, [0, 8.5, -0.3]);
  R.light = new THREE.PointLight(0xff7a20, 30, 14, 1.6); R.light.position.set(0, 2.6, 1.8); s.add(R.light);
  R.glow = makePoints(90, 0xb8f6ff, 1); s.add(R.glow);
  R.setPower = (p, t, ins) => { R.fuelMat.emissiveIntensity = 0.15 + 1.2 * p; R.light.intensity = 4 + 45 * p; R.rods.position.y = 2.6 + 3.0 * (1 - ins); setPts(R.glow, i => { if (hash(i * 3.1) > p) return null; const f = Math.floor(t * 14) + i * 17; return [-0.8 + hash(f) * 1.6, 1.3 + hash(f + 1) * 2.6, -0.8 + hash(f + 2) * 1.6]; }); };
  // pressurizer
  add(s, CYY(0.8, 3.6, 12), 0xe8dcc0, [-3.4, 2.6, -0.6]); add(s, new THREE.SphereGeometry(0.8, 12, 5, 0, 2 * PI, 0, PI / 2), 0xe8dcc0, [-3.4, 4.4, -0.6]); add(s, new THREE.SphereGeometry(0.8, 12, 5, 0, 2 * PI, PI / 2, PI / 2), 0xe8dcc0, [-3.4, 0.8, -0.6]);
  add(s, BOX(1.7, 0.18, 1.7), 0x8a949e, [-3.4, 3.0, -0.6]);
  pipe(s, [[-3.4, 0.3, -0.6], [-3.4, 0.3, -2.4], [3.4, 0.3, -2.4], [3.4, 0.3, 0], [3.4, 0.9, 0]], 0.14, '#d8691e', '#ffa45a', 0.8);
  // primary loop
  R.hot = pipe(s, [[1.5, 3.8, 0], [3.4, 3.8, 0], [3.4, 0.9, 0], [4.6, 0.9, 0]], 0.3, '#e0601a', '#ffb060', 2.2);
  R.cold = pipe(s, [[6.4, 0.9, 0], [7.2, 0.9, 0], [7.2, 0.9, -2.0], [0, 0.9, -2.0], [0, 0.9, -1.5]], 0.3, '#2f62c8', '#7fb0ff', 2.2);
  add(s, CYX(0.6, 1.2, 10), 0x3f8f6f, [3.6, 0.9, -2.0]); add(s, BOX(0.8, 0.9, 0.9), 0x2f6f55, [3.6, 1.7, -2.0]);
  // shield wall
  const shield = add(s, BOX(0.9, 7.2, 10), new THREE.MeshLambertMaterial({ color: 0x7c8590, transparent: true, opacity: 0.55, flatShading: true }), [9, 3.6, 0]);
  add(s, BOX(1.0, 0.6, 10), new THREE.MeshLambertMaterial({ map: hazTex }), [9, 7.4, 0]);
  // ===== STEAM GENERATOR (x=5.5) =====
  const SG = {}; const sgx = 5.5;
  add(s, new THREE.CylinderGeometry(1.25, 1.25, 5.6, 16, 1, true, PI / 4, PI * 1.5), M(0xcfd8de, { side: DS }), [sgx, 4.0, 0]);
  add(s, new THREE.SphereGeometry(1.25, 14, 5, 0, 2 * PI, PI / 2, PI / 2), 0xd8691e, [sgx, 1.2, 0]);
  add(s, new THREE.SphereGeometry(1.3, 14, 5, 0, 2 * PI, 0, PI / 2), 0xcfd8de, [sgx, 6.8, 0]);
  add(s, new THREE.CylinderGeometry(1.15, 1.15, 3.8, 16, 1, true, PI / 4, PI * 1.5), new THREE.MeshLambertMaterial({ color: 0x3d7fe0, transparent: true, opacity: 0.55, side: DS }), [sgx, 3.1, 0]);
  add(s, BOX(2.2, 0.15, 2.2), 0x8a949e, [sgx, 1.25, 0]);
  for (let k = 0; k < 4; k++) { const w = 0.25 + k * 0.2, top = 4.0 + k * 0.4; const c = new THREE.CurvePath(); c.add(new THREE.LineCurve3(V(sgx - w, 1.3, 0.2), V(sgx - w, top, 0.2))); c.add(new THREE.QuadraticBezierCurve3(V(sgx - w, top, 0.2), V(sgx, top + w * 1.4, 0.2), V(sgx + w, top, 0.2))); c.add(new THREE.LineCurve3(V(sgx + w, top, 0.2), V(sgx + w, 1.3, 0.2)));
    add(s, new THREE.TubeGeometry(c, 30, 0.07, 4, false), M(k % 2 ? 0xff8a2a : 0xe86a1e)); }
  SG.bub = makePoints(260, 0xffffff, 1); s.add(SG.bub);
  SG.steam = makePoints(200, 0xf2f6f8, 2); s.add(SG.steam);
  // steam line to turbine
  SG.steamLine = pipe(s, [[sgx, 8.0, 0], [sgx, 8.4, 0], [16, 8.4, 0], [16, 6.1, 0]], 0.26, '#d0d6dc', '#ffffff', 3.5);
  pipe(s, [[16, 8.4, 0], [22, 8.4, 0], [22, 2.9, 0]], 0.18, '#d0d6dc', '#ffffff', 3.5);
  // ===== MAIN TURBINE (x=16) =====
  const TB = {};
  add(s, new THREE.CylinderGeometry(1.55, 1.55, 5.4, 16, 1, true, PI / 2, PI), M(0x8c96a2, { side: DS }), [16, 4.6, 0], [0, 0, PI / 2]);
  add(s, BOX(1, 1.4, 1.2), 0x8c96a2, [16, 5.9, 0]);
  TB.rotor = new THREE.Group(); TB.rotor.position.set(16, 4.6, 0); s.add(TB.rotor);
  add(TB.rotor, CYX(0.3, 5.6, 8), 0xb0b8c0);
  const bladeM = M(0xd9dee3), bladeM2 = M(0xa6b0ba);
  for (let d = 0; d < 7; d++) { const x = -2.2 + d * 0.72, r = 0.35 + d * 0.07; add(TB.rotor, CYX(0.42, 0.2, 10), 0x7c8690, [x, 0, 0]); for (let b = 0; b < 14; b++) { const a = b * 2 * PI / 14; add(TB.rotor, BOX(0.1, r, 0.3), b % 2 ? bladeM : bladeM2, [x, Math.cos(a) * (0.42 + r / 2), Math.sin(a) * (0.42 + r / 2)], [a, 0.4, 0]); } }
  TB.steam = makePoints(240, 0xffffff, 1); s.add(TB.steam);
  // turbine -> gear shaft
  TB.shaft1 = add(s, CYX(0.18, 9.2, 8), 0xb0b8c0, [23.3, 4.6, 0]);
  // exhaust duct to condenser
  add(s, BOX(3.2, 0.7, 1.8), 0x6f7984, [16, 2.95, 0]);
  // ===== CONDENSER =====
  const CD = {};
  const cdm = M(0x76808b, { side: DS });
  add(s, BOX(5.2, 2.4, 0.15), cdm, [16, 1.45, -1.4]); add(s, BOX(5.2, 0.15, 2.8), cdm, [16, 0.3, 0]); add(s, BOX(0.15, 2.4, 2.8), cdm, [13.45, 1.45, 0]); add(s, BOX(0.15, 2.4, 2.8), cdm, [18.55, 1.45, 0]);
  add(s, BOX(5.2, 0.15, 2.8), new THREE.MeshLambertMaterial({ color: 0x76808b, transparent: true, opacity: 0.35 }), [16, 2.6, 0]);
  CD.tubeTex = stripeTex('#2fa8c8', '#7fe0f5'); CD.tubeTex.repeat.set(8, 1);
  const tubeM = new THREE.MeshLambertMaterial({ map: CD.tubeTex });
  for (let i = 0; i < 3; i++) for (let j = 0; j < 5; j++) add(s, CYX(0.12, 5.0, 6), tubeM, [16, 1.0 + i * 0.45, -1.0 + j * 0.5]);
  add(s, BOX(5.0, 0.35, 2.6), new THREE.MeshLambertMaterial({ color: 0x2f62c8, transparent: true, opacity: 0.85 }), [16, 0.55, 0]);
  CD.steam = makePoints(260, 0xffffff, 1); s.add(CD.steam); CD.drops = makePoints(120, 0x7fb0ff, 1); s.add(CD.drops);
  pipe(s, [[15, 1.4, -6.5], [15, 1.4, -1.5]], 0.25, '#2bb3a3', '#7ff0dd', 2);
  pipe(s, [[17.2, 1.0, -1.5], [17.2, 1.0, -6.5]], 0.25, '#2bb3a3', '#7ff0dd', 2);
  CD.feed = pipe(s, [[13.4, 0.75, 0.8], [7.6, 0.75, 0.8], [7.6, 4.2, 0.8], [6.7, 4.2, 0.3]], 0.2, '#2f62c8', '#7fb0ff', 2);
  add(s, CYX(0.4, 0.9, 10), 0x3f8f6f, [10.5, 0.75, 0.8]);
  // ===== TURBINE GENERATOR (x=22..25) =====
  const TG = {};
  add(s, CYX(0.8, 2.2, 12), 0x9aa4ae, [22, 2.1, 0]);
  TG.rotor = add(s, CYX(0.2, 6.2, 6), 0xb0b8c0, [23.8, 2.1, 0]);
  TG.gen = add(s, CYX(1.05, 2.2, 12), 0x3f8f6f, [24.6, 2.1, 0]);
  add(s, CYX(1.1, 0.25, 12), 0xc2783a, [23.4, 2.1, 0]); add(s, CYX(1.1, 0.25, 12), 0xc2783a, [25.8, 2.1, 0]);
  add(s, BOX(4.6, 0.5, 2.4), 0x3a4048, [23.4, 0.45, 0]);
  TG.cable = pipe(s, [[25.9, 3.1, 0], [26.6, 3.1, 0], [26.6, 9.9, -1.6], [-30, 9.9, -1.6], [-30, 7.0, -1.6]], 0.13, '#e0b020', '#fff07a', -3);
  // ===== GEARS (x=28) =====
  const GR = {};
  function gearGeo(r, teeth, th, depth) { const sh = new THREE.Shape(); const n = teeth * 4; for (let i = 0; i <= n; i++) { const a = i / n * 2 * PI; const rr = (i % 4 < 2) ? r + th : r; const x = Math.cos(a) * rr, y = Math.sin(a) * rr; i ? sh.lineTo(x, y) : sh.moveTo(x, y); } const g = new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: false, curveSegments: 1 }); g.translate(0, 0, -depth / 2); g.rotateY(PI / 2); return g; }
  GR.pinion = add(s, gearGeo(0.55, 10, 0.16, 0.7), 0xe0b34a, [28, 4.6, 0]);
  GR.bull = add(s, gearGeo(1.9, 36, 0.16, 0.6), 0xc99a35, [28, 1.95 + 0.05, 0]);
  for (let k = 0; k < 4; k++) add(GR.bull, BOX(0.65, 0.3, 3.2), 0xa77e28, [0, 0, 0], [k * PI / 4, 0, 0]);
  add(s, BOX(1.2, 0.5, 4.2), 0x3a4048, [28, 0.3, 0]);
  GR.shaft = new THREE.Group(); GR.shaft.position.set(28, 2.0, 0); s.add(GR.shaft);
  add(GR.shaft, CYX(0.28, 16, 8), 0xb8c0c8, [8, 0, 0]);
  for (let k = 0; k < 6; k++) add(GR.shaft, BOX(0.3, 0.12, 0.62), 0xe0b34a, [1.5 + k * 1.2, 0, 0], [k * 0.5, 0, 0]);
  add(s, BOX(1.4, 1.6, 1.6), 0x56606c, [31, 1.6, 0]);
  add(s, CYX(0.6, 0.5, 12), 0x2b3440, [34.6, 2.0, 0]);
  // ===== LIFE SUPPORT (x -31..-12) =====
  const LF = {};
  // distiller
  add(s, CYY(0.8, 3.2, 12), 0xaab4be, [-28, 2.0, 0]); add(s, new THREE.SphereGeometry(0.8, 12, 4, 0, 2 * PI, 0, PI / 2), 0xaab4be, [-28, 3.6, 0]);
  LF.heat = add(s, BOX(1.2, 0.4, 1.2), new THREE.MeshLambertMaterial({ color: 0xff7a2a, emissive: 0xff4a00, emissiveIntensity: 0.8 }), [-28, 0.4, 0]);
  pipe(s, [[-28, 4.4, 0], [-28, 4.9, 0], [-25.6, 4.9, 0], [-25.6, 3.6, 0]], 0.13, '#e8eef2', '#ffffff', 1.5);
  add(s, CYX(0.35, 1.6, 8), 0x7fc8e8, [-25.6, 3.4, 0]);
  add(s, BOX(1.8, 1.5, 1.4), new THREE.MeshLambertMaterial({ color: 0x9fd8f0, transparent: true, opacity: 0.4, side: DS }), [-25.6, 0.9, 0]);
  LF.fresh = add(s, BOX(1.7, 1.0, 1.3), new THREE.MeshLambertMaterial({ color: 0x3d8fe8, transparent: true, opacity: 0.9 }), [-25.6, 0.7, 0]);
  pipe(s, [[-28.5, 1.0, -5.5], [-28.5, 1.0, -0.6]], 0.14, '#2bb3a3', '#7ff0dd', 1.2);
  LF.vapor = makePoints(120, 0xffffff, 1); s.add(LF.vapor); LF.drip = makePoints(30, 0x7fd0ff, 1); s.add(LF.drip);
  // electrolysis
  add(s, BOX(2.6, 2.0, 1.4), new THREE.MeshLambertMaterial({ color: 0xbfe8f8, transparent: true, opacity: 0.3, side: DS }), [-20.5, 1.3, 0]);
  add(s, BOX(2.5, 1.5, 1.3), new THREE.MeshLambertMaterial({ color: 0x5aa8e8, transparent: true, opacity: 0.6 }), [-20.5, 1.05, 0]);
  add(s, BOX(0.2, 1.8, 0.2), 0x2b2f36, [-21.3, 1.4, 0]); add(s, BOX(0.2, 1.8, 0.2), 0x2b2f36, [-19.7, 1.4, 0]);
  add(s, BOX(0.3, 0.2, 0.3), 0x2b2f36, [-21.3, 2.4, 0]); add(s, BOX(0.3, 0.2, 0.3), 0xd24c3c, [-19.7, 2.4, 0]);
  pipe(s, [[-30, 7.0, -1.6], [-22, 7.0, -1.6], [-22, 2.6, -1.6], [-21.3, 2.6, 0]], 0.08, '#e0b020', '#fff07a', -2);
  pipe(s, [[-19.7, 2.6, 0.3], [-19.7, 3.6, 0.3], [-18.2, 3.6, 0.3], [-18.2, 3.1, 0.3]], 0.12, '#3fc6d8', '#a6f4ff', 1.2);
  add(s, CYY(0.5, 2.6, 10), 0x2f9fb0, [-18.2, 1.6, 0.3]); add(s, new THREE.SphereGeometry(0.5, 10, 4, 0, 2 * PI, 0, PI / 2), 0x2f9fb0, [-18.2, 2.9, 0.3]);
  pipe(s, [[-21.3, 2.6, -0.3], [-21.3, 4.2, -0.3], [-21.3, 4.2, -6]], 0.1, '#d0d6dc', '#ffffff', 1.2);
  LF.h2 = makePoints(90, 0xffffff, 1); s.add(LF.h2); LF.o2 = makePoints(60, 0x8ff6ff, 1); s.add(LF.o2);
  // scrubber
  add(s, BOX(2.2, 3.2, 1.6), 0x4f7a6a, [-14.5, 1.7, 0]); add(s, BOX(1.6, 0.6, 0.1), 0x2a3d36, [-14.5, 2.9, 0.82]);
  LF.fan = new THREE.Group(); LF.fan.position.set(-14.5, 1.5, 0.85); s.add(LF.fan);
  add(LF.fan, new THREE.CircleGeometry(0.75, 12), M(0x22302b, { side: DS }), [0, 0, -0.01]);
  for (let k = 0; k < 4; k++) add(LF.fan, BOX(0.18, 0.62, 0.05), 0xc8d0d6, [0, 0, 0.02], [0, 0, k * PI / 2]).geometry.translate(0, 0.33, 0);
  LF.co2 = makePoints(80, 0x9a8f86, 2); s.add(LF.co2); LF.air = makePoints(80, 0xbff2ff, 1); s.add(LF.air);
  // ===== FOOD STORE (x -46..-34) =====
  const FD = { items: [] }; const fr = rng(21);
  const canCols = [0xd24c3c, 0x3fa86a, 0xf2c230, 0xe8e0d0, 0x3f7fd0, 0xe07a2a];
  for (const rx of [-44, -40.5, -37]) {
    for (const z of [-1.3, 1.3]) for (const y of [0.4, 1.4, 2.4, 3.4]) add(s, BOX(2.8, 0.08, 1.0), 0x7c8690, [rx, y, z]);
    for (const dx of [-1.4, 1.4]) for (const z of [-1.8, -0.8, 0.8, 1.8]) add(s, BOX(0.08, 3.6, 0.08), 0x5c6670, [rx + dx, 1.9, z]);
    for (const z of [-1.3, 1.3]) for (const y of [0.4, 1.4, 2.4]) for (let k = 0; k < 7; k++) { const c = canCols[Math.floor(fr() * canCols.length)]; const m = add(s, y > 2 ? BOX(0.32, 0.4, 0.32) : CYY(0.15, 0.4, 6), c, [rx - 1.2 + k * 0.4, y + 0.25, z + (fr() - .5) * 0.3]); FD.items.push(m); }
  }
  for (let k = 0; k < 10; k++) { const m = add(s, BOX(0.9, 0.7, 0.9), 0xf0c23a, [-45 + (k % 5) * 1.0 + 5.5 * Math.floor(k / 5) * 0, 0.5, 4.0 - Math.floor(k / 5) * 1.0]); FD.items.push(m); }
  FD.items.forEach((m, i) => m.userData.rank = hash(i + 0.37));
  // crew
  const crew = [];
  function person(x, z, ry = 0, shirt = 0x3a5f9a) { const g = new THREE.Group(); g.position.set(x, 0.12, z); g.rotation.y = ry; s.add(g); add(g, BOX(0.4, 0.8, 0.26), 0x1e2a3e, [0, 0.4, 0]); add(g, BOX(0.5, 0.7, 0.3), shirt, [0, 1.15, 0]); add(g, BOX(0.32, 0.34, 0.32), 0xe0b48a, [0, 1.7, 0]); add(g, BOX(0.34, 0.1, 0.34), 0x1e2a3e, [0, 1.9, 0]); crew.push(g); return g; }
  person(-23, 2, 0.3); person(-16.5, 2.2, -0.4, 0x4a6a8a); person(-39, 3.6, 0.6, 0xe8e0d0); person(13, 2.8, -0.2); person(-2.5, 3.2, 0.5, 0x6a7a3a); person(26, 3.0, 0.2);
  return { s, R, SG, TB, CD, TG, GR, LF, FD, crew, shield };
})();

function animateInterior(t, o = {}) {
  const { R, SG, TB, CD, TG, GR, LF, FD } = IN;
  R.setPower(o.power ?? 1, t, o.ins ?? 0.45);
  const sgx = 5.5;
  setPts(SG.bub, i => { const P = 2.2, age = mod(t * 1.0 + i * P / 260, P); const a = hash(i) * 2 * PI, rr = 0.2 + hash(i + 1) * 0.85; if (Math.cos(a) > 0.6 && rr > 0.5) return null; return [sgx + Math.cos(a) * rr * 0.9, 1.5 + age * 1.65, Math.sin(a) * rr * 0.9 + 0.05]; });
  setPts(SG.steam, i => { const P = 1.6, age = mod(t + i * P / 200, P); const a = hash(i) * 6.28 + age * 3; return [sgx + Math.cos(a) * 0.7 * (1 - age / P), 5.2 + age * 1.6, Math.sin(a) * 0.5]; });
  const rpm = o.rpm ?? 1; TB.rotor.rotation.x = t * 9 * rpm; TB.shaft1.rotation.x = t * 9 * rpm;
  setPts(TB.steam, i => { const P = 1.0, age = mod(t * 1.0 + i * P / 240, P); const a = hash(i) * 6.28 + age * 8; const r = 0.5 + hash(i + 2) * 0.8; return [13.5 + age * 5.2, 4.6 + Math.sin(a) * r, Math.cos(a) * r * 0.3 - 0.3]; });
  setPts(CD.steam, i => { const P = 2.0, age = mod(t + i * P / 260, P); return [13.8 + hash(i) * 4.4, 2.5 - age * 0.9, -1.1 + hash(i + 1) * 2.0]; });
  setPts(CD.drops, i => { const P = 0.9, age = mod(t + i * P / 120, P); return [13.8 + hash(i + 4) * 4.4, 1.5 - age * 0.8, -1.0 + hash(i + 5) * 2.0]; });
  CD.tubeTex.offset.x = -t * 2;
  TG.rotor.rotation.x = t * 12 * rpm;
  GR.pinion.rotation.x = t * 3.5 * rpm; GR.bull.rotation.x = -t * 3.5 * rpm * 10 / 36 + 0.05; GR.shaft.rotation.x = -t * 3.5 * rpm * 10 / 36;
  setPts(LF.vapor, i => { const P = 1.5, age = mod(t + i * P / 120, P); return [-28 + (hash(i) - .5) * 1.0, 0.8 + age * 3.0, (hash(i + 1) - .5) * 1.0]; });
  setPts(LF.drip, i => { const P = 0.8, age = mod(t + i * P / 30, P); return [-25.6 + (hash(i) - .5) * 1.2, 3.1 - age * 1.8, (hash(i + 2) - .5) * 0.4]; });
  setPts(LF.h2, i => { const P = 1.3, age = mod(t + i * P / 90, P); return [-21.3 + (hash(i) - .5) * 0.3, 0.4 + age * 1.3, (hash(i + 1) - .5) * 0.5 + 0.7]; });
  setPts(LF.o2, i => { const P = 1.3, age = mod(t + i * P / 60, P); return [-19.7 + (hash(i) - .5) * 0.3, 0.4 + age * 1.3, (hash(i + 1) - .5) * 0.5 + 0.7]; });
  LF.fan.rotation.z = -t * 10;
  setPts(LF.co2, i => { const P = 2, age = mod(t + i * P / 80, P); return [-18.5 + age * 2.6, 0.9 + hash(i) * 1.4, 1.1 + (hash(i + 1) - .5) * 0.8]; });
  setPts(LF.air, i => { const P = 2, age = mod(t + i * P / 80, P); return [-14.5 + (hash(i) - .5) * 1.6, 3.4 + age * 2.2, (hash(i + 1) - .5) * 1.2]; });
  const rem = o.food ?? 1; FD.items.forEach(m => m.visible = m.userData.rank < rem);
  IN.crew.forEach((c, i) => c.position.y = 0.12 + Math.abs(Math.sin(t * 2 + i)) * 0.03);
}

// ---------- FISSION / CHAIN scene ----------
const FS = (() => {
  const s = new THREE.Scene(); s.background = new THREE.Color(0x0a1220); lights(s, 0xffffff, 0x223344, 1.2, 2.0, 0.5, [10, 20, 30]);
  const stars = makePoints(400, 0x2d4a66, 1); s.add(stars); const sr = rng(9); setPts(stars, () => [(sr() - .5) * 200, (sr() - .5) * 200, -60 - sr() * 60]);
  const icoG = new THREE.IcosahedronGeometry(0.4, 0);
  const pM = M(0xd9433a), nM = M(0x9fb3c6);
  // single nucleus
  const N = 64, nuc = new THREE.Group(); s.add(nuc); const parts = [];
  const dirS = V(0.55, 0.83, 0).normalize();
  for (let i = 0; i < N; i++) { const r = 1.5 * Math.cbrt((i + 0.5) / N); const y = 1 - 2 * (i + 0.5) / N, rad = Math.sqrt(1 - y * y), th = i * 2.39996; const p = V(Math.cos(th) * rad, y, Math.sin(th) * rad).multiplyScalar(r); const m = add(nuc, icoG, i % 9 < 4 ? pM : nM, [p.x, p.y, p.z]); m.userData.p0 = p.clone(); m.userData.side = p.dot(dirS) + (hash(i) - .5) * 0.3 > 0 ? 1 : -1; parts.push(m); }
  const neutronM = new THREE.MeshLambertMaterial({ color: 0xbff4ff, emissive: 0x3fb0e0, emissiveIntensity: 1 });
  const nIn = add(s, new THREE.IcosahedronGeometry(0.34, 1), neutronM);
  const nOut = [0, 1, 2].map(() => add(s, new THREE.IcosahedronGeometry(0.34, 1), neutronM));
  const outDirs = [V(-0.3, -1, 0.2), V(1, -0.35, 0.4), V(-1, 0.45, -0.3)].map(v => v.normalize());
  const trail = makePoints(400, 0x7fd8ff, 1); s.add(trail);
  const flashM = new THREE.MeshBasicMaterial({ color: 0xfff2b0, transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false });
  const flash = add(s, new THREE.IcosahedronGeometry(1, 1), flashM);
  const fl = new THREE.PointLight(0xffd080, 0, 40, 1.2); s.add(fl);
  const rays = makePoints(300, 0xffe08a, 2); s.add(rays);
  const fragM = new THREE.MeshLambertMaterial({ color: 0xff9a3a, emissive: 0xff5a10, emissiveIntensity: 0 });
  // chain
  const chain = new THREE.Group(); s.add(chain);
  const NN = 22, nucs = []; const cr = rng(42);
  for (let i = 0; i < 9; i++) for (let j = 0; j < 9; j++) for (let k = 0; k < 3; k++) nucs.push({ p: V((i - 4) * 4.4 + (cr() - .5) * 1.2, (j - 4) * 4.4 + (cr() - .5) * 1.2, (k - 1) * 4.4 + (cr() - .5) * 1.2), split: Infinity, dir: V(cr() - .5, cr() - .5, cr() - .5).normalize() });
  const inst = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.42, 0), new THREE.MeshLambertMaterial({ flatShading: true }), nucs.length * NN); chain.add(inst);
  const local = []; for (let i = 0; i < NN; i++) { const r = 1.05 * Math.cbrt((i + 0.5) / NN); const y = 1 - 2 * (i + 0.5) / NN, rad = Math.sqrt(1 - y * y), th = i * 2.39996; local.push(V(Math.cos(th) * rad, y, Math.sin(th) * rad).multiplyScalar(r)); }
  // simulate
  const speed = 5.2, neutrons = []; let center = 0; let best = 1e9; nucs.forEach((n, i) => { const d = n.p.length(); if (d < best) { best = d; center = i; } });
  const t0 = 1.0; nucs[center].split = t0 + 1.6; neutrons.push({ a: V(-24, 3, 2), b: nucs[center].p.clone(), t0: t0, t1: t0 + 1.6 });
  const queue = [center]; const targeted = new Set([center]);
  while (queue.length) { queue.sort((a, b) => nucs[a].split - nucs[b].split); const i = queue.shift(); const n = nucs[i]; const k = cr() < 0.5 ? 2 : 3;
    const near = nucs.map((m, j) => [j, m.p.distanceTo(n.p)]).filter(([j]) => !targeted.has(j)).sort((a, b) => a[1] - b[1]).slice(0, 6);
    for (let q = 0; q < k; q++) { if (near.length && cr() < 0.85) { const pick = Math.floor(cr() * Math.min(3, near.length)); const [j, d] = near.splice(pick, 1)[0]; targeted.add(j); const ta = n.split, tb = ta + d / speed; nucs[j].split = tb; neutrons.push({ a: n.p.clone(), b: nucs[j].p.clone(), t0: ta, t1: tb }); queue.push(j); } else { const dir = V(cr() - .5, cr() - .5, cr() - .5).normalize(); neutrons.push({ a: n.p.clone(), b: n.p.clone().addScaledVector(dir, 14), t0: n.split, t1: n.split + 14 / speed }); } } }
  const nInst = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.26, 0), neutronM, neutrons.length); chain.add(nInst);
  const fInst = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), flashM, nucs.length); chain.add(fInst);
  const dm = new THREE.Object3D(), col = new THREE.Color();
  const cP = new THREE.Color(0xd9433a), cN = new THREE.Color(0x9fb3c6), cHot = new THREE.Color(0xffa040);
  function updateChain(lt, heat) {
    let ii = 0;
    nucs.forEach((n, ni) => { const age = lt - n.split; for (let q = 0; q < NN; q++) { const lp = local[q]; const side = lp.dot(n.dir) > 0 ? 1 : -1; let p = n.p.clone().add(lp); if (age > 0) p.addScaledVector(n.dir, side * (0.4 + 1.4 * (1 - Math.exp(-2.5 * age)))); else if (age > -0.4) p.add(lp.clone().multiplyScalar(0.15 * Math.sin(age * 40))); dm.position.copy(p); dm.rotation.set(0, 0, 0); dm.scale.setScalar(1); dm.updateMatrix(); inst.setMatrixAt(ii, dm.matrix); col.copy(q % 9 < 4 ? cP : cN); if (age > 0) col.lerp(cHot, clamp(age * 0.5) * 0.6 + heat * 0.4); inst.setColorAt(ii, col); ii++; } });
    inst.instanceMatrix.needsUpdate = true; inst.instanceColor.needsUpdate = true;
    neutrons.forEach((n, i) => { const u = (lt - n.t0) / (n.t1 - n.t0); if (u < 0 || u > 1) dm.scale.setScalar(0); else { dm.scale.setScalar(1); dm.position.lerpVectors(n.a, n.b, u); } dm.updateMatrix(); nInst.setMatrixAt(i, dm.matrix); });
    nInst.instanceMatrix.needsUpdate = true;
    nucs.forEach((n, i) => { const a = lt - n.split; const sc = a > 0 && a < 0.5 ? 1.8 * Math.sin(PI * a / 0.5) : 0; dm.position.copy(n.p); dm.scale.setScalar(sc); dm.updateMatrix(); fInst.setMatrixAt(i, dm.matrix); });
    fInst.instanceMatrix.needsUpdate = true;
  }
  function updateSingle(lt, T) { // T: {hit, split}
    nuc.visible = true; chain.visible = false;
    const hit = T.hit, sp = T.split;
    const u = clamp((lt - (hit - 1.8)) / 1.8); nIn.visible = lt < hit + 0.05; nIn.position.set(lerp(-14, -1.2, u), lerp(-1.5, 0, u), 0);
    setPts(trail, i => { if (i >= 400) return null; const k = i % 40, which = Math.floor(i / 40); const tt = lt - k * 0.015; if (which === 0) { if (tt > hit || tt < hit - 1.8) return null; const uu = (tt - (hit - 1.8)) / 1.8; return [lerp(-14, -1.2, uu), lerp(-1.5, 0, uu), 0]; } if (which <= 3) { const a = tt - sp; if (a < 0) return null; const d = outDirs[which - 1]; const p = d.clone().multiplyScalar(1.2 + a * 6); return [p.x, p.y, p.z]; } return null; });
    const wob = lt > hit && lt < sp ? (lt - hit) / (sp - hit) : 0;
    parts.forEach(m => { const p0 = m.userData.p0; const a = lt - sp; m.material = m.userData.mat0 ??= m.material; if (a > 0) { const d = (0.6 + 3.2 * (1 - Math.exp(-1.4 * a)) + a * 0.25); m.position.copy(p0).addScaledVector(dirS, m.userData.side * d); m.material = m.userData.side > 0 ? fragM : fragM; } else { m.position.copy(p0); if (wob > 0) { m.position.x *= 1 + 0.35 * wob * Math.sin(lt * 30) * 0.5 + 0.25 * wob; m.position.y *= 1 - 0.12 * wob; } } });
    if (lt > sp) { fragM.emissiveIntensity = clamp((lt - sp) * 0.6, 0, 0.9); fragM.color.set(0xff9a3a); }
    nuc.rotation.y = lt * 0.2;
    const fa = lt - sp; flash.visible = fa > 0 && fa < 1.2; const fs = fa < 0.25 ? fa / 0.25 : 1 - (fa - 0.25) / 0.95; flash.scale.setScalar(0.5 + 4 * clamp(fs)); flashM.opacity = clamp(fs);
    fl.intensity = fa > 0 ? 60 * clamp(1 - fa / 3) : 0;
    setPts(rays, i => { if (fa < 0 || fa > 2.5) return null; const d = V(hash(i) - .5, hash(i + 1) - .5, hash(i + 2) - .5).normalize(); const r = fa * (8 + hash(i + 3) * 8); return [d.x * r, d.y * r, d.z * r]; });
    nOut.forEach((m, k) => { const a = lt - sp; m.visible = a > 0; m.position.copy(outDirs[k]).multiplyScalar(1.2 + Math.max(0, a) * 6); });
    return { nIn: nIn.position, flash: V(0, 0, 0), out: nOut.map(m => m.position) };
  }
  function showChain(lt, heat) { nuc.visible = false; chain.visible = true; nIn.visible = false; nOut.forEach(m => m.visible = false); flash.visible = false; setPts(trail, () => null); setPts(rays, () => null); fl.intensity = heat * 50; fl.position.set(0, 0, 8); updateChain(lt, heat); s.background.setRGB(lerp(0.004, 0.09, heat), lerp(0.007, 0.02, heat), lerp(0.016, 0.005, heat)); }
  return { s, updateSingle, showChain, nucs, center };
})();

// ---------- scene timeline logic ----------
const SCN = {};
const subOrbit = (c, ang, r, h) => V(c.x + Math.sin(ang) * r, c.y + h, c.z + Math.cos(ang) * r);

SCN.surface = (L, t) => {
  const lt = L.lt; const sx = SF.update(t, tt => tt * 1.6, -1.2, 0);
  const c = SF.sub.position.clone().add(V(2, 1.5, 0));
  let p = subOrbit(c, lerp(1.05, 0.62, ease(lt / 11)), lerp(62, 50, ease(lt / 11)), lerp(5, 10, ease(lt / 11)));
  if (lt > 10.5) { const e = ease((lt - 10.5) / 4.5); p.lerp(subOrbit(c, 0.3, 20, 3.5), e); }
  cam(p, c, 50);
  hudDepth(0);
  return SF.s;
};
SCN.ballast = (L, t) => {
  const lt = L.lt, g = UW.subG; UW.update(t, { subG: 1, bubbles: 1, bubbles2: 1, flow: 0.2 });
  const vent = L.sg[2] + 1.6, fillT = clamp((lt - vent) / 6.5); const fill = 0.04 + 0.92 * ease(fillT);
  const sink = sstep(vent + 2.5, L.d + 1.5, lt);
  g.position.set(0, lerp(-1.4, -13, sink) + 0.1 * Math.sin(t), 0); g.rotation.z = -0.06 * sstep(vent + 2, vent + 6, lt); g.userData.prop.rotation.x = t * 3;
  g.userData.setFill(fill);
  const cy = g.position.y;
  camKF(lt, [[0, [30, -10, 34], [5, -2, 0], 50], [L.sg[1], [33, -10, 30], [5, -2, 0], 50], [vent - 0.5, [34, -9, 30], [5, -2, 0], 50]]);
  if (lt > vent - 0.5) cam(V(34, cy - 7.6, 30), V(5, cy - 0.6, 0));
  UW.setDepth(Math.min(camera.position.y, -2) - 6);
  const open = lt > vent;
  setPts(UW.bubbles, i => { if (!open || fillT >= 1) return null; const P = 2.2, age = mod(lt * 1.0 + i * P / 700, P); if (lt - vent < age) return null; const tank = g.userData.tanks[i % 2]; const sp = (hash(i) - .5); return [tank.cx + sp * 1.2 + Math.sin(age * 9 + i) * 0.2, g.position.y + 2.1 + age * 3.5, (hash(i + 1) - .5) * 0.8]; });
  setPts(UW.bubbles2, i => { if (!open || fillT >= 1) return null; const P = 1.2, age = mod(lt + i * P / 500, P); const tank = g.userData.tanks[i % 2]; return [tank.cx + (hash(i) - .5) * 4, g.position.y - 2.6 + age * 1.2, (hash(i + 1) - .5) * 1.0]; });
  const T0 = V(13.2, 0, 2).add(g.position), T1 = V(-9.5, 0, 2).add(g.position);
  L_(T0, 'BALLAST TANK', L.sg[0] + 1.6, lt, { dx: -80, dy: 200 }); L_(T1, 'BALLAST TANK', L.sg[0] + 2.0, lt, { dx: -60, dy: -200, t1: L.sg[1] - 0.3 });
  L_(V(13.2, 0.8, 0).add(g.position), 'AIR', L.sg[1] + 0.4, lt, { dx: -80, dy: 150, t1: vent }); L_(V(-9.5, 0.8, 0).add(g.position), 'AIR', L.sg[1] + 0.4, lt, { dx: -80, dy: -150, t1: vent });
  L_(V(13.2, 2.1, 0).add(g.position), 'VENT OPEN', vent, lt, { dx: -110, dy: -150, color: '#ffd35a' });
  L_(V(-9.5, -1.6, 0).add(g.position), 'SEAWATER IN', vent + 1.0, lt, { dx: -60, dy: 200, color: '#7fd0ff' });
  hudDepth(Math.max(0, (-g.position.y - 1.4) * 2.7));
  return UW.s;
};
SCN.dive = (L, t) => {
  const lt = L.lt, g = UW.subA; UW.update(t, { subA: 1, flow: 1.4 });
  const u = lt / L.d; g.position.set(lerp(-14, 22, u), lerp(-9, -42, ease(u)), 0); g.rotation.z = -0.22 * sstep(0, 1.5, lt); g.userData.prop.rotation.x = t * 5;
  g.userData.sailPlanes.rotation.z = 0.3; g.userData.sternPlanes.rotation.z = 0.35 * sstep(0, 1, lt); g.userData.hullMat.opacity = 1;
  const c = g.position.clone();
  cam(c.clone().add(V(lerp(30, 22, u), lerp(10, 5, u), lerp(32, 38, u))), c.clone().add(V(3, -1, 0)), 50);
  UW.setDepth(c.y);
  L_(g.localToWorld(V(7.6, 4.0, 2.2)), 'DIVING PLANES', L.sg[0] + 0.4, lt, { dx: 60, dy: -120 });
  L_(g.localToWorld(V(-17.6, 0, 3)), 'DIVING PLANES', L.sg[0] + 0.9, lt, { dx: -60, dy: -160 });
  L_(g.localToWorld(V(0, -1.8, 1)), 'TRIM TANKS', L.sg[0] + L.sp[0] * 0.6, lt, { dx: 60, dy: 140, color: '#7fd0ff' });
  hudDepth(lerp(20, 110, ease(u)));
  return UW.s;
};
SCN.deep = (L, t) => {
  const lt = L.lt, g = UW.subA; UW.update(t, { subA: 1, arrows: 1, flow: 0.8 });
  g.position.set(0, -70, 0); g.rotation.z = 0; g.userData.sailPlanes.rotation.z = 0; g.userData.sternPlanes.rotation.z = 0; g.userData.prop.rotation.x = t * 4;
  const rev = sstep(L.sg[2] + 1.5, L.sg[2] + 3.0, lt); g.userData.hullMat.opacity = 1 - 0.75 * rev; g.userData.hullMat.depthWrite = rev < 0.1;
  UW.rg.visible = rev > 0; UW.rgl.intensity = 80 * rev; UW.rgm.emissiveIntensity = 0.5 + 0.5 * Math.sin(t * 6) * 0.3;
  const c = g.position;
  const ar = sstep(L.sg[1] + 1.5, L.sg[1] + 2.2, lt) * (1 - sstep(L.sg[2], L.sg[2] + 0.5, lt)); UW.arrows.visible = ar > 0.01;
  UW.arDirs.forEach((a, i) => { const r = 2.6 + 0.9 * (1 - ar) + 0.35 * Math.sin(t * 6 + i); a.m.position.set(a.x, c.y, 0).addScaledVector(a.d, r + 0.6); a.m.scale.setScalar(ar); });
  camKF(lt, [[0, [-30, -60, 30], [0, -70, 0], 50], [L.sg[1], [-12, -64, 30], [0, -70, 0], 50], [L.sg[2] + 0.8, [6, -66, 26], [0, -70, 0], 50], [L.d, [-3, -67.5, 9], [-3, -70, 0], 55]]);
  UW.setDepth(-75);
  if (lt > L.sg[0] && lt < L.sg[1] - 0.2) { const bl = Math.floor(t * 2.5) % 2; hudBig('NO OXYGEN', bl ? '#ff5a4a' : '#ffffff', 1180, 72); hudBig('NO FIRE', '#ffffff', 1270, 56); }
  if (lt > L.sg[1] + 2.5 && lt < L.sg[2]) { L_(V(5, -68, 2), '~240 TONS PER SQ METER', L.sg[1] + 2.5, lt, { dx: 40, dy: -260, color: '#ffd35a', size: 30 }); }
  L_(V(-3, -70, 1), 'REACTOR', L.sg[2] + 2.6, lt, { dx: 60, dy: -140, color: '#ffb43a' });
  const dep = lt < L.sg[1] ? 120 : lerp(120, 240, sstep(L.sg[1] + 0.5, L.sg[1] + 3, lt)) + (lt > L.sg[1] + 3 ? 2 * Math.sin(t) : 0);
  hudDepth(dep);
  return UW.s;
};
// interior helpers
const RPOS = V(0, 2.6, 0);
SCN.reactor = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.8, ins: 0.45 });
  camKF(lt, [[0, [6, 7, 15], [0, 3, 0], 50], [L.d, [3.5, 5, 9.5], [0, 2.8, 0], 50]], 1.25);
  L_(V(-0.4, 2.2, 0.8), 'FUEL RODS', L.sg[0] + 0.6, lt, { dx: -70, dy: 220 }); L_(V(0.3, 3.0, 0.5), 'URANIUM', L.sg[0] + 2.4, lt, { dx: 90, dy: -160, color: '#ffb43a' });
  L_(V(1.3, 5.0, 1.0), 'REACTOR', 0.3, lt, { dx: 80, dy: -100 });
  return IN.s;
};
SCN.fission = (L, t) => {
  const lt = L.lt; const hit = L.sg[0] + L.sp[0] * 0.38, sp = hit + 0.8;
  const P = FS.updateSingle(lt, { hit, split: sp });
  const zoom = sstep(sp, sp + 2.5, lt);
  cam(V(Math.sin(lt * 0.08) * 6, 1.5, lerp(15, 21, zoom)), V(-1, 0, 0), 50);
  if (lt < hit) L_(P.nIn.clone(), 'NEUTRON', 0.7, lt, { dx: 40, dy: -120, color: '#9fe8ff' });
  if (lt < sp) L_(V(0.6, 1.2, 0), 'URANIUM-235', 1.0, lt, { dx: 60, dy: -170 });
  L_(V(0, 0, 0), 'ENERGY', L.sg[1] + 0.9, lt, { dx: -110, dy: 230, color: '#ffd35a' });
  if (lt > L.sg[1] + 2.4) L_(P.out[1].clone(), 'NEW NEUTRONS', L.sg[1] + 2.4, lt, { dx: -120, dy: -150, color: '#9fe8ff' });
  return FS.s;
};
SCN.chain = (L, t) => {
  const lt = L.lt; const heat = sstep(L.sg[1] - 0.3, L.sg[1] + 1.5, lt);
  FS.showChain(lt + 1.2, heat);
  cam(V(Math.sin(lt * 0.12) * 10, 4 + lt * 0.3, lerp(14, 46, ease(lt / (L.sg[1] + 1)))), V(0, 0, 0), 50);
  if (heat > 0.3) hudBig('HEAT', '#ffb43a', 1150, 150, clamp((heat - 0.3) * 2));
  return FS.s;
};
SCN.rods = (L, t) => {
  const lt = L.lt; const s1 = L.sg[1], e1 = L.sp[1], s2 = L.sg[2], e2 = L.sp[2];
  let ins = 0.45;
  ins = lerp(ins, 0.95, sstep(s1 + e1 * 0.08, s1 + e1 * 0.3, lt)); ins = lerp(ins, 0.15, sstep(s1 + e1 * 0.52, s1 + e1 * 0.75, lt));
  const scram = s2 + e2 * 0.38; if (lt > scram) ins = lerp(0.15, 1.0, clamp((lt - scram) / 0.35));
  const power = lt > scram ? Math.max(0.02, (1 - ins) / 0.85 * 0.5 * Math.exp(-(lt - scram) * 1.5)) : clamp(1.15 - ins);
  animateInterior(t, { power, ins });
  camKF(lt, [[0, [4.5, 6.5, 10], [0, 4, 0], 50], [s1, [3, 5.2, 8.5], [0, 3.6, 0], 50], [L.d, [2.5, 4.8, 7.8], [0, 3.4, 0], 50]], 1.25);
  L_(V(-0.19, 4.3, 0.57), 'CONTROL RODS', L.sg[0] + 0.5, lt, { dx: -90, dy: -200 });
  if (lt > s1 + e1 * 0.08 && lt < s1 + e1 * 0.5) { hudBig('RODS IN', '#7fd0ff', 1180, 72); hudBig('SLOWER', '#ffffff', 1270, 54); }
  if (lt > s1 + e1 * 0.52 && lt < s2) { hudBig('RODS OUT', '#ffb43a', 1180, 72); hudBig('FASTER', '#ffffff', 1270, 54); }
  if (lt > scram) { const bl = Math.floor((lt - scram) * 3) % 2; hudBig('SCRAM', bl ? '#ff4a3a' : '#ffffff', 1200, 110); }
  hudCounter('REACTOR POWER', Math.round(power * 100) + '%', '#ffb43a', 70, 1420);
  return IN.s;
};
SCN.reactor2 = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.8, ins: 0.4 });
  camKF(lt, [[0, [3, 6, 12], [1, 3.5, 0], 50], [L.d, [16, 10, 42], [16, 3.5, 0], 50]], 1.25);
  L_(V(0, 3.2, 0.6), 'REACTOR', 0.6, lt, { dx: 60, dy: -200, color: '#ffb43a' });
  L_(V(33.5, 2, 0), 'PROPELLER SHAFT', L.sg[0] + 1.8, lt, { dx: -150, dy: 220 });
  if (lt > L.sg[0] + L.sp[0] * 0.6) hudBig('HEAT ONLY', '#ffb43a', 1250, 90);
  return IN.s;
};
SCN.primary = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.85, ins: 0.4 });
  const [a, b, c, d] = L.sg;
  camKF(lt, [[0, [4, 6.5, 15], [2.5, 2.8, 0], 50], [b, [3.5, 5, 12], [2, 2.6, 0], 50], [c + 0.5, [-1, 5.5, 11], [-2.2, 2.8, 0], 50], [d, [-1, 5.5, 11], [-2, 2.8, 0], 50], [d + 1.6, [7, 6, 14], [6, 3, 0], 50], [L.d, [8, 6, 15], [6.5, 3, 0], 50]], 1.25);
  L_(V(3.4, 2.6, 0.3), 'PRIMARY LOOP', a + 0.8, lt, { dx: 70, dy: -260, t1: c });
  L_(V(2.4, 3.8, 0.3), 'HOT', a + 1.6, lt, { dx: 20, dy: -110, color: '#ffb43a', t1: c });
  L_(V(4, 0.9, -2), 'COLD', a + 2.2, lt, { dx: 50, dy: 120, color: '#7fb0ff', t1: c });
  if (lt > b + 0.3 && lt < c) { hudBig('300+ °C', '#ff7a3a', 1200, 110); hudBig('NO BOILING', '#ffffff', 1300, 54); }
  L_(V(-3.4, 3.8, 0.2), 'PRESSURIZER', c + 1.0, lt, { dx: -40, dy: -200, t1: d });
  if (lt > c + L.sp[2] * 0.4 && lt < d) hudCounter('PRESSURE', '150+ ATM', '#ffd35a', 70, 1420);
  L_(V(9, 4.5, 3), 'SHIELDING', d + 1.8, lt, { dx: -40, dy: -180, color: '#ffd35a' });
  L_(V(3.4, 2.0, 0.3), 'RADIOACTIVE', d + 0.4, lt, { dx: -200, dy: 200, color: '#b6ff5a' });
  return IN.s;
};
SCN.steamgen = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.85, ins: 0.4 });
  const [a, b, c, d] = L.sg;
  camKF(lt, [[0, [9.5, 6, 11], [5.5, 3.6, 0], 50], [b, [8.5, 5, 8], [5.5, 3.2, 0], 50], [d, [7.5, 4.8, 7], [5.5, 3.6, 0], 48], [L.d, [10, 9.5, 12], [9, 6.5, 0], 50]], 1.25);
  L_(V(6.6, 6.0, 0.5), 'STEAM GENERATOR', a + 0.5, lt, { dx: 50, dy: -180, t1: b });
  L_(V(5.0, 4.2, 0.2), 'THIN TUBES', a + L.sp[0] * 0.6, lt, { dx: -140, dy: -150, color: '#ffb43a', t1: b });
  L_(V(6.2, 2.5, 0.8), 'SECOND LOOP', b + 0.6, lt, { dx: 80, dy: 160, color: '#7fd0ff', t1: c + 0.2 });
  if (lt > c && lt < d) { L_(V(5.3, 3.6, 0.2), 'HEAT: PASSES', c + 0.2, lt, { dx: -170, dy: -230, color: '#ffb43a' }); L_(V(6.2, 2.4, 0.7), 'WATER: STAYS', c + L.sp[2] * 0.5, lt, { dx: 70, dy: 200, color: '#7fd0ff' }); }
  L_(V(5.5, 8.4, 0), 'STEAM', d + 0.8, lt, { dx: 60, dy: -140 });
  return IN.s;
};
SCN.turbine = (L, t) => {
  const lt = L.lt; const spin = sstep(0, 2.5, lt); animateInterior(t, { power: 0.85, ins: 0.4, rpm: 0.3 + 0.7 * spin });
  const [a, b, c] = L.sg;
  camKF(lt, [[0, [18, 8.5, 12], [16, 5, 0], 50], [b, [18.5, 6.5, 9], [16.5, 4.6, 0], 50], [c, [20, 6.2, 10], [18, 4, 0], 50], [c + 1.5, [24.5, 5, 9.5], [23.5, 2.2, 0], 50], [L.d, [25, 5, 9], [23.8, 2.2, 0], 50]], 1.25);
  L_(V(15, 5.9, 0.6), 'TURBINE BLADES', a + 1.0, lt, { dx: -60, dy: -180, t1: b });
  if (lt < c) hudCounter('RPM', String(Math.round(4000 * eout(lt / 4) + (lt > 4 ? 30 * Math.sin(t * 7) : 0))), '#ffffff', 70, 1420);
  L_(V(17, 4.6, 1.2), 'MAIN ENGINE', b + 0.4, lt, { dx: 60, dy: -200, color: '#ffb43a', t1: c });
  L_(V(26, 4.6, 0), 'TO PROPELLER', b + 1.5, lt, { dx: -40, dy: 180, t1: c });
  L_(V(24.6, 3.1, 0.8), 'TURBINE GENERATOR', c + 0.5, lt, { dx: -220, dy: -200 });
  L_(V(26.6, 6, -0.8), 'ELECTRICITY', c + 2.2, lt, { dx: -90, dy: -180, color: '#ffe04a' });
  return IN.s;
};
SCN.condenser = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.85, ins: 0.4 });
  const [a, b, c] = L.sg;
  camKF(lt, [[0, [17, 5, 10], [16, 2, 0], 50], [b, [17, 3.5, 7.5], [16, 1.4, -0.5], 50], [c + 0.5, [14, 4, 9], [12, 1.5, 0], 50], [L.d, [8.5, 5, 11], [7.5, 3, 0], 50]], 1.25);
  L_(V(16, 2.6, 1.2), 'CONDENSER', a + 0.5, lt, { dx: -80, dy: -220, t1: b });
  L_(V(15, 2.0, 0.6), 'STEAM IN', a + 1.4, lt, { dx: 90, dy: -170, t1: b });
  L_(V(15, 1.4, -3), 'COLD SEAWATER', b + 0.3, lt, { dx: -120, dy: 220, color: '#7ff0dd', t1: c });
  L_(V(16, 0.8, 1), 'WATER', b + L.sp[1] * 0.6, lt, { dx: 80, dy: 160, color: '#7fb0ff', t1: c });
  L_(V(7.6, 2.4, 0.8), 'BACK TO STEAM GENERATOR', c + 1.4, lt, { dx: -60, dy: -260, color: '#7fb0ff' });
  if (lt > c + L.sp[2] * 0.6) hudBig('NO EXHAUST', '#ffffff', 1250, 80);
  return IN.s;
};
SCN.gears = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.85, ins: 0.4 });
  camKF(lt, [[0, [33, 6.5, 8], [28, 3, 0], 50], [L.d, [31.5, 4.5, 6], [28, 2.8, 0], 50]]);
  L_(V(28, 1.0, 1.2), 'REDUCTION GEARS', 0.6, lt, { dx: -90, dy: 260 });
  L_(V(28, 5.0, 0.4), 'FAST', 1.8, lt, { dx: 70, dy: -140, color: '#ff7a3a' });
  L_(V(28, 3.4, 1.2), 'SLOW', 2.6, lt, { dx: 100, dy: -60, color: '#7fd0ff' });
  return IN.s;
};
SCN.shaft = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.85, ins: 0.4 });
  camKF(lt, [[0, [29, 4.5, 6], [30, 2, 0], 50], [L.d, [33, 4, 5.5], [35, 2, 0], 50]], 1.25);
  L_(V(31.5, 2.0, 0.3), 'SHAFT', 0.4, lt, { dx: -80, dy: -180 });
  L_(V(34.6, 2.0, 0.4), 'THROUGH THE HULL', L.sp[0] * 0.55, lt, { dx: -160, dy: 200, color: '#ffd35a' });
  return IN.s;
};
SCN.prop = (L, t) => {
  const lt = L.lt, g = UW.subA; const [a, b] = L.sg; const pj = sstep(b + 0.2, b + 1.6, lt);
  UW.update(t, { subA: 1, thrown: 1, shroud: pj > 0, flow: 3 });
  g.position.set(0, -55, 0); g.rotation.z = 0; g.userData.hullMat.opacity = 1; g.userData.hullMat.depthWrite = true; g.userData.sailPlanes.rotation.z = 0; g.userData.sternPlanes.rotation.z = 0;
  g.userData.prop.rotation.x = t * 7; UW.shroud.scale.set(1, pj, 1); UW.shroud.visible = pj > 0.01;
  setPts(UW.thrown, i => { const P = 1.4, age = mod(lt + i * P / 900, P); const ang = i * 2.399 + age * 5; const r = 0.25 + hash(i) * 1.1 + age * 0.5; return [-21.8 - age * 12, -55 + Math.sin(ang) * r, Math.cos(ang) * r]; });
  camKF(lt, [[0, [-6, -51, 24], [-20, -55, 0], 50], [b, [-7, -52, 22], [-20.5, -55, 0], 50], [L.d, [-12, -53, 15], [-21.3, -55, 0], 50]]);
  UW.setDepth(-60);
  if (lt > a + 0.6 && lt < b) { hudArrow(600, 1440, 920, 1440, '#ffc83a'); hudArrow(480, 1440, 160, 1440, '#7fd0ff'); }
  L_(V(-21.3, -54.2, 0.5), 'PROPELLER', 0.4, lt, { dx: 60, dy: -170, t1: b });
  if (lt > a + 0.6 && lt < b) { hudBig('WATER BACK', '#7fd0ff', 1250, 64); hudBig('SUB FORWARD', '#ffc83a', 1340, 64); }
  L_(V(-21.2, -53.7, 1.2), 'PUMP-JET', b + 1.2, lt, { dx: 60, dy: -190, color: '#ffd35a' });
  return UW.s;
};
SCN.life = (L, t) => {
  const lt = L.lt; animateInterior(t, { power: 0.85, ins: 0.4 });
  const [a, b, c, d] = L.sg;
  camKF(lt, [[0, [-20, 9, 24], [-21, 2.5, 0], 50], [b - 0.3, [-21, 8, 21], [-21, 2.5, 0], 50], [b + 0.8, [-24.5, 4.8, 9], [-26.6, 2.2, 0], 50], [c - 0.3, [-24, 4.5, 9], [-26.4, 2, 0], 50], [c + 0.8, [-18.5, 4, 8], [-20.2, 1.6, 0], 50], [d - 0.3, [-18.5, 4, 8], [-20, 1.6, 0], 50], [d + 0.8, [-12.5, 4.2, 8], [-14.8, 2, 0], 50], [L.d, [-12.5, 4.2, 8.5], [-15, 2, 0], 50]], 1.25);
  L_(V(-29.9, 7.2, -1.6), 'POWER IN', a + 1.4, lt, { dx: 60, dy: -140, color: '#ffe04a', t1: b });
  L_(V(-28, 3.0, 0.8), 'DISTILLER', b + 0.6, lt, { dx: -70, dy: -230, t1: c });
  L_(V(-25.6, 0.8, 0.7), 'FRESH WATER', b + 1.6, lt, { dx: 60, dy: 200, color: '#7fd0ff', t1: c });
  L_(V(-28.5, 1.0, -2), 'SEAWATER', b + 1.0, lt, { dx: -40, dy: 280, color: '#7ff0dd', t1: c });
  L_(V(-19.7, 1.8, 0.7), 'OXYGEN', c + L.sp[2] * 0.3, lt, { dx: 80, dy: -220, color: '#8ff6ff', t1: d });
  L_(V(-21.3, 1.8, 0.7), 'HYDROGEN', c + L.sp[2] * 0.7, lt, { dx: -90, dy: -160, t1: d });
  L_(V(-18.2, 2.0, 0.8), 'O2 TANK', c + L.sp[2] * 0.9, lt, { dx: 70, dy: 150, color: '#8ff6ff', t1: d });
  L_(V(-14.5, 2.9, 0.8), 'CO2 SCRUBBER', d + 0.5, lt, { dx: -60, dy: -230 });
  L_(V(-17, 1.5, 1.1), 'CO2', d + 1.6, lt, { dx: -90, dy: 160, color: '#c9b8a8' });
  L_(V(-14.5, 4.5, 0), 'CLEAN AIR', d + 2.4, lt, { dx: 60, dy: -150, color: '#bff2ff' });
  return IN.s;
};
SCN.sonar = (L, t) => {
  const lt = L.lt, g = UW.subA; const [a, b, c] = L.sg;
  UW.update(t, { subA: 1, ship: 1, whale: 1, flow: 0.7 });
  g.position.set(0, -32, 0); g.rotation.z = 0; g.userData.hullMat.opacity = 1; g.userData.hullMat.depthWrite = true; g.userData.prop.rotation.x = t * 3; g.userData.sailPlanes.rotation.z = 0; g.userData.sternPlanes.rotation.z = 0;
  UW.ship.position.set(4 + lt * 1.2, 0.2, -36); UW.shipProp.rotation.x = t * 10;
  UW.whale.position.set(-14 + lt * 0.8, -50 + Math.sin(lt * 0.5) * 1.5, -24); UW.whale.rotation.z = 0.05 * Math.sin(lt); UW.tail.rotation.z = 0.35 * Math.sin(lt * 2.2);
  camKF(lt, [[0, [-30, -26, 32], [0, -30, 0], 52], [b - 0.5, [-14, -29, 22], [0, -31, 0], 50], [b + 0.8, [5, -29, 12], [1, -31.5, 0], 50], [c - 0.2, [7, -29, 12], [3, -31.5, 0], 50], [c + 1.5, [24, -26, 62], [2, -27, -12], 55], [L.d, [20, -26, 66], [0, -27, -14], 55]]);
  UW.setDepth(-32, 0.55);
  if (lt > c) { const src = [UW.ship.position.clone().add(V(-8, -2, 0)), UW.whale.position.clone()]; UW.rings.forEach((r, i) => { const s = src[i % 2]; const age = mod(lt * 1.0 + Math.floor(i / 2) * 0.75 + (i % 2) * 0.3, 4.5); r.visible = lt - c > age * 0 && true; const rad = 1 + age * 9; r.position.copy(s); r.scale.setScalar(rad); r.lookAt(camera.position); r.material.opacity = 0.55 * (1 - age / 4.5); }); }
  if (lt > a + 0.3 && lt < b) hudBig('SHHH...', '#bff2ff', 1250, 80);
  L_(V(2, -30.2, 1.9), 'SOUND-ABSORBING TILES', b + 1.0, lt, { dx: -250, dy: -260, t1: c });
  L_(V(-2, -32, 2.0), 'RUBBER MOUNTS INSIDE', b + L.sp[1] * 0.25, lt, { dx: -120, dy: 220, color: '#ffd35a', t1: c });
  L_(V(19.5, -32, 1), 'SONAR', c + 1.6, lt, { dx: 40, dy: 170, color: '#9ff3ff' });
  L_(UW.ship.position.clone().add(V(0, -2, 0)), 'SHIP', c + 2.2, lt, { dx: 40, dy: 140 });
  L_(UW.whale.position.clone().add(V(2, 1, 0)), 'WHALE', c + 2.7, lt, { dx: 60, dy: 140 });
  return UW.s;
};
SCN.food = (L, t) => {
  const lt = L.lt; const [a, b, c] = L.sg; const day = clamp((lt - c - 0.8) / (L.sp[2] + 1.0)) * 90;
  animateInterior(t, { power: 0.85, ins: 0.4, food: lt < c + 0.8 ? 1 : 1 - day / 98 });
  camKF(lt, [[0, [4, 6, 12], [0, 3.2, 0], 50], [b - 0.31, [3, 5.5, 10.5], [0, 3, 0], 50], [b - 0.3, [-34, 7.5, 17], [-40, 2, 0], 50], [b + 1.2, [-35, 7, 16], [-40, 2, 0], 50], [L.d, [-37, 5.5, 11], [-40.5, 1.7, 0], 50]], 1.25);
  if (lt < b + 0.4) { const yr = Math.round(33 * sstep(a + L.sp[0] * 0.5, a + L.sp[0], lt)); hudCounter('FUEL USED FOR', yr + ' YEARS', '#ffb43a', 70, 1420); L_(V(0, 3, 0.6), 'NO REFUELING', a + L.sp[0] * 0.65, lt, { dx: 70, dy: -200, color: '#ffb43a' }); }
  if (lt > b + 0.6 && lt < c) { hudBig('REACTOR: OK', '#b6ff5a', 1200, 64); if (lt > b + L.sp[1] * 0.7) hudBig('AIR: OK', '#b6ff5a', 1290, 64); }
  if (lt > c) { hudCounter('UNDERWATER', 'DAY ' + Math.round(day), '#ffffff', 70, 1420); L_(V(-40.5, 2.6, 1.4), 'FOOD', c + 0.4, lt, { dx: 80, dy: -220, color: '#ffb43a' }); }
  return IN.s;
};
SCN.surfacing = (L, t) => {
  const lt = L.lt, [a, b] = L.sg;
  if (lt < b - 0.4) {
    const g = UW.subG; UW.update(t, { subG: 1, bubbles: 1, bubbles2: 1, flow: 0.6 });
    const blow = sstep(a + 0.8, b - 0.6, lt); g.userData.setFill(1 - 0.95 * blow);
    g.position.set(0, lerp(-24, -12, sstep(a + 2, b, lt)), 0); g.rotation.z = 0.12 * sstep(a + 1.5, a + 4, lt); g.userData.prop.rotation.x = t * 4;
    g.updateMatrixWorld(); g.userData.setFill(1 - 0.95 * blow);
    setPts(UW.bubbles, i => { if (lt < a + 0.8) return null; const P = 1.6, age = mod(lt + i * P / 700, P); const tank = g.userData.tanks[i % 2]; const p = g.localToWorld(V(tank.cx + (hash(i) - .5) * 4, -1.9, (hash(i + 1) - .5) * 1.5)); return [p.x + Math.sin(age * 8 + i) * 0.3, p.y - 0.5 + age * 4 * (0.5 + hash(i + 3)), p.z]; });
    setPts(UW.bubbles2, i => { if (lt < a + 0.8) return null; const P = 1.0, age = mod(lt + i * P / 500, P); const tank = g.userData.tanks[i % 2]; const p = g.localToWorld(V(tank.cx + (hash(i) - .5) * 4, -1.9, 0)); return [p.x, p.y - age * 2.5, p.z + (hash(i + 2) - .5) * 1.5]; });
    const c = g.position; cam(V(c.x + 30, c.y - 6, 36), V(c.x + 2, c.y + 1, 0), 50); UW.setDepth(c.y - 4);
    L_(g.localToWorld(V(13.2, 0.6, 2)), 'HIGH-PRESSURE AIR', a + 1.0, lt, { dx: -200, dy: -200, color: '#ffffff' });
    L_(g.localToWorld(V(-9.5, -1.9, 1)), 'WATER OUT', a + 2.4, lt, { dx: -80, dy: 200, color: '#7fd0ff' });
    hudDepth(Math.max(0, -c.y * 2.7 - 4));
    return UW.s;
  }
  const st = lt - (b - 0.4); const br = 1.1;
  const y = st < br ? lerp(-9, 1.5, eout(st / br)) : lerp(1.5, -1.2, 1 - Math.exp(-(st - br) * 1.4)) + 0.6 * Math.exp(-(st - br) * 1.2) * Math.sin((st - br) * 3);
  const pitch = st < br ? lerp(0.4, 0.3, st / br) : 0.3 * Math.exp(-(st - br) * 1.5) * Math.cos((st - br) * 1.5);
  const t0 = L.st0; SF.update(t, tt => (tt - t0) * 2.0, y, pitch, st > 2.5 ? 1 : 0);
  SF.burst(t0 + (b - 0.4 - L.sg0) + br * 0.6, t, SF.sub.position.clone().add(V(10, 0, 0)));
  const c = SF.sub.position.clone(); cam(V(c.x + 40, 2.5, 40), V(c.x + 4, 2, 0), 50);
  hudDepth(Math.max(0, (-y - 1.2) * 3));
  return SF.s;
};
SCN.recap = (L, t) => {
  const lt = L.lt, [a, b] = L.sg; animateInterior(t, { power: 0.85, ins: 0.4 });
  const e0 = L.sp[0], e1 = L.sp[1];
  camKF(lt, [[0, [2, 7, 17], [1, 3, 0], 50], [a + e0 * 0.3, [5, 7, 17], [4, 3.5, 0], 50], [a + e0 * 0.55, [12, 8, 18], [11, 5, 0], 50], [a + e0 * 0.85, [17, 7, 16], [17, 4, 0], 50], [b + e1 * 0.25, [28, 6, 16], [29, 2.5, 0], 50], [b + e1 * 0.6, [34, 14, 26], [-8, 2.5, -1], 55], [L.d, [36, 16, 30], [-10, 2.5, -1], 55]]);
  L_(V(0, 2.6, 0.6), 'URANIUM', a + 0.3, lt, { dx: -70, dy: -200, color: '#ffb43a', t1: b + e1 * 0.5 });
  L_(V(3.4, 3.8, 0.3), 'HEAT', a + e0 * 0.25, lt, { dx: 50, dy: -230, color: '#ff7a3a', t1: b + e1 * 0.5 });
  L_(V(10, 8.4, 0), 'STEAM', a + e0 * 0.5, lt, { dx: 50, dy: -160, t1: b + e1 * 0.5 });
  L_(V(16, 4.6, 1.4), 'TURBINES', a + e0 * 0.78, lt, { dx: 60, dy: 200, color: '#7fd0ff', t1: b + e1 * 0.5 });
  L_(V(34.6, 2, 0.4), 'PROPELLER', b + e1 * 0.12, lt, { dx: -90, dy: -230, color: '#ffd35a', t1: b + e1 * 0.5 });
  L_(V(-20, 2.0, 0.6), 'POWER', b + e1 * 0.55, lt, { dx: -40, dy: -260, color: '#ffe04a' });
  L_(V(-40, 2.0, 0.6), 'LIFE', b + e1 * 0.7, lt, { dx: -40, dy: -320, color: '#b6ff5a' });
  return IN.s;
};
SCN.end = (L, t) => {
  const lt = L.lt; SF.update(t, tt => (tt - L.st0) * 2.2 - 10, -1.2, 0); setPts(SF.spray, () => null);
  const c = SF.sub.position.clone();
  cam(V(c.x - 34 - lt * 2, 9 + lt * 2.2, 30 + lt * 1.5), V(c.x + 4, 0, 0), 50);
  const a = sstep(0.3, 1.0, lt);
  hudBig('HOW A NUCLEAR', '#ffffff', 1060, 64, a); hudBig('SUBMARINE WORKS', '#ffb43a', 1140, 64, a);
  if (lt > 1.2) { const bl = 0.75 + 0.25 * Math.sin(lt * 5); hudBig('FOLLOW FOR MORE', '#ffffff', 1300, 52, sstep(1.2, 1.6, lt) * bl); }
  return SF.s;
};

// ---------- frame ----------
const segById = TL.segs;
window.renderFrame = (t) => {
  LBL = []; HUD = [];
  let sc = TL.scenes.find(s => t >= s.start && t < s.end) ?? TL.scenes[TL.scenes.length - 1];
  const sg = sc.segs.map(i => segById[i].start - sc.start), sp = sc.segs.map(i => segById[i].speechEnd - segById[i].start);
  const L = { lt: t - sc.start, d: sc.end - sc.start, sg, sp, st0: sc.start, sg0: 0 };
  const scene = SCN[sc.scene](L, t);
  for (const p of pipes) p.userData.tex.offset.x = -t * p.userData.speed / 0.7;
  renderer.render(scene, camera);
  ctx.imageSmoothingEnabled = false; ctx.globalAlpha = 1;
  const db = Math.min(t - sc.start + (sc.start === 0 ? 99 : 0), sc.end - t + (sc.end >= TL.total ? 99 : 0));
  const f = 1 - clamp(db / 0.32);
  if (f > 0.02) { const bs = 1 + Math.round(f * 9); tmp.width = Math.ceil(W / bs); tmp.height = Math.ceil(H / bs); tctx.imageSmoothingEnabled = false; tctx.drawImage(glc, 0, 0, tmp.width, tmp.height); ctx.drawImage(tmp, 0, 0, OW, OH); ctx.fillStyle = `rgba(0,0,0,${f * 0.55})`; ctx.fillRect(0, 0, OW, OH); }
  else ctx.drawImage(glc, 0, 0, OW, OH);
  // vignette
  ctx.fillStyle = vig; ctx.fillRect(0, 0, OW, OH);
  if (f < 0.5) { drawLabels(); HUD.forEach(h => h()); }
  ctx.fillStyle = topBand; ctx.fillRect(0, 0, OW, 560);
  drawCaption(t);
  // fade in/out
  if (t < 0.4) { ctx.fillStyle = `rgba(0,0,0,${1 - t / 0.4})`; ctx.fillRect(0, 0, OW, OH); }
  if (t > TL.total - 0.8) { ctx.fillStyle = `rgba(0,0,0,${(t - TL.total + 0.8) / 0.8})`; ctx.fillRect(0, 0, OW, OH); }
  return out.toDataURL('image/jpeg', 0.93);
};
const vig = (() => { const g = ctx.createRadialGradient(OW / 2, OH / 2, OH * 0.35, OW / 2, OH / 2, OH * 0.75); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.35)'); return g; })();
const topBand = (() => { const g = ctx.createLinearGradient(0, 0, 0, 560); g.addColorStop(0, 'rgba(0,0,0,0.45)'); g.addColorStop(0.6, 'rgba(0,0,0,0.25)'); g.addColorStop(1, 'rgba(0,0,0,0)'); return g; })();
window.ready = true;
