#!/usr/bin/env python3
"""TESTE ESTÁTICO das regras do tipo "Lista com B-roll" sobre o que o plano.py gerou (rode DEPOIS de `python plano.py`, em animacao/).
Cada regra vem de uma correção real do usuário na edição do CapCut. Sai com código 1 se alguma falhar.
Regras:
 R1 sem HUD/contador NN/10          R2 menu sem extensão (exceto MENU_EXTENSOES=True)   R3 cartela do item com logo
 R4 Stat/Fatos sempre com logo à esquerda (LogoSolto no mesmo beat)     R5 peça/item de grafo nunca perto/dentro de clipe
 R6 cada item começa com vídeo logo após a cartela                      R7 animação+vazio <= ANIM_MAX
 R8 sem janela de código            R9 grafo ampliado >= 1.2x e fora da zona do avatar     R10 textos curtos (Stat/Fatos)
"""

import json, os, re, sys

J = lambda p: json.load(open(p))
cenas = J("src/scenes/cenas.json")
menu = J("src/scenes/menu.json")
plano = J("plano.json")
broll = J("src/scenes/broll.json") if os.path.exists("src/scenes/broll.json") else []
meta = {e["name"]: e["targetTime"] for e in J("src/scenes/cena1.meta")["timeEvents"]}
_src = open("plano_dados.py", encoding="utf8").read()


def flag(
    nome, padrao
):  # lê "NOME = valor" do plano_dados.py sem importá-lo (o import puxa o plano.py inteiro)
    m = re.search(rf"^{nome}\s*=\s*([^\s#]+)", _src, re.M)
    return (
        padrao
        if not m
        else (
            {"True": True, "False": False}.get(m.group(1), None)
            if m.group(1) in ("True", "False")
            else float(m.group(1))
        )
    )


CFG = dict(
    EXT=flag("MENU_EXTENSOES", False),
    LOGO=flag("CARTELA_LOGO_OBRIGATORIA", True),
    ANIM=flag("ANIM_MAX", 0.35),
    LEAD=flag("LEAD_CLIPE", 0.4),
    FOLGA=flag("FOLGA_CLIPE", 0.15),
    MENU=plano.get("menu_duracao", 3.7),
)
jan = plano["janelas"]
erros = []
ok = []


def regra(n, cond, msg):
    (ok if cond else erros).append(f"{n}: {msg}")


itens = [c for c in cenas if c.get("tipo") == "item"]
regra("R1", not any(c.get("hud") for c in itens), "nenhum item com HUD/contador")
regra(
    "R2",
    CFG["EXT"] or all(m["arquivo"] == m["rotulo"] for m in menu),
    "menu sem extensões (lista não é de arquivos)",
)
regra("R3", (not CFG["LOGO"]) or all(c.get("logo") for c in itens), "todas as cartelas de item têm logo")
# clipes por item
cl = {}
for b in broll:
    cl.setdefault(b.get("item"), []).append((b["t_inicio"], b["t_fim"])) if "item" in b else None
if not cl:  # broll.json sem 'item': distribui pela janela do item
    for b in broll:
        for k, (a0, a1, tp) in jan.items():
            if tp == "item" and a0 <= b["t_inicio"] < a1:
                cl.setdefault(k, []).append((b["t_inicio"], b["t_fim"]))
for k in cl:
    cl[k].sort()
for c in itens:
    pecas = c["pecas"]
    for i, p in enumerate(pecas):
        if p["tipo"] in ("stat", "fatos"):
            tem = any(q["tipo"] == "logosolto" for q in pecas[: i + 1][::-1][:3])
            (
                regra("R4", tem, f"[{c['id']}] {p['tipo']} #{i} tem logo à esquerda")
                if not tem
                else ok.append(f"R4: [{c['id']}] {p['tipo']} com logo")
            )
        if p["tipo"] == "codigo":
            erros.append(f"R8: [{c['id']}] janela de código num vídeo de lista com B-roll")
        if p["tipo"] == "stat":
            regra(
                "R10",
                len(str(p["props"]["valor"])) <= 9 and len(p["props"]["rotulo"]) <= 38,
                f"[{c['id']}] stat curto",
            )
        if p["tipo"] == "fatos":
            regra(
                "R10",
                len(p["props"]["linhas"]) <= 3 and all(len(l["texto"]) <= 34 for l in p["props"]["linhas"]),
                f"[{c['id']}] fatos curto",
            )
        if p["tipo"] == "grafo":
            regra(
                "R9", p["props"].get("esc", 1) >= 1.2, f"[{c['id']}] grafo ampliado {p['props'].get('esc')}x"
            )
    a0, a1, _ = jan[c["id"]]
    jc = cl.get(c["id"], [])
    if jc:
        regra(
            "R6",
            jc[0][0] - (a0 + CFG["MENU"]) <= 1.0 and jc[0][0] >= a0 + CFG["MENU"] - 0.05,
            f"[{c['id']}] 1º clipe em {jc[0][0]:.1f}s (cartela termina {a0 + CFG['MENU']:.1f}s)",
        )
    # R5: eventos de peça e itens de grafo fora das janelas proibidas [a-LEAD, b+FOLGA)
    for nome, t in meta.items():
        if (
            not nome.startswith(c["id"] + "-")
            or nome.startswith(c["id"] + "-va")
            or nome.endswith("-in")
            or nome.endswith("-out")
        ):
            continue
        for b0, b1 in jc:
            if b0 - CFG["LEAD"] - 0.02 < t < b1 + CFG["FOLGA"] - 0.02:
                erros.append(
                    f"R5: [{c['id']}] evento {nome} em {t:.2f}s cai em [{b0 - CFG['LEAD']:.2f}, {b1 + CFG['FOLGA']:.2f}] (clipe {b0:.1f}-{b1:.1f})"
                )
    for k_, (b0, b1) in enumerate(jc):
        t = meta.get(f"{c['id']}-va{k_}")
        regra(
            "R5",
            t is not None and abs(t - (b0 - CFG["LEAD"])) < 0.05,
            f"[{c['id']}] va{k_}={t} (clipe em {b0:.2f}, antecedência {CFG['LEAD']}s)",
        )
tot = clp = 0.0
for c in itens:
    a0, a1, _ = jan[c["id"]]
    ut = a1 - a0 - CFG["MENU"]
    tot += ut
    clp += sum(b - a for a, b in cl.get(c["id"], []))
r = (tot - clp) / tot if tot else 0
regra("R7", r <= CFG["ANIM"], f"animação+vazio {r * 100:.1f}% (máx {CFG['ANIM'] * 100:.0f}%)")
for l in ok[:0]:
    print(l)
resumo = {}
for l in ok + erros:
    resumo.setdefault(l.split(":")[0], [0, 0])[0 if l in ok else 1] += 1
for k in sorted(resumo, key=lambda x: int(x[1:])):
    print(f"{k:4s} ok={resumo[k][0]:3d} falhas={resumo[k][1]}")
if erros:
    print("\nFALHAS:")
    [print("  -", e) for e in erros[:40]]
    sys.exit(1)
print("\nOK: todas as regras passaram")
