#!/usr/bin/env python3
"""FILTRO VISUAL DE B-ROLL por análise estática de quadros (CLIP zero-shot + OCR + rostos). Roda no venv com torch/transformers (venv_align) e tesseract.
Aprendido nos "lista de sistemas": clipes ruins = jogo (gameplay), pessoa/webcam/apresentador, vídeo super editado com texto/legendas/títulos gigantes na tela,
câmera filmando monitor, tela quase preta/estática, foto de caixa/jornal. Este script amostra quadros e dá nota por categoria.
Uso (em animacao/):
  venv_align/bin/python <skill>/scripts/broll/classificar_frames.py --clipes            # confere os proxies src/videos/clip_NN.mp4 do plano (src/scenes/broll.json)
  venv_align/bin/python <skill>/scripts/broll/classificar_frames.py --video ARQ.mp4 [--de 0 --ate 1800 --passo 6]   # varre um vídeo inteiro e lista TRECHOS LIMPOS
Saída: tabela por clipe (% de quadros em cada categoria) e, com --video, as janelas limpas (>= --min-limpo s) para usar como B-roll. Sai 1 se algum clipe reprova.
Categorias (rótulos CLIP em inglês): desktop (OK), jogo, pessoa, texto_editado, camera_monitor, preto. Reprova clipe se jogo>15%, pessoa>15%, texto_editado>25% ou camera_monitor>40%.
O OCR (tesseract) conta palavras GRANDES (altura > 4,5% do quadro): texto de edição (título/legenda) costuma ser grande; UI de sistema tem texto pequeno.
"""

import argparse, glob, json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
import cv2
import torch
from transformers import CLIPModel, CLIPProcessor

ap = argparse.ArgumentParser()
ap.add_argument("--clipes", action="store_true")
ap.add_argument("--video")
ap.add_argument("--de", type=float, default=0)
ap.add_argument("--ate", type=float, default=0)
ap.add_argument("--passo", type=float, default=6)
ap.add_argument("--min-limpo", type=float, default=30)
ap.add_argument("--sem-ocr", action="store_true")
ap.add_argument("--json")
a = ap.parse_args()
ROT = {
    "desktop": [
        "a screenshot of an operating system desktop with windows and icons",
        "a screenshot of a computer software user interface",
        "a tablet or phone operating system screen",
    ],
    "jogo": ["a video game with a character, health bar and combo counter", "a 3D video game scene"],
    "pessoa": ["a close-up of a person's face", "a person talking to the camera", "a webcam video of people"],
    "texto_editado": [
        "a youtube video with a big title text overlay",
        "a slide with large captions and subtitles text",
        "a thumbnail with text",
    ],
    "camera_monitor": [
        "a photo of a CRT monitor on a desk filmed with a camera",
        "a hand holding a device in a room",
    ],
    "preto": ["a black screen", "a blank white screen"],
}
nomes = list(ROT)
frases = [f for n in nomes for f in ROT[n]]
dono = [n for n in nomes for _ in ROT[n]]
dev = "cpu"
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").eval()
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
with torch.no_grad():
    T = model.get_text_features(**proc(text=frases, return_tensors="pt", padding=True))
    T = T / T.norm(dim=-1, keepdim=True)


def classificar(imgs):
    with torch.no_grad():
        I = model.get_image_features(**proc(images=imgs, return_tensors="pt"))
        I = I / I.norm(dim=-1, keepdim=True)
        p = (100 * I @ T.T).softmax(-1).numpy()
    out = []
    for r in p:
        s = {n: 0.0 for n in nomes}
        for v, d in zip(r, dono):
            s[d] += float(v)
        out.append(s)
    return out


_HAAR = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def tem_rosto(path):
    """True se o detector Haar encontra um rosto frontal (>= 7% da altura) no quadro."""
    cinza = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
    minimo = max(24, int(cinza.shape[0] * 0.07))
    return len(_HAAR.detectMultiScale(cinza, 1.1, 6, minSize=(minimo, minimo))) > 0


def ocr_grande(path):
    if a.sem_ocr:
        return 0
    r = subprocess.run(
        ["tesseract", path, "-", "-l", "eng+por", "--psm", "11", "tsv"], capture_output=True, text=True
    )
    h = Image.open(path).size[1]
    n = 0
    for ln in r.stdout.splitlines()[1:]:
        c = ln.split("\t")
        if (
            len(c) >= 12
            and c[11].strip()
            and float(c[10]) > 70
            and int(c[9]) > 0.045 * h
            and len(c[11].strip()) >= 2
        ):
            n += 1
    return n


def amostrar(arq, t0, t1, passo):
    tmp = tempfile.mkdtemp()
    fs = []
    t = t0
    while t < t1:
        f = f"{tmp}/q_{int(t*100):08d}.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                f"{t:.2f}",
                "-i",
                arq,
                "-frames:v",
                "1",
                "-vf",
                "scale=448:-2",
                f,
            ],
            capture_output=True,
        )
        if os.path.exists(f):
            fs.append((t, f))
        t += passo
    return fs


def analisar(arq, t0, t1, passo):
    fs = amostrar(arq, t0, t1, passo)
    res = []
    for i in range(0, len(fs), 16):
        lote = fs[i : i + 16]
        sc = classificar([Image.open(f).convert("RGB") for _, f in lote])
        for (t, f), s in zip(lote, sc):
            nocr = ocr_grande(f)
            if tem_rosto(
                f
            ):  # rosto/webcam/apresentador em qualquer parte do quadro (CLIP não vê rostos pequenos)
                s["pessoa"] = max(s["pessoa"], 0.9)
            topo = max(s, key=s.get)
            if s["pessoa"] >= 0.9:
                topo = "pessoa"
            if nocr >= 3 and topo in ("desktop", "texto_editado"):
                topo = "texto_editado"
            res.append(dict(t=t, cat=topo, ocr=nocr, **{k: round(v, 2) for k, v in s.items()}))
    return res


def resumo(res):
    n = max(1, len(res))
    pc = {c: sum(1 for r in res if r["cat"] == c) / n for c in nomes}
    return pc


def cortes_por_minuto(arq, t0, t1):
    """Taxa de cortes de cena (ffmpeg scene>0.35). Vídeo SUPER EDITADO (muitos cortes, zooms, memes) não serve como B-roll de tela."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "info",
            "-ss",
            str(t0),
            "-t",
            str(max(1.0, t1 - t0)),
            "-i",
            arq,
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
    n = r.stderr.count("pts_time")
    return n * 60.0 / max(1.0, t1 - t0)


def reprova(pc, cpm=0.0):
    return (
        pc["jogo"] > 0.15
        or pc["pessoa"] > 0.15
        or pc["texto_editado"] > 0.25
        or pc["camera_monitor"] > 0.40
        or pc["preto"] > 0.3
        or cpm > 14  # mais de ~14 cortes/min = vídeo super editado
    )


ruins = 0
relatorio = []
if a.clipes:
    broll = json.load(open("src/scenes/broll.json"))
    for k, b in enumerate(broll, 1):
        pv = f"src/videos/clip_{k:02d}.mp4"
        if not os.path.exists(pv):
            continue
        res = analisar(pv, 0, max(2, b["t_fim"] - b["t_inicio"]), 2.0)
        pc = resumo(res)
        cpm = cortes_por_minuto(pv, 0, max(2, b["t_fim"] - b["t_inicio"]) / 1.0)
        r = reprova(pc, cpm)
        ruins += r
        marca = "REPROVA" if r else "ok     "
        nome = os.path.basename(b["arquivo"])[:34]
        print(
            f"{marca} clip {k:02d} {nome:34s} fonte {b['in']:.0f}-{b['out']:.0f}s  "
            + " ".join(f"{c}={pc[c]*100:.0f}%" for c in nomes if pc[c] > 0)
            + f" cortes/min={cpm:.0f}"
        )
        relatorio.append(dict(clip=k, arquivo=b["arquivo"], **pc))
if a.video:
    dur = float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video],
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    res = analisar(a.video, a.de, a.ate or dur, a.passo)
    runs = []
    ini = None
    ult = None
    for r in res:
        bom = r["cat"] == "desktop" and r["ocr"] < 3
        if bom and ini is None:
            ini = r["t"]
        if not bom and ini is not None:
            if r["t"] - ini >= a.min_limpo:
                runs.append((ini, r["t"]))
            ini = None
        ult = r["t"]
    if ini is not None and ult - ini >= a.min_limpo:
        runs.append((ini, ult))
    print(
        f"TRECHOS LIMPOS em {os.path.basename(a.video)} (desktop, sem jogo/pessoa/texto editado; >= {a.min_limpo:.0f}s):"
    )
    for x, y in runs:
        print(f"   {x:7.0f}-{y:7.0f}s  ({y - x:.0f}s)  cortes/min={cortes_por_minuto(a.video, x, y):.0f}")
    relatorio = dict(limpos=runs, quadros=res)
if a.json:
    json.dump(relatorio, open(a.json, "w"), ensure_ascii=False, indent=1)
sys.exit(1 if ruins else 0)
