"""Publica na biblioteca da skill (assets/) as imagens deste projeto que ainda não existem lá (logo_*, foto_*, tela_*, etc.)
para reaproveitar em outros projetos. Uso: python scripts/publish_assets.py"""

import os, shutil, glob

d = os.path.abspath(".")
lib = None
while d != "/":
    c = os.path.join(d, ".claude", "skills", "animacao-narracao", "assets")
    if os.path.isdir(c):
        lib = c
        break
    d = os.path.dirname(d)
assert lib, "biblioteca de assets não encontrada"
n = 0
for f in glob.glob("src/images/*"):
    b = os.path.basename(f)
    if b.startswith(("ic-", "placeholder")) or b.endswith("-mono.svg"):
        continue  # gerados automaticamente
    if not os.path.exists(os.path.join(lib, b)):
        shutil.copy(f, os.path.join(lib, b))
        n += 1
print(f"{n} imagem(ns) nova(s) publicadas em {lib}")
