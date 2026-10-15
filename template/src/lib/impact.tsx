import {Layout, Rect, Txt, View2D} from '@motion-canvas/2d';
import {all, cancel, createRef, easeOutCubic, loop, ThreadGenerator, waitFor} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SHADOW} from './style';

/**
 * TEXTO DE IMPACTO DO CANAL — versão "terminal Monokai" (canal de programação, tom sério).
 * Referência: o efeito *typewriter* é o que mais lembra editor de código; fontes legíveis em movimento,
 * contraste forte e poucas palavras por vez (kinetic typography).
 * - Painel Monokai (#272822) com barra de destaque rosa à esquerda e etiqueta de comentário `// tag`.
 * - Linhas em MAIÚSCULAS mono, prefixo `>` verde, digitadas palavra por palavra (typewriter) com cursor ▌.
 * - Palavras-chave marcadas com asteriscos ganham cor do tema: `*rosa*`, `*v:verde*`, `*a:azul*`, `*l:laranja*`,
 *   `*y:amarelo*`, `*r:roxo*` (aceita várias palavras: `*v:DUAS PALAVRAS*`).
 * - Saída: o painel desliza 60px e some (0.35s).
 */
export interface ImpactCtl {
  no: Layout;
  enter(): ThreadGenerator;
  exit(): ThreadGenerator;
}

const COLOR_BRAND: Record<string, string> = {
  '': MK.pink,
  p: MK.pink,
  v: MK.green,
  a: MK.blue,
  l: MK.orange,
  y: MK.yellow,
  r: MK.purple,
};

export function impact(view: View2D, lines: string[], size = 84, tag = 'atenção'): ImpactCtl {
  const panel = createRef<Rect>();
  const cursor = createRef<Txt>();
  let blink: ThreadGenerator | null = null;
  const words: {t: Txt; text: string}[] = [];
  const root = (<Layout />) as Layout;
  let lastRow: Layout | null = null;
  const maxChars = Math.max(...lines.map(l => l.replace(/\*([a-z]:)?/g, '').length)) + 2;
  const width = Math.min(1700, maxChars * size * 0.61 + 190);
  const column = (<Layout layout direction="column" alignItems="start" gap={size * 0.22} />) as Layout;
  for (const line of lines) {
    const row = (<Layout layout direction="row" alignItems="center" gap={size * 0.62} />) as Layout;
    row.add(<Txt text=">" fontFamily={MONO} fontWeight={800} fontSize={size} fill={MK.green} />);
    let color: string | null = null;
    for (let raw of line.split(' ')) {
      let closes = false;
      const m = raw.match(/^\*([a-z]):?(.*)$/);
      if (raw.startsWith('*')) {
        const mm = raw.match(/^\*(?:([a-z]):)?(.*)$/)!;
        color = COLOR_BRAND[mm[1] ?? ''];
        raw = mm[2];
      }
      if (raw.endsWith('*')) {
        closes = true;
        raw = raw.slice(0, -1);
      }
      void m;
      const t = createRef<Txt>();
      row.add(<Txt ref={t} text="" fontFamily={MONO} fontWeight={800} fontSize={size} fill={color ?? MK.text} />);
      words.push({t: t(), text: raw});
      if (closes) color = null;
    }
    column.add(row);
    lastRow = row;
  }
  lastRow!.add(<Txt ref={cursor} text="▌" fontFamily={MONO} fontSize={size * 0.9} fill={MK.green} opacity={0} />);
  root.add(
    <Rect
      ref={panel}
      layout
      direction="column"
      gap={size * 0.3}
      width={width}
      padding={[size * 0.55, size * 0.7, size * 0.55, size * 0.9]}
      radius={22}
      fill="rgba(39, 40, 34, 0.96)"
      stroke="rgba(255,255,255,0.14)"
      lineWidth={2}
      opacity={0}
      {...SHADOW}
    >
      <Rect
        layout={false}
        width={14}
        height={() => panel().height() - 44}
        x={() => -panel().width() / 2 + 34}
        radius={7}
        fill={MK.pink}
      />
      {tag ? (
        <Txt
          text={`// ${tag}`}
          fontFamily={MONO}
          fontWeight={600}
          fontSize={Math.max(26, size * 0.36)}
          fill={MK.comment}
        />
      ) : null}
      {column}
    </Rect>,
  );
  view.add(root);
  return {
    no: root,
    *enter() {
      panel().x(-40);
      yield* all(panel().opacity(1, 0.25), panel().x(0, 0.4, easeOutCubic));
      cursor().opacity(1);
      for (const {t, text} of words) {
        yield* t.text(text, Math.max(0.07, text.length * 0.028));
        yield* waitFor(0.04);
      }
      blink = (yield loop(Infinity, function* () {
        yield* cursor().opacity(0.15, 0.45);
        yield* cursor().opacity(1, 0.45);
      })) as unknown as ThreadGenerator;
    },
    *exit() {
      if (blink) cancel(blink);
      yield* all(panel().opacity(0, 0.35), panel().x(60, 0.35));
    },
  };
}
