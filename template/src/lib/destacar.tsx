import {Layout, Rect} from '@motion-canvas/2d';
import {all, createRef, easeInOutSine, loop, sequence, waitFor} from '@motion-canvas/core';
import {DESTAQUE, RAIO} from './estilo';

/** Contorno pulsando em volta do node. Dura `pulsos` ciclos de 0.5s e remove o contorno. */
export function* destacar(node: Layout, pulsos = 3, cor = DESTAQUE) {
  const anel = createRef<Rect>();
  node.add(
    <Rect
      ref={anel}
      size={() => node.size().add(28)}
      radius={RAIO + 10}
      stroke={cor}
      lineWidth={0}
      opacity={0}
      layout={false}
    />,
  );
  for (let i = 0; i < pulsos; i++) {
    yield* all(anel().opacity(1, 0.25, easeInOutSine), anel().lineWidth(8, 0.25, easeInOutSine));
    yield* all(anel().opacity(0.35, 0.25, easeInOutSine), anel().lineWidth(3, 0.25, easeInOutSine));
  }
  yield* anel().opacity(0, 0.2);
  anel().remove();
}
