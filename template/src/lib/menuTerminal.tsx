import {Circle, Node, Rect, Txt} from '@motion-canvas/2d';
import {all, easeInOutCubic, easeOutCubic, linear, sequence} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SHADOW} from './style';
import {num} from './cards';
import type {ItemMenu, MenuExplorer} from './menuExplorer';

export interface ItemTerminal extends ItemMenu {
  detail?: string;
}

const LINE = 60;
const HEAD = 150; // barra de título + linha do comando

/**
 * Menu em estilo TERMINAL (variação V07 "Terminal ls"): janela escura com `$ ls -l ~/<tema>`; as linhas (`drwxr-xr-x NN nome detalhe`) entram
 * em sequência e a barra de seleção verde desliza do item anterior para o novo. Mesma API do menuExplorer (entrar(de, para) / sair()).
 * Itens já vistos ficam claros; o atual ganha a cor do item. Sem extensões (são diretórios, não arquivos).
 */
export function menuTerminal(items: ItemTerminal[], width = 820, title = 'items'): MenuExplorer {
  const tall = HEAD + items.length * LINE + 40;
  const win = (
    <Rect
      width={width}
      height={tall}
      radius={20}
      fill="#0f1210"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={3}
      clip
      opacity={0}
      {...SHADOW}
    />
  ) as Rect;
  win.add(<Rect width={width} height={54} y={-tall / 2 + 27} fill="#1d201c" />);
  [MK.pink, MK.yellow, MK.green].forEach((c, i) =>
    win.add(<Circle size={18} fill={c} position={[-width / 2 + 34 + i * 30, -tall / 2 + 27]} />),
  );
  win.add(
    <Txt
      text={`canal@review: ~/${title.toLowerCase()}`}
      fontFamily={MONO}
      fontSize={24}
      fill={MK.gray}
      y={-tall / 2 + 27}
    />,
  );
  const cmd = (
    <Txt
      text=""
      fontFamily={MONO}
      fontWeight={600}
      fontSize={32}
      fill={MK.green}
      position={[-width / 2 + 36, -tall / 2 + 100]}
      offset={[-1, 0]}
    />
  ) as Txt;
  win.add(cmd);
  const yL = (i: number) => -tall / 2 + HEAD + LINE * i + LINE / 2 + 6;
  const bar = (
    <Rect
      width={width - 36}
      height={LINE - 8}
      radius={8}
      fill="rgba(166,226,46,0.16)"
      stroke={MK.green}
      lineWidth={2}
      y={yL(0)}
      opacity={0}
    />
  ) as Rect;
  win.add(bar);
  const groups: Node[] = [];
  const names: Txt[] = [];
  // COLUNAS ALINHADAS (nome | detalhe): o detalhe começa sempre no mesmo x, à ESQUERDA, logo depois do maior nome.
  // Se não couber na janela, todas as fontes encolhem juntas (mesmo fator).
  const slug = (r: string) =>
    r
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  const largestName = Math.max(...items.map(i => slug(i.label).length));
  const largestDetail = Math.max(0, ...items.map(i => (i.detail ?? '').length));
  const FN = 28; // fonte do nome
  const FD = 24; // fonte do detalhe
  const widthRequired = 36 + 230 + largestName * FN * 0.62 + 36 + largestDetail * FD * 0.62 + 36;
  const k = Math.min(1, width / widthRequired);
  const colDetail = -width / 2 + 36 + 230 + largestName * FN * 0.62 * k + 36;
  items.forEach((it, i) => {
    const g = (<Node opacity={0} />) as Node;
    const y = yL(i);
    const x0 = -width / 2 + 36;
    g.add(
      <Txt
        text="drwxr-xr-x"
        fontFamily={MONO}
        fontSize={26}
        fill={MK.comment}
        position={[x0, y]}
        offset={[-1, 0]}
      />,
    );
    g.add(
      <Txt
        text={num(i + 1, items.length)}
        fontFamily={MONO}
        fontSize={28}
        fill={MK.gray}
        position={[x0 + 190, y]}
        offset={[-1, 0]}
      />,
    );
    const n = (
      <Txt
        text={slug(it.label)}
        fontFamily={MONO}
        fontWeight={700}
        fontSize={FN * k}
        fill={MK.comment}
        position={[x0 + 230, y]}
        offset={[-1, 0]}
      />
    ) as Txt;
    g.add(n);
    if (it.detail)
      g.add(
        <Txt
          text={it.detail}
          fontFamily={MONO}
          fontSize={FD * k}
          fill={MK.gray}
          position={[colDetail, y]}
          offset={[-1, 0]}
        />,
      );
    win.add(g);
    groups.push(g);
    names.push(n);
  });
  return {
    no: win as any,
    *enter(from: number, dst: number) {
      names.forEach((t, i) => t.fill(i <= from ? MK.text : MK.comment));
      bar.y(yL(Math.max(from, 0)));
      win.scale(0.95);
      yield* all(win.opacity(1, 0.25), win.scale(1, 0.35, easeOutCubic));
      yield* cmd.text(`$ ls -l ~/${title.toLowerCase()}`, 0.45, linear);
      yield* all(sequence(0.07, ...groups.map(g => g.opacity(1, 0.15))), bar.opacity(1, 0.3));
      yield* all(bar.y(yL(dst), 0.5, easeInOutCubic), names[dst].fill(items[dst].color, 0.35));
    },
    *exit() {
      yield* all(win.opacity(0, 0.3), win.scale(0.96, 0.3));
    },
  };
}
