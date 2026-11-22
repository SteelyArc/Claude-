// Van Gogh toolkit for the solar-system short (1080x1920).
// Pipeline per shot (after 09_postimp): flat base -> flow-field strokes with hue-bucket swatches -> boiling navy outlines -> live highlights.
window.VG = (() => {
  const P = PAINT;
  let W = 1080, H = 1920; U.onStage((w, h) => { W = w; H = h; });
  const TAU = Math.PI * 2;
  const C = {
    navy: '#101b58', ultra: '#1c348c', cobalt: '#2a52b2', sky: '#4a78cc', pale: '#9cc3ee', ice: '#d4e6f6',
    chrome: '#f5c518', lemon: '#fbe58a', orange: '#e8862a', verm: '#cf4526', rust: '#a8452c', earth: '#2f7fd0',
    viridian: '#2e8b57', cypress: '#163c28', olive: '#6f8f3a', ochre: '#c9962e', wheat: '#e6b84a', line: '#111a46', cream: '#f6edc8',
  };
  const SW = {
    night: P.swatch(['#1b2f86', '#24409e', '#2f55b8', '#3f6cc8', '#17287a', '#335fc0', '#1e3a8f'], 0.42),
    swirl: P.swatch(['#8fb6ee', '#a9c9f2', '#cfe3f6', '#6f98e0', '#e8eccc', '#bcd6f0'], 0.35),
    sun: P.swatch(['#fbe58a', '#f5c518', '#f8d040', '#ffd860', '#f0b030', '#fff2b0'], 0.3),
    flame: P.swatch(['#e8862a', '#f0a830', '#cf4526', '#f5b028', '#d8642a'], 0.32),
    cypress: P.swatch(['#163c28', '#1f5a36', '#2e7a48', '#122e22', '#3a6a3a'], 0.35),
    hill: P.swatch(['#2e6a4a', '#3f7f3e', '#6f8f3a', '#24503a', '#8aa040', '#2a5a6a'], 0.35),
    ocean: P.swatch(['#2f7fd0', '#3f95dc', '#2a64b8', '#5aa8e0', '#2f8f78'], 0.35),
    cream: P.swatch(['#f6edc8', '#f2e2a8', '#e8eccc', '#fff6d8'], 0.3),
  };
  // hue/sat/lum of an rgb triple
  const hsl = ([r, g, b]) => {
    r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
    if (!d) return [0, 0, l];
    const s = d / (1 - Math.abs(2 * l - 1)); let h;
    if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4;
    return [(h * 60 + 360) % 360, s, l];
  };
  // generic palette: pick a regional swatch from the base colour's hue (Van Gogh = a dozen hues per region)
  const palette = (x, y, col, r) => {
    const [h, s, l] = hsl(col);
    if (s < 0.18) return l > 0.75 ? SW.cream(col, r) : l < 0.55 ? SW.night(col, r) : null;
    if (h >= 40 && h < 70 && l > 0.5) return SW.sun(col, r);
    if (h < 40 || h >= 345) return SW.flame(col, r);
    if (h >= 70 && h < 175) return l < 0.25 ? SW.cypress(col, r) : SW.hill(col, r);
    if (h >= 175 && h < 205 && l > 0.35) return SW.ocean(col, r);
    if (h >= 175 && h < 262) return l < 0.46 ? SW.night(col, r) : SW.swirl(col, r);
    return null;
  };
  const tangent = (x, y, cx, cy, dir = 1, sq = 1) => Math.atan2((y - cy) / sq, x - cx) + dir * Math.PI / 2;
  // sky flow: tangent around swirl centres, rolling horizontal wave elsewhere
  const skyAngle = (x, y, t, swirls = []) => {
    let best = null, bd = 1e9;
    for (const s of swirls) { const d = Math.hypot(x - s[0], (y - s[1]) / (s[3] || 1)) / s[2]; if (d < bd) { bd = d; best = s; } }
    if (best && bd < 1.5) return tangent(x, y, best[0], best[1], best[4] || 1, best[3] || 1) + 0.12 * Math.sin(bd * 6 - t * 1.2);
    return 0.38 * Math.sin(y * 0.0065 + x * 0.004 + t * 0.7) + 0.12 * P.noise(x * 0.004 + t * 0.2, y * 0.004);
  };
  // spiral band (Starry Night swirl) painted into the base
  const spiral = (g, x, y, r, t, { cols = ['#9cc3ee', '#5a82d6', '#d4e6f6'], dir = 1, turns = 2.6, lw = 16, sq = 0.85 } = {}) => {
    g.save(); g.lineCap = 'round';
    cols.forEach((cc, ring) => {
      g.strokeStyle = cc; g.lineWidth = lw - ring * 3; g.beginPath();
      for (let a = 0; a < TAU * turns / 2 * 1.0; a += 0.1) {
        const rr = r * (0.2 + a / (TAU * turns / 2)) * (1 - ring * 0.1), aa = (a + ring * 0.7) * dir + t * 0.8 * dir;
        const px = x + Math.cos(aa) * rr, py = y + Math.sin(aa) * rr * sq; a ? g.lineTo(px, py) : g.moveTo(px, py);
      }
      g.stroke();
    });
    g.restore();
  };
  const disc = (g, x, y, r, inner, outer, light = [-0.35, -0.35]) => {
    const gr = g.createRadialGradient(x + r * light[0], y + r * light[1], r * 0.1, x, y, r);
    gr.addColorStop(0, inner); gr.addColorStop(1, outer); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill();
  };
  // gas-giant / rocky planet with latitude bands
  const planet = (g, p, t) => {
    const { x, y, r } = p;
    g.save(); g.beginPath(); g.arc(x, y, r, 0, TAU); g.clip();
    disc(g, x, y, r, p.c1, p.c2);
    if (p.bands) p.bands.forEach(([dy, hh, col], k) => {
      g.fillStyle = col; g.beginPath();
      for (let i = 0; i <= 24; i++) { const xx = x - r + (2 * r) * i / 24; const yy = y + dy * r + Math.sin(i * 0.8 + t * 1.5 + k) * r * 0.025; i ? g.lineTo(xx, yy) : g.moveTo(xx, yy); }
      for (let i = 24; i >= 0; i--) { const xx = x - r + (2 * r) * i / 24; const yy = y + (dy + hh) * r + Math.sin(i * 0.8 + t * 1.5 + k + 1) * r * 0.025; g.lineTo(xx, yy); }
      g.fill();
    });
    if (p.spot) { const [sx, sy, sr] = p.spot; spiral(g, x + sx * r, y + sy * r, sr * r, t * 1.4, { cols: ['#cf4526', '#f0a070', '#a8452c'], lw: Math.max(4, sr * r * 0.35), sq: 0.6, turns: 2.2 }); }
    if (p.land) p.land.forEach(([lx, ly, lr, rot]) => { g.fillStyle = '#3f8f3e'; g.beginPath(); g.ellipse(x + lx * r, y + ly * r, lr * r, lr * r * 0.6, rot, 0, TAU); g.fill(); });
    // terminator shade
    const sh = g.createRadialGradient(x - r * 0.4, y - r * 0.4, r * 0.3, x, y, r * 1.15); sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(10,20,70,.55)');
    g.fillStyle = sh; g.fillRect(x - r, y - r, 2 * r, 2 * r);
    g.restore();
  };
  // the stroke pass. passes = [{mask, cell, len, width, seed, outline}]
  const paint = (c, base, angle, t, passes, pal = palette) => {
    for (const ps of passes) P.strokes(c, base, { cell: 10, len: 24, width: 6.5, outline: 0.85, outlineMix: 0.42, outlineCol: [14, 22, 70], boil: 0, ...ps, angle, t, palette: pal });
  };
  // boiling navy outline around a path (8fps)
  const outline = (c, pts, t, { lw = 4.5, closed = true, amp = 2.2, col = C.line, seed = 1 } = {}) => {
    c.save(); c.strokeStyle = col; c.lineWidth = lw; c.lineJoin = 'round'; c.lineCap = 'round';
    P.roughPath(c, pts, { amp, seed: P.boilSeed(t, 8) * 31 + seed, closed, step: 12 }); c.stroke(); c.restore();
  };
  const circlePts = (x, y, r, n = 28, sq = 1) => Array.from({ length: n }, (_, i) => [x + Math.cos(i / n * TAU) * r, y + Math.sin(i / n * TAU) * r * sq]);
  // pulsing dashed halo rings (the lamp/star halos of the bedroom & starry night)
  const halo = (c, x, y, r0, r1, t, { col = '255,236,140', a = 0.3, lw = 14, speed = 0.8, n = 3 } = {}) => {
    c.save(); c.globalCompositeOperation = 'lighter'; c.lineCap = 'round';
    for (let k = 0; k < n; k++) { const ph = (t * speed + k / n) % 1, r = r0 + ph * (r1 - r0); c.strokeStyle = `rgba(${col},${a * (1 - ph)})`; c.lineWidth = lw; c.setLineDash([22, 14]); c.lineDashOffset = -t * 60; c.beginPath(); c.arc(x, y, r, 0, TAU); c.stroke(); }
    c.restore();
  };
  const star = (c, x, y, r, t, k = 0) => {
    const tw = 0.75 + 0.25 * Math.sin(t * 3 + k * 2.1);
    c.save(); c.globalCompositeOperation = 'lighter';
    const g = c.createRadialGradient(x, y, 0, x, y, r * 2.6 * tw); g.addColorStop(0, 'rgba(255,246,190,.95)'); g.addColorStop(0.35, 'rgba(250,220,90,.55)'); g.addColorStop(1, 'rgba(250,220,90,0)');
    c.fillStyle = g; c.beginPath(); c.arc(x, y, r * 2.6 * tw, 0, TAU); c.fill(); c.restore();
    c.fillStyle = '#fff3b8'; c.beginPath(); c.arc(x, y, r * 0.55, 0, TAU); c.fill();
  };
  // TikTok caption: chunky Lilita with navy outline + drop, pops in
  const caption = (c, text, y, lt, { size = 82, col = '#fbe58a', maxW = 900, pop = true } = {}) => {
    if (lt < 0) return;
    const k = pop ? U.clamp(lt / 0.18) : 1, s = pop ? (k < 1 ? 0.6 + 0.55 * U.ease.out(k) - 0.15 * Math.sin(k * Math.PI) : 1) : 1;
    c.save(); c.font = `${size}px "LilitaOne-400"`; c.textAlign = 'center'; c.textBaseline = 'middle';
    // wrap
    const words = text.split(' '), lines = []; let cur = '';
    for (const w of words) { const tr = cur ? cur + ' ' + w : w; if (c.measureText(tr).width > maxW && cur) { lines.push(cur); cur = w; } else cur = tr; }
    lines.push(cur);
    c.translate(W / 2, y); c.scale(s, s); c.rotate(-0.025);
    lines.forEach((ln, i) => {
      const yy = (i - (lines.length - 1) / 2) * size * 1.08;
      c.lineJoin = 'round'; c.strokeStyle = C.line; c.lineWidth = size * 0.2; c.strokeText(ln, 4, yy + 6);
      c.strokeText(ln, 0, yy); c.fillStyle = col; c.fillText(ln, 0, yy);
    });
    c.restore();
  };
  return { C, SW, P, TAU, hsl, palette, tangent, skyAngle, spiral, disc, planet, paint, outline, circlePts, halo, star, caption };
})();
