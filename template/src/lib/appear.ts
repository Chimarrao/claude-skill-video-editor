import {Node} from '@motion-canvas/2d';
import {all, easeOutCubic} from '@motion-canvas/core';

/** Fade in + escala 0.8 → 1 (~0.4s). */
export function* appear(node: Node, duration = 0.4) {
  node.opacity(0);
  node.scale(0.8);
  yield* all(node.opacity(1, duration, easeOutCubic), node.scale(1, duration, easeOutCubic));
}
