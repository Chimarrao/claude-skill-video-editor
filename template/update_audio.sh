#!/usr/bin/env bash
# Reedição de áudio (cortes/ajustes): NÃO recria nada — só re-sincroniza o que já existe.
# 1) copia o áudio novo  2) transcreve (large-v3)  3) alinhamento forçado  4) plan.py (âncoras por FRASE se ajustam sozinhas)
# 5) valida (tsc + códigos).  Uso: ./update_audio.sh [caminho_do_wav]   (padrão ../pronto.wav)
set -e
cd "$(dirname "$0")"
SRC="${1:-../pronto.wav}"; DST="src/audio/pronto.wav"
cp "$SRC" "$DST"
cp transcription.json "transcription_previous.json" 2>/dev/null || true
MODEL=large-v3 venv/bin/python transcribe.py "$DST" > transcription.log 2>&1
[ -x venv_align/bin/python ] && venv_align/bin/python align.py "$DST" >> transcription.log 2>&1
venv/bin/python plan.py 2>&1 | tee plan.log
npx tsc --noEmit && echo "tsc ok"
echo "Se alguma frase âncora não foi achada (corte removeu o trecho), edite só aquela âncora em plan_data.py e rode venv/bin/python plan.py"
