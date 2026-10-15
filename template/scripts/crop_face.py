"""Recorta fotos em quadrado 600x600 centrado no rosto (OpenCV Haar). Uso: python crop_face.py pasta_entrada pasta_saida [prefixo]"""

import sys, os, cv2
from PIL import Image

ent, sai = sys.argv[1], sys.argv[2]
pref = sys.argv[3] if len(sys.argv) > 3 else "foto_"
os.makedirs(sai, exist_ok=True)
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
for f in sorted(os.listdir(ent)):
    if not f.lower().endswith((".jpg", ".jpeg", ".png")):
        continue
    p = os.path.join(ent, f)
    im = Image.open(p).convert("RGB")
    w, h = im.size
    g = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2GRAY)
    faces = casc.detectMultiScale(g, 1.1, 5, minSize=(max(40, w // 12),) * 2)
    if len(faces):
        x, y, cw, ch = max(faces, key=lambda c: c[2] * c[3])
        cx, cy = x + cw / 2, y + ch / 2 + ch * 0.08
        side = min(min(w, h), cw * 2.6)
    else:
        cx, cy, side = w / 2, h * 0.38, min(w, h)
    x0 = min(max(0, cx - side / 2), w - side)
    y0 = min(max(0, cy - side / 2), h - side)
    out = im.crop((int(x0), int(y0), int(x0 + side), int(y0 + side))).resize((600, 600), Image.LANCZOS)
    name = pref + os.path.splitext(f)[0] + ".jpg"
    out.save(os.path.join(sai, name), quality=92)
    print(f, "face" if len(faces) else "center", "->", name)
