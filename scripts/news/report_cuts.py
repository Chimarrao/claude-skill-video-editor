#!/usr/bin/env python3
"""NEWS — relatório dos cortes: `cortes.md` na pasta do episódio (tabela de cada corte + lista CONFIRA) e resumo curto para o chat.
Uso: python report_cuts.py "<pasta do episódio>" [--nome "News NN - tema"]
Colunas: nº · tempo no bruto · duração · motivo (regravação / falso começo / comando / explicação refeita / pausa / início-fim) · texto removido.
CONFIRA: regravações em que a versão que FICOU é bem mais curta ou menos confiável que a removida (regra 3), explicações refeitas (regra 6),
remoções com texto > 20 s e qualquer corte marcado `confira` pelo editor ou pelo revisor."""

import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_lib import mmss

ap = argparse.ArgumentParser()
ap.add_argument("pasta")
ap.add_argument("--nome", default="")
ap.add_argument("--out", help="caminho do cortes.md (padrão: <pasta>/cortes.md)")
args = ap.parse_args()
pasta = os.path.abspath(args.pasta)
work = os.path.join(pasta, "work")
cuts = json.load(open(os.path.join(work, "cuts.json")))
tr = json.load(open(os.path.join(work, "transcription.json")))
words = [(w["start"], w["end"], w["word"].strip(), w.get("prob", 1.0)) for s in tr["segments"] for w in s["words"] if w["word"].strip()]
st = cuts["stats"]
rem = cuts["removed"]
pct = 100 * st["kept_s"] / st["dur_s"]


def depois(t, n=14):
    """Texto das n palavras que FICAM logo depois do corte (a versão mantida)."""
    ws = [w for w in words if w[0] >= t - 0.02][:n]
    return " ".join(w[2] for w in ws), (sum(w[3] for w in ws) / len(ws) if ws else 1.0)


linhas, confira = [], []
for k, r in enumerate(rem, 1):
    d = r["end"] - r["start"]
    txt = r.get("text", "")
    nota = r.get("nota", "")
    flag = bool(r.get("confira"))
    motivo = r["reason"]
    if "regravação" in motivo and txt:
        fica, prob = depois(r["end"])
        nw_rem, nw_fica = len(txt.split()), len(fica.split())
        if nw_rem > 1.5 * max(nw_fica, 1) or prob < 0.6:
            flag = True
            nota += f" fica: «{fica}»" + (f" (confiança baixa {prob:.2f})" if prob < 0.6 else "")
    if "explicação" in motivo or (len(txt.split()) > 0 and d > 20):
        flag = True
    linhas.append((k, r["start"], d, motivo, txt, nota, flag))
    if flag:
        confira.append(k)
por_motivo = {}
for r in rem:
    por_motivo.setdefault(r["reason"].split(" + ")[0], []).append(r["end"] - r["start"])
md = [
    f"# Cortes — {args.nome or os.path.basename(pasta)}",
    "",
    f"- Bruto: **{mmss(st['dur_s'])}** → mantido **{mmss(st['kept_s'])}** (**{pct:.0f}%**) · {len(cuts['kept'])} trechos · {len(rem)} cortes",
    "- Por motivo: " + " · ".join(f"{m}: {len(v)} ({sum(v):.0f}s)" for m, v in sorted(por_motivo.items(), key=lambda x: -sum(x[1]))),
    "",
    "| # | tempo no bruto | dur. | motivo | texto removido / nota | confira |",
    "|---|---|---|---|---|---|",
]
for k, t, d, mo, txt, nota, flag in linhas:
    md.append(f"| {k} | {mmss(t)} | {d:.1f}s | {mo} | {(txt[:140] + ('…' if len(txt) > 140 else '')) if txt else ''}{(' · ' + nota.strip()) if nota.strip() else ''} | {'⚠️' if flag else ''} |".replace("\n", " "))
md += ["", "## CONFIRA (cortes duvidosos)", ""]
md += [f"- **#{k}** {mmss(t)} ({d:.1f}s) {mo}: «{txt[:160]}» {nota.strip()}" for k, t, d, mo, txt, nota, flag in linhas if flag] or ["- (nenhum)"]
open(args.out or os.path.join(pasta, "cortes.md"), "w", encoding="utf8").write("\n".join(md) + "\n")
print(f"cortes.md: {pct:.0f}% mantido · {len(rem)} cortes · {len(confira)} para conferir")
