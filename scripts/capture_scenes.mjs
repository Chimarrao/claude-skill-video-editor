import puppeteer from 'puppeteer-core';
import fs from 'fs';
// uso: node capture_scenes.mjs <total_frames> <shots_file.json> [prefix]   (shots = [[name, segundos], ...])
const total = Number(process.argv[2]);
const shots = JSON.parse(fs.readFileSync(process.argv[3]));
const prefix = process.argv[4] || 's_';
const scale = 1745 / total;
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--no-sandbox'],
  defaultViewport: {width: 1800, height: 1000},
});
const page = await browser.newPage();
page.on('pageerror', e => console.log('PAGEERR', e.message));
page.on('console', m => {
  if (m.type() === 'error' && !/Connection timeout|Outdated Optimize/.test(m.text()))
    console.log('ERR', m.text().slice(0, 300));
});
await page.goto('http://localhost:9000', {waitUntil: 'networkidle2'});
await new Promise(r => setTimeout(r, 12000));
const cur = async () =>
  page.evaluate(() => {
    const m = document.body.innerText.match(/\[(\d+)\]/);
    return m ? Number(m[1]) : -1;
  });
let pan = 0;
for (const [name, sec] of shots) {
  const f = Math.round(sec * 30);
  let x = 926 + scale * f - pan;
  if (x > 1680 || x < 120) {
    const newPan = Math.max(0, 926 + scale * f - 900);
    await page.mouse.move(1300, 900);
    await page.mouse.wheel({deltaX: newPan - pan});
    pan = newPan;
    await new Promise(r => setTimeout(r, 800));
    x = 926 + scale * f - pan;
  }
  for (let k = 0; k < 4; k++) {
    await page.mouse.click(x, 830);
    await new Promise(r => setTimeout(r, 900));
    const c = await cur();
    const d = f - c;
    if (Math.abs(d) <= 5) break;
    x += d * scale;
  }
  await new Promise(r => setTimeout(r, 1400));
  await page.screenshot({path: `/tmp/pp/${prefix}${name}.png`, clip: {x: 454, y: 0, width: 1346, height: 762}});
}
await browser.close();
console.log('done');
