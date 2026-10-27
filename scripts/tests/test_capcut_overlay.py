#!/usr/bin/env python3
"""TESTE: overlay recortado no CapCut. Roda na pasta animacao/ (precisa de plan_data.py, plan.json, output/project.mov).
Gera o spec + monta o draft numa pasta TEMPORÁRIA (não toca nos projetos do CapCut) e confere:
 - nenhum pedaço de overlay < 1,5 s (pisca na tela);
 - nenhum segmento de overlay encosta num clipe de B-roll (animação nunca vaza sobre o vídeo);
 - overlay + clipes cobrem 100% da narração (sem buraco que o usuário teria que preencher);
 - source_timerange do overlay = target (sincronia com o .mov);
 - trilhas na ordem preenchimento → clipes → overlay → narração.
Uso: python test_capcut_overlay.py [--overlay output/project.mov]"""

import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

CAP = Path(__file__).resolve().parent.parent / "capcut"
ap = argparse.ArgumentParser()
ap.add_argument("--overlay", default="output/project.mov")
ap.add_argument("--voice", default=None)
args = ap.parse_args()
cwd = Path.cwd()
assert (cwd / "plan_data.py").exists(), "rode dentro de animacao/"
voice = args.voice or str((cwd / ".." / "pronto.wav").resolve())
tmp = Path(tempfile.mkdtemp(prefix="cc_test_"))
drafts = tmp / "drafts"
drafts.mkdir()
spec = tmp / "spec.json"
r = subprocess.run(
    [
        sys.executable,
        str(CAP / "spec_from_plan.py"),
        "--name",
        "TESTE overlay",
        "--voice",
        voice,
        "--overlay",
        args.overlay,
        "--output",
        str(spec),
        "--no-branding",  # a inserção da propaganda desloca o overlay de propósito; isso é coberto por test_capcut_brand.py
    ],
    capture_output=True,
    text=True,
)
assert r.returncode == 0, r.stderr
spec_doc = json.load(open(spec))
light_overlay = spec_doc.get("overlay_light") or []  # webdoc com B-roll: rótulo leve PODE ficar sobre o clipe
env = dict(os.environ, CAPCUT_DRAFTS_DIR=str(drafts), CAPCUT_TEST="1")
r = subprocess.run(
    [sys.executable, str(CAP / "build_draft.py"), str(spec), "--force"],
    capture_output=True,
    text=True,
    env=env,
)
assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
info = json.load(open(drafts / "TESTE overlay" / "draft_info.json"))
names = [t.get("name") for t in info["tracks"]]
errors = []
if names[:4] != ["filler", "clips", "overlay", "narration"]:
    errors.append(f"ordem das trilhas: {names}")
segments = lambda n: [
    (
        s["target_timerange"]["start"] / 1e6,
        (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6,
        s,
    )
    for s in next(t for t in info["tracks"] if t.get("name") == n)["segments"]
]
clips, overlay_segs = segments("clips"), segments("overlay")
total = info["duration"] / 1e6
if not overlay_segs:
    errors.append("overlay sem segmentos")
for a0, a1, s in overlay_segs:
    if abs(s["source_timerange"]["start"] / 1e6 - a0) > 0.04:
        errors.append(f"overlay {a0:.2f}: source {s['source_timerange']['start']/1e6:.2f} != target")
    for c0, c1, _ in clips:
        overlap = min(a1, c1) - max(a0, c0)
        if overlap > 0.034:
            # a parte do overlay que cobre o clipe precisa estar dentro de um rótulo leve permitido
            lo, hi = max(a0, c0), min(a1, c1)
            if not any(l0 - 0.05 <= lo and hi <= l1 + 0.05 for l0, l1 in light_overlay):
                errors.append(f"overlay {a0:.2f}-{a1:.2f} SOBRE clipe {c0:.2f}-{c1:.2f}")
covered = sorted([(x[0], x[1]) for x in clips + overlay_segs])
current = 0.0
gaps = []  # (overlay leve sobre clipe é permitido)
for x0, x1 in covered:
    if x0 - current > 0.07:
        gaps.append((round(current, 2), round(x0, 2)))
    current = max(current, x1)
if total - current > 0.07:
    gaps.append((round(current, 2), round(total, 2)))
gaps = [g for g in gaps if g[1] - g[0] > 1.6]  # sobras < 1,5 s entre clipes ficam só com o preenchimento (nada de overlay piscando)
if gaps:
    errors.append(f"buracos sem overlay nem clipe: {gaps[:5]}")
for a0, a1, _ in overlay_segs:
    if a1 - a0 < 1.5 - 0.01:
        errors.append(f"overlay {a0:.2f}-{a1:.2f} dura só {a1-a0:.2f}s: pisca na tela (mínimo 1,5 s)")
shutil.rmtree(tmp, ignore_errors=True)
print(f"trilhas {names[:4]} · {len(clips)} clipes · {len(overlay_segs)} segmentos de overlay · total {total:.1f}s")
if errors:
    print("FALHOU:")
    [print("  -", e) for e in errors]
    sys.exit(1)
print("OK: overlay recortado nas janelas sem B-roll, sem vazamento e sem buracos")
