import {Layout, Rect, Txt, View2D} from '@motion-canvas/2d';
import {all, createRef, easeOutCubic, sequence, ThreadGenerator} from '@motion-canvas/core';
import {BRANCO, FONTE, SOMBRA_TEXTO} from './estilo';

/**
 * PADRÃO DE TEXTO DE IMPACTO DO CANAL (sério, estilo reportagem; ≤5% do vídeo, nunca no começo):
 * - Faixa escura translúcida de ponta a ponta com filetes vermelhos finos em cima e embaixo.
 * - Texto em MAIÚSCULAS, peso 800, branco, sem contorno de desenho animado, espaçamento de letras.
 * - Cada linha sobe 40px e aparece (mask/fade 0.5s), linhas em sequência (0.18s). Sem overshoot, sem giro.
 * - Palavra-chave (*asteriscos*): vermelho suave + filete vermelho que se desenha sob a palavra.
 * - Saída: tudo some em 0.35s (fade).
 */
export interface ImpactoReportagemCtl {
  no: Layout;
  entrar(): ThreadGenerator;
  sair(): ThreadGenerator;
}

const VERMELHO = '#ff5a5f';

export function impactoReportagem(view: View2D, linhas: string[], tam = 120): ImpactoReportagemCtl {
  const faixa = createRef<Rect>();
  const filetes: Rect[] = [];
  const linhasRef: Rect[] = [];
  const marcas: Rect[] = [];
  const raiz = (<Layout />) as Layout;
  const altura = linhas.length * tam * 1.25 + tam * 1.1;
  raiz.add(
    <Rect ref={faixa} width={1920} height={altura} fill="rgba(6, 8, 14, 0.66)" opacity={0} scale={[1, 0.2]}>
      <Rect layout={false} width={1920} height={4} y={-altura / 2} fill={VERMELHO} />
      <Rect layout={false} width={1920} height={4} y={altura / 2} fill={VERMELHO} />
    </Rect>,
  );
  const coluna = (<Layout layout direction="column" alignItems="center" gap={tam * 0.12} />) as Layout;
  for (const linha of linhas) {
    const fila = createRef<Rect>();
    const interno = (<Layout layout direction="row" gap={tam * 0.3} alignItems="center" />) as Layout;
    let marcando = false;
    for (const bruto of linha.split(' ')) {
      const abre = bruto.startsWith('*');
      const fecha = bruto.endsWith('*');
      if (abre) marcando = true;
      const w = bruto.replace(/\*/g, '');
      const marcada = marcando;
      if (fecha) marcando = false;
      const caixa = createRef<Rect>();
      const barra = createRef<Rect>();
      interno.add(
        <Rect ref={caixa} layout>
          <Txt
            text={w}
            fontFamily={FONTE}
            fontWeight={800}
            fontSize={tam}
            letterSpacing={tam * 0.03}
            fill={marcada ? VERMELHO : BRANCO}
            {...SOMBRA_TEXTO}
            shadowBlur={22}
          />
          {marcada ? (
            <Rect
              ref={barra}
              layout={false}
              width={() => caixa().width()}
              height={Math.max(5, tam * 0.06)}
              fill={VERMELHO}
              offset={[-1, 0]}
              x={() => -caixa().width() / 2}
              y={() => caixa().height() / 2 + tam * 0.03}
              scale={[0, 1]}
            />
          ) : null}
        </Rect>,
      );
      if (marcada) marcas.push(barra());
    }
    coluna.add(
      <Rect ref={fila} layout clip opacity={0} y={40}>
        {interno}
      </Rect>,
    );
    linhasRef.push(fila());
  }
  raiz.add(coluna);
  view.add(raiz);
  void filetes;
  return {
    no: raiz,
    *entrar() {
      yield* faixa().opacity(1, 0.2);
      yield all(faixa().scale([1, 1], 0.4, easeOutCubic));
      yield* sequence(0.18, ...linhasRef.map(l => all(l.opacity(1, 0.5, easeOutCubic), l.y(0, 0.5, easeOutCubic))));
      yield* all(...marcas.map(m => m.scale([1, 1], 0.45, easeOutCubic)));
    },
    *sair() {
      yield* all(raiz.opacity(0, 0.35));
    },
  };
}
