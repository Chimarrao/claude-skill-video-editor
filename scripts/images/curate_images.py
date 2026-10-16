#!/usr/bin/env python3
"""Curadoria automática da biblioteca: marca no catálogo (`quality`) o que não presta e deixa o resto utilizável.

Marca como `low:<motivo>`: imagem praticamente lisa/vazia, quase toda transparente, proporção extrema (faixa/banner), muito pequena
para o tipo, ou quase-duplicata (dHash) de outra do mesmo assunto. NÃO apaga nada: `find_image.py` ignora `low` por padrão.
Uso: python curate_images.py [--only slug,slug]   (recalcula e grava database/image_catalog.json)
"""

import argparse, json, os, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(ROOT, "library")
CAT = os.path.join(ROOT, "database", "image_catalog.json")


def dhash(im, n=8):
    """Hash de diferença 64 bits: estável a redimensionamento/compressão."""
    g = np.asarray(im.convert("L").resize((n + 1, n), Image.LANCZOS), dtype=np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def analisa(path, kind):
    """Devolve (motivo ou None, hash) para um arquivo."""
    try:
        im = Image.open(path)
        im.load()
    except Exception:
        return "ilegível", None
    w, h = im.size
    rgba = im.convert("RGBA")
    small = rgba.resize((96, 96), Image.LANCZOS)
    a = np.asarray(small)[:, :, 3] / 255.0
    cover = float((a > 0.1).mean())
    if cover < 0.04:
        return "quase transparente", None
    rgb = np.asarray(small.convert("RGB"), dtype=np.float32)
    lum = rgb.mean(axis=2)
    visivel = lum[a > 0.1]
    if visivel.std() < 5 and kind != "logo":
        return "lisa/sem informação", None
    r = w / h
    if r > 8 or r < 0.12:
        return "proporção extrema", None
    if kind in ("tela", "foto", "obj") and min(w, h) < 300:
        return "pequena demais", None
    if kind == "logo" and max(w, h) < 120:
        return "pequena demais", None
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    bg.alpha_composite(rgba)
    return None, dhash(bg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    cat = json.load(open(CAT, encoding="utf8"))
    only = set(filter(None, args.only.split(",")))
    hashes = {}
    n_low = 0
    for name in sorted(cat["images"]):
        v = cat["images"][name]
        if only and v["subject"] not in only:
            continue
        path = os.path.join(LIB, v["file"])
        if not os.path.exists(path):
            v["quality"] = "low:arquivo ausente"
            continue
        motivo, hs = analisa(path, v["kind"])
        if not motivo and hs is not None:
            for outro, ho in hashes.get(v["subject"], []):
                if (hs != ho).sum() <= 4:
                    motivo = f"quase-duplicata de {outro}"
                    break
            else:
                hashes.setdefault(v["subject"], []).append((name, hs))
        v["quality"] = f"low:{motivo}" if motivo else "ok"
        n_low += bool(motivo)
    json.dump(cat, open(CAT, "w", encoding="utf8"), ensure_ascii=False, indent=1, sort_keys=True)
    total = len(cat["images"])
    print(f"{total} imagens: {total - n_low} ok, {n_low} marcadas low")


if __name__ == "__main__":
    main()
