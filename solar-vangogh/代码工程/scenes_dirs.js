// Three direction frames (same moment: "the Sun holds everything"), three compositions.
(() => {
  const { C, P, TAU } = VG;
  const W = 1080, H = 1920;
  const PL = {
    mercury: { c1: '#d8c8a8', c2: '#8a7a68' },
    venus: { c1: '#fbe0a0', c2: '#d8963a' },
    earth: { c1: '#6fb4f0', c2: '#1f4f9a', land: [[-0.3, -0.1, 0.38, 0.4], [0.35, 0.3, 0.3, -0.3]] },
    mars: { c1: '#f0885a', c2: '#a8452c' },
    jupiter: { c1: '#f4dcb0', c2: '#b0743a', bands: [[-0.55, 0.16, '#c98a4a'], [-0.18, 0.12, '#e8c48a'], [0.12, 0.18, '#b8743a'], [0.45, 0.12, '#d8a070']], spot: [0.3, 0.25, 0.22] },
    saturn: { c1: '#f6e2a8', c2: '#c09a48', bands: [[-0.3, 0.14, '#e0c070'], [0.1, 0.16, '#d0a858']] },
  };
  const ringSaturn = (g, x, y, r, front) => {
    g.save(); g.lineWidth = r * 0.16; g.strokeStyle = '#e8d090';
    g.beginPath(); g.ellipse(x, y, r * 2.0, r * 0.55, -0.25, front ? 0 : Math.PI, front ? Math.PI : TAU); g.stroke();
    g.lineWidth = r * 0.08; g.strokeStyle = '#c9a050'; g.beginPath(); g.ellipse(x, y, r * 1.65, r * 0.44, -0.25, front ? 0 : Math.PI, front ? Math.PI : TAU); g.stroke(); g.restore();
  };

  // ---------------- A: Starry hillside — the solar system IS the swirling sky, a figure swings a lantern on a string
  const A = (() => {
    const SUN = [540, 560], SQ = 0.42, ORB = [190, 285, 385, 490];
    const plan = [['mercury', 16, 2.1], ['earth', 30, 1.1], ['mars', 22, 0.8], ['jupiter', 58, 0.45]];
    const pos = (k, t) => { const a = 0.8 + k * 1.7 + t * plan[k][2] * 0.6; return [SUN[0] + Math.cos(a) * ORB[k], SUN[1] + Math.sin(a) * ORB[k] * SQ]; };
    const FS = 1.7, FO = [808, 1462], fp = ([x, y]) => [FO[0] + (x - FO[0]) * FS, FO[1] + (y - FO[1]) * FS];
    const hand = fp([868, 1230]);
    const lantern = t => { const a = t * 3.2; return [hand[0] + Math.cos(a) * 105, hand[1] + Math.sin(a) * 105 * 0.55]; };
    const hill = g => { g.beginPath(); g.moveTo(0, 1560); g.bezierCurveTo(260, 1470, 560, 1440, 760, 1450); g.bezierCurveTo(900, 1458, 1000, 1500, 1080, 1540); g.lineTo(1080, H); g.lineTo(0, H); g.closePath(); };
    const cypress = [[90, 1800], [70, 1500], [120, 1150], [150, 860], [175, 1150], [240, 1480], [230, 1800]];
    function base(g, t) {
      const sg = g.createLinearGradient(0, 0, 0, 1500); sg.addColorStop(0, '#101b58'); sg.addColorStop(0.6, '#24409e'); sg.addColorStop(1, '#3a66c4'); g.fillStyle = sg; g.fillRect(0, 0, W, H);
      ORB.forEach((rx, k) => { g.strokeStyle = k % 2 ? '#8fb6ee' : '#cfe3f6'; g.lineWidth = 16; g.beginPath(); g.ellipse(SUN[0], SUN[1], rx, rx * SQ, 0, 0, TAU); g.stroke(); });
      VG.spiral(g, 200, 220, 120, t, { dir: -1 }); VG.spiral(g, 900, 170, 90, t);
      VG.disc(g, SUN[0], SUN[1], 150, '#fff2b0', '#f0a830', [0, 0]);
      plan.forEach(([n, r], k) => { const [x, y] = pos(k, t); VG.planet(g, { x, y, r, ...PL[n] }, t); });
      // hill + village + figure
      g.fillStyle = '#2e6a4a'; hill(g); g.fill();
      g.fillStyle = '#173f2a'; g.fillRect(0, 1700, W, 220);
      g.fillStyle = '#163c28'; g.beginPath(); cypress.forEach((p, i) => i ? g.lineTo(...p) : g.moveTo(...p)); g.closePath(); g.fill();
      figure(g, t);
    }
    function figure(g, t) {
      g.save(); g.translate(FO[0], FO[1]); g.scale(FS, FS); g.translate(-FO[0], -FO[1]);
      g.fillStyle = '#1c348c'; g.beginPath(); g.moveTo(770, 1355); g.lineTo(845, 1355); g.lineTo(866, 1462); g.lineTo(752, 1462); g.closePath(); g.fill();           // coat
      g.strokeStyle = '#1c348c'; g.lineWidth = 26; g.lineCap = 'round'; g.beginPath(); g.moveTo(835, 1372); g.lineTo(868, 1230); g.stroke();                    // raised arm
      g.beginPath(); g.moveTo(780, 1372); g.lineTo(752, 1440); g.stroke();
      g.fillStyle = '#c9962e'; g.beginPath(); g.arc(808, 1326, 30, 0, TAU); g.fill();                                                                                       // straw hat crown
      g.beginPath(); g.ellipse(808, 1342, 58, 12, 0, 0, TAU); g.fill();
      g.strokeStyle = '#111a46'; g.lineWidth = 16; g.beginPath(); g.moveTo(785, 1462); g.lineTo(780, 1500); g.moveTo(835, 1462); g.lineTo(842, 1500); g.stroke();
      g.restore();
    }
    const angle = (x, y, t) => {
      if (y > 1440 && !(x < 250 && y > 850)) return 0.15 * Math.sin(x * 0.01 + t) + (y > 1700 ? 0 : -0.08);
      if (x > 60 && x < 250 && y > 840 && y < 1800) return -Math.PI / 2 + 0.3 * Math.sin(y * 0.02 + t * 2);
      const d = Math.hypot(x - SUN[0], (y - SUN[1]) / SQ);
      if (d < 150) return VG.tangent(x, y, SUN[0], SUN[1]) + t * 0.4;
      if (d < 560) return VG.tangent(x, y, SUN[0], SUN[1], 1, SQ) + 0.1 * Math.sin(d * 0.05 - t);
      return VG.skyAngle(x, y, t, [[200, 220, 120, 0.85, -1], [900, 170, 90, 0.85, 1]]);
    };
    return {
      draw(c, lt, t) {
        const b = P.scratch('dA'), g = b.getContext('2d'); base(g, t); c.drawImage(b, 0, 0);
        VG.paint(c, b, angle, t, [{ cell: 11, len: 34, width: 7.5, seed: 3 }]);
        // detail pass on planets & figure
        const det = (x, y) => Math.hypot(x - 820, y - 1330) < 230 || plan.some(([, r], k) => { const [px, py] = pos(k, t); return Math.hypot(x - px, y - py) < r; });
        VG.paint(c, b, (x, y) => (x > 640 && x < 1000 && y > 1150) ? -Math.PI / 2 : 0, t, [{ cell: 6, len: 12, width: 4, seed: 5, outline: 0.5, mask: det }]);
        VG.outline(c, cypress, t, { seed: 4 });
        VG.outline(c, [[770, 1355], [845, 1355], [866, 1462], [752, 1462]].map(fp), t, { seed: 6 }); VG.outline(c, VG.circlePts(...fp([808, 1330]), 34 * FS, 16, 0.9), t, { seed: 8 });
        VG.outline(c, VG.circlePts(SUN[0], SUN[1], 150), t, { seed: 7 });
        plan.forEach(([, r], k) => { const [x, y] = pos(k, t); VG.outline(c, VG.circlePts(x, y, r, 20), t, { seed: 10 + k, lw: 3.5 }); });
        // string + lantern = the orbit idea in one hand
        const [lx, ly] = lantern(lt);
        c.strokeStyle = '#f6edc8'; c.lineWidth = 3; c.beginPath(); c.moveTo(...hand); c.lineTo(lx, ly); c.stroke();
        VG.star(c, lx, ly, 20, t, 1); c.fillStyle = '#e8862a'; c.fillRect(lx - 12, ly - 14, 24, 28);
        VG.halo(c, SUN[0], SUN[1], 150, 300, t);
        [[110, 520, 10], [330, 90, 12], [700, 330, 9], [980, 420, 11], [80, 820, 8], [990, 760, 10], [420, 980, 8]].forEach(([x, y, r], k) => VG.star(c, x, y, r, t, k));
        VG.caption(c, 'The Sun is 99.8% of EVERYTHING', 1160, 1, { size: 86 });
      },
    };
  })();

  // ---------------- B: Sunflower Sun — huge close subject, Earth sweeping past over a wheat field
  const B = (() => {
    const SUN = [540, 690], R = 300;
    const earth = t => { const a = 0.35 + t * 0.18; return [540 + Math.cos(a) * 430, 1180 + Math.sin(a) * 180]; };
    function base(g, t) {
      const sg = g.createLinearGradient(0, 0, 0, 1400); sg.addColorStop(0, '#132063'); sg.addColorStop(1, '#2f5bb8'); g.fillStyle = sg; g.fillRect(0, 0, W, H);
      VG.spiral(g, 140, 1180, 110, t, { dir: -1 }); VG.spiral(g, 950, 1120, 80, t);
      // corona petals
      for (let i = 0; i < 26; i++) { const a = i / 26 * TAU + t * 0.15, l = R * (1.32 + 0.08 * Math.sin(t * 2 + i * 1.7));
        g.fillStyle = i % 2 ? '#e8862a' : '#f5b028'; g.beginPath(); g.moveTo(SUN[0] + Math.cos(a - 0.12) * R * 0.9, SUN[1] + Math.sin(a - 0.12) * R * 0.9);
        g.quadraticCurveTo(SUN[0] + Math.cos(a + 0.1) * l, SUN[1] + Math.sin(a + 0.1) * l, SUN[0] + Math.cos(a + 0.14) * R * 0.9, SUN[1] + Math.sin(a + 0.14) * R * 0.9); g.fill(); }
      VG.disc(g, SUN[0], SUN[1], R, '#fff2b0', '#f0a830', [0, 0]);
      VG.spiral(g, SUN[0], SUN[1], R * 0.75, t * 0.5, { cols: ['#f8d040', '#fff2b0', '#e8a030'], lw: 22, sq: 1 });
      // wheat field
      g.fillStyle = '#e6b84a'; g.beginPath(); g.moveTo(0, 1500); for (let x = 0; x <= W; x += 40) g.lineTo(x, 1480 + Math.sin(x * 0.012 + t) * 25); g.lineTo(W, H); g.lineTo(0, H); g.fill();
      g.fillStyle = '#c9962e'; g.fillRect(0, 1760, W, 160);
      // Earth trail + Earth
      for (let k = 1; k < 14; k++) { const [x, y] = earth(t - k * 0.35); g.fillStyle = `rgba(214,230,246,${0.7 - k * 0.045})`; g.beginPath(); g.arc(x, y, 14 - k * 0.7, 0, TAU); g.fill(); }
      const [ex, ey] = earth(t); VG.planet(g, { x: ex, y: ey, r: 62, ...PL.earth }, t);
      VG.planet(g, { x: 230, y: 330, r: 22, ...PL.mercury }, t); VG.planet(g, { x: 880, y: 250, r: 34, ...PL.venus }, t);
    }
    const angle = (x, y, t) => {
      const d = Math.hypot(x - SUN[0], y - SUN[1]);
      if (y > 1470) return -Math.PI / 2 + 0.5 + 0.25 * Math.sin(x * 0.015 + t * 2);
      if (d < R) return VG.tangent(x, y, SUN[0], SUN[1]) + t * 0.3;
      if (d < R * 1.45) return Math.atan2(y - SUN[1], x - SUN[0]) + 0.25 * Math.sin(d * 0.04 - t * 2);
      return VG.skyAngle(x, y, t, [[140, 1180, 110, 0.85, -1], [950, 1120, 80, 0.85, 1], [SUN[0], SUN[1], R * 1.9, 1, 1]]);
    };
    return {
      draw(c, lt, t) {
        const b = P.scratch('dB'), g = b.getContext('2d'); base(g, t); c.drawImage(b, 0, 0);
        VG.paint(c, b, angle, t, [{ cell: 10, len: 30, width: 7.5, seed: 8 }]);
        const [ex, ey] = earth(t);
        VG.paint(c, b, () => 0.1, t, [{ cell: 6, len: 12, width: 4, seed: 6, outline: 0.5, mask: (x, y) => Math.hypot(x - ex, y - ey) < 62 }]);
        VG.outline(c, VG.circlePts(SUN[0], SUN[1], R, 40), t, { seed: 3, lw: 5 });
        VG.outline(c, VG.circlePts(ex, ey, 62, 22), t, { seed: 9 });
        VG.halo(c, SUN[0], SUN[1], R, R * 1.6, t, { lw: 18, a: 0.25 });
        [[90, 120, 10], [1000, 520, 12], [70, 760, 9], [1010, 900, 9]].forEach(([x, y, r], k) => VG.star(c, x, y, r, t, k));
        VG.caption(c, 'The Sun is 99.8% of EVERYTHING', 1610, 1, { size: 86 });
      },
    };
  })();

  // ---------------- C: Top-down whirlpool — the whole system seen from above, every orbit a brush ring
  const C3 = (() => {
    const SUN = [540, 820], SQ = 0.62;
    const ORB = [['mercury', 150, 14, 2.2], ['venus', 210, 22, 1.6], ['earth', 280, 24, 1.2], ['mars', 350, 18, 0.9], ['jupiter', 560, 62, 0.4], ['saturn', 720, 50, 0.3]];
    const pos = (k, t) => { const [, rx, , w] = ORB[k]; const a = 1.1 + k * 2.05 + t * w * 0.5; return [SUN[0] + Math.cos(a) * rx, SUN[1] + Math.sin(a) * rx * SQ]; };
    function base(g, t) {
      const sg = g.createRadialGradient(SUN[0], SUN[1], 50, SUN[0], SUN[1], 1100); sg.addColorStop(0, '#2f55b8'); sg.addColorStop(0.5, '#1c348c'); sg.addColorStop(1, '#0f1a52'); g.fillStyle = sg; g.fillRect(0, 0, W, H);
      ORB.forEach(([, rx], k) => { g.strokeStyle = k % 2 ? '#8fb6ee' : '#cfe3f6'; g.lineWidth = 12; g.beginPath(); g.ellipse(SUN[0], SUN[1], rx, rx * SQ, 0, 0, TAU); g.stroke(); });
      // asteroid belt (wheat-gold rubble)
      const r = U.rng(4); for (let i = 0; i < 260; i++) { const a = r() * TAU + t * 0.25, rx = 420 + r() * 70; g.fillStyle = r() < 0.5 ? '#c9962e' : '#e6b84a'; g.beginPath(); g.arc(SUN[0] + Math.cos(a) * rx, SUN[1] + Math.sin(a) * rx * SQ, 3 + r() * 5, 0, TAU); g.fill(); }
      VG.disc(g, SUN[0], SUN[1], 105, '#fff2b0', '#f0a830', [0, 0]);
      ORB.forEach(([n, , r], k) => { const [x, y] = pos(k, t); if (n === 'saturn') ringSaturn(g, x, y, r, false); VG.planet(g, { x, y, r, ...PL[n] }, t); if (n === 'saturn') ringSaturn(g, x, y, r, true); });
    }
    const angle = (x, y, t) => {
      const d = Math.hypot(x - SUN[0], (y - SUN[1]) / SQ);
      if (d < 105) return VG.tangent(x, y, SUN[0], SUN[1]) + t * 0.5;
      return VG.tangent(x, y, SUN[0], SUN[1], 1, SQ) + 0.18 * Math.sin(d * 0.03 - t * 1.5) + 0.1 * P.noise(x * 0.005, y * 0.005 + t * 0.2);
    };
    return {
      draw(c, lt, t) {
        const b = P.scratch('dC'), g = b.getContext('2d'); base(g, t); c.drawImage(b, 0, 0);
        VG.paint(c, b, angle, t, [{ cell: 10, len: 32, width: 7, seed: 12 }]);
        const det = (x, y) => ORB.some(([, , r], k) => { const [px, py] = pos(k, t); return Math.hypot(x - px, y - py) < r; });
        VG.paint(c, b, () => 0, t, [{ cell: 6, len: 12, width: 4, seed: 7, outline: 0.5, mask: det }]);
        VG.outline(c, VG.circlePts(SUN[0], SUN[1], 105), t, { seed: 2 });
        ORB.forEach(([, , r], k) => { const [x, y] = pos(k, t); VG.outline(c, VG.circlePts(x, y, r, 20), t, { seed: 20 + k, lw: 3.5 }); });
        VG.halo(c, SUN[0], SUN[1], 105, 230, t);
        VG.caption(c, 'The Sun is 99.8% of EVERYTHING', 1560, 1, { size: 86 });
      },
    };
  })();
  SCENES.dirA = A; SCENES.dirB = B; SCENES.dirC = C3;
})();
