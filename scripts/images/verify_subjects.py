#!/usr/bin/env python3
"""Verifica se cada imagem colhida realmente é do assunto que o catálogo diz (a colheita por título da Wikipédia às vezes traz imagens de
OUTRO assunto: ex.: o artigo "System 1" devolveu a logo de uma TV coreana e de uma ferrovia).
Método: CLIP zero-shot — compara a imagem com os textos de TODOS os assuntos do mesmo tipo ("a screenshot of Windows XP", "the logo of BeOS"…)
e vê em que posição fica o assunto verdadeiro. Rank <= top => ok · até --review => `check:rank R` (use, mas confira) · acima => `low:fora do assunto`. O rank fica gravado no catálogo.
Precisa do venv com torch/transformers (venv_align do projeto). Uso: venv_align/bin/python verify_subjects.py [--top 40] [--only slug,slug]
"""

import argparse, json, os, sys

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(ROOT, "library")
CAT = os.path.join(ROOT, "database", "image_catalog.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subjects import SUBJECTS  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--top", type=int, default=40, help="rank até o qual a imagem é considerada do assunto (ok)")
ap.add_argument("--review", type=int, default=150, help="rank até o qual fica `check` (revisar); acima disso `low`")
ap.add_argument("--only", default="")
ap.add_argument("--batch", type=int, default=24)
args = ap.parse_args()
cat = json.load(open(CAT, encoding="utf8"))
titulo = {s["slug"]: s["wiki"][0].split("#")[0] for s in SUBJECTS}
FRASE = dict(logo="the logo of {}", tela="a screenshot of {}", foto="a photo related to {}", obj="a photo of {}")
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").eval()
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
slugs = sorted(titulo)
with torch.no_grad():
    txt = {}
    for kind, fr in FRASE.items():
        t = proc(text=[fr.format(titulo[s]) for s in slugs], return_tensors="pt", padding=True)
        e = model.get_text_features(**t)
        txt[kind] = (e / e.norm(dim=-1, keepdim=True)).numpy()
only = set(filter(None, args.only.split(",")))
nomes = [n for n, v in cat["images"].items() if (not only or v["subject"] in only) and os.path.exists(os.path.join(LIB, v["file"]))]
print(f"{len(nomes)} imagens para verificar…", flush=True)
ruins = 0
for i in range(0, len(nomes), args.batch):
    lote = nomes[i : i + args.batch]
    ims = []
    for n in lote:
        try:
            im = Image.open(os.path.join(LIB, cat["images"][n]["file"])).convert("RGBA")
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            ims.append(bg.convert("RGB"))
        except Exception:
            ims.append(Image.new("RGB", (64, 64), (255, 255, 255)))
    with torch.no_grad():
        e = model.get_image_features(**proc(images=ims, return_tensors="pt"))
    e = (e / e.norm(dim=-1, keepdim=True)).numpy()
    for n, ev in zip(lote, e):
        v = cat["images"][n]
        sims = txt[v["kind"]] @ ev
        ordem = np.argsort(-sims)
        rank = int(np.where(ordem == slugs.index(v["subject"]))[0][0]) + 1 if v["subject"] in slugs else 999
        v["rank"] = rank
        q = v.get("quality", "ok")
        if q.startswith(("check", "low:fora do assunto")) or q == "ok":
            if rank <= args.top:
                v["quality"] = "ok"
            elif rank <= args.review:
                v["quality"] = f"check:rank {rank}"  # utilizável, mas confira na folha de contato
            else:
                v["quality"] = f"low:fora do assunto (rank {rank})"
                ruins += 1
    if (i // args.batch) % 10 == 0:
        print(f"  {i + len(lote)}/{len(nomes)}", flush=True)
json.dump(cat, open(CAT, "w", encoding="utf8"), ensure_ascii=False, indent=1, sort_keys=True)
print(f"{ruins} imagens marcadas como fora do assunto (top {args.top} de {len(slugs)})")
