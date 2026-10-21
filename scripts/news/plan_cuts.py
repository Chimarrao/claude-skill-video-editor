#!/usr/bin/env python3
"""NEWS · PASSO 3 — o "editor": decide os cortes a partir da transcrição alinhada, da energia do áudio e do movimento da tela.

Uso: python plan_cuts.py "<pasta do episódio>" [--params news_params.json] [--out work/cuts.json]
Entrada (em <pasta>/work/): transcription.json (palavras alinhadas), features.npz (media_features.py).
Saída: cuts.json = {kept:[[ini,fim]...], removed:[{start,end,reason,text,confira}...], stats} em SEGUNDOS no arquivo fundido (= bruto).
Regras (ver SKILL.md → TIPO: News): ordem nunca muda; só se remove; regravação → fica a ÚLTIMA versão completa; comando falado, falso começo,
explicação refeita (só com alta certeza; senão vai para CONFIRA), pausas > pause_max encurtadas deixando respiro, início/fim; o corte cai em silêncio."""

import argparse, json, os, re, sys, unicodedata
from difflib import SequenceMatcher

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from news_lib import mmss  # noqa: E402


def norm(w):
    """Palavra sem acento/pontuação, minúscula."""
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))


def carrega_palavras(tr):
    """Lista plana de palavras {w, n, s, e, p} (texto, normalizada, início, fim, probabilidade)."""
    out = []
    for seg in tr["segments"]:
        for w in seg["words"]:
            t = w["word"].strip()
            if not t:
                continue
            out.append(dict(w=t, n=norm(t), s=float(w["start"]), e=float(w["end"]), p=float(w.get("prob", 1.0))))
    # o alinhamento às vezes erra o tempo de uma palavra curta (cai DENTRO da vizinha): força tempos monotônicos e sem sobreposição
    for k in range(1, len(out)):
        if out[k]["s"] < out[k - 1]["e"]:
            out[k]["s"] = out[k - 1]["e"]
        if out[k]["e"] < out[k]["s"] + 0.02:
            out[k]["e"] = out[k]["s"] + 0.02
    return out


def ajusta_palavras(words, feats, P):
    """O alinhamento forçado ESTICA uma palavra sobre o silêncio vizinho ("ela" com 7,8 s no ep. 05): palavra longa (> word_max_s) é encurtada para o trecho
    onde há fala de verdade (energia > piso + 25 dB). Sem isso a pausa some dos dados e o corte do silêncio nunca é feito."""
    e = feats["energy_db"]
    thr = float(np.percentile(e, 5)) + 25.0
    for w in words:
        if w["e"] - w["s"] <= P.get("word_max_s", 0.9):
            continue
        i0, i1 = int(w["s"] / 0.01), min(int(w["e"] / 0.01), len(e))
        fala = np.where(e[i0:i1] > thr)[0]
        if len(fala) == 0:
            w["e"] = w["s"] + 0.05
            continue
        # a palavra é a PRIMEIRA rajada de fala (lacunas <= 0,3 s dentro dela); rajadas depois do silêncio pertencem às palavras seguintes (alinhadas errado)
        k = 0
        while k + 1 < len(fala) and fala[k + 1] - fala[k] <= 30:
            k += 1
        a, b = i0 + fala[0], i0 + fala[k]
        if a * 0.01 - w["s"] > 0.4:
            w["s"] = max(w["s"], a * 0.01 - 0.03)
        if w["e"] - b * 0.01 > 0.4:
            w["e"] = min(w["e"], b * 0.01 + 0.05)
    return words


def enunciados(words, gap):
    """Agrupa palavras em enunciados: nova quebra quando a pausa antes da palavra >= gap. Devolve lista de (i0, i1) com i1 exclusivo."""
    utts, i0 = [], 0
    for i in range(1, len(words)):
        if words[i]["s"] - words[i - 1]["e"] >= gap:
            utts.append((i0, i))
            i0 = i
    utts.append((i0, len(words)))
    return utts


def texto(words, i0, i1):
    """Texto das palavras [i0, i1)."""
    return " ".join(w["w"] for w in words[i0:i1])


class Remocao:
    """Remoção em índices de palavra [i0, i1) com motivo; `confira` marca corte duvidoso para o relatório."""

    def __init__(self, i0, i1, motivo, confira=False, nota=""):
        self.i0, self.i1, self.motivo, self.confira, self.nota = i0, i1, motivo, confira, nota


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--params", default=os.path.join(HERE, "news_params.json"))
    ap.add_argument("--out")
    ap.add_argument("--features")
    ap.add_argument("--edits", help="JSON do REVISOR (o agente): {remove:[{t0,t1,motivo,confira,nota}] (por PALAVRAS no intervalo), cut:[{t0,t1,motivo,nota}] (por TEMPO exato), keep:[{t0,t1}]} em segundos do bruto; padrão work/edits.json se existir")
    args = ap.parse_args()
    P = json.load(open(args.params))
    pasta = os.path.abspath(args.pasta)
    work = os.path.join(pasta, "work")
    tr = json.load(open(os.path.join(work, "transcription.json")))
    words = carrega_palavras(tr)
    z = np.load(args.features or os.path.join(work, "features.npz"))
    feats = {k: z[k] for k in z.files}  # carrega UMA vez (npz relê e descomprime a cada acesso)
    ajusta_palavras(words, feats, P)
    from news_detect import detecta  # regras de detecção (arquivo separado)
    from news_cuts import constroi, aplica_cortes_tempo  # transforma remoções em intervalos mantidos

    utts = enunciados(words, P["utterance_gap_s"])
    rem = detecta(words, utts, feats, P)
    edits_path = args.edits or os.path.join(work, "edits.json")
    if os.path.exists(edits_path):  # revisão do agente: acrescenta remoções (ex.: explicação refeita) e protege trechos que o script cortou sem querer
        ed = json.load(open(edits_path))
        no = lambda t0, t1: [i for i, w in enumerate(words) if w["s"] >= t0 - 0.03 and w["e"] <= t1 + 0.03]
        for e in ed.get("keep", []):
            prot = set(no(e["t0"], e["t1"]))
            rem = [r for r in rem if not any(i in prot for i in range(r.i0, r.i1))]
        for e in ed.get("remove", []):
            ix = no(e["t0"], e["t1"])
            if ix:
                rem.append(Remocao(ix[0], ix[-1] + 1, e.get("motivo", "revisão"), confira=e.get("confira", False), nota=e.get("nota", "")))
        rem.sort(key=lambda r: (r.i0, r.i1))
    res = constroi(words, rem, feats, P)
    if os.path.exists(edits_path):
        tempos = json.load(open(edits_path)).get("cut", [])
        if tempos:
            res = aplica_cortes_tempo(res, tempos, feats, P)
    out = args.out or os.path.join(work, "cuts.json")
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    k = res["stats"]
    print(f"{len(res['kept'])} trechos mantidos · {k['kept_s']:.1f}s de {k['dur_s']:.1f}s ({100 * k['kept_s'] / k['dur_s']:.0f}%) · {len(res['removed'])} cortes → {out}")


if __name__ == "__main__":
    main()
