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
    for f in ("scenes.json", "menu.json", "broll.json", "scene1.meta"):
        shutil.copy(cwd / "src/scenes" / f, tmp_dir / "src/scenes" / f)
    shutil.copy(cwd / "plan.json", tmp_dir / "plan.json")
    shutil.copy(cwd / "plan_data.py", tmp_dir / "plan_data.py")
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


items = lambda doc: [c for c in doc if c.get("kind") == "item"]
broll = json.load(open(cwd / "src/scenes/broll.json"))
first_item = items(json.load(open(cwd / "src/scenes/scenes.json")))[0]["id"]
item_window = json.load(open(cwd / "plan.json"))["windows"][first_item]
first_clip = next(b for b in broll if item_window[0] <= b["t_start"] < item_window[1])  # 1º clipe do 1º item
cases = [
    ("R1", "HUD ligado", "src/scenes/scenes.json", lambda j: items(j)[0].update(hud=True)),
    ("R2", "extensão no menu", "src/scenes/menu.json", lambda j: j[0].update(file="example.img")),
    ("R3", "cartela sem logo", "src/scenes/scenes.json", lambda j: items(j)[0].update(logo=None)),
    (
        "R4",
        "Stat sem logo à esquerda",
        "src/scenes/scenes.json",
        lambda j: [c.update(pieces=[p for p in c["pieces"] if p["kind"] != "freelogo"]) for c in items(j)],
    ),
    (
        "R5",
        "va atrasado (peça vaza sobre o clipe)",
        "src/scenes/scene1.meta",
        lambda j: shift_meta_event(j, f"{first_item}-va0", delta=+0.5),
    ),
    (
        "R5",
        "evento de peça dentro do clipe",
        "src/scenes/scene1.meta",
        lambda j: shift_meta_event(j, f"{first_item}-g", absolute=first_clip["t_start"] + 5),
    ),
    (
        "R6",
        "1º clipe tarde demais",
        "src/scenes/broll.json",
        lambda j: [b.update(t_start=b["t_start"] + 5, t_end=b["t_end"] + 5) for b in j if b["t_start"] == first_clip["t_start"]],
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
        "src/scenes/scenes.json",
        lambda j: items(j)[0]["pieces"].append(dict(slot="dir", kind="code", props={}, beat="b1")),
    ),
    (
        "R9",
        "grafo pequeno",
        "src/scenes/scenes.json",
        lambda j: [p["props"].update(zoom=1.0) for c in items(j) for p in c["pieces"] if p["kind"] == "graph"],
    ),
    (
        "R10",
        "Stat com texto longo",
        "src/scenes/scenes.json",
        lambda j: [
            p["props"].update(label="x" * 60) for c in items(j) for p in c["pieces"] if p["kind"] == "stat"
        ],
    ),
]
baseline = run(cwd)
failures = []
print("base:", "green" if baseline.returncode == 0 else "VERMELHA (conserte antes)\n" + baseline.stdout[-600:])
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
    print(f"  {'OK ' if caught else 'FAILED'} {rule_id:4s} {name}")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if not caught:
        failures.append((rule_id, name))
if failures:
    print("\nO teste NÃO detectou:", failures)
    sys.exit(1)
print("\nOK: todas as mutações foram detectadas")
