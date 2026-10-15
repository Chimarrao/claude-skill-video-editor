#!/usr/bin/env python3
"""Folha de contato DETALHADA de um trecho de um vídeo. Uso: folha_trecho.py <video> <de_s> <ate_s> [--passo 1.0] [--saida folha.png]
Use depois da análise geral para conferir (nítido? marca d'água? texto legível?) o trecho que vai entrar no B-roll.
"""

import argparse, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("de", type=float)
ap.add_argument("ate", type=float)
ap.add_argument("--passo", type=float, default=1.0)
ap.add_argument("--saida", default="folha_trecho.png")
a = ap.parse_args()
ts = []
t = a.de
while t < a.ate and len(ts) < 36:
    ts.append(round(t, 2))
    t += max(a.passo, (a.ate - a.de) / 36)
W, H, cols = 480, 270, 6
rows = (len(ts) + cols - 1) // cols
sh = Image.new("RGB", (W * cols, H * rows), (20, 20, 20))
d = ImageDraw.Draw(sh)
for j, t in enumerate(ts):
    tmp = tempfile.mktemp(suffix=".jpg")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(t),
            "-i",
            a.video,
            "-frames:v",
            "1",
            "-vf",
            f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
            tmp,
        ],
        capture_output=True,
    )
    if os.path.exists(tmp):
        sh.paste(Image.open(tmp), ((j % cols) * W, (j // cols) * H))
        os.remove(tmp)
    d.rectangle(((j % cols) * W, (j // cols) * H, (j % cols) * W + 60, (j // cols) * H + 16), fill=(0, 0, 0))
    d.text(((j % cols) * W + 3, (j // cols) * H + 2), f"{t:.1f}s", fill=(255, 255, 0))
sh.save(a.saida)
print(a.saida)
