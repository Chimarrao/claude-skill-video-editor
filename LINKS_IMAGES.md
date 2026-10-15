# Links de imagens mais usadas (fonte oficial/confiável)
Use sempre a biblioteca `assets/` primeiro; estes links servem para baixar o que ainda não existir (e atualize esta lista quando achar uma nova fonte).
Download Wikimedia: `curl -sL -A "canal-anim/1.0 (email)" -o x.png "https://commons.wikimedia.org/wiki/Special:FilePath/<Arquivo>?width=800"` (sleep ≥1,5 s entre chamadas; 429 = rate limit). Simple Icons: `https://cdn.simpleicons.org/<slug>[/cor]`.

## Microsoft / Windows
- Windows 11 (wordmark): Commons `Windows_11_logo.svg` · ícone quadrado = recorte (0,0,170,177) → `logo_win11_icone.png`
- Windows 7: `Unofficial_fan_made_Windows_7_logo_variant.svg` · Vista: `..._Vista_logo_variant.svg` · XP: `..._XP_logo_variant.svg`
- Microsoft: `Microsoft_logo_(2012).svg` · Edge: `Microsoft_Edge_logo_(2019).svg` · Bing: `Bing_logo_(2016).svg` · OneDrive: `OneDrive_logo.svg`
- Copilot (colorido): `Microsoft-copilot-2026-seeklogo.svg` · Copilot+PC (laptop): `Microsoft_Copilot.png`
- Windows 11 screenshot: `Windows_11_screenshot.png` · TPM (foto): `TPM_Asus.jpg`
- Linux Mint desktop: `Linux_Mint_Cinnamon_22.3.png`
## Linguagens / tech (Simple Icons slugs)
c, cplusplus, dotnet, php, javascript, typescript, python, rust, go, lua, elixir, erlang, ruby, rubyonrails, kotlin, swift, mysql, postgresql, redis, docker, kubernetes, linux, linuxmint, github, firefox, googlechrome, intel, amd, nvidia, discord, pinterest, spotify, tiktok, instagram, wordpress, wikipedia, facebook, laravel, react, angular, vuedotjs, nodedotjs. (Não existem lá: Java → `Duke_(Java_mascot)_waving.svg`, C# → `C_Sharp_Logo_2023.svg`, Blizzard → `Blizzard_Entertainment_Logo_2015.svg`, Microsoft/Windows/Edge/Bing → Commons.)
## Pessoas (fotos)
- Wikipedia REST: `https://en.wikipedia.org/api/rest_v1/page/summary/<Titulo>` → `originalimage` → baixar via `Special:FilePath`.
- GitHub avatar: `api.github.com/users/<login>` · Bluesky: `public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor=<handle>` · Mastodon: `<instancia>/api/v1/accounts/lookup?acct=<user>`
- Lua (equipe): `https://www.lua.org/images/team.jpg`
## Ícones de linha
- Tabler (MIT): `https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/<name>.svg` (usado automaticamente via `ic:name`).
- Fluent Emoji 3D (MIT, tom leve): `download_icons.sh`.
