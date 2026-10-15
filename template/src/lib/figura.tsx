import {Img, Rect, RectProps, Txt, TxtProps} from '@motion-canvas/2d';
import {BRANCO, FONTE, RAIO, SOMBRA, SOMBRA_TEXTO} from './estilo';

export interface FiguraOpcoes extends RectProps {
  /** Altura da imagem em px (largura proporcional). */
  altura?: number;
  /** Placa branca arredondada atrás da imagem (logos escuros/coloridos sobre vídeo). */
  placa?: boolean;
  /** Ícone de linha dentro de um disco escuro translúcido com aro fino (tom sério, legível sobre qualquer vídeo). */
  moldura?: boolean;
  /** Foto de pessoa: recorte circular com anel branco. */
  redondo?: boolean;
  /** Rótulo curto (nome, data, número). Fica abaixo da imagem sem afetar o layout/setas. */
  rotulo?: string;
  /** Geometria exata calculada pelo plano.py (placa pw×ph com imagem iw×ih dentro). */
  pw?: number | null;
  ph?: number | null;
  iw?: number | null;
  ih?: number | null;
}

/** Imagem solta (PNG/WebP/SVG com transparência) com sombra suave; nasce invisível. */
export function figura(
  imagem: string,
  {altura = 280, placa = false, redondo = false, moldura = false, rotulo, pw, ph, iw, ih, ...props}: FiguraOpcoes = {},
): Rect {
  const tamanho = 36;
  if (rotulo) rotulo = rotulo.charAt(0).toUpperCase() + rotulo.slice(1); // primeira letra sempre maiúscula
  const texto = (extra: TxtProps = {}) =>
    (
      <Txt
        text={rotulo}
        {...extra}
        fontFamily={FONTE}
        fontWeight={800}
        fontSize={tamanho}
        fill={BRANCO}
        stroke="#0b0b10"
        lineWidth={9}
        strokeFirst
        lineJoin="round"
        {...SOMBRA_TEXTO}
      />
    ) as Txt;
  if (moldura) {
    return (
      <Rect opacity={0} size={altura} {...props}>
        <Rect
          size={altura}
          radius={altura / 2}
          fill="rgba(10, 12, 18, 0.62)"
          stroke="rgba(255,255,255,0.92)"
          lineWidth={4}
          {...SOMBRA}
        >
          <Img src={imagem} size={altura * 0.56} />
        </Rect>
        {rotulo ? texto({layout: false, y: altura / 2 + 46}) : null}
      </Rect>
    ) as Rect;
  }
  if (redondo) {
    return (
      <Rect opacity={0} size={altura} {...props}>
        <Rect size={altura} radius={altura / 2} clip stroke={BRANCO} lineWidth={10} {...SOMBRA}>
          <Img src={imagem} size={altura} />
        </Rect>
        {rotulo ? texto({layout: false, y: altura / 2 + 46}) : null}
      </Rect>
    ) as Rect;
  }
  // Rótulo abaixo da imagem; um espaçador invisível simétrico em cima mantém o centro da imagem/placa no centro
  // do nó (as setas ligam no meio). Placa: tamanho fixo calculado no plano.py (nada de caixas desproporcionais).
  const reserva = tamanho * 1.35;
  const miolo =
    placa && pw && ph ? (
      <Rect
        size={[pw, ph]}
        radius={Math.min(RAIO, ph * 0.2)}
        fill={BRANCO}
        alignItems="center"
        justifyContent="center"
        {...SOMBRA}
      >
        <Img src={imagem} width={iw ?? undefined} height={ih ?? undefined} />
      </Rect>
    ) : (
      <Img src={imagem} width={iw ?? undefined} height={ih ?? altura} {...SOMBRA} />
    );
  return (
    <Rect layout direction="column" alignItems="center" gap={8} opacity={0} {...props}>
      {rotulo ? <Rect height={reserva} /> : null}
      {miolo}
      {rotulo ? (
        <Rect height={reserva} alignItems="center" justifyContent="center">
          {texto()}
        </Rect>
      ) : null}
    </Rect>
  ) as Rect;
}
