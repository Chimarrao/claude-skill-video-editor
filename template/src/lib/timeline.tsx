import {Circle, Img, Layout, Line, Rect, Txt} from '@motion-canvas/2d';
import {all, createRef, easeOutBack, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {WHITE, FONT, SHADOW} from './style';

export interface ItemTime {
  year: number;
  name: string;
  logo: string | null;
  color: string;
  acronym?: string;
}
export interface LineTime {
  no: Rect;
  show(i: number): ThreadGenerator;
  exit(): ThreadGenerator;
}

/** Linha do tempo horizontal (eixo com décadas); itens nascem sobre o eixo e sobem/descem em 3 níveis sem se sobrepor. */
export function timeline(items: ItemTime[], width = 1700): LineTime {
  // Ordem cronológica, espaçamento uniforme (estilo mapa de metrô) e lados alternados: nada se sobrepõe.
  const order = items.map((it, i) => ({it, i})).sort((a, b) => a.it.year - b.it.year || a.i - b.i);
  const N = order.length;
  const root = (<Rect opacity={1} />) as Rect;
  root.add(
    <Line
      points={[
        [-width / 2 - 20, 0],
        [width / 2 + 40, 0],
      ]}
      stroke="rgba(248,248,242,0.85)"
      lineWidth={6}
      lineCap="round"
      endArrow
      arrowSize={20}
    />,
  );
  const nodes: Rect[] = new Array(N);
  order.forEach(({it, i}, k) => {
    const x = -width / 2 + (k + 0.5) * (width / N);
    const top = k % 2 === 0;
    const y = top ? -190 : 190;
    const group = (<Rect opacity={0} />) as Rect;
    group.add(
      <Line
        points={[
          [x, 0],
          [x, top ? y + 78 : y - 78],
        ]}
        stroke={it.color}
        lineWidth={5}
      />,
    );
    group.add(<Circle size={26} fill={it.color} stroke={WHITE} lineWidth={4} x={x} y={0} />);
    group.add(
      <Rect layout direction="column" alignItems="center" gap={6} x={x} y={y}>
        {it.logo ? (
          <Rect padding={12} radius={16} fill="#ffffff" {...SHADOW}>
            <Img src={it.logo} height={96} />
          </Rect>
        ) : (
          <Rect padding={[10, 18]} radius={16} fill={MK.background} stroke={it.color} lineWidth={4} {...SHADOW}>
            <Txt
              text={it.acronym ?? it.name.slice(0, 3).toUpperCase()}
              fontFamily={MONO}
              fontWeight={800}
              fontSize={it.acronym && it.acronym.length > 3 ? 40 : 64}
              fill={it.color}
            />
          </Rect>
        )}
        <Txt
          text={it.name}
          fontFamily={FONT}
          fontWeight={800}
          fontSize={34}
          fill={WHITE}
          stroke="#0b0b10"
          lineWidth={7}
          strokeFirst
          lineJoin="round"
        />
        <Txt
          text={String(it.year)}
          fontFamily={MONO}
          fontWeight={700}
          fontSize={30}
          fill={MK.yellow}
          stroke="#0b0b10"
          lineWidth={6}
          strokeFirst
          lineJoin="round"
        />
      </Rect>,
    );
    nodes[i] = group;
    root.add(group);
  });
  return {
    no: root,
    *show(i: number) {
      yield* nodes[i].opacity(1, 0.4);
    },
    *exit() {
      yield* all(root.opacity(0, 0.3));
    },
  };
}
