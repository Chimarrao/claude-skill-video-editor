import {Img, Layout, Rect, RectProps, Txt} from '@motion-canvas/2d';
import {BRANCO, FONTE, FUNDO_CARD, RAIO, SOMBRA, SOMBRA_TEXTO, TRACO} from './estilo';

/**
 * Card arredondado: imagem opcional no topo, `texto` em destaque e `legenda` menor.
 * `imagem` é a URL importada (`import logo from '../images/x.svg'`).
 * Nasce invisível (opacity 0) — use `aparecer(card)`.
 */
export function card(texto: string, imagem?: string, legenda?: string, props: RectProps = {}): Rect {
  return (
    <Rect
      layout
      direction="column"
      alignItems="center"
      justifyContent="center"
      gap={18}
      padding={[36, 52]}
      minWidth={360}
      radius={RAIO}
      fill={FUNDO_CARD}
      stroke={BRANCO}
      lineWidth={TRACO}
      opacity={0}
      {...SOMBRA}
      {...props}
    >
      {imagem ? <Img src={imagem} height={140} /> : null}
      <Txt
        text={texto}
        fontFamily={FONTE}
        fontWeight={700}
        fontSize={56}
        fill={BRANCO}
        textAlign="center"
        {...SOMBRA_TEXTO}
      />
      {legenda ? (
        <Txt
          text={legenda}
          fontFamily={FONTE}
          fontWeight={400}
          fontSize={34}
          fill="rgba(255,255,255,0.85)"
          textAlign="center"
          {...SOMBRA_TEXTO}
        />
      ) : null}
    </Rect>
  ) as Rect;
}
