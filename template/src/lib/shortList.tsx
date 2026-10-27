import {Circle, Img, Rect, Txt} from '@motion-canvas/2d';
import {all, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {WHITE, FONT, ACCENTS} from './style';
import {num} from './cards';

export interface ShortListItem {
  icon: string | null;
  label: string;
  num: number;
}
export interface ShortListNode {
  no: Rect;
  /** Entra o cartão `k` (o anterior perde o destaque). */
  show(k: number): ThreadGenerator;
  exit(): ThreadGenerator;
  /** Pausa para B-roll: a lista inteira some (fade) e volta com os cartões já vistos. */
  hide(): ThreadGenerator;
  reappear(): ThreadGenerator;
}

/**
 * Lista curta dentro do webdoc: título pequeno + cartões numerados (número, ícone em disco, rótulo curto) que entram um a um.
 * Tema escuro sério (painel rgba(39,40,34,.95) como os demais cartões); até 5 itens = 1 coluna, 6+ = 2 colunas.
 * Cabe sempre fora da zona do avatar do canal (canto inferior direito).
 */
export function shortList(title: string, items: ShortListItem[], color: string): ShortListNode {
  const two = items.length > 5;
  const WIDTH = two ? 600 : 780;
  const TALL = 96;
  const lines = two ? Math.ceil(items.length / 2) : items.length;
  const root = (<Rect layout direction="column" gap={26} alignItems="center" />) as Rect;
  const head = (
    <Rect layout direction="column" gap={10} alignItems="center">
      <Txt text={title} fontFamily={FONT} fontWeight={800} fontSize={46} fill={WHITE} />
      <Rect width={200} height={8} radius={4} fill={color} />
    </Rect>
  ) as Rect;
  head.opacity(0);
  root.add(head);
  const grid = (<Rect layout direction="row" gap={30} alignItems="start" />) as Rect;
  const columns: Rect[] = [];
  for (let c = 0; c < (two ? 2 : 1); c++) {
    const col = (<Rect layout direction="column" gap={16} />) as Rect;
    columns.push(col);
    grid.add(col);
  }
  root.add(grid);
  const cards: Rect[] = [];
  items.forEach((it, i) => {
    const col = columns[two ? (i < lines ? 0 : 1) : 0];
    const accent = ACCENTS[i % ACCENTS.length];
    const card = (
      <Rect
        layout
        width={WIDTH}
        height={TALL}
        gap={22}
        padding={[0, 28]}
        alignItems="center"
        radius={22}
        fill="rgba(16,18,26,0.96)"
        stroke={accent}
        lineWidth={2}
        opacity={0}
        shadowColor={accent}
        shadowBlur={14}
        shadowOffset={[0, 6]}
      >
        <Circle size={54} fill={accent} alignItems="center" justifyContent="center">
          <Txt text={num(it.num, items.length)} fontFamily={MONO} fontWeight={800} fontSize={30} fill="#0b0b10" />
        </Circle>
        {it.icon ? (
          <Rect
            size={62}
            radius={31}
            fill={accent}
            alignItems="center"
            justifyContent="center"
          >
            <Img src={it.icon} size={34} />
          </Rect>
        ) : null}
        <Txt
          text={it.label}
          width={WIDTH - 230}
          textWrap
          fontFamily={FONT}
          fontWeight={600}
          fontSize={38}
          fill={WHITE}
        />
      </Rect>
    ) as Rect;
    cards.push(card);
    col.add(card);
  });
  return {
    no: root,
    *show(k: number) {
      if (k === 0) yield head.opacity(1, 0.4);
      cards.forEach((c, i) => {
        if (i < k) c.lineWidth(2);
      });
      const c = cards[k];
      c.lineWidth(6);
      c.x(40);
      yield* all(c.opacity(1, 0.35), c.x(0, 0.45, easeOutCubic));
    },
    *exit() {
      yield* all(root.opacity(0, 0.35));
    },
    *hide() {
      yield* root.opacity(0, 0.3);
    },
    *reappear() {
      yield* root.opacity(1, 0.4);
    },
  };
}
