#!/usr/bin/env python3
"""Gera o spec.json do build_draft.py a partir do projeto Motion Canvas (plan_data.py BROLL) + voz + overlay.
Uso (na pasta animacao/): python spec_from_plan.py --name "Título do vídeo" --voice ../pronto.wav --overlay output/project.mov [--cover frame.png] [--output capcut_spec.json]
Depois: python build_draft.py capcut_spec.json"""

import argparse, importlib, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--voice", required=True)
ap.add_argument("--overlay", default=None)
ap.add_argument("--cover", default=None)
ap.add_argument("--output", default="capcut_spec.json")
ap.add_argument("--filler", default=None)
ap.add_argument("--no-branding", action="store_true", help="não injeta música/avatar/propaganda/vinheta final")
a = ap.parse_args()
sys.path.insert(0, os.getcwd())
plan_data = importlib.import_module("plan_data")
broll = getattr(plan_data, "BROLL", [])
spec = dict(
    name=a.name,
    voice=os.path.abspath(a.voice),
    overlay=os.path.abspath(a.overlay) if a.overlay else None,
    cover_frame=os.path.abspath(a.cover) if a.cover else None,
    clips=[
        dict(file=os.path.abspath(f), **{"in": i0, "out": i1}, speed=v, t_start=t, item=it)
        for it, f, i0, i1, v, t in sorted(broll, key=lambda b: b[5])
    ],
)
if os.path.exists("plan.json"):
    pj = json.load(open("plan.json"))
    spec["windows"] = pj.get("windows")
    spec["menu_duration"] = pj.get("menu_duration", 3.7)
# OVERLAY RECORTADO: o overlay só existe nas janelas SEM B-roll (o que o usuário fazia à mão: cortar o overlay em cima dos clipes).
# Assim nenhuma animação vaza sobre o B-roll mesmo com erro de alguns milissegundos, e cada janela é um bloco fácil de apagar.
duration = (json.load(open("plan.json")).get("duration") if os.path.exists("plan.json") else None) or max(
    (clip["t_start"] + (clip["out"] - clip["in"]) / clip["speed"] for clip in spec["clips"]), default=0
)
occupied = sorted((clip["t_start"], clip["t_start"] + (clip["out"] - clip["in"]) / clip["speed"]) for clip in spec["clips"])
segments, cursor = [], 0.0
for a_, b_ in occupied:
    if a_ - cursor > 0.05:
        segments.append([round(cursor, 3), round(a_, 3)])
    cursor = max(cursor, b_)
if duration - cursor > 0.05:
    segments.append([round(cursor, 3), round(duration, 3)])
# Webdoc com B-roll: rótulos LEVES sobre o vídeo (plan.json "overlay_light") também ficam no overlay (união com as janelas sem clipe)
light_overlay = (json.load(open("plan.json")).get("overlay_light") if os.path.exists("plan.json") else None) or []
if light_overlay:
    spec["overlay_light"] = light_overlay
    union = sorted([list(x) for x in segments] + [list(x) for x in light_overlay])
    merged = []
    for x0, x1 in union:
        if merged and x0 <= merged[-1][1] + 0.05:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    segments = merged
# SEM FLASHES: pedaço de overlay muito curto (sobra entre dois clipes, cauda de entrada/saída de uma animação) aparece como um "piscar" na tela.
# O usuário sempre apaga esses takes à mão: não os gere. Mínimo 1,5 s (os rótulos leves sobre B-roll duram >= 3 s).
MIN_OVERLAY_SEGMENT = 1.5
dropped = [x for x in segments if x[1] - x[0] < MIN_OVERLAY_SEGMENT]
segments = [x for x in segments if x[1] - x[0] >= MIN_OVERLAY_SEGMENT]
if dropped:
    print(f"overlay: {len(dropped)} pedaço(s) < {MIN_OVERLAY_SEGMENT}s descartado(s) (piscar): " + ", ".join(f"{x[0]:.1f}-{x[1]:.1f}" for x in dropped))
spec["overlay_segments"] = segments
# ALTERNATIVAS: se o usuário apagar uma animação, estende-se o clipe anterior (o que ele fazia à mão); tabela em ALTERNATIVES_BROLL.md
alternatives = []
import subprocess


def file_duration(f):
    """Duração do arquivo em segundos (0 se o ffprobe não responder)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


windows = spec.get("windows") or {}
for key, (start, end, type) in sorted(windows.items(), key=lambda kv: kv[1][0]):
    if type != "item":
        continue
    start = start + spec.get("menu_duration", 3.7)
    for gap_start, gap_end in segments:
        a_, b_ = max(gap_start, start), min(gap_end, end)
        if b_ - a_ < 2.0:
            continue
        prev = [
            clip
            for clip in spec["clips"]
            if clip["item"] == key and clip["t_start"] + (clip["out"] - clip["in"]) / clip["speed"] <= a_ + 0.05
        ]
        if not prev:
            continue
        clip = max(prev, key=lambda clip: clip["t_start"])
        src_end = clip["out"] + (b_ - a_) * clip["speed"]
        fits = src_end <= file_duration(clip["file"]) + 0.05
        alternatives.append(
            dict(
                item=key,
                window=[round(a_, 1), round(b_, 1)],
                extend=os.path.basename(clip["file"]),
                src_from=clip["out"],
                src_until=round(src_end, 1),
                speed=clip["speed"],
                fits=fits,
            )
        )
spec["alternatives"] = alternatives
if alternatives:
    lines = [
        "# Se apagar a animação, estenda o B-roll (corte o overlay na janela e puxe a borda do clipe anterior)",
        "",
        "| item | janela (s) | estender clipe | fonte (s) | vel. | cabe no arquivo |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {x['item']} | {x['window'][0]}–{x['window'][1]} | {x['extend']} | {x['src_from']}→{x['src_until']} | {x['speed']}x | {'sim' if x['fits'] else 'NÃO (trocar fonte)'} |"
        for x in alternatives
    ]
    open("ALTERNATIVES_BROLL.md", "w").write("\n".join(lines) + "\n")
if a.filler:
    spec["filler"] = os.path.abspath(a.filler)
# Marca (música, avatar, propaganda, vinheta final): ligada quando o plano define PROMO_AFTER e o pacote privado existe
if os.path.exists("plan.json"):
    _pj = json.load(open("plan.json"))
    if _pj.get("promo_t") is not None and not a.no_branding:
        spec["brand"] = dict(
            promo_t=_pj["promo_t"],
            promo_resume=_pj.get("promo_resume", _pj["promo_t"]),
            final_before_end=_pj.get("final_before_end", 6.9),
        )
json.dump(spec, open(a.output, "w"), ensure_ascii=False, indent=1)
print(f"{len(spec['clips'])} clipes -> {a.output}")
