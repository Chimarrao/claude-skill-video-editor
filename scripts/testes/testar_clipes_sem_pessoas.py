#!/usr/bin/env python3
"""TESTE: clipes de B-roll COM PESSOAS/ROSTOS (webcam, apresentador, plateia) — o usuário pediu para cortar e pular para um trecho sem gente.
Rode em animacao/ depois de gerar_proxies.py. Amostra 1 quadro/s de cada proxy src/videos/clip_NN.mp4 (já aparado no trecho do plano) e conta rostos
(OpenCV Haar frontal). Lista, por clipe, os segundos (do clipe) com rosto; sugere trocar de trecho. Requer opencv-python-headless (<4.11) no venv.
Uso: python testar_clipes_sem_pessoas.py [--limite 2]   (clipes com mais de N quadros com rosto são reprovados; sai 1)
"""

import json, os, subprocess, sys, tempfile, glob
import cv2

lim = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 2
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
broll = json.load(open("src/scenes/broll.json"))
ruins = []
for k, b in enumerate(broll, 1):
    pv = f"src/videos/clip_{k:02d}.mp4"
    if not os.path.exists(pv):
        continue
    tmp = tempfile.mkdtemp()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", pv, "-vf", "fps=1", f"{tmp}/f_%03d.jpg"], capture_output=True
    )
    com = []
    for f in sorted(glob.glob(f"{tmp}/f_*.jpg")):
        g = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2GRAY)
        cs = casc.detectMultiScale(g, 1.1, 6, minSize=(28, 28))
        if len(cs):
            com.append(int(os.path.basename(f)[2:5]) - 1)
    t0 = b["t_inicio"]
    nome = os.path.basename(b["arquivo"])[:38]
    if len(com) > lim:
        ruins.append(k)
        print(
            f"PESSOAS clip {k:02d} ({nome} fonte {b['in']:.0f}-{b['out']:.0f}s, na timeline {t0:.0f}s): rosto em {len(com)} de ~{int((b['t_fim'] - t0))} quadros (s do clipe: {com[:8]}) -> troque o trecho"
        )
    else:
        print(f"ok    clip {k:02d} ({nome}) rostos em {len(com)} quadros")
sys.exit(1 if ruins else 0)
