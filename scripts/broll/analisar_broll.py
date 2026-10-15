#!/usr/bin/env python3
"""Análise dos vídeos de B-roll (pasta Assets/) -> broll_analise.json + folhas de contato (a "visão" do assistente).
Uso: python analisar_broll.py <pasta_Assets> [--saida broll_analise.json] [--folhas folhas_broll] [--sem-fala]
Por arquivo: ffprobe (dur, resolução, fps, áudio), cortes de cena (scene>0.3), pretos (blackdetect), congelados (freezedetect),
movimento médio (score de cena a 5 fps), transcrição da fala do clipe (faster-whisper, se houver áudio audível) e folhas de contato
(1 frame a cada ~2 s + 1 frame por corte, com carimbo de tempo). Os campos item/nota/avisos_visuais são preenchidos DEPOIS, olhando as folhas.
Trechos candidatos = intervalos entre cortes (curtos são unidos), com score automático."""

import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

VID = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
IMG = {".jpg", ".jpeg", ".png", ".webp"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ffprobe(p):
    r = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,r_frame_rate,codec_name",
            "-of",
            "json",
            str(p),
        ]
    )
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), {})
    num, den = (v.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    return dict(
        duracao=float(d.get("format", {}).get("duration") or 0),
        largura=v.get("width"),
        altura=v.get("height"),
        fps=round(float(num) / max(float(den), 1), 2),
        tem_audio=any(s["codec_type"] == "audio" for s in d.get("streams", [])),
        codec=v.get("codec_name"),
    )


def passada(p, limiar=0.3):
    """UMA única decodificação (360 px, 5 fps): cortes (scene>limiar), pretos, congelados e movimento médio. ~4x mais rápido que 4 passadas."""
    r = run(
        [
            "ffmpeg",
            "-nostats",
            "-threads",
            "0",
            "-i",
            str(p),
            "-an",
            "-vf",
            "fps=5,scale=360:-2,blackdetect=d=0.4:pix_th=0.1,freezedetect=n=0.003:d=1.5,select='gte(scene,0)',metadata=print:key=lavfi.scene_score",
            "-f",
            "null",
            "-",
        ]
    )
    txt = r.stderr
    pares = re.findall(r"pts_time:([\d.]+)\s*\n[^\n]*scene_score=([\d.]+)", txt)
    cortes_ = [round(float(t), 2) for t, sc in pares if float(sc) > limiar]
    mov_ = [float(sc) for t, sc in pares if float(sc) <= limiar]

    def inter(chave):
        ini = [float(x) for x in re.findall(chave + r"_start: ([\d.]+)", txt)]
        fim = [float(x) for x in re.findall(chave + r"_end: ([\d.]+)", txt)]
        return [[round(x, 2), round(y, 2)] for x, y in zip(ini, fim)] + (
            [[round(ini[-1], 2), None]] if len(ini) > len(fim) else []
        )

    return cortes_, inter("black"), inter("freeze"), (round(sum(mov_) / len(mov_), 4) if mov_ else 0.0)


def volume_medio(p):
    r = run(["ffmpeg", "-nostats", "-i", str(p), "-af", "volumedetect", "-vn", "-f", "null", "-"])
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else -91.0


def _db():
    return Path(__file__).resolve().parent.parent / "assets_db.py"


def transcrever(p):
    # cache no banco (SHA-1 do arquivo + modelo)
    modelo = os.environ.get("MODELO", "small")
    cache = Path(tempfile.mktemp(suffix=".json"))
    if (
        subprocess.run(
            [sys.executable, str(_db()), "trans-buscar", str(p), "--saida", str(cache)], capture_output=True
        ).returncode
        == 0
    ):
        return json.load(open(cache))
    r = _transcrever(p)
    if r is not None:
        json.dump(r, open(cache, "w"), ensure_ascii=False)
        subprocess.run(
            [
                sys.executable,
                str(_db()),
                "trans-salvar",
                str(cache),
                str(p),
                "--modelo",
                modelo,
                "--nota",
                "clipe de B-roll",
            ],
            capture_output=True,
        )
    return r


def _transcrever(p):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    import numpy as np

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True,
    ).stdout
    w = np.frombuffer(raw, dtype=np.float32)[
        : int(float(os.environ.get("FALA_MAX", 600)) * 16000)
    ]  # só os primeiros FALA_MAX s (padrão 600) p/ não demorar em vídeos longos
    m = WhisperModel(os.environ.get("MODELO", "small"), device="cpu", compute_type="int8")
    segs, info = m.transcribe(w, beam_size=3, vad_filter=True, condition_on_previous_text=False)
    return dict(
        idioma=info.language,
        segmentos=[dict(inicio=round(s.start, 2), fim=round(s.end, 2), texto=s.text.strip()) for s in segs],
    )


def folha(p, dur, cortes_, destino, nome, passo=2.0, por_folha=24, max_frames=150):
    from PIL import Image, ImageDraw

    passo = max(
        passo, dur / max_frames
    )  # vídeos longos: passo adaptativo (≤ ~150 quadros); detalhe de um trecho: folha_trecho.py
    if len(cortes_) > max_frames // 2:
        cortes_ = cortes_[:: max(1, len(cortes_) // (max_frames // 2))]
    ts = sorted(
        set([round(i * passo, 2) for i in range(int(dur / passo) + 1)] + [round(c + 0.1, 2) for c in cortes_])
    )
    ts = [t for t in ts if t < max(dur - 0.05, 0.1)] or [0.0]
    destino.mkdir(parents=True, exist_ok=True)
    saidas = []
    W, H, cols = 320, 180, 6
    for k in range(0, len(ts), por_folha):
        bloco = ts[k : k + por_folha]
        rows = (len(bloco) + cols - 1) // cols
        sh = Image.new("RGB", (W * cols, (H + 4) * rows), (30, 30, 30))
        d = ImageDraw.Draw(sh)
        for j, t in enumerate(bloco):
            tmp = tempfile.mktemp(suffix=".jpg")
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(t),
                    "-i",
                    str(p),
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
                    tmp,
                ]
            )
            if os.path.exists(tmp):
                sh.paste(Image.open(tmp), ((j % cols) * W, (j // cols) * (H + 4)))
                os.remove(tmp)
            d.rectangle(
                ((j % cols) * W, (j // cols) * (H + 4), (j % cols) * W + 70, (j // cols) * (H + 4) + 16),
                fill=(0, 0, 0),
            )
            d.text(
                ((j % cols) * W + 3, (j // cols) * (H + 4) + 2),
                f"{t:.1f}s" + ("*" if any(abs(t - c - 0.1) < 0.01 for c in cortes_) else ""),
                fill=(255, 255, 0),
            )
        f = destino / f"{nome}_{k // por_folha + 1}.png"
        sh.save(f)
        saidas.append(str(f))
    return saidas


def trechos(dur, cortes_, pretos, congelados, mov):
    pts = [0.0] + [c for c in cortes_ if 0 < c < dur] + [dur]
    segs = [[a, b] for a, b in zip(pts, pts[1:])]
    uni = []  # une trechos < 3 s ao vizinho
    for a, b in segs:
        if uni and (b - a) < 3.0:
            uni[-1][1] = b
        else:
            uni.append([a, b])
    if len(uni) > 1 and (uni[0][1] - uni[0][0]) < 3.0:
        uni[1][0] = uni[0][0]
        uni.pop(0)
    out = []
    for a, b in uni:

        def cobre(lst):
            return sum(max(0, min(b, y if y is not None else dur) - max(a, x)) for x, y in lst) / max(
                b - a, 0.01
            )

        avisos = []
        if cobre(pretos) > 0.15:
            avisos.append("tela preta")
        if cobre(congelados) > 0.3:
            avisos.append("congelado")
        out.append(dict(inicio=round(a, 2), fim=round(b, 2), duracao=round(b - a, 2), avisos_auto=avisos))
    return out


def velocidade_sugerida(mov, tem_fala):
    if tem_fala:
        return 1.0
    return 2.0 if mov < 0.012 else 1.5


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--saida", default="broll_analise.json")
    ap.add_argument("--folhas", default="folhas_broll")
    ap.add_argument("--sem-fala", action="store_true")
    a = ap.parse_args()
    pasta = Path(a.pasta)
    res = []
    for f in sorted(pasta.rglob("*")):
        if f.name.startswith(".") or f.suffix.lower() not in VID | IMG:
            continue
        print("analisando", f.name, flush=True)
        if f.suffix.lower() in IMG:
            res.append(
                dict(
                    arquivo=str(f),
                    tipo="imagem",
                    notas="imagem estática: usar só como still (≥3 s), sem velocidade",
                )
            )
            continue
        info = ffprobe(f)
        c, pr, cg, mov = passada(f)
        vol = volume_medio(f) if info["tem_audio"] else -91.0
        fala = None if (a.sem_fala or vol < -42) else transcrever(f)
        tem_fala = bool(fala and sum(len(s["texto"]) for s in fala["segmentos"]) > 25)
        tr = trechos(info["duracao"], c, pr, cg, mov)
        for t in tr:
            t.update(
                item=None,
                nota=None,
                avisos_visuais=[],
                ritmo=("lento" if mov < 0.012 else "movimentado"),
                velocidade_sugerida=velocidade_sugerida(mov, tem_fala),
            )
        res.append(
            dict(
                arquivo=str(f),
                tipo="video",
                **info,
                cortes=c,
                pretos=pr,
                congelados=cg,
                movimento=mov,
                volume_medio_db=vol,
                fala=fala,
                folhas=folha(f, info["duracao"], c, Path(a.folhas), f.stem),
                trechos=tr,
            )
        )
    json.dump(res, open(a.saida, "w"), ensure_ascii=False, indent=1)
    print(f"{len(res)} arquivo(s) -> {a.saida}; folhas em {a.folhas}/")
