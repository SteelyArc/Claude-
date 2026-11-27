// Phoenix embroidery renderer.
// Runs inside a browser page (canvas 2D). Every visible mark is an individual
// simulated thread stitch: satin, herringbone (feather barbs), stem and tatami fill.
// Export: window.renderPhoenix(canvas, seed) -> draws onto a transparent canvas.

(function () {
  const W = 3000, H = 4000, MARGIN = 110;

  // ---------------------------------------------------------------- random
  let _s = 1;
  function seed(v) { _s = v >>> 0 || 1; }
  function rand() { // mulberry32
    _s |= 0; _s = (_s + 0x6D2B79F5) | 0;
    let t = Math.imul(_s ^ (_s >>> 15), 1 | _s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  const jit = (a) => (rand() * 2 - 1) * a;

  // ---------------------------------------------------------------- colour
  const C = {
    darkBrown: [44, 22, 16], brown: [86, 46, 28], deepCrimson: [92, 12, 22], crimson: [146, 22, 30],
    red: [182, 42, 32], burnt: [204, 84, 26], orange: [228, 120, 36], gold: [236, 176, 56],
    yellow: [246, 210, 104], cream: [242, 230, 204], blueDark: [46, 70, 102], blue: [84, 116, 150],
    blueLight: [146, 172, 196],
  };
  const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  function ramp(stops, t) {
    t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < stops.length; i++) {
      if (t <= stops[i][0]) {
        const [p0, c0] = stops[i - 1], [p1, c1] = stops[i];
        return mix(c0, c1, (t - p0) / (p1 - p0 || 1));
      }
    }
    return stops[stops.length - 1][1];
  }
  const css = (c, f = 1, a = 1) =>
    `rgba(${Math.max(0, Math.min(255, c[0] * f)) | 0},${Math.max(0, Math.min(255, c[1] * f)) | 0},${Math.max(0, Math.min(255, c[2] * f)) | 0},${a})`;

  // ---------------------------------------------------------------- state
  let ctx = null, MEASURE = false;
  let bb = [1e9, 1e9, -1e9, -1e9];
  const track = (x, y, pad = 0) => {
    bb[0] = Math.min(bb[0], x - pad); bb[1] = Math.min(bb[1], y - pad);
    bb[2] = Math.max(bb[2], x + pad); bb[3] = Math.max(bb[3], y + pad);
  };
  const TW = 6.0;              // thread width (design units)

  // ---------------------------------------------------------------- stitches
  function stitch(x1, y1, x2, y2, col, tw = TW, contrast = 1) {
    if (MEASURE) return;
    x1 += jit(1.1); y1 += jit(1.1); x2 += jit(1.1); y2 += jit(1.1);
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
    const nx = -dy / L, ny = dx / L;
    const v = 1 + jit(0.085);
    const g = ctx.createLinearGradient(x1, y1, x2, y2);
    const k = contrast;
    g.addColorStop(0, css(col, v * (1 - 0.42 * k)));
    g.addColorStop(0.18, css(col, v * (1 - 0.12 * k)));
    g.addColorStop(0.45, css(col, v * (1 + 0.2 * k)));
    g.addColorStop(0.78, css(col, v * (1 - 0.02 * k)));
    g.addColorStop(1, css(col, v * (1 - 0.45 * k)));
    ctx.lineCap = 'round';
    ctx.strokeStyle = g;
    ctx.lineWidth = tw;
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    // groove between neighbouring threads
    ctx.strokeStyle = css(C.darkBrown, 1, 0.22 * k);
    ctx.lineWidth = Math.max(0.8, tw * 0.16);
    ctx.beginPath();
    ctx.moveTo(x1 + nx * tw * 0.48, y1 + ny * tw * 0.48);
    ctx.lineTo(x2 + nx * tw * 0.48, y2 + ny * tw * 0.48); ctx.stroke();
    // specular glint of the twisted thread
    if (L > tw * 2) {
      ctx.strokeStyle = `rgba(255,248,230,${0.2 * k})`;
      ctx.lineWidth = tw * 0.24;
      ctx.beginPath();
      ctx.moveTo(x1 + dx * 0.22 - nx * tw * 0.2, y1 + dy * 0.22 - ny * tw * 0.2);
      ctx.lineTo(x1 + dx * 0.6 - nx * tw * 0.2, y1 + dy * 0.6 - ny * tw * 0.2); ctx.stroke();
    }
  }

  // stem / split stitch along a polyline (outlines, rachis, spirals)
  function stem(pts, col, tw = TW * 1.15, seg = 15) {
    if (pts.length < 2) return;
    const rs = resample(pts, seg * 0.55);
    for (let i = 0; i + 1 < rs.length; i++) {
      const a = rs[i], b = rs[Math.min(rs.length - 1, i + 2)];
      const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      const o = (i % 2 ? 1 : -1) * tw * 0.22;
      stitch(a[0] - dy / L * o, a[1] + dx / L * o, b[0] + dy / L * o, b[1] - dx / L * o, col, tw, 0.8);
    }
  }

  function resample(pts, step) {
    const out = [pts[0]];
    let carry = 0;
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      let d = step - carry;
      while (d <= L) {
        const t = d / L;
        out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
        d += step;
      }
      carry = L - (d - step);
    }
    out.push(pts[pts.length - 1]);
    return out;
  }

  // ---------------------------------------------------------------- geometry
  function cubic(p0, p1, p2, p3, t) {
    const u = 1 - t;
    return [u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]];
  }

  // Blade = a shape around a cubic spine with a width profile.
  function blade(P, Wd, profile, spacing = TW * 0.78) {
    let len = 0, prev = P[0];
    for (let i = 1; i <= 60; i++) { const p = cubic(...P, i / 60); len += Math.hypot(p[0] - prev[0], p[1] - prev[1]); prev = p; }
    const n = Math.max(6, Math.round(len / spacing));
    const S = [], L = [], R = [], T = [], Wl = [];
    for (let i = 0; i < n; i++) {
      const t = i / (n - 1);
      const p = cubic(...P, t);
      const q = cubic(...P, Math.min(1, t + 1e-3)), r = cubic(...P, Math.max(0, t - 1e-3));
      let dx = q[0] - r[0], dy = q[1] - r[1]; const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;
      const w = Wd * profile(t) / 2;
      S.push(p); T.push(t); Wl.push(w);
      L.push([p[0] - dy * w, p[1] + dx * w]);
      R.push([p[0] + dy * w, p[1] - dx * w]);
      track(p[0], p[1], w + 8);
    }
    return { S, L, R, T, W: Wl, n, len };
  }

  function outlinePts(b) { return b.L.concat(b.R.slice().reverse()); }
  function pathOf(pts) {
    const p = new Path2D();
    p.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) p.lineTo(pts[i][0], pts[i][1]);
    p.closePath();
    return p;
  }

  // Raised-embroidery shadow, only cast onto stitches already on the canvas.
  function raiseShadow(path, strength = 0.5, dx = 4, dy = 7, blur = 7) {
    if (MEASURE) return;
    ctx.save();
    ctx.globalCompositeOperation = 'source-atop';
    ctx.filter = `blur(${blur}px)`;
    ctx.translate(dx, dy);
    ctx.fillStyle = `rgba(30,8,4,${strength})`;
    ctx.fill(path);
    ctx.restore();
  }

  // underlay: fills tiny gaps between stitches so no transparent pinholes remain
  function underlay(path, col) {
    if (MEASURE) return;
    ctx.fillStyle = css(col, 0.55);
    ctx.fill(path);
  }

  // ---------------------------------------------------------------- elements
  const PROFILES = {
    primary: (t) => Math.pow(Math.sin(Math.PI * (0.13 + 0.87 * t)), 0.55),
    covert: (t) => Math.pow(Math.sin(Math.PI * (0.1 + 0.9 * t)), 0.33),
    scale: (t) => Math.pow(Math.sin(Math.PI * (0.06 + 0.94 * t)), 0.3),
    flame: (t) => Math.pow(1 - t, 1.05) * (0.75 + 0.5 * Math.sin(Math.PI * Math.min(1, t * 1.3))),
    plume: (t) => Math.pow(Math.sin(Math.PI * (0.02 + 0.98 * t)), 0.7) * (0.55 + 0.45 * (1 - t)),
  };

  // Feather with central rachis and herringbone barbs.
  function feather(P, Wd, stops, opt = {}) {
    const b = blade(P, Wd, opt.profile || PROFILES.primary);
    const outline = outlinePts(b);
    const path = pathOf(outline);
    raiseShadow(path, opt.shadow ?? 0.5);
    underlay(path, ramp(stops, 0.5));
    const slant = opt.slant ?? 0.95;
    for (let i = 0; i < b.n; i++) {
      const k = Math.max(1, Math.round(b.W[i] * slant / (TW * 0.78)));
      const j = Math.min(b.n - 1, i + k);
      const col = ramp(stops, b.T[i] + jit(0.05));
      stitch(b.S[i][0], b.S[i][1], b.L[j][0], b.L[j][1], col);
      stitch(b.S[i][0], b.S[i][1], b.R[j][0], b.R[j][1], mix(col, C.darkBrown, 0.08));
    }
    if (opt.band) { // contrasting stitched band near the tip (e.g. muted blue)
      const [t0, t1, bc] = opt.band;
      for (let i = 0; i < b.n; i++) {
        if (b.T[i] < t0 || b.T[i] > t1) continue;
        const k = Math.max(1, Math.round(b.W[i] * slant / (TW * 0.78)));
        const j = Math.min(b.n - 1, i + k);
        stitch(b.S[i][0], b.S[i][1], b.L[j][0], b.L[j][1], bc);
        stitch(b.S[i][0], b.S[i][1], b.R[j][0], b.R[j][1], mix(bc, C.darkBrown, 0.1));
      }
    }
    if (opt.rachis !== false) {
      const end = Math.floor(b.n * (opt.rachisEnd ?? 0.88));
      stem(b.S.slice(0, end), opt.rachis || C.gold, TW * 1.1);
    }
    stem(outline.concat([outline[0]]), opt.outline || C.darkBrown, TW * 1.25);
    return b;
  }

  // Satin across a blade (flames, beak, plumes).
  function satin(P, Wd, stops, opt = {}) {
    const b = blade(P, Wd, opt.profile || PROFILES.flame);
    const outline = outlinePts(b);
    const path = pathOf(outline);
    raiseShadow(path, opt.shadow ?? 0.45);
    underlay(path, ramp(stops, 0.5));
    const slant = opt.slant ?? 0.35;
    for (let i = 0; i < b.n; i++) {
      const k = Math.round(b.W[i] * slant / (TW * 0.78));
      const j = Math.min(b.n - 1, i + k);
      const col = ramp(stops, b.T[i] + jit(0.05));
      stitch(b.L[i][0], b.L[i][1], b.R[j][0], b.R[j][1], col, TW, opt.contrast ?? 1);
    }
    if (opt.outline !== false) stem(outline.concat([outline[0]]), opt.outline || C.darkBrown, TW * 1.2);
    return b;
  }

  // Tatami fill inside an arbitrary path.
  function tatami(path, bbox, colFn, angle = 0.35, stLen = 30) {
    if (MEASURE) return;
    ctx.save();
    ctx.clip(path);
    const [x0, y0, x1, y1] = bbox;
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, R = Math.hypot(x1 - x0, y1 - y0) / 2 + 10;
    const ca = Math.cos(angle), sa = Math.sin(angle);
    let row = 0;
    for (let v = -R; v <= R; v += TW * 0.82, row++) {
      const off = ((row * 11) % stLen);
      for (let u = -R - off; u <= R; u += stLen) {
        const a = [cx + ca * u - sa * v, cy + sa * u + ca * v];
        const b2 = [cx + ca * (u + stLen) - sa * v, cy + sa * (u + stLen) + ca * v];
        stitch(a[0], a[1], b2[0], b2[1], colFn(a[0], a[1]), TW, 0.55);
      }
    }
    ctx.restore();
  }

  // Japanese-style curling cloud: overlapping stitched discs with spirals.
  function cloud(cx, cy, s, flip = 1) {
    const discs = [[-1.55, 0.35, 0.62], [-0.75, -0.25, 0.85], [0.3, -0.45, 1], [1.3, 0.05, 0.78], [0.45, 0.45, 0.7], [-0.5, 0.5, 0.66]];
    for (const [dx, dy, r] of discs) {
      const x = cx + dx * s * flip, y = cy + dy * s, rr = r * s;
      track(x, y, rr + 10);
      const p = new Path2D(); p.arc(x, y, rr, 0, Math.PI * 2);
      raiseShadow(p, 0.45);
      underlay(p, C.blue);
      tatami(p, [x - rr, y - rr, x + rr, y + rr],
        (px, py) => mix(C.blueLight, C.blueDark, Math.max(0, Math.min(1, (py - (y - rr)) / (2 * rr) * 0.9 + 0.05))),
        0.5 * flip);
      // spiral in cream
      const sp = [];
      for (let a = 0; a < Math.PI * 3.1; a += 0.08) {
        const r2 = rr * 0.72 * (a / (Math.PI * 3.1));
        sp.push([x + Math.cos(a * flip + 2) * r2, y + Math.sin(a * flip + 2) * r2]);
      }
      stem(sp, C.cream, TW * 1.25, 14);
      const ring = [];
      for (let a = 0; a <= Math.PI * 2 + 0.05; a += 0.05) ring.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]);
      stem(ring, C.darkBrown, TW * 1.3);
      const ring2 = [];
      for (let a = 0; a <= Math.PI * 2 + 0.05; a += 0.05) ring2.push([x + Math.cos(a) * (rr - 14), y + Math.sin(a) * (rr - 14)]);
      stem(ring2, C.cream, TW * 0.95, 13);
    }
  }

  function ember(x, y, r, col) {
    satin([[x, y + r], [x + r * 0.2, y + r * 0.3], [x - r * 0.2, y - r * 0.3], [x, y - r]], r * 0.9,
      [[0, col], [1, C.yellow]], { profile: PROFILES.covert, slant: 0.1, shadow: 0.35 });
  }

  // ---------------------------------------------------------------- phoenix
  const CX = 1500;
  const rot = (v, a) => [v[0] * Math.cos(a) - v[1] * Math.sin(a), v[0] * Math.sin(a) + v[1] * Math.cos(a)];
  const add = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k];
  const deg = Math.PI / 180;
  const lerp = (a, b, t) => a + (b - a) * t;

  // arm of the right wing (mirrored for the left)
  const ARM = [[1590, 1520], [1820, 1300], [2060, 1080], [2290, 900]];

  const PRIMARY = [[0, C.deepCrimson], [0.35, C.crimson], [0.62, C.red], [0.82, C.burnt], [1, C.gold]];
  const SECOND = [[0, C.crimson], [0.5, C.burnt], [1, C.orange]];
  const COVERT = [[0, C.burnt], [0.55, C.orange], [1, C.gold]];
  const SMALL = [[0, C.orange], [0.7, C.gold], [1, C.yellow]];

  function wing(side) {
    const m = (p) => side > 0 ? p : [2 * CX - p[0], p[1]];
    const N = 14;
    const feathers = [];
    for (let j = 0; j < N; j++) {
      const u = j / (N - 1);
      const root = cubic(...ARM, 0.12 + 0.88 * u);
      const ang = lerp(52, -74, Math.pow(u, 0.85)) * deg;
      const len = 640 + 420 * Math.pow(u, 0.7) - (u > 0.9 ? (u - 0.9) * 900 : 0);
      feathers.push({ u, root, ang, len, w: 150 + 45 * u });
    }
    const spine = (f, lenK, rootShift = 0, bend = 1) => {
      const dir = [Math.cos(f.ang), Math.sin(f.ang)];
      const r = add(f.root, dir, rootShift);
      const perp = [dir[1], -dir[0]];
      const l = f.len * lenK;
      const p1 = add(r, dir, l * 0.33);
      const p2 = add(add(r, dir, l * 0.68), perp, -l * 0.05 * bend);
      const tipDir = rot(dir, -14 * deg * bend);
      const p3 = add(r, tipDir, l);
      return [r, p1, p2, p3].map(m);
    };
    // primaries + secondaries: outermost drawn first
    for (let j = N - 1; j >= 0; j--) {
      const f = feathers[j];
      feather(spine(f, 1, 0, 1.5), f.w, PRIMARY, {
        rachis: C.gold,
        band: [0.71, 0.745, C.blue],
        bend: 1.4,
      });
    }
    // greater coverts
    for (let j = N - 1; j >= 0; j--) {
      const f = feathers[j];
      feather(spine(f, 0.56, -10, 0.6), f.w * 0.92, SECOND, { profile: PROFILES.covert, rachis: C.yellow, rachisEnd: 0.8 });
    }
    // median coverts
    for (let j = N - 1; j >= 0; j -= 1) {
      const f = feathers[j];
      feather(spine(f, 0.33, -20, 0.3), f.w * 0.78, COVERT, { profile: PROFILES.covert, rachis: C.cream, rachisEnd: 0.75, shadow: 0.55 });
    }
    // lesser coverts: small scales along the arm, two rows
    for (let row = 0; row < 2; row++) {
      const K = 16 - row * 2;
      for (let k = K - 1; k >= 0; k--) {
        const u = 0.08 + 0.9 * k / (K - 1);
        const root = cubic(...ARM, u);
        const ang = lerp(52, -74, Math.pow(u, 0.85)) * deg + 10 * deg;
        const dir = [Math.cos(ang), Math.sin(ang)];
        const r = add(add(root, dir, -40 - row * 50), [dir[1], -dir[0]], -10);
        const l = 150 - row * 35;
        feather([r, add(r, dir, l * 0.35), add(r, dir, l * 0.7), add(r, dir, l)].map(m), 92 - row * 16, SMALL,
          { profile: PROFILES.scale, rachis: false, slant: 0.7, shadow: 0.6 });
      }
    }
  }

  function tail() {
    // flowing hōō tail plumes: S-curves that sweep out and curl back up
    const specs = [
      [[-30, 0], [-260, 520], [-1000, 860], [-1020, 300], 175],
      [[-20, 0], [-160, 620], [-720, 1020], [-760, 700], 165],
      [[-10, 0], [-80, 700], [-420, 1080], [-360, 1240], 155],
      [[0, 0], [60, 640], [-70, 1000], [0, 1330], 160],
    ];
    const base = [CX, 2160];
    const all = [];
    for (const [a, b, c, d, w] of specs) {
      all.push([a, b, c, d, w]);
      if (a[0] !== 0 || d[0] !== 0) all.push([[-a[0], a[1]], [-b[0], b[1]], [-c[0], c[1]], [-d[0], d[1]], w]);
    }
    for (const [a, b, c, d, w] of all) {
      const P = [add(base, a), add(base, b), add(base, c), add(base, d)];
      const bl = feather(P, w * 1.4, [[0, C.burnt], [0.35, C.red], [0.65, C.crimson], [0.78, C.deepCrimson], [1, C.crimson]], {
        profile: (t) => (0.6 + 0.45 * Math.exp(-Math.pow((t - 0.84) / 0.09, 2))) * Math.pow(Math.sin(Math.PI * (0.03 + 0.97 * t)), 0.45),
        slant: 1.6, rachis: C.gold, rachisEnd: 0.75,
      });
      const i = Math.floor(bl.n * 0.84), p = bl.S[i];
      const q = bl.S[Math.min(bl.n - 1, i + 3)];
      const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
      const rings = [[bl.W[i] * 0.8, C.gold], [bl.W[i] * 0.68, C.blue], [bl.W[i] * 0.42, C.cream], [bl.W[i] * 0.22, C.blueDark]];
      for (const [r, col] of rings) {
        const e = new Path2D();
        e.ellipse(p[0], p[1], r * 1.25, r, ang, 0, Math.PI * 2);
        raiseShadow(e, 0.35, 2, 4, 4);
        underlay(e, col);
        tatami(e, [p[0] - r * 1.3, p[1] - r * 1.3, p[0] + r * 1.3, p[1] + r * 1.3], () => col, ang + Math.PI / 2, 22);
      }
      const ring = [];
      for (let a2 = 0; a2 <= Math.PI * 2 + 0.05; a2 += 0.06)
        ring.push([p[0] + Math.cos(a2) * bl.W[i] * 1.07 * Math.cos(ang) - Math.sin(a2) * bl.W[i] * 0.86 * Math.sin(ang),
                   p[1] + Math.cos(a2) * bl.W[i] * 1.07 * Math.sin(ang) + Math.sin(a2) * bl.W[i] * 0.86 * Math.cos(ang)]);
      stem(ring, C.darkBrown, TW * 1.1);
    }
  }

  function tailCoverts() {
    const base = [CX, 2010];
    const N = 9;
    for (let pass = 0; pass < 2; pass++) {
      const order = [...Array(N).keys()].sort((a, b) => Math.abs(b - (N - 1) / 2) - Math.abs(a - (N - 1) / 2));
      for (const k of order) {
        const u = k / (N - 1) - 0.5;
        const ang = (90 + u * (pass ? 80 : 110)) * deg;
        const len = pass ? 330 : 470;
        const dir = [Math.cos(ang), Math.sin(ang)];
        const r = add(base, [u * (pass ? 180 : 300), pass * 60]);
        const perp = [dir[1], -dir[0]];
        const P = [r, add(r, dir, len * 0.35), add(add(r, dir, len * 0.7), perp, u * 40), add(r, rot(dir, u * 0.25), len)];
        feather(P, pass ? 140 : 170, pass ? COVERT : SECOND, { profile: PROFILES.covert, rachis: pass ? C.cream : C.yellow,
          rachisEnd: 0.8, band: pass ? null : [0.78, 0.82, C.blue] });
      }
    }
  }

  function body() {
    // teardrop silhouette from neck base to tail root
    const pts = [];
    for (let i = 0; i <= 80; i++) {
      const t = i / 80, y = lerp(1290, 2230, t);
      const w = 300 * Math.pow(Math.sin(Math.PI * Math.min(1, 0.15 + t * 0.95)), 0.8) * (1 - 0.25 * t);
      pts.push([CX + w, y]);
    }
    const left = pts.map((p) => [2 * CX - p[0], p[1]]).reverse();
    const sil = pts.concat(left);
    const path = pathOf(sil);
    sil.forEach((p) => track(p[0], p[1], 10));
    raiseShadow(path, 0.6, 6, 10, 10);
    underlay(path, C.burnt);
    if (!MEASURE) { ctx.save(); ctx.clip(path); }
    // scale feathers, bottom rows first so upper rows overlap
    const rowH = 64;
    for (let y = 2260, r = 0; y >= 1240; y -= rowH, r++) {
      const off = (r % 2) * 42;
      for (let x = CX - 340 - off; x <= CX + 340; x += 84) {
        const t = (y - 1240) / 1020;
        const stops = r % 2 ? [[0, C.burnt], [0.7, C.orange], [1, C.yellow]] : [[0, C.crimson], [0.6, C.burnt], [1, C.gold]];
        const P = [[x, y - 80], [x + jit(4), y - 50], [x + jit(4), y - 20], [x, y + 18]];
        feather(P, 92, t > 0.75 ? stops : stops, { profile: PROFILES.scale, rachis: false, slant: 0.8, shadow: 0.5 });
      }
    }
    if (!MEASURE) ctx.restore();
    stem(sil.concat([sil[0]]), C.darkBrown, TW * 1.4);
  }

  function scaleFill(path, x0, x1, yTop, yBot, sz, stopsA, stopsB) {
    if (!MEASURE) { ctx.save(); ctx.clip(path); }
    const rowH = sz * 0.72;
    for (let y = yBot, r = 0; y >= yTop; y -= rowH, r++) {
      const off = (r % 2) * sz * 0.5;
      for (let x = x0 - off; x <= x1; x += sz * 0.95) {
        const P = [[x, y - sz * 0.9], [x + jit(4), y - sz * 0.55], [x + jit(4), y - sz * 0.2], [x, y + sz * 0.2]];
        feather(P, sz * 1.08, r % 2 ? stopsA : stopsB, { profile: PROFILES.scale, rachis: false, slant: 0.8, shadow: 0.5 });
      }
    }
    if (!MEASURE) ctx.restore();
  }

  function headAndNeck() {
    const hx = 1450, hy = 930;
    // short curved neck filled with small scale feathers
    const nb = blade([[CX, 1480], [CX + 25, 1260], [1490, 1100], [hx + 10, hy + 40]], 340, (t) => 1 - 0.3 * t);
    const npts = outlinePts(nb), npath = pathOf(npts);
    raiseShadow(npath, 0.55, 5, 9, 9);
    underlay(npath, C.burnt);
    scaleFill(npath, 1250, 1750, hy, 1500, 72,
      [[0, C.burnt], [0.7, C.orange], [1, C.yellow]], [[0, C.red], [0.6, C.burnt], [1, C.gold]]);
    stem(npts.concat([npts[0]]), C.darkBrown, TW * 1.3);
    // hackles: long flowing neck plumes cascading over the chest
    const hack = [];
    for (let k = 0; k < 11; k++) {
      const u = k / 10 - 0.5;                         // -0.5..0.5
      const r = [hx + 20 + u * 260, hy + 60 + Math.abs(u) * 40];
      const sway = (k % 2 ? 1 : -1) * 30;
      const end = [CX + u * 520, 1560 + (0.5 - Math.abs(u)) * 160];
      hack.push([[r, [r[0] + sway, r[1] + 200], [end[0] - sway * 1.5, end[1] - 220], end], 120 - Math.abs(u) * 50, Math.abs(u)]);
    }
    hack.sort((a, b) => b[2] - a[2]);
    for (const [P, w] of hack) {
      feather(P, w, [[0, C.gold], [0.45, C.orange], [0.8, C.burnt], [1, C.crimson]],
        { profile: PROFILES.plume, slant: 1.3, rachis: C.yellow, rachisEnd: 0.8, shadow: 0.55 });
    }
    // crest: flowing, flame-like plumes sweeping back
    const crest = [
      [[hx + 40, hy - 90], [1520, 620], [1700, 520], [1660, 260], 120],
      [[hx + 70, hy - 70], [1650, 700], [1860, 680], [1930, 430], 130],
      [[hx + 90, hy - 40], [1760, 820], [2010, 860], [2140, 690], 110],
      [[hx + 100, hy - 10], [1800, 960], [2020, 1060], [2180, 1000], 90],
      [[hx + 10, hy - 100], [1420, 640], [1510, 470], [1430, 330], 90],
    ];
    for (const [a, b, c, d, w] of crest) {
      feather([a, b, c, d], w, [[0, C.deepCrimson], [0.35, C.crimson], [0.65, C.red], [0.88, C.burnt], [1, C.gold]],
        { profile: PROFILES.plume, slant: 1.4, rachis: C.gold, rachisEnd: 0.85 });
    }
    // head
    const RX = 150, RY = 118, HA = -0.35;
    const head = new Path2D(); head.ellipse(hx, hy, RX, RY, HA, 0, Math.PI * 2);
    track(hx, hy, 170);
    raiseShadow(head, 0.6);
    underlay(head, C.orange);
    tatami(head, [hx - 170, hy - 170, hx + 170, hy + 170],
      (x, y) => ramp([[0, C.yellow], [0.4, C.gold], [0.75, C.orange], [1, C.red]], (y - hy + 130) / 260), -0.7, 26);
    const hr = [];
    for (let a = 0; a <= Math.PI * 2 + 0.05; a += 0.04) {
      const ex = Math.cos(a) * RX, ey = Math.sin(a) * RY, c = Math.cos(HA), s2 = Math.sin(HA);
      hr.push([hx + ex * c - ey * s2, hy + ex * s2 + ey * c]);
    }
    stem(hr, C.darkBrown, TW * 1.35);
    // crimson mask sweeping back from the eye
    satin([[hx - 95, hy - 25], [hx - 30, hy - 45], [hx + 40, hy - 40], [hx + 140, hy - 10]], 58,
      [[0, C.deepCrimson], [1, C.crimson]], { profile: (t) => 0.55 + 0.45 * Math.sin(Math.PI * t), slant: 0.3 });
    // almond eye: gold iris, dark pupil
    const ex = hx - 40, ey = hy - 40;
    const almond = [];
    for (let a = 0; a <= Math.PI * 2 + 0.01; a += 0.1) {
      const xx = Math.cos(a) * 44, yy = Math.sin(a) * 20 * (1 - 0.35 * Math.cos(a));
      almond.push([ex + xx * Math.cos(-0.25) - yy * Math.sin(-0.25), ey + xx * Math.sin(-0.25) + yy * Math.cos(-0.25)]);
    }
    const eye = pathOf(almond);
    underlay(eye, C.gold);
    tatami(eye, [ex - 50, ey - 30, ex + 50, ey + 30], () => C.gold, 1.3, 12);
    const pupil = new Path2D(); pupil.arc(ex - 6, ey + 1, 13, 0, Math.PI * 2);
    tatami(pupil, [ex - 21, ey - 14, ex + 9, ey + 16], () => C.darkBrown, 1.2, 10);
    if (!MEASURE) { ctx.fillStyle = 'rgba(255,250,235,0.92)'; ctx.beginPath(); ctx.arc(ex - 11, ey - 4, 4, 0, 7); ctx.fill(); }
    stem(almond, C.darkBrown, TW * 1.1, 10);
    // hooked beak, open in a cry
    satin([[hx - 120, hy - 20], [hx - 220, hy - 95], [hx - 330, hy - 105], [hx - 350, hy - 20]], 96,
      [[0, C.gold], [0.7, C.yellow], [1, C.cream]], { profile: (t) => Math.pow(1 - t, 0.7), slant: 0.4 });
    satin([[hx - 115, hy + 35], [hx - 190, hy + 25], [hx - 250, hy + 5], [hx - 290, hy - 20]], 54,
      [[0, C.burnt], [1, C.gold]], { profile: (t) => Math.pow(1 - t, 0.75), slant: 0.4 });
    // wattle plumes under the beak
    feather([[hx - 80, hy + 80], [hx - 120, hy + 180], [hx - 190, hy + 240], [hx - 280, hy + 260]], 80,
      [[0, C.crimson], [1, C.burnt]], { profile: PROFILES.plume, slant: 1.3, rachis: C.gold });
  }

  // Organic fire mass: layered satin tongues with S-curves and curling tips.
  function flames(layer) {
    const cfg = {
      back: { n: 15, span: 900, hMax: 1300, hMin: 520, w: [190, 260], y: 3700,
              stops: [[0, C.deepCrimson], [0.45, C.crimson], [0.8, C.red], [1, C.burnt]] },
      mid: { n: 12, span: 780, hMax: 900, hMin: 380, w: [150, 210], y: 3720,
             stops: [[0, C.crimson], [0.35, C.red], [0.7, C.burnt], [1, C.orange]] },
      front: { n: 10, span: 640, hMax: 520, hMin: 260, w: [120, 170], y: 3740,
               stops: [[0, C.burnt], [0.4, C.orange], [0.8, C.gold], [1, C.yellow]] },
    }[layer];
    const items = [];
    for (let k = 0; k < cfg.n; k++) {
      const u = k / (cfg.n - 1) * 2 - 1;                       // -1..1
      const x = CX + u * cfg.span + jit(25);
      const env = Math.pow(Math.cos(u * Math.PI / 2), 0.8);
      const h = cfg.hMin + (cfg.hMax - cfg.hMin) * env * (0.8 + rand() * 0.3);
      const w = cfg.w[0] + rand() * (cfg.w[1] - cfg.w[0]);
      const lean = u * 160 + jit(60);
      const wave = (rand() < 0.5 ? -1 : 1) * (40 + rand() * 60);
      items.push({ x, h, w, lean, wave, d: Math.abs(u), y0: cfg.y - (1 - env) * 170 + jit(15) });
    }
    // outer tongues first so the centre ones sit on top
    items.sort((a, b) => b.d - a.d);
    for (const it of items) {
      const y = it.y0;
      const P = [[it.x, y], [it.x + it.wave, y - it.h * 0.35], [it.x - it.wave * 1.6 + it.lean * 0.4, y - it.h * 0.7],
                 [it.x + it.wave * 1.2 + it.lean, y - it.h]];
      satin(P, it.w, cfg.stops, { profile: PROFILES.flame, slant: 0.45 });
      if (layer !== 'front') {
        const P2 = [[it.x, y - 10], [it.x + it.wave * 0.8, y - it.h * 0.3], [it.x - it.wave * 1.2 + it.lean * 0.3, y - it.h * 0.52],
                    [it.x + it.wave * 0.6 + it.lean * 0.6, y - it.h * 0.68]];
        satin(P2, it.w * 0.5, layer === 'back' ? [[0, C.crimson], [0.6, C.burnt], [1, C.orange]] : [[0, C.burnt], [0.6, C.orange], [1, C.gold]],
          { profile: PROFILES.flame, slant: 0.45 });
      }
    }
    if (layer === 'mid') {
      // detached flickers
      const fl = [[-620, 2650, -1], [600, 2620, 1], [-380, 2520, 1], [380, 2500, -1], [-820, 2900, 1], [820, 2880, -1]];
      for (const [dx, y, s2] of fl) {
        const x = CX + dx;
        satin([[x, y], [x + 30 * s2, y - 60], [x - 20 * s2, y - 120], [x + 40 * s2, y - 190]], 70,
          [[0, C.red], [0.6, C.burnt], [1, C.gold]], { profile: PROFILES.flame, slant: 0.4 });
      }
    }
  }

  function scene() {
    cloud(640, 3420, 170, 1);
    cloud(2360, 3440, 170, -1);
    cloud(330, 2300, 100, -1);
    cloud(2670, 2260, 100, 1);
    flames('back');
    flames('mid');
    tail();
    tailCoverts();
    wing(1);
    wing(-1);
    body();
    headAndNeck();
    flames('front');
    const embers = [[760, 2930, 26], [2250, 2900, 30], [960, 2700, 18], [2050, 2690, 20], [600, 3050, 16], [2420, 3040, 18],
                    [1180, 3020, 16], [1830, 3010, 16], [880, 2380, 14], [2120, 2360, 14]];
    for (const [x, y, r] of embers) ember(x + jit(10), y + jit(10), r, C.burnt);
  }

  window.renderPhoenix = function (canvas, s = 1) {
    // pass 1: measure geometry
    MEASURE = true; bb = [1e9, 1e9, -1e9, -1e9]; seed(s); scene();
    const bw = bb[2] - bb[0], bh = bb[3] - bb[1];
    const k = Math.min((W - 2 * MARGIN) / bw, (H - 2 * MARGIN) / bh);
    const ox = (W - bw * k) / 2 - bb[0] * k, oy = (H - bh * k) / 2 - bb[1] * k;
    // pass 2: draw
    MEASURE = false; seed(s);
    canvas.width = W; canvas.height = H;
    ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, W, H);
    ctx.setTransform(k, 0, 0, k, ox, oy);
    scene();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    return { scale: k, bbox: bb };
  };
})();
