#!/usr/bin/env python3
"""TESTE: overlay recortado no CapCut. Roda na pasta animacao/ (precisa de plano_dados.py, plano.json, output/project.mov).
Gera o spec + monta o draft numa pasta TEMPORÁRIA (não toca nos projetos do CapCut) e confere:
 - nenhum segmento de overlay encosta num clipe de B-roll (animação nunca vaza sobre o vídeo);
 - overlay + clipes cobrem 100% da narração (sem buraco que o usuário teria que preencher);
 - source_timerange do overlay = target (sincronia com o .mov);
 - trilhas na ordem preenchimento → clipes → overlay → narração.
Uso: python testar_capcut_overlay.py [--overlay output/project.mov]"""

import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

CAP = Path(__file__).resolve().parent.parent / "capcut"
ap = argparse.ArgumentParser()
ap.add_argument("--overlay", default="output/project.mov")
ap.add_argument("--voz", default=None)
a = ap.parse_args()
cwd = Path.cwd()
assert (cwd / "plano_dados.py").exists(), "rode dentro de animacao/"
voz = a.voz or str((cwd / ".." / "pronto.wav").resolve())
tmp = Path(tempfile.mkdtemp(prefix="cc_teste_"))
drafts = tmp / "drafts"
drafts.mkdir()
spec = tmp / "spec.json"
r = subprocess.run(
    [
        sys.executable,
        str(CAP / "spec_do_plano.py"),
        "--nome",
        "TESTE overlay",
        "--voz",
        voz,
        "--overlay",
        a.overlay,
        "--saida",
        str(spec),
    ],
    capture_output=True,
    text=True,
)
assert r.returncode == 0, r.stderr
spec_j = json.load(open(spec))
leve = spec_j.get("overlay_leve") or []  # webdoc com B-roll: rótulo leve PODE ficar sobre o clipe
env = dict(os.environ, CAPCUT_DRAFTS_DIR=str(drafts), CAPCUT_TESTE="1")
r = subprocess.run(
    [sys.executable, str(CAP / "montar_draft.py"), str(spec), "--forcar"],
    capture_output=True,
    text=True,
    env=env,
)
assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
info = json.load(open(drafts / "TESTE overlay" / "draft_info.json"))
nomes = [t.get("name") for t in info["tracks"]]
erros = []
if nomes[:4] != ["preenchimento", "clipes", "overlay", "narracao"]:
    erros.append(f"ordem das trilhas: {nomes}")
seg = lambda n: [
    (
        s["target_timerange"]["start"] / 1e6,
        (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6,
        s,
    )
    for s in next(t for t in info["tracks"] if t.get("name") == n)["segments"]
]
clipes, ov = seg("clipes"), seg("overlay")
total = info["duration"] / 1e6
if not ov:
    erros.append("overlay sem segmentos")
for a0, a1, s in ov:
    if abs(s["source_timerange"]["start"] / 1e6 - a0) > 0.04:
        erros.append(f"overlay {a0:.2f}: source {s['source_timerange']['start']/1e6:.2f} != target")
    for c0, c1, _ in clipes:
        ov_ = min(a1, c1) - max(a0, c0)
        if ov_ > 0.034:
            # a parte do overlay que cobre o clipe precisa estar dentro de um rótulo leve permitido
            lo, hi = max(a0, c0), min(a1, c1)
            if not any(l0 - 0.05 <= lo and hi <= l1 + 0.05 for l0, l1 in leve):
                erros.append(f"overlay {a0:.2f}-{a1:.2f} SOBRE clipe {c0:.2f}-{c1:.2f}")
ocup = sorted([(x[0], x[1]) for x in clipes + ov])
cur = 0.0
buracos = []  # (overlay leve sobre clipe é permitido)
for x0, x1 in ocup:
    if x0 - cur > 0.07:
        buracos.append((round(cur, 2), round(x0, 2)))
    cur = max(cur, x1)
if total - cur > 0.07:
    buracos.append((round(cur, 2), round(total, 2)))
if buracos:
    erros.append(f"buracos sem overlay nem clipe: {buracos[:5]}")
shutil.rmtree(tmp, ignore_errors=True)
print(f"trilhas {nomes[:4]} · {len(clipes)} clipes · {len(ov)} segmentos de overlay · total {total:.1f}s")
if erros:
    print("FALHOU:")
    [print("  -", e) for e in erros]
    sys.exit(1)
print("OK: overlay recortado nas janelas sem B-roll, sem vazamento e sem buracos")
