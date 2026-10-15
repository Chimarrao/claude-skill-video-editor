import {Img, Layout, Rect, RectProps, Txt} from '@motion-canvas/2d';
import {WHITE, FONT, BACKGROUND_CARD, RADIUS, SHADOW, SHADOW_TEXT, STROKE} from './style';

/**
 * Card arredondado: imagem opcional no topo, `texto` em destaque e `legenda` menor.
 * `imagem` é a URL importada (`import logo from '../images/x.svg'`).
 * Nasce invisível (opacity 0) — use `aparecer(card)`.
 */
export function card(text: string, image?: string, caption?: string, props: RectProps = {}): Rect {
  return (
    <Rect
      layout
      direction="column"
      alignItems="center"
      justifyContent="center"
      gap={18}
      padding={[36, 52]}
      minWidth={360}
      radius={RADIUS}
      fill={BACKGROUND_CARD}
      stroke={WHITE}
      lineWidth={STROKE}
      opacity={0}
      {...SHADOW}
      {...props}
    >
      {image ? <Img src={image} height={140} /> : null}
      <Txt
        text={text}
        fontFamily={FONT}
        fontWeight={700}
        fontSize={56}
        fill={WHITE}
        textAlign="center"
        {...SHADOW_TEXT}
      />
      {caption ? (
        <Txt
          text={caption}
          fontFamily={FONT}
          fontWeight={400}
          fontSize={34}
          fill="rgba(255,255,255,0.85)"
          textAlign="center"
          {...SHADOW_TEXT}
        />
      ) : null}
    </Rect>
  ) as Rect;
}
