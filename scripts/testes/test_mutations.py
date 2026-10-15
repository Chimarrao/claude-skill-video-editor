#!/usr/bin/env python3
"""TESTE DOS TESTES: injeta defeitos conhecidos (cópia temporária) e confirma que test_list_broll_rules.py os pega.
Rode em animacao/ depois de `plan.py` + (opcional) o teste verde. Cada mutação deve FALHAR na regra indicada.
"""

import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
cwd = Path.cwd()
RULES_TEST = HERE / "test_list_broll_rules.py"


def setup():
    tmp_dir = Path(tempfile.mkdtemp(prefix="mut_"))
    (tmp_dir / "src/scenes").mkdir(parents=True)
    for f in ("cenas.json", "menu.json", "broll.json", "cena1.meta"):
        shutil.copy(cwd / "src/scenes" / f, tmp_dir / "src/scenes" / f)
    shutil.copy(cwd / "plano.json", tmp_dir / "plano.json")
    shutil.copy(cwd / "plano_dados.py", tmp_dir / "plano_dados.py")
    return tmp_dir


def run(tmp_dir):
    return subprocess.run([sys.executable, str(RULES_TEST)], cwd=tmp_dir, capture_output=True, text=True)


def mutate_json(tmp_dir, file, fn):
    p = tmp_dir / file
    doc = json.load(open(p))
    fn(doc)
    json.dump(doc, open(p, "w"), ensure_ascii=False)


def shift_meta_event(doc, prefix, delta=None, absolute=None):
    for e in doc["timeEvents"]:
        if e["name"].startswith(prefix):
            e["targetTime"] = absolute if absolute is not None else e["targetTime"] + delta
            return
    raise SystemExit(f"evento {prefix} não existe")


items = lambda doc: [c for c in doc if c.get("tipo") == "item"]
broll = json.load(open(cwd / "src/scenes/broll.json"))
first_clip = broll[0]
cases = [
    ("R1", "HUD ligado", "src/scenes/cenas.json", lambda j: items(j)[0].update(hud=True)),
    ("R2", "extensão no menu", "src/scenes/menu.json", lambda j: j[0].update(arquivo="kolibri.img")),
    ("R3", "cartela sem logo", "src/scenes/cenas.json", lambda j: items(j)[0].update(logo=None)),
    (
        "R4",
        "Stat sem logo à esquerda",
        "src/scenes/cenas.json",
        lambda j: [c.update(pecas=[p for p in c["pecas"] if p["tipo"] != "logosolto"]) for c in items(j)],
    ),
    (
        "R5",
        "va atrasado (peça vaza sobre o clipe)",
        "src/scenes/cena1.meta",
        lambda j: shift_meta_event(j, "haiku-va0", delta=+0.5),
    ),
    (
        "R5",
        "evento de peça dentro do clipe",
        "src/scenes/cena1.meta",
        lambda j: (
            shift_meta_event(j, "haiku-g", absolute=first_clip["t_inicio"] if False else 0)
            if False
            else shift_meta_event(
                j, "reactos-b", absolute=[b for b in broll if "UM SISTEMA" in b["arquivo"]][0]["t_inicio"] + 5
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
        lambda j: items(j)[0]["pecas"].append(dict(slot="dir", tipo="codigo", props={}, beat="b1")),
    ),
    (
        "R9",
        "grafo pequeno",
        "src/scenes/cenas.json",
        lambda j: [p["props"].update(esc=1.0) for c in items(j) for p in c["pecas"] if p["tipo"] == "grafo"],
    ),
    (
        "R10",
        "Stat com texto longo",
        "src/scenes/cenas.json",
        lambda j: [
            p["props"].update(rotulo="x" * 60) for c in items(j) for p in c["pecas"] if p["tipo"] == "stat"
        ],
    ),
]
baseline = run(cwd)
failures = []
print("base:", "verde" if baseline.returncode == 0 else "VERMELHA (conserte antes)\n" + baseline.stdout[-600:])
if baseline.returncode:
    sys.exit(2)
for rule_id, name, file, fn in cases:
    tmp_dir = setup()
    try:
        mutate_json(tmp_dir, file, fn)
    except SystemExit as e:
        print(f"  PULOU {name}: {e}")
        continue
    r = run(tmp_dir)
    caught = r.returncode == 1 and (
        f"{rule_id}:" in r.stdout
        or f"{rule_id} " in r.stdout
        and "falhas=0" not in [line for line in r.stdout.splitlines() if line.startswith(rule_id + " ")][0:1]
        and True
    )
    caught = r.returncode == 1 and any(
        line.strip().startswith(("- " + rule_id + ":", rule_id + " ")) and "falhas=0" not in line
        for line in r.stdout.splitlines()
    )
    print(f"  {'OK ' if caught else 'FALHOU'} {rule_id:4s} {name}")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if not caught:
        failures.append((rule_id, name))
if failures:
    print("\nO teste NÃO detectou:", failures)
    sys.exit(1)
print("\nOK: todas as mutações foram detectadas")
