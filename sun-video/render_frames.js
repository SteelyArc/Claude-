// node render_frames.js <html> <outDir> <scale> <fps> <worker> <workers> [times...]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [html, outDir, scale, fps, wi, wn, ...extra] = process.argv.slice(2);
const THREE_LOCAL = process.env.THREE_LOCAL;
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('page error:', e.message));
  p.on('console', m => { if (m.type() === 'error' || /ERROR|warning X/.test(m.text())) console.error('console:', m.text().slice(0, 2000)); });
  await p.route('**/three.min.js', r => r.fulfill({ path: THREE_LOCAL, contentType: 'application/javascript' }));
  await p.goto('file://' + path.resolve(html) + `?capture&scale=${scale}`);
  await p.waitForFunction(() => typeof window.renderAt === 'function');
  await p.evaluate(() => document.fonts.ready);
  const dur = await p.evaluate(() => window.DURATION);
  fs.mkdirSync(outDir, { recursive: true });
  let times;
  if (extra.length) times = extra.map(Number).map((t, i) => [t, `s${String(i).padStart(3, '0')}`]);
  else { const n = Math.round(dur * fps); times = []; for (let i = Number(wi); i < n; i += Number(wn)) times.push([i / fps, `f${String(i).padStart(5, '0')}`]); }
  const t0 = Date.now();
  for (const [t, name] of times) {
    const f = `${outDir}/${name}.jpg`;
    if (fs.existsSync(f)) continue;
    await p.evaluate(t => window.renderAt(t), t);
    await p.screenshot({ path: f + '.tmp', type: 'jpeg', quality: 95 });
    fs.renameSync(f + '.tmp', f);
  }
  console.error(`worker ${wi}: ${times.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  await b.close();
})();
