import {Layout, Rect} from '@motion-canvas/2d';
import {all, createRef, easeInOutSine, loop, sequence, waitFor} from '@motion-canvas/core';
import {HIGHLIGHT, RADIUS} from './style';

/** Contorno pulsando em volta do node. Dura `pulsos` ciclos de 0.5s e remove o contorno. */
export function* emphasize(node: Layout, pulses = 3, color = HIGHLIGHT) {
  const ring = createRef<Rect>();
  node.add(
    <Rect
      ref={ring}
      size={() => node.size().add(28)}
      radius={RADIUS + 10}
      stroke={color}
      lineWidth={0}
      opacity={0}
      layout={false}
    />,
  );
  for (let i = 0; i < pulses; i++) {
    yield* all(ring().opacity(1, 0.25, easeInOutSine), ring().lineWidth(8, 0.25, easeInOutSine));
    yield* all(ring().opacity(0.35, 0.25, easeInOutSine), ring().lineWidth(3, 0.25, easeInOutSine));
  }
  yield* ring().opacity(0, 0.2);
  ring().remove();
}
