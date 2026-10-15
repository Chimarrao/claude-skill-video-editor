#!/usr/bin/env bash
# Uso: baixar_icones.sh <pasta_destino> "Camera with flash" "Locked" "Brain" ...
# Baixa Fluent Emoji 3D (MIT, PNG transparente) -> <pasta>/camera_with_flash.png
# Pessoas/gestos têm variante: use "Man technologist" etc. (tenta .../Default/3D/..._default.png).
dest="$1"; shift; mkdir -p "$dest"
base="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets"
for n in "$@"; do
  f=$(echo "$n" | tr 'A-Z ' 'a-z_'); e=$(echo "$n" | sed 's/ /%20/g')
  c=$(curl -s -o "$dest/$f.png" -w "%{http_code}" "$base/$e/3D/${f}_3d.png")
  [ "$c" != 200 ] && c=$(curl -s -o "$dest/$f.png" -w "%{http_code}" "$base/$e/Default/3D/${f}_3d_default.png")
  echo "$c $n"; [ "$c" != 200 ] && rm -f "$dest/$f.png"
done
# Logos de marcas: curl -o x.svg https://cdn.simpleicons.org/<nome>/white
# Logos removidos do Simple Icons (Microsoft/Windows): Wikimedia -> curl -sL -A "x/1.0 (email)" "https://commons.wikimedia.org/wiki/Special:FilePath/<Arquivo.svg>?width=600" -o x.png (sleep 2 entre chamadas: rate limit 429)
