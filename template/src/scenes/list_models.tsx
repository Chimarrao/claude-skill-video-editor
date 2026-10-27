import {Gradient, Img, Rect, Txt, makeScene2D} from '@motion-canvas/2d';
import {all, createRef, easeOutCubic, sequence, waitFor} from '@motion-canvas/core';
import {WHITE, FONT, ACCENTS} from '../lib/style';
import {MONO} from '../lib/monokai';
import icClock from '../images/ic-clock-bolt.svg';
import icHistory from '../images/ic-history.svg';
import icLaptop from '../images/ic-device-laptop.svg';

// MODELOS DE LISTA (prévia para escolher o definitivo): mesmo conteúdo, 6 jeitos de desenhar.
// Cada modelo mostra 3 itens entrando um a um. Nada de brilho/halo: só cor, forma e tipografia.
const ITEMS: [string, string][] = [
  ['Primeira impressão em segundos', icClock],
  ['Amigável ou intimidadora?', icHistory],
  ['Moderno ou antigo?', icLaptop],
];
const W = 1000;

function shade(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16);
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v * f)));
  return `rgb(${c((n >> 16) & 255)},${c((n >> 8) & 255)},${c(n & 255)})`;
}
function alpha(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}
const txt = (t: string, size: number, fill: string, weight = 700, extra: any = {}) => (
  <Txt text={t} fontFamily={FONT} fontWeight={weight} fontSize={size} fill={fill} {...extra} />
);

type Maker = (text: string, icon: string, c: string, i: number) => Rect;

// A — Barra lateral: painel escuro discreto, faixa colorida só na borda esquerda, ícone sobre tinta suave.
const A: Maker = (t, icon, c) => (
  <Rect layout width={W} height={124} radius={20} fill="#12141c" stroke="rgba(255,255,255,0.12)" lineWidth={2} alignItems="center" gap={28} paddingLeft={44} paddingRight={36} clip>
    <Rect layout={false} x={-W / 2 + 9} width={18} height={124} fill={c} />
    <Rect layout width={78} height={78} radius={39} fill={alpha(c, 0.22)} alignItems="center" justifyContent="center">
      <Img src={icon} size={46} />
    </Rect>
    {txt(t, 46, WHITE, 700)}
  </Rect>
) as Rect;

// B — Pílula sólida: a linha inteira é da cor; texto escuro; ícone em disco escuro.
const B: Maker = (t, icon, c) => (
  <Rect layout width={W} height={112} radius={56} fill={c} alignItems="center" gap={26} paddingLeft={18} paddingRight={40}>
    <Rect layout width={80} height={80} radius={40} fill="rgba(11,11,16,0.88)" alignItems="center" justifyContent="center">
      <Img src={icon} size={46} />
    </Rect>
    {txt(t, 48, '#0b0b10', 800)}
  </Rect>
) as Rect;

// C — Numerada: sem caixa; número grande colorido, divisor e texto; uma linha fina embaixo.
const C: Maker = (t, icon, c, i) => (
  <Rect layout direction="column" width={W} gap={18}>
    <Rect layout alignItems="center" gap={32}>
      {txt(`0${i + 1}`, 92, c, 900, {fontFamily: MONO})}
      <Rect width={6} height={78} radius={3} fill={c} />
      {txt(t, 52, WHITE, 700)}
    </Rect>
    <Rect width={W} height={3} fill="rgba(255,255,255,0.16)" />
  </Rect>
) as Rect;

// D — Vidro: degradê da cor para o painel escuro, aro fino da cor, ícone só em anel.
const D: Maker = (t, icon, c) => (
  <Rect
    layout
    width={W}
    height={120}
    radius={26}
    fill={new Gradient({type: 'linear', from: [-W / 2, 0], to: [W / 2, 0], stops: [{offset: 0, color: alpha(c, 0.55)}, {offset: 0.7, color: 'rgba(14,16,22,0.92)'}]})}
    stroke={alpha(c, 0.7)}
    lineWidth={2}
    alignItems="center"
    gap={28}
    paddingLeft={34}
  >
    <Rect layout width={74} height={74} radius={37} stroke={c} lineWidth={5} alignItems="center" justifyContent="center">
      <Img src={icon} size={42} />
    </Rect>
    {txt(t, 46, WHITE, 700)}
  </Rect>
) as Rect;

// E — Marca-texto: sem caixa; ícone solto e uma tarja de marca-texto atrás do texto.
const E: Maker = (t, icon, c) => {
  const label = createRef<Txt>();
  return (
    <Rect layout width={W} alignItems="center" gap={30} height={110}>
      <Img src={icon} size={64} />
      <Rect layout alignItems="center">
        <Rect layout={false} y={20} width={() => label().width() + 24} height={34} radius={6} fill={alpha(c, 0.7)} />
        <Txt ref={label} text={t} fontFamily={FONT} fontWeight={800} fontSize={56} fill={WHITE} />
      </Rect>
    </Rect>
  ) as Rect;
};

// F — Degradê sólido: cartão com degradê diagonal da cor, texto branco, ícone em disco translúcido.
const F: Maker = (t, icon, c) => (
  <Rect
    layout
    width={W}
    height={120}
    radius={30}
    fill={new Gradient({type: 'linear', from: [-W / 2, -60], to: [W / 2, 60], stops: [{offset: 0, color: c}, {offset: 1, color: shade(c, 0.5)}]})}
    alignItems="center"
    gap={28}
    paddingLeft={30}
  >
    <Rect layout width={76} height={76} radius={38} fill="rgba(0,0,0,0.3)" alignItems="center" justifyContent="center">
      <Img src={icon} size={44} />
    </Rect>
    {txt(t, 48, WHITE, 800, {shadowColor: 'rgba(0,0,0,0.35)', shadowBlur: 6, shadowOffset: [0, 2]})}
  </Rect>
) as Rect;

const MODELS: [string, string, Maker, number][] = [
  ['A', 'Barra lateral colorida', A, 22],
  ['B', 'Pílula sólida', B, 22],
  ['C', 'Numerada, sem caixa', C, 34],
  ['D', 'Vidro com degradê', D, 22],
  ['E', 'Marca-texto', E, 30],
  ['F', 'Degradê sólido', F, 22],
];

export default makeScene2D(function* (view) {
  // fundo parecido com o do vídeo (o editor mostra xadrez e o texto branco some)
  view.add(
    <Rect
      width={1920}
      height={1080}
      fill={new Gradient({type: 'linear', from: [0, -540], to: [0, 540], stops: [{offset: 0, color: '#03070a'}, {offset: 1, color: '#0b2a1b'}]})}
    />,
  );
  for (const [id, name, make, gap] of MODELS) {
    const box = (<Rect layout direction="column" gap={gap} alignItems="center" />) as Rect;
    const rows: Rect[] = ITEMS.map(([t, icon], i) => {
      const r = make(t, icon, ACCENTS[i % ACCENTS.length], i);
      r.opacity(0);
      box.add(r);
      return r;
    });
    const label = (
      <Txt text={`MODELO ${id} · ${name}`} x={-640} y={-470} fontFamily={FONT} fontWeight={800} fontSize={40} fill="#9fb0c0" />
    ) as Txt;
    view.add(box);
    view.add(label);
    yield* sequence(0.5, ...rows.map(r => all(r.opacity(1, 0.35), r.x(0, 0.45, easeOutCubic))));
    yield* waitFor(3.2);
    yield* all(...rows.map(r => r.opacity(0, 0.35)), label.opacity(0, 0.35));
    box.remove();
    label.remove();
    yield* waitFor(0.3);
  }
});
