import {Layout, Line} from '@motion-canvas/2d';
import {createRef, easeInOutCubic, Reference, Vector2} from '@motion-canvas/core';
import {BRANCO, SOMBRA} from './estilo';

export type Lado = 'left' | 'right' | 'top' | 'bottom';
export type EstiloSeta = 'reta' | 'cotovelo';

const ESPESSURA = 11;

/**
 * Seta grossa (Line com endArrow) ligando as bordas de `a` e `b`; começa com end=0.
 * Os pontos são funções dos nodes, então a seta acompanha se eles se moverem.
 * `cotovelo` faz um caminho em ângulo reto com cantos arredondados (bom para árvores);
 * `reta` é uma linha direta. `a` e `b` devem ter o mesmo pai (a seta entra no pai de `a`).
 */
export function setaEntre(
  a: Layout,
  b: Layout,
  ladoA: Lado = 'right',
  ladoB: Lado = 'left',
  estilo: EstiloSeta = 'reta',
  bus?: number | null,
): Reference<Line> {
  const ref = createRef<Line>();
  const p0 = () => a[ladoA]();
  const p3 = () => b[ladoB]();
  const horizontal = ladoA === 'right' || ladoA === 'left';
  const meio = () => (bus != null ? bus : horizontal ? (p0().x + p3().x) / 2 : (p0().y + p3().y) / 2);
  const p1 = () => (horizontal ? new Vector2(meio(), p0().y) : new Vector2(p0().x, meio()));
  const p2 = () => (horizontal ? new Vector2(meio(), p3().y) : new Vector2(p3().x, meio()));
  a.parent()!.add(
    <Line
      ref={ref}
      points={estilo === 'cotovelo' ? [p0, p1, p2, p3] : [p0, p3]}
      stroke={BRANCO}
      lineWidth={ESPESSURA}
      endArrow
      arrowSize={ESPESSURA * 2.6}
      lineCap="round"
      lineJoin="round"
      radius={estilo === 'cotovelo' ? 44 : 0}
      end={0}
      {...SOMBRA}
    />,
  );
  return ref;
}

/** Desenha a seta (end 0 → 1). */
export function* desenharSeta(seta: Reference<Line>, duracao = 0.5) {
  yield* seta().end(1, duracao, easeInOutCubic);
}
