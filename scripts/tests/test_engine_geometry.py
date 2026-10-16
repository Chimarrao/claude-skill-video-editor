#!/usr/bin/env python3
"""TESTE do motor (template/plan.py + geometry.py) contra os defeitos que o usuário já reprovou. Não precisa de projeto nem de rede.

 E1 ligação única = seta RETA e alinhada (nada de S torto)           E2 enumeração sem ligações = FILEIRA lado a lado, nunca coluna
 E3 estilo da seta: reta para até 2 ramos, cotovelo só em leque 3+   E4 a seta nunca corta o rótulo do próprio nó (geometry.problems)
 E5 itens do mesmo grafo entram com pelo menos ITEM_GAP s            E6 a geometria detecta a seta que atravessa texto (teste do teste)
 E7 o último item do grafo realmente entra (a thread de enter() fica viva até a animação terminar)
 E8 rótulo com separador isolado ("PalmOS 6 · Cobalt") quebra no separador, sem "·" pendurado   E9 marcas em camelCase (iPad, iOS) não viram "IPad"
 E10 a ponta da seta encosta no miolo da placa mesmo com rótulo de 2 linhas; seta solta é acusada (teste do teste)
 E11 o nome da cartela do item encolhe para caber na largura (nada vaza da tela: "Palm OS Cobalt" passava de 800 px)
 E12 rótulo cortado na borda do quadro / dentro da zona do avatar é acusado; o ajuste automático desloca o grafo para dentro
 E13 o título respeita os itens de grafo ancorados depois dele (plan.py)
Uso: python test_engine_geometry.py   (de qualquer pasta)
"""

import json, os, sys, tempfile
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "template"
tmp = Path(tempfile.mkdtemp(prefix="eng_"))
words = [dict(word=w, start=1.0 + 0.1 * i, end=1.05 + 0.1 * i) for i, w in enumerate("alfa beta gama delta epsilon zeta eta teta iota kapa".split())]
json.dump(dict(duration=30.0, segments=[dict(words=words, start=1.0, end=3.0, text="")]), open(tmp / "t.json", "w"))
os.environ["TRANSCRIPTION"] = str(tmp / "t.json")
os.chdir(tmp)
sys.path.insert(0, str(TEMPLATE))
import plan  # noqa: E402
import geometry  # noqa: E402

ok, falhas = [], []


def teste(nome, cond, msg=""):
    (ok if cond else falhas).append(f"{nome}: {msg}" if not cond else nome)


def item(label, id=None, parent=None, **kw):
    """Item de grafo sem arquivo de imagem (disco/foto redonda), para testar só a geometria."""
    d = plan.Item("foto_x", label=label, id=id, parent=parent, h=130, circular=True, **kw)
    d["bezel"] = False
    return d


def pos_out(items, dir_, links=()):
    out, s, depth = plan.layout(items, dir_, links=links)
    return out, s


# E1: ligação única alinhada (LR e TB), inclusive com outra raiz no mesmo nível
for d in ("LR", "TB"):
    its = [item("A", "a"), item("B", parent="a")]
    out, _ = pos_out(its, d)
    cross = (lambda p: p[1]) if d == "LR" else (lambda p: p[0])
    teste(f"E1 ligação única alinhada {d}", abs(cross(out[0]) - cross(out[1])) < 1, f"{out}")
its = [item("A", "a"), item("R2", "r2"), item("C", parent="a")]
out, _ = pos_out(its, "LR")
teste("E1 ligação única alinhada com 2 raízes", abs(out[0][1] - out[2][1]) < 1 or abs(out[1][1] - out[2][1]) < 1, f"{out}")

# E2: enumeração sem ligações vira fileira
its = [item(n) for n in ("Bugs", "Instabilidade", "Desempenho", "Rejeição de mercado", "Impacto histórico")]
for d in ("LR", "TB"):
    out, _ = pos_out(its, d)
    ys = [out[i][1] for i in range(5)]
    xs = [out[i][0] for i in range(5)]
    teste(f"E2 enumeração em fileira (dir={d})", max(ys) - min(ys) < 1 and xs == sorted(xs) and len(set(xs)) == 5, f"y={ys} x={xs}")

# E3: estilo das setas
par = [(0, 1)]
teste("E3 ligação única reta", plan.edge_style(par, 0, 1, 120) == "straight")
par = [(0, 1), (0, 2)]
teste("E3 dois ramos retos", plan.edge_style(par, 0, 1, 120) == "straight")
par = [(0, 1), (0, 2), (0, 3)]
teste("E3 leque de 3 em cotovelo", plan.edge_style(par, 0, 1, 120) == "elbow")


# E4/E6: a seta não corta o rótulo; com o desenho antigo (sem LABEL_DROP) a geometria TEM que acusar
def cena(drop):
    pai = dict(img="x", x=0, y=0, h=130, plate=False, bezel=True, circular=False, label="Sistema operacional", iw=130, ih=130, pw=None, ph=None)
    filho = dict(img="y", x=0, y=300, h=130, plate=False, bezel=True, circular=False, label="Hardware", iw=130, ih=130, pw=None, ph=None)
    edges = [dict(src=0, dst=1, sides=["bottom", "top"], style="straight", bus=None)]
    antigo = geometry.LABEL_DROP
    geometry.LABEL_DROP = drop
    try:
        return geometry.problems([pai, filho], edges)
    finally:
        geometry.LABEL_DROP = antigo


teste("E4 seta com LABEL_DROP não corta o rótulo", cena(80) == [], f"{cena(80)}")
teste("E6 sem LABEL_DROP a geometria acusa o corte", any("corta o rótulo" in p for p in cena(0)), f"{cena(0)}")

# E5: ritmo — 4 itens ancorados na MESMA palavra entram espaçados por ITEM_GAP
plan.CFG["ITEM_GAP"] = 0.9
sc = plan.GraphScene("g", 0.0, [item(f"I{k}", at=("alfa", 1.0)) for k in range(4)])
js, ev = plan.build_graph(sc, 0.5, 12.0)
bs = sorted({t for n, t in ev if not n.endswith("-in")})
difs = [round(b - a, 2) for a, b in zip(bs, bs[1:])]
teste("E5 itens espaçados pelo ritmo mínimo", len(bs) == 4 and all(d >= 0.85 for d in difs), f"tempos={bs} difs={difs}")

# E7: o enter() do grafo mantém a thread viva até o último item terminar (senão o último item e sua seta nunca aparecem)
gp = (TEMPLATE / "src/lib/graphPiece.tsx").read_text(encoding="utf8")
fim_loop = gp.split("*enter()")[1].split("*exit()")[0]
teste("E7 graphPiece.enter espera o último item", "waitFor(0.8)" in fim_loop.split("if (!ev) yield* waitFor(0.55);")[-1], "falta o waitFor final")


# E8: separador isolado some na quebra de linha (nada de "PalmOS 6 ·" / "· Cobalt")
for lab in ("PalmOS 6 · Cobalt", "Android 3 · Honeycomb", "Android 3.0 · fev/2011"):
    w = geometry.wrap_label(lab)
    teste(f"E8 rótulo '{lab}' sem separador pendurado", "\n" in w and not any(l.strip().startswith(("·", "-", "•")) or l.strip().endswith(("·", "-", "•")) for l in w.split("\n")), repr(w))
teste("E8 rótulo curto com separador continua em 1 linha", geometry.wrap_label("iOS · watchOS") == "iOS · watchOS")

# E9: o figure.tsx não coloca "I" maiúsculo em iPad/iOS
fig = (TEMPLATE / "src/lib/figure.tsx").read_text(encoding="utf8")
teste("E9 figure.tsx preserva camelCase (iPad/iOS/webOS)", "[a-z]+[A-Z]" in fig and "toUpperCase" in fig, "falta o teste de camelCase antes do toUpperCase")

# E10: placa larga com rótulo de 2 linhas: a seta de cima chega a ~TIP_GAP do miolo (não 100 px acima, na reserva do rótulo)
pai10 = dict(img="x", x=0, y=0, h=130, plate=False, bezel=True, circular=False, label="Palm", iw=130, ih=130, pw=None, ph=None)
placa = dict(img="y", x=0, y=300, h=110, plate=True, bezel=False, circular=False, label="PalmSource: software", iw=250, ih=70, pw=290, ph=100)
ed = [dict(src=0, dst=1, sides=["bottom", "top"], style="straight", bus=None)]
teste("E10 ponta da seta encosta na placa (rótulo de 2 linhas)", geometry.problems([pai10, placa], ed) == [], f"{geometry.problems([pai10, placa], ed)}")
antigo_gap = geometry.TIP_GAP
geometry.TIP_GAP = 120
try:
    teste("E10 seta solta é acusada (teste do teste)", any("seta solta" in p for p in geometry.problems([pai10, placa], ed)))
finally:
    geometry.TIP_GAP = antigo_gap
arrow = (TEMPLATE / "src/lib/arrowBetween.tsx").read_text(encoding="utf8")
teste("E10 arrowBetween usa o miolo (core) das colunas", "(n as any).core" in arrow and "(column as any).core" in fig)


# E11: nome da cartela cabe na largura da cartela (fonte proporcional ao tamanho do nome)
cards = (TEMPLATE / "src/lib/cards.tsx").read_text(encoding="utf8")
teste("E11 cartela do item ajusta a fonte ao tamanho do nome", "Math.floor(780 / (0.55 * name.length))" in cards, "falta o ajuste de fonte em titleItem")


# E12: rótulo de 2 linhas colado na borda de baixo (Steve Jobs (NeXT) saía do quadro) e rótulo dentro da zona do avatar (Sistemas tão ruins)
def it12(y, x=0, label="Steve Jobs\n(NeXT)"):
    return dict(img="f", x=x, y=y, h=90, plate=False, bezel=False, circular=True, label=label, iw=90, ih=90, pw=None, ph=None)


corte = [it12(0), it12(400)]
teste("E12 rótulo de 2 linhas encostando embaixo é acusado", any("área segura" in p for p in geometry.frame_problems(corte)), f"{geometry.frame_problems(corte)}")
av = [it12(0), it12(300, x=655, label="Sistemas\ntão ruins")]
teste("E12 rótulo na zona do avatar é acusado", any("avatar" in p for p in geometry.frame_problems(av)), f"{geometry.frame_problems(av)}")
sh = geometry.fit_shift(av)
teste("E12 fit_shift tira o grafo da zona do avatar", sh is not None and not geometry.frame_problems(av, 1.0, sh[0], sh[1]), f"{sh}")
teste("E12 grafo bem posicionado não tem problema", geometry.frame_problems([it12(-200), it12(100, x=-300)]) == [])
bb = geometry.visible_bbox([it12(0)])
teste("E12 bbox visível inclui o rótulo (embaixo do disco)", bb[3] > 45 + 90, f"{bb}")

# E13: o título encolhe para terminar antes do item de grafo ancorado depois dele
src_plan = (TEMPLATE / "plan.py").read_text(encoding="utf8")
teste("E13 plan.py limita o título pelos itens de grafo da cena", "if isinstance(_at, tuple) and Anchor(_at[1], _at[0]) > t + 0.05" in src_plan, "falta o limite do título")

print("\n".join(f"  ok    {n}" for n in ok))
if falhas:
    print("\nFALHOU:\n  - " + "\n  - ".join(falhas))
    sys.exit(1)
print(f"\nOK: {len(ok)} verificações do motor passaram")
