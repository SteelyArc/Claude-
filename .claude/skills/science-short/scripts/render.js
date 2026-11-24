// Render a science-short HTML page to MP4, frame by frame (deterministic).
// Usage: node render.js <page.html> <out.mp4> [--fps 30] [--stills 0,1.5,3]
// The page must expose window.renderAt(t) and window.DURATION, and stay still when loaded with ?capture.
// CDN scripts are served from local copies when the network blocks the CDN (see LOCAL_LIBS).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const args = process.argv.slice(2);
const page = path.resolve(args[0]);
const out = path.resolve(args[1] || page.replace(/\.html$/, '.mp4'));
const opt = (k, d) => { const i = args.indexOf(k); return i > -1 ? args[i + 1] : d; };
const fps = Number(opt('--fps', 30));
const stills = opt('--stills', null);

// Map CDN file names to local copies, e.g. after `npm i three@0.128.0` in this folder.
const LOCAL_LIBS = { 'three.min.js': path.join(__dirname, 'node_modules/three/build/three.min.js') };

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('page error:', e.message));
  for (const [name, file] of Object.entries(LOCAL_LIBS)) {
    if (fs.existsSync(file)) await p.route('**/' + name, r => r.fulfill({ path: file, contentType: 'application/javascript' }));
  }
  await p.goto('file://' + page + '?capture');
  await p.waitForFunction(() => typeof window.renderAt === 'function');
  const duration = await p.evaluate(() => window.DURATION);
  const dir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'frames-'));
  const times = stills ? stills.split(',').map(Number) : Array.from({ length: Math.round(duration * fps) }, (_, i) => i / fps);
  for (let i = 0; i < times.length; i++) {
    await p.evaluate(t => window.renderAt(t), times[i]);
    await p.screenshot({ path: `${dir}/f${String(i).padStart(5, '0')}.png` });
  }
  await browser.close();
  if (stills) {
    const sheet = out.replace(/\.mp4$/, '') + '-stills.png';
    execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-i', `${dir}/f%05d.png`, '-filter_complex', `scale=360:640,tile=${times.length}x1`, sheet]);
    console.log('contact sheet:', sheet);
  } else {
    execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-framerate', String(fps), '-i', `${dir}/f%05d.png`,
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', out]);
    console.log('video:', out);
  }
  fs.rmSync(dir, { recursive: true, force: true });
})();
