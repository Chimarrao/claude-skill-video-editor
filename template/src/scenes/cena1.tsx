import {Img, Node, Rect, Txt, Video, View2D, makeScene2D} from '@motion-canvas/2d';
import {
  PlaybackState,
  ThreadGenerator,
  all,
  delay,
  easeOutCubic,
  useScene,
  waitFor,
  waitUntil,
} from '@motion-canvas/core';
import {
  Lado,
  Peca,
  aparecer,
  desenharSeta,
  destacar,
  comparativo,
  fatosLista,
  telaCard,
  figura,
  grafoPeca,
  hudItem,
  impacto,
  impactoReportagem,
  janelaCodigo,
  linhaTempo,
  listaCurta,
  logoCard,
  logoSolto,
  menuExplorer,
  menuTerminal,
  pessoasCard,
  secaoCard,
  setaEntre,
  statCard,
  sumir,
  tituloItem,
} from '../lib';
import cenas from './cenas.json';
import codigos from './codigos.json';
import MENU from './menu.json';
import LISTA from './lista.json';
import PREVIA from './previa.json';

// Tudo vem de JSON gerado por plano.py (cenas.json: tempos/layout/eventos) e scripts/tokenizar.mjs (codigos.json).
const URLS = import.meta.glob('../images/*', {eager: true, import: 'default'}) as Record<string, string>;
const IMG: Record<string, string> = {};
for (const [caminho, url] of Object.entries(URLS))
  IMG[
    caminho
      .split('/')
      .pop()!
      .replace(/\.[^.]+$/, '')
  ] = url;
const img = (nome: string | null | undefined) => (nome ? IMG[nome] : null);

interface Item {
  img: string | null;
  x: number;
  y: number;
  h: number;
  placa?: boolean;
  redondo?: boolean;
  moldura?: boolean;
  rotulo?: string;
  pw?: number | null;
  ph?: number | null;
  iw?: number | null;
  ih?: number | null;
  beat: string;
  destaque?: boolean;
  alvo?: number;
}
interface Aresta {
  de: number;
  para: number;
  quando: number;
  lados: [Lado, Lado];
  estilo: 'reta' | 'cotovelo';
  bus?: number | null;
}
interface PecaJson {
  slot: 'logo' | 'pessoas' | 'dir' | 'centro' | 'overlay' | 'esq';
  tipo:
    | 'logo'
    | 'logosolto'
    | 'pessoas'
    | 'codigo'
    | 'stat'
    | 'fatos'
    | 'secao'
    | 'tempo'
    | 'grafo'
    | 'titulo'
    | 'comparativo'
    | 'tela';
  props: any;
  beat: string;
}
interface Cena {
  id: string;
  tipo: 'grafo' | 'impacto' | 'item' | 'secao' | 'tempo' | 'listacurta' | 'broll';
  itens?: Item[];
  arestas?: Aresta[];
  linhas?: string[];
  tam?: number;
  tag?: string;
  estilo?: 'monokai' | 'reportagem';
  idx?: number;
  total?: number;
  nome?: string;
  cor?: string;
  pecas?: PecaJson[];
  menu?: {de: number; para: number} | null;
  leve?: boolean;
  nva?: number;
  sub?: string;
  hud?: boolean;
  logo?: string | null;
  logo_placa?: boolean;
  logo_asp?: number;
  titulo?: string;
  rotulo?: string | null;
  data?: string | null;
  dur?: number;
}

const VIDS = import.meta.glob('../videos/*.mp4', {eager: true, import: 'default'}) as Record<string, string>;
const vid = (n: string) => VIDS[`../videos/${n}.mp4`];

/**
 * PRÉVIA do B-roll no editor (porta 9000): preenchimento embaixo + clipes (proxies 640p) nos mesmos tempos do CapCut, por baixo do overlay.
 * Ligada por `PREVIA_BROLL` (plano_dados.py -> previa.json) e AUTOMATICAMENTE desligada ao renderizar: o .mov final fica só com o overlay.
 */
function* previa(view: View2D): ThreadGenerator {
  if (!(PREVIA as any).ativa || useScene().playback.state === PlaybackState.Rendering) return;
  const fundo = new Video({src: vid('preenchimento'), size: [1920, 1080], loop: true});
  view.add(fundo);
  fundo.moveToBottom();
  fundo.play();
  let t = 0;
  for (const c of (PREVIA as any).clipes as {video: string; t0: number; dur: number; vel: number}[]) {
    if (c.t0 > t) yield* waitFor(c.t0 - t);
    const v = new Video({src: vid(c.video), size: [1920, 1080], playbackRate: c.vel});
    view.add(v);
    v.moveToBottom();
    fundo.moveToBottom();
    v.play();
    yield* waitFor(c.dur);
    v.remove();
    t = c.t0 + c.dur;
  }
}

const ev = (id: string, beat: string) => waitUntil(`${id}-${beat}`);

function* grafo(view: View2D, c: Cena): ThreadGenerator {
  const itens = c.itens!;
  const nos = itens.map(it =>
    it.img
      ? figura(IMG[it.img], {
          x: it.x,
          y: it.y,
          altura: it.h,
          placa: it.placa,
          redondo: it.redondo,
          moldura: it.moldura,
          rotulo: it.rotulo,
          pw: it.pw,
          ph: it.ph,
          iw: it.iw,
          ih: it.ih,
        })
      : null,
  );
  nos.forEach(n => n && view.add(n));
  const setas = (c.arestas ?? []).map(a =>
    setaEntre(nos[a.de]!, nos[a.para]!, a.lados[0], a.lados[1], a.estilo, a.bus),
  );
  let ultimo = '';
  for (const [i, it] of itens.entries()) {
    if (it.beat !== ultimo) {
      yield* ev(c.id, it.beat);
      ultimo = it.beat;
    }
    if (it.img) {
      const entrando = (c.arestas ?? []).map((a, k) => (a.quando === i ? k : -1)).filter(k => k >= 0);
      yield all(
        ...entrando.map(k => desenharSeta(setas[k], 0.35)),
        delay(entrando.length ? 0.2 : 0, aparecer(nos[i]!)),
      );
    }
    if (it.destaque) yield destacar(nos[it.alvo ?? i]!, 3);
  }
  yield* ev(c.id, 'out');
  const todos = [...nos.filter(n => n), ...setas.map(s => s())] as Node[];
  yield* all(...todos.map(n => sumir(n)));
  todos.forEach(n => n.remove());
}

function* texto(view: View2D, c: Cena) {
  const t =
    c.estilo === 'reportagem' ? impactoReportagem(view, c.linhas!, c.tam) : impacto(view, c.linhas!, c.tam, c.tag);
  yield* ev(c.id, 'in');
  yield* t.entrar();
  yield* ev(c.id, 'out');
  yield* t.sair();
  t.no.remove();
}

/** Layout LEVE (itens com B-roll por baixo): peças menores nos cantos para não esconder o vídeo. [x, y, escala] */
const POS_LEVE = {
  esq: [-720, 0, 0.6],
  logo: [-770, -400, 0.5],
  pessoas: [-770, 320, 0.55],
  dir: [540, 290, 0.62],
  centro: [0, 0, 1],
} as Record<string, number[]>;
const POS = {esq: [-470, 10], logo: [-640, -235], pessoas: [-640, 250], dir: [300, 28], centro: [0, 0]} as Record<
  string,
  number[]
>;

function construir(p: PecaJson): {peca: Peca; revelar?: () => any} {
  const a = p.props;
  switch (p.tipo) {
    case 'logosolto':
      return {peca: logoSolto(img(a.logo)!, a.h ?? 250, !!a.placa, a.asp ?? 1)};
    case 'logo':
      return {peca: logoCard(img(a.logo) ?? null, a.nome, a.ano, a.cor, a.sigla, 190, a.asp ?? 1)};
    case 'pessoas':
      return {
        peca: pessoasCard(
          a.pessoas.map((x: any) => ({foto: img(x.foto) ?? null, nome: x.nome, papel: x.papel})),
          IMG['ic-user'],
          !!a.grupo,
        ),
      };
    case 'stat':
      return {peca: statCard(a.valor, a.rotulo, a.cor, a.pct)};
    case 'fatos':
      return {peca: fatosLista(a.linhas.map((l: any) => ({icone: IMG[l.icone], texto: l.texto})))};
    case 'comparativo':
      return {
        peca: comparativo(
          a.colunas.map((c: any) => ({...c, logo: img(c.logo)})),
          a.linhas,
        ),
      };
    case 'tela':
      return {peca: telaCard(IMG[a.img], a.legenda, a.largura)};
    case 'grafo':
      return {peca: grafoPeca(a.itens, a.arestas, (n: string) => IMG[n], a.eventos ?? [])};
    case 'secao':
      return {
        peca: secaoCard(
          a.tag,
          a.titulo,
          a.sub,
          (a.logos ?? []).map((l: string) => IMG[l]),
        ),
      };
    case 'codigo': {
      const cod = (codigos as any)[a.id];
      const j = janelaCodigo(
        cod.arquivo,
        cod.linguagem,
        cod.cor,
        cod.linhas,
        a.largura ?? 1040,
        [IMG['ic-files-cinza'], IMG['ic-search-cinza'], IMG['ic-git-branch-cinza']].filter(Boolean),
      );
      return {
        peca: {
          no: j.no,
          *entrar() {
            yield* j.revelar();
          },
          *sair() {
            yield* all(j.no.opacity(0, 0.3));
          },
        },
      };
    }
    default:
      throw new Error('peca desconhecida ' + p.tipo);
  }
}

/** Cena de item da lista / seção: menu (troca de item) + peças em slots (logo, criadores, direita). */
function* composta(view: View2D, c: Cena): ThreadGenerator {
  const wraps: Node[] = [];
  const overlays = c.pecas!.filter(p => p.slot === 'overlay');
  const pecas = c.pecas!.filter(p => p.slot !== 'overlay').map(p => ({p, ...construir(p)}));
  const titulos = overlays.map(p => {
    const t = impacto(view, p.props.linhas, p.props.tam, p.props.tag);
    t.no.position([0, -10]);
    return {p, t};
  });
  for (const q of pecas) {
    const [x, y, esc0] = c.leve
      ? POS_LEVE[q.p.slot]
      : [...POS[q.p.slot], q.p.slot === 'centro' && ['fatos', 'stat', 'comparativo'].includes(q.p.tipo) ? 1.4 : 1];
    // grafo: ampliado (esc) e centrado — o usuário dava zoom 1,4–1,7× à mão em todo grafo
    const [gx, gy, esc] =
      q.p.tipo === 'grafo' && !c.leve
        ? [(q.p.props.dx as number) ?? 0, (q.p.props.dy as number) ?? 0, (q.p.props.esc as number) ?? 1.5]
        : [x, y, esc0];
    const wrap = new Node({position: [gx, gy], scale: esc});
    q.peca.no.position([0, 0]);
    wrap.add(q.peca.no);
    view.add(wrap);
    wraps.push(wrap);
  }
  const hud = c.idx && c.hud ? hudItem(c.idx, c.total!, c.nome!, c.cor!) : null;
  if (hud) {
    hud.no.position([690, 498]);
    view.add(hud.no);
  }
  let menu: {no: any; entrar: (de: number, para: number) => any; sair: () => any} | null = null;
  let titulo: Peca | null = null;
  if (c.menu) {
    menu =
      (LISTA as any).estilo === 'terminal'
        ? menuTerminal(MENU as any, 840, (LISTA as any).titulo)
        : menuExplorer(MENU as any, 700, (LISTA as any).titulo);
    menu.no.position([(LISTA as any).estilo === 'terminal' ? -450 : -520, 0]);
    view.add(menu.no);
    titulo = tituloItem(c.idx!, c.nome!, c.sub ?? '', c.cor!, c.total!, img(c.logo), !!c.logo_placa, c.logo_asp ?? 1);
    titulo.no.position([(LISTA as any).estilo === 'terminal' ? 440 : 400, 0]);
    view.add(titulo.no);
  }
  yield* waitUntil(`${c.id}-in`);
  if (menu) {
    const m = menu;
    const tt = titulo!;
    yield (function* () {
      yield delay(0.5, tt.entrar());
      yield* m.entrar(c.menu!.de, c.menu!.para);
      yield* waitFor(1.9);
      yield* all(m.sair(), tt.sair());
      m.no.remove();
      tt.no.remove();
    })();
  }
  // Itens sem peças (tipo Lista com B-roll: overlay mínimo): só menu/cartela + HUD (entra quando a cartela sai)
  const shown: Node[] = [];
  if (hud) {
    yield delay(c.menu ? 3.7 : 0.2, hud.entrar());
    shown.push(hud.no);
  }
  const atual: Record<string, Peca | null> = {};
  const vis: Peca[] = [];
  const visW: Node[] = [];
  // B-roll: a cada início de clipe (evento <id>-vaK) as peças somem; só o HUD fica por cima do vídeo
  for (let k = 0; k < (c.nva ?? 0); k++) {
    const nome = `${c.id}-va${k}`;
    yield (function* () {
      yield* waitUntil(nome);
      const lista = vis.splice(0, vis.length);
      const ws = visW.splice(0, visW.length);
      // some tudo de imediato (inclusive linhas que ainda estavam entrando): nada de peça solta sobre o clipe
      yield* all(...ws.map(w => w.opacity(0, 0.12)), ...lista.map(p => p.sair()));
      ws.forEach(w => w.opacity(0));
    })();
  }
  let ultimo = 'in';
  const ordem = [
    ...pecas.map(q => ({p: q.p, q, t: null as any})),
    ...titulos.map(t => ({p: t.p, q: null as any, t: t.t})),
  ].sort(
    (x, y) =>
      Number(x.p.beat.replace('b', '').replace('in', '0')) - Number(y.p.beat.replace('b', '').replace('in', '0')),
  );
  for (const o of ordem) {
    if (o.p.beat !== ultimo) {
      yield* ev(c.id, o.p.beat);
      ultimo = o.p.beat;
    }
    if (o.t) {
      const t = o.t;
      const dur = o.p.props.dur as number;
      const vis = shown.slice();
      // "palco central": o resto escurece enquanto o título fala, depois volta
      yield (function* () {
        yield* all(...vis.map(n => n.opacity(0, 0.25)));
        yield* t.entrar();
        yield* waitFor(dur);
        yield* t.sair();
        t.no.remove();
        yield* all(...vis.map(n => n.opacity(1, 0.35)));
      })();
      continue;
    }
    const q = o.q;
    shown.push(q.peca.no);
    const ant = atual[q.p.slot];
    if (ant && (q.p.slot === 'dir' || q.p.slot === 'esq' || (q.p.slot === 'centro' && q.p.tipo !== 'secao'))) {
      yield* ant.sair();
      const k = shown.indexOf(ant.no);
      if (k >= 0) shown.splice(k, 1);
    }
    atual[q.p.slot] = q.peca;
    vis.push(q.peca);
    visW.push(q.peca.no.parent() as Node);
    yield q.peca.entrar();
  }
  yield* ev(c.id, 'out');
  const todos = pecas.map(q => q.peca);
  if (hud) todos.push(hud);
  yield* all(...todos.map(p => p.sair()));
  todos.forEach(p => p.no.remove());
  wraps.forEach(w => w.remove());
}

function* tempo(view: View2D, c: Cena) {
  const p = c.pecas![0];
  const lt = linhaTempo(
    p.props.itens.map((x: any) => ({ano: x.ano, nome: x.nome, logo: img(x.logo), cor: x.cor, sigla: x.sigla})),
  );
  view.add(lt.no);
  const marcos: {beat: string; i: number}[] = p.props.marcos;
  let ultimo = '';
  for (const m of marcos) {
    if (m.beat !== ultimo) {
      yield* ev(c.id, m.beat);
      ultimo = m.beat;
    }
    yield lt.mostrar(m.i);
  }
  yield* ev(c.id, 'out');
  yield* lt.sair();
  lt.no.remove();
}

/** Webdoc com B-roll: lista curta no meio do vídeo (cartões numerados entrando na fala). */
function* listaCurtaCena(view: View2D, c: Cena): ThreadGenerator {
  const itens = (c as any).itens as {icone: string; rotulo: string; num: number}[];
  const lc = listaCurta(
    c.titulo ?? '',
    itens.map(i => ({...i, icone: IMG[i.icone] ?? null})),
    ((c as any).cor as string) ?? '#66d9ef',
  );
  lc.no.position([0, 0]);
  view.add(lc.no);
  const npausas = (((c as any).pausas as number[][]) ?? []).length;
  for (let j = 0; j < npausas; j++) {
    yield (function* () {
      yield* waitUntil(`${c.id}-p${j}a`);
      yield* lc.esconder();
      yield* waitUntil(`${c.id}-p${j}b`);
      yield* lc.reaparecer();
    })();
  }
  yield* waitUntil(`${c.id}-in`);
  for (let k = 0; k < itens.length; k++) {
    yield* waitUntil(`${c.id}-i${k}`);
    yield* lc.mostrar(k);
  }
  yield* ev(c.id, 'out');
  yield* lc.sair();
  lc.no.remove();
}

/** Webdoc com B-roll: janela de vídeo; overlay LEVE = rótulo/data/logo no canto inferior ESQUERDO (o direito é do avatar). */
function* brollCena(view: View2D, c: Cena): ThreadGenerator {
  yield* waitUntil(`${c.id}-in`);
  if (c.dur && (c.rotulo || c.data || c.logo)) {
    const alt = Math.min(86, 150 / Math.max(c.logo_asp ?? 1, 0.2));
    const faixa = (
      <Rect
        layout
        gap={22}
        alignItems="center"
        padding={[14, 26]}
        radius={20}
        fill="rgba(39,40,34,0.92)"
        stroke="rgba(255,255,255,0.16)"
        lineWidth={2}
        position={[-930, 500]}
        offset={[-1, 1]}
        opacity={0}
      >
        {c.logo ? (
          c.logo_placa ? (
            <Rect padding={[8, 14]} radius={14} fill="#ffffff" alignItems="center">
              <Img src={IMG[c.logo]} height={alt} />
            </Rect>
          ) : (
            <Img src={IMG[c.logo]} height={alt} />
          )
        ) : null}
        <Rect layout direction="column" gap={6} alignItems="start">
          {c.rotulo ? (
            <Txt
              text={c.rotulo}
              fontFamily="Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
              fontWeight={700}
              fontSize={40}
              fill="#ffffff"
            />
          ) : null}
          {c.data ? (
            <Rect layout gap={10} alignItems="center">
              <Img src={IMG['ic-calendar']} size={26} />
              <Txt
                text={c.data}
                fontFamily="'JetBrains Mono', 'SF Mono', Menlo, monospace"
                fontWeight={600}
                fontSize={28}
                fill="#a6e22e"
              />
            </Rect>
          ) : null}
        </Rect>
      </Rect>
    ) as Rect;
    view.add(faixa);
    yield* waitFor(0.6);
    yield* all(faixa.opacity(1, 0.35), faixa.x(-910, 0.45, easeOutCubic));
    yield* waitFor(Math.max(c.dur - 0.9, 0.2));
    yield* faixa.opacity(0, 0.3);
    faixa.remove();
  }
  yield* ev(c.id, 'out');
}

export default makeScene2D(function* (view) {
  yield previa(view);
  for (const c of cenas as unknown as Cena[]) {
    if (c.tipo === 'impacto') yield* texto(view, c);
    else if (c.tipo === 'item' || c.tipo === 'secao') yield* composta(view, c);
    else if (c.tipo === 'tempo') yield* tempo(view, c);
    else if (c.tipo === 'listacurta') yield* listaCurtaCena(view, c);
    else if (c.tipo === 'broll') yield* brollCena(view, c);
    else yield* grafo(view, c);
  }
  yield* waitUntil('fim'); // fecha exatamente na duração do áudio
});
