const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const [, , outDir, w, nw, fps, total] = process.argv; fs.mkdirSync(outDir, { recursive: true });
  const N = Math.round(+fps * +total);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 600, height: 1000 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('http://localhost:8123/index.html'); await p.waitForFunction('window.ready===true', null, { timeout: 60000 });
  let done = 0; const t0 = Date.now();
  for (let i = +w; i < N; i += +nw) {
    const f = `${outDir}/${String(i).padStart(5, '0')}.jpg`; if (fs.existsSync(f)) continue;
    const d = await p.evaluate(t => renderFrame(t), i / +fps);
    fs.writeFileSync(f + '.tmp', Buffer.from(d.split(',')[1], 'base64')); fs.renameSync(f + '.tmp', f);
    if (++done % 300 === 0) console.log(`w${w} ${done} frames ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  console.log(`w${w} DONE`); await b.close();
})();
