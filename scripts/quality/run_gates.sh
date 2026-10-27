#!/usr/bin/env bash
# QUALITY GATES em sequência (rodar em animacao/). Para no primeiro bloco que falhar e diz qual foi.
#   run_gates.sh            → gates antes do render: plano (STRICT), tsc, testes de regras, filtro de clipes, gate_plan
#   ALLOW_EMPTY=id1,id2 run_gates.sh → ids de Empty(...) declarados de propósito (ex.: vinheta do usuário) que o P6 aceita
#   run_gates.sh --frames   → também o gate de frames reais (precisa de output/project.mov e capcut_spec.json)
# Regra da skill: nada vai para o render/CapCut com gate vermelho; gate vermelho depois do render = corrigir e re-renderizar (ou recomeçar).
SK="$(cd "$(dirname "$0")/../.." && pwd)"
PY=venv/bin/python; [ -x "$PY" ] || PY=python3
PYA=venv_align/bin/python; [ -x "$PYA" ] || PYA=$PY
FALHAS=()
passo() { local nome="$1"; shift; echo; echo "=== $nome"; if "$@"; then echo "    ✅ $nome"; else echo "    ❌ $nome"; FALHAS+=("$nome"); fi; }
# o editor (render.mjs) reescreve src/scenes/scene1.meta quando o render termina: com ele aberto, plan.py e testes leem um meta incompleto (R5 falso)
if pgrep -f "render.mjs" > /dev/null; then echo "render.mjs ainda aberto: feche-o (touch /tmp/pp/render.stop) e espere sair antes de rodar os gates"; exit 2; fi
passo "plan.py (STRICT)" env STRICT=1 $PY plan.py
passo "tsc" npx tsc --noEmit
passo "motor: geometria/ritmo/alinhamento" $PY "$SK/scripts/tests/test_engine_geometry.py"
passo "gate 2: regras de frame (testes sintéticos)" $PY "$SK/scripts/tests/test_frame_rules.py"
passo "gate 1: testes do próprio gate (P8)" $PY "$SK/scripts/tests/test_gate_plan.py"
passo "regras da lista com B-roll" $PY "$SK/scripts/tests/test_list_broll_rules.py"
passo "clipes sem pessoas" $PY "$SK/scripts/tests/test_clips_without_people.py"
passo "clipes: filtro CLIP+OCR" env TOKENIZERS_PARALLELISM=false $PYA "$SK/scripts/broll/classify_frames.py" --clips
passo "folhas dos clipes (OLHAR!)" $PY "$SK/scripts/quality/clip_sheets.py"
passo "gate 1: plano (ritmo, setas, imagens, janelas vazias)" $PY "$SK/scripts/quality/gate_plan.py" --allow-empty "${ALLOW_EMPTY:-}"
if [ "$1" = "--frames" ]; then
  passo "montagem do CapCut: marca" $PY "$SK/scripts/tests/test_capcut_brand.py"
  passo "montagem do CapCut: overlay recortado" $PY "$SK/scripts/tests/test_capcut_overlay.py"
  passo "gate 2: frames reais" $PY "$SK/scripts/quality/gate_frames.py"
fi
echo
if [ ${#FALHAS[@]} -gt 0 ]; then echo "GATES VERMELHOS: ${FALHAS[*]}"; exit 1; fi
echo "TODOS OS GATES VERDES"
