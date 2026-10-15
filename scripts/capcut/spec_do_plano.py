#!/usr/bin/env python3
"""Gera o spec.json do montar_draft.py a partir do projeto Motion Canvas (plano_dados.py BROLL) + voz + overlay.
Uso (na pasta animacao/): python spec_do_plano.py --nome "Título do vídeo" --voz ../pronto.wav --overlay output/project.mov [--capa frame.png] [--saida capcut_spec.json]
Depois: python montar_draft.py capcut_spec.json"""

import argparse, importlib, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("--nome", required=True)
ap.add_argument("--voz", required=True)
ap.add_argument("--overlay", default=None)
ap.add_argument("--capa", default=None)
ap.add_argument("--saida", default="capcut_spec.json")
ap.add_argument("--preenchimento", default=None)
ap.add_argument("--sem-marca", action="store_true", help="não injeta música/avatar/propaganda/vinheta final")
a = ap.parse_args()
sys.path.insert(0, os.getcwd())
pd = importlib.import_module("plano_dados")
broll = getattr(pd, "BROLL", [])
spec = dict(
    nome=a.nome,
    voz=os.path.abspath(a.voz),
    overlay=os.path.abspath(a.overlay) if a.overlay else None,
    capa_frame=os.path.abspath(a.capa) if a.capa else None,
    clipes=[
        dict(arquivo=os.path.abspath(f), **{"in": i0, "out": i1}, velocidade=v, t_inicio=t, item=it)
        for it, f, i0, i1, v, t in sorted(broll, key=lambda b: b[5])
    ],
)
if os.path.exists("plano.json"):
    pj = json.load(open("plano.json"))
    spec["janelas"] = pj.get("janelas")
    spec["menu_duracao"] = pj.get("menu_duracao", 3.7)
# OVERLAY RECORTADO: o overlay só existe nas janelas SEM B-roll (o que o usuário fazia à mão: cortar o overlay em cima dos clipes).
# Assim nenhuma animação vaza sobre o B-roll mesmo com erro de alguns milissegundos, e cada janela é um bloco fácil de apagar.
dur = (json.load(open("plano.json")).get("duracao") if os.path.exists("plano.json") else None) or max(
    (c["t_inicio"] + (c["out"] - c["in"]) / c["velocidade"] for c in spec["clipes"]), default=0
)
ocup = sorted((c["t_inicio"], c["t_inicio"] + (c["out"] - c["in"]) / c["velocidade"]) for c in spec["clipes"])
segs, cur = [], 0.0
for a_, b_ in ocup:
    if a_ - cur > 0.05:
        segs.append([round(cur, 3), round(a_, 3)])
    cur = max(cur, b_)
if dur - cur > 0.05:
    segs.append([round(cur, 3), round(dur, 3)])
# Webdoc com B-roll: rótulos LEVES sobre o vídeo (plano.json "overlay_leve") também ficam no overlay (união com as janelas sem clipe)
leve = (json.load(open("plano.json")).get("overlay_leve") if os.path.exists("plano.json") else None) or []
if leve:
    spec["overlay_leve"] = leve
    uni = sorted([list(x) for x in segs] + [list(x) for x in leve])
    mer = []
    for x0, x1 in uni:
        if mer and x0 <= mer[-1][1] + 0.05:
            mer[-1][1] = max(mer[-1][1], x1)
        else:
            mer.append([x0, x1])
    segs = mer
spec["overlay_segmentos"] = segs
# ALTERNATIVAS: se o usuário apagar uma animação, estende-se o clipe anterior (o que ele fazia à mão); tabela em ALTERNATIVAS_BROLL.md
alt = []
import subprocess


def dur_arq(f):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


jan = spec.get("janelas") or {}
for k, (j0, j1, tp) in sorted(jan.items(), key=lambda kv: kv[1][0]):
    if tp != "item":
        continue
    ini = j0 + spec.get("menu_duracao", 3.7)
    for g0, g1 in segs:
        a_, b_ = max(g0, ini), min(g1, j1)
        if b_ - a_ < 2.0:
            continue
        prev = [
            c
            for c in spec["clipes"]
            if c["item"] == k and c["t_inicio"] + (c["out"] - c["in"]) / c["velocidade"] <= a_ + 0.05
        ]
        if not prev:
            continue
        c = max(prev, key=lambda c: c["t_inicio"])
        fim_src = c["out"] + (b_ - a_) * c["velocidade"]
        ok = fim_src <= dur_arq(c["arquivo"]) + 0.05
        alt.append(
            dict(
                item=k,
                janela=[round(a_, 1), round(b_, 1)],
                estender=os.path.basename(c["arquivo"]),
                src_de=c["out"],
                src_ate=round(fim_src, 1),
                velocidade=c["velocidade"],
                cabe=ok,
            )
        )
spec["alternativas"] = alt
if alt:
    linhas = [
        "# Se apagar a animação, estenda o B-roll (corte o overlay na janela e puxe a borda do clipe anterior)",
        "",
        "| item | janela (s) | estender clipe | fonte (s) | vel. | cabe no arquivo |",
        "|---|---|---|---|---|---|",
    ]
    linhas += [
        f"| {x['item']} | {x['janela'][0]}–{x['janela'][1]} | {x['estender']} | {x['src_de']}→{x['src_ate']} | {x['velocidade']}x | {'sim' if x['cabe'] else 'NÃO (trocar fonte)'} |"
        for x in alt
    ]
    open("ALTERNATIVAS_BROLL.md", "w").write("\n".join(linhas) + "\n")
if a.preenchimento:
    spec["preenchimento"] = os.path.abspath(a.preenchimento)
# Marca (música, avatar, propaganda, vinheta final): ligada quando o plano define PROPAGANDA_APOS e o pacote privado existe
if os.path.exists("plano.json"):
    _pj = json.load(open("plano.json"))
    if _pj.get("propaganda_t") is not None and not a.sem_marca:
        spec["marca"] = dict(
            propaganda_t=_pj["propaganda_t"],
            propaganda_retoma=_pj.get("propaganda_retoma", _pj["propaganda_t"]),
            final_antes_do_fim=_pj.get("final_antes_do_fim", 6.9),
        )
json.dump(spec, open(a.saida, "w"), ensure_ascii=False, indent=1)
print(f"{len(spec['clipes'])} clipes -> {a.saida}")
