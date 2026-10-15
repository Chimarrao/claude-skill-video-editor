import puppeteer from 'puppeteer-core';
import fs from 'fs';
const shots = JSON.parse(fs.readFileSync('/tmp/pp/shots.json'));
const only = process.argv.slice(2);
const b = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--no-sandbox'],
  defaultViewport: {width: 1800, height: 1000},
});
const p = await b.newPage();
await p.goto('http://localhost:9000', {waitUntil: 'networkidle2'});
await new Promise(r => setTimeout(r, 10000));
const cur = async () =>
  p.evaluate(() => {
    const m = document.body.innerText.match(/\[(\d+)\]/);
    return m ? Number(m[1]) : -1;
  });
let pan = 0;
for (const [id, f] of shots) {
  if (only.length && !only.includes(id)) continue;
  const want = f < 3400 ? 0 : 1200;
  if (want !== pan) {
    await p.mouse.move(1300, 900);
    await p.mouse.wheel({deltaX: want - pan});
    pan = want;
    await new Promise(r => setTimeout(r, 800));
  }
  let x = 926 + 0.1113 * f - pan;
  for (let k = 0; k < 3; k++) {
    await p.mouse.click(x, 830);
    await new Promise(r => setTimeout(r, 900));
    const c = await cur();
    const d = f - c;
    if (Math.abs(d) <= 6) break;
    x += d * 0.1113;
  }
  await new Promise(r => setTimeout(r, 1500));
  await p.screenshot({path: `/tmp/pp/s_${id}.png`, clip: {x: 454, y: 0, width: 1346, height: 762}});
}
await b.close();
console.log('done');
