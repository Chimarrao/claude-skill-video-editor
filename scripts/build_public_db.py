#!/usr/bin/env python3
"""Gera o banco PÚBLICO (database/assets.publico.db) a partir do privado (database/assets.db).
O banco público guarda só REFERÊNCIAS: as imagens públicas viram arquivos individuais em database/public_images/ (versionados no git),
então nenhum arquivo do repositório fica perto do limite de 100 MB do GitHub.
Entram só logos pequenas (<= 100 KB, livres e de boa qualidade) e as miniaturas das variações de lista; saem transcrições, vídeos,
fotos de pessoas, telas e objetos."""

import os, shutil, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBDIR = os.path.join(ROOT, "database")
SRC = os.path.join(DBDIR, "assets.db")
DST = os.path.join(DBDIR, "assets.publico.db")
PUB = os.path.join(DBDIR, "public_images")
TMP = "/tmp/_assets_pub.db"

if not os.path.exists(SRC):
    print("build_public_db: sem database/assets.db (nada a fazer)")
    sys.exit(0)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import assets_db  # noqa: E402  (read_asset)

shutil.copy(SRC, TMP)
c = sqlite3.connect(TMP)
c.execute("DELETE FROM transcripts")
c.execute("DROP TABLE IF EXISTS videos")
c.execute(
    "DELETE FROM assets WHERE category IN ('person','screen','object','photo') OR bytes > 100000 "
    "OR COALESCE(quality,'ok') != 'ok' OR COALESCE(nonfree,0) = 1"
)
shutil.rmtree(PUB, ignore_errors=True)
os.makedirs(os.path.join(PUB, "variations"), exist_ok=True)
n = miss = 0
for name, ext, b64, ref in c.execute("SELECT name, ext, base64, file FROM assets").fetchall():
    data = assets_db.read_asset(name, ext, b64, ref)
    if data is None:
        miss += 1
        c.execute("DELETE FROM assets WHERE name=?", (name,))
        continue
    open(os.path.join(PUB, f"{name}.{ext}"), "wb").write(data)
    c.execute("UPDATE assets SET file=?, base64=NULL WHERE name=?", (f"public_images/{name}.{ext}", name))
    n += 1
t = 0
if c.execute("SELECT 1 FROM sqlite_master WHERE name='list_variations'").fetchone():
    cols = {r[1] for r in c.execute("PRAGMA table_info(list_variations)")}
    if "thumb_file" not in cols:
        c.execute("ALTER TABLE list_variations ADD COLUMN thumb_file TEXT")
    for vid, b64, ref in c.execute("SELECT id, thumb_base64, thumb_file FROM list_variations").fetchall():
        src = os.path.join(DBDIR, ref) if ref and os.path.exists(os.path.join(DBDIR, ref)) else None
        data = open(src, "rb").read() if src else (__import__("base64").b64decode(b64) if b64 else None)
        if data:
            open(os.path.join(PUB, "variations", f"{vid}.png"), "wb").write(data)
            c.execute("UPDATE list_variations SET thumb_file=?, thumb_base64=NULL WHERE id=?", (f"public_images/variations/{vid}.png", vid))
            t += 1
c.commit()
c.execute("VACUUM")
c.close()
shutil.copy(TMP, DST)
print(f"build_public_db: {n} imagem(ns) + {t} miniatura(s) em database/public_images/ ({miss} sem arquivo); banco público {os.path.getsize(DST)/1e6:.2f} MB")
