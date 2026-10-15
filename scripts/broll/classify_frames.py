#!/usr/bin/env python3
"""FILTRO VISUAL DE B-ROLL por análise estática de quadros (CLIP zero-shot + OCR + rostos). Roda no venv com torch/transformers (venv_align) e tesseract.
Aprendido nos "lista de sistemas": clipes ruins = jogo (gameplay), pessoa/webcam/apresentador, vídeo super editado com texto/legendas/títulos gigantes na tela,
câmera filmando monitor, tela quase preta/estática, foto de caixa/jornal. Este script amostra quadros e dá nota por categoria.
Uso (em animacao/):
  venv_align/bin/python <skill>/scripts/broll/classify_frames.py --clips            # confere os proxies src/videos/clip_NN.mp4 do plano (src/scenes/broll.json)
  venv_align/bin/python <skill>/scripts/broll/classify_frames.py --video ARQ.mp4 [--start 0 --end 1800 --step 6]   # varre um vídeo inteiro e lista TRECHOS LIMPOS
Saída: tabela por clipe (% de quadros em cada categoria) e, com --video, as janelas limpas (>= --min-clean s) para usar como B-roll. Sai 1 se algum clipe reprova.
Categorias (rótulos CLIP em inglês): desktop (OK), jogo, pessoa, text_edited, camera_monitor, preto. Reprova clipe se jogo>15%, pessoa>15%, text_edited>25% ou camera_monitor>40%.
O OCR (tesseract) conta palavras GRANDES (altura > 4,5% do quadro): texto de edição (título/legenda) costuma ser grande; UI de sistema tem texto pequeno.
"""

import argparse, glob, json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
import cv2
import torch
from transformers import CLIPModel, CLIPProcessor

parser = argparse.ArgumentParser()
parser.add_argument("--clips", action="store_true")
parser.add_argument("--video")
parser.add_argument("--start", type=float, default=0)
parser.add_argument("--end", type=float, default=0)
parser.add_argument("--step", type=float, default=6)
parser.add_argument("--min-clean", type=float, default=30)
parser.add_argument("--skip-ocr", action="store_true")
parser.add_argument("--json")
args = parser.parse_args()
LABELS = {
    "desktop": [
        "a screenshot of an operating system desktop with windows and icons",
        "a screenshot of a computer software user interface",
        "a tablet or phone operating system screen",
    ],
    "game": ["a video game with a character, health bar and combo counter", "a 3D video game scene"],
    "person": ["a close-up of a person's face", "a person talking to the camera", "a webcam video of people"],
    "text_edited": [
        "a youtube video with a big title text overlay",
        "a slide with large captions and subtitles text",
        "a thumbnail with text",
    ],
    "camera_monitor": [
        "a photo of a CRT monitor on a desk filmed with a camera",
        "a hand holding a device in a room",
    ],
    "black": ["a black screen", "a blank white screen"],
}
names = list(LABELS)
prompts = [phrase for name in names for phrase in LABELS[name]]
owner = [name for name in names for _ in LABELS[name]]
device = "cpu"
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").eval()
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
with torch.no_grad():
    T = model.get_text_features(**processor(text=prompts, return_tensors="pt", padding=True))
    T = T / T.norm(dim=-1, keepdim=True)


def classify(images):
    """Pontua cada imagem por categoria com CLIP zero-shot (desktop, jogo, pessoa, texto editado, câmera filmando monitor, preto)."""
    with torch.no_grad():
        image_features = model.get_image_features(**processor(images=images, return_tensors="pt"))
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        probs = (100 * image_features @ T.T).softmax(-1).numpy()
    results = []
    for row in probs:
        scores = {name: 0.0 for name in names}
        for value, label in zip(row, owner):
            scores[label] += float(value)
        results.append(scores)
    return results


_HAAR = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def has_face(path):
    """True se o detector Haar encontra um rosto frontal (>= 7% da altura) no quadro."""
    gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
    min_size = max(24, int(gray.shape[0] * 0.07))
    return len(_HAAR.detectMultiScale(gray, 1.1, 6, minSize=(min_size, min_size))) > 0


def count_large_text(path):
    """Conta palavras GRANDES no quadro (OCR): texto de edição costuma ser grande, texto de interface é pequeno."""
    if args.skip_ocr:
        return 0
    result = subprocess.run(
        ["tesseract", path, "-", "-l", "eng+por", "--psm", "11", "tsv"], capture_output=True, text=True
    )
    height = Image.open(path).size[1]
    count = 0
    for line in result.stdout.splitlines()[1:]:
        cols = line.split("\t")
        if (
            len(cols) >= 12
            and cols[11].strip()
            and float(cols[10]) > 70
            and int(cols[9]) > 0.045 * height
            and len(cols[11].strip()) >= 2
        ):
            count += 1
    return count


def sample(file, start, end, step):
    """Extrai quadros de `file` entre `start` e `end` a cada `step` s (arquivos JPEG numa pasta temporária)."""
    tmp_dir = tempfile.mkdtemp()
    samples = []
    current = start
    while current < end:
        frame_path = f"{tmp_dir}/q_{int(current*100):08d}.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                f"{current:.2f}",
                "-i",
                file,
                "-frames:v",
                "1",
                "-vf",
                "scale=448:-2",
                frame_path,
            ],
            capture_output=True,
        )
        if os.path.exists(frame_path):
            samples.append((current, frame_path))
        current += step
    return samples


def analyze(file, start, end, step):
    """Classifica os quadros amostrados (CLIP + OCR + rostos) e devolve uma linha por quadro."""
    samples = sample(file, start, end, step)
    frames = []
    for i in range(0, len(samples), 16):
        batch = samples[i : i + 16]
        scores = classify([Image.open(frame_path).convert("RGB") for _, frame_path in batch])
        for (timestamp, frame_path), frame_scores in zip(batch, scores):
            skip_ocr = count_large_text(frame_path)
            if has_face(
                frame_path
            ):  # rosto/webcam/apresentador em qualquer parte do quadro (CLIP não vê rostos pequenos)
                frame_scores["person"] = max(frame_scores["person"], 0.9)
            top_cat = max(frame_scores, key=frame_scores.get)
            if frame_scores["person"] >= 0.9:
                top_cat = "person"
            if skip_ocr >= 3 and top_cat in ("desktop", "text_edited"):
                top_cat = "text_edited"
            frames.append(dict(t=timestamp, cat=top_cat, ocr=skip_ocr, **{k: round(v, 2) for k, v in frame_scores.items()}))
    return frames


def summarize(frames):
    """Fração de quadros em cada categoria."""
    total = max(1, len(frames))
    fractions = {category: sum(1 for frame in frames if frame["cat"] == category) / total for category in names}
    return fractions


def cuts_per_minute(file, start, end):
    """Taxa de cortes de cena (ffmpeg scene>0.35). Vídeo SUPER EDITADO (muitos cortes, zooms, memes) não serve como B-roll de tela."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "info",
            "-ss",
            str(start),
            "-t",
            str(max(1.0, end - start)),
            "-i",
            file,
            "-vf",
            "select='gt(scene,0.35)',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    count = result.stderr.count("pts_time")
    return count * 60.0 / max(1.0, end - start)


def should_reject(fractions, cpm=0.0):
    """Regra de reprovação: jogo/pessoa > 15%, texto editado > 25%, câmera filmando monitor > 40%, preto > 30% ou > 14 cortes/min."""
    return (
        fractions["game"] > 0.15
        or fractions["person"] > 0.15
        or fractions["text_edited"] > 0.25
        or fractions["camera_monitor"] > 0.40
        or fractions["black"] > 0.3
        or cpm > 14  # mais de ~14 cortes/min = vídeo super editado
    )


rejected_count = 0
report = []
if args.clips:
    broll = json.load(open("src/scenes/broll.json"))
    for k, entry in enumerate(broll, 1):
        proxy_path = f"src/videos/clip_{k:02d}.mp4"
        if not os.path.exists(proxy_path):
            continue
        frames = analyze(proxy_path, 0, max(2, entry["t_end"] - entry["t_start"]), 2.0)
        fractions = summarize(frames)
        cpm = cuts_per_minute(proxy_path, 0, max(2, entry["t_end"] - entry["t_start"]) / 1.0)
        rejected = should_reject(fractions, cpm)
        rejected_count += rejected
        status_label = "FAILS" if rejected else "ok     "
        name = os.path.basename(entry["file"])[:34]
        print(
            f"{status_label} clip {k:02d} {name:34s} fonte {entry['in']:.0f}-{entry['out']:.0f}s  "
            + " ".join(f"{c}={fractions[c]*100:.0f}%" for c in names if fractions[c] > 0)
            + f" cortes/min={cpm:.0f}"
        )
        report.append(dict(clip=k, file=entry["file"], **fractions))
if args.video:
    duration = float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.video],
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    frames = analyze(args.video, args.start, args.end or duration, args.step)
    clean_runs = []
    start = None
    last = None
    for frame in frames:
        is_clean = frame["cat"] == "desktop" and frame["ocr"] < 3
        if is_clean and start is None:
            start = frame["t"]
        if not is_clean and start is not None:
            if frame["t"] - start >= args.min_clean:
                clean_runs.append((start, frame["t"]))
            start = None
        last = frame["t"]
    if start is not None and last - start >= args.min_clean:
        clean_runs.append((start, last))
    print(
        f"TRECHOS LIMPOS em {os.path.basename(args.video)} (desktop, sem jogo/pessoa/texto editado; >= {args.min_clean:.0f}s):"
    )
    for x, y in clean_runs:
        print(f"   {x:7.0f}-{y:7.0f}s  ({y - x:.0f}s)  cortes/min={cuts_per_minute(args.video, x, y):.0f}")
    report = dict(clean=clean_runs, frames=frames)
if args.json:
    json.dump(report, open(args.json, "w"), ensure_ascii=False, indent=1)
sys.exit(1 if rejected_count else 0)
