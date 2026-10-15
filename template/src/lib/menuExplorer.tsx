import {Circle, Layout, Rect, Txt} from '@motion-canvas/2d';
import {all, createRef, easeInOutCubic, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SOMBRA} from './estilo';

export interface ItemMenu {
  rotulo: string;
  arquivo: string;
  cor: string;
}
export interface MenuExplorer {
  no: Rect;
  /** Entra com o destaque no item `de` (ou nenhum) e desliza até o item `para`. */
  entrar(de: number, para: number): ThreadGenerator;
  sair(): ThreadGenerator;
}

const ALTURA_LINHA = 46;
const CABECALHO = 92;

/**
 * Menu de itens no formato do explorador de arquivos do VS Code (Monokai). Aparece a cada troca de item da
 * lista: a barra de destaque desliza do item anterior para o novo; itens já vistos ficam claros.
 */
export function menuExplorer(itens: ItemMenu[], largura = 700, titulo = 'ITENS'): MenuExplorer {
  const altura = CABECALHO + itens.length * ALTURA_LINHA + 28;
  const barra = createRef<Rect>();
  const no = createRef<Rect>();
  const textos: Txt[] = [];
  const pontos: Circle[] = [];
  <Rect
    ref={no}
    width={largura}
    height={altura}
    radius={18}
    fill={MK.fundo}
    stroke="rgba(255,255,255,0.16)"
    lineWidth={2}
    clip
    opacity={0}
    {...SOMBRA}
  >
    <Rect
      layout={false}
      width={largura}
      height={CABECALHO - 14}
      y={-altura / 2 + (CABECALHO - 14) / 2}
      fill={MK.fundo2}
    />
    <Txt
      layout={false}
      text="EXPLORADOR"
      fontFamily={MONO}
      fontSize={22}
      fontWeight={700}
      letterSpacing={4}
      fill={MK.cinza}
      x={-largura / 2 + 36}
      y={-altura / 2 + 30}
      offset={[-1, 0]}
    />
    <Txt
      layout={false}
      text={`⌄ ${titulo}`}
      fontFamily={MONO}
      fontSize={24}
      fontWeight={700}
      fill={MK.texto}
      x={-largura / 2 + 36}
      y={-altura / 2 + 66}
      offset={[-1, 0]}
    />
    <Rect
      ref={barra}
      layout={false}
      width={largura - 24}
      height={ALTURA_LINHA - 6}
      radius={8}
      fill="rgba(166, 226, 46, 0.16)"
      stroke={MK.verde}
      lineWidth={2}
      y={-altura / 2 + CABECALHO + ALTURA_LINHA / 2}
      opacity={0}
    />
  </Rect>;
  const raiz = no();
  itens.forEach((it, i) => {
    const y = -altura / 2 + CABECALHO + ALTURA_LINHA * i + ALTURA_LINHA / 2;
    const c = createRef<Circle>();
    const t = createRef<Txt>();
    raiz.add(<Circle ref={c} layout={false} size={16} fill={it.cor} x={-largura / 2 + 52} y={y} opacity={0.35} />);
    raiz.add(
      <Txt
        ref={t}
        layout={false}
        text={`${itens.length > 9 ? String(i + 1).padStart(2, '0') : String(i + 1)}  ${it.arquivo}`}
        fontFamily={MONO}
        fontSize={29}
        fontWeight={500}
        fill={MK.comentario}
        x={-largura / 2 + 82}
        y={y}
        offset={[-1, 0]}
      />,
    );
    textos.push(t());
    pontos.push(c());
  });
  const yDe = (i: number) => -altura / 2 + CABECALHO + ALTURA_LINHA * i + ALTURA_LINHA / 2;
  return {
    no: raiz,
    *entrar(de: number, para: number) {
      // itens anteriores a `de` já vistos (claros)
      textos.forEach((t, i) => {
        t.fill(i <= de ? MK.texto : MK.comentario);
        pontos[i].opacity(i <= de ? 0.9 : 0.35);
      });
      barra().y(yDe(Math.max(de, 0)));
      barra().opacity(de >= 0 ? 1 : 0);
      raiz.scale(0.94);
      yield* all(raiz.opacity(1, 0.3), raiz.scale(1, 0.4, easeOutCubic));
      yield* barra().opacity(1, 0.15);
      yield* all(
        barra().y(yDe(para), 0.55, easeInOutCubic),
        textos[para].fill(MK.verde, 0.4),
        pontos[para].opacity(1, 0.4),
      );
    },
    *sair() {
      yield* all(raiz.opacity(0, 0.3), raiz.scale(0.96, 0.3));
    },
  };
}
