#!/usr/bin/env python3
"""Análise dos vídeos de B-roll (pasta Assets/) -> broll_analysis.json + folhas de contato (a "visão" do assistente).
Uso: python analyze_broll.py <folder> [--output broll_analysis.json] [--contact-sheets sheets_broll] [--no-speech]
Por arquivo: ffprobe (dur, resolução, fps, áudio), cortes de cena (scene>0.3), pretos (blackdetect), congelados (freezedetect),
movimento médio (score de cena a 5 fps), transcrição da fala do clipe (faster-whisper, se houver áudio audível) e folhas de contato
(1 frame a cada ~2 s + 1 frame por corte, com carimbo de tempo). Os campos item/nota/warnings_visual são preenchidos DEPOIS, olhando as folhas.
Trechos candidatos = intervalos entre cortes (curtos são unidos), com score automático."""

import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def run(cmd, **kw):
    """Executa um comando capturando saída como texto."""
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ffprobe(path):
    """Duração, resolução, fps, codec e se tem áudio do arquivo (via ffprobe)."""
    r = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,r_frame_rate,codec_name",
            "-of",
            "json",
            str(path),
        ]
    )
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), {})
    num, den = (v.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    return dict(
        duration=float(d.get("format", {}).get("duration") or 0),
        width=v.get("width"),
        height=v.get("height"),
        fps=round(float(num) / max(float(den), 1), 2),
        has_audio=any(s["codec_type"] == "audio" for s in d.get("streams", [])),
        codec=v.get("codec_name"),
    )


def single_pass(path, threshold=0.3):
    """UMA única decodificação (360 px, 5 fps): cortes (scene>threshold), pretos, congelados e movimento médio. ~4x mais rápido que 4 passadas."""
    r = run(
        [
            "ffmpeg",
            "-nostats",
            "-threads",
            "0",
            "-i",
            str(path),
            "-an",
            "-vf",
            "fps=5,scale=360:-2,blackdetect=d=0.4:pix_th=0.1,freezedetect=n=0.003:d=1.5,select='gte(scene,0)',metadata=print:key=lavfi.scene_score",
            "-f",
            "null",
            "-",
        ]
    )
    txt = r.stderr
    pairs = re.findall(r"pts_time:([\d.]+)\s*\n[^\n]*scene_score=([\d.]+)", txt)
    cuts = [round(float(t), 2) for t, sc in pairs if float(sc) > threshold]
    motion_scores = [float(sc) for t, sc in pairs if float(sc) <= threshold]

    def get_intervals(key):
        """Extrai os intervalos [início, fim] de um detector do ffmpeg (blackdetect/freezedetect)."""
        starts = [float(x) for x in re.findall(key + r"_start: ([\d.]+)", txt)]
        ends = [float(x) for x in re.findall(key + r"_end: ([\d.]+)", txt)]
        return [[round(x, 2), round(y, 2)] for x, y in zip(starts, ends)] + (
            [[round(starts[-1], 2), None]] if len(starts) > len(ends) else []
        )

    return cuts, get_intervals("black"), get_intervals("freeze"), (round(sum(motion_scores) / len(motion_scores), 4) if motion_scores else 0.0)


def mean_volume(path):
    """Volume médio em dB (volumedetect); −91 se não houver áudio."""
    r = run(["ffmpeg", "-nostats", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"])
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else -91.0


def _db():
    """Caminho do `assets_db.py` da skill (cache de transcrições)."""
    return Path(__file__).resolve().parent.parent / "assets_db.py"


def transcribe(path):
    # cache no banco (SHA-1 do arquivo + modelo)
    """Transcreve o áudio do clipe reaproveitando o cache do banco (SHA-1 + modelo); salva o resultado novo no banco."""
    model = os.environ.get("MODEL", "small")
    cache = Path(tempfile.mktemp(suffix=".json"))
    if (
        subprocess.run(
            [sys.executable, str(_db()), "transcript-find", str(path), "--output", str(cache)], capture_output=True
        ).returncode
        == 0
    ):
        return json.load(open(cache))
    r = _transcribe(path)
    if r is not None:
        json.dump(r, open(cache, "w"), ensure_ascii=False)
        subprocess.run(
            [
                sys.executable,
                str(_db()),
                "transcript-save",
                str(cache),
                str(path),
                "--model",
                model,
                "--note",
                "clipe de B-roll",
            ],
            capture_output=True,
        )
    return r


def _transcribe(path):
    """Transcrição propriamente dita com faster-whisper (primeiros `SPEECH_MAX` s); `None` se a lib não estiver instalada."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    import numpy as np

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True,
    ).stdout
    w = np.frombuffer(raw, dtype=np.float32)[
        : int(float(os.environ.get("SPEECH_MAX", 600)) * 16000)
    ]  # só os primeiros SPEECH_MAX s (padrão 600) p/ não demorar em vídeos longos
    m = WhisperModel(os.environ.get("MODEL", "small"), device="cpu", compute_type="int8")
    segments, info = m.transcribe(w, beam_size=3, vad_filter=True, condition_on_previous_text=False)
    return dict(
        language=info.language,
        segments=[dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip()) for s in segments],
    )


def contact_sheet(path, duration, cuts, dest, name, step=2.0, per_sheet=24, max_frames=150):
    """Gera folhas de contato do vídeo (1 quadro a cada ~2 s + 1 por corte, carimbados com o tempo) para o Claude olhar."""
    from PIL import Image, ImageDraw

    step = max(
        step, duration / max_frames
    )  # vídeos longos: passo adaptativo (≤ ~150 quadros); detalhe de um trecho: segment_sheet.py
    if len(cuts) > max_frames // 2:
        cuts = cuts[:: max(1, len(cuts) // (max_frames // 2))]
    timestamps = sorted(
        set([round(i * step, 2) for i in range(int(duration / step) + 1)] + [round(c + 0.1, 2) for c in cuts])
    )
    timestamps = [t for t in timestamps if t < max(duration - 0.05, 0.1)] or [0.0]
    dest.mkdir(parents=True, exist_ok=True)
    outputs = []
    W, H, cols = 320, 180, 6
    for k in range(0, len(timestamps), per_sheet):
        block = timestamps[k : k + per_sheet]
        rows = (len(block) + cols - 1) // cols
        sheet = Image.new("RGB", (W * cols, (H + 4) * rows), (30, 30, 30))
        draw = ImageDraw.Draw(sheet)
        for j, t in enumerate(block):
            tmp = tempfile.mktemp(suffix=".jpg")
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(t),
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
                    tmp,
                ]
            )
            if os.path.exists(tmp):
                sheet.paste(Image.open(tmp), ((j % cols) * W, (j // cols) * (H + 4)))
                os.remove(tmp)
            draw.rectangle(
                ((j % cols) * W, (j // cols) * (H + 4), (j % cols) * W + 70, (j // cols) * (H + 4) + 16),
                fill=(0, 0, 0),
            )
            draw.text(
                ((j % cols) * W + 3, (j // cols) * (H + 4) + 2),
                f"{t:.1f}s" + ("*" if any(abs(t - c - 0.1) < 0.01 for c in cuts) else ""),
                fill=(255, 255, 0),
            )
        f = dest / f"{name}_{k // per_sheet + 1}.png"
        sheet.save(f)
        outputs.append(str(f))
    return outputs


def build_segments(duration, cuts, blacks, frozen, motion):
    """Divide o vídeo nos cortes de cena, une trechos < 3 s e marca avisos automáticos (tela preta, congelado, sem movimento)."""
    bounds = [0.0] + [c for c in cuts if 0 < c < duration] + [duration]
    segments = [[a, b] for a, b in zip(bounds, bounds[1:])]
    merged = []  # une trechos < 3 s ao vizinho
    for a, b in segments:
        if merged and (b - a) < 3.0:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    if len(merged) > 1 and (merged[0][1] - merged[0][0]) < 3.0:
        merged[1][0] = merged[0][0]
        merged.pop(0)
    out = []
    for a, b in merged:

        def covers(items_list):
            """Fração do trecho [a, b] coberta pelos intervalos detectados."""
            return sum(max(0, min(b, y if y is not None else duration) - max(a, x)) for x, y in items_list) / max(
                b - a, 0.01
            )

        warnings = []
        if covers(blacks) > 0.15:
            warnings.append("tela preta")
        if covers(frozen) > 0.3:
            warnings.append("frozen")
        out.append(dict(start=round(a, 2), end=round(b, 2), duration=round(b - a, 2), warnings_auto=warnings))
    return out


def suggested_speed(motion, has_speech):
    """Velocidade sugerida no CapCut: 1x se há fala, 2x se quase não há movimento, senão 1,5x."""
    if has_speech:
        return 1.0
    return 2.0 if motion < 0.012 else 1.5


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--output", default="broll_analysis.json")
    parser.add_argument("--contact-sheets", default="sheets_broll")
    parser.add_argument("--no-speech", action="store_true")
    args = parser.parse_args()
    folder = Path(args.folder)
    results = []
    for file in sorted(folder.rglob("*")):
        if file.name.startswith(".") or file.suffix.lower() not in VIDEO_EXTS | IMAGE_EXTS:
            continue
        print("analyzing", file.name, flush=True)
        if file.suffix.lower() in IMAGE_EXTS:
            results.append(
                dict(
                    file=str(file),
                    kind="image",
                    scores="imagem estática: usar só como still (≥3 s), sem velocidade",
                )
            )
            continue
        info = ffprobe(file)
        cuts, blacks, frozen, motion = single_pass(file)
        volume = mean_volume(file) if info["has_audio"] else -91.0
        speech = None if (args.no_speech or volume < -42) else transcribe(file)
        has_speech = bool(speech and sum(len(s["text"]) for s in speech["segments"]) > 25)
        segments = build_segments(info["duration"], cuts, blacks, frozen, motion)
        for segment in segments:
            segment.update(
                item=None,
                score=None,
                warnings_visual=[],
                rhythm=("slow" if motion < 0.012 else "busy"),
                speed_suggested=suggested_speed(motion, has_speech),
            )
        results.append(
            dict(
                file=str(file),
                kind="video",
                **info,
                cortes=cuts,
                blacks=blacks,
                frozen=frozen,
                motion=motion,
                volume_medio_db=volume,
                speech=speech,
                sheets=contact_sheet(file, info["duration"], cuts, Path(args.contact_sheets), file.stem),
                spans=segments,
            )
        )
    json.dump(results, open(args.output, "w"), ensure_ascii=False, indent=1)
    print(f"{len(results)} arquivo(s) -> {args.output}; folhas em {args.contact_sheets}/")
