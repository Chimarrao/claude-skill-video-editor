#!/usr/bin/env bash
# NEWS · PASSO 2 — transcrição large-v3 + alinhamento forçado (fluxo da skill) sobre o arquivo FUNDIDO.
# Uso: transcribe_news.sh "<pasta do episódio>" "<arquivo fundido .mov>" ["vocabulário: nomes, siglas, empresas da notícia"]
# Saída em <pasta>/work/: transcription.json (palavras com tempos alinhados), transcription_raw.json, transcription.txt. Reaproveita do banco por SHA-1.
# Python: PY_WHISPER (venv com faster-whisper) e PY_ALIGN (venv com torch/transformers); se não definidos, procura venv/venv_align em animacao/ de algum projeto.
set -euo pipefail
PASTA="$(cd "$1" && pwd)"; FUNDIDO="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; VOCAB="${3:-}"
SK="$(cd "$(dirname "$0")/../.." && pwd)"
achar() { # $1 = nome do venv
  find "$SK/../../../" -maxdepth 4 -type d -name "$1" 2>/dev/null | while read d; do [ -x "$d/bin/python" ] && echo "$d/bin/python" && break; done
}
PY_WHISPER="${PY_WHISPER:-$(achar venv)}"; PY_ALIGN="${PY_ALIGN:-$(achar venv_align)}"
[ -n "$PY_WHISPER" ] && [ -n "$PY_ALIGN" ] || { echo "faltam os venvs (uv venv --python 3.12 venv && uv pip install --python venv/bin/python faster-whisper; e venv_align: ver SKILL.md)"; exit 2; }
mkdir -p "$PASTA/work"; cd "$PASTA/work"
[ -n "$VOCAB" ] && echo "$VOCAB" > vocabulary.txt
[ -f vocabulary.txt ] || echo "$(basename "$PASTA" | sed 's/^[0-9]* - //')" > vocabulary.txt
echo "[transcrição] $(date +%T) $FUNDIDO"
MODEL=large-v3 nice -n 5 "$PY_WHISPER" "$SK/template/transcribe.py" "$FUNDIDO" | tail -3
echo "[alinhamento] $(date +%T)"
cp transcription.json transcription_raw.json 2>/dev/null || true
nice -n 5 "$PY_ALIGN" "$SK/template/align.py" "$FUNDIDO" | tail -3
echo "[fim] $(date +%T)"
