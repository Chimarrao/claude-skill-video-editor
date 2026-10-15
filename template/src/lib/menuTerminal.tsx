import {Circle, Node, Rect, Txt} from '@motion-canvas/2d';
import {all, easeInOutCubic, easeOutCubic, linear, sequence} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SOMBRA} from './estilo';
import {num} from './cartoes';
import type {ItemMenu, MenuExplorer} from './menuExplorer';

export interface ItemTerminal extends ItemMenu {
  detalhe?: string;
}

const LINHA = 60;
const CAB = 150; // barra de título + linha do comando

/**
 * Menu em estilo TERMINAL (variação V07 "Terminal ls"): janela escura com `$ ls -l ~/<tema>`; as linhas (`drwxr-xr-x NN nome detalhe`) entram
 * em sequência e a barra de seleção verde desliza do item anterior para o novo. Mesma API do menuExplorer (entrar(de, para) / sair()).
 * Itens já vistos ficam claros; o atual ganha a cor do item. Sem extensões (são diretórios, não arquivos).
 */
export function menuTerminal(itens: ItemTerminal[], largura = 820, titulo = 'itens'): MenuExplorer {
  const alt = CAB + itens.length * LINHA + 40;
  const jan = (
    <Rect
      width={largura}
      height={alt}
      radius={20}
      fill="#0f1210"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={3}
      clip
      opacity={0}
      {...SOMBRA}
    />
  ) as Rect;
  jan.add(<Rect width={largura} height={54} y={-alt / 2 + 27} fill="#1d201c" />);
  [MK.rosa, MK.amarelo, MK.verde].forEach((c, i) =>
    jan.add(<Circle size={18} fill={c} position={[-largura / 2 + 34 + i * 30, -alt / 2 + 27]} />),
  );
  jan.add(
    <Txt
      text={`canal@review: ~/${titulo.toLowerCase()}`}
      fontFamily={MONO}
      fontSize={24}
      fill={MK.cinza}
      y={-alt / 2 + 27}
    />,
  );
  const cmd = (
    <Txt
      text=""
      fontFamily={MONO}
      fontWeight={600}
      fontSize={32}
      fill={MK.verde}
      position={[-largura / 2 + 36, -alt / 2 + 100]}
      offset={[-1, 0]}
    />
  ) as Txt;
  jan.add(cmd);
  const yL = (i: number) => -alt / 2 + CAB + LINHA * i + LINHA / 2 + 6;
  const barra = (
    <Rect
      width={largura - 36}
      height={LINHA - 8}
      radius={8}
      fill="rgba(166,226,46,0.16)"
      stroke={MK.verde}
      lineWidth={2}
      y={yL(0)}
      opacity={0}
    />
  ) as Rect;
  jan.add(barra);
  const grupos: Node[] = [];
  const nomes: Txt[] = [];
  itens.forEach((it, i) => {
    const g = (<Node opacity={0} />) as Node;
    const y = yL(i);
    const x0 = -largura / 2 + 36;
    g.add(
      <Txt
        text="drwxr-xr-x"
        fontFamily={MONO}
        fontSize={26}
        fill={MK.comentario}
        position={[x0, y]}
        offset={[-1, 0]}
      />,
    );
    g.add(
      <Txt
        text={num(i + 1, itens.length)}
        fontFamily={MONO}
        fontSize={28}
        fill={MK.cinza}
        position={[x0 + 190, y]}
        offset={[-1, 0]}
      />,
    );
    const n = (
      <Txt
        text={it.rotulo
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-|-$/g, '')}
        fontFamily={MONO}
        fontWeight={700}
        fontSize={28}
        fill={MK.comentario}
        position={[x0 + 230, y]}
        offset={[-1, 0]}
      />
    ) as Txt;
    g.add(n);
    if (it.detalhe)
      g.add(
        <Txt
          text={it.detalhe}
          fontFamily={MONO}
          fontSize={24}
          fill={MK.cinza}
          position={[largura / 2 - 36, y]}
          offset={[1, 0]}
        />,
      );
    jan.add(g);
    grupos.push(g);
    nomes.push(n);
  });
  return {
    no: jan as any,
    *entrar(de: number, para: number) {
      nomes.forEach((t, i) => t.fill(i <= de ? MK.texto : MK.comentario));
      barra.y(yL(Math.max(de, 0)));
      jan.scale(0.95);
      yield* all(jan.opacity(1, 0.25), jan.scale(1, 0.35, easeOutCubic));
      yield* cmd.text(`$ ls -l ~/${titulo.toLowerCase()}`, 0.45, linear);
      yield* all(sequence(0.07, ...grupos.map(g => g.opacity(1, 0.15))), barra.opacity(1, 0.3));
      yield* all(barra.y(yL(para), 0.5, easeInOutCubic), nomes[para].fill(itens[para].cor, 0.35));
    },
    *sair() {
      yield* all(jan.opacity(0, 0.3), jan.scale(0.96, 0.3));
    },
  };
}
