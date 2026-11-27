// Rasterise an SVG to a transparent RGBA PNG with headless Chromium.
// usage: node render.js in.svg out.png width height
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const [svgPath, pngPath, w, h] = process.argv.slice(2);
  const width = parseInt(w, 10), height = parseInt(h, 10);
  const svg = fs.readFileSync(svgPath, 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent(
    `<!doctype html><html><head><style>html,body{margin:0;padding:0;background:transparent}svg{display:block}</style></head><body>${svg}</body></html>`
  );
  await page.screenshot({ path: pngPath, omitBackground: true, clip: { x: 0, y: 0, width, height } });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
