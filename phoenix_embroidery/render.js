// Render the phoenix embroidery to a transparent RGBA PNG.
// usage: node phoenix_embroidery/render.js [out.png] [seed]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const out = path.resolve(process.argv[2] || path.join(__dirname, '..', 'phoenix_embroidery.png'));
  const seed = parseInt(process.argv[3] || '1988', 10);
  const code = fs.readFileSync(path.join(__dirname, 'phoenix.js'), 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent('<!doctype html><html><body style="margin:0;background:transparent"><canvas id="c"></canvas></body></html>');
  await page.addScriptTag({ content: code });
  const info = await page.evaluate((s) => {
    const c = document.getElementById('c');
    const r = window.renderPhoenix(c, s);
    return { ...r, data: c.toDataURL('image/png') };
  }, seed);
  fs.writeFileSync(out, Buffer.from(info.data.split(',')[1], 'base64'));
  console.log('wrote', out, 'scale', info.scale.toFixed(3));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
