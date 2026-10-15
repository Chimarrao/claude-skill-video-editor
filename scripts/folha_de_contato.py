"""Monta folhas de contato (12 cenas por imagem) a partir de /tmp/pp/s_<id>.png e /tmp/pp/shots.json."""

import json
from PIL import Image, ImageDraw

shots = json.load(open("/tmp/pp/shots.json"))
W, H = 560, 317
for k in range(0, len(shots), 12):
    sheet = Image.new("RGB", (W * 3, H * 4), (60, 60, 60))
    d = ImageDraw.Draw(sheet)
    for j, (id_, f) in enumerate(shots[k : k + 12]):
        try:
            im = Image.open(f"/tmp/pp/s_{id_}.png").convert("RGB").resize((W, H))
        except Exception:
            continue
        sheet.paste(im, ((j % 3) * W, (j // 3) * H))
        d.text(((j % 3) * W + 8, (j // 3) * H + 22), id_, fill=(255, 0, 0))
    sheet.save(f"/tmp/pp/sheet{k//12}.png")
