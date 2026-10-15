"""Recorta fotos em quadrado 600x600 centrado no rosto (OpenCV Haar). Uso: python recorte_rosto.py pasta_entrada pasta_saida [prefixo]"""

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
    caras = casc.detectMultiScale(g, 1.1, 5, minSize=(max(40, w // 12),) * 2)
    if len(caras):
        x, y, cw, ch = max(caras, key=lambda c: c[2] * c[3])
        cx, cy = x + cw / 2, y + ch / 2 + ch * 0.08
        lado = min(min(w, h), cw * 2.6)
    else:
        cx, cy, lado = w / 2, h * 0.38, min(w, h)
    x0 = min(max(0, cx - lado / 2), w - lado)
    y0 = min(max(0, cy - lado / 2), h - lado)
    out = im.crop((int(x0), int(y0), int(x0 + lado), int(y0 + lado))).resize((600, 600), Image.LANCZOS)
    nome = pref + os.path.splitext(f)[0] + ".jpg"
    out.save(os.path.join(sai, nome), quality=92)
    print(f, "rosto" if len(caras) else "centro", "->", nome)
