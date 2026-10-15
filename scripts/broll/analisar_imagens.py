#!/usr/bin/env python3
"""Análise das IMAGENS da pasta Assets/ (Webdoc com B-roll): dimensão, proporção, transparência, tamanho, uso sugerido e folha de contato.
Uso (em animacao/): python analisar_imagens.py [../Assets] [--saida imagens_analise.json] [--folha folha_imagens.png]
Uso sugerido (heurística; CONFIRA a folha de contato — o conteúdo só você enxerga):
  tela        largura >= 700 px e sem transparência → entra como Tela('asset:arquivo', 'legenda curta') (print/foto com legenda, parada, sem zoom)
  tela_baixa  400–699 px → serve em Tela com largura reduzida (o plano.py nunca estica além da resolução)
  logo        transparente (ou quadrada pequena) → LogoSolto/Logo/grafo (cartão branco se escuro/opaco)
  descartar   < 400 px, ou proporção > 4:1 (banner), ou arquivo mínimo
Nunca esticar imagem além da resolução nem aplicar zoom lento de enchimento."""

import argparse, json, os, sys, warnings

warnings.filterwarnings("ignore")
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("pasta", nargs="?", default="../Assets")
ap.add_argument("--saida", default="imagens_analise.json")
ap.add_argument("--folha", default="folha_imagens.png")
a = ap.parse_args()
EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif")
arqs = sorted(f for f in os.listdir(a.pasta) if f.lower().endswith(EXT) and not f.startswith("."))
res = []
for f in arqs:
    p = os.path.join(a.pasta, f)
    try:
        im = Image.open(p)
        w, h = im.size
        modo = im.mode
        alfa = False
        esc = None
        if modo in ("RGBA", "LA") or "transparency" in im.info:
            ex = im.convert("RGBA").getchannel("A").getextrema()
            alfa = ex[0] < 250
        rgb = im.convert("RGB").resize((32, 32))
        px = list(rgb.getdata())
        lum = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in px) / len(px)
        prop = w / h
        if min(w, h) < 400 or prop > 4 or prop < 0.25:
            uso = "descartar"
        elif alfa:
            uso = "logo"
        elif w >= 700:
            uso = "tela"
        else:
            uso = "tela_baixa"
        if alfa and min(w, h) >= 400 and w >= 700 and prop > 1.2:
            uso = "logo"  # banner transparente largo: provável logo/wordmark
        res.append(
            dict(
                arquivo=f,
                largura=w,
                altura=h,
                proporcao=round(prop, 2),
                transparente=alfa,
                luminosidade=round(lum),
                kb=os.path.getsize(p) // 1024,
                uso=uso,
            )
        )
    except Exception as e:
        res.append(dict(arquivo=f, erro=str(e), uso="descartar"))
json.dump(res, open(a.saida, "w"), ensure_ascii=False, indent=1)
# folha de contato
W, H, cols = 360, 270, 5
linhas = max(1, (len(arqs) + cols - 1) // cols)
sh = Image.new("RGB", (W * cols, H * linhas), (30, 30, 30))
d = ImageDraw.Draw(sh)
for k, r in enumerate(res):
    x, y = (k % cols) * W, (k // cols) * H
    try:
        im = Image.open(os.path.join(a.pasta, r["arquivo"])).convert("RGBA")
        im.thumbnail((W - 8, H - 34))
        bg = Image.new("RGBA", im.size, (70, 70, 70, 255))
        bg.alpha_composite(im)
        sh.paste(bg.convert("RGB"), (x + 4, y + 4))
    except Exception:
        pass
    d.rectangle((x, y + H - 28, x + W, y + H), fill=(0, 0, 0))
    d.text(
        (x + 4, y + H - 24),
        f"{r['arquivo'][:30]} {r.get('largura','?')}x{r.get('altura','?')} {r['uso']}",
        fill=(255, 255, 0),
    )
sh.save(a.folha)
print(f"{len(res)} imagens -> {a.saida}, {a.folha}")
for r in res:
    print(
        f"  {r['uso']:10s} {r.get('largura','?')}x{r.get('altura','?')} {'alfa ' if r.get('transparente') else ''}{r['arquivo']}"
    )
