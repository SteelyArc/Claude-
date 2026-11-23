const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const [, , outDir, ...times] = process.argv; fs.mkdirSync(outDir, { recursive: true });
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 600, height: 1000 } });
  p.on('console', m => { if (m.type() === 'error' || m.type()==='warning') console.log('PAGE', m.type(), m.text()); }); p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('http://localhost:8123/index.html'); await p.waitForFunction('window.ready===true', null, { timeout: 60000 });
  for (const t of times) { const t0=Date.now(); const d = await p.evaluate(t => renderFrame(+t), t); fs.writeFileSync(`${outDir}/t${(+t).toFixed(1)}.jpg`, Buffer.from(d.split(',')[1], 'base64')); console.log(t, Date.now()-t0,'ms'); }
  await b.close();
})();
