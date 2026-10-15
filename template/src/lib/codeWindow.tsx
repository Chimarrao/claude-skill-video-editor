import {Circle, Img, Layout, Rect, Txt} from '@motion-canvas/2d';
import {all, createRef, easeOutCubic, sequence, ThreadGenerator} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {SHADOW} from './style';

export type Token = [string, string]; // [texto, cor]
export interface CodeWindow {
  no: Rect;
  reveal(): ThreadGenerator;
}

/**
 * Janela do VS Code com tema Monokai: barra de título, activity bar, aba do arquivo, editor com números de
 * linha e barra de status. As linhas entram em sequência (efeito de digitação por token).
 * `icones` = urls dos ícones cinza da activity bar (opcional).
 */
export function codeWindow(
  file: string,
  language: string,
  colorLanguage: string,
  lines: Token[][],
  width = 1040,
  icons: string[] = [],
): CodeWindow {
  const maxChars = Math.max(...lines.map(l => l.reduce((s, t) => s + t[0].length, 0)), 12);
  const available = width - 56 - 96 - 48;
  const fs = Math.max(20, Math.min(32, available / (maxChars * 0.605)));
  const lh = fs * 1.55;
  const heightEditor = lines.length * lh + 44;
  const heightTotal = 46 + 44 + heightEditor + 36;
  const rows: Layout[] = [];
  const toks: Txt[][] = [];
  const nums: Txt[] = [];

  const gutter = (<Layout layout direction="column" width={96} paddingRight={22} alignItems="end" />) as Layout;
  const code = (<Layout layout direction="column" />) as Layout;
  lines.forEach((line, i) => {
    const n = (
      <Txt text={String(i + 1)} fontFamily={MONO} fontSize={fs} height={lh} fill={MK.gray} opacity={0} />
    ) as Txt;
    nums.push(n);
    gutter.add(n);
    const row = (<Layout layout direction="row" height={lh} alignItems="center" opacity={0} x={18} />) as Layout;
    const tl: Txt[] = [];
    for (const [text, color] of line) {
      const t = (
        <Txt text={text} textWrap="pre" fontFamily={MONO} fontSize={fs} fontWeight={500} fill={color} opacity={0} />
      ) as Txt;
      tl.push(t);
      row.add(t);
    }
    if (!line.length) {
      const t = (<Txt text=" " textWrap="pre" fontFamily={MONO} fontSize={fs} opacity={0} />) as Txt;
      tl.push(t);
      row.add(t);
    }
    toks.push(tl);
    rows.push(row);
    code.add(row);
  });

  const no = createRef<Rect>();
  <Rect
    ref={no}
    layout
    direction="column"
    width={width}
    height={heightTotal}
    radius={18}
    fill={MK.background}
    stroke="rgba(255,255,255,0.14)"
    lineWidth={2}
    clip
    opacity={0}
    {...SHADOW}
  />;
  const window = no();
  window.add(
    <Rect height={46} width={width} fill={MK.background2} alignItems="center" paddingLeft={20} paddingRight={20} gap={10}>
      <Circle size={15} fill="#ff5f56" />
      <Circle size={15} fill="#ffbd2e" />
      <Circle size={15} fill="#27c93f" />
      <Rect grow={1} justifyContent="center">
        <Txt
          text={`${file} — Studio Code`}
          fontFamily="'Helvetica Neue', Arial, sans-serif"
          fontSize={20}
          fill={MK.gray}
        />
      </Rect>
      <Rect width={75} />
    </Rect>,
  );
  window.add(
    <Rect direction="row" width={width} height={44 + heightEditor}>
      <Rect width={56} fill={MK.background2} direction="column" alignItems="center" paddingTop={18} gap={26}>
        {icons.map(u => (
          <Img src={u} size={28} />
        ))}
      </Rect>
      <Rect direction="column" grow={1}>
        <Rect height={44} fill={MK.background2} alignItems="end">
          <Rect height={44} fill={MK.background} paddingLeft={24} paddingRight={26} alignItems="center" gap={10}>
            <Circle size={11} fill={colorLanguage} />
            <Txt text={file} fontFamily={MONO} fontSize={20} fill={MK.text} />
          </Rect>
        </Rect>
        <Rect direction="row" paddingTop={22} height={heightEditor}>
          {gutter}
          {code}
        </Rect>
      </Rect>
    </Rect>,
  );
  window.add(
    <Rect
      height={36}
      width={width}
      fill={MK.background2}
      alignItems="center"
      paddingLeft={20}
      paddingRight={20}
      justifyContent="space-between"
    >
      <Txt text="⎇ main" fontFamily={MONO} fontSize={18} fill={MK.gray} />
      <Txt text={`${language}   UTF-8   LF`} fontFamily={MONO} fontSize={18} fill={MK.gray} />
    </Rect>,
  );
  return {
    no: window,
    *reveal() {
      yield* window.opacity(1, 0.25);
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
