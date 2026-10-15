#!/usr/bin/env bash
# Uso: download_icons.sh <pasta_destino> "Camera with flash" "Locked" "Brain" ...
# Baixa Fluent Emoji 3D (MIT, PNG transparente) -> <pasta>/camera_with_flash.png
# Pessoas/gestos têm variante: use "Man technologist" etc. (tenta .../Default/3D/..._default.png).
dest="$1"; shift; mkdir -p "$dest"
base="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets"
for name in "$@"; do
  file=$(echo "$name" | tr 'A-Z ' 'a-z_'); encoded=$(echo "$name" | sed 's/ /%20/g')
  code=$(curl -s -o "$dest/$file.png" -w "%{http_code}" "$base/$encoded/3D/${file}_3d.png")
  [ "$code" != 200 ] && code=$(curl -s -o "$dest/$file.png" -w "%{http_code}" "$base/$encoded/Default/3D/${file}_3d_default.png")
  echo "$code $name"; [ "$code" != 200 ] && rm -f "$dest/$file.png"
done
# Logos de marcas: curl -o x.svg https://cdn.simpleicons.org/<nome>/white
# Logos removidos do Simple Icons (Microsoft/Windows): Wikimedia -> curl -sL -A "x/1.0 (email)" "https://commons.wikimedia.org/wiki/Special:FilePath/<Arquivo.svg>?width=600" -o x.png (sleep 2 entre chamadas: rate limit 429)
