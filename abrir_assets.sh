#!/usr/bin/env bash
# Abre o banco de assets (SQLite, base64). Ex.: dentro do sqlite3:
#   SELECT nome, categoria, largura, altura FROM assets WHERE nome LIKE 'logo_%';
# Fora: ./abrir_assets.sh sincronizar [pasta...] | listar [filtro] | exportar 'logo_win%' [pasta]
cd "$(dirname "$0")" || exit 1
PY="python3"
for c in "${ANIMACAO_PY:-}" "./venv/bin/python" "$OLDPWD/venv/bin/python"; do
  [ -x "$c" ] && PY="$c" && break
done
if [ $# -eq 0 ]; then set -- abrir; fi
cd "$OLDPWD" 2>/dev/null || true
exec "$PY" "$(dirname "$0")/scripts/assets_db.py" "$@"
