#!/usr/bin/env bash
# Reedição de áudio (cortes/ajustes): NÃO recria nada — só re-sincroniza o que já existe.
# 1) copia o áudio novo  2) transcreve (large-v3)  3) alinhamento forçado  4) plano.py (âncoras por FRASE se ajustam sozinhas)
# 5) valida (tsc + códigos).  Uso: ./atualizar_audio.sh [caminho_do_wav]   (padrão ../pronto.wav)
set -e
cd "$(dirname "$0")"
SRC="${1:-../pronto.wav}"; DST="src/audio/pronto.wav"
cp "$SRC" "$DST"
cp transcricao.json "transcricao_anterior.json" 2>/dev/null || true
MODELO=large-v3 venv/bin/python transcrever.py "$DST" > transcricao.log 2>&1
[ -x venv_align/bin/python ] && venv_align/bin/python alinhar.py "$DST" >> transcricao.log 2>&1
venv/bin/python plano.py 2>&1 | tee plano.log
npx tsc --noEmit && echo "tsc ok"
echo "Se alguma frase âncora não foi achada (corte removeu o trecho), edite só aquela âncora em plano_dados.py e rode venv/bin/python plano.py"
