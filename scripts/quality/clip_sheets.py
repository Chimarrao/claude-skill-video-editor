#!/usr/bin/env python3
"""Folhas de contato dos CLIPES de B-roll escolhidos (5 quadros por clipe, dos proxies de src/videos/): para OLHAR antes do render.
O classificador (CLIP+OCR+rosto) não vê tudo: jogo/página de vídeo dentro do desktop, quadro preto, janelinha minúscula, câmera filmando monitor.
Roda em animacao/: python clip_sheets.py → qa/clips_sheet_NN.png (6 clipes por folha). Depois: Read nas PNGs e troque o que estiver ruim.
"""

import json, os, subprocess, tempfile
from pathlib import Path

from PIL import Image, ImageDraw

cwd = Path.cwd()
broll = json.load(open(cwd / "src/scenes/broll.json"))
out = cwd / "qa"
out.mkdir(exist_ok=True)
for f in out.glob("clips_sheet_*.png"):
    f.unlink()
POR_FOLHA, N = 6, 5
for s0 in range(0, len(broll), POR_FOLHA):
    grupo = broll[s0 : s0 + POR_FOLHA]
    folha = Image.new("RGB", (N * 384, len(grupo) * 234), (25, 25, 25))
    for r, b in enumerate(grupo):
        proxy = cwd / f"src/videos/clip_{s0 + r + 1:02d}.mp4"
        if not proxy.exists():
            continue
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(proxy)], capture_output=True, text=True).stdout or 0)
        for k in range(N):
            with tempfile.TemporaryDirectory() as d:
                f = Path(d) / "f.png"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{dur * (k + 0.5) / N:.2f}", "-i", str(proxy), "-frames:v", "1", "-vf", "scale=384:216", str(f)])
                if f.exists():
                    folha.paste(Image.open(f).convert("RGB"), (k * 384, r * 234 + 18))
        d = ImageDraw.Draw(folha)
        d.text((4, r * 234 + 3), f"#{s0 + r + 1} {os.path.basename(b['file'])[:44]} {b['in']:.0f}-{b['out']:.0f}s x{b['speed']} @ {b['t_start']:.0f}s", fill=(255, 255, 0))
    folha.save(out / f"clips_sheet_{s0 // POR_FOLHA:02d}.png")
print(f"{len(broll)} clipes → {out}/clips_sheet_*.png (OLHE cada folha)")
