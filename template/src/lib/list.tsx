import {Layout, Rect, RectProps, Txt} from '@motion-canvas/2d';
import {ThreadGenerator, all, easeOutCubic, waitFor} from '@motion-canvas/core';
import {WHITE, FONT, BACKGROUND_CARD, RADIUS, SHADOW, SHADOW_TEXT, STROKE} from './style';

export interface Listing {
  /** Container da lista (adicione à cena). */
  no: Layout;
  /** Faz o item `i` entrar (fade + desliza da esquerda). Use com waitUntil para sincronizar item a item. */
  show(i: number): ThreadGenerator;
  /** Entrada em sequência automática, `intervalo` segundos entre itens. */
  every(interval?: number): ThreadGenerator;
  /** Some o container inteiro. */
  hide(duration?: number): ThreadGenerator;
}

/** Itens entrando em sequência, cada um numa pílula branca arredondada. */
export function listing(items: string[], props: RectProps = {}): Listing {
  const no = (
    <Layout layout direction="column" gap={22} alignItems="start" {...props}>
      {items.map(t => (
        <Rect
          layout
          alignItems="center"
          gap={22}
          padding={[22, 44]}
          radius={RADIUS}
          fill={BACKGROUND_CARD}
          stroke={WHITE}
          lineWidth={STROKE}
          opacity={0}
          {...SHADOW}
        >
          <Rect width={18} height={18} radius={9} fill={WHITE} />
          <Txt text={t} fontFamily={FONT} fontWeight={600} fontSize={52} fill={WHITE} {...SHADOW_TEXT} />
        </Rect>
      ))}
    </Layout>
  ) as Layout;
  const children = () => no.children() as Rect[];
  return {
    no,
    *show(i: number) {
      const it = children()[i];
      it.opacity(0);
      it.x(-60);
      yield* all(it.opacity(1, 0.4, easeOutCubic), it.x(0, 0.4, easeOutCubic));
    },
    *every(interval = 0.6) {
      for (let i = 0; i < items.length; i++) {
        yield* this.show(i);
        yield* waitFor(interval);
      }
    },
    *hide(duration = 0.25) {
      yield* no.opacity(0, duration);
    },
  };
}
