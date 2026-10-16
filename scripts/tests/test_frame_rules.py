#!/usr/bin/env python3
"""TESTE das regras puras do gate de frames (quality/frame_rules.py) com quadros sintéticos — sem render, sem projeto.
 T1 quadro todo preto reprova (F6)        T2 quadro liso cinza reprova          T3 interface escura COM texto passa (Android Honeycomb)
 T4 tela clara normal passa               T5 a cartela de abertura do item isenta o F2; o resto do item não
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quality"))
from frame_rules import base_vazia, cartela_do_item  # noqa: E402

falhas = []


def teste(nome, cond):
    print(("ok    " if cond else "FALHA ") + nome)
    if not cond:
        falhas.append(nome)


preto = np.zeros((108, 192))
teste("T1 quadro preto reprova", base_vazia(preto))
teste("T2 quadro liso cinza reprova", base_vazia(np.full((108, 192), 120.0)))
ui = np.zeros((108, 192))
ui[20:24, 30:150] = 220  # linhas de texto claras sobre fundo preto (~4% dos pixels)
ui[50:54, 30:120] = 200
ui[80:84, 30:100] = 200
teste("T3 interface escura com texto passa", not base_vazia(ui))
rng = np.random.default_rng(1)
teste("T4 tela clara com conteúdo passa", not base_vazia(rng.uniform(40, 220, (108, 192))))
teste("T5 cartela do item (1 s depois do início) isenta F2", cartela_do_item(691.0, [688.0, 760.0, "item"], "item"))
teste("T5 depois da cartela volta a valer F2", not cartela_do_item(700.0, [688.0, 760.0, "item"], "item"))
teste("T5 cena que não é item não tem cartela", not cartela_do_item(689.0, [688.0, 760.0, "graph"], "graph"))
print(f"\n{'FALHOU' if falhas else 'OK'} — {len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
