"""Biblioteca comum do tipo NEWS (só cortes): ffmpeg/ffprobe, áudio em numpy, correlação cruzada (GCC-PHAT), descoberta de arquivos do episódio,
medição de loudness e caminhos de trabalho. Só numpy (sem scipy)."""

import glob, json, os, re, subprocess, sys
import numpy as np

SR_XC = 16000  # taxa usada nas correlações e nas energias


def run(cmd, **kw):
    """subprocess.run com captura de texto; levanta erro com a saída do ffmpeg se falhar."""
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd[:4]))}… falhou:\n{r.stderr[-1500:]}")
    return r


def probe(path):
    """ffprobe em JSON (streams + format)."""
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(r.stdout)


def duration(path):
    """Duração em segundos do arquivo."""
    return float(probe(path)["format"]["duration"])


def video_info(path):
    """(largura, altura, fps) do primeiro stream de vídeo."""
    for s in probe(path)["streams"]:
        if s["codec_type"] == "video":
            n, d = s["r_frame_rate"].split("/")
            return s["width"], s["height"], float(n) / float(d)
    raise RuntimeError("sem vídeo")


def load_mono(path, start=0.0, dur=None, sr=SR_XC, stream="a:0"):
    """Áudio mono float32 em `sr` Hz (trecho opcional), via ffmpeg."""
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}"]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", path, "-map", stream, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def gcc_phat(a, b, sr=SR_XC, max_ms=500.0):
    """Atraso (ms) de `b` em relação a `a` por GCC-PHAT (robusto a EQ/redução de ruído) + pico normalizado (0..1).
    Positivo = o conteúdo de `b` aparece DEPOIS do mesmo conteúdo em `a`."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    A, B = np.fft.rfft(a, n), np.fft.rfft(b, n)
    R = B * np.conj(A)
    R /= np.maximum(np.abs(R), 1e-12)
    cc = np.fft.irfft(R, n)
    m = int(sr * max_ms / 1000)
    cc = np.concatenate((cc[-m:], cc[: m + 1]))
    k = int(np.argmax(np.abs(cc)))
    pico = float(np.abs(cc[k]) / (np.median(np.abs(cc)) * 20 + 1e-12))
    # refinamento parabólico
    if 0 < k < len(cc) - 1:
        y0, y1, y2 = abs(cc[k - 1]), abs(cc[k]), abs(cc[k + 1])
        den = y0 - 2 * y1 + y2
        frac = 0.5 * (y0 - y2) / den if den else 0.0
    else:
        frac = 0.0
    return float((k - m + frac) * 1000.0 / sr), float(min(1.0, pico / 10))


def pontos_sync(dur_total, janela=20.0):
    """3 pontos (início, meio, fim) para medir sincronia, evitando as pontas exatas."""
    j = min(janela, dur_total / 4)
    return [dur_total * 0.03, dur_total * 0.5 - j / 2, max(0.0, dur_total * 0.97 - j)]


def medir_atraso(path_a, path_b, dur_total, janela=20.0, stream_a="a:0", stream_b="a:0"):
    """Atraso (ms) de B em relação a A em 3 pontos: lista de (t, atraso_ms, confiança)."""
    out = []
    for t in pontos_sync(dur_total, janela):
        a = load_mono(path_a, t, janela, stream=stream_a)
        b = load_mono(path_b, t, janela, stream=stream_b)
        n = min(len(a), len(b))
        d, c = gcc_phat(a[:n], b[:n])
        out.append((round(t, 1), round(d, 2), round(c, 2)))
    return out


def loudness(path, stream="a:0"):
    """Loudness integrado (LUFS), pico verdadeiro (dBTP) e LRA via ebur128."""
    r = subprocess.run(
        ["ffmpeg", "-nostats", "-i", path, "-map", stream, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True
    )
    t = r.stderr[r.stderr.rfind("Summary:") :]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", t).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", t).group(1))
    lra = float(re.search(r"LRA:\s+([\d.]+) LU", t).group(1))
    return dict(I=i, TP=tp, LRA=lra)


def achar_candidatos(pasta):
    """Vídeo bruto (.mov que não termina em -limpo/-limpo-auto) e áudio tratado (.wav/.WAV) da pasta do episódio. PRONTO.mp4, thumbs e *-limpo.mov antigos são ignorados."""
    vids = [f for f in glob.glob(os.path.join(pasta, "*")) if f.lower().endswith(".mov") and not re.search(r"-limpo(-auto)?\.mov$", f, re.I)]
    wavs = [f for f in glob.glob(os.path.join(pasta, "*")) if f.lower().endswith(".wav")]
    return sorted(vids), sorted(wavs)


def work_dir(pasta):
    """Pasta de trabalho do episódio (`work/`): relatórios, transcrição, cortes."""
    w = os.path.join(pasta, "work")
    os.makedirs(w, exist_ok=True)
    return w


def mmss(t):
    """Segundos -> m:ss.cc"""
    return f"{int(t // 60)}:{t % 60:05.2f}"
