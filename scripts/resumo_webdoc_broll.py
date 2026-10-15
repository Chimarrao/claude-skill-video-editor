#!/usr/bin/env python3
"""RESUMO FINAL do Webdoc com B-roll (rode em animacao/ depois de plano.py): tabela por bloco do roteiro + Assets não usados + trechos só com preenchimento.
Uso: python resumo_webdoc_broll.py [--assets ../Assets] [--nome "Título do projeto no CapCut"] [--md RESUMO_WEBDOC.md]
Colunas: tempo | recurso (B-roll / animação / imagem / lista curta / título / só preenchimento) | arquivo·trecho·velocidade (se B-roll) | observação.
"""

import argparse, json, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("--assets", default="../Assets")
ap.add_argument("--nome", default="")
ap.add_argument("--md", default="RESUMO_WEBDOC.md")
a = ap.parse_args()
plano = json.load(open("plano.json"))
cenas = {c["id"]: c for c in json.load(open("src/scenes/cenas.json"))}
broll = json.load(open("src/scenes/broll.json")) if os.path.exists("src/scenes/broll.json") else []
fmt = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
jan = sorted(plano["janelas"].items(), key=lambda kv: kv[1][0])
linhas = []
so_fill = []
usados = set()
imgs_usadas = set()


def clipes_de(a0, a1):
    return [b for b in broll if a0 - 0.05 <= b["t_inicio"] < a1]


for k, (i, (t0, t1, tp)) in enumerate(jan):
    c = cenas.get(i, {})
    obs = ""
    arq = "—"
    if tp in ("broll", "vazio"):
        cl = clipes_de(t0, t1)
        cob = sum(b["t_fim"] - b["t_inicio"] for b in cl)
        dur = t1 - t0
        rec = "B-roll" if cl else "só preenchimento"
        arq = (
            "; ".join(
                f"{os.path.basename(b['arquivo'])} [{b['in']:.0f}–{b['out']:.0f}s] {b['velocidade']}x"
                for b in cl
            )
            or "—"
        )
        for b in cl:
            usados.add(os.path.basename(b["arquivo"]))
        vazio = dur - cob
        if cl and vazio > 3:
            obs = f"{vazio:.0f}s sem clipe (completar à mão)"
        if not cl:
            obs = "COMPLETAR À MÃO"
            so_fill.append((i, round(t0, 1), round(t1, 1)))
        elif vazio > 3:
            so_fill.append((i, round(t0 + cob, 1), round(t1, 1)))
        if tp == "broll" and c.get("rotulo"):
            obs += (
                (" · " if obs else "")
                + f"rótulo leve: {c['rotulo']}"
                + (f" ({c['data']})" if c.get("data") else "")
            )
    elif tp == "listacurta":
        cl = clipes_de(t0, t1)
        rec = "lista curta" + (" + B-roll nas pausas" if cl else "")
        arq = f"{c.get('total', '?')} itens: " + " · ".join(x["rotulo"] for x in c.get("itens", []))
        obs = c.get("titulo", "")
        if cl:
            arq += " || B-roll: " + "; ".join(
                f"{os.path.basename(b['arquivo'])} [{b['in']:.0f}–{b['out']:.0f}s] {b['velocidade']}x @{b['t_inicio']:.0f}s"
                for b in cl
            )
        for b in cl:
            usados.add(os.path.basename(b["arquivo"]))
    elif tp == "impacto":
        rec = "título de impacto"
        arq = " / ".join(c.get("linhas", []))
    else:
        tipos = [p["tipo"] for p in c.get("pecas", [])] if c.get("pecas") else []
        rec = "imagem/animação" if any(t in ("tela",) for t in tipos) else "animação"
        for p in c.get("pecas", []):
            if p["tipo"] == "tela":
                imgs_usadas.add(p["props"]["img"])
                arq = f"Tela: {p['props']['img']}"
                obs = p["props"].get("legenda", "")
        if tp == "grafo":
            arq = " + ".join(x["img"] for x in c.get("itens", []) if x.get("img"))[:90]
        if tp == "tempo":
            rec = "linha do tempo"
        if not arq or arq == "—":
            arq = ", ".join(tipos)
    linhas.append(f"| {fmt(t0)}–{fmt(t1)} | {rec} | {arq} | {obs} |")
tab = ["| tempo | recurso | arquivo · trecho · velocidade | observação |", "|---|---|---|---|"] + linhas
# Assets não usados
todos = sorted(
    f for f in os.listdir(a.assets) if not f.startswith(".") and os.path.isfile(os.path.join(a.assets, f))
)
usados_img = {n for n in imgs_usadas}
for c in cenas.values():
    for it in c.get("itens", []) if isinstance(c.get("itens"), list) else []:
        if isinstance(it, dict) and it.get("img"):
            usados_img.add(it["img"])


def slug(f):
    return re.sub(r"[^a-z0-9]+", "_", os.path.splitext(f)[0].lower()).strip("_")[:40]


nao = []
for f in todos:
    if f in usados:
        continue
    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and (f"tela_asset_{slug(f)}" in usados_img):
        continue
    nao.append(f)
txt = ["# Resumo — Webdoc com B-roll" + (f" · projeto CapCut: «{a.nome}»" if a.nome else ""), ""] + tab
txt += [
    "",
    "## Assets NÃO usados (diga o motivo no relatório: baixa qualidade, repetido, fora do roteiro…)",
    "",
] + ([f"- {f}" for f in nao] or ["- (todos usados)"])
txt += ["", "## Trechos só com preenchimento (você completa à mão)", ""] + (
    [f"- {i}: {fmt(x)}–{fmt(y)} ({y - x:.0f}s)" for i, x, y in so_fill] or ["- (nenhum)"]
)
if a.nome:
    txt += ["", f"Projeto no CapCut: «{a.nome}»"]
open(a.md, "w").write("\n".join(txt) + "\n")
print("\n".join(txt))
