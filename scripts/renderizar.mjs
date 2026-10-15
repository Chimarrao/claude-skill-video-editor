import puppeteer from 'puppeteer-core';
import fs from 'fs';
try {
  const pv = JSON.parse(fs.readFileSync('src/scenes/previa.json', 'utf8'));
  if (pv.ativa)
    console.log(
      'AVISO: PREVIA_BROLL ativa — o motor a ignora ao renderizar, mas confirme PREVIA_BROLL=False no plano_dados.py',
    );
} catch (e) {}
const OUT = process.env.OUT || '/tmp/none';
const b = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: [
    '--no-sandbox',
    '--disable-background-timer-throttling',
    '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows',
  ],
  defaultViewport: {width: 1800, height: 1000},
});
const p = await b.newPage();
p.on('console', m => {
  const t = m.text();
  if (m.type() === 'error' || /render|ffmpeg/i.test(t))
    console.log(new Date().toISOString(), 'C', m.type(), t.slice(0, 200));
});
p.on('pageerror', e => console.log('PAGEERR', e.message));
await p.goto('http://localhost:9000', {waitUntil: 'networkidle2'});
await new Promise(r => setTimeout(r, 25000));
const txt = await p.evaluate(() => document.body.innerText);
console.log('SETTINGS OK?', /2\.0x/.test(txt), /Video \(FFmpeg\)/.test(txt));
await p.screenshot({path: '/tmp/pp/render_before.png', clip: {x: 0, y: 0, width: 460, height: 760}});
await p.mouse.click(300, 642);
console.log(new Date().toISOString(), 'clicked render');
try {
  fs.unlinkSync('/tmp/pp/render.stop');
} catch (e) {}
const t0 = Date.now();
while (true) {
  await new Promise(r => setTimeout(r, 30000));
  const t = await p.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 400));
  const files = fs.existsSync(OUT) ? fs.readdirSync(OUT).map(f => [f, fs.statSync(OUT + '/' + f).size]) : [];
  console.log(Math.round((Date.now() - t0) / 1000) + 's', JSON.stringify(files), '|', t.slice(0, 160));
  await p.screenshot({path: '/tmp/pp/render_now.png', clip: {x: 0, y: 0, width: 460, height: 760}}).catch(() => {});
  if (fs.existsSync('/tmp/pp/render.stop')) break;
}
await b.close();
