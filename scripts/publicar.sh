#!/usr/bin/env bash
# Commit + push automático da skill (regra do usuário: TODA alteração na skill é commitada e enviada ao GitHub).
# Uso: scripts/publicar.sh "mensagem do commit"      (rodar depois de editar qualquer arquivo da skill)
# Antes do commit regenera banco/assets.publico.db a partir de banco/assets.db SEM as transcrições (banco/assets.db fica fora do git).
set -e
cd "$(dirname "$0")/.."
MSG="${1:-atualização da skill}"
if [ -f banco/assets.db ]; then
  cp banco/assets.db /tmp/_assets_pub.db
  # banco PÚBLICO: sem transcrições, sem referências de vídeos, sem fotos de pessoas/telas/objetos de vídeos específicos
  sqlite3 /tmp/_assets_pub.db "DELETE FROM transcricoes; DROP TABLE IF EXISTS videos; DELETE FROM assets WHERE categoria IN ('pessoa','tela','objeto'); VACUUM;" 2>/dev/null || true
  cp /tmp/_assets_pub.db banco/assets.publico.db
fi
git add -A
if git diff --cached --quiet; then echo "publicar: nada a commitar"; exit 0; fi
git commit -q -m "$MSG

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -q origin "$(git branch --show-current)" && echo "publicar: enviado ($(git log --oneline | head -1))"
