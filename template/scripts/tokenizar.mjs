// codigos_fonte.json -> src/scenes/codigos.json com tokens coloridos no tema Monokai (highlight.js).
import fs from 'node:fs';
import hljs from 'highlight.js';

const MK = {
  texto: '#f8f8f2',
  comentario: '#75715e',
  rosa: '#f92672',
  laranja: '#fd971f',
  amarelo: '#e6db74',
  verde: '#a6e22e',
  azul: '#66d9ef',
  roxo: '#ae81ff',
};
const MAPA = [
  [/^hljs-comment|^hljs-quote/, MK.comentario],
  [/^hljs-string|^hljs-template-variable|^hljs-regexp|^hljs-char/, MK.amarelo],
  [/^hljs-number|^hljs-literal|^hljs-symbol|^hljs-bullet/, MK.roxo],
  [/^hljs-title.*function|^hljs-function/, MK.verde],
  [/^hljs-title.*class|^hljs-type|^hljs-built_in|^hljs-class/, MK.azul],
  [/^hljs-title/, MK.verde],
  [/^hljs-keyword|^hljs-selector-tag|^hljs-doctag|^hljs-operator|^hljs-name/, MK.rosa],
  [/^hljs-meta|^hljs-preprocessor/, MK.rosa],
  [/^hljs-params|^hljs-attr|^hljs-attribute|^hljs-variable/, MK.laranja],
  [/^hljs-subst/, MK.texto],
];
const corDe = classes => {
  for (const cl of classes) for (const [re, cor] of MAPA) if (re.test(cl)) return cor;
  return null;
};
function tokens(html) {
  const out = [];
  const pilha = [];
  const re = /<span class="([^"]+)">|<\/span>|([^<]+)/g;
  let m;
  while ((m = re.exec(html))) {
    if (m[1]) pilha.push(m[1].split(' '));
    else if (m[0] === '</span>') pilha.pop();
    else {
      const t = m[2]
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#x27;/g, "'");
      let cor = MK.texto;
      for (let i = pilha.length - 1; i >= 0; i--) {
        const c = corDe(pilha[i]);
        if (c) {
          cor = c;
          break;
        }
      }
      out.push([t, cor]);
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
function cobol(linha) {
  const out = [];
  for (const p of linha.split(/(\s+|\.)/)) {
    if (!p) continue;
    let cor = MK.texto;
    if (COBOL_KW.has(p)) cor = MK.rosa;
    else if (/^\d+$/.test(p)) cor = MK.roxo;
    else if (/^[A-Z]$/.test(p) && linha.trim().startsWith('01')) cor = MK.laranja;
    out.push([p, cor]);
  }
  return out;
}
const fonte = JSON.parse(fs.readFileSync('codigos_fonte.json', 'utf8'));
const saida = {};
for (const [id, c] of Object.entries(fonte)) {
  let linhas;
  if (c.hl === 'cobol') linhas = c.codigo.split('\n').map(cobol);
  else {
    const html = hljs.highlight(c.codigo, {language: c.hl, ignoreIllegals: true}).value;
    // quebra por linha preservando cores
    const toks = tokens(html);
    linhas = [[]];
    for (const [t, cor] of toks) {
      const partes = t.split('\n');
      partes.forEach((p, i) => {
        if (i > 0) linhas.push([]);
        if (p) linhas[linhas.length - 1].push([p, cor]);
      });
    }
  }
  saida[id] = {arquivo: c.arquivo, linguagem: c.linguagem, cor: c.cor, linhas};
}
// separa corridas de espaços em tokens próprios (o layout do Motion Canvas apara espaços nas pontas do texto)
for (const c of Object.values(saida)) {
  c.linhas = c.linhas.map(l => l.flatMap(([t, cor]) => (t.match(/\s+|\S+/g) ?? []).map(p => [p, cor])));
}
fs.writeFileSync('src/scenes/codigos.json', JSON.stringify(saida));
console.log('codigos:', Object.keys(saida).length);
