import {Circle, Img, Line, Node, Rect, Txt, makeScene2D, View2D} from '@motion-canvas/2d';
import {
  ThreadGenerator,
  all,
  createSignal,
  delay,
  easeInOutCubic,
  easeOutBack,
  easeOutCubic,
  linear,
  sequence,
  waitFor,
} from '@motion-canvas/core';
import {BRANCO, FONTE, MK, MONO, SOMBRA, menuExplorer, tituloItem} from '../lib';

// ===== Projeto de TESTE: variações de estilo para vídeos de LISTA (SOs, Linux, Windows, Tech). Cada variação ~10 s, dados de exemplo. =====
const URLS = import.meta.glob('../images/*', {eager: true, import: 'default'}) as Record<string, string>;
const IMG: Record<string, string> = {};
for (const [caminho, url] of Object.entries(URLS))
  IMG[
    caminho
      .split('/')
      .pop()!
      .replace(/\.[^.]+$/, '')
  ] = url;

interface It {
  n: string;
  s: string;
  c: string;
  img?: string;
  asp?: number;
  sig?: string;
  v?: number;
}
const SO: It[] = [
  {n: 'KolibriOS', s: '2004 · cabe num disquete', c: '#a6e22e', sig: 'K', v: 30},
  {n: 'Haiku', s: '2004 · herdeiro do BeOS', c: '#66d9ef', img: 'logo_haiku_icon', asp: 1, v: 55},
  {n: 'FreeBSD', s: '1993 · titã invisível', c: '#f92672', sig: 'BSD', v: 80},
  {n: 'ReactOS', s: '1996 · clone do NT', c: '#fd971f', img: 'logo_reactos_t', asp: 1, v: 45},
  {n: 'AROS', s: '1995 · alma do Amiga', c: '#ae81ff', img: 'logo_aros', asp: 1.67, v: 25},
];
const WIN: It[] = [
  {n: 'Windows XP', s: '2001', c: '#66d9ef', img: 'logo_winxp', asp: 1.67, v: 70},
  {n: 'Windows Vista', s: '2007', c: '#f92672', img: 'logo_vista', asp: 1.25, v: 20},
  {n: 'Windows 7', s: '2009', c: '#a6e22e', img: 'logo_win7', asp: 1.59, v: 90},
  {n: 'Windows 10', s: '2015', c: '#fd971f', sig: '10', v: 75},
  {n: 'Windows 11', s: '2021', c: '#66d9ef', img: 'logo_win11_icone', asp: 1, v: 60},
];
const LNX: It[] = [
  {n: 'Ubuntu', s: 'Canonical · 2004', c: '#fd971f', sig: 'U', v: 85},
  {n: 'Debian', s: 'Comunidade · 1993', c: '#f92672', sig: 'D', v: 65},
  {n: 'Arch', s: 'Rolling · 2002', c: '#66d9ef', sig: 'A', v: 50},
  {n: 'Fedora', s: 'Red Hat · 2003', c: '#ae81ff', sig: 'F', v: 55},
  {n: 'Linux Mint', s: 'Clem · 2006', c: '#a6e22e', img: 'logo_linuxmint', asp: 1, v: 70},
];
const TECH: It[] = [
  {n: 'Intel', s: 'CPUs', c: '#66d9ef', img: 'logo_intel', asp: 1, v: 60},
  {n: 'AMD', s: 'CPUs e GPUs', c: '#f92672', img: 'logo_amd', asp: 1, v: 75},
  {n: 'NVIDIA', s: 'GPUs', c: '#a6e22e', img: 'logo_nvidia', asp: 1, v: 95},
  {n: 'GitHub', s: 'Código', c: '#ae81ff', img: 'logo_github', asp: 1, v: 50},
  {n: 'Firefox', s: 'Navegador', c: '#fd971f', img: 'logo_firefox', asp: 1, v: 35},
];

const FUNDO = '#0c1110';
const PAINEL = 'rgba(39,40,34,0.95)';
const ARO = 'rgba(255,255,255,0.16)';
const pos = (x: number, y: number) => [x, y] as [number, number];

/** Ícone do item: logo (altura `h`, largura limitada a `maxW`) ou emblema com sigla. */
function ico(it: It, h: number, maxW = 9999): Node {
  if (it.img) {
    // logo SEMPRE em cartão branco (logos escuros somem no fundo escuro)
    const w0 = h * (it.asp ?? 1);
    const k = Math.min(1, (maxW - 0.2 * h) / (w0 + 0.2 * h), 1);
    const iw = w0 * k * 0.8,
      ih = h * k * 0.8;
    return (
      <Rect width={iw + h * 0.2} height={ih + h * 0.2} radius={h * 0.2} fill="#ffffff">
        <Img src={IMG[it.img]} width={iw} height={ih} />
      </Rect>
    ) as Node;
  }
  return (
    <Circle size={h} fill={it.c}>
      <Txt
        text={it.sig ?? it.n[0]}
        fontFamily={MONO}
        fontWeight={800}
        fontSize={h * (it.sig && it.sig.length > 1 ? 0.34 : 0.46)}
        fill="#0b0b10"
      />
    </Circle>
  ) as Node;
}

function chip(root: Node, id: string, nome: string, uso: string) {
  root.add(
    <Rect
      layout
      gap={16}
      padding={[10, 20]}
      radius={14}
      fill="rgba(0,0,0,0.55)"
      stroke={ARO}
      lineWidth={2}
      position={[-930, 520]}
      offset={[-1, 1]}
    >
      <Txt text={id} fontFamily={MONO} fontWeight={800} fontSize={30} fill={MK.verde} />
      <Txt text={nome} fontFamily={FONTE} fontWeight={700} fontSize={30} fill="#ffffff" />
      <Txt text={'· ' + uso} fontFamily={FONTE} fontWeight={500} fontSize={26} fill={MK.cinza} />
    </Rect>,
  );
}

// ---------- V01: Explorador (estilo atual — referência) ----------
function* v01(root: Node): ThreadGenerator {
  const m = menuExplorer(
    SO.map(i => ({rotulo: i.n, arquivo: i.n.toLowerCase() + '.img', cor: i.c})),
    700,
    'SISTEMAS',
  );
  m.no.position([-520, 0]);
  root.add(m.no);
  const t = tituloItem(2, 'FreeBSD', '1993 · titã invisível', '#f92672', 5, null, false, 1);
  t.no.position([400, 0]);
  root.add(t.no);
  yield* all(m.entrar(0, 2), delay(0.5, t.entrar()));
  yield* waitFor(3.2);
  yield* all(m.sair(), t.sair());
}

// ---------- V02: Pódio ----------
function* v02(root: Node): ThreadGenerator {
  const ordem = [SO[1], SO[2], SO[3]]; // 2º, 1º, 3º
  const xs = [-440, 0, 440],
    hs = [300, 440, 220],
    pos_ = ['2', '1', '3'],
    cores = ['#c0c0c0', '#ffd166', '#cd7f32'];
  const base = 300;
  const barras: Rect[] = [],
    icos: Node[] = [],
    nomes: Txt[] = [];
  root.add(<Txt text="TOP 3" fontFamily={MONO} fontWeight={800} fontSize={64} fill={MK.verde} position={[0, -430]} />);
  ordem.forEach((it, i) => {
    const b = (
      <Rect
        width={340}
        height={0}
        offset={[0, 1]}
        position={[xs[i], base]}
        radius={[22, 22, 0, 0]}
        fill={cores[i]}
        {...SOMBRA}
      >
        <Txt
          text={pos_[i]}
          fontFamily={MONO}
          fontWeight={800}
          fontSize={150}
          fill="rgba(0,0,0,0.35)"
          y={-hs[i] / 2 + 100}
        />
      </Rect>
    ) as Rect;
    root.add(b);
    barras.push(b);
    const ic = ico(it, 190, 260);
    ic.position(pos(xs[i], base - hs[i] - 130));
    ic.opacity(0);
    ic.scale(0.6);
    root.add(ic);
    icos.push(ic);
    const nm = (
      <Txt
        text={it.n}
        fontFamily={FONTE}
        fontWeight={800}
        fontSize={44}
        fill={BRANCO}
        position={[xs[i], base + 50]}
        opacity={0}
      />
    ) as Txt;
    root.add(nm);
    nomes.push(nm);
  });
  for (const i of [2, 0, 1]) {
    yield* all(
      barras[i].height(hs[i], 0.9, easeOutCubic),
      delay(0.5, all(icos[i].opacity(1, 0.4), icos[i].scale(1, 0.5, easeOutBack))),
      delay(0.6, nomes[i].opacity(1, 0.4)),
    );
    yield* waitFor(0.5);
  }
  yield* waitFor(2.2);
}

// ---------- V03: Carrossel de cartas ----------
function* v03(root: Node): ThreadGenerator {
  const D = 430;
  const cont = (<Node />) as Node;
  root.add(cont);
  const cards: Rect[] = LNX.map((it, i) => {
    const c = (
      <Rect
        width={360}
        height={500}
        radius={30}
        fill={PAINEL}
        stroke={it.c}
        lineWidth={5}
        position={[i * D, 0]}
        {...SOMBRA}
      >
        <Rect width={360} height={14} y={-243} fill={it.c} radius={7} />
        <Txt
          text={`#${i + 1}`}
          fontFamily={MONO}
          fontWeight={800}
          fontSize={44}
          fill={MK.comentario}
          position={[-120, -190]}
        />
      </Rect>
    ) as Rect;
    const g = ico(it, 190, 250);
    g.position([0, -40]);
    c.add(g);
    c.add(<Txt text={it.n} fontFamily={FONTE} fontWeight={800} fontSize={50} fill={BRANCO} y={110} />);
    c.add(<Txt text={it.s} fontFamily={MONO} fontWeight={500} fontSize={28} fill={it.c} y={170} />);
    c.scale(0.8);
    c.opacity(0);
    cont.add(c);
    return c;
  });
  yield* all(...cards.map((c, i) => delay(i * 0.1, all(c.opacity(0.55, 0.4), c.scale(0.8, 0.4)))));
  for (let k = 0; k < LNX.length; k++) {
    yield* all(
      cont.x(-k * D, 0.7, easeInOutCubic),
      ...cards.map((c, i) => all(c.scale(i === k ? 1.12 : 0.8, 0.6), c.opacity(i === k ? 1 : 0.5, 0.6))),
    );
    yield* waitFor(1.1);
  }
}

// ---------- V04: Linha de metrô (roadmap) ----------
function* v04(root: Node): ThreadGenerator {
  const xs = WIN.map((_, i) => -720 + i * 360);
  const linha = (
    <Line
      points={[
        [-860, 0],
        [860, 0],
      ]}
      stroke="#ffffff"
      lineWidth={10}
      lineCap="round"
      end={0}
    />
  ) as Line;
  root.add(linha);
  const estacoes = WIN.map((it, i) => {
    const up = i % 2 === 0;
    const g = (<Node position={[xs[i], 0]} opacity={0} />) as Node;
    g.add(<Circle size={46} fill={FUNDO} stroke={it.c} lineWidth={10} />);
    g.add(
      <Line
        points={[
          [0, up ? -30 : 30],
          [0, up ? -110 : 110],
        ]}
        stroke={it.c}
        lineWidth={5}
      />,
    );
    const ic = ico(it, 130, 220);
    ic.position([0, up ? -190 : 190]);
    g.add(ic);
    g.add(
      <Txt
        text={it.n}
        fontFamily={FONTE}
        fontWeight={800}
        fontSize={40}
        fill={BRANCO}
        position={[0, up ? -300 : 300]}
      />,
    );
    g.add(
      <Txt text={it.s} fontFamily={MONO} fontWeight={700} fontSize={32} fill={it.c} position={[0, up ? -345 : 345]} />,
    );
    root.add(g);
    return g;
  });
  const trem = (
    <Rect width={90} height={34} radius={17} fill={MK.verde} position={[xs[0] - 110, 0]} {...SOMBRA} />
  ) as Rect;
  root.add(trem);
  yield* linha.end(1, 0.8, easeOutCubic);
  for (let i = 0; i < WIN.length; i++) {
    yield* trem.x(xs[i], 1.0, easeInOutCubic);
    yield* estacoes[i].opacity(1, 0.25);
    yield estacoes[i].scale(1.1, 0.25).to(1, 0.25);
    yield* waitFor(0.25);
  }
  yield* waitFor(1.2);
}

// ---------- V05: Corrida de barras (ranking) ----------
function* v05(root: Node): ThreadGenerator {
  const v1 = TECH.map(t => t.v!),
    v2 = [90, 40, 95, 70, 20];
  const N = TECH.length,
    H = 120,
    W = 1000;
  const linhas = TECH.map((it, i) => {
    const g = (<Node position={[-480, -260 + i * H]} opacity={0} />) as Node;
    const ic = ico(it, 84, 84);
    ic.position([-90, 0]);
    g.add(ic);
    g.add(
      <Txt
        text={it.n}
        fontFamily={FONTE}
        fontWeight={700}
        fontSize={40}
        fill={BRANCO}
        position={[-170, 0]}
        offset={[1, 0]}
      />,
    );
    g.add(<Rect width={W} height={64} radius={14} fill="rgba(255,255,255,0.06)" position={[W / 2, 0]} />);
    const barra = (<Rect width={0} height={64} radius={14} fill={it.c} position={[0, 0]} offset={[-1, 0]} />) as Rect;
    g.add(barra);
    root.add(g);
    return {g, barra};
  });
  root.add(<Txt text="valores de exemplo" fontFamily={MONO} fontSize={26} fill={MK.comentario} position={[0, 400]} />);
  yield* all(
    ...linhas.map((l, i) => delay(i * 0.12, all(l.g.opacity(1, 0.3), l.barra.width(v1[i] * 9.5, 1.0, easeOutCubic)))),
  );
  yield* waitFor(0.8);
  const rank = (v: number[]) =>
    v
      .map((x, i) => [x, i])
      .sort((a, b) => b[0] - a[0])
      .map(p => p[1]);
  const r2 = rank(v2);
  yield* all(
    ...linhas.map((l, i) =>
      all(l.barra.width(v2[i] * 9.5, 1.2, easeInOutCubic), l.g.y(-260 + r2.indexOf(i) * H, 1.2, easeInOutCubic)),
    ),
  );
  yield* waitFor(2.4);
}

// ---------- V06: Grade com holofote ----------
function* v06(root: Node): ThreadGenerator {
  const itens = [...TECH, {n: '+ mais', s: '', c: '#75715e', sig: '+'} as It];
  const tiles = itens.map((it, i) => {
    const x = -420 + (i % 3) * 420,
      y = -170 + Math.floor(i / 3) * 290;
    const t = (
      <Rect
        width={360}
        height={250}
        radius={26}
        fill={PAINEL}
        stroke={ARO}
        lineWidth={3}
        position={[x, y]}
        opacity={0.35}
      />
    ) as Rect;
    const g = ico(it, 130, 220);
    g.position([0, -10]);
    t.add(g);
    root.add(t);
    return t;
  });
  const legenda = (
    <Rect
      layout
      direction="column"
      alignItems="center"
      gap={4}
      padding={[14, 34]}
      radius={20}
      fill={PAINEL}
      stroke={ARO}
      lineWidth={2}
      position={[0, 400]}
      opacity={0}
    >
      <Txt text="" fontFamily={FONTE} fontWeight={800} fontSize={48} fill={BRANCO} />
      <Txt text="" fontFamily={MONO} fontWeight={600} fontSize={30} fill={MK.verde} />
    </Rect>
  ) as Rect;
  root.add(legenda);
  yield* all(...tiles.map((t, i) => delay(i * 0.08, t.opacity(0.35, 0.3))));
  yield* legenda.opacity(1, 0.3);
  const [nome, sub] = legenda.children() as Txt[];
  for (let k = 0; k < 5; k++) {
    nome.text(itens[k].n);
    sub.text(itens[k].s);
    nome.fill(BRANCO);
    sub.fill(itens[k].c);
    yield* all(
      ...tiles.map((t, i) =>
        all(
          t.scale(i === k ? 1.2 : 1, 0.35, easeOutCubic),
          t.opacity(i === k ? 1 : 0.3, 0.35),
          t.stroke(i === k ? itens[k].c : ARO, 0.35),
        ),
      ),
    );
    yield* waitFor(1.3);
  }
}

// ---------- V07: Terminal (ls / seleção) ----------
function* v07(root: Node): ThreadGenerator {
  const jan = (
    <Rect width={1360} height={760} radius={22} fill="#0f1210" stroke={ARO} lineWidth={3} clip {...SOMBRA} />
  ) as Rect;
  root.add(jan);
  jan.add(<Rect width={1360} height={56} y={-352} fill="#1d201c" />);
  [MK.rosa, MK.amarelo, MK.verde].forEach((c, i) =>
    jan.add(<Circle size={20} fill={c} position={[-620 + i * 34, -352]} />),
  );
  jan.add(<Txt text="usuario@canal: ~/distros" fontFamily={MONO} fontSize={26} fill={MK.cinza} y={-352} />);
  const cmd = (
    <Txt
      text=""
      fontFamily={MONO}
      fontWeight={600}
      fontSize={38}
      fill={MK.verde}
      position={[-620, -270]}
      offset={[-1, 0]}
    />
  ) as Txt;
  jan.add(cmd);
  const sel = (
    <Rect
      width={1260}
      height={62}
      radius={8}
      fill="rgba(166,226,46,0.16)"
      stroke={MK.verde}
      lineWidth={2}
      position={[0, -170]}
      opacity={0}
    />
  ) as Rect;
  jan.add(sel);
  const linhas = LNX.map((it, i) => {
    const y = -170 + i * 76;
    const g = (<Node opacity={0} />) as Node;
    g.add(
      <Txt
        text="drwxr-xr-x"
        fontFamily={MONO}
        fontSize={34}
        fill={MK.comentario}
        position={[-600, y]}
        offset={[-1, 0]}
      />,
    );
    g.add(
      <Txt
        text={String(i + 1).padStart(2, '0')}
        fontFamily={MONO}
        fontSize={34}
        fill={MK.cinza}
        position={[-300, y]}
        offset={[-1, 0]}
      />,
    );
    g.add(
      <Txt
        text={it.n.toLowerCase().replace(' ', '-')}
        fontFamily={MONO}
        fontWeight={700}
        fontSize={36}
        fill={MK.texto}
        position={[-220, y]}
        offset={[-1, 0]}
      />,
    );
    g.add(<Txt text={it.s} fontFamily={MONO} fontSize={32} fill={MK.cinza} position={[110, y]} offset={[-1, 0]} />);
    jan.add(g);
    return g;
  });
  yield* cmd.text('$ ls -l ~/distros', 1.0, linear);
  yield* sequence(0.25, ...linhas.map(l => l.opacity(1, 0.2)));
  sel.opacity(1);
  for (let k = 0; k < LNX.length; k++) {
    yield* sel.y(-170 + k * 76, 0.35, easeInOutCubic);
    yield* waitFor(0.75);
  }
  yield* cmd.text('$ cat linux-mint/README', 0.9, linear);
  yield* waitFor(1.0);
}

// ---------- V08: Menu do GRUB ----------
function* v08(root: Node): ThreadGenerator {
  const quadro = (<Rect width={1280} height={720} fill="#0a0a0a" stroke="#c9c9c9" lineWidth={4} {...SOMBRA} />) as Rect;
  root.add(quadro);
  quadro.add(<Txt text="GNU GRUB  version 2.12" fontFamily={MONO} fontSize={34} fill="#c9c9c9" y={-310} />);
  quadro.add(<Rect width={1160} height={440} stroke="#c9c9c9" lineWidth={3} y={-40} />);
  const barra = (<Rect width={1140} height={54} fill="#c9c9c9" position={[0, -196]} />) as Rect;
  quadro.add(barra);
  const textos = SO.map((it, i) => {
    const t = (
      <Txt
        text={`${i === 0 ? '*' : ' '}${it.n} (on /dev/sda${i + 1})`}
        fontFamily={MONO}
        fontWeight={600}
        fontSize={36}
        fill="#c9c9c9"
        position={[-540, -196 + i * 66]}
        offset={[-1, 0]}
      />
    ) as Txt;
    quadro.add(t);
    return t;
  });
  quadro.add(
    <Txt
      text="Use ▲ and ▼ to select which entry is highlighted. Press enter to boot."
      fontFamily={MONO}
      fontSize={26}
      fill="#9a9a9a"
      y={222}
    />,
  );
  const cont = (
    <Txt
      text="The highlighted entry will be executed automatically in 5s."
      fontFamily={MONO}
      fontSize={26}
      fill="#9a9a9a"
      y={266}
    />
  ) as Txt;
  quadro.add(cont);
  textos[0].fill('#0a0a0a');
  for (let k = 1; k < SO.length; k++) {
    yield* waitFor(1.0);
    textos[k - 1].fill('#c9c9c9');
    textos[k].fill('#0a0a0a');
    yield* barra.y(-196 + k * 66, 0.12, linear);
    cont.text(`The highlighted entry will be executed automatically in ${5 - k}s.`);
  }
  yield* waitFor(1.4);
  yield* quadro.scale(1.04, 0.3).to(1, 0.3);
}

// ---------- V09: Janelas do Windows empilhadas ----------
function* v09(root: Node): ThreadGenerator {
  const jans = WIN.map((it, i) => {
    const x = -420 + i * 200,
      y = -190 + i * 90;
    const j = (
      <Rect
        width={760}
        height={420}
        radius={14}
        fill="#202124"
        stroke="rgba(255,255,255,0.22)"
        lineWidth={2}
        position={[x, y]}
        opacity={0}
        {...SOMBRA}
      >
        <Rect width={760} height={50} y={-185} fill="#2b2d31" radius={[14, 14, 0, 0]} />
        <Txt
          text={it.n}
          fontFamily="'Segoe UI', Inter, sans-serif"
          fontSize={26}
          fill="#e8e8e8"
          position={[-350, -185]}
          offset={[-1, 0]}
        />
        <Txt
          text="—      ▢      ✕"
          fontFamily="'Segoe UI', Inter, sans-serif"
          fontSize={26}
          fill="#e8e8e8"
          position={[300, -185]}
        />
      </Rect>
    ) as Rect;
    const g = ico(it, 150, 240);
    g.position([-200, 20]);
    j.add(g);
    j.add(
      <Txt
        text={it.n}
        fontFamily={FONTE}
        fontWeight={800}
        fontSize={56}
        fill={BRANCO}
        position={[40, -10]}
        offset={[-1, 0]}
      />,
    );
    j.add(
      <Txt
        text={it.s}
        fontFamily={MONO}
        fontWeight={700}
        fontSize={36}
        fill={it.c}
        position={[40, 55]}
        offset={[-1, 0]}
      />,
    );
    root.add(j);
    return j;
  });
  for (let i = 0; i < jans.length; i++) {
    jans[i].scale(0.9);
    yield* all(jans[i].opacity(1, 0.35), jans[i].scale(1, 0.45, easeOutBack));
    yield* waitFor(0.9);
  }
  yield* waitFor(1.2);
}

// ---------- V10: Cartas colecionáveis (stats) ----------
function* v10(root: Node): ThreadGenerator {
  const rot = [-9, 0, 9],
    xs = [-470, 0, 470],
    stats = ['Leveza', 'Comunidade', 'Uso diário'];
  const cartas = SO.slice(0, 3).map((it, i) => {
    const c = (
      <Rect
        width={420}
        height={640}
        radius={30}
        fill="#1c1d19"
        stroke={it.c}
        lineWidth={7}
        position={[xs[i], i === 1 ? -10 : 20]}
        rotation={rot[i]}
        scale={[0, 1]}
        {...SOMBRA}
      >
        <Rect width={420} height={70} y={-285} fill={it.c} radius={[24, 24, 0, 0]} />
        <Txt text={it.n} fontFamily={FONTE} fontWeight={800} fontSize={42} fill="#0b0b10" y={-285} />
      </Rect>
    ) as Rect;
    const g = ico(it, 190, 300);
    g.position([0, -130]);
    c.add(g);
    c.add(<Txt text={it.s} fontFamily={MONO} fontWeight={600} fontSize={24} fill={it.c} y={-10} />);
    const barras: Rect[] = [];
    stats.forEach((s, k) => {
      c.add(
        <Txt
          text={s}
          fontFamily={FONTE}
          fontWeight={600}
          fontSize={28}
          fill={BRANCO}
          position={[-170, 70 + k * 80]}
          offset={[-1, 0]}
        />,
      );
      c.add(<Rect width={340} height={20} radius={10} fill="rgba(255,255,255,0.12)" position={[0, 105 + k * 80]} />);
      const b = (
        <Rect width={0} height={20} radius={10} fill={it.c} position={[-170, 105 + k * 80]} offset={[-1, 0]} />
      ) as Rect;
      c.add(b);
      barras.push(b);
    });
    root.add(c);
    return {c, barras, vals: [it.v!, 100 - it.v! * 0.4, ((it.v! * 7) % 100) + 20]};
  });
  for (let i = 0; i < 3; i++) {
    yield* cartas[i].c.scale([1, 1], 0.5, easeOutBack);
    yield all(...cartas[i].barras.map((b, k) => b.width(3.4 * cartas[i].vals[k], 0.9, easeOutCubic)));
    yield* waitFor(0.6);
  }
  yield* waitFor(2.4);
}

// ---------- V11: Tier list ----------
function* v11(root: Node): ThreadGenerator {
  const tiers = [
    ['S', '#ff7f7f'],
    ['A', '#ffbf7f'],
    ['B', '#ffdf7f'],
    ['C', '#bfff7f'],
  ] as const;
  const destino = [0, 1, 1, 2, 3];
  tiers.forEach(([l, c], i) => {
    root.add(
      <Rect width={1300} height={160} fill="#1a1c19" stroke={ARO} lineWidth={2} position={[0, -270 + i * 175]}>
        <Rect width={150} height={160} fill={c} x={-575}>
          <Txt text={l} fontFamily={MONO} fontWeight={800} fontSize={96} fill="#0b0b10" />
        </Rect>
      </Rect>,
    );
  });
  const cont: number[] = [0, 0, 0, 0];
  const pecas: Rect[] = [];
  for (let i = 0; i < TECH.length; i++) {
    const t = destino[i];
    const x = -440 + cont[t] * 170;
    cont[t]++;
    const p = (
      <Rect
        width={140}
        height={140}
        radius={18}
        fill={PAINEL}
        stroke={TECH[i].c}
        lineWidth={4}
        position={[x, 700]}
        {...SOMBRA}
      />
    ) as Rect;
    const g = ico(TECH[i], 96, 110);
    p.add(g);
    root.add(p);
    pecas.push(p);
    yield* p.position([x, -270 + t * 175], 0.7, easeOutBack);
    yield* waitFor(0.45);
  }
  yield* waitFor(2.4);
}

// ---------- V12: Hub radial (mapa mental) ----------
function* v12(root: Node): ThreadGenerator {
  const centro = (
    <Circle size={240} fill={PAINEL} stroke={MK.verde} lineWidth={8} scale={0} {...SOMBRA}>
      <Txt text="LINUX" fontFamily={MONO} fontWeight={800} fontSize={54} fill={MK.verde} y={70} />
    </Circle>
  ) as Circle;
  const tux = ico({n: 'Tux', s: '', c: MK.verde, img: 'logo_tux', asp: 1}, 120);
  tux.position([0, -30]);
  centro.add(tux);
  root.add(centro);
  yield* centro.scale(1, 0.5, easeOutBack);
  const R = 400;
  for (let i = 0; i < LNX.length; i++) {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / LNX.length;
    const x = Math.cos(a) * R * 1.55,
      y = Math.sin(a) * R * 0.95;
    const l = (
      <Line
        points={[
          [Math.cos(a) * 130, Math.sin(a) * 130],
          [x * 0.82, y * 0.82],
        ]}
        stroke={LNX[i].c}
        lineWidth={5}
        end={0}
      />
    ) as Line;
    root.add(l);
    const n = (<Node position={[x, y]} scale={0} />) as Node;
    n.add(<Circle size={170} fill={PAINEL} stroke={LNX[i].c} lineWidth={6} />);
    const ic = ico(LNX[i], 110, 150);
    n.add(ic);
    n.add(<Txt text={LNX[i].n} fontFamily={FONTE} fontWeight={800} fontSize={36} fill={BRANCO} y={125} />);
    root.add(n);
    yield* l.end(1, 0.4, easeOutCubic);
    yield* n.scale(1, 0.4, easeOutBack);
    yield* waitFor(0.45);
  }
  yield* waitFor(2.2);
}

// ---------- V13: Dock com magnificação ----------
function* v13(root: Node): ThreadGenerator {
  const itens = [
    ...TECH,
    {n: 'Spotify', s: '', c: '#a6e22e', img: 'logo_spotify', asp: 1} as It,
    {n: 'Edge', s: '', c: '#66d9ef', img: 'logo_edge', asp: 1} as It,
    {n: 'Copilot', s: '', c: '#ae81ff', img: 'logo_copilot', asp: 1.07} as It,
  ];
  const GAP = 150,
    x0 = -((itens.length - 1) * GAP) / 2;
  root.add(
    <Txt text="Ferramentas do dia a dia" fontFamily={FONTE} fontWeight={800} fontSize={72} fill={BRANCO} y={-250} />,
  );
  const dock = (
    <Rect
      width={itens.length * GAP + 80}
      height={150}
      radius={44}
      fill="rgba(255,255,255,0.12)"
      stroke={ARO}
      lineWidth={3}
      position={[0, 220]}
      opacity={0}
    />
  ) as Rect;
  root.add(dock);
  const ptr = createSignal(x0 - 400);
  const nomeTxt = (<Txt text="" fontFamily={FONTE} fontWeight={800} fontSize={54} fill={BRANCO} y={20} />) as Txt;
  root.add(nomeTxt);
  itens.forEach((it, i) => {
    const x = x0 + i * GAP;
    const e = () => 1 + 0.95 * Math.exp(-(((x - ptr()) / 115) ** 2));
    const g = ico(it, 96, 130);
    g.position(() => pos(x, 220 + 30 - 38 * e()));
    g.scale(e);
    root.add(g);
  });
  yield* dock.opacity(1, 0.4);
  for (let k = 0; k < itens.length; k++) {
    yield* ptr(x0 + k * GAP, k === 0 ? 0.9 : 0.55, easeInOutCubic);
    nomeTxt.text(itens[k].n);
    yield* waitFor(0.6);
  }
  yield* waitFor(1.0);
}

// ---------- V14: Contagem regressiva de ranking ----------
function* v14(root: Node): ThreadGenerator {
  const anel = (<Circle size={520} stroke="rgba(255,255,255,0.12)" lineWidth={30} position={[-440, 0]} />) as Circle;
  const prog = (
    <Circle
      size={520}
      stroke={MK.verde}
      lineWidth={30}
      lineCap="round"
      startAngle={-90}
      endAngle={-90}
      position={[-440, 0]}
    />
  ) as Circle;
  const num = (
    <Txt text="5" fontFamily={MONO} fontWeight={800} fontSize={330} fill={BRANCO} position={[-440, 0]} />
  ) as Txt;
  const nome = (
    <Txt text="" fontFamily={FONTE} fontWeight={800} fontSize={120} fill={BRANCO} position={[300, 120]} />
  ) as Txt;
  const sub = (
    <Txt text="" fontFamily={MONO} fontWeight={600} fontSize={42} fill={MK.verde} position={[300, 220]} />
  ) as Txt;
  const holder = (<Node position={[300, -100]} />) as Node;
  [anel, prog, num, nome, sub, holder].forEach(n => root.add(n));
  for (let k = 0; k < SO.length; k++) {
    const it = SO[SO.length - 1 - k],
      rank = SO.length - k;
    num.text(String(rank));
    nome.text(it.n);
    sub.text(it.s);
    sub.fill(it.c);
    prog.stroke(it.c);
    holder.removeChildren();
    const g = ico(it, 190, 280);
    holder.add(g);
    num.scale(1.25);
    nome.opacity(0);
    sub.opacity(0);
    g.opacity(0);
    prog.endAngle(-90);
    yield* all(
      num.scale(1, 0.35, easeOutBack),
      nome.opacity(1, 0.3),
      sub.opacity(1, 0.3),
      g.opacity(1, 0.3),
      prog.endAngle(-90 + 360 * ((k + 1) / SO.length), 0.8, easeOutCubic),
    );
    yield* waitFor(1.05);
  }
}

const VARS: [string, string, string, (r: Node) => ThreadGenerator][] = [
  ['V01', 'Explorador (atual)', 'referência · programação/SOs', v01],
  ['V02', 'Pódio', 'ranking curto · qualquer tema', v02],
  ['V03', 'Carrossel de cartas', 'distros · Linux', v03],
  ['V04', 'Linha de metrô', 'evolução/versões · Windows', v04],
  ['V05', 'Corrida de barras', 'comparativo · Tech', v05],
  ['V06', 'Grade com holofote', 'logos/empresas · Tech', v06],
  ['V07', 'Terminal ls', 'Linux/SOs', v07],
  ['V08', 'Menu do GRUB', 'SOs · Linux', v08],
  ['V09', 'Janelas do Windows', 'Windows', v09],
  ['V10', 'Cartas com stats', 'SOs/jogos · Tech', v10],
  ['V11', 'Tier list', 'rankings · Tech', v11],
  ['V12', 'Hub radial', 'ecossistema · Linux', v12],
  ['V13', 'Dock com zoom', 'ferramentas · Tech', v13],
  ['V14', 'Contagem regressiva', 'top N · qualquer tema', v14],
];

export default makeScene2D(function* (view: View2D) {
  view.fill(FUNDO);
  for (const [id, nome, uso, fn] of VARS) {
    const root = (<Node opacity={0} />) as Node;
    view.add(root);
    chip(root, id, nome, uso);
    yield* root.opacity(1, 0.3);
    yield* fn(root);
    yield* root.opacity(0, 0.35);
    root.remove();
  }
});
