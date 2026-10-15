#!/usr/bin/env python3
"""Extrai o PACOTE DE MARCA (música, avatar, propaganda, vinheta final) de projetos do CapCut já editados à mão.
Uso:
  python extract_brand_pack.py --ref "<pasta do draft com avatar+propaganda+música>" [--ref-ending "<draft com a vinheta final>"]
         [--avatar "predefinições6"] [--promo "predefinições4"] [--music "predefinições2"] [--ending "predefinições3"]
         [--output private/brand_pack]
Os nomes são os que o CapCut deu às predefinições (substring do nome do material). O pacote é privado (pasta ignorada pelo git).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--ref", required=True)
ap.add_argument("--ref-ending", default=None)
# Nomes das predefinições vêm de brand.DEFAULT_NAMES (chaves em pt, formato do pacote); flags CLI em inglês com apelido pt oculto.
_flag_aliases = {"promo": ("--promo", "--promo"), "music": ("--music", "--music"), "final": ("--ending", "--final")}
for role, default in brand.DEFAULT_NAMES.items():
    if role in _flag_aliases:
        ap.add_argument(_flag_aliases[role][0], _flag_aliases[role][1], default=default)
    else:
        ap.add_argument(f"--{role}", default=default)
ap.add_argument("--output", default=str(brand.DEFAULT_PACK))
a = ap.parse_args()
brand.extract(
    a.ref,
    a.ref_ending,
    dict(avatar=a.avatar, promo=a.promo, music=a.music, final=a.ending),
    a.output,
)
