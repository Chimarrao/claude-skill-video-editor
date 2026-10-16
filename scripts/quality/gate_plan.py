#!/usr/bin/env python3
"""QUALITY GATE 1 (estático): confere os JSONs gerados pelo plan.py contra cada defeito que o usuário já reprovou.
Roda em animacao/ depois de `plan.py`. Sai com 1 se houver ERRO; AVISO pede olhar a folha de contato (gate_frames.py).

 P1 ritmo        itens de um grafo entram a >= ITEM_GAP s; no gancho (35 s) no máx. ~0,55 entradas/s
 P2 setas        ligação única/≤2 ramos = reta e alinhada; a seta não corta rótulo/ícone (geometry.py); rótulos não se sobrepõem
 P3 enumerações  itens sem ligações = fileira lado a lado (mesmo y), nunca coluna
 P4 linha do tempo  proibida na abertura (< 120 s) salvo ALLOW_TIMELINE_INTRO=True; marcos precisam de âncora falada
 P5 imagens      rótulo que cita um assunto do catálogo (BeOS, NeXTSTEP, Windows XP…) com ícone genérico = ERRO: use a logo/foto
 P6 janelas vazias  trecho > 4 s sem animação NEM clipe (só fundo + fala) = ERRO (abertura inclusa), exceto `Empty` declarado
 P7 rótulos      <= 26 caracteres, primeira letra maiúscula, sem rótulo repetido no mesmo grafo
 P8 clipes       dois clipes nunca repetem o mesmo trecho do mesmo vídeo-fonte, nem se sobrepõem na linha do tempo
 P9 título×grafo item de grafo NUNCA entra enquanto um título cobre o palco (o resto escurece: os itens "aparecem do nada" depois)
 P10 quadro      ícone ou RÓTULO a < 60 px da borda do quadro ou dentro da zona do avatar (canto inferior direito), já com ampliação/deslocamento
Grava qa/gate_plan.json. Uso: python gate_plan.py [--gap 0.9] [--allow-empty id1,id2]
"""

import argparse, json, os, re, sys
from pathlib import Path

cwd = Path.cwd()
ap = argparse.ArgumentParser()
ap.add_argument("--gap", type=float, default=None, help="intervalo mínimo entre itens (padrão: ITEM_GAP do plan_data ou 0,9)")
ap.add_argument("--allow-empty", default="", help="ids de cenas que podem ficar sem nada na tela (ex.: Empty declarado de propósito)")
ap.add_argument("--hook-seconds", type=float, default=35.0)
args = ap.parse_args()
assert (cwd / "plan.json").exists() and (cwd / "src/scenes/scenes.json").exists(), "rode dentro de animacao/ depois do plan.py"
sys.path.insert(0, str(cwd))
import geometry  # noqa: E402  (copiado do template para o projeto)

J = lambda p: json.load(open(cwd / p))
plan, scenes, meta = J("plan.json"), J("src/scenes/scenes.json"), J("src/scenes/scene1.meta")
broll = J("src/scenes/broll.json") if (cwd / "src/scenes/broll.json").exists() else []
src = (cwd / "plan_data.py").read_text(encoding="utf8") if (cwd / "plan_data.py").exists() else ""


def flag(nome, default):
    m = re.search(rf"^{nome}\s*=\s*([^\s#]+)", src, re.M)
    return m.group(1) if m else default


GAP = args.gap if args.gap is not None else float(flag("ITEM_GAP", "0.9"))
ALLOW_TL = str(flag("ALLOW_TIMELINE_INTRO", "False")) == "True"
events = {e["name"]: e["targetTime"] for e in meta["timeEvents"]}
errors, warns = [], []
erro = lambda c, m: errors.append(f"{c}: {m}")
aviso = lambda c, m: warns.append(f"{c}: {m}")

# ---------- catálogo (sugestões de imagem) ----------
ROOT = Path(__file__).resolve().parents[2]
catalog = {}
cat_path = ROOT / "database" / "image_catalog.json"
if cat_path.exists():
    catalog = json.load(open(cat_path, encoding="utf8")).get("images", {})
assets = {p.stem for p in (ROOT / "assets").glob("*") if p.is_file()}
subjects = {}  # slug -> melhor nome de arquivo de logo/foto
for name, v in catalog.items():
    if v.get("quality", "ok") == "ok":  # só sugere imagem verificada (check/low ficam de fora)
        subjects.setdefault(v["subject"], []).append(name)
for a in assets:
    if a.startswith(("logo_", "foto_")):
        subjects.setdefault(a.split("_", 1)[1], []).append(a)


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split()


def sugestao(label):
    """Assunto do catálogo citado no rótulo (todas as palavras do slug presentes), com a melhor imagem sugerida."""
    toks = set(norm(label))
    melhores = []
    for slug, files in subjects.items():
        partes = [p for p in slug.split("_") if p]
        if len(partes) == 0 or (len(partes) == 1 and len(partes[0]) < 3):
            continue
        if all(p in toks for p in partes):
            pref = sorted(files, key=lambda n: (not n.startswith(("logo_", "foto_")), len(n)))
            melhores.append((len(partes), slug, pref[0]))
    return max(melhores)[2] if melhores else None


# ---------- grafos (cenas G e peças Graph dentro de item/section) ----------
def grafos():
    for c in scenes:
        if c["kind"] == "graph":
            yield c["id"], c["items"], c["edges"], None, (1.0, 0.0, 0.0)
        for p in c.get("pieces", []):
            if p["kind"] == "graph":
                pr = p["props"]
                yield c["id"] + "/graph", pr["items"], pr["edges"], pr.get("events"), (pr.get("zoom", 1.0), pr.get("dx", 0.0), pr.get("dy", 0.0))


for gid, items, edges, evs, (zoom, gdx, gdy) in grafos():
    base = gid.split("/")[0]
    # P10 quadro: nada (ícone nem rótulo) na borda ou na zona do avatar
    for pb in geometry.frame_problems(items, zoom, gdx, gdy):
        erro("P10 quadro", f"[{gid}] {pb}")
    # P2 geometria
    for pb in geometry.problems(items, edges):
        erro("P2 setas", f"[{gid}] {pb}")
    kids, pais = {}, {}
    for e in edges:
        kids.setdefault(e["src"], []).append(e["dst"])
        pais.setdefault(e["dst"], []).append(e["src"])
    for e in edges:
        a, b = items[e["src"]], items[e["dst"]]
        lado = "x" if e["sides"][0] in ("bottom", "top") else "y"
        desvio = abs(a[lado] - b[lado])
        if len(kids[e["src"]]) == 1 and len(pais[e["dst"]]) == 1:
            if e["style"] != "straight" or desvio > 8:
                erro("P2 setas", f"[{gid}] ligação única {e['src'] + 1}→{e['dst'] + 1} não é reta/alinhada (estilo {e['style']}, desvio {desvio:.0f}px)")
        elif len(kids[e["src"]]) <= 2 and e["style"] != "straight":
            erro("P2 setas", f"[{gid}] {e['src'] + 1}→{e['dst'] + 1}: até 2 ramos devem ser retos")
    # P3 enumeração em fileira
    if not edges and len([i for i in items if i.get("img")]) >= 3:
        ys = [i["y"] for i in items if i.get("img") and not i.get("beat") == "x"]
        if max(ys) - min(ys) > 8:
            erro("P3 enumeração", f"[{gid}] {len(ys)} itens sem ligações em coluna/desalinhados (y varia {max(ys) - min(ys):.0f}px): deve ser fileira lado a lado")
    # P5 imagens do catálogo
    for k, it in enumerate(items):
        lab = it.get("label") or ""
        if str(it.get("img", "")).startswith("ic-") and lab:
            sug = sugestao(lab)
            if sug:
                erro("P5 imagens", f"[{gid}] item {k + 1} '{lab}' usa ícone genérico, mas há imagem no catálogo: {sug} (Item('{sug}', plate=True…))")
        # P7 rótulos
        if lab and len(lab) > 26:
            erro("P7 rótulos", f"[{gid}] '{lab}' > 26 caracteres")
    labs = [i.get("label") for i in items if i.get("label")]
    if len(labs) != len(set(labs)):
        aviso("P7 rótulos", f"[{gid}] rótulo repetido no mesmo grafo")
    # P1 ritmo (por evento do item)
    tempos = []
    if evs:
        tempos = sorted({round(events[e], 2) for e in evs if e and e in events})
    else:
        beats = sorted({i["beat"] for i in items if i.get("beat")})
        tempos = sorted({round(events.get(f"{base}-{b}", 0), 2) for b in beats if f"{base}-{b}" in events})
    for a, b in zip(tempos, tempos[1:]):
        if b - a < GAP - 0.06:
            erro("P1 ritmo", f"[{gid}] itens a {b - a:.2f}s um do outro ({a:.1f}→{b:.1f}s; mínimo {GAP}s)")

# P1 densidade do gancho
reveals = sorted({round(t, 1) for n, t in events.items() if re.search(r"-g\d+_|-b\d+$", n) and t < args.hook_seconds})
if len(reveals) / args.hook_seconds > 0.55:
    erro("P1 ritmo", f"gancho com {len(reveals)} entradas em {args.hook_seconds:.0f}s ({len(reveals) / args.hook_seconds:.2f}/s > 0,55/s): reduza ou espace as animações")

# P4 linha do tempo
for c in scenes:
    if c["kind"] == "timeline":
        t0 = plan["windows"].get(c["id"], [0])[0]
        if t0 < 120 and not ALLOW_TL:
            erro("P4 linha do tempo", f"[{c['id']}] linha do tempo na abertura ({t0:.0f}s): não prende nem explica; use animação ancorada na fala (ALLOW_TIMELINE_INTRO=True libera)")

# P6 janelas vazias (só fundo + fala): união de animação (plan.json life) + clipes
cobertura = []
for k, spans in plan.get("life", {}).items():
    cobertura += [tuple(s) for s in spans]
cobertura += [(b["t_start"], b["t_end"]) for b in broll]
if plan.get("promo_t") is not None:  # a propaganda do CapCut ocupa esse trecho: não é janela vazia
    cobertura.append((plan["promo_t"], plan.get("promo_resume") or plan["promo_t"]))
cobertura.sort()
merged = []
for a, b in cobertura:
    if merged and a <= merged[-1][1] + 0.05:
        merged[-1][1] = max(merged[-1][1], b)
    else:
        merged.append([a, b])
permitidos = set(filter(None, args.allow_empty.split(",")))
t = 0.0
vazios = []
for a, b in merged + [[plan["duration"], plan["duration"]]]:
    if a - t > 4.0:
        vazios.append((round(t, 1), round(a, 1)))
    t = max(t, b)
for a, b in vazios:
    ids = [i for i, w in plan["windows"].items() if w[0] <= a + 0.1 and w[1] >= b - 0.1]
    if ids and all(i in permitidos for i in ids):
        continue
    erro("P6 janela vazia", f"{a:.1f}–{b:.1f}s ({b - a:.1f}s, cena {','.join(ids) or '?'}) só com fundo e fala: coloque animação/B-roll")

# P9 título×grafo: o título cobre o palco (o resto escurece) de `início` até `início + 0,25 + 0,4 + digitação + dur + 0,35`;
# item de grafo que entra nesse intervalo fica invisível e "aparece do nada" quando o título sai
for c in scenes:
    for p in c.get("pieces", []):
        if p["slot"] != "overlay" or p["kind"] != "title":
            continue
        t_ini = events.get(f"{c['id']}-{p['beat']}")
        if t_ini is None:
            continue
        palavras = [w for l in p["props"]["lines"] for w in re.sub(r"\*([a-z]:)?", "", l).split()]
        digitacao = sum(max(0.07, len(w) * 0.028) + 0.04 for w in palavras)
        t_fim = t_ini + 0.25 + 0.4 + digitacao + p["props"]["dur"] + 0.35
        for q in c.get("pieces", []):
            if q["kind"] != "graph":
                continue
            for ev in q["props"].get("events") or []:
                te = events.get(ev)
                if te is not None and t_ini + 0.05 < te < t_fim - 0.3:
                    erro("P9 título×grafo", f"[{c['id']}] item de grafo em {te:.1f}s entra com o título cobrindo o palco ({t_ini:.1f}–{t_fim:.1f}s): encurte o título (dur) ou ancore o item depois")

# P8 clipes: trecho repetido do mesmo arquivo (o espectador vê a mesma cena duas vezes) ou clipes sobrepostos no tempo
por_arquivo = {}
for k, b in enumerate(broll, 1):
    for k2, a0, a1 in por_arquivo.get(b["file"], []):
        if min(a1, b["out"]) - max(a0, b["in"]) > 0.5:
            erro("P8 clipes", f"clip {k} ({b['in']:.0f}–{b['out']:.0f}s) repete o trecho do clip {k2} ({a0:.0f}–{a1:.0f}s) de {os.path.basename(b['file'])}")
    por_arquivo.setdefault(b["file"], []).append((k, b["in"], b["out"]))
for k, (a, b) in enumerate(zip(broll, broll[1:]), 1):
    if b["t_start"] < a["t_end"] - 0.05:
        erro("P8 clipes", f"clip {k + 1} começa em {b['t_start']:.1f}s antes de o clip {k} terminar ({a['t_end']:.1f}s)")

os.makedirs(cwd / "qa", exist_ok=True)
json.dump(dict(errors=errors, warnings=warns, gap=GAP), open(cwd / "qa/gate_plan.json", "w"), ensure_ascii=False, indent=1)
for w in warns:
    print("AVISO ", w)
for e in errors:
    print("ERRO  ", e)
print(f"\nGATE 1 (plano): {'FALHOU' if errors else 'OK'} — {len(errors)} erro(s), {len(warns)} aviso(s)")
sys.exit(1 if errors else 0)
