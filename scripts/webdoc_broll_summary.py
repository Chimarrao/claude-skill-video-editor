#!/usr/bin/env python3
"""RESUMO FINAL do Webdoc com B-roll (rode em animacao/ depois de plan.py): tabela por bloco do roteiro + Assets não usados + trechos só com preenchimento.
Uso: python webdoc_broll_summary.py [--assets ../Assets] [--name "Título do projeto no CapCut"] [--md SUMMARY_WEBDOC.md]
Colunas: tempo | recurso (B-roll / animação / imagem / lista curta / título / só preenchimento) | arquivo·trecho·velocidade (se B-roll) | observação.
"""

import argparse, json, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("--assets", default="../Assets")
ap.add_argument("--name", default="")
ap.add_argument("--md", default="SUMMARY_WEBDOC.md")
args = ap.parse_args()
plan = json.load(open("plan.json"))
scenes = {c["id"]: c for c in json.load(open("src/scenes/scenes.json"))}
broll = json.load(open("src/scenes/broll.json")) if os.path.exists("src/scenes/broll.json") else []
fmt = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
windows = sorted(plan["windows"].items(), key=lambda kv: kv[1][0])
rows = []
filler_only = []
used = set()
used_images = set()


def clips_in(start, end):
    return [b for b in broll if start - 0.05 <= b["t_start"] < end]


for k, (i, (t0, t1, tp)) in enumerate(windows):
    c = scenes.get(i, {})
    note = ""
    file = "—"
    if tp in ("broll", "empty"):
        cl = clips_in(t0, t1)
        coverage = sum(b["t_end"] - b["t_start"] for b in cl)
        duration = t1 - t0
        resource = "B-roll" if cl else "só preenchimento"
        file = (
            "; ".join(
                f"{os.path.basename(b['file'])} [{b['in']:.0f}–{b['out']:.0f}s] {b['speed']}x"
                for b in cl
            )
            or "—"
        )
        for b in cl:
            used.add(os.path.basename(b["file"]))
        empty_gap = duration - coverage
        if cl and empty_gap > 3:
            note = f"{empty_gap:.0f}s sem clipe (completar à mão)"
        if not cl:
            note = "COMPLETAR À MÃO"
            filler_only.append((i, round(t0, 1), round(t1, 1)))
        elif empty_gap > 3:
            filler_only.append((i, round(t0 + coverage, 1), round(t1, 1)))
        if tp == "broll" and c.get("label"):
            note += (
                (" · " if note else "")
                + f"rótulo leve: {c['label']}"
                + (f" ({c['data']})" if c.get("data") else "")
            )
    elif tp == "shortlist":
        cl = clips_in(t0, t1)
        resource = "lista curta" + (" + B-roll nas pausas" if cl else "")
        file = f"{c.get('total', '?')} itens: " + " · ".join(x["label"] for x in c.get("items", []))
        note = c.get("title", "")
        if cl:
            file += " || B-roll: " + "; ".join(
                f"{os.path.basename(b['file'])} [{b['in']:.0f}–{b['out']:.0f}s] {b['speed']}x @{b['t_start']:.0f}s"
                for b in cl
            )
        for b in cl:
            used.add(os.path.basename(b["file"]))
    elif tp == "impact":
        resource = "título de impacto"
        file = " / ".join(c.get("lines", []))
    else:
        types = [p["kind"] for p in c.get("pieces", [])] if c.get("pieces") else []
        resource = "imagem/animação" if any(t in ("screen",) for t in types) else "animação"
        for p in c.get("pieces", []):
            if p["kind"] == "screen":
                used_images.add(p["props"]["img"])
                file = f"Tela: {p['props']['img']}"
                note = p["props"].get("caption", "")
        if tp == "graph":
            file = " + ".join(x["img"] for x in c.get("items", []) if x.get("img"))[:90]
        if tp == "timeline":
            resource = "linha do tempo"
        if not file or file == "—":
            file = ", ".join(types)
    rows.append(f"| {fmt(t0)}–{fmt(t1)} | {resource} | {file} | {note} |")
table = ["| tempo | recurso | arquivo · trecho · velocidade | observação |", "|---|---|---|---|"] + rows
# Assets não usados
all_files = sorted(
    f for f in os.listdir(args.assets) if not f.startswith(".") and os.path.isfile(os.path.join(args.assets, f))
)
used_images_set = {n for n in used_images}
for c in scenes.values():
    for it in c.get("items", []) if isinstance(c.get("items"), list) else []:
        if isinstance(it, dict) and it.get("img"):
            used_images_set.add(it["img"])


def slug(f):
    return re.sub(r"[^a-z0-9]+", "_", os.path.splitext(f)[0].lower()).strip("_")[:40]


unused = []
for f in all_files:
    if f in used:
        continue
    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and (f"tela_asset_{slug(f)}" in used_images_set):
        continue
    unused.append(f)
text = ["# Resumo — Webdoc com B-roll" + (f" · projeto CapCut: «{args.name}»" if args.name else ""), ""] + table
text += [
    "",
    "## Assets NÃO usados (diga o motivo no relatório: baixa qualidade, repetido, fora do roteiro…)",
    "",
] + ([f"- {f}" for f in unused] or ["- (todos usados)"])
text += ["", "## Trechos só com preenchimento (você completa à mão)", ""] + (
    [f"- {i}: {fmt(x)}–{fmt(y)} ({y - x:.0f}s)" for i, x, y in filler_only] or ["- (nenhum)"]
)
if args.name:
    text += ["", f"Projeto no CapCut: «{args.name}»"]
open(args.md, "w").write("\n".join(text) + "\n")
print("\n".join(text))
