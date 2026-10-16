#!/usr/bin/env bash
# Render do overlay em TRECHOS (resiste a queda do Chrome por falta de memória: o macOS com swap cheio derruba o Chrome headless
# no meio do render de 30 min e perde tudo). Cada trecho vira /tmp/slices/part_K.mov (+ .ok); no fim concatena sem recodificar.
# Uso (em animacao/, vite na porta 9000):  bash <skill>/scripts/render_slices.sh [duração_total_s] [trecho_s=174]
#   ex.: render_slices.sh 869.42        → 5 trechos de 174 s; trecho que cair é refeito (até 3 tentativas); trechos prontos são pulados
# Detalhe: o `range` do Motion Canvas é INCLUSIVO no fim (6 s = 181 quadros), então cada trecho termina 1/30 s antes do próximo começar.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TOTAL="${1:?informe a duração total do áudio em segundos (plan.json: duration)}"
LEN="${2:-174}"
N=$(python3 -c "import math;print(math.ceil($TOTAL/$LEN))")
mkdir -p /tmp/slices
# ESM resolve `puppeteer-core` a partir da pasta do .mjs: roda uma cópia numa pasta que tenha o pacote (PUPPETEER_DIR, padrão /tmp/pp)
PDIR="${PUPPETEER_DIR:-/tmp/pp}"
mkdir -p "$PDIR"
[ -d "$PDIR/node_modules/puppeteer-core" ] || (cd "$PDIR" && npm i puppeteer-core >/dev/null 2>&1)
cp "$HERE/render_one.mjs" "$PDIR/render_one.mjs"
setrange() { python3 - "$1" "$2" <<'P'
import json, sys
m = json.load(open("src/project.meta"))
m["shared"]["range"] = [float(sys.argv[1]), None if sys.argv[2] == "null" else float(sys.argv[2])]
json.dump(m, open("src/project.meta", "w"), indent=2)
P
}
# O EDITOR TRUNCA O scene1.meta quando um render termina/cai (196 → ~46 eventos). Render com meta truncado dá overlay EMBARALHADO
# (as peças de todas as cenas aparecem juntas, os eventos "já passaram"). Por isso: plan.py restaura o meta antes de CADA trecho e
# o trecho só começa com o meta completo.
restaura_meta() {
  python3 plan.py > /dev/null 2>&1 || { echo "plan.py falhou"; exit 1; }
  python3 - <<'P'
import json, sys
n = len(json.load(open("src/scenes/scene1.meta"))["timeEvents"])
plan = len(json.load(open("plan.json"))["events"])
if n < plan:
    print(f"meta truncado ({n} de {plan} eventos): abortando"); sys.exit(1)
P
}
for K in $(seq 0 $((N - 1))); do
  [ -f /tmp/slices/part_$K.ok ] && continue
  A=$((K * LEN))
  if [ "$K" -eq $((N - 1)) ]; then B=null; else B=$(python3 -c "print(round(($K+1)*$LEN-1/30,4))"); fi
  setrange "$A" "$B"
  for TENT in 1 2 3; do
    rm -f output/project.mov /tmp/slices/part_$K.ok
    echo "== trecho ${K} (${A} a ${B}) tentativa ${TENT} $(date +%T)"
    pkill -f "Google Chrome.*headless" 2>/dev/null; sleep 2
    restaura_meta || exit 1
    setrange "$A" "$B"
    OUT="$PWD/output" node "$PDIR/render_one.mjs" 2>&1 | tail -3
    DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 output/project.mov 2>/dev/null || true)
    MIN=$([ "$K" -eq $((N - 1)) ] && echo 5 || echo $((LEN - 2)))
    if [ -n "$DUR" ] && python3 -c "import sys;sys.exit(0 if float('$DUR')>$MIN else 1)"; then
      mv output/project.mov /tmp/slices/part_$K.mov && touch /tmp/slices/part_$K.ok
      break
    fi
  done
done
setrange 0 null
# cada trecho (menos o último) traz 1 quadro a mais que o pretendido (o fim do range é inclusivo e arredonda para cima): `outpoint` = LEN s
# descarta esse quadro (ProRes é intra-quadro: o corte com -c copy é exato) — senão cada emenda duplicaria 1 quadro e o overlay atrasaria 1/30 s por trecho
for K in $(seq 0 $((N - 1))); do
  echo "file '/tmp/slices/part_$K.mov'"
  [ "$K" -lt $((N - 1)) ] && echo "outpoint $LEN"
done > /tmp/slices/list.txt
ffmpeg -v error -y -f concat -safe 0 -i /tmp/slices/list.txt -c copy output/project.mov && echo "CONCAT-OK $(date +%T)"
ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 output/project.mov | sed 's/^/quadros no overlay final: /'
echo "(esperado ≈ duração × 30 + 1; confira com: python3 -c \"print($TOTAL*30)\")"
