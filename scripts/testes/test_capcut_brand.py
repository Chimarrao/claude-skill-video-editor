#!/usr/bin/env python3
"""TESTE: a MARCA (música, avatar, propaganda, vinheta final) foi aplicada corretamente no draft do CapCut?
Monta o draft numa pasta TEMPORÁRIA (nada é escrito nos seus projetos) e confere:
   M1 integridade: todo material_id / extra_material_refs existe e não há IDs repetidos entre materiais
   M2 trilhas na ordem  preenchimento · clipes · overlay · avatar · final · narracao · musica
   M3 música cobre 0..fim sem buracos e termina junto com o vídeo
   M4 avatar ausente durante a propaganda e durante a vinheta final; presente no resto até a vinheta
   M5 propaganda (vídeo + áudio) começa no instante pedido e tem a duração do pacote; nada do overlay/B-roll/narração sobrepõe a propaganda
   M6 vinheta final nos últimos segundos, por cima do B-roll; B-roll e preenchimento chegam até o fim
   M7 nenhuma trilha tem segmentos sobrepostos
Rode em animacao/ (precisa de plano.json com propaganda_t, capcut_spec.json e o pacote privado). Sai 1 se algo falhar.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CAP = Path(__file__).resolve().parent.parent / "capcut"
source_spec = Path("capcut_spec.json")
assert source_spec.exists(), "rode `spec_from_plan.py` antes (capcut_spec.json) dentro de animacao/"
spec = json.load(open(source_spec))
assert spec.get("marca"), "spec sem 'marca': defina PROPAGANDA_APOS no plan_data.py (e extraia o pacote)"
tmp = Path(tempfile.mkdtemp(prefix="cc_marca_"))
drafts = tmp / "drafts"
drafts.mkdir()
spec["nome"] = "TESTE marca"
json.dump(spec, open(tmp / "spec.json", "w"))
env = dict(os.environ, CAPCUT_DRAFTS_DIR=str(drafts), CAPCUT_TESTE="1")
r = subprocess.run(
    [sys.executable, str(CAP / "build_draft.py"), str(tmp / "spec.json"), "--force"],
    capture_output=True,
    text=True,
    env=env,
)
assert r.returncode == 0, r.stdout[-1200:] + r.stderr[-1200:]
info = json.load(open(drafts / "TESTE marca" / "draft_info.json"))
total = info["duration"] / 1e6
errors = []

# M1 integridade
ids = {}
for material_list, items in info["materials"].items():
    if isinstance(items, list):
        for m in items:
            if isinstance(m, dict) and "id" in m:
                if m["id"] in ids:
                    errors.append(f"M1: id repetido {m['id'][:8]} em {material_list}/{ids[m['id']]}")
                ids[m["id"]] = material_list
for t in info["tracks"]:
    for s in t["segments"]:
        for ref in [s["material_id"]] + s.get("extra_material_refs", []):
            if ref not in ids:
                errors.append(f"M1: referência inexistente {ref[:8]} na trilha {t.get('name')}")

# M2 ordem das trilhas
names = [t.get("name") for t in info["tracks"]]
expected = ["preenchimento", "clipes", "overlay", "avatar", "final", "narracao", "musica"]
if names != expected:
    errors.append(f"M2: ordem das trilhas {names} != {expected}")
tracks_by_name = {t["name"]: t for t in info["tracks"]}
segments = lambda n: sorted(
    [
        (
            s["target_timerange"]["start"] / 1e6,
            (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6,
            s,
        )
        for s in tracks_by_name[n]["segments"]
    ],
    key=lambda x: x[0],
)

# M7 sobreposição por trilha
for n in expected:
    s = segments(n)
    for (a0, a1, _), (b0, b1, _) in zip(s, s[1:]):
        if b0 < a1 - 0.034 and n not in ("narracao",):
            errors.append(f"M7: trilha {n} tem sobreposição {a0:.2f}-{a1:.2f} × {b0:.2f}-{b1:.2f}")

# M3 música
music = segments("musica")
if abs(music[0][0]) > 0.034:
    errors.append("M3: música não começa em 0")
for (a0, a1, _), (b0, b1, _) in zip(music, music[1:]):
    if abs(b0 - a1) > 0.034:
        errors.append(f"M3: buraco/sobreposição na música {a1:.2f}→{b0:.2f}")
if abs(music[-1][1] - total) > 0.1:
    errors.append(f"M3: música termina em {music[-1][1]:.2f}s, vídeo em {total:.2f}s")

# M5 propaganda
promo_time = spec["marca"]["propaganda_t"]
resume_time = spec["marca"].get("propaganda_retoma", promo_time)
promo_video_clips = [
    x
    for x in segments("clipes")
    if "predefin" in json.dumps(x[2].get("extra_material_refs", [])) or abs(x[0] - promo_time) < 0.05
]
promo_video_clips = [x for x in segments("clipes") if abs(x[0] - promo_time) < 0.05]
if not promo_video_clips:
    errors.append(f"M5: propaganda (vídeo) não começa em {promo_time}s")
    promo_duration = 0
else:
    promo_duration = promo_video_clips[0][1] - promo_video_clips[0][0]
if not any(abs(x[0] - promo_time) < 0.05 for x in segments("narracao")):
    errors.append("M5: áudio da propaganda não começa em T")
for n in ("clipes", "overlay"):
    for a0, a1, s in segments(n):
        if abs(a0 - promo_time) < 0.05 and n == "clipes":
            continue
        if a0 < promo_time + promo_duration - 0.034 and a1 > promo_time + 0.034:
            errors.append(f"M5: {n} {a0:.2f}-{a1:.2f} SOBRE a propaganda ({promo_time:.1f}-{promo_time + promo_duration:.1f})")
after = [
    x
    for x in segments("narracao")
    if x[0] >= promo_time + promo_duration - 0.05
    and "extract_music" in json.dumps(x[2].get("extra_material_refs", []))
    or x[0] >= promo_time + promo_duration - 0.05
]
if after:
    src_start = after[0][2]["source_timerange"]["start"] / 1e6
    if abs(src_start - resume_time) > 0.1:
        errors.append(
            f"M5: a narração retoma da fonte em {src_start:.2f}s, esperado {resume_time:.2f}s (o silêncio {promo_time:.1f}-{resume_time:.1f}s deve ser removido)"
        )
for a0, a1, s in segments("narracao"):
    if a0 < promo_time + promo_duration - 0.034 and a1 > promo_time + 0.034 and abs(a0 - promo_time) > 0.05:
        errors.append(f"M5: narração {a0:.2f}-{a1:.2f} sobre a propaganda")

# M4/M6 avatar e vinheta final
outro = segments("final")
if len(outro) != 1 or outro[0][1] < total - 0.1:
    errors.append(
        f"M6: vinheta final deveria terminar com o vídeo ({outro[0][1] if outro else None} vs {total:.2f})"
    )
else:
    f0, f1, _ = outro[0]
    for a0, a1, _ in segments("avatar"):
        if a1 > f0 + 0.034:
            errors.append(f"M4: avatar {a0:.2f}-{a1:.2f} aparece na vinheta final ({f0:.1f}s)")
        if a0 < promo_time + promo_duration - 0.034 and a1 > promo_time + 0.034:
            errors.append(f"M4: avatar aparece durante a propaganda")
    avatar = segments("avatar")
    if abs(avatar[0][0]) > 0.034 or abs(avatar[-1][1] - f0) > 0.1:
        errors.append(
            f"M4: avatar deve ir de 0 até o início da vinheta ({f0:.1f}s): {[(round(a, 1), round(b, 1)) for a, b, _ in avatar]}"
        )
    # B-roll chega até o fim por baixo da vinheta
    clips = [x for x in segments("clipes") if abs(x[0] - promo_time) > 0.05]
    if not clips or clips[-1][1] < total - 0.1:
        errors.append(
            f"M6: B-roll termina em {clips[-1][1] if clips else None}, o vídeo em {total:.2f}s (B-roll precisa ir até o fim)"
        )
filler = segments("preenchimento")
if filler[-1][1] < total - 0.1:
    errors.append("M6: preenchimento não chega ao fim")
shutil.rmtree(tmp, ignore_errors=True)
print(f"trilhas {names} · total {total:.1f}s · propaganda em {promo_time:.1f}s ({promo_duration:.1f}s)")
if errors:
    print("FALHOU:")
    [print("  -", e) for e in errors[:40]]
    sys.exit(1)
print("OK: marca aplicada (música/avatar/propaganda/vinheta) sem sobreposições nem buracos")
