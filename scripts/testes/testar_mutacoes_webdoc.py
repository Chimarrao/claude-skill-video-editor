#!/usr/bin/env python3
"""TESTE DOS TESTES (Webdoc com B-roll): injeta defeitos numa cópia temporária e confirma que testar_regras_webdoc_broll.py os pega. Rode em animacao/."""

import json, shutil, subprocess, sys, tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
cwd = Path.cwd()
T = AQUI / "testar_regras_webdoc_broll.py"


def preparar():
    d = Path(tempfile.mkdtemp(prefix="mutw_"))
    (d / "src/scenes").mkdir(parents=True)
    (d / "src").joinpath("images").symlink_to(cwd / "src/images")
    for f in ("cenas.json", "broll.json", "cena1.meta"):
        shutil.copy(cwd / "src/scenes" / f, d / "src/scenes" / f)
    shutil.copy(cwd / "plano.json", d / "plano.json")
    return d


def rodar(d):
    return subprocess.run([sys.executable, str(T)], cwd=d, capture_output=True, text=True)


def mj(d, arq, fn):
    p = d / arq
    j = json.load(open(p))
    fn(j)
    json.dump(j, open(p, "w"), ensure_ascii=False)


def ev(j, nome, delta=None, abs_=None):
    for e in j["timeEvents"]:
        if e["name"] == nome:
            e["targetTime"] = abs_ if abs_ is not None else e["targetTime"] + delta
            return
    raise SystemExit(f"evento {nome} ausente")


def ev_t(i, k):
    return [
        e for e in json.load(open(cwd / "src/scenes/cena1.meta"))["timeEvents"] if e["name"] == f"{i}-i{k}"
    ][0]["targetTime"]


def lista(j):
    return next(c for c in j if c["tipo"] == "listacurta")


an = lambda j: next(c for c in j if c["tipo"] == "secao")
base = json.load(open(cwd / "plano.json"))
lcid = lista(json.load(open(cwd / "src/scenes/cenas.json")))["id"]
anid = an(json.load(open(cwd / "src/scenes/cenas.json")))["id"]
casos = [
    (
        "W1",
        "clipe sobre cena de animação",
        "src/scenes/broll.json",
        lambda j: j[0].update(t_inicio=base["janelas"][anid][0] + 1, t_fim=base["janelas"][anid][0] + 9),
    ),
    (
        "W2",
        "clipe curto (1.5 s)",
        "src/scenes/broll.json",
        lambda j: j[0].update(t_fim=j[0]["t_inicio"] + 1.5),
    ),
    ("W2", "velocidade 3x", "src/scenes/broll.json", lambda j: j[0].update(velocidade=3.0)),
    (
        "W3",
        "rótulo leve de 12 s",
        "plano.json",
        lambda j: j.update(overlay_leve=[[x[0], x[0] + 12] for x in j["overlay_leve"]]),
    ),
    (
        "W4",
        "rótulo de lista com 50 caracteres",
        "src/scenes/cenas.json",
        lambda j: lista(j)["itens"][0].update(rotulo="x" * 50),
    ),
    (
        "W4",
        "itens da lista colados (0.3 s)",
        "src/scenes/cena1.meta",
        lambda j: ev(
            j,
            f"{lcid}-i1",
            abs_=[e for e in j["timeEvents"] if e["name"] == f"{lcid}-i0"][0]["targetTime"] + 0.3,
        ),
    ),
    (
        "W4",
        "lista com 1 item",
        "src/scenes/cenas.json",
        lambda j: lista(j).update(itens=lista(j)["itens"][:1], total=1),
    ),
    (
        "W5",
        "título de impacto aos 10 s",
        "plano.json",
        lambda j: j["janelas"].update(t_falso=[10.0, 14.0, "impacto"]),
    ),
    (
        "W5",
        "títulos > 5% do vídeo",
        "plano.json",
        lambda j: j["janelas"].update(t_falso=[100.0, 100.0 + 0.2 * j["duracao"], "impacto"]),
    ),
    (
        "W6",
        "cena de item (menu/HUD)",
        "src/scenes/cenas.json",
        lambda j: j.append(dict(tipo="item", id="x_item", pecas=[])),
    ),
    (
        "W7",
        "Tela esticada (largura 5000)",
        "src/scenes/cenas.json",
        lambda j: [
            p["props"].update(largura=5000) for c in j for p in (c.get("pecas") or []) if p["tipo"] == "tela"
        ],
    ),
    (
        "W4",
        "pausa de lista com item dentro",
        "src/scenes/cenas.json",
        lambda j: lista(j).update(pausas=[[ev_t(lcid, 0) - 0.2, ev_t(lcid, 0) + 6]]),
    ),
    (
        "W8",
        "janela de código",
        "src/scenes/cenas.json",
        lambda j: an(j)["pecas"].append(dict(slot="dir", tipo="codigo", props={}, beat="b1")),
    ),
]
b = rodar(cwd)
print("base:", "verde" if b.returncode == 0 else "VERMELHA\n" + b.stdout[-500:])
if b.returncode:
    sys.exit(2)
falhas = []
for regra, nome, arq, fn in casos:
    d = preparar()
    try:
        mj(d, arq, fn)
    except SystemExit as e:
        print(f"  PULOU {nome}: {e}")
        continue
    r = rodar(d)
    pegou = r.returncode == 1 and any(
        l.strip().startswith(("- " + regra + ":", regra + " ")) and "falhas=0" not in l
        for l in r.stdout.splitlines()
    )
    print(f"  {'OK ' if pegou else 'FALHOU'} {regra:3s} {nome}")
    shutil.rmtree(d, ignore_errors=True)
    if not pegou:
        falhas.append((regra, nome))
if falhas:
    print("\nNÃO detectou:", falhas)
    sys.exit(1)
print("\nOK: todas as mutações foram detectadas")
