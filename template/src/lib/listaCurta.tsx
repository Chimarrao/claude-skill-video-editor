import {Circle, Img, Rect, Txt} from '@motion-canvas/2d';
import {all, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {BRANCO, FONTE, SOMBRA} from './estilo';
import {num} from './cartoes';

export interface ItemListaCurta {
  icone: string | null;
  rotulo: string;
  num: number;
}
export interface ListaCurtaNo {
  no: Rect;
  /** Entra o cartão `k` (o anterior perde o destaque). */
  mostrar(k: number): ThreadGenerator;
  sair(): ThreadGenerator;
  /** Pausa para B-roll: a lista inteira some (fade) e volta com os cartões já vistos. */
  esconder(): ThreadGenerator;
  reaparecer(): ThreadGenerator;
}

/**
 * Lista curta dentro do webdoc: título pequeno + cartões numerados (número, ícone em disco, rótulo curto) que entram um a um.
 * Tema escuro sério (painel rgba(39,40,34,.95) como os demais cartões); até 5 itens = 1 coluna, 6+ = 2 colunas.
 * Cabe sempre fora da zona do avatar do canal (canto inferior direito).
 */
export function listaCurta(titulo: string, itens: ItemListaCurta[], cor: string): ListaCurtaNo {
  const duas = itens.length > 5;
  const LARG = duas ? 600 : 780;
  const ALT = 96;
  const linhas = duas ? Math.ceil(itens.length / 2) : itens.length;
  const raiz = (<Rect layout direction="column" gap={26} alignItems="center" />) as Rect;
  const cab = (
    <Rect layout direction="column" gap={10} alignItems="center">
      <Txt text={titulo} fontFamily={FONTE} fontWeight={800} fontSize={46} fill={BRANCO} />
      <Rect width={200} height={8} radius={4} fill={cor} />
    </Rect>
  ) as Rect;
  cab.opacity(0);
  raiz.add(cab);
  const grade = (<Rect layout direction="row" gap={30} alignItems="start" />) as Rect;
  const colunas: Rect[] = [];
  for (let c = 0; c < (duas ? 2 : 1); c++) {
    const col = (<Rect layout direction="column" gap={16} />) as Rect;
    colunas.push(col);
    grade.add(col);
  }
  raiz.add(grade);
  const cartoes: Rect[] = [];
  itens.forEach((it, i) => {
    const col = colunas[duas ? (i < linhas ? 0 : 1) : 0];
    const cartao = (
      <Rect
        layout
        width={LARG}
        height={ALT}
        gap={22}
        padding={[0, 28]}
        alignItems="center"
        radius={22}
        fill="rgba(39,40,34,0.95)"
        stroke="rgba(255,255,255,0.14)"
        lineWidth={2}
        opacity={0}
        {...SOMBRA}
      >
        <Circle size={54} fill={cor} alignItems="center" justifyContent="center">
          <Txt text={num(it.num, itens.length)} fontFamily={MONO} fontWeight={800} fontSize={30} fill="#0b0b10" />
        </Circle>
        {it.icone ? (
          <Rect
            size={62}
            radius={31}
            fill={MK.fundo2}
            stroke="rgba(255,255,255,0.4)"
            lineWidth={3}
            alignItems="center"
            justifyContent="center"
          >
            <Img src={it.icone} size={34} />
          </Rect>
        ) : null}
        <Txt
          text={it.rotulo}
          width={LARG - 230}
          textWrap
          fontFamily={FONTE}
          fontWeight={600}
          fontSize={38}
          fill={BRANCO}
        />
      </Rect>
    ) as Rect;
    cartoes.push(cartao);
    col.add(cartao);
  });
  return {
    no: raiz,
    *mostrar(k: number) {
      if (k === 0) yield cab.opacity(1, 0.4);
      cartoes.forEach((c, i) => {
        if (i < k) c.stroke('rgba(255,255,255,0.14)');
      });
      const c = cartoes[k];
      c.stroke(cor);
      c.x(40);
      yield* all(c.opacity(1, 0.35), c.x(0, 0.45, easeOutCubic));
    },
    *sair() {
      yield* all(raiz.opacity(0, 0.35));
    },
    *esconder() {
      yield* raiz.opacity(0, 0.3);
    },
    *reaparecer() {
      yield* raiz.opacity(1, 0.4);
    },
  };
}
