// Renderiza UM trecho do overlay (o `range` já está em src/project.meta) e sai sozinho quando o arquivo para de crescer e o ffmpeg termina.
// Usado por render_slices.sh. Uso (em animacao/, com o vite na porta 9000): OUT="$PWD/output" node render_one.mjs
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import {execSync} from 'child_process';

const OUT = process.env.OUT || 'output';
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--no-sandbox', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'],
  defaultViewport: {width: 1800, height: 1000},
});
const page = await browser.newPage();
page.on('console', m => {
  const t = m.text();
  if (m.type() === 'error' && !/Connection timeout|asynchronous property|Img2|collectPromise|^Error$/.test(t))
    console.log(new Date().toISOString(), 'C', t.slice(0, 160));
});
page.on('pageerror', e => console.log('PAGEERR', e.message));
await page.goto('http://localhost:9000', {waitUntil: 'networkidle2'});
await new Promise(r => setTimeout(r, 25000));
await page.mouse.click(300, 642); // botão RENDER do painel de configurações
console.log(new Date().toISOString(), 'clicked render');
const file = OUT + '/project.mov';
let last = -1;
let parado = 0;
while (true) {
  await new Promise(r => setTimeout(r, 20000));
  const size = fs.existsSync(file) ? fs.statSync(file).size : 0;
  let ffmpeg = false;
  try {
    execSync('pgrep -f "@ffmpeg-installer"');
    ffmpeg = true;
  } catch (e) {}
  console.log(new Date().toISOString(), size, ffmpeg ? 'ffmpeg' : 'sem-ffmpeg');
  parado = size > 0 && size === last && !ffmpeg ? parado + 1 : 0; // arquivo estável e ffmpeg encerrado, 2 vezes seguidas = trecho pronto
  last = size;
  if (parado >= 2) break;
}
await browser.close();
console.log('FIM-DO-TRECHO');
