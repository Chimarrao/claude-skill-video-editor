#!/usr/bin/env bash
# Commit + push automático da skill (regra do usuário: TODA alteração na skill é commitada e enviada ao GitHub).
# Uso: scripts/publish.sh "mensagem do commit"      (rodar depois de editar qualquer arquivo da skill)
# Antes do commit regenera database/assets.publico.db (só referências) + database/public_images/ (arquivos) a partir de database/assets.db, SEM transcrições (assets.db e database/images/ ficam fora do git).
set -e
cd "$(dirname "$0")/.."
MSG="${1:-atualização da skill}"
python3 scripts/build_public_db.py   # banco público = só referências; as imagens públicas vão como arquivos em database/public_images/
git add -A
if git diff --cached --quiet; then echo "publish: nada a commitar"; exit 0; fi
git commit -q -m "$MSG

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -q origin "$(git branch --show-current)" && echo "publish: enviado ($(git log --oneline | head -1))"
