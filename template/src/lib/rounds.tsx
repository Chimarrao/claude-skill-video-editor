import {Circle, Img, Rect, Txt} from '@motion-canvas/2d';
import {all, createRef, easeInOutCubic, easeOutBack, easeOutCubic, sequence, ThreadGenerator, waitFor} from '@motion-canvas/core';
import {FONT, SHADOW, SHADOW_TEXT, WHITE} from './style';
import {Piece} from './cards';

/**
 * Peças do tipo "Webdoc com rounds" (comparativo A × B em estilo ringue/versus): cartela de round, duelo, selo de vencedor,
 * barras de dados, cartas de perfil e placar final. Cada lado do duelo tem cor própria (A quente, B frio por padrão).
 * Tudo cabe em 1920×1080 e evita a zona do avatar (canto inferior direito).
 */
export interface DuelSide {
  name: string;
  logo?: string | null;
  asp?: number;
  color: string;
  chips?: string[];
}
export interface ProfileData {
  title: string;
  traits: string[];
  edition: string;
  color: string;
  logo?: string | null;
  asp?: number;
  tag?: string;
}
export interface RoundResult {
  label: string;
  result: string;
  winner: 'A' | 'B' | 'draw' | 'depends';
  color: string;
}

const PANEL = 'rgba(14, 16, 22, 0.9)';
const EDGE = 'rgba(255, 255, 255, 0.2)';

/** Entrada/saída padrão de uma peça de round: fade + escala curta. */
function basic(no: Rect, extra?: () => ThreadGenerator): Piece {
  no.opacity(0);
  return {
    no,
    *enter() {
      no.scale(0.94);
      yield* all(no.opacity(1, 0.35), no.scale(1, 0.45, easeOutCubic), ...(extra ? [extra()] : []));
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.scale(0.97, 0.3));
    },
  };
}

/** Logo em placa branca (tamanho máximo wxh, mantendo a proporção). */
function plate(logo: string | null | undefined, asp = 1, w = 190, h = 130, pad = 22) {
  if (!logo) return null;
  const iw = Math.min(w, h * asp);
  return (
    <Rect padding={pad} radius={28} fill="#ffffff" alignItems="center" justifyContent="center" {...SHADOW}>
      <Img src={logo} width={iw} height={iw / asp} />
    </Rect>
  );
}

const txt = (text: string, size: number, fill: string, weight = 800, extra: any = {}) => (
  <Txt text={text} fontFamily={FONT} fontWeight={weight} fontSize={size} fill={fill} {...extra} />
);

/** Cartela "ROUND N": os dois lados nas pontas, o número grande no meio e o tema embaixo. */
export function roundCard(n: string, title: string, sub: string, a: DuelSide, b: DuelSide): Piece {
  const left = createRef<Rect>();
  const right = createRef<Rect>();
  const mid = createRef<Rect>();
  const side = (s: DuelSide, ref: any) => (
    <Rect
      ref={ref}
      layout
      direction="column"
      alignItems="center"
      gap={20}
      width={480}
      paddingTop={34}
      paddingBottom={34}
      radius={34}
      fill={PANEL}
      stroke={s.color}
      lineWidth={6}
      {...SHADOW}
    >
      {plate(s.logo, s.asp ?? 1)}
      {txt(s.name, 54, s.color, 800, {textWrap: true, width: 420, textAlign: 'center'})}
    </Rect>
  );
  const no = (
    <Rect layout direction="row" alignItems="center" gap={34}>
      {side(a, left)}
      <Rect ref={mid} layout direction="column" alignItems="center" gap={6} width={520} paddingTop={26} paddingBottom={26} radius={34} fill={PANEL} stroke={EDGE} lineWidth={3} {...SHADOW}>
        {txt('ROUND', 52, 'rgba(255,255,255,0.75)', 800, {letterSpacing: 14})}
        {txt(n, 250, WHITE, 900, {shadowColor: 'rgba(0,0,0,0.7)', shadowBlur: 24, shadowOffset: [0, 8]})}
        {txt(title, 54, WHITE, 800, {textWrap: true, width: 500, textAlign: 'center', ...SHADOW_TEXT})}
        {sub ? txt(sub, 34, 'rgba(255,255,255,0.7)', 600, {textWrap: true, width: 500, textAlign: 'center'}) : null}
      </Rect>
      {side(b, right)}
    </Rect>
  ) as Rect;
  no.opacity(0);
  return {
    no,
    *enter() {
      left().x(-320);
      right().x(320);
      left().opacity(0);
      right().opacity(0);
      mid().scale(1.5);
      mid().opacity(0);
      yield* all(
        no.opacity(1, 0.15),
        left().x(0, 0.55, easeOutBack),
        left().opacity(1, 0.35),
        right().x(0, 0.55, easeOutBack),
        right().opacity(1, 0.35),
        mid().scale(1, 0.6, easeOutBack),
        mid().opacity(1, 0.3),
      );
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.scale(0.96, 0.3));
    },
  };
}

/** Duelo A × B: dois cartões com logo, nome e "chips" (3 traços), medalha VS no meio; `focus` destaca um lado e apaga o outro. */
export function duel(a: DuelSide, b: DuelSide, focus: 'A' | 'B' | 'both' | 'winA' | 'winB' = 'both'): Piece {
  const refs = [createRef<Rect>(), createRef<Rect>()];
  const bodies = [createRef<Rect>(), createRef<Rect>()];
  const badges = [createRef<Rect>(), createRef<Rect>()];
  // O painel (fundo) é SEMPRE o mesmo, em qualquer foco. Foco A/B: o lado que não está sendo descrito perde só o CONTEÚDO (logo, nome, chips) e a
  // borda afina. winA/winB (veredito): os dois ficam inteiros; o vencedor ganha borda grossa e a faixa "VENCE" (sobre a borda, fora do fluxo).
  // Trocar de foco NÃO recria a peça: `setFocus` anima o conteúdo, a borda e a faixa (transição suave entre um lado e outro).
  const target = (f: string, i: number) => ({
    dim: (f === 'A' && i === 1) || (f === 'B' && i === 0),
    win: (f === 'winA' && i === 0) || (f === 'winB' && i === 1),
  });
  const card = (s: DuelSide, i: number) => {
    const t = target(focus, i);
    return (
      <Rect
        ref={refs[i]}
        layout
        direction="column"
        alignItems="center"
        gap={22}
        width={700}
        paddingTop={38}
        paddingBottom={38}
        radius={36}
        fill={PANEL}
        stroke={s.color}
        lineWidth={t.dim ? 3 : t.win ? 10 : 7}
        {...SHADOW}
      >
        <Rect ref={badges[i]} layout={false} width={250} height={58} radius={22} fill={s.color} y={() => -refs[i]().height() / 2} zIndex={2} opacity={t.win ? 1 : 0}>
          {txt('VENCE', 40, '#0b0b10', 900, {letterSpacing: 8})}
        </Rect>
        <Rect ref={bodies[i]} layout direction="column" alignItems="center" gap={22} opacity={t.dim ? 0.38 : 1}>
          {plate(s.logo, s.asp ?? 1, 210, 140)}
          {txt(s.name, 62, s.color, 900)}
          <Rect layout direction="column" gap={12} alignItems="start" width={560}>
            {(s.chips ?? []).map(c => (
              <Rect layout direction="row" gap={16} alignItems="center">
                <Circle size={16} fill={s.color} />
                {txt(c, 38, WHITE, 700, {textWrap: true, width: 520})}
              </Rect>
            ))}
          </Rect>
        </Rect>
      </Rect>
    );
  };
  const vs = (
    <Rect layout={false} width={140} height={140} radius={70} fill="#0b0b10" stroke={WHITE} lineWidth={6} {...SHADOW}>
      <Txt text="VS" fontFamily={FONT} fontWeight={900} fontSize={60} fill={WHITE} />
    </Rect>
  );
  const no = (
    <Rect layout direction="row" alignItems="center" gap={60}>
      {card(a, 0)}
      {card(b, 1)}
    </Rect>
  ) as Rect;
  no.add(vs);
  vs.position([0, -20]);
  no.opacity(0);
  return {
    no,
    kind: 'duel',
    *enter() {
      refs[0]().x(-260);
      refs[1]().x(260);
      vs.scale(0.4);
      yield* all(
        no.opacity(1, 0.3),
        refs[0]().x(0, 0.5, easeOutCubic),
        refs[1]().x(0, 0.5, easeOutCubic),
        vs.scale(1, 0.5, easeOutBack),
      );
    },
    *setFocus(f: string) {
      yield* all(
        ...[0, 1].map(i => {
          const t = target(f, i);
          return all(
            bodies[i]().opacity(t.dim ? 0.38 : 1, 0.45, easeInOutCubic),
            refs[i]().lineWidth(t.dim ? 3 : t.win ? 10 : 7, 0.45, easeInOutCubic),
            badges[i]().opacity(t.win ? 1 : 0, 0.45, easeInOutCubic),
          );
        }),
      );
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.scale(0.97, 0.3));
    },
  } as Piece;
}

/** Selo de vencedor do round (carimbo): "XFCE VENCE", "EMPATE", "DEPENDE DO PERFIL". */
export function verdictBadge(label: string, result: string, sub: string, color: string, logo?: string | null, asp = 1): Piece {
  const no = (
    <Rect
      layout
      direction="row"
      alignItems="center"
      gap={44}
      paddingTop={44}
      paddingBottom={44}
      paddingLeft={64}
      paddingRight={64}
      radius={38}
      fill={PANEL}
      stroke={color}
      lineWidth={10}
      {...SHADOW}
    >
      {plate(logo, asp, 200, 140)}
      <Rect layout direction="column" gap={10} alignItems="start" width={820}>
        {txt(label, 40, 'rgba(255,255,255,0.75)', 800, {letterSpacing: 8})}
        {txt(result, result.length > 16 ? 86 : 110, color, 900, {textWrap: true, width: 820})}
        {sub ? txt(sub, 38, WHITE, 600, {textWrap: true, width: 820}) : null}
      </Rect>
    </Rect>
  ) as Rect;
  no.opacity(0);
  return {
    no,
    *enter() {
      no.scale(1.7);
      no.rotation(-9);
      yield* all(no.opacity(1, 0.2), no.scale(1, 0.5, easeOutBack), no.rotation(-3, 0.5, easeOutBack));
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.scale(0.97, 0.3));
    },
  };
}

export interface BarItem {
  label: string;
  value: number;
  color: string;
  text: string;
  logo?: string | null;
  asp?: number;
}
/** Barras horizontais (ex.: RAM em repouso): crescem uma a uma e o valor aparece colado na ponta de cada barra. */
export function barsChart(title: string, unit: string, items: BarItem[], note = ''): Piece {
  const W = 900;
  const max = Math.max(...items.map(i => i.value)) * 1.25;
  const bars = items.map(() => createRef<Rect>());
  const vals = items.map(() => createRef<Txt>());
  const no = (
    <Rect
      layout
      direction="column"
      gap={30}
      paddingTop={44}
      paddingBottom={44}
      paddingLeft={56}
      paddingRight={56}
      radius={36}
      fill={PANEL}
      stroke={EDGE}
      lineWidth={3}
      {...SHADOW}
    >
      <Rect layout direction="row" gap={20} alignItems="end">
        {txt(title, 54, WHITE, 900)}
        {txt(unit, 34, 'rgba(255,255,255,0.65)', 600)}
      </Rect>
      {items.map((it, k) => (
        <Rect layout direction="row" gap={26} alignItems="center">
          <Rect layout direction="column" alignItems="center" gap={10} width={230}>
            {plate(it.logo, it.asp ?? 1, 120, 80, 12)}
            {txt(it.label, 38, it.color, 800)}
          </Rect>
          <Rect layout direction="row" gap={22} alignItems="center" width={W} height={78} radius={14} fill="rgba(255,255,255,0.06)">
            <Rect ref={bars[k]} height={78} radius={14} fill={it.color} width={4} />
            <Txt ref={vals[k]} text={it.text} fontFamily={FONT} fontWeight={900} fontSize={46} fill={WHITE} opacity={0} {...SHADOW_TEXT} />
          </Rect>
        </Rect>
      ))}
      {note ? txt(note, 32, 'rgba(255,255,255,0.7)', 600, {textWrap: true, width: 1100}) : null}
    </Rect>
  ) as Rect;
  no.opacity(0);
  return {
    no,
    *enter() {
      no.scale(0.94);
      yield* all(no.opacity(1, 0.35), no.scale(1, 0.45, easeOutCubic));
      yield* sequence(
        0.35,
        ...items.map((it, k) =>
          (function* () {
            yield* bars[k]().width(Math.max(8, (it.value / max) * (W - 330)), 0.9, easeOutCubic);
            yield* vals[k]().opacity(1, 0.25);
          })(),
        ),
      );
      yield* waitFor(0.1);
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.scale(0.97, 0.3));
    },
  };
}

/** Carta de perfil: "PERFIL N", título, traços e a faixa "INSTALE: <edição>" no rodapé. */
export function profileCard(n: string, p: ProfileData): Piece {
  const no = (
    <Rect
      layout
      direction="column"
      alignItems="center"
      width={1060}
      radius={38}
      fill={PANEL}
      stroke={p.color}
      lineWidth={7}
      clip
      {...SHADOW}
    >
      <Rect layout direction="row" gap={48} padding={52} alignItems="center" width={1060}>
        <Rect layout direction="column" alignItems="center" gap={10}>
          <Circle size={170} fill={p.color} alignItems="center" justifyContent="center" layout>
            {txt(n, 100, '#0b0b10', 900)}
          </Circle>
          {txt('PERFIL', 34, 'rgba(255,255,255,0.7)', 800, {letterSpacing: 10})}
        </Rect>
        <Rect layout direction="column" gap={18} alignItems="start" width={740}>
          {txt(p.title, 62, WHITE, 900, {textWrap: true, width: 740})}
          {p.traits.map(t => (
            <Rect layout direction="row" gap={16} alignItems="start">
              {txt('✓', 38, p.color, 900)}
              {txt(t, 38, 'rgba(255,255,255,0.92)', 600, {textWrap: true, width: 690})}
            </Rect>
          ))}
        </Rect>
      </Rect>
      <Rect layout direction="row" gap={30} alignItems="center" justifyContent="center" width={1060} height={150} fill={p.color}>
        {txt('INSTALE', 44, '#0b0b10', 800, {letterSpacing: 8})}
        {plate(p.logo, p.asp ?? 1, 150, 90, 12)}
        {txt(p.edition, 64, '#0b0b10', 900)}
      </Rect>
    </Rect>
  ) as Rect;
  no.opacity(0);
  return {
    no,
    *enter() {
      no.y(70);
      no.scale(0.96);
      yield* all(no.opacity(1, 0.4), no.y(0, 0.5, easeOutCubic), no.scale(1, 0.5, easeOutBack));
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.y(-40, 0.3));
    },
  };
}

/** Linha final com todos os perfis lado a lado (resumo): cartas compactas entrando em sequência. */
export function profileRow(profiles: ProfileData[]): Piece {
  const n = profiles.length;
  const w = Math.min(430, (1780 - 30 * (n - 1)) / n);
  const cards = profiles.map(() => createRef<Rect>());
  const no = (
    <Rect layout direction="row" gap={30} alignItems="stretch">
      {profiles.map((p, k) => (
        <Rect
          ref={cards[k]}
          layout
          direction="column"
          alignItems="center"
          width={w}
          radius={32}
          fill={PANEL}
          stroke={p.color}
          lineWidth={6}
          clip
          {...SHADOW}
        >
          <Rect layout direction="column" alignItems="center" gap={14} padding={30} height={330} justifyContent="center">
            <Circle size={96} fill={p.color} alignItems="center" justifyContent="center" layout>
              {txt(String(k + 1), 56, '#0b0b10', 900)}
            </Circle>
            {txt(p.tag ?? p.title, 38, WHITE, 800, {textWrap: true, width: w - 60, textAlign: 'center'})}
          </Rect>
          <Rect layout direction="column" alignItems="center" justifyContent="center" gap={8} width={w} height={150} fill={p.color}>
            {txt('INSTALE', 28, '#0b0b10', 800, {letterSpacing: 6})}
            {txt(p.edition, 46, '#0b0b10', 900, {textWrap: true, width: w - 40, textAlign: 'center'})}
          </Rect>
        </Rect>
      ))}
    </Rect>
  ) as Rect;
  no.opacity(0);
  return {
    no,
    *enter() {
      cards.forEach(c => {
        c().opacity(0);
        c().y(60);
      });
      yield no.opacity(1, 0.1);
      yield* sequence(0.35, ...cards.map(c => all(c().opacity(1, 0.4), c().y(0, 0.5, easeOutBack))));
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.scale(0.97, 0.3));
    },
  };
}

/** Placar final: um cartão por round com o resultado (sem somar pontos). */
export function scoreStrip(results: RoundResult[]): Piece {
  const n = results.length;
  const w = Math.min(560, (1700 - 34 * (n - 1)) / n);
  const cards = results.map(() => createRef<Rect>());
  const no = (
    <Rect layout direction="row" gap={34} alignItems="stretch">
      {results.map((r, k) => (
        <Rect
          ref={cards[k]}
          layout
          direction="column"
          alignItems="center"
          gap={16}
          width={w}
          padding={36}
          radius={34}
          fill={PANEL}
          stroke={r.color}
          lineWidth={7}
          {...SHADOW}
        >
          {txt(`ROUND ${k + 1}`, 36, 'rgba(255,255,255,0.7)', 800, {letterSpacing: 8})}
          {txt(r.label, 50, WHITE, 900, {textWrap: true, width: w - 72, textAlign: 'center'})}
          <Rect layout width={w - 72} height={6} radius={3} fill={r.color} />
          {txt(r.result, 54, r.color, 900, {textWrap: true, width: w - 72, textAlign: 'center'})}
        </Rect>
      ))}
    </Rect>
  ) as Rect;
  no.opacity(0);
  return {
    no,
    *enter() {
      cards.forEach(c => {
        c().opacity(0);
        c().scale(0.8);
      });
      yield no.opacity(1, 0.1);
      yield* sequence(0.4, ...cards.map(c => all(c().opacity(1, 0.35), c().scale(1, 0.5, easeOutBack))));
    },
    *exit() {
      yield* all(no.opacity(0, 0.3), no.scale(0.97, 0.3));
    },
  };
}
