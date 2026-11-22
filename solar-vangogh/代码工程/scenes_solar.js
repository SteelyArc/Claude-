// "How the solar system works" — 14 Van Gogh shots, 1080x1920.
// Each shot: world drawn flat into a screen-space base through its camera -> flow strokes (angle looked up in world coords) -> overlays in world coords.
(() => {
  const { C, P, TAU } = VG;
  const W = 1080, H = 1920, E = U.ease, cl = U.clamp, lerp = U.lerp;
  const sm = (a, b, x) => { const k = cl((x - a) / (b - a)); return k * k * (3 - 2 * k); };
  const camT = (g, cam) => g.setTransform(cam.s, 0, 0, cam.s, W / 2 - cam.x * cam.s, H / 2 - cam.y * cam.s);
  const inv = (cam, x, y) => [(x - W / 2) / cam.s + cam.x, (y - H / 2) / cam.s + cam.y];
  const mixCam = (a, b, k) => ({ x: lerp(a.x, b.x, k), y: lerp(a.y, b.y, k), s: a.s * Math.pow(b.s / a.s, k) });

  const PL = {
    mercury: { c1: '#d8c8a8', c2: '#8a7a68', bands: [[-0.2, 0.1, '#b0a088'], [0.3, 0.08, '#c0b090']] },
    venus: { c1: '#fbe0a0', c2: '#d8963a', bands: [[-0.4, 0.2, '#f0c070'], [0.15, 0.2, '#e8b060']] },
    earth: { c1: '#6fb4f0', c2: '#1f4f9a', land: [[-0.3, -0.1, 0.38, 0.4], [0.35, 0.3, 0.3, -0.3], [0.1, -0.55, 0.2, 0.2]] },
    mars: { c1: '#f0885a', c2: '#a8452c', bands: [[0.1, 0.12, '#c05a38']] },
    jupiter: { c1: '#f4dcb0', c2: '#b0743a', bands: [[-0.7, 0.12, '#c98a4a'], [-0.42, 0.14, '#e8c48a'], [-0.15, 0.12, '#b8743a'], [0.1, 0.16, '#e0b070'], [0.38, 0.12, '#c07a40'], [0.6, 0.14, '#d8a070']], spot: [0.28, 0.3, 0.22] },
    saturn: { c1: '#f6e2a8', c2: '#c09a48', bands: [[-0.5, 0.14, '#e0c070'], [-0.1, 0.16, '#d0a858'], [0.3, 0.14, '#e8cc80']] },
    uranus: { c1: '#c8f0ec', c2: '#4aa8b0' },
    neptune: { c1: '#3f6cc8', c2: '#142a7a', bands: [[-0.45, 0.1, '#2f55b8'], [-0.1, 0.08, '#6f98e0'], [0.25, 0.12, '#1c348c']], spot: [-0.25, 0.15, 0.16] },
  };
  const rings = (g, x, y, r, front, rot = -0.25, cols = ['#e8d090', '#c9a050']) => {
    g.save(); g.lineCap = 'butt';
    g.lineWidth = r * 0.2; g.strokeStyle = cols[0]; g.beginPath(); g.ellipse(x, y, r * 2.05, r * 0.55, rot, front ? 0 : Math.PI, front ? Math.PI : TAU); g.stroke();
    g.lineWidth = r * 0.1; g.strokeStyle = cols[1]; g.beginPath(); g.ellipse(x, y, r * 1.62, r * 0.44, rot, front ? 0 : Math.PI, front ? Math.PI : TAU); g.stroke();
    g.restore();
  };
  const planetFull = (g, n, x, y, r, t, ringRot) => {
    if (n === 'saturn') rings(g, x, y, r, false, ringRot);
    if (n === 'uranus') rings(g, x, y, r, false, ringRot ?? 1.5, ['#d4e6f6', '#9cc3ee']);
    VG.planet(g, { x, y, r, ...PL[n] }, t);
    if (n === 'saturn') rings(g, x, y, r, true, ringRot);
    if (n === 'uranus') rings(g, x, y, r, true, ringRot ?? 1.5, ['#d4e6f6', '#9cc3ee']);
  };
  const sunBody = (g, x, y, R, t, petals = true) => {
    if (petals) for (let i = 0; i < 30; i++) {
      const a = i / 30 * TAU + t * 0.12, l = R * (1.28 + 0.1 * Math.sin(t * 2.2 + i * 1.7));
      g.fillStyle = i % 2 ? '#e8862a' : '#f5b028'; g.beginPath(); g.moveTo(x + Math.cos(a - 0.1) * R * 0.92, y + Math.sin(a - 0.1) * R * 0.92);
      g.quadraticCurveTo(x + Math.cos(a + 0.12) * l, y + Math.sin(a + 0.12) * l, x + Math.cos(a + 0.12) * R * 0.92, y + Math.sin(a + 0.12) * R * 0.92); g.fill();
    }
    VG.disc(g, x, y, R, '#fff2b0', '#f0a830', [0, 0]);
    VG.spiral(g, x, y, R * 0.78, t * 0.5, { cols: ['#f8d040', '#fff2b0', '#e8a030'], lw: Math.max(8, R * 0.08), sq: 1 });
  };
  const nightFill = (g, x0, y0, x1, y1, top = '#101b58', bot = '#3a66c4') => {
    const sg = g.createLinearGradient(0, y0, 0, y1); sg.addColorStop(0, top); sg.addColorStop(0.6, '#24409e'); sg.addColorStop(1, bot); g.fillStyle = sg; g.fillRect(x0, y0, x1 - x0, y1 - y0);
  };
  const starsDraw = (c, list, t) => list.forEach(([x, y, r], k) => VG.star(c, x, y, r, t, k));
  const randStars = (seed, n, x0, y0, x1, y1) => { const r = U.rng(seed); return Array.from({ length: n }, () => [x0 + r() * (x1 - x0), y0 + r() * (y1 - y0), 7 + r() * 7]); };
  const arrow = (c, x0, y0, x1, y1, col, lw, k = 1) => {
    if (k <= 0) return; const x = lerp(x0, x1, k), y = lerp(y0, y1, k), a = Math.atan2(y - y0, x - x0);
    c.save(); c.lineCap = 'round'; c.lineJoin = 'round';
    for (const [cc, ww] of [[C.line, lw + 8], [col, lw]]) {
      c.strokeStyle = cc; c.lineWidth = ww; c.beginPath(); c.moveTo(x0, y0); c.lineTo(x, y);
      c.moveTo(x + Math.cos(a + 2.6) * lw * 3.2, y + Math.sin(a + 2.6) * lw * 3.2); c.lineTo(x, y); c.lineTo(x + Math.cos(a - 2.6) * lw * 3.2, y + Math.sin(a - 2.6) * lw * 3.2); c.stroke();
    }
    c.restore();
  };
  // painted label inside the world (counts as an object, not a caption)
  const label = (c, text, x, y, size, col = '#f6edc8', rot = -0.04) => {
    c.save(); c.translate(x, y); c.rotate(rot); c.font = `${size}px "LilitaOne-400"`; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.lineJoin = 'round'; c.strokeStyle = C.line; c.lineWidth = size * 0.22; c.strokeText(text, 0, 0); c.fillStyle = col; c.fillText(text, 0, 0); c.restore();
  };

  // generic shot runner
  const shot = ({ cam, base, angle, over, seed = 3, cell = 11, len = 34, width = 7.5, detail }) => ({
    draw(c, lt, t) {
      const cm = cam(lt), b = P.scratch('solarBase'), g = b.getContext('2d');
      g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H); camT(g, cm); base(g, lt, t, cm); g.setTransform(1, 0, 0, 1, 0, 0);
      c.drawImage(b, 0, 0);
      VG.paint(c, b, (x, y) => angle(...inv(cm, x, y), t, lt), t, [{ cell, len: len * Math.min(1.25, Math.max(0.8, Math.sqrt(cm.s))), width, seed }]);
      if (detail) VG.paint(c, b, (x, y) => (detail.angle ? detail.angle(...inv(cm, x, y), t, lt) : 0), t,
        [{ cell: 6, len: 12, width: 4, seed: seed + 50, outline: 0.5, mask: (x, y) => detail.mask(...inv(cm, x, y), t, lt) }]);
      c.save(); camT(c, cm); over(c, lt, t, cm); c.restore();
    },
  });

  // ================= HILL WORLD (s01–s04, s14) =================
  const HW = (() => {
    const SUN = [540, -760], SQ = 0.42, ORB = [190, 285, 385, 490];
    const plan = [['mercury', 16, 2.1], ['venus', 24, 1.5], ['earth', 28, 1.1], ['jupiter', 58, 0.45]];
    const ppos = (k, t) => { const a = 0.8 + k * 1.7 + t * plan[k][2] * 0.6; return [SUN[0] + Math.cos(a) * ORB[k], SUN[1] + Math.sin(a) * ORB[k] * SQ]; };
    const swirls = [[180, -1350, 130, 0.85, -1], [930, -1420, 95, 0.85, 1], [900, 120, 100, 0.85, 1], [170, 330, 115, 0.85, -1], [880, -150, 70, 0.85, -1]];
    const stars = randStars(11, 26, 0, -1800, W, 1100).filter(([x, y]) => Math.hypot(x - SUN[0], (y - SUN[1]) / SQ) > 560);
    const O = [600, 1600], FS = 1.8, fp = (dx, dy) => [O[0] + dx * FS, O[1] + dy * FS];
    const HAND = fp(60, -232), HEAD = fp(0, -136);
    const cypress = [[60, 2050], [40, 1700], [95, 1300], [130, 900], [160, 1300], [230, 1700], [215, 2050]];
    const hillPath = g => { g.beginPath(); g.moveTo(-400, 1720); g.bezierCurveTo(200, 1600, 450, 1560, 640, 1590); g.bezierCurveTo(820, 1610, 1000, 1660, 1500, 1720); g.lineTo(1500, 2600); g.lineTo(-400, 2600); g.closePath(); };
    function base(g, t, st = {}) {
      nightFill(g, -600, -2000, 1700, 1700);
      ORB.forEach((rx, k) => { g.strokeStyle = k % 2 ? '#8fb6ee' : '#cfe3f6'; g.lineWidth = 16; g.beginPath(); g.ellipse(SUN[0], SUN[1], rx, rx * SQ, 0, 0, TAU); g.stroke(); });
      swirls.forEach(([x, y, r, , d]) => VG.spiral(g, x, y, r, t, { dir: d }));
      sunBody(g, SUN[0], SUN[1], 150, t, false);
      plan.forEach(([n, r], k) => { const [x, y] = ppos(k, t); VG.planet(g, { x, y, r, ...PL[n] }, t); });
      // village lights strip beyond the hill
      g.fillStyle = '#1c2f6a'; g.beginPath(); g.moveTo(-400, 1690); for (let x = -400; x <= 1500; x += 60) g.lineTo(x, 1640 + ((x / 60) % 3) * 14); g.lineTo(1500, 1760); g.lineTo(-400, 1760); g.fill();
      g.fillStyle = '#2e6a4a'; hillPath(g); g.fill();
      g.fillStyle = '#1f5a36'; g.fillRect(-400, 1900, 1900, 700);
      g.fillStyle = '#163c28'; g.beginPath(); cypress.forEach((p, i) => i ? g.lineTo(...p) : g.moveTo(...p)); g.closePath(); g.fill();
      figure(g, t, st);
    }
    function figure(g, t, st) {
      const sh = st.shake ? Math.sin(t * 60) * st.shake : 0;
      g.save(); g.translate(O[0] + sh, O[1]); g.scale(FS, FS);
      g.fillStyle = '#16267a'; g.beginPath(); g.moveTo(-38, -107); g.lineTo(37, -107); g.lineTo(58, 0); g.lineTo(-56, 0); g.closePath(); g.fill();
      g.strokeStyle = '#16267a'; g.lineWidth = 24; g.lineCap = 'round';
      const hy = st.armDown ? -150 : -232, hx = st.armDown ? 70 : 60;
      g.beginPath(); g.moveTo(27, -90); g.lineTo(hx, hy); g.stroke(); g.beginPath(); g.moveTo(-28, -90); g.lineTo(-56, -22); g.stroke();
      g.strokeStyle = '#111a46'; g.lineWidth = 15; g.beginPath(); g.moveTo(-22, 0); g.lineTo(-26, 40); g.moveTo(26, 0); g.lineTo(32, 40); g.stroke();
      // head (back of head: orange-brown hair) + straw hat, hat squashes on BONK
      g.fillStyle = '#a8452c'; g.beginPath(); g.arc(0, -128, 24, 0, TAU); g.fill();
      const sq = st.squash || 0;
      g.save(); g.translate(0, -140); g.scale(1 + sq * 0.35, 1 - sq * 0.45);
      g.fillStyle = '#e6b84a'; g.beginPath(); g.ellipse(0, 4, 58, 13, 0, 0, TAU); g.fill();
      g.beginPath(); g.arc(0, -6, 28, Math.PI, TAU); g.lineTo(28, 2); g.lineTo(-28, 2); g.fill();
      g.fillStyle = '#1c348c'; g.fillRect(-28, -6, 56, 7);
      g.restore(); g.restore();
    }
    const figOutline = (c, t, st = {}) => {
      const sh = st.shake ? Math.sin(t * 60) * st.shake : 0, q = (x, y) => [O[0] + sh + x * FS, O[1] + y * FS];
      VG.outline(c, [q(-38, -107), q(37, -107), q(58, 0), q(-56, 0)], t, { seed: 6 });
      c.save(); c.strokeStyle = C.line; c.lineWidth = 4; c.lineCap = 'round'; c.beginPath(); c.moveTo(...q(27, -90)); c.lineTo(...q(60, -232)); c.stroke(); c.restore();
      const sq = st.squash || 0;
      VG.outline(c, VG.circlePts(O[0] + sh, O[1] + (-136 + 4 * (1 - sq * 0.45)) * FS, 58 * FS * (1 + sq * 0.35), 22, 0.22 * (1 - sq * 0.45) / (1 + sq * 0.35)), t, { seed: 8, lw: 4 });
    };
    const angle = (x, y, t) => {
      if (x > 30 && x < 240 && y > 880 && y < 2050 && Math.abs(x - 135) < 110 * (1 - Math.abs(y - 1700) / 1100)) return -Math.PI / 2 + 0.3 * Math.sin(y * 0.02 + t * 2);
      if (y > 1570) return 0.15 * Math.sin(x * 0.01 + t) + (y > 1900 ? 0 : -0.08);
      const d = Math.hypot(x - SUN[0], (y - SUN[1]) / SQ);
      if (d < 150) return VG.tangent(x, y, SUN[0], SUN[1]) + t * 0.4;
      if (d < 560) return VG.tangent(x, y, SUN[0], SUN[1], 1, SQ) + 0.1 * Math.sin(d * 0.05 - t);
      return VG.skyAngle(x, y, t, swirls);
    };
    const detMask = (x, y, t) => (Math.abs(x - O[0]) < 130 && y > O[1] - 330 && y < O[1] + 80) || plan.some(([, r], k) => { const [px, py] = ppos(k, t); return Math.hypot(x - px, y - py) < r; });
    const detAngle = (x, y) => (Math.abs(x - O[0]) < 130 && y > O[1] - 230) ? -Math.PI / 2 : 0;
    const skyOver = (c, t) => {
      VG.outline(c, cypress, t, { seed: 4 });
      VG.outline(c, VG.circlePts(SUN[0], SUN[1], 150), t, { seed: 7 });
      plan.forEach(([, r], k) => { const [x, y] = ppos(k, t); VG.outline(c, VG.circlePts(x, y, r, 20), t, { seed: 10 + k, lw: 3.5 }); });
      VG.halo(c, SUN[0], SUN[1], 150, 300, t);
      starsDraw(c, stars, t);
    };
    const lantern = (c, x, y, t, hx = HAND[0], hy = HAND[1], string = true) => {
      if (string) { c.strokeStyle = '#f6edc8'; c.lineWidth = 3.5; c.beginPath(); c.moveTo(hx, hy); c.lineTo(x, y); c.stroke(); }
      VG.star(c, x, y, 26, t, 1);
      c.fillStyle = '#e8862a'; c.strokeStyle = C.line; c.lineWidth = 4; c.beginPath(); c.rect(x - 15, y - 17, 30, 34); c.fill(); c.stroke();
      c.fillStyle = '#fbe58a'; c.fillRect(x - 8, y - 10, 16, 20);
    };
    const swing = (a, rad = 120) => [HAND[0] + Math.cos(a) * rad, HAND[1] + Math.sin(a) * rad * 0.55];
    return { SUN, O, FS, HAND, HEAD, base, angle, detMask, detAngle, skyOver, figOutline, lantern, swing, stars };
  })();
  const CLOSE = { x: 560, y: 1290, s: 1.18 };
  const hillShot = (camFn, over, stFn = () => ({}), seed = 3) => shot({
    cam: camFn, seed,
    base: (g, lt, t) => HW.base(g, t, stFn(lt)),
    angle: HW.angle,
    detail: { mask: HW.detMask, angle: HW.detAngle },
    over: (c, lt, t, cm) => { HW.skyOver(c, t); HW.figOutline(c, t, stFn(lt)); over(c, lt, t, cm); },
  });

  // s01 — swinging the lantern
  SCENES.s01 = hillShot(lt => ({ x: CLOSE.x, y: CLOSE.y + 20 * Math.sin(lt * 0.6), s: CLOSE.s }), (c, lt, t) => {
    const [x, y] = HW.swing(lt * 3.6); HW.lantern(c, x, y, t);
  });
  // s02 — the string snaps, lantern flies off and becomes a star
  SCENES.s02 = hillShot(lt => mixCam(CLOSE, { x: 760, y: 820, s: 0.9 }, E.inOut(sm(0.85, 2.6, lt))), (c, lt, t) => {
    const TS = 0.8, a0 = TS * 3.6;
    if (lt < TS) { const [x, y] = HW.swing(lt * 3.6); HW.lantern(c, x, y, t); return; }
    const [x0, y0] = HW.swing(a0), vx = -Math.sin(a0) * 120 * 3.6, vy = Math.cos(a0) * 120 * 0.55 * 3.6;
    const k = lt - TS, x = x0 + vx * k * 0.9 + 180 * k * k, y = y0 + vy * k * 0.5 - 260 * k * k;
    const sc = Math.max(0.15, 1 - k * 0.3);
    // broken string stub dangles from the hand
    c.strokeStyle = '#f6edc8'; c.lineWidth = 3.5; c.beginPath(); c.moveTo(...HW.HAND); c.lineTo(HW.HAND[0] + 10 * Math.sin(lt * 9), HW.HAND[1] + 40); c.stroke();
    c.save(); c.translate(x, y); c.scale(sc, sc); c.rotate(k * 4); HW.lantern(c, 0, 0, t, 0, 0, false); c.restore();
    if (k > 2.3) { const p = cl((k - 2.3) / 0.4); c.save(); c.globalAlpha = p; VG.star(c, x, y, 30, t, 4); c.restore(); }
    // snap sparks
    if (k < 0.4) { c.save(); c.strokeStyle = '#fbe58a'; c.lineWidth = 5; c.lineCap = 'round'; for (let i = 0; i < 6; i++) { const a = i / 6 * TAU, r0 = 20 + k * 200; c.beginPath(); c.moveTo(x0 + Math.cos(a) * r0, y0 + Math.sin(a) * r0); c.lineTo(x0 + Math.cos(a) * (r0 + 30), y0 + Math.sin(a) * (r0 + 30)); c.stroke(); } c.restore(); }
  }, () => ({}), 5);
  // s03 — stop swinging: BONK
  const TD = 1.25, TI = 1.95;   // slow-down end, impact
  const s03st = lt => { const k = lt - TI; return k < 0 ? {} : { squash: Math.max(0, Math.exp(-k * 3) * Math.cos(k * 14)) * 0.9 + 0.05 * Math.max(0, 1 - k), shake: k < 0.35 ? 8 * (1 - k / 0.35) : 0 }; };
  SCENES.s03 = hillShot(lt => {
    const k = lt - TI, base = { x: CLOSE.x, y: CLOSE.y - 40, s: CLOSE.s };
    if (k < 0) return base;
    const push = { x: HW.HEAD[0], y: HW.HEAD[1] + 40, s: 1.75 }, kk = sm(0, 0.18, k);         // snap-in on impact
    const cm = mixCam(base, push, kk); cm.x += Math.sin(k * 70) * 10 * Math.max(0, 1 - k * 2.5); return cm;
  }, (c, lt, t) => {
    if (lt < TD) { const w = 3.6 * (1 - lt / TD * 0.85), a = lt * 3.6 - 0.5 * lt * lt / TD * 3.6 * 0.85; const [x, y] = HW.swing(a, 120 * (1 - lt / TD * 0.6)); HW.lantern(c, x, y, t); return; }
    const [sx, sy] = HW.swing(TD * 3.6 - 0.5 * TD * 3.6 * 0.85, 48);
    const hx = HW.HEAD[0], hy = HW.HEAD[1] - 60;
    if (lt < TI) { const k = (lt - TD) / (TI - TD), e = k * k; HW.lantern(c, lerp(sx, hx, k), lerp(sy - 40 * Math.sin(k * Math.PI), hy, e), t); return; }
    const k = lt - TI;
    HW.lantern(c, hx + 6 * Math.sin(k * 5), hy - 8, t);
    for (let i = 0; i < 3; i++) { const a = k * 5 + i * TAU / 3; VG.star(c, hx + Math.cos(a) * 120, hy - 70 + Math.sin(a) * 30, 14, t, i); }
    if (k < 1.2) label(c, 'BONK!', hx + 40, hy - 200, 110 * (0.6 + 0.4 * E.out(cl(k / 0.15))), '#f5c518', 0.2);
  }, s03st, 7);
  // s04 — tilt up: planets do the same trick (string = gravity)
  SCENES.s04 = hillShot(lt => mixCam({ x: CLOSE.x, y: CLOSE.y - 40, s: CLOSE.s }, { x: 540, y: -660, s: 1.0 }, E.inOut(sm(0, 3.0, lt))), (c, lt, t) => {
    const [x, y] = HW.swing(lt * 3.6); HW.lantern(c, x, y, t);
    // gravity "strings" from the Sun to each planet light up
    const k = sm(2.6, 3.4, lt);
    if (k > 0) {
      c.save(); c.globalAlpha = k; c.setLineDash([16, 14]); c.lineDashOffset = -t * 40; c.lineWidth = 5; c.strokeStyle = '#fbe58a';
      [0, 1, 2, 3].forEach(i => { const p = [[16, 2.1], [24, 1.5], [28, 1.1], [58, 0.45]][i]; const a = 0.8 + i * 1.7 + t * p[1] * 0.6, rx = [190, 285, 385, 490][i];
        c.beginPath(); c.moveTo(HW.SUN[0], HW.SUN[1]); c.lineTo(HW.SUN[0] + Math.cos(a) * rx, HW.SUN[1] + Math.sin(a) * rx * 0.42); c.stroke(); });
      c.restore();
    }
  }, () => ({}), 9);

  // ================= s05 — The Sun, close =================
  SCENES.s05 = (() => {
    const S = [540, 860], R = 430, sw = [[150, 120, 110, 0.85, -1], [960, 1650, 120, 0.85, 1], [120, 1720, 90, 0.85, 1]];
    return shot({
      seed: 13,
      cam: lt => ({ x: 540, y: 960 - lt * 12, s: 1.0 + lt * 0.03 }),
      base: (g, lt, t) => { nightFill(g, -200, -200, 1300, 2200, '#132063', '#2a52b2'); sw.forEach(([x, y, r, , d]) => VG.spiral(g, x, y, r, t, { dir: d })); sunBody(g, S[0], S[1], R, t);
        if (lt > 2.5) VG.planet(g, { x: 880, y: 1520, r: 13, ...PL.earth }, t); },
      angle: (x, y, t) => { const d = Math.hypot(x - S[0], y - S[1]); if (d < R) return VG.tangent(x, y, S[0], S[1]) + t * 0.3; if (d < R * 1.45) return Math.atan2(y - S[1], x - S[0]) + 0.25 * Math.sin(d * 0.04 - t * 2); return VG.skyAngle(x, y, t, sw.concat([[S[0], S[1], R * 2, 1, 1]])); },
      over: (c, lt, t) => {
        VG.outline(c, VG.circlePts(S[0], S[1], R, 44), t, { seed: 3, lw: 6 }); VG.halo(c, S[0], S[1], R, R * 1.6, t, { lw: 22, a: 0.22 });
        starsDraw(c, [[90, 360, 10], [1000, 260, 12], [980, 1200, 9], [70, 1300, 10]], t);
        if (lt > 2.5) { const k = E.out(cl((lt - 2.5) / 0.3)); VG.outline(c, VG.circlePts(880, 1520, 13, 12), t, { lw: 3 }); arrow(c, 760, 1700, 862, 1545, '#f6edc8', 7, k); label(c, 'you are here', 640, 1745, 52 * k, '#f6edc8', -0.08); }
      },
    });
  })();

  // ================= s06 — Earth falls and keeps missing =================
  SCENES.s06 = (() => {
    const S = [1350, -250], R = 520, ORR = 1500;    // Sun off the top-right corner; Earth on a big circle
    const ea = lt => 2.05 - lt * 0.1;                 // angle along orbit
    const epos = lt => [S[0] + Math.cos(ea(lt)) * ORR, S[1] + Math.sin(ea(lt)) * ORR];
    return shot({
      seed: 17,
      cam: lt => { const [x, y] = epos(lt); return { x: x + 120, y: y - 260, s: 1.0 }; },
      base: (g, lt, t) => {
        nightFill(g, -1500, -1500, 2500, 2500, '#132063', '#2a52b2');
        g.strokeStyle = '#9cc3ee'; g.lineWidth = 14; g.beginPath(); g.arc(S[0], S[1], ORR, 1.2, 2.6); g.stroke();
        sunBody(g, S[0], S[1], R, t);
        const [x, y] = epos(lt); VG.planet(g, { x, y, r: 120, ...PL.earth }, t);
      },
      angle: (x, y, t) => { const d = Math.hypot(x - S[0], y - S[1]); if (d < R) return VG.tangent(x, y, S[0], S[1]) + t * 0.3; if (d < R * 1.4) return Math.atan2(y - S[1], x - S[0]); return VG.tangent(x, y, S[0], S[1]) + 0.15 * Math.sin(d * 0.02 - t * 1.5); },
      detail: { mask: (x, y, t, lt) => { const [ex, ey] = epos(lt); return Math.hypot(x - ex, y - ey) < 120; } },
      over: (c, lt, t) => {
        const [x, y] = epos(lt), a = ea(lt);
        VG.outline(c, VG.circlePts(x, y, 120, 26), t, { seed: 9 });
        VG.outline(c, VG.circlePts(S[0], S[1], R, 44), t, { seed: 2, lw: 6 });
        const toSun = [Math.cos(a + Math.PI), Math.sin(a + Math.PI)], side = [Math.sin(a), -Math.cos(a)];
        // beat 1: fall arrow towards the Sun
        arrow(c, x + toSun[0] * 140, y + toSun[1] * 140, x + toSun[0] * 360, y + toSun[1] * 360, '#e8862a', 14, E.out(cl(lt / 0.5)));
        if (lt < 2.3) label(c, 'FALL', x + toSun[0] * 300 + 90, y + toSun[1] * 300 + 40, 64, '#e8862a', -0.1);
        // beat 2: sideways arrow + the would-be straight line + the real curved path
        const k2 = E.out(cl((lt - 2.3) / 0.5));
        if (k2 > 0) {
          c.save(); c.setLineDash([18, 16]); c.lineWidth = 6; c.strokeStyle = 'rgba(246,237,200,.8)'; c.beginPath(); c.moveTo(x, y); c.lineTo(x + side[0] * 900 * k2, y + side[1] * 900 * k2); c.stroke();
          c.strokeStyle = '#f5c518'; c.lineWidth = 8; c.beginPath(); c.arc(S[0], S[1], ORR, a - 0.5 * k2, a, false); c.stroke(); c.restore();
          arrow(c, x + side[0] * 140, y + side[1] * 140, x + side[0] * 380, y + side[1] * 380, '#f6edc8', 14, k2);
          label(c, 'MISS', x + side[0] * 330 - 40, y + side[1] * 330 + 100, 64 * k2, '#f6edc8', 0.08);
        }
        // beat 3: speed lines
        const k3 = cl((lt - 4.5) / 0.4);
        if (k3 > 0) { c.save(); c.lineCap = 'round'; for (let i = 0; i < 9; i++) { const o = (i - 4) * 30, ph = (t * 3 + i * 0.37) % 1; c.strokeStyle = `rgba(246,237,200,${0.8 * k3 * (1 - ph)})`; c.lineWidth = 6;
          const bx = x - side[0] * (150 + ph * 300) + Math.cos(a) * o, by = y - side[1] * (150 + ph * 300) + Math.sin(a) * o; c.beginPath(); c.moveTo(bx, by); c.lineTo(bx - side[0] * 120, by - side[1] * 120); c.stroke(); } c.restore();
          label(c, '30 km/s', x - 20, y + 210, 72 * E.out(k3), '#f5c518', -0.06); }
      },
    });
  })();

  // ================= s07 — Mercury laps, Venus bakes (top-down) =================
  SCENES.s07 = (() => {
    const S = [540, 780], SQ = 0.62, OR = [['mercury', 170, 20, TAU / 1.6], ['venus', 270, 34, TAU / 5], ['earth', 370, 34, TAU / 9]];
    const pos = (k, lt) => { const [, rx, , w] = OR[k]; const a = [0.3, 2.2, 3.8][k] + lt * w; return [S[0] + Math.cos(a) * rx, S[1] + Math.sin(a) * rx * SQ]; };
    const sw = [[170, 1500, 110, 0.85, -1], [930, 1580, 90, 0.85, 1]];
    return shot({
      seed: 19, cam: lt => ({ x: 540, y: 900, s: 1.0 }),
      base: (g, lt, t) => {
        nightFill(g, 0, 0, W, H, '#132063', '#2a52b2'); sw.forEach(([x, y, r, , d]) => VG.spiral(g, x, y, r, t, { dir: d }));
        OR.forEach(([, rx], k) => { g.strokeStyle = k % 2 ? '#8fb6ee' : '#cfe3f6'; g.lineWidth = 12; g.beginPath(); g.ellipse(S[0], S[1], rx, rx * SQ, 0, 0, TAU); g.stroke(); });
        sunBody(g, S[0], S[1], 100, t);
        OR.forEach(([n, , r], k) => { const [x, y] = pos(k, lt); VG.planet(g, { x, y, r: n === 'venus' && lt > 2.5 ? r * 1.25 : r, ...PL[n] }, t); });
      },
      angle: (x, y, t) => { const d = Math.hypot(x - S[0], (y - S[1]) / SQ); if (d < 100) return VG.tangent(x, y, S[0], S[1]) + t * 0.5; if (d < 470) return VG.tangent(x, y, S[0], S[1], 1, SQ) + 0.12 * Math.sin(d * 0.04 - t); return VG.skyAngle(x, y, t, sw); },
      detail: { mask: (x, y, t, lt) => OR.some(([, , r], k) => { const [px, py] = pos(k, lt); return Math.hypot(x - px, y - py) < r * 1.3; }) },
      over: (c, lt, t) => {
        VG.outline(c, VG.circlePts(S[0], S[1], 100), t, { seed: 1 });
        OR.forEach(([n, , r], k) => { const [x, y] = pos(k, lt); VG.outline(c, VG.circlePts(x, y, n === 'venus' && lt > 2.5 ? r * 1.25 : r, 18), t, { seed: 30 + k, lw: 3.5 }); });
        // Mercury trail + lap counter painted beside it
        const [mx, my] = pos(0, lt);
        for (let i = 1; i < 10; i++) { const [px, py] = pos(0, lt - i * 0.035); c.fillStyle = `rgba(232,220,190,${0.5 - i * 0.05})`; c.beginPath(); c.arc(px, py, 18 - i, 0, TAU); c.fill(); }
        if (lt < 2.6) label(c, `${1 + Math.floor(lt / 1.6)} yr`, mx, my - 60, 46, '#f6edc8');
        // Venus heat
        if (lt > 2.5) { const [vx, vy] = pos(1, lt), k = cl((lt - 2.5) / 0.3); VG.halo(c, vx, vy, 40, 120, t, { col: '240,120,40', a: 0.5 * k, lw: 12, speed: 1.6 });
          c.save(); c.strokeStyle = `rgba(232,134,42,${k})`; c.lineWidth = 6; c.lineCap = 'round'; for (let i = -1; i <= 1; i++) { c.beginPath(); for (let s = 0; s <= 12; s++) { const yy = vy - 60 - s * 9, xx = vx + i * 26 + Math.sin(s * 0.8 - t * 8 + i) * 8; s ? c.lineTo(xx, yy) : c.moveTo(xx, yy); } c.stroke(); } c.restore();
          label(c, '465°C', vx, vy + 85, 56 * E.out(k), '#e8862a', 0.05); }
      },
    });
  })();

  // ================= s08 — asteroid belt pan =================
  SCENES.s08 = (() => {
    const rocks = (() => { const r = U.rng(21); return Array.from({ length: 70 }, () => ({ x: r() * 3200 - 400, y: 500 + r() * 1100 + (r() - 0.5) * 300, r: 22 + r() * r() * 110, sp: (r() - 0.5) * 1.6, ph: r() * TAU, col: r() < 0.5 ? '#c9962e' : r() < 0.5 ? '#e6b84a' : '#a8452c', n: 7 + (r() * 4 | 0), j: Array.from({ length: 11 }, () => 0.75 + r() * 0.45) })); })();
    const shape = (k, q, lt) => Array.from({ length: k.n }, (_, i) => { const a = i / k.n * TAU + k.ph + lt * k.sp; return [k.x + Math.cos(a) * k.r * k.j[i], k.y + Math.sin(a) * k.r * k.j[i] * 0.85]; });
    const sw = [[300, 200, 120, 0.85, 1], [1400, 1750, 140, 0.85, -1], [2300, 250, 110, 0.85, -1]];
    return shot({
      seed: 23, cam: lt => ({ x: 540 + E.inOut(cl(lt / 4)) * 1200, y: 960, s: 1.0 }),
      base: (g, lt, t) => { nightFill(g, -400, 0, 3000, H, '#101b58', '#2a52b2'); sw.forEach(([x, y, r, , d]) => VG.spiral(g, x, y, r, t, { dir: d }));
        rocks.forEach(k => { const p = shape(k, 0, lt); g.fillStyle = k.col; g.beginPath(); p.forEach((q, i) => i ? g.lineTo(...q) : g.moveTo(...q)); g.closePath(); g.fill(); g.fillStyle = 'rgba(20,30,80,.35)'; g.beginPath(); g.arc(k.x + k.r * 0.25, k.y + k.r * 0.2, k.r * 0.35, 0, TAU); g.fill(); }); },
      angle: (x, y, t, lt) => { for (const k of rocks) if (Math.hypot(x - k.x, y - k.y) < k.r) return k.ph + lt * k.sp; return 0.35 * Math.sin(x * 0.004 + t * 0.7) + VG.skyAngle(x, y, t, sw) * 0.5; },
      over: (c, lt, t) => { rocks.forEach((k, i) => VG.outline(c, shape(k, 0, lt), t, { seed: i, lw: 4, amp: 1.6 })); starsDraw(c, [[200, 1700, 10], [900, 300, 12], [1700, 260, 9], [2100, 1500, 11]], t); },
    });
  })();

  // ================= s09 — Jupiter: snap zoom to the Great Red Spot, Earth pops in for scale =================
  SCENES.s09 = (() => {
    const J = [540, 960], R = 760, SP = [J[0] + 0.28 * R, J[1] + 0.3 * R];
    const EP = [SP[0] - 40, SP[1] - 330];
    return shot({
      seed: 29,
      cam: lt => mixCam({ x: 540, y: 960, s: 0.62 }, { x: SP[0] - 20, y: SP[1] - 120, s: 1.45 }, E.out(sm(0.45, 0.95, lt))),
      base: (g, lt, t) => { nightFill(g, -1500, -1800, 2600, 3800, '#101b58', '#24409e'); VG.planet(g, { x: J[0], y: J[1], r: R, ...PL.jupiter }, t * 0.6);
        if (lt > 2.5) VG.planet(g, { x: EP[0], y: EP[1], r: 120 * E.out(cl((lt - 2.5) / 0.25)), ...PL.earth }, t); },
      angle: (x, y, t) => { const ds = Math.hypot(x - SP[0], (y - SP[1]) / 0.6); if (ds < 0.24 * R) return VG.tangent(x, y, SP[0], SP[1], 1, 0.6) + t * 0.8; if (Math.hypot(x - J[0], y - J[1]) < R) return 0.12 * Math.sin(x * 0.01 + y * 0.03 + t); return VG.skyAngle(x, y, t, []); },
      over: (c, lt, t) => {
        VG.outline(c, VG.circlePts(J[0], J[1], R, 60), t, { seed: 5, lw: 7 });
        if (lt > 2.5) { const k = E.out(cl((lt - 2.5) / 0.25)); VG.outline(c, VG.circlePts(EP[0], EP[1], 120 * k, 22), t, { seed: 6 }); label(c, 'Earth', EP[0] + 190, EP[1] - 120, 62 * k, '#f6edc8', -0.1); arrow(c, EP[0] + 150, EP[1] - 80, EP[0] + 90, EP[1] - 40, '#f6edc8', 8, k); }
      },
    });
  })();

  // ================= s10 — Saturn floating in a bathtub =================
  SCENES.s10 = (() => {
    const WL = 1260;   // water line
    const sat = lt => [540, WL - 120 + Math.sin(lt * 2.4) * 22 + (lt > 2.3 ? -40 * Math.exp(-(lt - 2.3) * 3) * Math.cos((lt - 2.3) * 12) : 0)];
    const sw = [[200, 260, 110, 0.85, -1], [900, 420, 90, 0.85, 1]];
    const tub = g => { g.beginPath(); g.moveTo(40, WL - 30); g.lineTo(1040, WL - 30); g.lineTo(1000, 1650); g.quadraticCurveTo(980, 1760, 860, 1760); g.lineTo(220, 1760); g.quadraticCurveTo(100, 1760, 80, 1650); g.closePath(); };
    return shot({
      seed: 31, cam: lt => ({ x: 540, y: 1000, s: 1.0 }),
      base: (g, lt, t) => {
        nightFill(g, 0, 0, W, H, '#132063', '#2a52b2'); sw.forEach(([x, y, r, , d]) => VG.spiral(g, x, y, r, t, { dir: d }));
        g.fillStyle = '#e6b84a'; [[150, 1700], [930, 1700]].forEach(([x, y]) => { g.beginPath(); g.ellipse(x, y + 90, 40, 70, 0, 0, TAU); g.fill(); });    // claw feet
        g.fillStyle = '#f6edc8'; tub(g); g.fill();
        const [x, y] = sat(lt); planetFull(g, 'saturn', x, y, 230, t, -0.22 + Math.sin(lt * 2.4) * 0.05);
        // water (painted over the lower part of Saturn = floating)
        g.save(); tub(g); g.clip(); g.fillStyle = '#3f95dc'; g.beginPath(); g.moveTo(0, WL);
        for (let xx = 0; xx <= W; xx += 30) g.lineTo(xx, WL + Math.sin(xx * 0.02 + lt * 3) * 12); g.lineTo(W, H); g.lineTo(0, H); g.fill();
        g.fillStyle = 'rgba(28,52,140,.35)'; g.fillRect(0, WL + 120, W, 700); g.restore();
        g.fillStyle = '#f6edc8'; g.fillRect(20, WL - 50, 1040, 40);   // tub rim
      },
      angle: (x, y, t, lt) => { const [sx, sy] = sat(lt);
        if (y > WL - 20 && y < 1780 && x > 40 && x < 1040) return y < WL + 30 ? 0.1 * Math.sin(x * 0.02 + t * 3) : 0.35 * Math.sin(x * 0.012 + y * 0.01 + t * 2);
        if (Math.hypot(x - sx, y - sy) < 230) return -0.22; if (Math.abs((y - sy) - (x - sx) * -0.22) < 70 && Math.abs(x - sx) < 480) return -0.22;
        return VG.skyAngle(x, y, t, sw); },
      detail: { mask: (x, y, t, lt) => { const [sx, sy] = sat(lt); return Math.hypot(x - sx, y - sy) < 230 && y < WL; }, angle: () => -0.22 },
      over: (c, lt, t) => {
        const [x, y] = sat(lt);
        VG.outline(c, [[40, WL - 50], [1060, WL - 50], [1060, WL - 10], [1000, 1650], [860, 1760], [220, 1760], [80, 1650], [20, WL - 10], [20, WL - 50]], t, { seed: 3, closed: false });
        // splash droplets when it bobs back down
        if (lt > 2.3 && lt < 3.4) { const k = lt - 2.3; for (let i = 0; i < 9; i++) { const a = -Math.PI / 2 + (i - 4) * 0.28, v = 520 + (i % 3) * 120; const dx = x + Math.cos(a) * v * k * 0.8 + (i - 4) * 40, dy = WL - 10 + Math.sin(a) * v * k + 900 * k * k;
          if (dy < WL + 10) { c.fillStyle = '#9cc3ee'; c.strokeStyle = C.line; c.lineWidth = 3; c.beginPath(); c.arc(dx, dy, 14, 0, TAU); c.fill(); c.stroke(); } } }
        // rubber-duck-sized bubbles
        for (let i = 0; i < 6; i++) { const ph = (t * 0.5 + i / 6) % 1, bx = 160 + i * 150, by = WL + 380 - ph * 380; c.strokeStyle = `rgba(214,230,246,${1 - ph})`; c.lineWidth = 4; c.beginPath(); c.arc(bx + Math.sin(t * 3 + i) * 12, by, 12 + i % 3 * 5, 0, TAU); c.stroke(); }
        label(c, 'density 0.69', x - 10, y - 330, 50, '#f6edc8', -0.05);
      },
    });
  })();

  // ================= s11 — Uranus rolls by on its side =================
  SCENES.s11 = (() => {
    const R = 260, upos = lt => [lt < 0.8 ? lerp(-300, 540, E.out(lt / 0.8)) : lt < 2.2 ? 540 + 34 * Math.sin((lt - 0.8) * 7) * Math.exp(-(lt - 0.8) * 1.2) : lerp(540, 1450, E.in((lt - 2.2) / 0.8)), 980];
    const sw = [[220, 330, 130, 0.85, -1], [880, 1580, 120, 0.85, 1]];
    return shot({
      seed: 37, cam: lt => ({ x: 540, y: 960, s: 1.0 }),
      base: (g, lt, t) => { nightFill(g, 0, 0, W, H, '#101b58', '#2a52b2'); sw.forEach(([x, y, r, , d]) => VG.spiral(g, x, y, r, t, { dir: d }));
        const [x, y] = upos(lt), rot = 1.5 + (x + 300) / R * 0.06;
        rings(g, x, y, R, false, rot, ['#d4e6f6', '#9cc3ee']);
        g.save(); g.beginPath(); g.arc(x, y, R, 0, TAU); g.clip(); VG.disc(g, x, y, R, '#c8f0ec', '#4aa8b0');
        // vertical bands that roll with it
        const roll = (x + 300) / R; for (let i = -3; i <= 3; i++) { const bx = x + ((i * 0.3 + roll * 0.25) % 2 + 2) % 2 * R - R; g.fillStyle = i % 2 ? 'rgba(214,240,236,.9)' : 'rgba(40,120,140,.85)'; g.fillRect(bx, y - R, R * 0.2, 2 * R); }
        { const sx = x + Math.sin(roll * 1.6) * R * 0.6, sy = y - R * 0.35; g.fillStyle = '#f6edc8'; g.beginPath(); g.ellipse(sx, sy, R * 0.12 * Math.abs(Math.cos(roll * 1.6)) + 4, R * 0.12, 0, 0, TAU); g.fill(); }
        g.restore();
        rings(g, x, y, R, true, rot, ['#d4e6f6', '#9cc3ee']);
      },
      angle: (x, y, t, lt) => { const [ux, uy] = upos(lt); if (Math.hypot(x - ux, y - uy) < R) return Math.PI / 2 + 0.1; if (Math.abs(x - ux) < 160 && Math.abs(y - uy) < 560) return Math.PI / 2; return VG.skyAngle(x, y, t, sw); },
      detail: { mask: (x, y, t, lt) => { const [ux, uy] = upos(lt); return Math.hypot(x - ux, y - uy) < R; }, angle: () => Math.PI / 2 },
      over: (c, lt, t) => { const [x, y] = upos(lt); VG.outline(c, VG.circlePts(x, y, R, 30), t, { seed: 8, lw: 6 });
        // motion puffs behind
        for (let i = 0; i < 4; i++) { const ph = (t * 2 + i / 4) % 1; c.strokeStyle = `rgba(214,230,246,${0.7 * (1 - ph)})`; c.lineWidth = 7; c.beginPath(); c.arc(x - R - 40 - ph * 160, y + R - 30 - i * 20, 20 + ph * 30, 0, TAU); c.stroke(); }
        label(c, '98° tilt', 540, 1640, 64, '#f6edc8', -0.05); },
    });
  })();

  // ================= s12 — Neptune: wind and a very long year =================
  SCENES.s12 = (() => {
    const N = [540, 880], R = 340;
    return shot({
      seed: 41, cam: lt => ({ x: 540, y: 930, s: 1.0 + lt * 0.035 }),
      base: (g, lt, t) => { nightFill(g, -100, -100, 1200, 2100, '#0f1a52', '#24409e'); VG.planet(g, { x: N[0], y: N[1], r: R, ...PL.neptune }, t * 2.5);
        // calendar block
        g.fillStyle = '#f6edc8'; g.fillRect(340, 1400, 400, 300); g.fillStyle = '#cf4526'; g.fillRect(340, 1400, 400, 70); },
      angle: (x, y, t) => { if (Math.hypot(x - N[0], y - N[1]) < R) return 0.05 * Math.sin(y * 0.05 + t * 3); if (y > 1390 && y < 1710 && x > 330 && x < 750) return 0; return 0.08 * Math.sin(y * 0.01 + t * 2); },
      over: (c, lt, t) => {
        VG.outline(c, VG.circlePts(N[0], N[1], R, 40), t, { seed: 2, lw: 6 });
        // wind streaks racing across
        c.save(); c.lineCap = 'round'; for (let i = 0; i < 14; i++) { const ph = (t * 1.4 + i * 0.137) % 1, y = 520 + i * 55, x = -300 + ph * 1700; c.strokeStyle = `rgba(230,240,250,${0.75 * Math.sin(ph * Math.PI)})`; c.lineWidth = 9; c.beginPath(); c.moveTo(x, y); c.quadraticCurveTo(x + 120, y - 12, x + 260, y); c.stroke(); } c.restore();
        VG.outline(c, [[340, 1400], [740, 1400], [740, 1700], [340, 1700]], t, { seed: 4 });
        const yr = Math.min(165, Math.floor(Math.pow(cl(lt / 2.6), 1.6) * 165) + 1);
        c.save(); c.font = '150px "LilitaOne-400"'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = C.line; c.fillText(String(yr), 540, 1595); c.font = '44px "LilitaOne-400"'; c.fillStyle = '#f6edc8'; c.fillText('YEARS', 540, 1437); c.restore();
        if (lt > 2.6) label(c, '1 lap!', 820, 1390, 70 * E.out(cl((lt - 2.6) / 0.2)), '#f5c518', 0.15);
      },
    });
  })();

  // ================= s13 — the whole system, pull out =================
  SCENES.s13 = (() => {
    const S = [540, 960], SQ = 0.6;
    const OR = [['mercury', 140, 14, 2.2], ['venus', 200, 22, 1.6], ['earth', 265, 24, 1.25], ['mars', 330, 18, 0.95], ['jupiter', 560, 62, 0.45], ['saturn', 760, 50, 0.32], ['uranus', 960, 36, 0.22], ['neptune', 1140, 36, 0.17]];
    const pos = (k, t) => { const [, rx, , w] = OR[k]; const a = 1.1 + k * 2.05 + t * w * 0.6; return [S[0] + Math.cos(a) * rx, S[1] + Math.sin(a) * rx * SQ]; };
    return shot({
      seed: 43, cam: lt => mixCam({ x: 540, y: 960, s: 1.7 }, { x: 540, y: 960, s: 0.62 }, E.inOut(cl(lt / 3.6))),
      base: (g, lt, t) => {
        const sg = g.createRadialGradient(S[0], S[1], 50, S[0], S[1], 2200); sg.addColorStop(0, '#2f55b8'); sg.addColorStop(0.45, '#1c348c'); sg.addColorStop(1, '#0f1a52'); g.fillStyle = sg; g.fillRect(-1500, -1500, 4100, 5000);
        OR.forEach(([, rx], k) => { g.strokeStyle = k % 2 ? '#8fb6ee' : '#cfe3f6'; g.lineWidth = 12; g.beginPath(); g.ellipse(S[0], S[1], rx, rx * SQ, 0, 0, TAU); g.stroke(); });
        const r = U.rng(4); for (let i = 0; i < 300; i++) { const a = r() * TAU + t * 0.25, rx = 400 + r() * 80; g.fillStyle = r() < 0.5 ? '#c9962e' : '#e6b84a'; g.beginPath(); g.arc(S[0] + Math.cos(a) * rx, S[1] + Math.sin(a) * rx * SQ, 3 + r() * 5, 0, TAU); g.fill(); }
        sunBody(g, S[0], S[1], 100, t);
        OR.forEach(([n, , r2], k) => { const [x, y] = pos(k, t); planetFull(g, n, x, y, r2, t); });
      },
      angle: (x, y, t) => { const d = Math.hypot(x - S[0], (y - S[1]) / SQ); if (d < 100) return VG.tangent(x, y, S[0], S[1]) + t * 0.5; return VG.tangent(x, y, S[0], S[1], 1, SQ) + 0.18 * Math.sin(d * 0.03 - t * 1.5) + 0.1 * P.noise(x * 0.005, y * 0.005 + t * 0.2); },
      over: (c, lt, t) => { VG.outline(c, VG.circlePts(S[0], S[1], 100), t, { seed: 2 }); OR.forEach(([, , r2], k) => { const [x, y] = pos(k, t); VG.outline(c, VG.circlePts(x, y, r2, 18), t, { seed: 20 + k, lw: 3.5 }); }); VG.halo(c, S[0], S[1], 100, 240, t); },
    });
  })();

  // s14 — back on the hill: pull out so the sky's solar system sits behind the lantern-swinger
  SCENES.s14 = hillShot(lt => mixCam({ x: CLOSE.x, y: CLOSE.y - 40, s: CLOSE.s }, { x: 540, y: 420, s: 0.62 }, E.inOut(sm(0.6, 3.2, lt))), (c, lt, t) => {
    const [x, y] = HW.swing(lt * 3.6); HW.lantern(c, x, y, t);
  }, () => ({}), 11);
})();
