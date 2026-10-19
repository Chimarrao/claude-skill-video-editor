#!/usr/bin/env python3
"""NEWS · PASSO 4b — prévia renderizada `PRONTO_auto.mp4`: os MESMOS cortes (cuts.json) em ffmpeg, com precisão de quadro (re-encode, nunca -c copy).
Formato igual aos finais do usuário: 1920x1080, 60 fps, HEVC (hvc1), AAC 44,1 kHz estéreo, -23 LUFS integrados.
Uso: python render_preview.py <fundido.mov> <cuts.json> <saida.mp4> [--encoder hevc_videotoolbox|libx265] [--crf 20]"""

import argparse, json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_lib import loudness  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("fundido")
ap.add_argument("cuts")
ap.add_argument("saida")
ap.add_argument("--encoder", default="hevc_videotoolbox")
ap.add_argument("--bitrate", default="14M")
ap.add_argument("--crf", default="20")
args = ap.parse_args()
kept = json.load(open(args.cuts))["kept"]


def filtro(kept, so_audio=False):
    """filter_complex com trim/atrim de cada trecho + concat (vídeo escalado para 1920x1080 a 60 fps)."""
    partes, ins = [], ""
    for k, (a, b) in enumerate(kept):
        if not so_audio:
            partes.append(f"[0:v]trim=start={a:.5f}:end={b:.5f},setpts=PTS-STARTPTS,fps=60,scale=1920:1080:flags=lanczos[v{k}]")
        partes.append(f"[0:a]atrim=start={a:.5f}:end={b:.5f},asetpts=PTS-STARTPTS,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{k}]")
        ins += (f"[v{k}]" if not so_audio else "") + f"[a{k}]"
    partes.append(f"{ins}concat=n={len(kept)}:v={0 if so_audio else 1}:a=1{'' if so_audio else '[v]'}[a]")
    return ";".join(partes)


# 1) loudness do áudio já cortado (para o ganho final): renderiza só o áudio num wav temporário
tmp = tempfile.mkdtemp(prefix="news_prev_")
wav = os.path.join(tmp, "a.wav")
fs = os.path.join(tmp, "f_audio.txt")
open(fs, "w").write(filtro(kept, so_audio=True))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.fundido, "-/filter_complex", fs, "-map", "[a]", "-c:a", "pcm_f32le", wav], check=True)
lo = loudness(wav)
ganho = -23.0 - lo["I"]
if lo["TP"] + ganho > -1.5:
    ganho = -1.5 - lo["TP"]
print(f"loudness dos cortes: {lo['I']:.1f} LUFS (TP {lo['TP']:.1f}) → ganho {ganho:+.2f} dB")

# 2) render final
ff = os.path.join(tmp, "f.txt")
txt = filtro(kept) + f";[a]volume={ganho:.3f}dB[af]"
open(ff, "w").write(txt)
enc = ["-c:v", args.encoder, "-b:v", args.bitrate, "-tag:v", "hvc1"] if args.encoder == "hevc_videotoolbox" else ["-c:v", "libx265", "-crf", args.crf, "-preset", "medium", "-tag:v", "hvc1", "-x265-params", "log-level=error"]
cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", args.fundido, "-/filter_complex", ff, "-map", "[v]", "-map", "[af]", *enc, "-pix_fmt", "yuv420p", "-r", "60", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", args.saida]
subprocess.run(cmd, check=True)
final = loudness(args.saida)
print("prévia:", args.saida, "· loudness final:", final)
