import {Img, Rect, RectProps, Txt, TxtProps} from '@motion-canvas/2d';
import {WHITE, FONT, RADIUS, SHADOW, SHADOW_TEXT} from './style';

export interface FigureOptions extends RectProps {
  /** Altura da imagem em px (largura proporcional). */
  height?: number;
  /** Placa branca arredondada atrás da imagem (logos escuros/coloridos sobre vídeo). */
  plate?: boolean;
  /** Ícone de linha dentro de um disco escuro translúcido com aro fino (tom sério, legível sobre qualquer vídeo). */
  bezel?: boolean;
  /** Foto de pessoa: recorte circular com anel branco. */
  circular?: boolean;
  /** Rótulo curto (nome, data, número). Fica abaixo da imagem sem afetar o layout/setas. */
  label?: string;
  /** Geometria exata calculada pelo plan.py (placa pw×ph com imagem iw×ih dentro). */
  pw?: number | null;
  ph?: number | null;
  iw?: number | null;
  ih?: number | null;
}

/** Imagem solta (PNG/WebP/SVG com transparência) com sombra suave; nasce invisível. */
export function figure(
  image: string,
  {height = 280, plate = false, circular = false, bezel = false, label, pw, ph, iw, ih, ...props}: FigureOptions = {},
): Rect {
  const size = 36;
  if (label) label = label.charAt(0).toUpperCase() + label.slice(1); // primeira letra sempre maiúscula
  const text = (extra: TxtProps = {}) =>
    (
      <Txt
        text={label}
        {...extra}
        fontFamily={FONT}
        fontWeight={800}
        fontSize={size}
        fill={WHITE}
        stroke="#0b0b10"
        lineWidth={9}
        strokeFirst
        lineJoin="round"
        {...SHADOW_TEXT}
      />
    ) as Txt;
  // Nos nós sem coluna (disco de ícone / foto redonda) o rótulo fica ABAIXO da caixa do nó: `labelDrop` diz às setas que saem
  // por baixo até onde o texto termina, para a seta nunca atravessar o rótulo.
  const comRotulo = (no: Rect) => {
    (no as any).labelDrop = label ? 80 : 0;
    return no;
  };
  if (bezel) {
    return comRotulo(
      <Rect opacity={0} size={height} {...props}>
        <Rect
          size={height}
          radius={height / 2}
          fill="rgba(10, 12, 18, 0.62)"
          stroke="rgba(255,255,255,0.92)"
          lineWidth={4}
          {...SHADOW}
        >
          <Img src={image} size={height * 0.56} />
        </Rect>
        {label ? text({layout: false, y: height / 2 + 46}) : null}
      </Rect> as Rect,
    );
  }
  if (circular) {
    return comRotulo(
      <Rect opacity={0} size={height} {...props}>
        <Rect size={height} radius={height / 2} clip stroke={WHITE} lineWidth={10} {...SHADOW}>
          <Img src={image} size={height} />
        </Rect>
        {label ? text({layout: false, y: height / 2 + 46}) : null}
      </Rect> as Rect,
    );
  }
  // Rótulo abaixo da imagem; um espaçador invisível simétrico em cima mantém o centro da imagem/placa no centro
  // do nó (as setas ligam no meio). Placa: tamanho fixo calculado no plan.py (nada de caixas desproporcionais).
  const reserve = size * 1.35;
  const core =
    plate && pw && ph ? (
      <Rect
        size={[pw, ph]}
        radius={Math.min(RADIUS, ph * 0.2)}
        fill={WHITE}
        alignItems="center"
        justifyContent="center"
        {...SHADOW}
      >
        <Img src={image} width={iw ?? undefined} height={ih ?? undefined} />
      </Rect>
    ) : (
      <Img src={image} width={iw ?? undefined} height={ih ?? height} {...SHADOW} />
    );
  return (
    <Rect layout direction="column" alignItems="center" gap={8} opacity={0} {...props}>
      {label ? <Rect height={reserve} /> : null}
      {core}
      {label ? (
        <Rect height={reserve} alignItems="center" justifyContent="center">
          {text()}
        </Rect>
      ) : null}
    </Rect>
  ) as Rect;
}
