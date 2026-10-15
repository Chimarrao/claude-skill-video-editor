import {Node} from '@motion-canvas/2d';
import {all, easeInCubic} from '@motion-canvas/core';

/** Fade out rápido (~0.25s), com leve encolhida. */
export function* sumir(node: Node, duracao = 0.25) {
  yield* all(node.opacity(0, duracao, easeInCubic), node.scale(0.95, duracao, easeInCubic));
}
