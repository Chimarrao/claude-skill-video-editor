#!/usr/bin/env bash
# Commit + push automático da skill (regra do usuário: TODA alteração na skill é commitada e enviada ao GitHub).
# Uso: scripts/publish.sh "mensagem do commit"      (rodar depois de editar qualquer arquivo da skill)
# Antes do commit regenera database/assets.publico.db a partir de database/assets.db SEM as transcrições (database/assets.db fica fora do git).
set -e
cd "$(dirname "$0")/.."
MSG="${1:-atualização da skill}"
if [ -f database/assets.db ]; then
  cp database/assets.db /tmp/_assets_pub.db
  # banco PÚBLICO: só logos pequenas (<= 100 KB, livres e de boa qualidade); sem transcrições, vídeos, fotos de pessoas, telas ou objetos
  sqlite3 /tmp/_assets_pub.db "DELETE FROM transcripts; DROP TABLE IF EXISTS videos; DELETE FROM assets WHERE category IN ('person','screen','object','photo') OR bytes > 100000 OR COALESCE(quality,'ok') != 'ok' OR COALESCE(nonfree,0) = 1; VACUUM;" 2>/dev/null || true
  cp /tmp/_assets_pub.db database/assets.publico.db
fi
git add -A
if git diff --cached --quiet; then echo "publish: nada a commitar"; exit 0; fi
git commit -q -m "$MSG

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -q origin "$(git branch --show-current)" && echo "publish: enviado ($(git log --oneline | head -1))"
