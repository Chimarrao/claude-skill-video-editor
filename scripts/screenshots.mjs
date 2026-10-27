// Screenshots do editor (porta 9000) em instantes dados: confere cada cena ANTES do render. Espera ≥ 7 s depois de cada clique (itens recém-criados carregam a imagem depois).
// Uso (copie para uma pasta com `npm i puppeteer-core`): node screenshots.mjs <frames_totais> <shots.json> [prefixo]   (shots = [[nome, segundos], ...]; 30 fps)
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const total = Number(process.argv[2]);
const shots = JSON.parse(fs.readFileSync(process.argv[3]));
const pref = process.argv[4] || 's_';
const escala = 1745 / total;
const b = await puppeteer.launch({executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: 'new', args: ['--no-sandbox'], defaultViewport: {width: 1800, height: 1000}});
const p = await b.newPage();
p.on('pageerror', e => console.log('PAGEERR', e.message));
p.on('console', m => {
  if (m.type() === 'error' && !/Connection timeout|Outdated Optimize|asynchronous property|Img2|collectPromise|^Error$/.test(m.text())) console.log('ERR', m.text().slice(0, 300));
});
await p.goto('http://localhost:9000', {waitUntil: 'networkidle2'});
await new Promise(r => setTimeout(r, 12000));
const cur = async () => p.evaluate(() => { const m = document.body.innerText.match(/\[(\d+)\]/); return m ? Number(m[1]) : -1; });
let pan = 0;
for (const [nome, seg] of shots) {
  const f = Math.round(seg * 30);
  let x = 926 + escala * f - pan;
  if (x > 1680 || x < 120) {
    const novo = Math.max(0, 926 + escala * f - 900);
    await p.mouse.move(1300, 900);
    await p.mouse.wheel({deltaX: novo - pan});
    pan = novo;
    await new Promise(r => setTimeout(r, 800));
    x = 926 + escala * f - pan;
  }
  for (let k = 0; k < 4; k++) {
    await p.mouse.click(x, 830);
    await new Promise(r => setTimeout(r, 900));
    const c = await cur();
    const d = f - c;
    if (Math.abs(d) <= 5) break;
    x += d * escala;
  }
  await new Promise(r => setTimeout(r, 7000));
  await p.screenshot({path: `/tmp/pp/${pref}${nome}.png`, clip: {x: 454, y: 0, width: 1346, height: 762}});
}
await b.close();
console.log('done');
