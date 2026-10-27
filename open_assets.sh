#!/usr/bin/env bash
# Abre o banco de assets (SQLite; imagens como arquivos em database/images/). Ex.: dentro do sqlite3:
#   SELECT name, category, width, height FROM assets WHERE name LIKE 'logo_%';
# Fora: ./open_assets.sh sync [pasta...] | list [filtro] | export 'logo_win%' [pasta]
cd "$(dirname "$0")" || exit 1
PY="python3"
for c in "${ANIMATION_PY:-}" "./venv/bin/python" "$OLDPWD/venv/bin/python"; do
  [ -x "$c" ] && PY="$c" && break
done
if [ $# -eq 0 ]; then set -- open; fi
cd "$OLDPWD" 2>/dev/null || true
exec "$PY" "$(dirname "$0")/scripts/assets_db.py" "$@"
