"""Pacote de MARCA para os projetos do CapCut: música de fundo, avatar no canto, propaganda (inserida após o gancho) e vinheta final.

Esses elementos são "predefinições" (clipes compostos) que o editor salva no CapCut. Em vez de refazê-los, a skill os COPIA de um projeto
de referência já editado à mão e os injeta em todo projeto novo:

    1) extrair  (uma vez):  python extrair_pacote_marca.py --ref <draft_com_propaganda_avatar_musica> --ref-final <draft_com_vinheta_final>
       -> grava `privado/pacote_marca/` (pacote.json + subdraft/ + Resources/combination/). Pasta IGNORADA pelo git (é a marca do canal).
    2) aplicar  (automático em montar_draft.py quando o spec traz "marca"): insere a propaganda no tempo T, desloca o resto da timeline,
       estende música e preenchimento até o fim e coloca avatar/vinheta final.

Layout resultante (de baixo para cima): preenchimento · clipes (B-roll + propaganda) · overlay · avatar · final · narração (+ áudio da propaganda) · música.
Regras do editor:  avatar NÃO aparece durante a propaganda nem na vinheta final;  a música vai do início ao fim;  o B-roll vai até o fim, com a vinheta
final POR CIMA dele;  volume normalizado (loudness) na música e na propaganda.
"""

import json
import re
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

PH = "##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##"
RAIZ_SKILL = Path(__file__).resolve().parent.parent.parent
PACOTE_PADRAO = RAIZ_SKILL / "privado" / "pacote_marca"
# nomes padrão das predefinições do CapCut (o editor as chama "Minhas predefinições N"); sobrescreva por argumento se mudar
NOMES_PADRAO = dict(
    avatar="predefinições6", propaganda="predefinições4", musica="predefinições2", final="predefinições3"
)

novo_id = lambda: str(uuid.uuid4()).upper()


def _indexar(draft):
    """Mapa id -> (lista, material) de todos os materiais do draft."""
    indice = {}
    for lista, itens in draft["materials"].items():
        if isinstance(itens, list):
            for material in itens:
                if isinstance(material, dict) and "id" in material:
                    indice[material["id"]] = (lista, material)
    return indice


def _nome_material(material):
    return material.get("material_name") or material.get("name") or ""


def _segmentos_do_papel(draft, trecho_nome, tipo):
    """Segmentos (trilha, segmento, grupo, material) cujo material tem `trecho_nome` no nome, na ordem do tempo."""
    indice = _indexar(draft)
    achados = []
    for trilha in draft["tracks"]:
        if trilha["type"] != tipo:
            continue
        for seg in trilha["segments"]:
            grupo, material = indice.get(seg["material_id"], ("?", {}))
            if trecho_nome in _nome_material(material):
                achados.append((trilha, seg, grupo, material))
    achados.sort(key=lambda x: x[1]["target_timerange"]["start"])
    return achados


def _item(draft, seg, grupo, material):
    """Item serializável: o segmento + o material principal + os materiais extras (speed, combination, loudness...)."""
    indice = _indexar(draft)
    extras = [(indice[r][0], indice[r][1]) for r in seg.get("extra_material_refs", []) if r in indice]
    return dict(segmento=seg, principal=(grupo, material), extras=extras)


def extrair(ref, ref_final=None, nomes=None, saida=PACOTE_PADRAO):
    """Lê (somente leitura) os drafts de referência e grava o pacote de marca em `saida`."""
    nomes = {**NOMES_PADRAO, **(nomes or {})}
    saida = Path(saida)
    if saida.exists():
        shutil.rmtree(saida)
    (saida / "subdraft").mkdir(parents=True)
    (saida / "Resources" / "combination").mkdir(parents=True)
    papeis = {}
    fontes = [(Path(ref), json.load(open(Path(ref) / "draft_info.json")))]
    if ref_final:
        fontes.append((Path(ref_final), json.load(open(Path(ref_final) / "draft_info.json"))))

    def procurar(nome, tipo):
        for pasta, draft in fontes:
            achados = _segmentos_do_papel(draft, nome, tipo)
            if achados:
                return pasta, draft, achados
        raise SystemExit(f"predefinição '{nome}' ({tipo}) não encontrada nos drafts de referência")

    pasta, draft, av = procurar(nomes["avatar"], "video")
    papeis["avatar_inicio"] = (pasta, _item(draft, av[0][1], av[0][2], av[0][3]))
    papeis["avatar_continua"] = (pasta, _item(draft, av[-1][1], av[-1][2], av[-1][3]))
    pasta, draft, pv = procurar(nomes["propaganda"], "video")
    papeis["propaganda_video"] = (pasta, _item(draft, pv[0][1], pv[0][2], pv[0][3]))
    pasta, draft, pa = procurar(nomes["propaganda"], "audio")
    papeis["propaganda_audio"] = (pasta, _item(draft, pa[0][1], pa[0][2], pa[0][3]))
    pasta, draft, mu = procurar(nomes["musica"], "audio")
    papeis["musica"] = (pasta, _item(draft, mu[0][1], mu[0][2], mu[0][3]))
    pasta, draft, fi = procurar(nomes["final"], "video")
    papeis["final"] = (pasta, _item(draft, fi[0][1], fi[0][2], fi[0][3]))

    meta18, pastas_copiadas = [], set()
    for papel, (pasta, item) in papeis.items():
        texto = json.dumps(item, ensure_ascii=False)
        for sub in set(re.findall(r"/subdraft/([0-9A-F-]{36})", texto)):  # subdrafts dos clipes compostos
            if sub not in pastas_copiadas and (pasta / "subdraft" / sub).exists():
                shutil.copytree(pasta / "subdraft" / sub, saida / "subdraft" / sub)
                pastas_copiadas.add(sub)
        for arq in set(re.findall(r"Resources/combination/([^\"/]+)", texto)):  # áudios guardados no projeto
            origem = pasta / "Resources" / "combination" / arq
            if origem.exists():
                shutil.copy2(origem, saida / "Resources" / "combination" / arq)
        meta = json.load(open(pasta / "draft_meta_info.json"))
        for grupo in meta.get("draft_materials", []):
            if grupo.get("type") == 18:
                for entrada in grupo["value"]:
                    if (
                        any(sub in entrada.get("file_Path", "") for sub in pastas_copiadas)
                        and entrada not in meta18
                    ):
                        meta18.append(entrada)
    json.dump(
        dict(papeis={k: v[1] for k, v in papeis.items()}, meta18=meta18),
        open(saida / "pacote.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    print(f"pacote de marca gravado em {saida}: {sorted(papeis)} · {len(pastas_copiadas)} clipes compostos")
    return saida


def carregar(pasta=PACOTE_PADRAO):
    """Carrega o pacote; devolve None se não existir (o projeto sai sem marca)."""
    pasta = Path(pasta)
    if not (pasta / "pacote.json").exists():
        return None
    dados = json.load(open(pasta / "pacote.json"))
    dados["pasta"] = pasta
    return dados


def _clonar(item, mats, inicio_us, duracao_us, src_inicio_us=0, volume=None):
    """Cria um segmento novo a partir do item do pacote (novos IDs, novos materiais) e o devolve."""
    grupo, principal = item["principal"]
    novo_principal = deepcopy(principal)
    novo_principal["id"] = novo_id()
    mats.setdefault(grupo, []).append(novo_principal)
    refs = []
    for grupo_extra, extra in item["extras"]:
        copia = deepcopy(extra)
        copia["id"] = novo_id()
        mats.setdefault(grupo_extra, []).append(copia)
        refs.append(copia["id"])
    seg = deepcopy(item["segmento"])
    seg.update(
        id=novo_id(),
        material_id=novo_principal["id"],
        extra_material_refs=refs,
        source_timerange={"start": src_inicio_us, "duration": duracao_us},
        target_timerange={"start": inicio_us, "duration": duracao_us},
    )
    if volume is not None:
        seg["volume"] = volume
    return seg


def _duracao(item):
    return item["segmento"]["target_timerange"]["duration"]


def _recortar(seg, inicio_us, fim_us, mats):
    """Pedaço do segmento restrito ao intervalo de timeline [inicio_us, fim_us] (a fonte acompanha). Devolve None se vazio."""
    ini = seg["target_timerange"]["start"]
    fim = ini + seg["target_timerange"]["duration"]
    a, b = max(ini, inicio_us), min(fim, fim_us)
    if b - a < 1000:
        return None
    novo = deepcopy(seg)
    velocidade = seg.get("speed") or 1.0
    novo["target_timerange"] = {"start": a, "duration": b - a}
    novo["source_timerange"] = {
        "start": seg["source_timerange"]["start"] + int(round((a - ini) * velocidade)),
        "duration": int(round((b - a) * velocidade)),
    }
    return novo


def _deslocar(trilhas, mats, t_us, retoma_us, d_us):
    """Abre espaço para a propaganda.

    t_us        instante em que a narração PARA (dentro da pausa depois do gancho)
    retoma_us   instante da narração original em que ela RETOMA (logo antes da próxima frase) — o silêncio [t, retoma] é removido
    d_us        duração da propaganda
    Tudo que começa depois de `retoma_us` desloca para a direita em (d_us − silêncio removido); o que cai dentro do silêncio some;
    o que atravessa t_us ou retoma_us é cortado (a fonte continua de onde parou).
    """
    delta = d_us - (retoma_us - t_us)
    for trilha in trilhas:
        if trilha.get("name") == "preenchimento":  # contínuo: só estende
            ultimo = trilha["segments"][-1]
            ultimo["target_timerange"]["duration"] += delta
            ultimo["source_timerange"]["duration"] += delta
            continue
        novos = []
        for seg in trilha["segments"]:
            antes = _recortar(seg, 0, t_us, mats)
            depois = _recortar(seg, retoma_us, 10**15, mats)
            if antes is not None:
                novos.append(antes)
            if depois is not None:
                depois["target_timerange"]["start"] += delta
                if (
                    antes is not None
                ):  # segmento partido em dois: a metade nova precisa dos próprios materiais extras
                    depois["id"] = novo_id()
                    depois["extra_material_refs"] = _copiar_extras(seg.get("extra_material_refs", []), mats)
                novos.append(depois)
        trilha["segments"] = novos


def _copiar_extras(refs, mats):
    """Duplica os materiais extras (speeds, canvas...) para a metade nova de um segmento cortado."""
    indice = _indexar({"materials": mats})
    novos = []
    for r in refs:
        if r in indice:
            lista, mat = indice[r]
            copia = deepcopy(mat)
            copia["id"] = novo_id()
            mats[lista].append(copia)
            novos.append(copia["id"])
    return novos


def _trilha(modelo, nome, segmentos):
    """Trilha nova com o mesmo formato de uma trilha-modelo do template."""
    trilha = deepcopy(modelo)
    trilha.update(id=novo_id(), name=nome, segments=segmentos)
    return trilha


def aplicar(
    pacote,
    tracks,
    mats,
    proj,
    meta,
    narr_fim_us,
    t_propaganda_us,
    retoma_us=None,
    final_antes_us=6_900_000,
    estender_broll=True,
):
    """Injeta a marca no projeto em montagem.

    pacote           dado de `carregar()`
    tracks           lista de trilhas já montadas (preenchimento, clipes, overlay, narracao) — é modificada
    mats             dicionário de materiais do draft — é modificado
    proj             pasta do projeto no CapCut (recebe subdraft/ e Resources/combination/)
    meta             dicionário do draft_meta_info.json — recebe os clipes compostos (type 18)
    narr_fim_us      duração da narração SEM a propaganda (µs)
    t_propaganda_us  instante (µs) em que a narração para e a propaganda entra (pausa da fala, depois do gancho)
    retoma_us        instante (µs) do áudio original em que a fala retoma (None = igual a t_propaganda_us: não remove silêncio)
    final_antes_us   quanto antes do fim da narração a vinheta final começa
    devolve          (trilhas_novas_na_ordem, duracao_total_us)
    """
    papeis = pacote["papeis"]
    d_prop = _duracao(papeis["propaganda_video"])
    d_final = _duracao(papeis["final"])
    retoma_us = t_propaganda_us if retoma_us is None else retoma_us
    delta = d_prop - (
        retoma_us - t_propaganda_us
    )  # quanto a timeline cresce (propaganda menos o silêncio removido)
    nar_fim = narr_fim_us + delta  # narração termina depois de inserida a propaganda
    final_ini = nar_fim - final_antes_us
    total = max(nar_fim, final_ini + d_final)

    trilhas_base = [t for t in tracks if t.get("name") in ("preenchimento", "clipes", "overlay", "narracao")]
    _deslocar(trilhas_base, mats, t_propaganda_us, retoma_us, d_prop)
    por_nome = {t["name"]: t for t in tracks}

    # preenchimento e B-roll vão até o fim do vídeo (a vinheta final fica POR CIMA do B-roll)
    pre = por_nome["preenchimento"]["segments"][-1]
    falta = total - (pre["target_timerange"]["start"] + pre["target_timerange"]["duration"])
    if falta > 0:
        pre["target_timerange"]["duration"] += falta
        pre["source_timerange"]["duration"] += falta
    clipes = por_nome["clipes"]
    if estender_broll and clipes["segments"]:
        ult = max(clipes["segments"], key=lambda s: s["target_timerange"]["start"])
        fim_ult = ult["target_timerange"]["start"] + ult["target_timerange"]["duration"]
        if (
            fim_ult < total and total - fim_ult < 6_000_000
        ):  # só fecha vão pequeno no final; vão grande é decisão de edição
            extra = total - fim_ult
            ult["target_timerange"]["duration"] += extra
            ult["source_timerange"]["duration"] += int(round(extra * (ult.get("speed") or 1.0)))

    # propaganda: vídeo na trilha de clipes + áudio na trilha da narração (loudness já vem nos extras do áudio)
    video_prop = _clonar(papeis["propaganda_video"], mats, t_propaganda_us, d_prop)
    audio_prop = _clonar(papeis["propaganda_audio"], mats, t_propaganda_us, d_prop)
    clipes["segments"].append(video_prop)
    clipes["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    por_nome["narracao"]["segments"].append(audio_prop)
    por_nome["narracao"]["segments"].sort(key=lambda s: s["target_timerange"]["start"])

    modelo_video = next(t for t in tracks if t["type"] == "video")
    modelo_audio = next(t for t in tracks if t["type"] == "audio")

    # avatar no canto: antes da propaganda e depois dela, até a vinheta final
    avatar_a = _clonar(papeis["avatar_inicio"], mats, 0, t_propaganda_us)
    src_continua = papeis["avatar_continua"]["segmento"]["source_timerange"]["start"]
    avatar_b = _clonar(
        papeis["avatar_continua"],
        mats,
        t_propaganda_us + d_prop,
        final_ini - (t_propaganda_us + d_prop),
        src_continua,
    )
    # vinheta final por cima do B-roll, sem avatar
    final = _clonar(papeis["final"], mats, final_ini, d_final)
    # música do início ao fim (repete a faixa se o vídeo for mais longo que ela)
    d_musica = _duracao(papeis["musica"])
    volume = papeis["musica"]["segmento"].get("volume", 1.0)
    musica_segs, cursor = [], 0
    loudness = next(
        (m for g, m in papeis["propaganda_audio"]["extras"] if g == "loudnesses"), None
    )  # volume normalizado
    while cursor < total:
        pedaco = min(d_musica, total - cursor)
        seg_musica = _clonar(papeis["musica"], mats, cursor, pedaco, 0, volume)
        if loudness is not None and not any(g == "loudnesses" for g, _ in papeis["musica"]["extras"]):
            normalizacao = deepcopy(loudness)
            normalizacao["id"] = novo_id()
            mats.setdefault("loudnesses", []).append(normalizacao)
            seg_musica["extra_material_refs"].append(normalizacao["id"])
        musica_segs.append(seg_musica)
        cursor += pedaco

    for indice, seg in enumerate([avatar_a, avatar_b], start=3):
        seg["render_index"] = seg["track_render_index"] = indice
    final["render_index"] = final["track_render_index"] = 4
    trilha_avatar = _trilha(modelo_video, "avatar", [avatar_a, avatar_b])
    trilha_final = _trilha(modelo_video, "final", [final])
    trilha_musica = _trilha(modelo_audio, "musica", musica_segs)

    ordem = []
    for t in tracks:
        if t.get("name") == "narracao":
            ordem += [trilha_avatar, trilha_final]
        ordem.append(t)
    ordem.append(trilha_musica)

    # clipes compostos: pastas subdraft/, áudios em Resources/combination/ e entradas da lista de mídia do CapCut
    for sub in (pacote["pasta"] / "subdraft").glob("*"):
        shutil.copytree(sub, proj / "subdraft" / sub.name, dirs_exist_ok=True)
    (proj / "Resources" / "combination").mkdir(parents=True, exist_ok=True)
    for arq in (pacote["pasta"] / "Resources" / "combination").glob("*"):
        shutil.copy2(arq, proj / "Resources" / "combination" / arq.name)
    grupo18 = next((g for g in meta["draft_materials"] if g.get("type") == 18), None)
    if grupo18 is not None:
        for entrada in pacote.get("meta18", []):
            nova = deepcopy(entrada)
            nova["id"] = novo_id()
            grupo18["value"].append(nova)
    return ordem, total
