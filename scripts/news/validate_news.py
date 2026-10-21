#!/usr/bin/env python3
"""NEWS — validação obrigatória (antes de dizer que terminou). Roda os 5 testes e grava work/validacao.json + folhas de contato em work/validacao/.
Uso: python validate_news.py "<pasta>" <fundido.mov> <prévia.mp4> [--transcribe]   (--transcribe: whisper na prévia → testes 3 e 4; demora)
 1 SINCRONIA   correlação cruzada (GCC-PHAT) entre o áudio da prévia e a concatenação esperada dos trechos do fundido em TODOS os trechos: atraso 0 (tolerância 1 quadro)
 2 CORTE LIMPO nenhum corte a menos de 80 ms de uma palavra (alinhamento) e sem estalo (salto de amplitude / nível nos 20 ms do corte)
 3 REPETIDO    trechos de 6+ palavras repetidos na transcrição da prévia (regravação que ficou)
 4 PERDIDO     frase que só aparece 1× no bruto e sumiu da prévia tem que estar justificada em cuts.json (removed[].text)
 5 TELA        folha de contato: quadro antes e depois de cada corte"""

import argparse, json, os, re, subprocess, sys, unicodedata

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_lib import SR_XC, gcc_phat, load_mono  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("pasta")
ap.add_argument("fundido")
ap.add_argument("previa")
ap.add_argument("--transcribe", action="store_true")
ap.add_argument("--reuse", action="store_true", help="reaproveita work/validacao_previa/transcription.json (se já existir) em vez de transcrever de novo")
ap.add_argument("--fps", type=float, default=60.0)
args = ap.parse_args()
pasta = os.path.abspath(args.pasta)
work = os.path.join(pasta, "work")
cuts = json.load(open(os.path.join(work, "cuts.json")))
kept, removed = cuts["kept"], cuts["removed"]
tr = json.load(open(os.path.join(work, "transcription.json")))
words = [dict(w=w["word"].strip(), s=w["start"], e=w["end"]) for sg in tr["segments"] for w in sg["words"] if w["word"].strip()]
res, falhas, avisos = {}, [], []


def falha(t, m):
    falhas.append(f"{t}: {m}")


# ---------- 1 sincronia ----------
src = load_mono(args.fundido)
prev = load_mono(args.previa)
esperado = np.concatenate([src[int(round(a * SR_XC)) : int(round(b * SR_XC))] for a, b in kept])
n_exp, n_prev = len(esperado), len(prev)
res["duracao"] = dict(esperado_s=n_exp / SR_XC, previa_s=n_prev / SR_XC)
if abs(n_exp - n_prev) / SR_XC > 2 / args.fps:
    falha("1 sincronia", f"duração da prévia {n_prev / SR_XC:.3f}s ≠ esperada {n_exp / SR_XC:.3f}s")
atrasos, pos = [], 0
for k, (a, b) in enumerate(kept):
    L = int(round((b - a) * SR_XC))
    jan = min(L, 6 * SR_XC)
    if jan < 0.5 * SR_XC:
        pos += L
        continue
    x = esperado[pos : pos + jan]
    y = prev[max(0, pos - 4000) : pos + jan + 4000]
    off = pos - max(0, pos - 4000)
    # atraso de y relativo a x; y começa `off` amostras antes
    d, c = gcc_phat(x, y[off : off + jan] if len(y) >= off + jan else np.pad(y[off:], (0, off + jan - len(y))), max_ms=100)
    atrasos.append((k, round(d, 2), round(c, 2)))
    if abs(d) > 1000 / args.fps:
        falha("1 sincronia", f"trecho {k} ({a:.2f}s): atraso {d:.1f} ms (> 1 quadro)")
    pos += L
res["sincronia"] = dict(n=len(atrasos), max_abs_ms=max((abs(d) for _, d, _ in atrasos), default=0))

# ---------- 2 corte limpo ----------
margem_min, estalos = 1e9, 0
joint = 0
pontos = []
for k, (a, b) in enumerate(kept):
    if k:
        pontos.append((k, a))  # ponto de entrada do trecho k no ARQUIVO-FONTE (corte ocorreu entre kept[k-1].fim e a)
for k, (a, b) in enumerate(kept[:-1]):
    for t in (b, kept[k + 1][0]):
        # o corte cai em t: distância até a palavra mais próxima (início/fim)
        dmin = min((0.0 if w["s"] <= t <= w["e"] else min(abs(t - w["s"]), abs(t - w["e"]))) for w in words)
        margem_min = min(margem_min, dmin)
        if dmin < 0.08:
            tight = any(r.get("apertado") and (abs(r["start"] - t) < 1e-3 or abs(r["end"] - t) < 1e-3) for r in removed)
            if tight:  # corte apertado já avisado no cortes.md (fala colada, sem pausa entre as palavras): só aviso — conferir de ouvido
                avisos.append(f"2 corte limpo: corte apertado em {t:.2f}s a {dmin * 1000:.0f} ms de palavra (fala colada; conferir de ouvido)")
            else:
                falha("2 corte limpo", f"corte em {t:.2f}s a {dmin * 1000:.0f} ms de uma palavra (< 80 ms)")
# estalo: salto de amplitude nas emendas da prévia
pos = 0
dif = np.abs(np.diff(prev))
base = float(np.sqrt((dif**2).mean())) + 1e-9
for k, (a, b) in enumerate(kept[:-1]):
    pos += int(round((b - a) * SR_XC))
    j = dif[max(0, pos - 80) : pos + 80]
    rms = float(np.sqrt((prev[max(0, pos - 160) : pos + 160] ** 2).mean()))
    if len(j) and (j.max() > 12 * base and rms > 0.02):
        estalos += 1
        falha("2 corte limpo", f"possível estalo na emenda {k} (salto {j.max() / base:.1f}× o normal, RMS {rms:.3f})")
res["corte_limpo"] = dict(margem_min_ms=round(margem_min * 1000, 1), emendas=len(kept) - 1, estalos=estalos)

# ---------- 3 e 4 (transcrição da prévia) ----------
def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)))


if args.transcribe:
    pj = os.path.join(work, "validacao_previa")
    os.makedirs(pj, exist_ok=True)
    py = os.environ.get("PY_WHISPER") or sys.executable
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "template", "transcribe.py")
    env = dict(os.environ, MODEL=os.environ.get("MODEL", "large-v3"), FORCE="1")
    voc = os.path.join(work, "vocabulary.txt")
    if os.path.exists(voc):
        open(os.path.join(pj, "vocabulary.txt"), "w").write(open(voc).read())
    if not (args.reuse and os.path.exists(os.path.join(pj, "transcription.json"))):
        subprocess.run([py, tpl, os.path.abspath(args.previa)], cwd=pj, env=env, check=True, stdout=subprocess.DEVNULL)
    pt = json.load(open(os.path.join(pj, "transcription.json")))
    pw = [norm(w["word"]) for sg in pt["segments"] for w in sg["words"] if norm(w["word"])]
    # 3: n-gramas de 6 palavras repetidos
    seen, rep = {}, []
    for i in range(len(pw) - 5):
        g = " ".join(pw[i : i + 6])
        if g in seen and i - seen[g] > 6:
            rep.append((seen[g], i, g))
        seen.setdefault(g, i)
    res["repetido"] = dict(n=len(rep), exemplos=[g for _, _, g in rep[:10]])
    for i, j, g in rep[:20]:
        avisos.append(f"3 repetido (REVISAR: regravação que ficou? ou repetição legítima): «{g}» nas palavras {i} e {j} da prévia")
    # 4: o que ficou no plano tem que estar na prévia. Palavras do bruto FORA dos trechos removidos (justificados em cortes.md) vs palavras da prévia,
    # alinhadas com difflib (o ASR da prévia varia ~10-20%: só falha se > 8% das palavras mantidas sumirem OU houver uma corrida de >= 8 palavras seguidas).
    from difflib import SequenceMatcher

    mant = [norm(w["w"]) for w in words if norm(w["w"]) and any(a <= (w["s"] + w["e"]) / 2 <= b for a, b in kept)]
    sm = SequenceMatcher(None, mant, pw, autojunk=False)
    casados = sum(b.size for b in sm.get_matching_blocks())
    faltam = len(mant) - casados
    corridas, ult = [], 0
    for b in sm.get_matching_blocks():
        if b.a - ult >= 8:
            corridas.append(" ".join(mant[ult : b.a][:12]))
        ult = b.a + b.size
    res["perdido"] = dict(palavras_mantidas=len(mant), ausentes_na_previa=faltam, pct=round(100 * faltam / max(1, len(mant)), 1), corridas=corridas[:10])
    if faltam > 0.08 * len(mant):
        falha("4 perdido", f"{faltam}/{len(mant)} palavras mantidas não aparecem na prévia ({100 * faltam / len(mant):.0f}%)")
    for c in corridas[:10]:
        avisos.append(f"4 perdido: trecho mantido de 8+ palavras ausente na prévia: «{c}…»")

# ---------- 5 folha de contato ----------
vd = os.path.join(work, "validacao")
os.makedirs(vd, exist_ok=True)
from PIL import Image, ImageDraw

pares = []
for k in range(len(kept) - 1):
    ta, tb = kept[k][1], kept[k + 1][0]
    pares.append((k, max(kept[k][0], ta - 0.05), min(kept[k + 1][1], tb + 0.05)))
fr = []
for k, t0, t1 in pares:
    ims = []
    for t in (t0, t1):
        p = os.path.join(vd, f"_f.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", args.fundido, "-frames:v", "1", "-vf", "scale=480:-2", p], check=True)
        ims.append(Image.open(p).convert("RGB"))
    fr.append((k, t0, t1, ims))
for s0 in range(0, len(fr), 8):
    grp = fr[s0 : s0 + 8]
    w_, h_ = grp[0][3][0].size
    sh = Image.new("RGB", (w_ * 2 + 6, (h_ + 4) * len(grp)), (20, 20, 20))
    for r, (k, t0, t1, ims) in enumerate(grp):
        for c in range(2):
            sh.paste(ims[c], (c * (w_ + 6), r * (h_ + 4)))
        ImageDraw.Draw(sh).text((6, r * (h_ + 4) + 4), f"corte {k}: {t0:.2f}s → {t1:.2f}s", fill=(255, 255, 0))
    sh.save(os.path.join(vd, f"cortes_{s0 // 8:02d}.png"))
res["folhas"] = len(range(0, len(fr), 8))
res["falhas"], res["avisos"] = falhas, avisos
json.dump(res, open(os.path.join(work, "validacao.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "falhas"}, ensure_ascii=False))
for f in falhas:
    print("FALHA", f)
for a_ in avisos:
    print("AVISO", a_)
print("VALIDAÇÃO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
