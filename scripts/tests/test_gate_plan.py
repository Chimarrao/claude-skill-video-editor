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
confere("G1 projeto limpo sem erro P8", "P8 clipes" not in roda(tmp))

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

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(tmp2, ignore_errors=True)
print(f"\n{'FALHOU' if falhas else 'OK'} — {len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
