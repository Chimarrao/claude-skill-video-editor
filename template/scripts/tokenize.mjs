// codes_source.json -> src/scenes/codes.json com tokens coloridos no tema Monokai (highlight.js).
import fs from 'node:fs';
import hljs from 'highlight.js';

const MK = {
  text: '#f8f8f2',
  comment: '#75715e',
  pink: '#f92672',
  orange: '#fd971f',
  yellow: '#e6db74',
  green: '#a6e22e',
  blue: '#66d9ef',
  purple: '#ae81ff',
};
const MAP = [
  [/^hljs-comment|^hljs-quote/, MK.comment],
  [/^hljs-string|^hljs-template-variable|^hljs-regexp|^hljs-char/, MK.yellow],
  [/^hljs-number|^hljs-literal|^hljs-symbol|^hljs-bullet/, MK.purple],
  [/^hljs-title.*function|^hljs-function/, MK.green],
  [/^hljs-title.*class|^hljs-type|^hljs-built_in|^hljs-class/, MK.blue],
  [/^hljs-title/, MK.green],
  [/^hljs-keyword|^hljs-selector-tag|^hljs-doctag|^hljs-operator|^hljs-name/, MK.pink],
  [/^hljs-meta|^hljs-preprocessor/, MK.pink],
  [/^hljs-params|^hljs-attr|^hljs-attribute|^hljs-variable/, MK.orange],
  [/^hljs-subst/, MK.text],
];
const colorFrom = classes => {
  for (const cl of classes) for (const [re, color] of MAP) if (re.test(cl)) return color;
  return null;
};
function tokens(html) {
  const out = [];
  const stack = [];
  const re = /<span class="([^"]+)">|<\/span>|([^<]+)/g;
  let m;
  while ((m = re.exec(html))) {
    if (m[1]) stack.push(m[1].split(' '));
    else if (m[0] === '</span>') stack.pop();
    else {
      const t = m[2]
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#x27;/g, "'");
      let color = MK.text;
      for (let i = stack.length - 1; i >= 0; i--) {
        const c = colorFrom(stack[i]);
        if (c) {
          color = c;
          break;
        }
      }
      out.push([t, color]);
    }
  }
  return out;
}
// COBOL não existe no highlight.js: tokenização própria.
const COBOL_KW = new Set(
  'IDENTIFICATION DIVISION PROGRAM-ID DATA WORKING-STORAGE SECTION PROCEDURE ADD TO GIVING DISPLAY STOP RUN PIC VALUE MOVE PERFORM IF ELSE END-IF'.split(
    ' ',
  ),
);
function cobol(line) {
  const out = [];
  for (const p of line.split(/(\s+|\.)/)) {
    if (!p) continue;
    let color = MK.text;
    if (COBOL_KW.has(p)) color = MK.pink;
    else if (/^\d+$/.test(p)) color = MK.purple;
    else if (/^[A-Z]$/.test(p) && line.trim().startsWith('01')) color = MK.orange;
    out.push([p, color]);
  }
  return out;
}
const font = JSON.parse(fs.readFileSync('codes_source.json', 'utf8'));
const output = {};
for (const [id, c] of Object.entries(font)) {
  let lines;
  if (c.hl === 'cobol') lines = c.code.split('\n').map(cobol);
  else {
    const html = hljs.highlight(c.code, {language: c.hl, ignoreIllegals: true}).value;
    // quebra por linha preservando cores
    const toks = tokens(html);
    lines = [[]];
    for (const [t, color] of toks) {
      const parts = t.split('\n');
      parts.forEach((p, i) => {
        if (i > 0) lines.push([]);
        if (p) lines[lines.length - 1].push([p, color]);
      });
    }
  }
  output[id] = {file: c.file, language: c.language, color: c.color, lines};
}
// separa corridas de espaços em tokens próprios (o layout do Motion Canvas apara espaços nas pontas do texto)
for (const c of Object.values(output)) {
  c.lines = c.lines.map(l => l.flatMap(([t, color]) => (t.match(/\s+|\S+/g) ?? []).map(p => [p, color])));
}
fs.writeFileSync('src/scenes/codes.json', JSON.stringify(output));
console.log('codigos:', Object.keys(output).length);
