import {Layout, Line} from '@motion-canvas/2d';
import {createRef, easeInOutCubic, Reference, Vector2} from '@motion-canvas/core';
import {WHITE, SHADOW} from './style';

export type Side = 'left' | 'right' | 'top' | 'bottom';
export type StyleArrow = 'straight' | 'elbow';

const THICKNESS = 11;

/**
 * Seta grossa (Line com endArrow) ligando as bordas de `a` e `b`; começa com end=0.
 * Os pontos são funções dos nodes, então a seta acompanha se eles se moverem.
 * `cotovelo` faz um caminho em ângulo reto com cantos arredondados (bom para árvores);
 * `reta` é uma linha direta. `a` e `b` devem ter o mesmo pai (a seta entra no pai de `a`).
 */
export function arrowBetween(
  a: Layout,
  b: Layout,
  sideA: Side = 'right',
  sideB: Side = 'left',
  style: StyleArrow = 'straight',
  bus?: number | null,
): Reference<Line> {
  const ref = createRef<Line>();
  const drop = sideA === 'bottom' ? ((a as any).labelDrop as number | undefined) ?? 0 : 0; // saída por baixo começa depois do rótulo
  const p0 = () => (drop ? a[sideA]().addY(drop) : a[sideA]());
  const p3 = () => b[sideB]();
  const horizontal = sideA === 'right' || sideA === 'left';
  const middle = () => (bus != null ? bus : horizontal ? (p0().x + p3().x) / 2 : (p0().y + p3().y) / 2);
  const p1 = () => (horizontal ? new Vector2(middle(), p0().y) : new Vector2(p0().x, middle()));
  const p2 = () => (horizontal ? new Vector2(middle(), p3().y) : new Vector2(p3().x, middle()));
  a.parent()!.add(
    <Line
      ref={ref}
      points={style === 'elbow' ? [p0, p1, p2, p3] : [p0, p3]}
      stroke={WHITE}
      lineWidth={THICKNESS}
      endArrow
      arrowSize={THICKNESS * 2.6}
      lineCap="round"
      lineJoin="round"
      radius={style === 'elbow' ? 44 : 0}
      end={0}
      {...SHADOW}
    />,
  );
  return ref;
}

/** Desenha a seta (end 0 → 1). */
export function* drawArrow(arrow: Reference<Line>, duration = 0.5) {
  yield* arrow().end(1, duration, easeInOutCubic);
}
