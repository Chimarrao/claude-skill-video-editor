#!/usr/bin/env python3
"""Extrai o PACOTE DE MARCA (música, avatar, propaganda, vinheta final) de projetos do CapCut já editados à mão.
Uso:
  python extrair_pacote_marca.py --ref "<pasta do draft com avatar+propaganda+música>" [--ref-final "<draft com a vinheta final>"]
         [--avatar "predefinições6"] [--propaganda "predefinições4"] [--musica "predefinições2"] [--final "predefinições3"]
         [--saida privado/pacote_marca]
Os nomes são os que o CapCut deu às predefinições (substring do nome do material). O pacote é privado (pasta ignorada pelo git).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marca  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--ref", required=True)
ap.add_argument("--ref-final")
for papel, padrao in marca.NOMES_PADRAO.items():
    ap.add_argument(f"--{papel}", default=padrao)
ap.add_argument("--saida", default=str(marca.PACOTE_PADRAO))
a = ap.parse_args()
marca.extrair(
    a.ref,
    a.ref_final,
    dict(avatar=a.avatar, propaganda=a.propaganda, musica=a.musica, final=a.final),
    a.saida,
)
