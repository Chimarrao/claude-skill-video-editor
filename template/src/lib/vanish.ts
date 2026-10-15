import {Node} from '@motion-canvas/2d';
import {all, easeInCubic} from '@motion-canvas/core';

/** Fade out rápido (~0.25s), com leve encolhida. */
export function* vanish(node: Node, duration = 0.25) {
  yield* all(node.opacity(0, duration, easeInCubic), node.scale(0.95, duration, easeInCubic));
}
