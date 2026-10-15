import {Rect} from '@motion-canvas/2d';
import {all, delay, waitFor, waitUntil} from '@motion-canvas/core';
import {Peca} from './cartoes';
import {figura} from './figura';
import {setaEntre} from './setaEntre';
import {desenharSeta} from './setaEntre';
import {aparecer} from './aparecer';
import type {Lado} from './setaEntre';

export interface ItemG {
  img: string | null;
  x: number;
  y: number;
  h: number;
  placa?: boolean;
  redondo?: boolean;
  moldura?: boolean;
  rotulo?: string | null;
  pw?: number | null;
  ph?: number | null;
  iw?: number | null;
  ih?: number | null;
}
export interface ArestaG {
  de: number;
  para: number;
  quando: number;
  lados: [Lado, Lado];
  estilo: 'reta' | 'cotovelo';
  bus?: number | null;
}

/** Grafo/árvore dentro de uma peça (região da direita): os itens aparecem em sequência (0.55s), setas se desenham junto. */
export function grafoPeca(
  itens: ItemG[],
  arestas: ArestaG[],
  url: (nome: string) => string,
  eventos: (string | null)[] = [],
): Peca {
  const no = (<Rect />) as Rect;
  const nos = itens.map(it =>
    it.img
      ? figura(url(it.img), {
          x: it.x,
          y: it.y,
          altura: it.h,
          placa: it.placa,
          redondo: it.redondo,
          moldura: it.moldura,
          rotulo: it.rotulo ?? undefined,
          pw: it.pw,
          ph: it.ph,
          iw: it.iw,
          ih: it.ih,
        })
      : null,
  );
  nos.forEach(n => n && no.add(n));
  const setas = arestas.map(a => setaEntre(nos[a.de]!, nos[a.para]!, a.lados[0], a.lados[1], a.estilo, a.bus));
  return {
    no,
    *entrar() {
      for (const [i, n] of nos.entries()) {
        if (!n) continue;
        const entrando = arestas.map((a, k) => (a.quando === i ? k : -1)).filter(k => k >= 0);
        const ev = eventos[i];
        if (ev) yield* waitUntil(ev); // item sincronizado com a palavra falada
        yield all(...entrando.map(k => desenharSeta(setas[k], 0.35)), delay(entrando.length ? 0.2 : 0, aparecer(n)));
        if (!ev) yield* waitFor(0.55);
      }
    },
    *sair() {
      yield* no.opacity(0, 0.3);
    },
  };
}
