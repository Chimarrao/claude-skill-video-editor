#!/usr/bin/env python3
"""Lista (somente leitura) as trilhas/segmentos de um draft do CapCut: tempo, fonte, velocidade, escala/posição, volume, tipo e nome do material.
Uso: dump_draft.py <pasta_do_draft | draft_info.json> [--materials]   (--materials: lista também compound clips, áudios, loudness)
"""

import json, os, sys

a = sys.argv[1]
p = os.path.join(a, "draft_info.json") if os.path.isdir(a) else a
j = json.load(open(p))
M = {}
for k in ("videos", "audios", "texts", "stickers", "drafts", "effects"):
    for m in j["materials"].get(k, []):
        M[m["id"]] = (k, m)
display_name = (
    lambda m: os.path.basename((m.get("path") or "").replace("\\", "/"))
    or m.get("material_name")
    or m.get("name")
    or m.get("type")
    or "?"
)
print(
    f"{j.get('name')} · {j['duration'] / 1e6:.1f}s · canvas {j.get('canvas_config', {}).get('width')}x{j.get('canvas_config', {}).get('height')}"
)
for ti, t in enumerate(j["tracks"]):
    print(f"\n=== trilha {ti} {t['type']} nome={t.get('name')!r} segs={len(t['segments'])}")
    for s in t["segments"]:
        k, m = M.get(s["material_id"], ("?", {}))
        tr = s["target_timerange"]
        sr = s.get("source_timerange") or {}
        cl = s.get("clip") or {}
        sc = cl.get("scale") or {}
        tf = cl.get("transform") or {}
        print(
            f"  {tr['start'] / 1e6:8.2f}-{(tr['start'] + tr['duration']) / 1e6:8.2f} ({tr['duration'] / 1e6:6.2f}s) src {sr.get('start', 0) / 1e6:7.2f}+{sr.get('duration', 0) / 1e6:6.2f} v={s.get('speed')} vol={s.get('volume')} esc=({sc.get('x')},{sc.get('y')}) pos=({tf.get('x')},{tf.get('y')}) [{k}] {display_name(m)[:60]} {m.get('type', '')}"
        )
if "--materials" in sys.argv or "--materiais" in sys.argv:
    print("\n--- materiais compostos (drafts) ---")
    for d in j["materials"].get("drafts", []):
        print(d.get("id"), d.get("name"), round(d.get("duration", 0) / 1e6, 1))
    print(
        "--- loudnesses ---",
        [
            (l.get("id")[:6], l.get("target_loudness"), l.get("enable"))
            for l in j["materials"].get("loudnesses", [])
        ][:12],
    )
    print("--- audios ---")
    for au in j["materials"].get("audios", []):
        print(au.get("id")[:8], au.get("name"), au.get("type"), round(au.get("duration", 0) / 1e6, 1))
