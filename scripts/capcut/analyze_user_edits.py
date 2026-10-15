#!/usr/bin/env python3
"""Lê (SEM EDITAR) o draft do CapCut depois que o usuário mexeu e compara com o que o skill gerou (capcut_spec.json).
Objetivo: aprender o gosto do usuário — o que ele CORTOU (animações removidas), ESTICOU (B-roll estendido/lentidão), TROCOU (outra fonte),
ACRESCENTOU (logos/fotos/vídeos novos, posição/escala), AMPLIOU (zoom no overlay) — para refinar regras e planos futuros.
Uso:  python analyze_user_edits.py <pasta_do_draft | draft_info.json> [--spec animacao/capcut_spec.json] [--md output.md] [--json output.json]
Dica: copie o draft para /tmp antes (o CapCut regrava os arquivos); o script só abre arquivos para leitura.
Tempo: tudo é convertido para o TEMPO ORIGINAL do plano (descontando vinhetas/inserções do usuário) usando os trechos da narração.
"""

import argparse, json, os, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("draft")
ap.add_argument("--spec", default="capcut_spec.json")
ap.add_argument("--md")
ap.add_argument("--json")
a = ap.parse_args()
p = Path(a.draft)
p = p / "draft_info.json" if p.is_dir() else p
j = json.load(open(p))
spec = json.load(open(a.spec)) if os.path.exists(a.spec) else {}
us_to_s = lambda us: us / 1e6
materials = {m["id"]: m for k in ("videos", "audios") for m in j["materials"].get(k, [])}
basename_of = (
    lambda m: os.path.basename((m.get("path") or "").replace("\\", "/"))
    or m.get("material_name")
    or m.get("name")
    or "?"
)
tracks = [(t.get("name") or "", t["type"], t["segments"]) for t in j["tracks"]]
# --- mapa de tempo usuário -> original, pela narração (voice_narration.wav) ---
narration = [
    (
        us_to_s(s["target_timerange"]["start"]),
        us_to_s(s["target_timerange"]["start"] + s["target_timerange"]["duration"]),
        us_to_s(s["source_timerange"]["start"]),
    )
    for n, ty, segs in tracks
    if ty == "audio"
    for s in segs
    if "voice_narration" in basename_of(materials.get(s["material_id"], {}))
]
narration.sort()


def to_original(t):
    """Converte um tempo da timeline editada pelo usuário para o tempo original da narração (`None` se cair numa inserção dele)."""
    for start, t1, s0 in narration:
        if start - 1e-3 <= t <= t1 + 1e-3:
            return round(s0 + (t - start), 3)
    return None


insertions = []  # inserções do usuário (vãos entre trechos da narração)
for (a0, a1, s0), (b0, b1, s1) in zip(narration, narration[1:]):
    if b0 - a1 > 0.5 or abs((b0 - s1) - (a0 - s0)) > 0.5:
        insertions.append(
            dict(
                in_user_time=[round(a1, 2), round(b0, 2)],
                duration=round(b0 - a1, 2),
                narration_skipped=round(s1 - (s0 + a1 - a0), 2),
            )
        )
expected_clips = {}  # (arquivo, in, out) planejados
for c in spec.get("clips", []):
    expected_clips.setdefault(os.path.basename(c["file"]), []).append(c)
report = dict(
    insertions=insertions,
    clips=[],
    logos_photos=[],
    overlay_kept=[],
    overlay_removed=[],
    overlay_zoom=[],
    tracks_extras=[],
    videos_new=[],
)
for name, ty, segs in tracks:
    if ty != "video":
        if name not in ("narration", "") or len(segs):
            report["tracks_extras"].append(
                dict(
                    kind=ty,
                    name=name,
                    segments=len(segs),
                    files=sorted({basename_of(materials.get(s["material_id"], {})) for s in segs})[:4],
                )
            )
        continue
    for s in segs:
        m = materials.get(s["material_id"], {})
        basename = basename_of(m)
        start = us_to_s(s["target_timerange"]["start"])
        duration = us_to_s(s["target_timerange"]["duration"])
        orig_start = to_original(start)
        orig_end = to_original(start + duration - 1e-3)
        clip_info = s.get("clip") or {}
        scale = (clip_info.get("scale") or {}).get("x")
        transform = clip_info.get("transform") or {}
        src_range = s.get("source_timerange") or {}
        speed = s.get("speed")
        if name == "overlay" or "project.mov" in basename:
            src_start = us_to_s(src_range.get("start", 0))
            report["overlay_kept"].append([round(src_start, 2), round(src_start + duration, 2)])
            if scale and abs(scale - 1) > 0.02:
                report["overlay_zoom"].append(
                    dict(
                        overlay=[round(src_start, 2), round(src_start + duration, 2)],
                        scale=round(scale, 2),
                        pos=[round(transform.get("x", 0), 3), round(transform.get("y", 0), 3)],
                    )
                )
            continue
        if name == "filler" or "background_fill" in basename:
            continue
        if m.get("type") == "photo" or basename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")):
            report["logos_photos"].append(
                dict(
                    file=basename,
                    time_original=[orig_start, orig_end] if orig_start is not None else None,
                    duration=round(duration, 2),
                    scale=round(scale or 1, 3),
                    pos=[round(transform.get("x", 0), 3), round(transform.get("y", 0), 3)],
                )
            )
            continue
        if basename.startswith("Minhas ") or "predefini" in basename or orig_start is None:
            report["tracks_extras"].append(
                dict(
                    kind="video",
                    name=name or "(sem nome)",
                    file=basename,
                    in_user_time=[round(start, 1), round(start + duration, 1)],
                    scale=round(scale or 1, 2),
                    pos=[round(transform.get("x", 0), 2), round(transform.get("y", 0), 2)],
                )
            )
            continue
        expected = expected_clips.get(basename, [])
        matched = next((c for c in expected if abs(c["in"] - us_to_s(src_range.get("start", 0))) < 0.6), None)
        if not expected:
            report["videos_new"].append(
                dict(
                    file=basename,
                    time_original=[orig_start, round(orig_start + duration, 2)],
                    source=[
                        round(us_to_s(src_range.get("start", 0)), 1),
                        round(us_to_s(src_range.get("start", 0) + src_range.get("duration", 0)), 1),
                    ],
                    speed=round(speed or 1, 2),
                )
            )
            continue
        report["clips"].append(
            dict(
                file=basename,
                time_original=[orig_start, round(orig_start + duration, 2)],
                source=[
                    round(us_to_s(src_range.get("start", 0)), 2),
                    round(us_to_s(src_range.get("start", 0) + src_range.get("duration", 0)), 2),
                ],
                speed=round(speed or 1, 2),
                planned=(
                    dict(
                        t=[
                            round(matched["t_start"], 1),
                            round(matched["t_start"] + (matched["out"] - matched["in"]) / matched["speed"], 1),
                        ],
                        speed=matched["speed"],
                    )
                    if matched
                    else None
                ),
                change=(
                    "equal"
                    if matched
                    and abs(duration - (matched["out"] - matched["in"]) / matched["speed"]) < 0.3
                    and abs((speed or 1) - matched["speed"]) < 0.05
                    else ("ESTICADO/ENCURTADO" if matched else "TROCA DE TRECHO/NOVO")
                ),
            )
        )
report["overlay_kept"].sort()
cursor = 0.0
overlay_duration = max((x[1] for x in report["overlay_kept"]), default=0)
for x0, x1 in report["overlay_kept"]:
    if x0 - cursor > 0.3:
        report["overlay_removed"].append([round(cursor, 2), round(x0, 2)])
    cursor = max(cursor, x1)
# overlay_removed que o spec já deixava sem overlay (janelas de clipe) não é "corte do usuário": filtra pelos segmentos planejados
plan = spec.get("overlay_segments")
if plan:
    filtered = []
    for x0, x1 in report["overlay_removed"]:
        for p0, p1 in plan:  # só o que cai em janela que EXISTIA no plano
            lo, hi = max(x0, p0), min(x1, p1)
            if hi - lo > 0.3:
                filtered.append([round(lo, 2), round(hi, 2)])
    report["overlay_removed_vs_plan"] = filtered
# --- relatório ---
L = [
    f"# Edição do usuário — {j.get('name')}",
    "",
    (
        f"- duração no CapCut: {us_to_s(j['duration']):.1f}s · narração planejada: {spec.get('windows') and max(v[1] for v in spec['windows'].values()):.1f}s"
        if spec.get("windows")
        else f"- duração no CapCut: {us_to_s(j['duration']):.1f}s"
    ),
]
for i_ in insertions:
    L.append(
        f"- INSERÇÃO do usuário em {i_['in_user_time']} ({i_['duration']}s; narração pulada {i_['narration_skipped']}s) — todos os tempos abaixo já descontam isso"
    )
L += ["", "## Overlay (animações) — CORTADO pelo usuário (tempo original)", ""]
for x in report.get("overlay_removed_vs_plan", report["overlay_removed"]):
    item_name = next((k for k, v in (spec.get("windows") or {}).items() if v[0] <= x[0] < v[1]), "")
    L.append(f"- {x[0]}–{x[1]}s ({x[1]-x[0]:.1f}s) {item_name}")
L += ["", "## Overlay AMPLIADO (zoom manual)", ""] + [
    f"- {z['overlay']} escala {z['scale']}× pos {z['pos']}" for z in report["overlay_zoom"]
]
L += ["", "## Logos/fotos que o usuário acrescentou na trilha de clipes", ""] + [
    f"- {l['file']} em {l['time_original']} ({l['duration']}s) escala {l['scale']} pos {l['pos']}"
    for l in report["logos_photos"]
]
L += ["", "## B-roll alterado", ""] + [
    f"- {c['change']}: {c['file'][:50]} {c['time_original']} fonte {c['source']} {c['speed']}x"
    + (f" (plano {c['planned']['t']} {c['planned']['speed']}x)" if c["planned"] else "")
    for c in report["clips"]
    if c["change"] != "equal"
]
L += ["", "## Vídeos novos (fora do plano)", ""] + [
    f"- {v['file']} em {v['time_original']} fonte {v['source']} {v['speed']}x"
    for v in report["videos_new"]
]
L += ["", "## Faixas/vinhetas extras do usuário", ""] + [f"- {f}" for f in report["tracks_extras"]]
md = "\n".join(L)
if a.md:
    open(a.md, "w").write(md)
if a.json:
    json.dump(report, open(a.json, "w"), ensure_ascii=False, indent=1)
print(md)
