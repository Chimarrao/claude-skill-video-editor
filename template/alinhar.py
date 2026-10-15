"""Alinhamento forçado (CTC, wav2vec2 PT) dos tokens do Whisper -> tempos por palavra com precisão de ~20-40 ms.
Uso: venv_align/bin/python alinhar.py src/audio/x.wav   (lê transcricao_raw.json, grava transcricao.json)
Palavras sem letras alinháveis (números) herdam o tempo do Whisper, limitado pelos vizinhos alinhados."""

import json, os, sys, unicodedata, subprocess
import numpy as np, torch
from torchaudio.functional import forced_align
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

audio = sys.argv[1]
for _c in [
    os.path.join(
        os.path.abspath(os.path.join(".", *[".."] * i)),
        ".claude",
        "skills",
        "animacao-narracao",
        "scripts",
        "assets_db.py",
    )
    for i in range(0, 6)
]:
    if os.path.exists(_c) and not os.environ.get("FORCAR"):
        if (
            subprocess.run(
                [sys.executable, _c, "trans-buscar", audio, "--so-alinhada", "--saida", "transcricao.json"]
            ).returncode
            == 0
        ):
            print("palavras alinhadas: (transcrição alinhada reaproveitada do banco)")
            sys.exit(0)
        break
MOD = "jonatasgrosman/wav2vec2-large-xlsr-53-portuguese"
proc = Wav2Vec2Processor.from_pretrained(MOD)
model = Wav2Vec2ForCTC.from_pretrained(MOD).eval()
vocab = proc.tokenizer.get_vocab()
BLANK = vocab["<pad>"]
SEP = vocab["|"]
wav = np.frombuffer(
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", audio, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True,
        check=True,
    ).stdout,
    dtype=np.float32,
)
SR = 16000
STRIDE = 0.02
T = json.load(open("transcricao_raw.json"))


def chars(w):
    w = unicodedata.normalize("NFC", w.lower().strip())
    return [c for c in w if c in vocab and c not in "|"]


def emissions(a, b):
    x = wav[int(a * SR) : int(b * SR)]
    x = (x - x.mean()) / (x.std() + 1e-7)
    with torch.inference_mode():
        lg = model(torch.from_numpy(x)[None]).logits
    return torch.log_softmax(lg, -1)[0]


tot = ok = 0
for seg in T["segments"]:
    words = seg["words"]
    if not words:
        continue
    a = max(0, seg["start"] - 0.5)
    b = min(len(wav) / SR, seg["end"] + 0.5)
    em = emissions(a, b)
    seq, owner = [], []
    for i, w in enumerate(words):
        cs = chars(w["word"])
        if not cs:
            continue
        for c in cs:
            seq.append(vocab[c])
            owner.append(i)
        seq.append(SEP)
        owner.append(-1)
    if len(seq) < 2 or len(seq) > em.shape[0]:
        continue
    try:
        ali, _ = forced_align(em[None], torch.tensor([seq], dtype=torch.int32), blank=BLANK)
    except Exception as e:
        print("falhou", seg["text"][:40], e)
        continue
    ali = ali[0].tolist()
    # percorre frames: cada token da sequência ocupa uma corrida de frames iguais (ignorando blank)
    pos, first, last = -1, {}, {}
    prev = BLANK
    for f, tok in enumerate(ali):
        if tok != BLANK and (tok != prev or prev == BLANK):
            pos += 1
        if tok != BLANK:
            o = owner[pos] if pos < len(owner) else -1
            if o >= 0:
                first.setdefault(o, f)
                last[o] = f
        prev = tok
    for i, w in enumerate(words):
        tot += 1
        if i in first:
            w["start_whisper"], w["end_whisper"] = w["start"], w["end"]
            w["start"] = round(a + first[i] * STRIDE, 3)
            w["end"] = round(a + (last[i] + 1) * STRIDE, 3)
            w["aligned"] = True
            ok += 1
    # palavras não alinhadas: limita ao intervalo entre vizinhos alinhados
    for i, w in enumerate(words):
        if w.get("aligned"):
            continue
        lo = max((words[j]["end"] for j in range(i) if words[j].get("aligned")), default=seg["start"])
        hi = min(
            (words[j]["start"] for j in range(i + 1, len(words)) if words[j].get("aligned")),
            default=seg["end"],
        )
        w["start"] = round(min(max(w["start"], lo), hi), 3)
        w["end"] = round(min(max(w["end"], w["start"]), hi), 3)
    seg["start"] = words[0]["start"]
    seg["end"] = words[-1]["end"]
print(f"palavras alinhadas: {ok}/{tot}")
json.dump(T, open("transcricao.json", "w"), ensure_ascii=False, indent=1)
for _c in [
    os.path.join(d, ".claude", "skills", "animacao-narracao", "scripts", "assets_db.py")
    for d in [os.path.abspath(".")] + [os.path.abspath(os.path.join(".", *[".."] * i)) for i in range(1, 6)]
]:
    if os.path.exists(_c):
        subprocess.run(
            [
                sys.executable,
                _c,
                "trans-salvar",
                "transcricao.json",
                audio,
                "--modelo",
                os.environ.get("MODELO", "large-v3"),
                "--alinhado",
            ]
        )
        break
