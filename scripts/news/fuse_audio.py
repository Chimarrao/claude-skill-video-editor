#!/usr/bin/env python3
"""NEWS · PASSO 1 — funde o áudio tratado (.wav do iZotope) no vídeo bruto SEM re-encode do vídeo.

Uso:  python fuse_audio.py "<pasta do episódio>" [--video X.mov] [--wav Y.wav] [--out Z.mov] [--force-out]
Faz: (1) acha vídeo bruto + .wav (vários candidatos → sai com código 3 e lista: PERGUNTE ao usuário);
     (2) mede o atraso entre o áudio do vídeo e o .wav em 3 pontos (GCC-PHAT); > 20 ms → compensa e registra;
     (3) `ffmpeg -map 0:v:0 -map 1:a:0 -c:v copy -c:a pcm_s24le`; (4) valida duração (≤ 0,15 s do bruto; o wav costuma ser ~0,04 s mais curto)
     e mede o atraso de novo no fundido; (5) mede loudness (ebur128) e, se fora de -24…-22 LUFS, aplica loudnorm em 2 passadas (-23 LUFS / TP -1,5).
Nunca sobrescreve um `*-limpo.mov` existente: se já houver, grava `*-limpo-auto.mov` (ou use --out). Relatório: work/fuse_report.json
"""

import argparse, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_lib import *  # noqa

ap = argparse.ArgumentParser()
ap.add_argument("pasta")
ap.add_argument("--video")
ap.add_argument("--wav")
ap.add_argument("--out")
ap.add_argument("--target", type=float, default=-23.0)
ap.add_argument("--limite-atraso-ms", type=float, default=20.0)
args = ap.parse_args()

pasta = os.path.abspath(args.pasta)
vids, wavs = achar_candidatos(pasta)
video = args.video or (vids[0] if len(vids) == 1 else None)
wav = args.wav or (wavs[0] if len(wavs) == 1 else None)
if not video or not wav:
    print("CANDIDATOS AMBÍGUOS — pergunte ao usuário qual usar:")
    print("  vídeos:", *vids, sep="\n    ")
    print("  áudios:", *wavs, sep="\n    ")
    sys.exit(3)
video, wav = os.path.abspath(video), os.path.abspath(wav)
base = os.path.splitext(video)[0]
out = args.out or base + "-limpo.mov"
if not args.out and os.path.exists(out):
    out = base + "-limpo-auto.mov"  # nunca sobrescreve o -limpo.mov que o usuário já pode ter aberto no CapCut
work = work_dir(pasta)
rep = dict(video=video, wav=wav, out=out)

dv, dw = duration(video), duration(wav)
rep.update(dur_video=dv, dur_wav=dw)
print(f"vídeo {dv:.3f}s · wav {dw:.3f}s")

# (2) sincronia antes
antes = medir_atraso(video, wav, min(dv, dw))
rep["atraso_antes"] = antes
print("atraso wav vs vídeo (t, ms, confiança):", antes)
if min(c for _, _, c in antes) < 0.3:
    print("AVISO: correlação fraca em algum ponto — confira a sincronia ouvindo/olhando antes de seguir")
ds = [d for _, d, _ in antes]
med = float(sorted(ds)[1])
if max(ds) - min(ds) > 20:
    print("AVISO: o atraso varia entre os pontos (deriva); o script usa a mediana, mas confira")
off = med if abs(med) > args.limite_atraso_ms else 0.0
rep["compensacao_ms"] = off

# (5) loudness do wav (decide a normalização)
lw = loudness(wav)
rep["loudness_wav"] = lw
print("loudness do wav:", lw)
af = []
if not (-24.0 <= lw["I"] <= -22.0):
    # loudnorm em 2 passadas (mede, depois aplica linear)
    r = subprocess.run(
        ["ffmpeg", "-nostats", "-i", wav, "-af", f"loudnorm=I={args.target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True
    )
    j = json.loads(r.stderr[r.stderr.rfind("{") : r.stderr.rfind("}") + 1])
    af = [
        "-af",
        f"loudnorm=I={args.target}:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true",
    ]
    rep["loudnorm"] = j
    print(f"loudnorm 2 passadas: {lw['I']} → {args.target} LUFS")

# (3) fusão
cmd = ["ffmpeg", "-v", "error", "-y", "-i", video]
if off > 0:  # wav atrasado em relação ao vídeo: pula o início do wav
    cmd += ["-ss", f"{off / 1000:.4f}", "-i", wav]
elif off < 0:  # wav adiantado: atrasa o wav
    cmd += ["-itsoffset", f"{-off / 1000:.4f}", "-i", wav]
else:
    cmd += ["-i", wav]
cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "pcm_s24le"] + af + ["-shortest", out]
run(cmd)
print("fundido:", out)

# (4) validação
do = duration(out)
rep["dur_out"] = do
ok_dur = abs(do - dv) <= 0.15
depois = medir_atraso(wav, out, min(do, dw))
rep["atraso_depois"] = depois
print(f"duração fundido {do:.3f}s (bruto {dv:.3f}s) → {'ok' if ok_dur else 'DIVERGE'}")
print("atraso fundido vs wav:", depois)
lo = loudness(out)
rep["loudness_out"] = lo
print("loudness do fundido:", lo)
rep["ok"] = bool(ok_dur and all(abs(d) <= 20 for _, d, _ in depois))
json.dump(rep, open(os.path.join(work, "fuse_report.json"), "w"), indent=1)
print("RESULTADO:", "OK" if rep["ok"] else "FALHOU")
sys.exit(0 if rep["ok"] else 1)
