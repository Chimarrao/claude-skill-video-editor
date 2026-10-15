import {Circle, Img, Layout, Rect, Txt} from '@motion-canvas/2d';
import {all, createRef, easeOutCubic, sequence, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SOMBRA} from './estilo';

export type Token = [string, string]; // [texto, cor]
export interface JanelaCodigo {
  no: Rect;
  revelar(): ThreadGenerator;
}

/**
 * Janela do VS Code com tema Monokai: barra de título, activity bar, aba do arquivo, editor com números de
 * linha e barra de status. As linhas entram em sequência (efeito de digitação por token).
 * `icones` = urls dos ícones cinza da activity bar (opcional).
 */
export function janelaCodigo(
  arquivo: string,
  linguagem: string,
  corLinguagem: string,
  linhas: Token[][],
  largura = 1040,
  icones: string[] = [],
): JanelaCodigo {
  const maxChars = Math.max(...linhas.map(l => l.reduce((s, t) => s + t[0].length, 0)), 12);
  const disponivel = largura - 56 - 96 - 48;
  const fs = Math.max(20, Math.min(32, disponivel / (maxChars * 0.605)));
  const lh = fs * 1.55;
  const alturaEditor = linhas.length * lh + 44;
  const alturaTotal = 46 + 44 + alturaEditor + 36;
  const rows: Layout[] = [];
  const toks: Txt[][] = [];
  const nums: Txt[] = [];

  const gutter = (<Layout layout direction="column" width={96} paddingRight={22} alignItems="end" />) as Layout;
  const codigo = (<Layout layout direction="column" />) as Layout;
  linhas.forEach((linha, i) => {
    const n = (
      <Txt text={String(i + 1)} fontFamily={MONO} fontSize={fs} height={lh} fill={MK.cinza} opacity={0} />
    ) as Txt;
    nums.push(n);
    gutter.add(n);
    const row = (<Layout layout direction="row" height={lh} alignItems="center" opacity={0} x={18} />) as Layout;
    const tl: Txt[] = [];
    for (const [texto, cor] of linha) {
      const t = (
        <Txt text={texto} textWrap="pre" fontFamily={MONO} fontSize={fs} fontWeight={500} fill={cor} opacity={0} />
      ) as Txt;
      tl.push(t);
      row.add(t);
    }
    if (!linha.length) {
      const t = (<Txt text=" " textWrap="pre" fontFamily={MONO} fontSize={fs} opacity={0} />) as Txt;
      tl.push(t);
      row.add(t);
    }
    toks.push(tl);
    rows.push(row);
    codigo.add(row);
  });

  const no = createRef<Rect>();
  <Rect
    ref={no}
    layout
    direction="column"
    width={largura}
    height={alturaTotal}
    radius={18}
    fill={MK.fundo}
    stroke="rgba(255,255,255,0.14)"
    lineWidth={2}
    clip
    opacity={0}
    {...SOMBRA}
  />;
  const janela = no();
  janela.add(
    <Rect height={46} width={largura} fill={MK.fundo2} alignItems="center" paddingLeft={20} paddingRight={20} gap={10}>
      <Circle size={15} fill="#ff5f56" />
      <Circle size={15} fill="#ffbd2e" />
      <Circle size={15} fill="#27c93f" />
      <Rect grow={1} justifyContent="center">
        <Txt
          text={`${arquivo} — Studio Code`}
          fontFamily="'Helvetica Neue', Arial, sans-serif"
          fontSize={20}
          fill={MK.cinza}
        />
      </Rect>
      <Rect width={75} />
    </Rect>,
  );
  janela.add(
    <Rect direction="row" width={largura} height={44 + alturaEditor}>
      <Rect width={56} fill={MK.fundo2} direction="column" alignItems="center" paddingTop={18} gap={26}>
        {icones.map(u => (
          <Img src={u} size={28} />
        ))}
      </Rect>
      <Rect direction="column" grow={1}>
        <Rect height={44} fill={MK.fundo2} alignItems="end">
          <Rect height={44} fill={MK.fundo} paddingLeft={24} paddingRight={26} alignItems="center" gap={10}>
            <Circle size={11} fill={corLinguagem} />
            <Txt text={arquivo} fontFamily={MONO} fontSize={20} fill={MK.texto} />
          </Rect>
        </Rect>
        <Rect direction="row" paddingTop={22} height={alturaEditor}>
          {gutter}
          {codigo}
        </Rect>
      </Rect>
    </Rect>,
  );
  janela.add(
    <Rect
      height={36}
      width={largura}
      fill={MK.fundo2}
      alignItems="center"
      paddingLeft={20}
      paddingRight={20}
      justifyContent="space-between"
    >
      <Txt text="⎇ main" fontFamily={MONO} fontSize={18} fill={MK.cinza} />
      <Txt text={`${linguagem}   UTF-8   LF`} fontFamily={MONO} fontSize={18} fill={MK.cinza} />
    </Rect>,
  );
  return {
    no: janela,
    *revelar() {
      yield* janela.opacity(1, 0.25);
      yield* sequence(
        0.16,
        ...rows.map((r, i) =>
          all(
            nums[i].opacity(1, 0.15),
            r.opacity(1, 0.1),
            r.x(0, 0.3, easeOutCubic),
            sequence(0.035, ...toks[i].map(t => t.opacity(1, 0.05))),
          ),
        ),
      );
    },
  };
}
