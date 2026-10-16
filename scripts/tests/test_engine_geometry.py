#!/usr/bin/env python3
"""TESTE do motor (template/plan.py + geometry.py) contra os defeitos que o usuário já reprovou. Não precisa de projeto nem de rede.

 E1 ligação única = seta RETA e alinhada (nada de S torto)           E2 enumeração sem ligações = FILEIRA lado a lado, nunca coluna
 E3 estilo da seta: reta para até 2 ramos, cotovelo só em leque 3+   E4 a seta nunca corta o rótulo do próprio nó (geometry.problems)
 E5 itens do mesmo grafo entram com pelo menos ITEM_GAP s            E6 a geometria detecta a seta que atravessa texto (teste do teste)
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

print("\n".join(f"  ok    {n}" for n in ok))
if falhas:
    print("\nFALHOU:\n  - " + "\n  - ".join(falhas))
    sys.exit(1)
print(f"\nOK: {len(ok)} verificações do motor passaram")
