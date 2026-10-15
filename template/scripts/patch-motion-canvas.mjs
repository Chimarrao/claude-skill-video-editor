// Ajustes em node_modules (rodam no postinstall; idempotentes):
// 1) editor abre com áudio ligado (padrão do Motion Canvas é mudo);
// 2) exportador FFmpeg gera .mov ProRes 4444 com canal alpha (o padrão é mp4 sem transparência).
import fs from 'node:fs';

function patch(file, pares) {
  if (!fs.existsSync(file)) return console.log('ignorado (não existe):', file);
  let s = fs.readFileSync(file, 'utf8');
  for (const [de, para] of pares) s = s.split(de).join(para);
  fs.writeFileSync(file, s);
  console.log('ok:', file);
}

patch('node_modules/@motion-canvas/core/lib/app/Player.js', [['muted: true,', 'muted: false,']]);
patch('node_modules/@motion-canvas/ffmpeg/lib/server/FFmpegExporterServer.js', [
  ['`${settings.name}.mp4`', '`${settings.name}.mov`'],
  [
    "['-pix_fmt yuv420p', '-shortest']",
    "['-c:v prores_ks', '-profile:v 4444', '-pix_fmt yuva444p10le', '-alpha_bits 16', '-vendor apl0', '-shortest']",
  ],
]);
try {
  fs.chmodSync('node_modules/@ffmpeg-installer/darwin-x64/ffmpeg', 0o755);
} catch {}
fs.rmSync('node_modules/.vite', {recursive: true, force: true}); // cache pré-empacotado ignoraria o patch do Player
