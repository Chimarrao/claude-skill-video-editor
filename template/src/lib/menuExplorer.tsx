import {Circle, Layout, Rect, Txt} from '@motion-canvas/2d';
import {all, createRef, easeInOutCubic, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SHADOW} from './style';

export interface ItemMenu {
  label: string;
  file: string;
  color: string;
}
export interface MenuExplorer {
  no: Rect;
  /** Entra com o destaque no item `de` (ou nenhum) e desliza até o item `para`. */
  enter(from: number, dst: number): ThreadGenerator;
  exit(): ThreadGenerator;
}

const HEIGHT_LINE = 46;
const HEADER = 92;

/**
 * Menu de itens no formato do explorador de arquivos do VS Code (Monokai). Aparece a cada troca de item da
 * lista: a barra de destaque desliza do item anterior para o novo; itens já vistos ficam claros.
 */
export function menuExplorer(items: ItemMenu[], width = 700, title = 'ITEMS'): MenuExplorer {
  const height = HEADER + items.length * HEIGHT_LINE + 28;
  const bar = createRef<Rect>();
  const no = createRef<Rect>();
  const texts: Txt[] = [];
  const points: Circle[] = [];
  <Rect
    ref={no}
    width={width}
    height={height}
    radius={18}
    fill={MK.background}
    stroke="rgba(255,255,255,0.16)"
    lineWidth={2}
    clip
    opacity={0}
    {...SHADOW}
  >
    <Rect
      layout={false}
      width={width}
      height={HEADER - 14}
      y={-height / 2 + (HEADER - 14) / 2}
      fill={MK.background2}
    />
    <Txt
      layout={false}
      text="EXPLORER"
      fontFamily={MONO}
      fontSize={22}
      fontWeight={700}
      letterSpacing={4}
      fill={MK.gray}
      x={-width / 2 + 36}
      y={-height / 2 + 30}
      offset={[-1, 0]}
    />
    <Txt
      layout={false}
      text={`⌄ ${title}`}
      fontFamily={MONO}
      fontSize={24}
      fontWeight={700}
      fill={MK.text}
      x={-width / 2 + 36}
      y={-height / 2 + 66}
      offset={[-1, 0]}
    />
    <Rect
      ref={bar}
      layout={false}
      width={width - 24}
      height={HEIGHT_LINE - 6}
      radius={8}
      fill="rgba(166, 226, 46, 0.16)"
      stroke={MK.green}
      lineWidth={2}
      y={-height / 2 + HEADER + HEIGHT_LINE / 2}
      opacity={0}
    />
  </Rect>;
  const root = no();
  items.forEach((it, i) => {
    const y = -height / 2 + HEADER + HEIGHT_LINE * i + HEIGHT_LINE / 2;
    const c = createRef<Circle>();
    const t = createRef<Txt>();
    root.add(<Circle ref={c} layout={false} size={16} fill={it.color} x={-width / 2 + 52} y={y} opacity={0.35} />);
    root.add(
      <Txt
        ref={t}
        layout={false}
        text={`${items.length > 9 ? String(i + 1).padStart(2, '0') : String(i + 1)}  ${it.file}`}
        fontFamily={MONO}
        fontSize={29}
        fontWeight={500}
        fill={MK.comment}
        x={-width / 2 + 82}
        y={y}
        offset={[-1, 0]}
      />,
    );
    texts.push(t());
    points.push(c());
  });
  const yFrom = (i: number) => -height / 2 + HEADER + HEIGHT_LINE * i + HEIGHT_LINE / 2;
  return {
    no: root,
    *enter(from: number, dst: number) {
      // itens anteriores a `de` já vistos (claros)
      texts.forEach((t, i) => {
        t.fill(i <= from ? MK.text : MK.comment);
        points[i].opacity(i <= from ? 0.9 : 0.35);
      });
      bar().y(yFrom(Math.max(from, 0)));
      bar().opacity(from >= 0 ? 1 : 0);
      root.scale(0.94);
      yield* all(root.opacity(1, 0.3), root.scale(1, 0.4, easeOutCubic));
      yield* bar().opacity(1, 0.15);
      yield* all(
        bar().y(yFrom(dst), 0.55, easeInOutCubic),
        texts[dst].fill(MK.green, 0.4),
        points[dst].opacity(1, 0.4),
      );
    },
    *exit() {
      yield* all(root.opacity(0, 0.3), root.scale(0.96, 0.3));
    },
  };
}
