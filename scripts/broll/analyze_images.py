#!/usr/bin/env python3
"""Análise das IMAGENS da pasta Assets/ (Webdoc com B-roll): dimensão, proporção, transparência, tamanho, uso sugerido e folha de contato.
Uso (em animacao/): python analyze_images.py [folder] [--output imagens_analise.json] [--contact-sheet folha_imagens.png]
Uso sugerido (heurística; CONFIRA a folha de contato — o conteúdo só você enxerga):
  tela        largura >= 700 px e sem transparência → entra como Tela('asset:arquivo', 'legenda curta') (print/foto com legenda, parada, sem zoom)
  tela_baixa  400–699 px → serve em Tela com largura reduzida (o plano.py nunca estica além da resolução)
  logo        transparente (ou quadrada pequena) → LogoSolto/Logo/grafo (cartão branco se escuro/opaco)
  descartar   < 400 px, ou proporção > 4:1 (banner), ou arquivo mínimo
Nunca esticar imagem além da resolução nem aplicar zoom lento de enchimento."""

import argparse, json, os, sys, warnings

warnings.filterwarnings("ignore")
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("folder", nargs="?", default="../Assets")
parser.add_argument("--output", "--saida", default="imagens_analise.json")
parser.add_argument("--contact-sheet", "--folha", default="folha_imagens.png")
args = parser.parse_args()
EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif")
files = sorted(f for f in os.listdir(args.folder) if f.lower().endswith(EXT) and not f.startswith("."))
results = []
for f in files:
    path = os.path.join(args.folder, f)
    try:
        image = Image.open(path)
        w, h = image.size
        mode = image.mode
        alpha = False
        if mode in ("RGBA", "LA") or "transparency" in image.info:
            # confere o canal alfa real (paleta pode enganar)
            extreme_alpha = image.convert("RGBA").getchannel("A").getextrema()
            alpha = extreme_alpha[0] < 250
        rgb = image.convert("RGB").resize((32, 32))
        px = list(rgb.getdata())
        brightness = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in px) / len(px)
        aspect = w / h
        if min(w, h) < 400 or aspect > 4 or aspect < 0.25:
            usage = "descartar"
        elif alpha:
            usage = "logo"
        elif w >= 700:
            usage = "tela"
        else:
            usage = "tela_baixa"
        if alpha and min(w, h) >= 400 and w >= 700 and aspect > 1.2:
            usage = "logo"  # banner transparente largo: provável logo/wordmark
        results.append(
            dict(
                arquivo=f,
                largura=w,
                altura=h,
                proporcao=round(aspect, 2),
                transparente=alpha,
                luminosidade=round(brightness),
                kb=os.path.getsize(path) // 1024,
                uso=usage,
            )
        )
    except Exception as e:
        results.append(dict(arquivo=f, erro=str(e), uso="descartar"))
json.dump(results, open(args.output, "w"), ensure_ascii=False, indent=1)
# folha de contato para conferir o conteúdo de olho (só a imagem mostra o real)
W, H, cols = 360, 270, 5
rows = max(1, (len(files) + cols - 1) // cols)
sheet = Image.new("RGB", (W * cols, H * rows), (30, 30, 30))
draw = ImageDraw.Draw(sheet)
for k, r in enumerate(results):
    x, y = (k % cols) * W, (k // cols) * H
    try:
        image = Image.open(os.path.join(args.folder, r["arquivo"])).convert("RGBA")
        image.thumbnail((W - 8, H - 34))
        # fundo cinza para ver transparência na miniatura
        background = Image.new("RGBA", image.size, (70, 70, 70, 255))
        background.alpha_composite(image)
        sheet.paste(background.convert("RGB"), (x + 4, y + 4))
    except Exception:
        pass
    draw.rectangle((x, y + H - 28, x + W, y + H), fill=(0, 0, 0))
    draw.text(
        (x + 4, y + H - 24),
        f"{r['arquivo'][:30]} {r.get('largura','?')}x{r.get('altura','?')} {r['uso']}",
        fill=(255, 255, 0),
    )
sheet.save(args.contact_sheet)
print(f"{len(results)} imagens -> {args.output}, {args.contact_sheet}")
for r in results:
    print(
        f"  {r['uso']:10s} {r.get('largura','?')}x{r.get('altura','?')} {'alfa ' if r.get('transparente') else ''}{r['arquivo']}"
    )
