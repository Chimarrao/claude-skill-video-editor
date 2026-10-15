import {Layout, Rect, RectProps, Txt} from '@motion-canvas/2d';
import {ThreadGenerator, all, easeOutCubic, waitFor} from '@motion-canvas/core';
import {BRANCO, FONTE, FUNDO_CARD, RAIO, SOMBRA, SOMBRA_TEXTO, TRACO} from './estilo';

export interface Lista {
  /** Container da lista (adicione à cena). */
  no: Layout;
  /** Faz o item `i` entrar (fade + desliza da esquerda). Use com waitUntil para sincronizar item a item. */
  mostrar(i: number): ThreadGenerator;
  /** Entrada em sequência automática, `intervalo` segundos entre itens. */
  todos(intervalo?: number): ThreadGenerator;
  /** Some o container inteiro. */
  esconder(duracao?: number): ThreadGenerator;
}

/** Itens entrando em sequência, cada um numa pílula branca arredondada. */
export function lista(itens: string[], props: RectProps = {}): Lista {
  const no = (
    <Layout layout direction="column" gap={22} alignItems="start" {...props}>
      {itens.map(t => (
        <Rect
          layout
          alignItems="center"
          gap={22}
          padding={[22, 44]}
          radius={RAIO}
          fill={FUNDO_CARD}
          stroke={BRANCO}
          lineWidth={TRACO}
          opacity={0}
          {...SOMBRA}
        >
          <Rect width={18} height={18} radius={9} fill={BRANCO} />
          <Txt text={t} fontFamily={FONTE} fontWeight={600} fontSize={52} fill={BRANCO} {...SOMBRA_TEXTO} />
        </Rect>
      ))}
    </Layout>
  ) as Layout;
  const filhos = () => no.children() as Rect[];
  return {
    no,
    *mostrar(i: number) {
      const it = filhos()[i];
      it.opacity(0);
      it.x(-60);
      yield* all(it.opacity(1, 0.4, easeOutCubic), it.x(0, 0.4, easeOutCubic));
    },
    *todos(intervalo = 0.6) {
      for (let i = 0; i < itens.length; i++) {
        yield* this.mostrar(i);
        yield* waitFor(intervalo);
      }
    },
    *esconder(duracao = 0.25) {
      yield* no.opacity(0, duracao);
    },
  };
}
