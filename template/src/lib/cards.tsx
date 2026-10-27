import {Node, Circle, Img, Layout, Rect, Txt} from '@motion-canvas/2d';
import {
  all,
  createRef,
  easeInOutSine,
  easeOutBack,
  easeOutCubic,
  sequence,
  ThreadGenerator,
  waitFor,
} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {WHITE, FONT, SHADOW, SHADOW_TEXT, ACCENTS, tint} from './style';

/** Numeração: zero à esquerda só quando o total passa de 9 (01/12, mas 1/4). */
export const num = (i: number, total: number) => (total > 9 ? String(i).padStart(2, '0') : String(i));

/** Pulso sutil de escala num nó (usado nas animações de ambiente). */
export function* pulse(no: Node, amp = 1.045) {
  yield* no.scale(amp, 0.4, easeInOutSine);
  yield* no.scale(1, 0.5, easeInOutSine);
}

/** Percorre os itens em ciclo (um pulso a cada ~3 s) — mantém a tela viva em retenções longas. */
export function* cycle(nodes: Node[], start = 3, step = 3, amp = 1.05) {
  yield* waitFor(start);
  let i = 0;
  while (true) {
    yield* pulse(nodes[i % nodes.length], amp);
    yield* waitFor(Math.max(0.1, step - 0.9));
    i++;
  }
}

export interface Piece {
  no: Rect;
  /** Animação de ambiente opcional (loop); o motor cancela quando a peça deixa de ser a ativa. */
  ambient?(): ThreadGenerator;
  /** Peças que sabem trocar de estado sem sair/entrar (ex.: duelo trocando o foco A→B): o motor chama isto no lugar de exit()+enter(). */
  kind?: string;
  setFocus?(focus: string): ThreadGenerator;
  enter(): ThreadGenerator;
  exit(): ThreadGenerator;
}

function pieceSimple(no: Rect, extra?: () => ThreadGenerator): Piece {
  no.opacity(0);
  return {
    no,
    *enter() {
      no.scale(0.9);
      yield* all(no.opacity(1, 0.35), no.scale(1, 0.45, easeOutCubic), ...(extra ? [extra()] : []));
    },
    *exit() {
      yield* all(no.opacity(0, 0.28), no.scale(0.96, 0.28));
    },
  };
}

/** Logo grande à esquerda: cru (sem cartão) quando tem transparência; em cartão branco arredondado quando é opaco. Padrão de edição do usuário (~250 px, centro-esquerda). */
export function freeLogo(logo: string, height = 250, plate = false, asp = 1): Piece {
  height = Math.min(height, 520 / Math.max(asp, 0.2));
  const no = (
    plate ? (
      <Rect
        layout
        padding={[26, 34]}
        radius={32}
        fill="#ffffff"
        alignItems="center"
        justifyContent="center"
        {...SHADOW}
      >
        <Img src={logo} height={height - 40} />
      </Rect>
    ) : (
      <Rect layout alignItems="center" justifyContent="center">
        <Img src={logo} height={height} />
      </Rect>
    )
  ) as Rect;
  return pieceSimple(no);
}

/** Logo oficial em placa branca + nome e ano. Sem logo oficial: `sigla` em fonte mono sobre fundo Monokai. */
export function logoCard(
  logo: string | null,
  name: string,
  year: string,
  color: string,
  acronym?: string,
  height = 190,
  asp = 1,
): Piece {
  height = Math.min(height, 420 / Math.max(asp, 0.2));
  const plate = logo ? (
    <Rect padding={[34, 46]} radius={36} fill="#ffffff" alignItems="center" justifyContent="center" {...SHADOW}>
      <Img src={logo} height={height} />
    </Rect>
  ) : (
    <Rect padding={[34, 56]} radius={36} fill={MK.background} stroke={color} lineWidth={5} alignItems="center" {...SHADOW}>
      <Txt
        text={acronym ?? name.slice(0, 3).toUpperCase()}
        fontFamily={MONO}
        fontWeight={800}
        fontSize={height * 0.62}
        fill={color}
      />
    </Rect>
  );
  const no = (
    <Rect layout direction="column" alignItems="center" gap={22}>
      {plate}
      <Rect
        layout
        radius={16}
        fill="rgba(39,40,34,0.94)"
        paddingLeft={26}
        paddingRight={26}
        paddingTop={12}
        paddingBottom={12}
        gap={20}
        alignItems="center"
        stroke="rgba(255,255,255,0.14)"
        lineWidth={2}
      >
        <Txt text={name} fontFamily={FONT} fontWeight={800} fontSize={50} fill={WHITE} />
        <Txt text={year} fontFamily={MONO} fontWeight={700} fontSize={34} fill={MK.yellow} />
      </Rect>
    </Rect>
  ) as Rect;
  return pieceSimple(no);
}

export interface Person {
  photo: string | null;
  name: string;
  role?: string;
}

/** Criadores: foto redonda com anel branco + nome (+ papel). `grupo` = foto única retangular com vários nomes. */
export function peopleCard(people: Person[], iconUser: string, group = false): Piece {
  if (group) {
    const no = (
      <Rect layout direction="column" alignItems="center" gap={16}>
        <Rect radius={24} clip stroke={WHITE} lineWidth={8} {...SHADOW}>
          <Img src={people[0].photo!} width={560} />
        </Rect>
        {people
          .filter(p => p.name)
          .map(p => (
            <Txt
              text={p.name}
              fontFamily={FONT}
              fontWeight={800}
              fontSize={34}
              fill={WHITE}
              stroke="#0b0b10"
              lineWidth={8}
              strokeFirst
              lineJoin="round"
            />
          ))}
      </Rect>
    ) as Rect;
    return pieceSimple(no);
  }
  const n = people.length;
  const size = n === 1 ? 230 : n === 2 ? 180 : 130;
  const fs = n === 1 ? 40 : n === 2 ? 32 : 24;
  const width = size + (n >= 3 ? 36 : 70);
  const no = (
    <Rect layout direction="row" gap={n === 1 ? 0 : n === 2 ? 24 : 12} alignItems="start">
      {people.map(p => (
        <Rect direction="column" alignItems="center" gap={12} width={width}>
          <Rect
            size={size}
            radius={size / 2}
            clip
            stroke={WHITE}
            lineWidth={8}
            fill={MK.background}
            alignItems="center"
            justifyContent="center"
            {...SHADOW}
          >
            {p.photo ? <Img src={p.photo} size={size} /> : <Img src={iconUser} size={size * 0.55} />}
          </Rect>
          <Txt
            text={p.name}
            width={width}
            textWrap
            fontFamily={FONT}
            fontWeight={800}
            fontSize={fs}
            textAlign="center"
            fill={WHITE}
            stroke="#0b0b10"
            lineWidth={8}
            strokeFirst
            lineJoin="round"
          />
          {p.role ? (
            <Txt
              text={p.role}
              width={width}
              textWrap
              fontFamily={FONT}
              fontWeight={500}
              fontSize={fs * 0.72}
              textAlign="center"
              fill="#d9d9cc"
              stroke="#0b0b10"
              lineWidth={6}
              strokeFirst
              lineJoin="round"
            />
          ) : null}
        </Rect>
      ))}
    </Rect>
  ) as Rect;
  return pieceSimple(no);
}

/** Número grande (estatística) em painel Monokai; `pct` (0–100) acrescenta um donut que se completa. */
export function statCard(value: string, label: string, color: string, pct?: number): Piece {
  const arc = createRef<Circle>();
  const no = (
    <Rect
      layout
      direction="row"
      gap={40}
      alignItems="center"
      padding={[36, 48]}
      radius={24}
      fill="rgba(39,40,34,0.95)"
      stroke="rgba(255,255,255,0.14)"
      lineWidth={2}
      {...SHADOW}
    >
      {pct != null ? (
        <Rect size={230} alignItems="center" justifyContent="center">
          <Circle layout={false} size={210} stroke="rgba(255,255,255,0.12)" lineWidth={26} />
          <Circle
            ref={arc}
            layout={false}
            size={210}
            stroke={color}
            lineWidth={26}
            lineCap="round"
            startAngle={-90}
            endAngle={-90}
          />
          <Txt layout={false} text={value} fontFamily={MONO} fontWeight={800} fontSize={58} fill={color} />
        </Rect>
      ) : null}
      <Rect direction="column" gap={10} alignItems="start" width={pct != null ? 520 : 680}>
        {pct == null ? (
          <Rect layout direction="row" alignItems="end" gap={18}>
            {value.split(' ').map((part, k, all_) => (
              <Txt
                text={part}
                fontFamily={MONO}
                fontWeight={800}
                fontSize={Math.max(70, Math.min(130, 680 / (value.replace(' ', '').length * 0.62 + 1))) * (k > 0 && all_.length > 1 ? 0.62 : 1)}
                fill={color}
              />
            ))}
          </Rect>
        ) : null}
        <Txt
          text={label}
          width={pct != null ? 520 : 680}
          textWrap
          fontFamily={FONT}
          fontWeight={600}
          fontSize={38}
          fill={WHITE}
        />
      </Rect>
    </Rect>
  ) as Rect;
  return pieceSimple(no, function* () {
    if (pct != null) yield* arc().endAngle(-90 + 360 * (pct / 100), 1.1, easeOutCubic);
  });
}

export interface FactLine {
  icon: string;
  text: string;
  color?: string;
}
/** Lista de fatos: ícone de linha em disco + frase curta; entram em sequência. */
export function factsList(lines: FactLine[]): Piece {
  // MODELO A (escolhido pelo usuário): painel escuro discreto, faixa colorida só na borda esquerda, ícone sobre tinta suave da mesma cor.
  const items: Rect[] = [];
  const W = 960;
  const H = 124;
  const no = (<Rect layout direction="column" gap={22} alignItems="center" />) as Rect;
  lines.forEach((l, i) => {
    const accent = l.color ?? ACCENTS[i % ACCENTS.length];
    const r = (
      <Rect
        layout
        width={W}
        height={H}
        radius={20}
        fill="#12141c"
        stroke="rgba(255,255,255,0.12)"
        lineWidth={2}
        alignItems="center"
        gap={28}
        paddingLeft={44}
        paddingRight={36}
        clip
        opacity={0}
      >
        <Rect layout={false} x={-W / 2 + 9} width={18} height={H} fill={accent} />
        <Rect layout width={78} height={78} radius={39} fill={tint(accent, 0.22)} alignItems="center" justifyContent="center">
          <Img src={l.icon} size={46} />
        </Rect>
        <Txt text={l.text} width={W - 220} textWrap fontFamily={FONT} fontWeight={700} fontSize={44} fill={WHITE} />
      </Rect>
    ) as Rect;
    items.push(r);
    no.add(r);
  });
  return {
    no,
    *enter() {
      items.forEach(r => r.x(60));
      yield* sequence(0.45, ...items.map(r => all(r.opacity(1, 0.35), r.x(0, 0.45, easeOutCubic))));
    },
    *exit() {
      yield* all(...items.map(r => r.opacity(0, 0.25)));
    },
  };
}

/** Marcador discreto no canto: nº do item / total + linguagem. */
export function hudItem(idx: number, total: number, name: string, color: string): Piece {
  const no = (
    <Rect
      layout
      radius={14}
      fill="rgba(39,40,34,0.92)"
      paddingLeft={20}
      paddingRight={22}
      paddingTop={10}
      paddingBottom={10}
      gap={14}
      alignItems="center"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={2}
    >
      <Circle size={16} fill={color} />
      <Txt text={`${num(idx, total)}/${total}`} fontFamily={MONO} fontWeight={700} fontSize={26} fill={MK.green} />
      <Txt text={name} fontFamily={MONO} fontWeight={600} fontSize={26} fill={MK.text} />
    </Rect>
  ) as Rect;
  return pieceSimple(no);
}

/** Cartela de seção / parte da lista (comentário + título + subtítulo + logos das linguagens da seção). */
export function sectionCard(tag: string, title: string, sub: string, logos: string[]): Piece {
  const no = (
    <Rect
      layout
      direction="column"
      gap={22}
      alignItems="start"
      padding={[44, 64]}
      radius={26}
      fill="rgba(39,40,34,0.95)"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={2}
      {...SHADOW}
    >
      <Txt text={`// ${tag}`} fontFamily={MONO} fontWeight={600} fontSize={34} fill={MK.comment} />
      <Txt text={title} fontFamily={FONT} fontWeight={800} fontSize={86} fill={WHITE} />
      <Txt text={sub} fontFamily={MONO} fontWeight={600} fontSize={36} fill={MK.green} />
      {logos.length ? (
        <Rect layout gap={20} marginTop={10}>
          {logos.map(u => (
            <Rect width={96} height={96} radius={20} fill="#ffffff" alignItems="center" justifyContent="center">
              <Img src={u} width={64} height={64} />
            </Rect>
          ))}
        </Rect>
      ) : null}
    </Rect>
  ) as Rect;
  return pieceSimple(no);
}

/** Cartela grande do item (mostrada junto do menu na troca de item): nº, nome e subtítulo. */
export function titleItem(
  idx: number,
  name: string,
  sub: string,
  color: string,
  total = 10,
  logo?: string | null,
  plate = false,
  asp = 1,
): Piece {
  const tall = Math.min(210, 360 / Math.max(asp, 0.2));
  const no = (
    <Rect layout direction="column" gap={20} alignItems="start" width={800}>
      {logo ? (
        plate ? (
          <Rect padding={[18, 28]} radius={26} fill="#ffffff" alignItems="center" justifyContent="center" {...SHADOW}>
            <Img src={logo} height={tall - 36} />
          </Rect>
        ) : (
          <Img src={logo} height={tall} />
        )
      ) : null}
      <Txt text={`#${num(idx, total)}`} fontFamily={MONO} fontWeight={700} fontSize={64} fill={MK.comment} />
      <Txt
        text={name}
        fontFamily={FONT}
        fontWeight={800}
        fontSize={Math.min(name.length > 15 ? 84 : name.length > 9 ? 120 : 170, Math.floor(780 / (0.55 * name.length)))} // nunca passa da largura da cartela (800)
        fill={WHITE}
        stroke="#0b0b10"
        lineWidth={14}
        strokeFirst
        lineJoin="round"
      />
      <Rect width={260} height={10} radius={5} fill={color} />
      <Txt
        text={sub}
        fontFamily={MONO}
        fontWeight={600}
        fontSize={40}
        fill={MK.green}
        stroke="#0b0b10"
        lineWidth={8}
        strokeFirst
        lineJoin="round"
      />
    </Rect>
  ) as Rect;
  return pieceSimple(no);
}

export interface ComparisonColumn {
  logo: string | null;
  label: string;
  color: string;
}
export interface ComparisonRow {
  label: string;
  values: string[];
  wins?: number | null;
}

/** Comparison A vs B em painel Monokai: cabeçalho com logos e linhas que entram em sequência; o vencedor da linha ganha ✓ verde. */
export function comparison(columns: ComparisonColumn[], lines: ComparisonRow[]): Piece {
  const items: Rect[] = [];
  const WIDTH_LABEL = 330;
  const WIDTH_COL = 330;
  const no = (
    <Rect
      layout
      direction="column"
      gap={14}
      padding={[28, 32]}
      radius={24}
      fill="rgba(39,40,34,0.95)"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={2}
      {...SHADOW}
    >
      <Rect layout gap={14} alignItems="center">
        <Rect width={WIDTH_LABEL} />
        {columns.map(c => (
          <Rect width={WIDTH_COL} direction="column" alignItems="center" gap={8}>
            {c.logo ? (
              <Rect padding={[10, 16]} radius={16} fill="#ffffff" alignItems="center" justifyContent="center">
                <Img src={c.logo} height={64} />
              </Rect>
            ) : null}
            <Txt text={c.label} fontFamily={MONO} fontWeight={800} fontSize={30} fill={c.color} />
          </Rect>
        ))}
      </Rect>
    </Rect>
  ) as Rect;
  for (const l of lines) {
    const r = (
      <Rect layout gap={14} alignItems="center" padding={[10, 0]} opacity={0}>
        <Txt
          text={l.label}
          width={WIDTH_LABEL}
          textWrap
          fontFamily={FONT}
          fontWeight={600}
          fontSize={30}
          fill="#d9d9cc"
        />
        {l.values.map((v, i) => (
          <Rect
            width={WIDTH_COL}
            alignItems="center"
            justifyContent="center"
            gap={10}
            padding={[12, 10]}
            radius={14}
            fill={l.wins === i ? 'rgba(166,226,46,0.16)' : 'rgba(255,255,255,0.05)'}
            stroke={l.wins === i ? '#a6e22e' : null}
            lineWidth={2}
          >
            <Txt
              text={v}
              width={WIDTH_COL - 30}
              textWrap
              textAlign="center"
              fontFamily={MONO}
              fontWeight={700}
              fontSize={32}
              fill={l.wins === i ? '#a6e22e' : WHITE}
            />
          </Rect>
        ))}
      </Rect>
    ) as Rect;
    items.push(r);
    no.add(r);
  }
  no.opacity(0);
  return {
    no,
    *enter() {
      no.scale(0.94);
      yield* all(no.opacity(1, 0.35), no.scale(1, 0.4, easeOutCubic));
      yield* sequence(0.5, ...items.map(r => r.opacity(1, 0.3)));
    },
    *exit() {
      yield* all(no.opacity(0, 0.28));
    },
  };
}

/** Captura de tela / foto em moldura com aro branco e legenda (bom para interfaces). */
export function screenCard(image: string, caption: string, width = 900): Piece {
  const no = (
    <Rect layout direction="column" alignItems="center" gap={14}>
      <Rect radius={20} clip stroke={WHITE} lineWidth={6} {...SHADOW}>
        <Img src={image} width={width} />
      </Rect>
      <Txt
        text={caption}
        fontFamily={FONT}
        fontWeight={800}
        fontSize={36}
        fill={WHITE}
        stroke="#0b0b10"
        lineWidth={8}
        strokeFirst
        lineJoin="round"
      />
    </Rect>
  ) as Rect;
  return pieceSimple(no);
}
