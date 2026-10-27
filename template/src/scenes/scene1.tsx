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
  Side,
  Piece,
  appear,
  drawArrow,
  emphasize,
  comparison,
  factsList,
  screenCard,
  figure,
  graphPiece,
  hudItem,
  impact,
  impactReport,
  codeWindow,
  timeline,
  shortList,
  logoCard,
  freeLogo,
  menuExplorer,
  menuTerminal,
  peopleCard,
  sectionCard,
  arrowBetween,
  statCard,
  vanish,
  titleItem,
  roundCard,
  duel,
  verdictBadge,
  barsChart,
  profileCard,
  profileRow,
  scoreStrip,
} from '../lib';
import scenes from './scenes.json';
import codes from './codes.json';
import MENU from './menu.json';
import LISTING from './list.json';
import PREVIEW from './preview.json';

// Tudo vem de JSON gerado por plan.py (scenes.json: tempos/layout/eventos) e scripts/tokenize.mjs (codes.json).
const URLS = import.meta.glob('../images/*', {eager: true, import: 'default'}) as Record<string, string>;
const IMG: Record<string, string> = {};
for (const [path, url] of Object.entries(URLS))
  IMG[
    path
      .split('/')
      .pop()!
      .replace(/\.[^.]+$/, '')
  ] = url;
const img = (name: string | null | undefined) => (name ? IMG[name] : null);

interface Item {
  img: string | null;
  x: number;
  y: number;
  h: number;
  plate?: boolean;
  circular?: boolean;
  bezel?: boolean;
  label?: string;
  pw?: number | null;
  ph?: number | null;
  iw?: number | null;
  ih?: number | null;
  beat: string;
  highlight?: boolean;
  target?: number;
}
interface Edge {
  src: number;
  dst: number;
  when: number;
  sides: [Side, Side];
  style: 'straight' | 'elbow';
  bus?: number | null;
}
interface PieceJson {
  slot: 'logo' | 'people' | 'dir' | 'center' | 'overlay' | 'left';
  kind:
    | 'logo'
    | 'freelogo'
    | 'people'
    | 'code'
    | 'stat'
    | 'facts'
    | 'section'
    | 'timeline'
    | 'graph'
    | 'title'
    | 'comparison'
    | 'screen'
    | 'round'
    | 'duel'
    | 'verdict'
    | 'bars'
    | 'profile'
    | 'profiles'
    | 'scorestrip';
  props: any;
  beat: string;
}
interface Scene {
  id: string;
  kind: 'graph' | 'impact' | 'item' | 'section' | 'timeline' | 'shortlist' | 'broll';
  items?: Item[];
  edges?: Edge[];
  lines?: string[];
  size?: number;
  tag?: string;
  style?: 'monokai' | 'report';
  idx?: number;
  total?: number;
  name?: string;
  color?: string;
  pieces?: PieceJson[];
  menu?: {src: number; dst: number} | null;
  light?: boolean;
  nva?: number;
  sub?: string;
  hud?: boolean;
  logo?: string | null;
  logo_plate?: boolean;
  logo_asp?: number;
  title?: string;
  label?: string | null;
  data?: string | null;
  dur?: number;
}

const VIDS = import.meta.glob('../videos/*.mp4', {eager: true, import: 'default'}) as Record<string, string>;
const vid = (n: string) => VIDS[`../videos/${n}.mp4`];

/**
 * PRÉVIA do B-roll no editor (porta 9000): preenchimento embaixo + clipes (proxies 640p) nos mesmos tempos do CapCut, por baixo do overlay.
 * Ligada por `BROLL_PREVIEW` (plan_data.py -> preview.json) e AUTOMATICAMENTE desligada ao renderizar: o .mov final fica só com o overlay.
 */
function* preview(view: View2D): ThreadGenerator {
  if (!(PREVIEW as any).active || useScene().playback.state === PlaybackState.Rendering) return;
  const background = new Video({src: vid('filler'), size: [1920, 1080], loop: true});
  view.add(background);
  background.moveToBottom();
  background.play();
  let t = 0;
  for (const c of (PREVIEW as any).clips as {video: string; t0: number; dur: number; speed: number}[]) {
    if (c.t0 > t) yield* waitFor(c.t0 - t);
    const v = new Video({src: vid(c.video), size: [1920, 1080], playbackRate: c.speed});
    view.add(v);
    v.moveToBottom();
    background.moveToBottom();
    v.play();
    yield* waitFor(c.dur);
    v.remove();
    t = c.t0 + c.dur;
  }
}

const ev = (id: string, beat: string) => waitUntil(`${id}-${beat}`);

function* graph(view: View2D, c: Scene): ThreadGenerator {
  const items = c.items!;
  const nodes = items.map(it =>
    it.img
      ? figure(IMG[it.img], {
          x: it.x,
          y: it.y,
          height: it.h,
          plate: it.plate,
          circular: it.circular,
          bezel: it.bezel,
          label: it.label,
          pw: it.pw,
          ph: it.ph,
          iw: it.iw,
          ih: it.ih,
        })
      : null,
  );
  nodes.forEach(n => n && view.add(n));
  const arrows = (c.edges ?? []).map(a =>
    arrowBetween(nodes[a.src]!, nodes[a.dst]!, a.sides[0], a.sides[1], a.style, a.bus),
  );
  let last = '';
  for (const [i, it] of items.entries()) {
    if (it.beat !== last) {
      yield* ev(c.id, it.beat);
      last = it.beat;
    }
    if (it.img) {
      const entering = (c.edges ?? []).map((a, k) => (a.when === i ? k : -1)).filter(k => k >= 0);
      yield all(
        ...entering.map(k => drawArrow(arrows[k], 0.35)),
        delay(entering.length ? 0.2 : 0, appear(nodes[i]!)),
      );
    }
    if (it.highlight) yield emphasize(nodes[it.target ?? i]!, 3);
  }
  yield* ev(c.id, 'out');
  const every = [...nodes.filter(n => n), ...arrows.map(s => s())] as Node[];
  yield* all(...every.map(n => vanish(n)));
  every.forEach(n => n.remove());
}

function* text(view: View2D, c: Scene) {
  const t =
    c.style === 'report' ? impactReport(view, c.lines!, c.size) : impact(view, c.lines!, c.size, c.tag);
  yield* ev(c.id, 'in');
  yield* t.enter();
  yield* ev(c.id, 'out');
  yield* t.exit();
  t.no.remove();
}

/** Layout LEVE (itens com B-roll por baixo): peças menores nos cantos para não esconder o vídeo. [x, y, escala] */
const POS_LIGHT = {
  left: [-720, 0, 0.6],
  logo: [-770, -400, 0.5],
  people: [-770, 320, 0.55],
  dir: [540, 290, 0.62],
  center: [0, 0, 1],
} as Record<string, number[]>;
const POS = {left: [-470, 10], logo: [-640, -235], people: [-640, 250], dir: [300, 28], center: [0, 0]} as Record<
  string,
  number[]
>;

function build(p: PieceJson): {piece: Piece; reveal?: () => any} {
  const a = p.props;
  switch (p.kind) {
    case 'freelogo':
      return {piece: freeLogo(img(a.logo)!, a.h ?? 250, !!a.plate, a.asp ?? 1)};
    case 'logo':
      return {piece: logoCard(img(a.logo) ?? null, a.name, a.year, a.color, a.acronym, 190, a.asp ?? 1)};
    case 'people':
      return {
        piece: peopleCard(
          a.people.map((x: any) => ({photo: img(x.photo) ?? null, name: x.name, role: x.role})),
          IMG['ic-user'],
          !!a.group,
        ),
      };
    case 'stat':
      return {piece: statCard(a.value, a.label, a.color, a.pct)};
    case 'facts':
      return {piece: factsList(a.lines.map((l: any) => ({icon: IMG[l.icon], text: l.text, color: l.color})))};
    case 'comparison':
      return {
        piece: comparison(
          a.columns.map((c: any) => ({...c, logo: img(c.logo)})),
          a.lines,
        ),
      };
    case 'screen':
      return {piece: screenCard(IMG[a.img], a.caption, a.width)};
    case 'graph':
      return {piece: graphPiece(a.items, a.edges, (n: string) => IMG[n], a.events ?? [])};
    case 'section':
      return {
        piece: sectionCard(
          a.tag,
          a.title,
          a.sub,
          (a.logos ?? []).map((l: string) => IMG[l]),
        ),
      };
    case 'code': {
      const code = (codes as any)[a.id];
      const j = codeWindow(
        code.file,
        code.language,
        code.color,
        code.lines,
        a.width ?? 1040,
        [IMG['ic-files-cinza'], IMG['ic-search-cinza'], IMG['ic-git-branch-cinza']].filter(Boolean),
      );
      return {
        piece: {
          no: j.no,
          *enter() {
            yield* j.reveal();
          },
          *exit() {
            yield* all(j.no.opacity(0, 0.3));
          },
        },
      };
    }
    case 'round':
      return {piece: roundCard(a.n, a.title, a.sub ?? '', {...a.a, logo: img(a.a.logo)}, {...a.b, logo: img(a.b.logo)})};
    case 'duel':
      return {piece: duel({...a.a, logo: img(a.a.logo)}, {...a.b, logo: img(a.b.logo)}, a.focus ?? 'both')};
    case 'verdict':
      return {piece: verdictBadge(a.label, a.result, a.sub ?? '', a.color, img(a.logo), a.asp ?? 1)};
    case 'bars':
      return {
        piece: barsChart(
          a.title,
          a.unit ?? '',
          a.items.map((i: any) => ({...i, logo: img(i.logo)})),
          a.note ?? '',
        ),
      };
    case 'profile':
      return {piece: profileCard(a.n, {...a.profile, logo: img(a.profile.logo)})};
    case 'profiles':
      return {piece: profileRow(a.profiles.map((p: any) => ({...p, logo: img(p.logo)})))};
    case 'scorestrip':
      return {piece: scoreStrip(a.results)};
    default:
      throw new Error('peca desconhecida ' + p.kind);
  }
}

/** Cena de item da lista / seção: menu (troca de item) + peças em slots (logo, criadores, direita). */
function* composite(view: View2D, c: Scene): ThreadGenerator {
  const wraps: Node[] = [];
  const overlays = c.pieces!.filter(p => p.slot === 'overlay');
  const pieces = c.pieces!.filter(p => p.slot !== 'overlay').map(p => ({p, ...build(p)}));
  const titles = overlays.map(p => {
    const t = impact(view, p.props.lines, p.props.size, p.props.tag);
    t.no.position([0, -10]);
    return {p, t};
  });
  for (const q of pieces) {
    const [x, y, zoom0] = c.light
      ? POS_LIGHT[q.p.slot]
      : [...POS[q.p.slot], q.p.slot === 'center' && ['facts', 'stat', 'comparison'].includes(q.p.kind) ? 1.45 : 1];
    // grafo: ampliado (esc) e centrado — o usuário dava zoom 1,4–1,7× à mão em todo grafo
    const [gx, gy, zoom] =
      q.p.kind === 'graph' && !c.light
        ? [(q.p.props.dx as number) ?? 0, (q.p.props.dy as number) ?? 0, (q.p.props.zoom as number) ?? 1.5]
        : [x, y, zoom0];
    const wrap = new Node({position: [gx, gy], scale: zoom});
    q.piece.no.position([0, 0]);
    wrap.add(q.piece.no);
    view.add(wrap);
    wraps.push(wrap);
  }
  const hud = c.idx && c.hud ? hudItem(c.idx, c.total!, c.name!, c.color!) : null;
  if (hud) {
    hud.no.position([690, 498]);
    view.add(hud.no);
  }
  let menu: {no: any; enter: (src: number, dst: number) => any; exit: () => any} | null = null;
  let title: Piece | null = null;
  if (c.menu) {
    menu =
      (LISTING as any).style === 'terminal'
        ? menuTerminal(MENU as any, 840, (LISTING as any).title)
        : menuExplorer(MENU as any, 700, (LISTING as any).title);
    menu.no.position([(LISTING as any).style === 'terminal' ? -450 : -520, 0]);
    view.add(menu.no);
    title = titleItem(c.idx!, c.name!, c.sub ?? '', c.color!, c.total!, img(c.logo), !!c.logo_plate, c.logo_asp ?? 1);
    title.no.position([(LISTING as any).style === 'terminal' ? 440 : 400, 0]);
    view.add(title.no);
  }
  yield* waitUntil(`${c.id}-in`);
  if (menu) {
    const m = menu;
    const tt = title!;
    yield (function* () {
      yield delay(0.5, tt.enter());
      yield* m.enter(c.menu!.src, c.menu!.dst);
      yield* waitFor(1.9);
      yield* all(m.exit(), tt.exit());
      m.no.remove();
      tt.no.remove();
    })();
  }
  // Itens sem peças (tipo Lista com B-roll: overlay mínimo): só menu/cartela + HUD (entra quando a cartela sai)
  const shown: Node[] = [];
  if (hud) {
    yield delay(c.menu ? 3.7 : 0.2, hud.enter());
    shown.push(hud.no);
  }
  const current: Record<string, Piece | null> = {};
  const visible: Piece[] = [];
  const visibleW: Node[] = [];
  // B-roll: a cada início de clipe (evento <id>-vaK) as peças somem; só o HUD fica por cima do vídeo
  for (let k = 0; k < (c.nva ?? 0); k++) {
    const name = `${c.id}-va${k}`;
    yield (function* () {
      yield* waitUntil(name);
      const listing = visible.splice(0, visible.length);
      const ws = visibleW.splice(0, visibleW.length);
      // some tudo de imediato (inclusive linhas que ainda estavam entrando): nada de peça solta sobre o clipe
      yield* all(...ws.map(w => w.opacity(0, 0.12)), ...listing.map(p => p.exit()));
      ws.forEach(w => w.opacity(0));
    })();
  }
  let last = 'in';
  const order = [
    ...pieces.map(q => ({p: q.p, q, t: null as any})),
    ...titles.map(t => ({p: t.p, q: null as any, t: t.t})),
  ].sort(
    (x, y) =>
      Number(x.p.beat.replace('b', '').replace('in', '0')) - Number(y.p.beat.replace('b', '').replace('in', '0')),
  );
  for (const o of order) {
    if (o.p.beat !== last) {
      yield* ev(c.id, o.p.beat);
      last = o.p.beat;
    }
    if (o.t) {
      const t = o.t;
      const dur = o.p.props.dur as number;
      const visible = shown.slice();
      // "palco central": o resto escurece enquanto o título fala, depois volta
      yield (function* () {
        yield* all(...visible.map(n => n.opacity(0, 0.25)));
        yield* t.enter();
        yield* waitFor(dur);
        yield* t.exit();
        t.no.remove();
        yield* all(...visible.map(n => n.opacity(1, 0.35)));
      })();
      continue;
    }
    const q = o.q;
    const ant = current[q.p.slot];
    // duelo seguido de duelo (troca de foco A→B→veredito): transição SUAVE no mesmo cartão, sem sair e entrar de novo
    if (ant && q.p.kind === 'duel' && ant.kind === 'duel' && ant.setFocus) {
      yield* ant.setFocus((q.p.props.focus as string) ?? 'both');
      (q.piece.no.parent() as Node).remove();
      continue;
    }
    shown.push(q.piece.no);
    if (ant && (q.p.slot === 'dir' || q.p.slot === 'left' || (q.p.slot === 'center' && q.p.kind !== 'section'))) {
      yield* ant.exit();
      const k = shown.indexOf(ant.no);
      if (k >= 0) shown.splice(k, 1);
    }
    // grafo ampliado e centralizado ocupa o quadro todo: o logo solto da esquerda sai antes (senão fica sob os itens do grafo)
    const leftLogo = current['left'];
    if (q.p.kind === 'graph' && !c.light && leftLogo) {
      current['left'] = null;
      const k = shown.indexOf(leftLogo.no);
      if (k >= 0) shown.splice(k, 1);
      yield* leftLogo.exit();
    }
    current[q.p.slot] = q.piece;
    visible.push(q.piece);
    visibleW.push(q.piece.no.parent() as Node);
    yield q.piece.enter();
  }
  yield* ev(c.id, 'out');
  const every = pieces.map(q => q.piece);
  if (hud) every.push(hud);
  yield* all(...every.map(p => p.exit()));
  every.forEach(p => p.no.remove());
  wraps.forEach(w => w.remove());
}

function* timing(view: View2D, c: Scene) {
  const p = c.pieces![0];
  const lt = timeline(
    p.props.items.map((x: any) => ({year: x.year, name: x.name, logo: img(x.logo), color: x.color, acronym: x.acronym})),
  );
  view.add(lt.no);
  const milestones: {beat: string; i: number}[] = p.props.milestones;
  let last = '';
  for (const m of milestones) {
    if (m.beat !== last) {
      yield* ev(c.id, m.beat);
      last = m.beat;
    }
    yield lt.show(m.i);
  }
  yield* ev(c.id, 'out');
  yield* lt.exit();
  lt.no.remove();
}

/** Webdoc com B-roll: lista curta no meio do vídeo (cartões numerados entrando na fala). */
function* shortListScene(view: View2D, c: Scene): ThreadGenerator {
  const items = (c as any).items as {icon: string; label: string; num: number}[];
  const lc = shortList(
    c.title ?? '',
    items.map(i => ({...i, icon: IMG[i.icon] ?? null})),
    ((c as any).color as string) ?? '#66d9ef',
  );
  lc.no.position([0, 0]);
  view.add(lc.no);
  const npauses = (((c as any).pauses as number[][]) ?? []).length;
  for (let j = 0; j < npauses; j++) {
    yield (function* () {
      yield* waitUntil(`${c.id}-p${j}a`);
      yield* lc.hide();
      yield* waitUntil(`${c.id}-p${j}b`);
      yield* lc.reappear();
    })();
  }
  yield* waitUntil(`${c.id}-in`);
  for (let k = 0; k < items.length; k++) {
    yield* waitUntil(`${c.id}-i${k}`);
    yield* lc.show(k);
  }
  yield* ev(c.id, 'out');
  yield* lc.exit();
  lc.no.remove();
}

/** Webdoc com B-roll: janela de vídeo; overlay LEVE = rótulo/data/logo no canto inferior ESQUERDO (o direito é do avatar). */
function* brollScene(view: View2D, c: Scene): ThreadGenerator {
  yield* waitUntil(`${c.id}-in`);
  if (c.dur && (c.label || c.data || c.logo)) {
    const tall = Math.min(86, 150 / Math.max(c.logo_asp ?? 1, 0.2));
    const strip = (
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
          c.logo_plate ? (
            <Rect padding={[8, 14]} radius={14} fill="#ffffff" alignItems="center">
              <Img src={IMG[c.logo]} height={tall} />
            </Rect>
          ) : (
            <Img src={IMG[c.logo]} height={tall} />
          )
        ) : null}
        <Rect layout direction="column" gap={6} alignItems="start">
          {c.label ? (
            <Txt
              text={c.label}
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
    view.add(strip);
    yield* waitFor(0.6);
    yield* all(strip.opacity(1, 0.35), strip.x(-910, 0.45, easeOutCubic));
    yield* waitFor(Math.max(c.dur - 0.9, 0.2));
    yield* strip.opacity(0, 0.3);
    strip.remove();
  }
  yield* ev(c.id, 'out');
}

export default makeScene2D(function* (view) {
  yield preview(view);
  for (const c of scenes as unknown as Scene[]) {
    if (c.kind === 'impact') yield* text(view, c);
    else if (c.kind === 'item' || c.kind === 'section') yield* composite(view, c);
    else if (c.kind === 'timeline') yield* timing(view, c);
    else if (c.kind === 'shortlist') yield* shortListScene(view, c);
    else if (c.kind === 'broll') yield* brollScene(view, c);
    else yield* graph(view, c);
  }
  yield* waitUntil('end'); // fecha exatamente na duração do áudio
});
