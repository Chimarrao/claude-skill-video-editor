#!/usr/bin/env python3
"""TESTE do tipo NEWS (sem rede, sem vídeo): transcrição e features sintéticas → regras de detecção e construção dos cortes.
 N1 pausa longa é encurtada com respiro e o corte cai em silêncio, a >= 80 ms das palavras     N2 regravação (início repetido) → fica a última versão
 N3 sufixo repetido ("É uma | É uma plataforma") sai do enunciado anterior                      N4 reticências ("...") = frase abandonada sai
 N5 fragmento curto sem pontuação final sai; frase curta com ponto final fica                   N6 comando falado remove a tentativa que falhou
 N7 a ORDEM nunca muda e os trechos mantidos não se sobrepõem                                   N8 início/fim: corta antes da 1ª fala e depois da última
 N9 tudo cai na grade de 60 fps"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "news"))
import json

import plan_cuts as pc
from news_cuts import constroi
from news_detect import detecta

P = json.load(open(Path(__file__).resolve().parents[1] / "news" / "news_params.json"))
ok, falhas = [], []


def teste(nome, cond, msg=""):
    (ok if cond else falhas).append(nome if cond else f"{nome}: {msg}")


def monta(frases, dur):
    """frases = [(início, [palavras], dur_palavra)] → (words, feats). Cada palavra dura `dur_palavra`, 0,1 s entre palavras da frase."""
    words = []
    for t0, ws, dw in frases:
        t = t0
        for w in ws:
            words.append(dict(w=w, n=pc.norm(w), s=t, e=t + dw, p=0.99))
            t += dw + 0.1
    e = np.full(int(dur / 0.01), -68.0, dtype=np.float32)
    for w in words:
        e[int(w["s"] / 0.01) : int(w["e"] / 0.01)] = -30.0
    fr = np.zeros((int(dur * 10) + 2, 54, 96), dtype=np.uint8)
    return words, dict(energy_db=e, frames=fr, motion=np.zeros(len(fr) - 1, dtype=np.float32), fps=10.0)


def roda(frases, dur=40.0, **over):
    Q = dict(P, **over)
    words, feats = monta(frases, dur)
    utts = pc.enunciados(words, Q["utterance_gap_s"])
    rem = detecta(words, utts, feats, Q)
    return words, constroi(words, rem, feats, Q), rem


# N1 pausa longa
w, r, _ = roda([(2.0, "Olá pessoal vamos começar hoje.".split(), 0.3), (8.0, "A notícia é bem interessante mesmo.".split(), 0.3)])
cortes = [x for x in r["removed"] if x["reason"] == "pausa"]
teste("N1 pausa de ~4 s vira corte", len(cortes) == 1, f"{r['removed']}")
if cortes:
    c = cortes[0]
    ult = [x for x in w if x["e"] < 6][-1]
    prox = [x for x in w if x["s"] > 7][0]
    teste("N1 corte a >= 80 ms das palavras", c["start"] >= ult["e"] + 0.08 - 1e-6 and c["end"] <= prox["s"] - 0.08 + 1e-6, f"{c} {ult['e']} {prox['s']}")
    teste("N1 deixa respiro (>= 0,1 s dos dois lados)", c["start"] - ult["e"] >= 0.1 and prox["s"] - c["end"] >= 0.1)
# pausa curta não corta
w, r, _ = roda([(2.0, "Olá pessoal.".split(), 0.3), (3.0, "Vamos lá.".split(), 0.3)])
teste("N1 pausa curta (<= pause_max) não vira corte", not [x for x in r["removed"] if x["reason"] == "pausa"], f"{r['removed']}")

# N2 regravação por início repetido
w, r, rem = roda([(2.0, "Primeiramente com relação ao email eu fiz uma busca aqui".split(), 0.25), (9.0, "Primeiramente com relação ao email eu fiz a busca completa".split(), 0.25)])
txt = " ".join(x["w"] for x in w if any(a <= x["s"] < b for a, b in r["kept"]))
teste("N2 fica só a última versão da frase", txt.count("Primeiramente") == 1 and "completa" in txt, txt)

# N3 sufixo repetido
w, r, _ = roda([(2.0, "Aqui tem eventos esportivos é uma".split(), 0.25), (6.0, "é uma plataforma famosa no Brasil".split(), 0.25)], margin_tiers=[0.08, 0.04])  # fala colada (0,1 s entre palavras): só com margem menor
txt = " ".join(x["w"] for x in w if any(a <= x["s"] < b for a, b in r["kept"]))
teste("N3 sufixo repetido sai do enunciado anterior", txt.count("é uma") == 1 and "plataforma" in txt and "esportivos" in txt, txt)

# N4 reticências
w, r, _ = roda([(2.0, "Acredito que a proporção não seja...".split(), 0.25), (8.0, "Acredito que o impacto não seja grande.".split(), 0.25)])
txt = " ".join(x["w"] for x in w if any(a <= x["s"] < b for a, b in r["kept"]))
teste("N4 frase com reticências sai", "proporção" not in txt and "impacto" in txt, txt)

# N5 fragmento sem ponto vs frase curta com ponto
w, r, _ = roda([(2.0, "Isso é importante.".split(), 0.25), (5.0, ["mas"], 0.25), (8.0, "Agora vamos ver o caso de hoje.".split(), 0.25), (12.0, ["Tá."], 0.25), (15.0, "Seguindo em frente com o assunto.".split(), 0.25)])
txt = " ".join(x["w"] for x in w if any(a <= x["s"] < b for a, b in r["kept"]))
teste("N5 fragmento 'mas' sai", " mas " not in f" {txt} ", txt)
teste("N5 'Tá.' com ponto final fica", "Tá." in txt, txt)

# N6 comando falado
w, r, _ = roda([(2.0, "Então a empresa disse que o erro foi".split(), 0.25), (8.0, ["corta"], 0.3), (12.0, "A empresa informou que houve falha.".split(), 0.25)])
txt = " ".join(x["w"] for x in w if any(a <= x["s"] < b for a, b in r["kept"]))
teste("N6 comando remove a tentativa que falhou e o próprio comando", "corta" not in txt and "erro" not in txt and "informou" in txt, txt)

# N7/N8/N9 invariantes
k = r["kept"]
teste("N7 trechos mantidos em ordem e sem sobreposição", all(k[i][1] <= k[i + 1][0] + 1e-9 for i in range(len(k) - 1)) and all(a < b for a, b in k), str(k))
teste("N8 corta antes da 1ª fala (pre-roll) e depois da última", k[0][0] > 0.5 and k[-1][1] < 40.0, str((k[0], k[-1])))
fps = P["fps_out"]
teste("N9 tempos na grade de 60 fps", all(abs(t * fps - round(t * fps)) < 1e-6 for a, b in k for t in (a, b)), str(k[:2]))

print("\n".join(f"  ok    {n}" for n in ok))
if falhas:
    print("\nFALHOU:\n  - " + "\n  - ".join(falhas))
    sys.exit(1)
print(f"\nOK: {len(ok)} verificações do tipo NEWS passaram")
