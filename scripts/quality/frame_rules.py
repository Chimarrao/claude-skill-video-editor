"""Regras puras (sem I/O) do gate de frames — separadas para serem testadas com quadros sintéticos (tests/test_frame_rules.py)."""

import numpy as np


def base_vazia(gray):
    """Quadro de B-roll vazio? `gray` = luminância 0-255 (matriz). Preto total ou liso demais reprova; interface ESCURA com texto
    (Android Honeycomb, terminal: média baixa mas > 1% de pixels claros) é conteúdo legítimo e passa."""
    g = np.asarray(gray, dtype=np.float32)
    claros = float((g > 40).mean())
    return bool(g.std() < 4 or (g.mean() < 10 and claros < 0.01))


def cartela_do_item(t, janela, tipo, menu_duration=3.7):
    """O instante cai na cartela de abertura do item (terminal + nome grande)? Ali um elemento grande é intencional (F2 não se aplica)."""
    return tipo == "item" and janela[0] <= t < janela[0] + menu_duration + 0.3
