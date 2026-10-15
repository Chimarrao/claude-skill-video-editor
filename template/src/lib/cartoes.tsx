import {Node, Circle, Img, Layout, Rect, Txt} from '@motion-canvas/2d';
import {
  all,
  createRef,
  easeInOutSine,
  easeOutBack,
  easeOutCubic,
  sequence,
  ThreadGenerator,
  waitFor,
} from '@motion-canvas/core';
import {MK, MONO} from './monokai';
import {BRANCO, FONTE, SOMBRA, SOMBRA_TEXTO} from './estilo';

/** Numeração: zero à esquerda só quando o total passa de 9 (01/12, mas 1/4). */
export const num = (i: number, total: number) => (total > 9 ? String(i).padStart(2, '0') : String(i));

/** Pulso sutil de escala num nó (usado nas animações de ambiente). */
export function* pulso(no: Node, amp = 1.045) {
  yield* no.scale(amp, 0.4, easeInOutSine);
  yield* no.scale(1, 0.5, easeInOutSine);
}

/** Percorre os itens em ciclo (um pulso a cada ~3 s) — mantém a tela viva em retenções longas. */
export function* ciclo(nos: Node[], inicio = 3, passo = 3, amp = 1.05) {
  yield* waitFor(inicio);
  let i = 0;
  while (true) {
    yield* pulso(nos[i % nos.length], amp);
    yield* waitFor(Math.max(0.1, passo - 0.9));
    i++;
  }
}

export interface Peca {
  no: Rect;
  /** Animação de ambiente opcional (loop); o motor cancela quando a peça deixa de ser a ativa. */
  ambiente?(): ThreadGenerator;
  entrar(): ThreadGenerator;
  sair(): ThreadGenerator;
}

function pecaSimples(no: Rect, extra?: () => ThreadGenerator): Peca {
  no.opacity(0);
  return {
    no,
    *entrar() {
      no.scale(0.9);
      yield* all(no.opacity(1, 0.35), no.scale(1, 0.45, easeOutCubic), ...(extra ? [extra()] : []));
    },
    *sair() {
      yield* all(no.opacity(0, 0.28), no.scale(0.96, 0.28));
    },
  };
}

/** Logo grande à esquerda: cru (sem cartão) quando tem transparência; em cartão branco arredondado quando é opaco. Padrão de edição do usuário (~250 px, centro-esquerda). */
export function logoSolto(logo: string, altura = 250, placa = false, asp = 1): Peca {
  altura = Math.min(altura, 520 / Math.max(asp, 0.2));
  const no = (
    placa ? (
      <Rect
        layout
        padding={[26, 34]}
        radius={32}
        fill="#ffffff"
        alignItems="center"
        justifyContent="center"
        {...SOMBRA}
      >
        <Img src={logo} height={altura - 40} />
      </Rect>
    ) : (
      <Rect layout alignItems="center" justifyContent="center">
        <Img src={logo} height={altura} />
      </Rect>
    )
  ) as Rect;
  return pecaSimples(no);
}

/** Logo oficial em placa branca + nome e ano. Sem logo oficial: `sigla` em fonte mono sobre fundo Monokai. */
export function logoCard(
  logo: string | null,
  nome: string,
  ano: string,
  cor: string,
  sigla?: string,
  altura = 190,
  asp = 1,
): Peca {
  altura = Math.min(altura, 420 / Math.max(asp, 0.2));
  const placa = logo ? (
    <Rect padding={[34, 46]} radius={36} fill="#ffffff" alignItems="center" justifyContent="center" {...SOMBRA}>
      <Img src={logo} height={altura} />
    </Rect>
  ) : (
    <Rect padding={[34, 56]} radius={36} fill={MK.fundo} stroke={cor} lineWidth={5} alignItems="center" {...SOMBRA}>
      <Txt
        text={sigla ?? nome.slice(0, 3).toUpperCase()}
        fontFamily={MONO}
        fontWeight={800}
        fontSize={altura * 0.62}
        fill={cor}
      />
    </Rect>
  );
  const no = (
    <Rect layout direction="column" alignItems="center" gap={22}>
      {placa}
      <Rect
        layout
        radius={16}
        fill="rgba(39,40,34,0.94)"
        paddingLeft={26}
        paddingRight={26}
        paddingTop={12}
        paddingBottom={12}
        gap={20}
        alignItems="center"
        stroke="rgba(255,255,255,0.14)"
        lineWidth={2}
      >
        <Txt text={nome} fontFamily={FONTE} fontWeight={800} fontSize={50} fill={BRANCO} />
        <Txt text={ano} fontFamily={MONO} fontWeight={700} fontSize={34} fill={MK.amarelo} />
      </Rect>
    </Rect>
  ) as Rect;
  return pecaSimples(no);
}

export interface Pessoa {
  foto: string | null;
  nome: string;
  papel?: string;
}

/** Criadores: foto redonda com anel branco + nome (+ papel). `grupo` = foto única retangular com vários nomes. */
export function pessoasCard(pessoas: Pessoa[], iconeUsuario: string, grupo = false): Peca {
  if (grupo) {
    const no = (
      <Rect layout direction="column" alignItems="center" gap={16}>
        <Rect radius={24} clip stroke={BRANCO} lineWidth={8} {...SOMBRA}>
          <Img src={pessoas[0].foto!} width={560} />
        </Rect>
        {pessoas
          .filter(p => p.nome)
          .map(p => (
            <Txt
              text={p.nome}
              fontFamily={FONTE}
              fontWeight={800}
              fontSize={34}
              fill={BRANCO}
              stroke="#0b0b10"
              lineWidth={8}
              strokeFirst
              lineJoin="round"
            />
          ))}
      </Rect>
    ) as Rect;
    return pecaSimples(no);
  }
  const n = pessoas.length;
  const tam = n === 1 ? 230 : n === 2 ? 180 : 130;
  const fs = n === 1 ? 40 : n === 2 ? 32 : 24;
  const larg = tam + (n >= 3 ? 36 : 70);
  const no = (
    <Rect layout direction="row" gap={n === 1 ? 0 : n === 2 ? 24 : 12} alignItems="start">
      {pessoas.map(p => (
        <Rect direction="column" alignItems="center" gap={12} width={larg}>
          <Rect
            size={tam}
            radius={tam / 2}
            clip
            stroke={BRANCO}
            lineWidth={8}
            fill={MK.fundo}
            alignItems="center"
            justifyContent="center"
            {...SOMBRA}
          >
            {p.foto ? <Img src={p.foto} size={tam} /> : <Img src={iconeUsuario} size={tam * 0.55} />}
          </Rect>
          <Txt
            text={p.nome}
            width={larg}
            textWrap
            fontFamily={FONTE}
            fontWeight={800}
            fontSize={fs}
            textAlign="center"
            fill={BRANCO}
            stroke="#0b0b10"
            lineWidth={8}
            strokeFirst
            lineJoin="round"
          />
          {p.papel ? (
            <Txt
              text={p.papel}
              width={larg}
              textWrap
              fontFamily={FONTE}
              fontWeight={500}
              fontSize={fs * 0.72}
              textAlign="center"
              fill="#d9d9cc"
              stroke="#0b0b10"
              lineWidth={6}
              strokeFirst
              lineJoin="round"
            />
          ) : null}
        </Rect>
      ))}
    </Rect>
  ) as Rect;
  return pecaSimples(no);
}

/** Número grande (estatística) em painel Monokai; `pct` (0–100) acrescenta um donut que se completa. */
export function statCard(valor: string, rotulo: string, cor: string, pct?: number): Peca {
  const arco = createRef<Circle>();
  const no = (
    <Rect
      layout
      direction="row"
      gap={40}
      alignItems="center"
      padding={[36, 48]}
      radius={24}
      fill="rgba(39,40,34,0.95)"
      stroke="rgba(255,255,255,0.14)"
      lineWidth={2}
      {...SOMBRA}
    >
      {pct != null ? (
        <Rect size={230} alignItems="center" justifyContent="center">
          <Circle layout={false} size={210} stroke="rgba(255,255,255,0.12)" lineWidth={26} />
          <Circle
            ref={arco}
            layout={false}
            size={210}
            stroke={cor}
            lineWidth={26}
            lineCap="round"
            startAngle={-90}
            endAngle={-90}
          />
          <Txt layout={false} text={valor} fontFamily={MONO} fontWeight={800} fontSize={58} fill={cor} />
        </Rect>
      ) : null}
      <Rect direction="column" gap={10} alignItems="start" width={pct != null ? 520 : 680}>
        {pct == null ? (
          <Txt
            text={valor}
            fontFamily={MONO}
            fontWeight={800}
            fontSize={Math.max(70, Math.min(130, 680 / (valor.length * 0.62)))}
            fill={cor}
          />
        ) : null}
        <Txt
          text={rotulo}
          width={pct != null ? 520 : 680}
          textWrap
          fontFamily={FONTE}
          fontWeight={600}
          fontSize={38}
          fill={BRANCO}
        />
      </Rect>
    </Rect>
  ) as Rect;
  return pecaSimples(no, function* () {
    if (pct != null) yield* arco().endAngle(-90 + 360 * (pct / 100), 1.1, easeOutCubic);
  });
}

export interface FatoLinha {
  icone: string;
  texto: string;
}
/** Lista de fatos: ícone de linha em disco + frase curta; entram em sequência. */
export function fatosLista(linhas: FatoLinha[]): Peca {
  const itens: Rect[] = [];
  const no = (<Rect layout direction="column" gap={18} alignItems="start" />) as Rect;
  for (const l of linhas) {
    const r = (
      <Rect
        layout
        gap={24}
        alignItems="center"
        padding={[16, 28]}
        radius={20}
        fill="rgba(39,40,34,0.95)"
        stroke="rgba(255,255,255,0.14)"
        lineWidth={2}
        opacity={0}
        {...SOMBRA}
      >
        <Rect
          size={64}
          radius={32}
          fill={MK.fundo2}
          stroke="rgba(255,255,255,0.4)"
          lineWidth={3}
          alignItems="center"
          justifyContent="center"
        >
          <Img src={l.icone} size={36} />
        </Rect>
        <Txt text={l.texto} width={640} textWrap fontFamily={FONTE} fontWeight={600} fontSize={38} fill={BRANCO} />
      </Rect>
    ) as Rect;
    itens.push(r);
    no.add(r);
  }
  return {
    no,
    *entrar() {
      yield* sequence(0.45, ...itens.map(r => all(r.opacity(1, 0.3), r.x(0, 0.4, easeOutCubic))));
    },
    *sair() {
      yield* all(...itens.map(r => r.opacity(0, 0.25)));
    },
  };
}

/** Marcador discreto no canto: nº do item / total + linguagem. */
export function hudItem(idx: number, total: number, nome: string, cor: string): Peca {
  const no = (
    <Rect
      layout
      radius={14}
      fill="rgba(39,40,34,0.92)"
      paddingLeft={20}
      paddingRight={22}
      paddingTop={10}
      paddingBottom={10}
      gap={14}
      alignItems="center"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={2}
    >
      <Circle size={16} fill={cor} />
      <Txt text={`${num(idx, total)}/${total}`} fontFamily={MONO} fontWeight={700} fontSize={26} fill={MK.verde} />
      <Txt text={nome} fontFamily={MONO} fontWeight={600} fontSize={26} fill={MK.texto} />
    </Rect>
  ) as Rect;
  return pecaSimples(no);
}

/** Cartela de seção / parte da lista (comentário + título + subtítulo + logos das linguagens da seção). */
export function secaoCard(tag: string, titulo: string, sub: string, logos: string[]): Peca {
  const no = (
    <Rect
      layout
      direction="column"
      gap={22}
      alignItems="start"
      padding={[44, 64]}
      radius={26}
      fill="rgba(39,40,34,0.95)"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={2}
      {...SOMBRA}
    >
      <Txt text={`// ${tag}`} fontFamily={MONO} fontWeight={600} fontSize={34} fill={MK.comentario} />
      <Txt text={titulo} fontFamily={FONTE} fontWeight={800} fontSize={86} fill={BRANCO} />
      <Txt text={sub} fontFamily={MONO} fontWeight={600} fontSize={36} fill={MK.verde} />
      {logos.length ? (
        <Rect layout gap={20} marginTop={10}>
          {logos.map(u => (
            <Rect width={96} height={96} radius={20} fill="#ffffff" alignItems="center" justifyContent="center">
              <Img src={u} width={64} height={64} />
            </Rect>
          ))}
        </Rect>
      ) : null}
    </Rect>
  ) as Rect;
  return pecaSimples(no);
}

/** Cartela grande do item (mostrada junto do menu na troca de item): nº, nome e subtítulo. */
export function tituloItem(
  idx: number,
  nome: string,
  sub: string,
  cor: string,
  total = 10,
  logo?: string | null,
  placa = false,
  asp = 1,
): Peca {
  const alt = Math.min(210, 360 / Math.max(asp, 0.2));
  const no = (
    <Rect layout direction="column" gap={20} alignItems="start" width={800}>
      {logo ? (
        placa ? (
          <Rect padding={[18, 28]} radius={26} fill="#ffffff" alignItems="center" justifyContent="center" {...SOMBRA}>
            <Img src={logo} height={alt - 36} />
          </Rect>
        ) : (
          <Img src={logo} height={alt} />
        )
      ) : null}
      <Txt text={`#${num(idx, total)}`} fontFamily={MONO} fontWeight={700} fontSize={64} fill={MK.comentario} />
      <Txt
        text={nome}
        fontFamily={FONTE}
        fontWeight={800}
        fontSize={nome.length > 15 ? 84 : nome.length > 9 ? 120 : 170}
        fill={BRANCO}
        stroke="#0b0b10"
        lineWidth={14}
        strokeFirst
        lineJoin="round"
      />
      <Rect width={260} height={10} radius={5} fill={cor} />
      <Txt
        text={sub}
        fontFamily={MONO}
        fontWeight={600}
        fontSize={40}
        fill={MK.verde}
        stroke="#0b0b10"
        lineWidth={8}
        strokeFirst
        lineJoin="round"
      />
    </Rect>
  ) as Rect;
  return pecaSimples(no);
}

export interface ColunaComp {
  logo: string | null;
  rotulo: string;
  cor: string;
}
export interface LinhaComp {
  rotulo: string;
  valores: string[];
  vence?: number | null;
}

/** Comparativo A vs B em painel Monokai: cabeçalho com logos e linhas que entram em sequência; o vencedor da linha ganha ✓ verde. */
export function comparativo(colunas: ColunaComp[], linhas: LinhaComp[]): Peca {
  const itens: Rect[] = [];
  const LARG_ROT = 330;
  const LARG_COL = 330;
  const no = (
    <Rect
      layout
      direction="column"
      gap={14}
      padding={[28, 32]}
      radius={24}
      fill="rgba(39,40,34,0.95)"
      stroke="rgba(255,255,255,0.16)"
      lineWidth={2}
      {...SOMBRA}
    >
      <Rect layout gap={14} alignItems="center">
        <Rect width={LARG_ROT} />
        {colunas.map(c => (
          <Rect width={LARG_COL} direction="column" alignItems="center" gap={8}>
            {c.logo ? (
              <Rect padding={[10, 16]} radius={16} fill="#ffffff" alignItems="center" justifyContent="center">
                <Img src={c.logo} height={64} />
              </Rect>
            ) : null}
            <Txt text={c.rotulo} fontFamily={MONO} fontWeight={800} fontSize={30} fill={c.cor} />
          </Rect>
        ))}
      </Rect>
    </Rect>
  ) as Rect;
  for (const l of linhas) {
    const r = (
      <Rect layout gap={14} alignItems="center" padding={[10, 0]} opacity={0}>
        <Txt
          text={l.rotulo}
          width={LARG_ROT}
          textWrap
          fontFamily={FONTE}
          fontWeight={600}
          fontSize={30}
          fill="#d9d9cc"
        />
        {l.valores.map((v, i) => (
          <Rect
            width={LARG_COL}
            alignItems="center"
            justifyContent="center"
            gap={10}
            padding={[12, 10]}
            radius={14}
            fill={l.vence === i ? 'rgba(166,226,46,0.16)' : 'rgba(255,255,255,0.05)'}
            stroke={l.vence === i ? '#a6e22e' : null}
            lineWidth={2}
          >
            <Txt
              text={v}
              width={LARG_COL - 30}
              textWrap
              textAlign="center"
              fontFamily={MONO}
              fontWeight={700}
              fontSize={32}
              fill={l.vence === i ? '#a6e22e' : BRANCO}
            />
          </Rect>
        ))}
      </Rect>
    ) as Rect;
    itens.push(r);
    no.add(r);
  }
  no.opacity(0);
  return {
    no,
    *entrar() {
      no.scale(0.94);
      yield* all(no.opacity(1, 0.35), no.scale(1, 0.4, easeOutCubic));
      yield* sequence(0.5, ...itens.map(r => r.opacity(1, 0.3)));
    },
    *sair() {
      yield* all(no.opacity(0, 0.28));
    },
  };
}

/** Captura de tela / foto em moldura com aro branco e legenda (bom para interfaces). */
export function telaCard(imagem: string, legenda: string, largura = 900): Peca {
  const no = (
    <Rect layout direction="column" alignItems="center" gap={14}>
      <Rect radius={20} clip stroke={BRANCO} lineWidth={6} {...SOMBRA}>
        <Img src={imagem} width={largura} />
      </Rect>
      <Txt
        text={legenda}
        fontFamily={FONTE}
        fontWeight={800}
        fontSize={36}
        fill={BRANCO}
        stroke="#0b0b10"
        lineWidth={8}
        strokeFirst
        lineJoin="round"
      />
    </Rect>
  ) as Rect;
  return pecaSimples(no);
}
