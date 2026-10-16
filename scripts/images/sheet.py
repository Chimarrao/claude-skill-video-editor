#!/usr/bin/env python3
"""Folha de contato de imagens da biblioteca (para OLHAR antes de usar): nome, tamanho e fundo claro/escuro.
Uso: python sheet.py "padrão*" [saida.png] [--cols 6] [--dir library]   (o padrão aceita curingas; vários separados por vírgula)
"""

import argparse, fnmatch, os, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser()
ap.add_argument("padrao")
ap.add_argument("saida", nargs="?", default="/tmp/folha_imagens.png")
ap.add_argument("--cols", type=int, default=6)
ap.add_argument("--dir", default=os.path.join(ROOT, "library"))
ap.add_argument("--cell", type=int, default=300)
a = ap.parse_args()
pats = a.padrao.split(",")
files = sorted(f for f in os.listdir(a.dir) if any(fnmatch.fnmatch(f, p) for p in pats) and not f.startswith("."))
if not files:
    sys.exit("nenhum arquivo")
C = a.cell
rows = (len(files) + a.cols - 1) // a.cols
sheet = Image.new("RGB", (a.cols * C, rows * (C + 26)), (40, 40, 40))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    try:
        im = Image.open(os.path.join(a.dir, f)).convert("RGBA")
    except Exception:
        continue
    w, h = im.size
    th = im.copy()
    th.thumbnail((C - 8, C - 8))
    bg = Image.new("RGBA", (C - 8, C - 8), (255, 255, 255, 255) if i % 2 == 0 else (60, 60, 60, 255))
    bg.paste(th, ((C - 8 - th.width) // 2, (C - 8 - th.height) // 2), th)
    x, y = (i % a.cols) * C, (i // a.cols) * (C + 26)
    sheet.paste(bg.convert("RGB"), (x + 4, y + 4))
    d.text((x + 6, y + C - 2), f"{f[:40]}  {w}x{h}", fill=(255, 255, 0))
sheet.save(a.saida)
print(a.saida, len(files), "imagens")
