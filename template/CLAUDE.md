# Animações — "lista de linguagens (exemplo)" (tipo Lista sem B-roll, tema Monokai)
Fluxo e padrões: skill `animacao-narracao` (`Tecnologia/.claude/skills/animacao-narracao/SKILL.md`).
- **Áudio editado → `./update_audio.sh`** (copia `../pronto.wav`, transcreve large-v3, alinha, `plan.py`, `tsc`). NÃO recriar nada: só ajustar âncoras que o corte quebrou.
- Plano: `plan_data.py` → `venv/bin/python plan.py` → `src/scenes/{scenes,menu,codes}.json`, `scene1.meta`, `PLAN.md`.
- Códigos: `codes_source.json` + `venv/bin/python scripts/validate_codes.py` (valida de verdade; Docker p/ asm, cobol, c#, java, lua, elixir).
- Render 4K (.mov alpha): painel Video Settings → RENDER (aguardar aprovação).

Lista com B-roll: `Assets/` ao lado do áudio → `scripts/broll/analyze_broll.py` → olhar folhas → `plan_broll.py` → `BROLL` no `plan_data.py` → `plan.py` → render → `scripts/capcut/spec_from_plan.py` + `build_draft.py` (veja SKILL.md).
