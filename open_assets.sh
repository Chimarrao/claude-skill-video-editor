#!/usr/bin/env bash
# Abre o banco de assets (SQLite, base64). Ex.: dentro do sqlite3:
#   SELECT nome, categoria, largura, altura FROM assets WHERE nome LIKE 'logo_%';
# Fora: ./open_assets.sh sync [pasta...] | list [filtro] | export 'logo_win%' [pasta]
# (aceita também os nomes antigos sincronizar/listar/exportar/abrir por compatibilidade)
cd "$(dirname "$0")" || exit 1
PY="python3"
for c in "${ANIMACAO_PY:-}" "./venv/bin/python" "$OLDPWD/venv/bin/python"; do
  [ -x "$c" ] && PY="$c" && break
done
if [ $# -eq 0 ]; then set -- open; fi
# Compatibilidade: traduz subcomandos antigos (pt) para os novos (en) antes de repassar
case "$1" in
  sincronizar) shift; set -- sync "$@" ;;
  listar) shift; set -- list "$@" ;;
  exportar) shift; set -- export "$@" ;;
  abrir) shift; set -- open "$@" ;;
esac
cd "$OLDPWD" 2>/dev/null || true
exec "$PY" "$(dirname "$0")/scripts/assets_db.py" "$@"
