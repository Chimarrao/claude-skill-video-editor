#!/usr/bin/env python3
"""TESTE DO GATE 1 (gate_plan.py): injeta clipes repetidos/sobrepostos numa cópia do projeto e confirma que o P8 pega.
Rode em animacao/ depois de `plan.py`. Também confirma que o projeto limpo não dispara P8.
"""

import json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE.parent / "quality" / "gate_plan.py"
cwd = Path.cwd()
falhas = []


def copia():
    """Cópia temporária com o que o gate lê."""
    tmp = Path(tempfile.mkdtemp(prefix="gp_"))
    (tmp / "src/scenes").mkdir(parents=True)
    for f in ("scenes.json", "menu.json", "broll.json", "scene1.meta"):
        if (cwd / "src/scenes" / f).exists():
            shutil.copy(cwd / "src/scenes" / f, tmp / "src/scenes" / f)
    for f in ("plan.json", "plan_data.py", "geometry.py"):
        shutil.copy(cwd / f, tmp / f)
    return tmp


def roda(tmp):
    """Executa o gate na cópia e devolve a saída."""
    r = subprocess.run([sys.executable, str(GATE)], cwd=tmp, capture_output=True, text=True)
    return r.stdout + r.stderr


def confere(nome, ok, detalhe=""):
    print(("ok    " if ok else "FALHA ") + nome + (f"  {detalhe}" if detalhe and not ok else ""))
    if not ok:
        falhas.append(nome)


# G1 projeto limpo não dispara P8
tmp = copia()
confere("G1 projeto limpo sem erro P8/P9/P10", all(k not in roda(tmp) for k in ("P8 clipes", "P9 título", "P10 quadro")))

# G2 trecho repetido do mesmo vídeo
broll = json.load(open(tmp / "src/scenes/broll.json"))
dup = dict(broll[1])
dup["t_start"], dup["t_end"] = broll[-1]["t_end"] + 1, broll[-1]["t_end"] + 5
json.dump(broll + [dup], open(tmp / "src/scenes/broll.json", "w"))
confere("G2 P8 pega trecho repetido do mesmo arquivo", "P8 clipes" in roda(tmp) and "repete o trecho" in roda(tmp))

# G3 clipes sobrepostos na linha do tempo
tmp2 = copia()
b2 = json.load(open(tmp2 / "src/scenes/broll.json"))
b2[1]["t_start"] = b2[0]["t_end"] - 2
json.dump(b2, open(tmp2 / "src/scenes/broll.json", "w"))
confere("G3 P8 pega clipes sobrepostos no tempo", "antes de o clip" in roda(tmp2))

# G4 P9: item de grafo entrando com o título cobrindo o palco; G5 P10: rótulo cortado na borda
tmp3 = copia()
sc = json.load(open(tmp3 / "src/scenes/scenes.json"))
meta = json.load(open(tmp3 / "src/scenes/scene1.meta"))
ev = {e["name"]: e for e in meta["timeEvents"]}
alvo = None
for c in sc:
    pcs = c.get("pieces", [])
    titulo = next((q for q in pcs if q["slot"] == "overlay" and q["kind"] == "title"), None)
    grafo = next((q for q in pcs if q["kind"] == "graph" and q["props"].get("events")), None)
    if titulo and grafo and f"{c['id']}-{titulo['beat']}" in ev:
        alvo = (c, titulo, grafo)
        break
if alvo is None:
    print("pula  G4 (projeto sem cena com título + grafo; vale para listas)")
if alvo:
    c, titulo, grafo = alvo
    ev[grafo["props"]["events"][-1]]["targetTime"] = ev[f"{c['id']}-{titulo['beat']}"]["targetTime"] + 0.8
    json.dump(meta, open(tmp3 / "src/scenes/scene1.meta", "w"))
    confere("G4 P9 pega item de grafo entrando sob o título", "P9 título×grafo" in roda(tmp3))
tmp4 = copia()
sc4 = json.load(open(tmp4 / "src/scenes/scenes.json"))
alvo5 = next((c for c in sc4 if c["kind"] == "graph"), None)
if alvo5 is None:
    print("pula  G5 (projeto sem GraphScene; vale para listas/webdoc com grafo de cena inteira)")
else:
    alvo5["items"][0]["x"] = 930  # rótulo/ícone para fora da área segura
    json.dump(sc4, open(tmp4 / "src/scenes/scenes.json", "w"))
    confere("G5 P10 pega item fora da área segura do quadro", "P10 quadro" in roda(tmp4))
for d in (tmp3, tmp4):
    shutil.rmtree(d, ignore_errors=True)

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(tmp2, ignore_errors=True)
print(f"\n{'FALHOU' if falhas else 'OK'} — {len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
