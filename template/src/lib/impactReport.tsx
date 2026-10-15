import {Layout, Rect, Txt, View2D} from '@motion-canvas/2d';
import {all, createRef, easeOutCubic, sequence, ThreadGenerator} from '@motion-canvas/core';
import {WHITE, FONT, SHADOW_TEXT} from './style';

/**
 * PADRÃO DE TEXTO DE IMPACTO DO CANAL (sério, estilo reportagem; ≤5% do vídeo, nunca no começo):
 * - Faixa escura translúcida de ponta a ponta com filetes vermelhos finos em cima e embaixo.
 * - Texto em MAIÚSCULAS, peso 800, branco, sem contorno de desenho animado, espaçamento de letras.
 * - Cada linha sobe 40px e aparece (mask/fade 0.5s), linhas em sequência (0.18s). Sem overshoot, sem giro.
 * - Palavra-chave (*asteriscos*): vermelho suave + filete vermelho que se desenha sob a palavra.
 * - Saída: tudo some em 0.35s (fade).
 */
export interface ReportImpactCtl {
  no: Layout;
  enter(): ThreadGenerator;
  exit(): ThreadGenerator;
}

const RED = '#ff5a5f';

export function impactReport(view: View2D, lines: string[], size = 120): ReportImpactCtl {
  const strip = createRef<Rect>();
  const dividers: Rect[] = [];
  const linesRef: Rect[] = [];
  const marks: Rect[] = [];
  const root = (<Layout />) as Layout;
  const height = lines.length * size * 1.25 + size * 1.1;
  root.add(
    <Rect ref={strip} width={1920} height={height} fill="rgba(6, 8, 14, 0.66)" opacity={0} scale={[1, 0.2]}>
      <Rect layout={false} width={1920} height={4} y={-height / 2} fill={RED} />
      <Rect layout={false} width={1920} height={4} y={height / 2} fill={RED} />
    </Rect>,
  );
  const column = (<Layout layout direction="column" alignItems="center" gap={size * 0.12} />) as Layout;
  for (const line of lines) {
    const row = createRef<Rect>();
    const internal = (<Layout layout direction="row" gap={size * 0.3} alignItems="center" />) as Layout;
    let marking = false;
    for (const raw of line.split(' ')) {
      const opens = raw.startsWith('*');
      const closes = raw.endsWith('*');
      if (opens) marking = true;
      const w = raw.replace(/\*/g, '');
      const marked = marking;
      if (closes) marking = false;
      const box = createRef<Rect>();
      const bar = createRef<Rect>();
      internal.add(
        <Rect ref={box} layout>
          <Txt
            text={w}
            fontFamily={FONT}
            fontWeight={800}
            fontSize={size}
            letterSpacing={size * 0.03}
            fill={marked ? RED : WHITE}
            {...SHADOW_TEXT}
            shadowBlur={22}
          />
          {marked ? (
            <Rect
              ref={bar}
              layout={false}
              width={() => box().width()}
              height={Math.max(5, size * 0.06)}
              fill={RED}
              offset={[-1, 0]}
              x={() => -box().width() / 2}
              y={() => box().height() / 2 + size * 0.03}
              scale={[0, 1]}
            />
          ) : null}
        </Rect>,
      );
      if (marked) marks.push(bar());
    }
    column.add(
      <Rect ref={row} layout clip opacity={0} y={40}>
        {internal}
      </Rect>,
    );
    linesRef.push(row());
  }
  root.add(column);
  view.add(root);
  void dividers;
  return {
    no: root,
    *enter() {
      yield* strip().opacity(1, 0.2);
      yield all(strip().scale([1, 1], 0.4, easeOutCubic));
      yield* sequence(0.18, ...linesRef.map(l => all(l.opacity(1, 0.5, easeOutCubic), l.y(0, 0.5, easeOutCubic))));
      yield* all(...marks.map(m => m.scale([1, 1], 0.45, easeOutCubic)));
    },
    *exit() {
      yield* all(root.opacity(0, 0.35));
    },
  };
}
