"""Monta folhas de contato (12 cenas por imagem) a partir de /tmp/pp/s_<id>.png e /tmp/pp/shots.json."""

import json
from PIL import Image, ImageDraw

shots = json.load(open("/tmp/pp/shots.json"))
W, H = 560, 317
for batch_idx in range(0, len(shots), 12):
    sheet = Image.new("RGB", (W * 3, H * 4), (60, 60, 60))
    draw = ImageDraw.Draw(sheet)
    for item_idx, (scene_id, file) in enumerate(shots[batch_idx : batch_idx + 12]):
        try:
            image = Image.open(f"/tmp/pp/s_{scene_id}.png").convert("RGB").resize((W, H))
        except Exception:
            continue
        sheet.paste(image, ((item_idx % 3) * W, (item_idx // 3) * H))
        draw.text(((item_idx % 3) * W + 8, (item_idx // 3) * H + 22), scene_id, fill=(255, 0, 0))
    sheet.save(f"/tmp/pp/sheet{batch_idx//12}.png")
