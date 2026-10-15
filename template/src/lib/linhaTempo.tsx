import {Circle, Img, Layout, Line, Rect, Txt} from '@motion-canvas/2d';
import {all, createRef, easeOutBack, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {BRANCO, FONTE, SOMBRA} from './estilo';

export interface ItemTempo {
  ano: number;
  nome: string;
  logo: string | null;
  cor: string;
  sigla?: string;
}
export interface LinhaTempo {
  no: Rect;
  mostrar(i: number): ThreadGenerator;
  sair(): ThreadGenerator;
}

/** Linha do tempo horizontal (eixo com décadas); itens nascem sobre o eixo e sobem/descem em 3 níveis sem se sobrepor. */
export function linhaTempo(itens: ItemTempo[], largura = 1700): LinhaTempo {
  // Ordem cronológica, espaçamento uniforme (estilo mapa de metrô) e lados alternados: nada se sobrepõe.
  const ordem = itens.map((it, i) => ({it, i})).sort((a, b) => a.it.ano - b.it.ano || a.i - b.i);
  const N = ordem.length;
  const raiz = (<Rect opacity={1} />) as Rect;
  raiz.add(
    <Line
      points={[
        [-largura / 2 - 20, 0],
        [largura / 2 + 40, 0],
      ]}
      stroke="rgba(248,248,242,0.85)"
      lineWidth={6}
      lineCap="round"
      endArrow
      arrowSize={20}
    />,
  );
  const nos: Rect[] = new Array(N);
  ordem.forEach(({it, i}, k) => {
    const x = -largura / 2 + (k + 0.5) * (largura / N);
    const cima = k % 2 === 0;
    const y = cima ? -190 : 190;
    const grupo = (<Rect opacity={0} />) as Rect;
    grupo.add(
      <Line
        points={[
          [x, 0],
          [x, cima ? y + 78 : y - 78],
        ]}
        stroke={it.cor}
        lineWidth={5}
      />,
    );
    grupo.add(<Circle size={26} fill={it.cor} stroke={BRANCO} lineWidth={4} x={x} y={0} />);
    grupo.add(
      <Rect layout direction="column" alignItems="center" gap={6} x={x} y={y}>
        {it.logo ? (
          <Rect padding={12} radius={16} fill="#ffffff" {...SOMBRA}>
            <Img src={it.logo} height={96} />
          </Rect>
        ) : (
          <Rect padding={[10, 18]} radius={16} fill={MK.fundo} stroke={it.cor} lineWidth={4} {...SOMBRA}>
            <Txt
              text={it.sigla ?? it.nome.slice(0, 3).toUpperCase()}
              fontFamily={MONO}
              fontWeight={800}
              fontSize={it.sigla && it.sigla.length > 3 ? 40 : 64}
              fill={it.cor}
            />
          </Rect>
        )}
        <Txt
          text={it.nome}
          fontFamily={FONTE}
          fontWeight={800}
          fontSize={34}
          fill={BRANCO}
          stroke="#0b0b10"
          lineWidth={7}
          strokeFirst
          lineJoin="round"
        />
        <Txt
          text={String(it.ano)}
          fontFamily={MONO}
          fontWeight={700}
          fontSize={30}
          fill={MK.amarelo}
          stroke="#0b0b10"
          lineWidth={6}
          strokeFirst
          lineJoin="round"
        />
      </Rect>,
    );
    nos[i] = grupo;
    raiz.add(grupo);
  });
  return {
    no: raiz,
    *mostrar(i: number) {
      yield* nos[i].opacity(1, 0.4);
    },
    *sair() {
      yield* all(raiz.opacity(0, 0.3));
    },
  };
}
