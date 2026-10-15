#!/usr/bin/env python3
"""TESTE: clipes de B-roll COM PESSOAS/ROSTOS (webcam, apresentador, plateia) — o usuário pediu para cortar e pular para um trecho sem gente.
Rode em animacao/ depois de generate_proxies.py. Amostra 1 quadro/s de cada proxy src/videos/clip_NN.mp4 (já aparado no trecho do plano) e conta rostos
(OpenCV Haar frontal). Lista, por clipe, os segundos (do clipe) com rosto; sugere trocar de trecho. Requer opencv-python-headless (<4.11) no venv.
Uso: python test_clips_without_people.py [--limit 2]   (clipes com mais de N quadros com rosto são reprovados; sai 1)
"""

import json, os, subprocess, sys, tempfile, glob
import cv2

limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else (
    int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 2
)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
broll = json.load(open("src/scenes/broll.json"))
failed_clips = []
for clip_idx, clip in enumerate(broll, 1):
    proxy = f"src/videos/clip_{clip_idx:02d}.mp4"
    if not os.path.exists(proxy):
        continue
    tmp = tempfile.mkdtemp()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", proxy, "-vf", "fps=1", f"{tmp}/f_%03d.jpg"], capture_output=True
    )
    frames_with_faces = []
    for frame_file in sorted(glob.glob(f"{tmp}/f_*.jpg")):
        gray = cv2.cvtColor(cv2.imread(frame_file), cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 6, minSize=(28, 28))
        if len(faces):
            frames_with_faces.append(int(os.path.basename(frame_file)[2:5]) - 1)
    start_time = clip["t_inicio"]
    name = os.path.basename(clip["arquivo"])[:38]
    if len(frames_with_faces) > limit:
        failed_clips.append(clip_idx)
        print(
            f"PESSOAS clip {clip_idx:02d} ({name} fonte {clip['in']:.0f}-{clip['out']:.0f}s, na timeline {start_time:.0f}s): rosto em {len(frames_with_faces)} de ~{int((clip['t_fim'] - start_time))} quadros (s do clipe: {frames_with_faces[:8]}) -> troque o trecho"
        )
    else:
        print(f"ok    clip {clip_idx:02d} ({name}) rostos em {len(frames_with_faces)} quadros")
sys.exit(1 if failed_clips else 0)
