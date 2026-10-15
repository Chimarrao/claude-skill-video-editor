import {Layout, Rect, Txt, View2D} from '@motion-canvas/2d';
import {all, cancel, createRef, easeOutCubic, loop, ThreadGenerator, waitFor} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SOMBRA} from './estilo';

/**
 * TEXTO DE IMPACTO DO CANAL — versão "terminal Monokai" (canal de programação, tom sério).
 * Referência: o efeito *typewriter* é o que mais lembra editor de código; fontes legíveis em movimento,
 * contraste forte e poucas palavras por vez (kinetic typography).
 * - Painel Monokai (#272822) com barra de destaque rosa à esquerda e etiqueta de comentário `// tag`.
 * - Linhas em MAIÚSCULAS mono, prefixo `>` verde, digitadas palavra por palavra (typewriter) com cursor ▌.
 * - Palavras-chave marcadas com asteriscos ganham cor do tema: `*rosa*`, `*v:verde*`, `*a:azul*`, `*l:laranja*`,
 *   `*y:amarelo*`, `*r:roxo*` (aceita várias palavras: `*v:DUAS PALAVRAS*`).
 * - Saída: o painel desliza 60px e some (0.35s).
 */
export interface ImpactoCtl {
  no: Layout;
  entrar(): ThreadGenerator;
  sair(): ThreadGenerator;
}

const COR_MARCA: Record<string, string> = {
  '': MK.rosa,
  p: MK.rosa,
  v: MK.verde,
  a: MK.azul,
  l: MK.laranja,
  y: MK.amarelo,
  r: MK.roxo,
};

export function impacto(view: View2D, linhas: string[], tam = 84, tag = 'atenção'): ImpactoCtl {
  const painel = createRef<Rect>();
  const cursor = createRef<Txt>();
  let piscar: ThreadGenerator | null = null;
  const palavras: {t: Txt; texto: string}[] = [];
  const raiz = (<Layout />) as Layout;
  let ultimaFila: Layout | null = null;
  const maxChars = Math.max(...linhas.map(l => l.replace(/\*([a-z]:)?/g, '').length)) + 2;
  const largura = Math.min(1700, maxChars * tam * 0.61 + 190);
  const coluna = (<Layout layout direction="column" alignItems="start" gap={tam * 0.22} />) as Layout;
  for (const linha of linhas) {
    const fila = (<Layout layout direction="row" alignItems="center" gap={tam * 0.62} />) as Layout;
    fila.add(<Txt text=">" fontFamily={MONO} fontWeight={800} fontSize={tam} fill={MK.verde} />);
    let cor: string | null = null;
    for (let bruto of linha.split(' ')) {
      let fecha = false;
      const m = bruto.match(/^\*([a-z]):?(.*)$/);
      if (bruto.startsWith('*')) {
        const mm = bruto.match(/^\*(?:([a-z]):)?(.*)$/)!;
        cor = COR_MARCA[mm[1] ?? ''];
        bruto = mm[2];
      }
      if (bruto.endsWith('*')) {
        fecha = true;
        bruto = bruto.slice(0, -1);
      }
      void m;
      const t = createRef<Txt>();
      fila.add(<Txt ref={t} text="" fontFamily={MONO} fontWeight={800} fontSize={tam} fill={cor ?? MK.texto} />);
      palavras.push({t: t(), texto: bruto});
      if (fecha) cor = null;
    }
    coluna.add(fila);
    ultimaFila = fila;
  }
  ultimaFila!.add(<Txt ref={cursor} text="▌" fontFamily={MONO} fontSize={tam * 0.9} fill={MK.verde} opacity={0} />);
  raiz.add(
    <Rect
      ref={painel}
      layout
      direction="column"
      gap={tam * 0.3}
      width={largura}
      padding={[tam * 0.55, tam * 0.7, tam * 0.55, tam * 0.9]}
      radius={22}
      fill="rgba(39, 40, 34, 0.96)"
      stroke="rgba(255,255,255,0.14)"
      lineWidth={2}
      opacity={0}
      {...SOMBRA}
    >
      <Rect
        layout={false}
        width={14}
        height={() => painel().height() - 44}
        x={() => -painel().width() / 2 + 34}
        radius={7}
        fill={MK.rosa}
      />
      {tag ? (
        <Txt
          text={`// ${tag}`}
          fontFamily={MONO}
          fontWeight={600}
          fontSize={Math.max(26, tam * 0.36)}
          fill={MK.comentario}
        />
      ) : null}
      {coluna}
    </Rect>,
  );
  view.add(raiz);
  return {
    no: raiz,
    *entrar() {
      painel().x(-40);
      yield* all(painel().opacity(1, 0.25), painel().x(0, 0.4, easeOutCubic));
      cursor().opacity(1);
      for (const {t, texto} of palavras) {
        yield* t.text(texto, Math.max(0.07, texto.length * 0.028));
        yield* waitFor(0.04);
      }
      piscar = (yield loop(Infinity, function* () {
        yield* cursor().opacity(0.15, 0.45);
        yield* cursor().opacity(1, 0.45);
      })) as unknown as ThreadGenerator;
    },
    *sair() {
      if (piscar) cancel(piscar);
      yield* all(painel().opacity(0, 0.35), painel().x(60, 0.35));
    },
  };
}
