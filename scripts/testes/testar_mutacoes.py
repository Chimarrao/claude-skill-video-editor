#!/usr/bin/env python3
"""TESTE DOS TESTES: injeta defeitos conhecidos (cópia temporária) e confirma que testar_regras_lista_broll.py os pega.
Rode em animacao/ depois de `plano.py` + (opcional) o teste verde. Cada mutação deve FALHAR na regra indicada.
"""

import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
cwd = Path.cwd()
T = AQUI / "testar_regras_lista_broll.py"


def preparar():
    d = Path(tempfile.mkdtemp(prefix="mut_"))
    (d / "src/scenes").mkdir(parents=True)
    for f in ("cenas.json", "menu.json", "broll.json", "cena1.meta"):
        shutil.copy(cwd / "src/scenes" / f, d / "src/scenes" / f)
    shutil.copy(cwd / "plano.json", d / "plano.json")
    shutil.copy(cwd / "plano_dados.py", d / "plano_dados.py")
    return d


def rodar(d):
    return subprocess.run([sys.executable, str(T)], cwd=d, capture_output=True, text=True)


def mut_json(d, arq, fn):
    p = d / arq
    j = json.load(open(p))
    fn(j)
    json.dump(j, open(p, "w"), ensure_ascii=False)


def meta_evento(j, pref, delta=None, abs_=None):
    for e in j["timeEvents"]:
        if e["name"].startswith(pref):
            e["targetTime"] = abs_ if abs_ is not None else e["targetTime"] + delta
            return
    raise SystemExit(f"evento {pref} não existe")


itens = lambda j: [c for c in j if c.get("tipo") == "item"]
broll = json.load(open(cwd / "src/scenes/broll.json"))
c0 = broll[0]
casos = [
    ("R1", "HUD ligado", "src/scenes/cenas.json", lambda j: itens(j)[0].update(hud=True)),
    ("R2", "extensão no menu", "src/scenes/menu.json", lambda j: j[0].update(arquivo="kolibri.img")),
    ("R3", "cartela sem logo", "src/scenes/cenas.json", lambda j: itens(j)[0].update(logo=None)),
    (
        "R4",
        "Stat sem logo à esquerda",
        "src/scenes/cenas.json",
        lambda j: [c.update(pecas=[p for p in c["pecas"] if p["tipo"] != "logosolto"]) for c in itens(j)],
    ),
    (
        "R5",
        "va atrasado (peça vaza sobre o clipe)",
        "src/scenes/cena1.meta",
        lambda j: meta_evento(j, "haiku-va0", delta=+0.5),
    ),
    (
        "R5",
        "evento de peça dentro do clipe",
        "src/scenes/cena1.meta",
        lambda j: (
            meta_evento(j, "haiku-g", abs_=c0["t_inicio"] if False else 0)
            if False
            else meta_evento(
                j, "reactos-b", abs_=[b for b in broll if "UM SISTEMA" in b["arquivo"]][0]["t_inicio"] + 5
            )
        ),
    ),
    (
        "R6",
        "1º clipe tarde demais",
        "src/scenes/broll.json",
        lambda j: j[0].update(t_inicio=j[0]["t_inicio"] + 5, t_fim=j[0]["t_fim"] + 5),
    ),
    (
        "R7",
        "animação demais (remove clipes)",
        "src/scenes/broll.json",
        lambda j: [j.pop() for _ in range(len(j) // 2)],
    ),
    (
        "R8",
        "janela de código",
        "src/scenes/cenas.json",
        lambda j: itens(j)[0]["pecas"].append(dict(slot="dir", tipo="codigo", props={}, beat="b1")),
    ),
    (
        "R9",
        "grafo pequeno",
        "src/scenes/cenas.json",
        lambda j: [p["props"].update(esc=1.0) for c in itens(j) for p in c["pecas"] if p["tipo"] == "grafo"],
    ),
    (
        "R10",
        "Stat com texto longo",
        "src/scenes/cenas.json",
        lambda j: [
            p["props"].update(rotulo="x" * 60) for c in itens(j) for p in c["pecas"] if p["tipo"] == "stat"
        ],
    ),
]
base = rodar(cwd)
falhas = []
print("base:", "verde" if base.returncode == 0 else "VERMELHA (conserte antes)\n" + base.stdout[-600:])
if base.returncode:
    sys.exit(2)
for regra, nome, arq, fn in casos:
    d = preparar()
    try:
        mut_json(d, arq, fn)
    except SystemExit as e:
        print(f"  PULOU {nome}: {e}")
        continue
    r = rodar(d)
    pegou = r.returncode == 1 and (
        f"{regra}:" in r.stdout
        or f"{regra} " in r.stdout
        and "falhas=0" not in [l for l in r.stdout.splitlines() if l.startswith(regra + " ")][0:1]
        and True
    )
    pegou = r.returncode == 1 and any(
        l.strip().startswith(("- " + regra + ":", regra + " ")) and "falhas=0" not in l
        for l in r.stdout.splitlines()
    )
    print(f"  {'OK ' if pegou else 'FALHOU'} {regra:4s} {nome}")
    shutil.rmtree(d, ignore_errors=True)
    if not pegou:
        falhas.append((regra, nome))
if falhas:
    print("\nO teste NÃO detectou:", falhas)
    sys.exit(1)
print("\nOK: todas as mutações foram detectadas")
