import {Rect} from '@motion-canvas/2d';
import {all, delay, waitFor, waitUntil} from '@motion-canvas/core';
import {Piece} from './cards';
import {figure} from './figure';
import {arrowBetween} from './arrowBetween';
import {drawArrow} from './arrowBetween';
import {appear} from './appear';
import type {Side} from './arrowBetween';

export interface ItemG {
  img: string | null;
  x: number;
  y: number;
  h: number;
  plate?: boolean;
  circular?: boolean;
  bezel?: boolean;
  label?: string | null;
  pw?: number | null;
  ph?: number | null;
  iw?: number | null;
  ih?: number | null;
}
export interface EdgeG {
  src: number;
  dst: number;
  when: number;
  sides: [Side, Side];
  style: 'straight' | 'elbow';
  bus?: number | null;
}

/** Grafo/árvore dentro de uma peça (região da direita): os itens aparecem em sequência (0.55s), setas se desenham junto. */
export function graphPiece(
  items: ItemG[],
  edges: EdgeG[],
  url: (name: string) => string,
  events: (string | null)[] = [],
): Piece {
  const no = (<Rect />) as Rect;
  const nodes = items.map(it =>
    it.img
      ? figure(url(it.img), {
          x: it.x,
          y: it.y,
          height: it.h,
          plate: it.plate,
          circular: it.circular,
          bezel: it.bezel,
          label: it.label ?? undefined,
          pw: it.pw,
          ph: it.ph,
          iw: it.iw,
          ih: it.ih,
        })
      : null,
  );
  nodes.forEach(n => n && no.add(n));
  const arrows = edges.map(a => arrowBetween(nodes[a.src]!, nodes[a.dst]!, a.sides[0], a.sides[1], a.style, a.bus));
  return {
    no,
    *enter() {
      for (const [i, n] of nodes.entries()) {
        if (!n) continue;
        const entering = edges.map((a, k) => (a.when === i ? k : -1)).filter(k => k >= 0);
        const ev = events[i];
        if (ev) yield* waitUntil(ev); // item sincronizado com a palavra falada
        yield all(...entering.map(k => drawArrow(arrows[k], 0.35)), delay(entering.length ? 0.2 : 0, appear(n)));
        if (!ev) yield* waitFor(0.55);
      }
    },
    *exit() {
      yield* no.opacity(0, 0.3);
    },
  };
}
