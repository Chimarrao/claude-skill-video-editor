"""Transcrição local de alta precisão (faster-whisper large-v3, int8, CPU) com timestamps por palavra.
Uso: MODEL=large-v3 PROMPT="termos..." python transcribe.py src/audio/x.wav
Saída: transcription.json (segmentos+palavras) e transcription.txt. Depois rode align.py (alinhamento forçado) se disponível.
"""

import json, sys, os, subprocess
import numpy as np
from faster_whisper import WhisperModel

audio = sys.argv[1] if len(sys.argv) > 1 else "src/audio/pronto.wav"
MODEL_USED = os.environ.get("MODEL", "large-v3")


def _db():
    """Localiza scripts/assets_db.py da skill (sobe as pastas até achar .claude/skills/animacao-narracao)."""
    d = os.path.abspath(".")
    while d != "/":
        c = os.path.join(d, ".claude", "skills", "animacao-narracao", "scripts", "assets_db.py")
        if os.path.exists(c):
            return c
        d = os.path.dirname(d)
    return None


# Reaproveita do banco (por SHA-1 do áudio) se já foi transcrita (FORCE=1 ignora)
if _db() and not os.environ.get("FORCE"):
    r = subprocess.run(
        [sys.executable, _db(), "transcript-find", audio, "--output", "transcription.json"],
        capture_output=True,
        text=True,
    )
    print(r.stdout.strip())
    if r.returncode == 0:
        import json as _j

        d = _j.load(open("transcription.json"))
        open("transcription_raw.json", "w").write(open("transcription.json").read())
        m = lambda t: f"{int(t//60):02d}:{t%60:05.2f}"
        open("transcription.txt", "w").write(
            "\n".join(f"[{m(s['start'])}] {s['text']}" for s in d["segments"]) + "\n"
        )
        print("ok", d["duration"], len(d["segments"]), "(do banco)")
        sys.exit(0)

raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", audio, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
    capture_output=True,
    check=True,
).stdout
wave = np.frombuffer(raw, dtype=np.float32)
prompt = os.environ.get("PROMPT") or (
    open("vocabulary.txt").read().strip() if os.path.exists("vocabulary.txt") else None
)
model = WhisperModel(
    os.environ.get("MODEL", "large-v3"), device="cpu", compute_type="int8", cpu_threads=os.cpu_count()
)
segs, info = model.transcribe(
    wave,
    language="pt",
    word_timestamps=True,
    beam_size=5,
    best_of=5,
    condition_on_previous_text=False,
    initial_prompt=prompt,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=120),
    temperature=0.0,
)
out = {"duration": info.duration, "segments": []}
lines = []
m = lambda t: f"{int(t//60):02d}:{t%60:05.2f}"
for s in segs:
    out["segments"].append(
        {
            "start": s.start,
            "end": s.end,
            "text": s.text.strip(),
            "words": [
                {"start": w.start, "end": w.end, "word": w.word, "prob": w.probability} for w in s.words
            ],
        }
    )
    lines.append(f"[{m(s.start)} - {m(s.end)}] {s.text.strip()}")
    print(lines[-1], flush=True)
json.dump(out, open("transcription_raw.json", "w"), ensure_ascii=False, indent=1)
json.dump(out, open("transcription.json", "w"), ensure_ascii=False, indent=1)
open("transcription.txt", "w").write("\n".join(lines) + "\n")
print("ok", info.duration, len(lines))
if _db():
    subprocess.run(
        [sys.executable, _db(), "transcript-save", "transcription_raw.json", audio, "--model", MODEL_USED]
    )
