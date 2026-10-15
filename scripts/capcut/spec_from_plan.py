#!/usr/bin/env python3
"""Gera o spec.json do build_draft.py a partir do projeto Motion Canvas (plano_dados.py BROLL) + voz + overlay.
Uso (na pasta animacao/): python spec_from_plan.py --name "Título do vídeo" --voice ../pronto.wav --overlay output/project.mov [--cover frame.png] [--output capcut_spec.json]
Depois: python build_draft.py capcut_spec.json"""

import argparse, importlib, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("--name", "--nome", required=True)
ap.add_argument("--voice", "--voz", required=True)
ap.add_argument("--overlay", default=None)
ap.add_argument("--cover", "--capa", default=None)
ap.add_argument("--output", "--saida", default="capcut_spec.json")
ap.add_argument("--filler", "--preenchimento", default=None)
ap.add_argument("--no-branding", "--sem-marca", action="store_true", help="não injeta música/avatar/propaganda/vinheta final")
a = ap.parse_args()
sys.path.insert(0, os.getcwd())
plan_data = importlib.import_module("plano_dados")
broll = getattr(plan_data, "BROLL", [])
spec = dict(
    nome=a.name,
    voz=os.path.abspath(a.voice),
    overlay=os.path.abspath(a.overlay) if a.overlay else None,
    capa_frame=os.path.abspath(a.cover) if a.cover else None,
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
duration = (json.load(open("plano.json")).get("duracao") if os.path.exists("plano.json") else None) or max(
    (clip["t_inicio"] + (clip["out"] - clip["in"]) / clip["velocidade"] for clip in spec["clipes"]), default=0
)
occupied = sorted((clip["t_inicio"], clip["t_inicio"] + (clip["out"] - clip["in"]) / clip["velocidade"]) for clip in spec["clipes"])
segments, cursor = [], 0.0
for a_, b_ in occupied:
    if a_ - cursor > 0.05:
        segments.append([round(cursor, 3), round(a_, 3)])
    cursor = max(cursor, b_)
if duration - cursor > 0.05:
    segments.append([round(cursor, 3), round(duration, 3)])
# Webdoc com B-roll: rótulos LEVES sobre o vídeo (plano.json "overlay_leve") também ficam no overlay (união com as janelas sem clipe)
light_overlay = (json.load(open("plano.json")).get("overlay_leve") if os.path.exists("plano.json") else None) or []
if light_overlay:
    spec["overlay_leve"] = light_overlay
    union = sorted([list(x) for x in segments] + [list(x) for x in light_overlay])
    merged = []
    for x0, x1 in union:
        if merged and x0 <= merged[-1][1] + 0.05:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    segments = merged
spec["overlay_segmentos"] = segments
# ALTERNATIVAS: se o usuário apagar uma animação, estende-se o clipe anterior (o que ele fazia à mão); tabela em ALTERNATIVAS_BROLL.md
alternatives = []
import subprocess


def file_duration(f):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


windows = spec.get("janelas") or {}
for key, (start, end, type) in sorted(windows.items(), key=lambda kv: kv[1][0]):
    if type != "item":
        continue
    start = start + spec.get("menu_duracao", 3.7)
    for gap_start, gap_end in segments:
        a_, b_ = max(gap_start, start), min(gap_end, end)
        if b_ - a_ < 2.0:
            continue
        prev = [
            clip
            for clip in spec["clipes"]
            if clip["item"] == key and clip["t_inicio"] + (clip["out"] - clip["in"]) / clip["velocidade"] <= a_ + 0.05
        ]
        if not prev:
            continue
        clip = max(prev, key=lambda clip: clip["t_inicio"])
        src_end = clip["out"] + (b_ - a_) * clip["velocidade"]
        fits = src_end <= file_duration(clip["arquivo"]) + 0.05
        alternatives.append(
            dict(
                item=key,
                janela=[round(a_, 1), round(b_, 1)],
                estender=os.path.basename(clip["arquivo"]),
                src_de=clip["out"],
                src_ate=round(src_end, 1),
                velocidade=clip["velocidade"],
                cabe=fits,
            )
        )
spec["alternativas"] = alternatives
if alternatives:
    lines = [
        "# Se apagar a animação, estenda o B-roll (corte o overlay na janela e puxe a borda do clipe anterior)",
        "",
        "| item | janela (s) | estender clipe | fonte (s) | vel. | cabe no arquivo |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {x['item']} | {x['janela'][0]}–{x['janela'][1]} | {x['estender']} | {x['src_de']}→{x['src_ate']} | {x['velocidade']}x | {'sim' if x['cabe'] else 'NÃO (trocar fonte)'} |"
        for x in alternatives
    ]
    open("ALTERNATIVAS_BROLL.md", "w").write("\n".join(lines) + "\n")
if a.filler:
    spec["preenchimento"] = os.path.abspath(a.filler)
# Marca (música, avatar, propaganda, vinheta final): ligada quando o plano define PROPAGANDA_APOS e o pacote privado existe
if os.path.exists("plano.json"):
    _pj = json.load(open("plano.json"))
    if _pj.get("propaganda_t") is not None and not a.no_branding:
        spec["marca"] = dict(
            propaganda_t=_pj["propaganda_t"],
            propaganda_retoma=_pj.get("propaganda_retoma", _pj["propaganda_t"]),
            final_antes_do_fim=_pj.get("final_antes_do_fim", 6.9),
        )
json.dump(spec, open(a.output, "w"), ensure_ascii=False, indent=1)
print(f"{len(spec['clipes'])} clipes -> {a.output}")
