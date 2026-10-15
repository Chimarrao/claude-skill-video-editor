#!/usr/bin/env python3
"""Folha de contato DETALHADA de um trecho de um vídeo. Uso: segment_sheet.py <video> <start> <end> [--step 1.0] [--output folha.png]
Use depois da análise geral para conferir (nítido? marca d'água? texto legível?) o trecho que vai entrar no B-roll.
"""

import argparse, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("video")
parser.add_argument("start", type=float)
parser.add_argument("end", type=float)
parser.add_argument("--step", type=float, default=1.0)
parser.add_argument("--output", default="sheet_span.png")
args = parser.parse_args()
timestamps = []
t = args.start
while t < args.end and len(timestamps) < 36:
    timestamps.append(round(t, 2))
    # passo mínimo garante no máximo 36 quadros por folha
    t += max(args.step, (args.end - args.start) / 36)
W, H, cols = 480, 270, 6
rows = (len(timestamps) + cols - 1) // cols
sheet = Image.new("RGB", (W * cols, H * rows), (20, 20, 20))
draw = ImageDraw.Draw(sheet)
for j, t in enumerate(timestamps):
    tmp = tempfile.mktemp(suffix=".jpg")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(t),
            "-i",
            args.video,
            "-frames:v",
            "1",
            "-vf",
            f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
            tmp,
        ],
        capture_output=True,
    )
    if os.path.exists(tmp):
        sheet.paste(Image.open(tmp), ((j % cols) * W, (j // cols) * H))
        os.remove(tmp)
    draw.rectangle(((j % cols) * W, (j // cols) * H, (j % cols) * W + 60, (j // cols) * H + 16), fill=(0, 0, 0))
    draw.text(((j % cols) * W + 3, (j // cols) * H + 2), f"{t:.1f}s", fill=(255, 255, 0))
sheet.save(args.output)
print(args.output)
