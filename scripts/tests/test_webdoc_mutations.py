#!/usr/bin/env python3
"""TESTE DOS TESTES (Webdoc com B-roll): injeta defeitos numa cópia temporária e confirma que test_webdoc_broll_rules.py os pega. Rode em animacao/."""

import json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
cwd = Path.cwd()
RULES_TEST = HERE / "test_webdoc_broll_rules.py"


def setup():
    tmp_dir = Path(tempfile.mkdtemp(prefix="mutw_"))
    (tmp_dir / "src/scenes").mkdir(parents=True)
    (tmp_dir / "src").joinpath("images").symlink_to(cwd / "src/images")
    for f in ("scenes.json", "broll.json", "scene1.meta"):
        shutil.copy(cwd / "src/scenes" / f, tmp_dir / "src/scenes" / f)
    shutil.copy(cwd / "plan.json", tmp_dir / "plan.json")
    return tmp_dir


def run(tmp_dir):
    return subprocess.run([sys.executable, str(RULES_TEST)], cwd=tmp_dir, capture_output=True, text=True)


def mutate_json(tmp_dir, file, fn):
    p = tmp_dir / file
    doc = json.load(open(p))
    fn(doc)
    json.dump(doc, open(p, "w"), ensure_ascii=False)


def shift_event(doc, name, delta=None, absolute=None):
    for e in doc["timeEvents"]:
        if e["name"] == name:
            e["targetTime"] = absolute if absolute is not None else e["targetTime"] + delta
            return
    raise SystemExit(f"evento {name} ausente")


def event_time(scene_idx, k):
    return [
        e for e in json.load(open(cwd / "src/scenes/scene1.meta"))["timeEvents"] if e["name"] == f"{scene_idx}-i{k}"
    ][0]["targetTime"]


def find_short_list(doc):
    return next(c for c in doc if c["kind"] == "shortlist")


find_section = lambda doc: next(c for c in doc if c["kind"] == "section")
base = json.load(open(cwd / "plan.json"))
list_id = find_short_list(json.load(open(cwd / "src/scenes/scenes.json")))["id"]
section_id = find_section(json.load(open(cwd / "src/scenes/scenes.json")))["id"]
cases = [
    (
        "W1",
        "clipe sobre cena de animação",
        "src/scenes/broll.json",
        lambda j: j[0].update(t_start=base["windows"][section_id][0] + 1, t_end=base["windows"][section_id][0] + 9),
    ),
    (
        "W2",
        "clipe curto (1.5 s)",
        "src/scenes/broll.json",
        lambda j: j[0].update(t_end=j[0]["t_start"] + 1.5),
    ),
    ("W2", "velocidade 3x", "src/scenes/broll.json", lambda j: j[0].update(speed=3.0)),
    (
        "W3",
        "rótulo leve de 12 s",
        "plan.json",
        lambda j: j.update(overlay_light=[[x[0], x[0] + 12] for x in j["overlay_light"]]),
    ),
    (
        "W4",
        "rótulo de lista com 50 caracteres",
        "src/scenes/scenes.json",
        lambda j: find_short_list(j)["items"][0].update(label="x" * 50),
    ),
    (
        "W4",
        "itens da lista colados (0.3 s)",
        "src/scenes/scene1.meta",
        lambda j: shift_event(
            j,
            f"{list_id}-i1",
            absolute=[e for e in j["timeEvents"] if e["name"] == f"{list_id}-i0"][0]["targetTime"] + 0.3,
        ),
    ),
    (
        "W4",
        "lista com 1 item",
        "src/scenes/scenes.json",
        lambda j: find_short_list(j).update(items=find_short_list(j)["items"][:1], total=1),
    ),
    (
        "W5",
        "título de impacto aos 10 s",
        "plan.json",
        lambda j: j["windows"].update(t_false=[10.0, 14.0, "impact"]),
    ),
    (
        "W5",
        "títulos > 5% do vídeo",
        "plan.json",
        lambda j: j["windows"].update(t_false=[100.0, 100.0 + 0.2 * j["duration"], "impact"]),
    ),
    (
        "W6",
        "cena de item (menu/HUD)",
        "src/scenes/scenes.json",
        lambda j: j.append(dict(kind="item", id="x_item", pieces=[])),
    ),
    (
        "W7",
        "Tela esticada (largura 5000)",
        "src/scenes/scenes.json",
        lambda j: [
            p["props"].update(width=5000) for c in j for p in (c.get("pieces") or []) if p["kind"] == "screen"
        ],
    ),
    (
        "W4",
        "pausa de lista com item dentro",
        "src/scenes/scenes.json",
        lambda j: find_short_list(j).update(pauses=[[event_time(list_id, 0) - 0.2, event_time(list_id, 0) + 6]]),
    ),
    (
        "W8",
        "janela de código",
        "src/scenes/scenes.json",
        lambda j: find_section(j)["pieces"].append(dict(slot="dir", kind="code", props={}, beat="b1")),
    ),
]
b = run(cwd)
print("base:", "green" if b.returncode == 0 else "VERMELHA\n" + b.stdout[-500:])
if b.returncode:
    sys.exit(2)
failures = []
for rule_id, name, file, fn in cases:
    tmp_dir = setup()
    try:
        mutate_json(tmp_dir, file, fn)
    except SystemExit as e:
        print(f"  PULOU {name}: {e}")
        continue
    r = run(tmp_dir)
    caught = r.returncode == 1 and any(
        line.strip().startswith(("- " + rule_id + ":", rule_id + " ")) and "falhas=0" not in line
        for line in r.stdout.splitlines()
    )
    print(f"  {'OK ' if caught else 'FAILED'} {rule_id:3s} {name}")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if not caught:
        failures.append((rule_id, name))
if failures:
    print("\nNÃO detectou:", failures)
    sys.exit(1)
print("\nOK: todas as mutações foram detectadas")
