import {Layout, Line} from '@motion-canvas/2d';
import {createRef, easeInOutCubic, Reference, Vector2} from '@motion-canvas/core';
import {WHITE, SHADOW} from './style';

export type Side = 'left' | 'right' | 'top' | 'bottom';
export type StyleArrow = 'straight' | 'elbow';

const THICKNESS = 11;

const TIP_GAP = 4; // vão entre a ponta da seta e a borda do miolo (espelha geometry.TIP_GAP)

/**
 * Ponto de ligação de `n` no lado `side`. Colunas (placa/logo com rótulo) expõem `core` = [largura, altura] do miolo: a seta
 * encosta na placa/imagem e não na caixa da coluna, que é mais larga/alta por causa do rótulo. Sem `core` (disco, foto redonda): borda do nó.
 * Saída por baixo (`bottom`) continua na borda da coluna, depois do rótulo.
 */
function anchor(n: Layout, side: Side): Vector2 {
  const core = (n as any).core as [number, number] | undefined;
  if (!core || side === 'bottom') return n[side]();
  const c = n.position();
  const [w, h] = core;
  if (side === 'left') return c.addX(-w / 2 - TIP_GAP);
  if (side === 'right') return c.addX(w / 2 + TIP_GAP);
  return c.addY(-h / 2 - TIP_GAP);
}

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
  const p0 = () => (drop ? anchor(a, sideA).addY(drop) : anchor(a, sideA));
  const p3 = () => anchor(b, sideB);
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
