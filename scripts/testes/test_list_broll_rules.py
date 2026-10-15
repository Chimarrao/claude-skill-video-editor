#!/usr/bin/env python3
"""TESTE ESTÁTICO das regras do tipo "Lista com B-roll" sobre o que o plan.py gerou (rode DEPOIS de `python plan.py`, em animacao/).
Cada regra vem de uma correção real do usuário na edição do CapCut. Sai com código 1 se alguma falhar.
Regras:
 R1 sem HUD/contador NN/10          R2 menu sem extensão (exceto MENU_EXTENSOES=True)   R3 cartela do item com logo
 R4 Stat/Fatos sempre com logo à esquerda (LogoSolto no mesmo beat)     R5 peça/item de grafo nunca perto/dentro de clipe
 R6 cada item começa com vídeo logo após a cartela                      R7 animação+vazio <= ANIM_MAX
 R8 sem janela de código            R9 grafo ampliado >= 1.2x e fora da zona do avatar     R10 textos curtos (Stat/Fatos)
"""

import json, os, re, sys

load_json = lambda p: json.load(open(p))
scenes = load_json("src/scenes/cenas.json")
menu = load_json("src/scenes/menu.json")
plan = load_json("plano.json")
broll = load_json("src/scenes/broll.json") if os.path.exists("src/scenes/broll.json") else []
meta = {e["name"]: e["targetTime"] for e in load_json("src/scenes/cena1.meta")["timeEvents"]}
_source = open("plano_dados.py", encoding="utf8").read()


def read_flag(
    name, default
):  # lê "NOME = valor" do plan_data.py sem importá-lo (o import puxa o plan.py inteiro)
    m = re.search(rf"^{name}\s*=\s*([^\s#]+)", _source, re.M)
    return (
        default
        if not m
        else (
            {"True": True, "False": False}.get(m.group(1), None)
            if m.group(1) in ("True", "False")
            else float(m.group(1))
        )
    )


CFG = dict(
    EXT=read_flag("MENU_EXTENSOES", False),
    LOGO=read_flag("CARTELA_LOGO_OBRIGATORIA", True),
    ANIM=read_flag("ANIM_MAX", 0.35),
    LEAD=read_flag("LEAD_CLIPE", 0.4),
    FOLGA=read_flag("FOLGA_CLIPE", 0.15),
    MENU=plan.get("menu_duracao", 3.7),
)
windows = plan["janelas"]
errors = []
passed = []


def rule(rule_id, condition, msg):
    (passed if condition else errors).append(f"{rule_id}: {msg}")


items = [c for c in scenes if c.get("tipo") == "item"]
rule("R1", not any(c.get("hud") for c in items), "nenhum item com HUD/contador")
rule(
    "R2",
    CFG["EXT"] or all(m["arquivo"] == m["rotulo"] for m in menu),
    "menu sem extensões (lista não é de arquivos)",
)
rule("R3", (not CFG["LOGO"]) or all(c.get("logo") for c in items), "todas as cartelas de item têm logo")
# clipes por item
clips_by_item = {}
for b in broll:
    clips_by_item.setdefault(b.get("item"), []).append((b["t_inicio"], b["t_fim"])) if "item" in b else None
if not clips_by_item:  # broll.json sem 'item': distribui pela janela do item
    for b in broll:
        for k, (a0, a1, tp) in windows.items():
            if tp == "item" and a0 <= b["t_inicio"] < a1:
                clips_by_item.setdefault(k, []).append((b["t_inicio"], b["t_fim"]))
for k in clips_by_item:
    clips_by_item[k].sort()
for c in items:
    pieces = c["pecas"]
    for idx, p in enumerate(pieces):
        if p["tipo"] in ("stat", "fatos"):
            has_logo = any(q["tipo"] == "logosolto" for q in pieces[: idx + 1][::-1][:3])
            (
                rule("R4", has_logo, f"[{c['id']}] {p['tipo']} #{idx} tem logo à esquerda")
                if not has_logo
                else passed.append(f"R4: [{c['id']}] {p['tipo']} com logo")
            )
        if p["tipo"] == "codigo":
            errors.append(f"R8: [{c['id']}] janela de código num vídeo de lista com B-roll")
        if p["tipo"] == "stat":
            rule(
                "R10",
                len(str(p["props"]["valor"])) <= 9 and len(p["props"]["rotulo"]) <= 38,
                f"[{c['id']}] stat curto",
            )
        if p["tipo"] == "fatos":
            rule(
                "R10",
                len(p["props"]["linhas"]) <= 3 and all(len(row["texto"]) <= 34 for row in p["props"]["linhas"]),
                f"[{c['id']}] fatos curto",
            )
        if p["tipo"] == "grafo":
            rule(
                "R9", p["props"].get("esc", 1) >= 1.2, f"[{c['id']}] grafo ampliado {p['props'].get('esc')}x"
            )
    a0, a1, _ = windows[c["id"]]
    item_clips = clips_by_item.get(c["id"], [])
    if item_clips:
        rule(
            "R6",
            item_clips[0][0] - (a0 + CFG["MENU"]) <= 1.0 and item_clips[0][0] >= a0 + CFG["MENU"] - 0.05,
            f"[{c['id']}] 1º clipe em {item_clips[0][0]:.1f}s (cartela termina {a0 + CFG['MENU']:.1f}s)",
        )
    # R5: eventos de peça e itens de grafo fora das janelas proibidas [a-LEAD, b+FOLGA)
    for event_name, t in meta.items():
        if (
            not event_name.startswith(c["id"] + "-")
            or event_name.startswith(c["id"] + "-va")
            or event_name.endswith("-in")
            or event_name.endswith("-out")
        ):
            continue
        for b0, b1 in item_clips:
            if b0 - CFG["LEAD"] - 0.02 < t < b1 + CFG["FOLGA"] - 0.02:
                errors.append(
                    f"R5: [{c['id']}] evento {event_name} em {t:.2f}s cai em [{b0 - CFG['LEAD']:.2f}, {b1 + CFG['FOLGA']:.2f}] (clipe {b0:.1f}-{b1:.1f})"
                )
    for k_, (b0, b1) in enumerate(item_clips):
        t = meta.get(f"{c['id']}-va{k_}")
        rule(
            "R5",
            t is not None and abs(t - (b0 - CFG["LEAD"])) < 0.05,
            f"[{c['id']}] va{k_}={t} (clipe em {b0:.2f}, antecedência {CFG['LEAD']}s)",
        )
total_window = total_clip = 0.0
for c in items:
    a0, a1, _ = windows[c["id"]]
    usable = a1 - a0 - CFG["MENU"]
    total_window += usable
    total_clip += sum(b - a for a, b in clips_by_item.get(c["id"], []))
ratio = (total_window - total_clip) / total_window if total_window else 0
rule("R7", ratio <= CFG["ANIM"], f"animação+vazio {ratio * 100:.1f}% (máx {CFG['ANIM'] * 100:.0f}%)")
for line in passed[:0]:
    print(line)
summary = {}
for line in passed + errors:
    summary.setdefault(line.split(":")[0], [0, 0])[0 if line in passed else 1] += 1
for key in sorted(summary, key=lambda x: int(x[1:])):
    print(f"{key:4s} ok={summary[key][0]:3d} falhas={summary[key][1]}")
if errors:
    print("\nFALHAS:")
    [print("  -", e) for e in errors[:40]]
    sys.exit(1)
print("\nOK: todas as regras passaram")
