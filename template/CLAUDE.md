# Animações — "lista de linguagens (exemplo)" (tipo Lista sem B-roll, tema Monokai)
Fluxo e padrões: skill `animacao-narracao` (`Tecnologia/.claude/skills/animacao-narracao/SKILL.md`).
- **Áudio editado → `./atualizar_audio.sh`** (copia `../pronto.wav`, transcreve large-v3, alinha, `plano.py`, `tsc`). NÃO recriar nada: só ajustar âncoras que o corte quebrou.
- Plano: `plano_dados.py` → `venv/bin/python plano.py` → `src/scenes/{cenas,menu,codigos}.json`, `cena1.meta`, `PLANO.md`.
- Códigos: `codigos_fonte.json` + `venv/bin/python scripts/validar_codigos.py` (valida de verdade; Docker p/ asm, cobol, c#, java, lua, elixir).
- Render 4K (.mov alpha): painel Video Settings → RENDER (aguardar aprovação).

Lista com B-roll: `Assets/` ao lado do áudio → `scripts/broll/analisar_broll.py` → olhar folhas → `planejar_broll.py` → `BROLL` no `plano_dados.py` → `plano.py` → render → `scripts/capcut/spec_do_plano.py` + `montar_draft.py` (veja SKILL.md).
