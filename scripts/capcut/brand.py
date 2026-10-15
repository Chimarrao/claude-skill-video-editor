"""Pacote de marca para os projetos do CapCut: música, avatar, propaganda e vinheta final.

São predefinições copiadas de um projeto de referência já editado à mão:

    1) extract (uma vez): python extract_brand_pack.py --ref <draft_com_marca> --ref-ending <draft_com_final>
       -> grava `private/brand_pack/` (pack.json + subdraft/ + Resources/combination/). Pasta privada, fora do git.
    2) apply (automático em build_draft.py quando o spec traz "brand"): insere a propaganda no tempo T,
       desloca o resto da timeline, estende música e preenchimento até o fim e coloca avatar/vinheta final.

Layout (de baixo para cima): filler · clips · overlay · avatar · final · narration (+ áudio da propaganda) · music.
Regras: avatar some na propaganda e na vinheta final; música cobre tudo; B-roll vai até o fim, com a vinheta por cima;
volume normalizado (loudness) na música e na propaganda.

Chaves do pack.json: roles (avatar_start, avatar_continues, promo_video, promo_audio, music, final), cada uma com
segment / main / extras, e meta18. Trilhas e pastas do CapCut são mantidas como estão.
"""

import json
import re
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

PH = "##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##"
SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PACK = SKILL_ROOT / "private" / "brand_pack"
# nomes das predefinições do editor (ele as chama "Minhas predefinições N"); troque por argumento se mudar
DEFAULT_NAMES = dict(
    avatar="predefinições6", promo="predefinições4", music="predefinições2", final="predefinições3"
)

new_id = lambda: str(uuid.uuid4()).upper()


def _index(draft):
    """Mapa id -> (lista, material) de todos os materiais do draft."""
    index = {}
    for items_list, items in draft["materials"].items():
        if isinstance(items, list):
            for material in items:
                if isinstance(material, dict) and "id" in material:
                    index[material["id"]] = (items_list, material)
    return index


def _material_name(material):
    return material.get("material_name") or material.get("name") or ""


def _segments_by_role(draft, name_fragment, type):
    """Segmentos (trilha, segmento, grupo, material) com `name_fragment` no nome, em ordem de tempo."""
    index = _index(draft)
    matches = []
    for track in draft["tracks"]:
        if track["type"] != type:
            continue
        for seg in track["segments"]:
            group, material = index.get(seg["material_id"], ("?", {}))
            if name_fragment in _material_name(material):
                matches.append((track, seg, group, material))
    matches.sort(key=lambda x: x[1]["target_timerange"]["start"])
    return matches


def _item(draft, seg, group, material):
    """Item serializável: segmento + material principal + extras (speed, combination, loudness...)."""
    index = _index(draft)
    extras = [(index[r][0], index[r][1]) for r in seg.get("extra_material_refs", []) if r in index]
    return dict(segment=seg, main=(group, material), extras=extras)


def extract(ref, ref_ending=None, names=None, output=DEFAULT_PACK):
    """Lê (só leitura) os drafts de referência e grava o pacote de marca em `output`."""
    names = {**DEFAULT_NAMES, **(names or {})}
    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    (output / "subdraft").mkdir(parents=True)
    (output / "Resources" / "combination").mkdir(parents=True)
    roles = {}
    sources = [(Path(ref), json.load(open(Path(ref) / "draft_info.json")))]
    if ref_ending:
        sources.append((Path(ref_ending), json.load(open(Path(ref_ending) / "draft_info.json"))))

    def find(name, type):
        for folder, draft in sources:
            matches = _segments_by_role(draft, name, type)
            if matches:
                return folder, draft, matches
        raise SystemExit(f"predefinição '{name}' ({type}) não encontrada nos drafts de referência")

    folder, draft, avatar_segs = find(names["avatar"], "video")
    roles["avatar_start"] = (folder, _item(draft, avatar_segs[0][1], avatar_segs[0][2], avatar_segs[0][3]))
    roles["avatar_continues"] = (folder, _item(draft, avatar_segs[-1][1], avatar_segs[-1][2], avatar_segs[-1][3]))
    folder, draft, promo_video_segs = find(names["promo"], "video")
    roles["promo_video"] = (
        folder,
        _item(draft, promo_video_segs[0][1], promo_video_segs[0][2], promo_video_segs[0][3]),
    )
    folder, draft, promo_audio_segs = find(names["promo"], "audio")
    roles["promo_audio"] = (
        folder,
        _item(draft, promo_audio_segs[0][1], promo_audio_segs[0][2], promo_audio_segs[0][3]),
    )
    folder, draft, music_segs = find(names["music"], "audio")
    roles["music"] = (folder, _item(draft, music_segs[0][1], music_segs[0][2], music_segs[0][3]))
    folder, draft, ending_segs = find(names["final"], "video")
    roles["final"] = (folder, _item(draft, ending_segs[0][1], ending_segs[0][2], ending_segs[0][3]))

    meta18, copied_folders = [], set()
    for role, (folder, item) in roles.items():
        text = json.dumps(item, ensure_ascii=False)
        for sub in set(re.findall(r"/subdraft/([0-9A-F-]{36})", text)):  # subdrafts dos clipes compostos
            if sub not in copied_folders and (folder / "subdraft" / sub).exists():
                shutil.copytree(folder / "subdraft" / sub, output / "subdraft" / sub)
                copied_folders.add(sub)
        for filename in set(re.findall(r"Resources/combination/([^\"/]+)", text)):  # áudios guardados no projeto
            source = folder / "Resources" / "combination" / filename
            if source.exists():
                shutil.copy2(source, output / "Resources" / "combination" / filename)
        meta = json.load(open(folder / "draft_meta_info.json"))
        for group in meta.get("draft_materials", []):
            if group.get("type") == 18:
                for entry in group["value"]:
                    if (
                        any(sub in entry.get("file_Path", "") for sub in copied_folders)
                        and entry not in meta18
                    ):
                        meta18.append(entry)
    json.dump(
        dict(roles={k: v[1] for k, v in roles.items()}, meta18=meta18),
        open(output / "pack.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    print(f"pacote de marca gravado em {output}: {sorted(roles)} · {len(copied_folders)} clipes compostos")
    return output


def load(folder=DEFAULT_PACK):
    """Carrega o pacote; devolve None se não existir (o projeto sai sem marca)."""
    folder = Path(folder)
    if not (folder / "pack.json").exists():
        return None
    data = json.load(open(folder / "pack.json"))
    data["folder"] = folder
    return data


def _clone(item, mats, start_us, duration_us, src_start_us=0, volume=None):
    """Cria segmento novo do item do pacote (IDs e materiais novos) e o devolve."""
    group, main = item["main"]
    new_main = deepcopy(main)
    new_main["id"] = new_id()
    mats.setdefault(group, []).append(new_main)
    refs = []
    for extra_group, extra in item["extras"]:
        extra_copy = deepcopy(extra)
        extra_copy["id"] = new_id()
        mats.setdefault(extra_group, []).append(extra_copy)
        refs.append(extra_copy["id"])
    seg = deepcopy(item["segment"])
    seg.update(
        id=new_id(),
        material_id=new_main["id"],
        extra_material_refs=refs,
        source_timerange={"start": src_start_us, "duration": duration_us},
        target_timerange={"start": start_us, "duration": duration_us},
    )
    if volume is not None:
        seg["volume"] = volume
    return seg


def _duration(item):
    return item["segment"]["target_timerange"]["duration"]


def _trim(seg, start_us, end_us, mats):
    """Pedaço do segmento no intervalo [start_us, end_us] (a fonte acompanha). Devolve None se vazio."""
    seg_start = seg["target_timerange"]["start"]
    seg_end = seg_start + seg["target_timerange"]["duration"]
    a, b = max(seg_start, start_us), min(seg_end, end_us)
    if b - a < 1000:
        return None
    trimmed = deepcopy(seg)
    speed = seg.get("speed") or 1.0
    trimmed["target_timerange"] = {"start": a, "duration": b - a}
    trimmed["source_timerange"] = {
        "start": seg["source_timerange"]["start"] + int(round((a - seg_start) * speed)),
        "duration": int(round((b - a) * speed)),
    }
    return trimmed


def _make_room(tracks, mats, stop_us, resume_us, promo_dur_us):
    """Abre espaço para a propaganda.

    stop_us       instante em que a narração PARA (na pausa após o gancho)
    resume_us     instante original em que ela RETOMA (antes da próxima frase) — o silêncio some
    promo_dur_us  duração da propaganda
    O que passa de `resume_us` desloca em (promo menos silêncio); o que cai no silêncio some;
    o que cruza a borda é cortado (a fonte continua de onde parou).
    """
    delta = promo_dur_us - (resume_us - stop_us)
    for track in tracks:
        if track.get("name") == "filler":  # contínuo: só estende
            last = track["segments"][-1]
            last["target_timerange"]["duration"] += delta
            last["source_timerange"]["duration"] += delta
            continue
        new_segs = []
        for seg in track["segments"]:
            before = _trim(seg, 0, stop_us, mats)
            after = _trim(seg, resume_us, 10**15, mats)
            if before is not None:
                new_segs.append(before)
            if after is not None:
                after["target_timerange"]["start"] += delta
                if (
                    before is not None
                ):  # metade nova de segmento partido precisa dos próprios extras
                    after["id"] = new_id()
                    after["extra_material_refs"] = _clone_extras(seg.get("extra_material_refs", []), mats)
                new_segs.append(after)
        track["segments"] = new_segs


def _clone_extras(refs, mats):
    """Duplica os extras (speeds, canvas...) para a metade nova de um segmento cortado."""
    index = _index({"materials": mats})
    cloned = []
    for r in refs:
        if r in index:
            items_list, mat = index[r]
            copy = deepcopy(mat)
            copy["id"] = new_id()
            mats[items_list].append(copy)
            cloned.append(copy["id"])
    return cloned


def _make_track(template, name, segments):
    """Trilha nova com o formato de uma trilha-modelo do template."""
    track = deepcopy(template)
    track.update(id=new_id(), name=name, segments=segments)
    return track


def apply(
    pack,
    tracks,
    mats,
    project,
    meta,
    narr_end_us,
    promo_time_us,
    resume_us=None,
    ending_before_end_us=6_900_000,
    extend_broll=True,
):
    """Injeta a marca no projeto em montagem.

    pack                 dado de `load()`
    tracks               trilhas já montadas (preenchimento, clipes, overlay, narracao) — é modificada
    mats                 materiais do draft — é modificado
    project              pasta do projeto no CapCut (recebe subdraft/ e Resources/combination/)
    meta                 draft_meta_info.json — recebe os clipes compostos (type 18)
    narr_end_us          duração da narração SEM a propaganda (µs)
    promo_time_us        instante (µs) em que a narração para e a propaganda entra (pausa após o gancho)
    resume_us            instante (µs) original em que a fala retoma (None = igual a promo: sem remover silêncio)
    ending_before_end_us quanto antes do fim a vinheta final começa
    devolve              (trilhas_novas_na_ordem, duracao_total_us)
    """
    roles = pack["roles"]
    promo_dur = _duration(roles["promo_video"])
    ending_dur = _duration(roles["final"])
    resume_us = promo_time_us if resume_us is None else resume_us
    delta = promo_dur - (
        resume_us - promo_time_us
    )  # quanto a timeline cresce (propaganda menos o silêncio removido)
    narr_end = narr_end_us + delta  # narração termina após inserir a propaganda
    ending_start = narr_end - ending_before_end_us
    total = max(narr_end, ending_start + ending_dur)

    base_tracks = [t for t in tracks if t.get("name") in ("filler", "clips", "overlay", "narration")]
    _make_room(base_tracks, mats, promo_time_us, resume_us, promo_dur)
    by_name = {t["name"]: t for t in tracks}

    # preenchimento e B-roll vão até o fim (a vinheta final fica POR CIMA do B-roll)
    filler_last = by_name["filler"]["segments"][-1]
    missing = total - (filler_last["target_timerange"]["start"] + filler_last["target_timerange"]["duration"])
    if missing > 0:
        filler_last["target_timerange"]["duration"] += missing
        filler_last["source_timerange"]["duration"] += missing
    clips_track = by_name["clips"]
    if extend_broll and clips_track["segments"]:
        last_seg = max(clips_track["segments"], key=lambda s: s["target_timerange"]["start"])
        last_end = last_seg["target_timerange"]["start"] + last_seg["target_timerange"]["duration"]
        if (
            last_end < total and total - last_end < 6_000_000
        ):  # só fecha vão pequeno no fim; vão grande é decisão de edição
            extra = total - last_end
            last_seg["target_timerange"]["duration"] += extra
            last_seg["source_timerange"]["duration"] += int(round(extra * (last_seg.get("speed") or 1.0)))

    # propaganda: vídeo na trilha de clipes + áudio na da narração (loudness vem nos extras do áudio)
    promo_video = _clone(roles["promo_video"], mats, promo_time_us, promo_dur)
    promo_audio = _clone(roles["promo_audio"], mats, promo_time_us, promo_dur)
    clips_track["segments"].append(promo_video)
    clips_track["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    by_name["narration"]["segments"].append(promo_audio)
    by_name["narration"]["segments"].sort(key=lambda s: s["target_timerange"]["start"])

    video_template = next(t for t in tracks if t["type"] == "video")
    audio_template = next(t for t in tracks if t["type"] == "audio")

    # avatar no canto: antes da propaganda e depois dela, até a vinheta final
    avatar_first = _clone(roles["avatar_start"], mats, 0, promo_time_us)
    cont_src_start = roles["avatar_continues"]["segment"]["source_timerange"]["start"]
    avatar_rest = _clone(
        roles["avatar_continues"],
        mats,
        promo_time_us + promo_dur,
        ending_start - (promo_time_us + promo_dur),
        cont_src_start,
    )
    # vinheta final por cima do B-roll, sem avatar
    ending = _clone(roles["final"], mats, ending_start, ending_dur)
    # música do início ao fim (repete a faixa se o vídeo for mais longo que ela)
    music_dur = _duration(roles["music"])
    volume = roles["music"]["segment"].get("volume", 1.0)
    music_segs, cursor = [], 0
    loudness = next(
        (m for g, m in roles["promo_audio"]["extras"] if g == "loudnesses"), None
    )  # volume normalizado
    while cursor < total:
        chunk = min(music_dur, total - cursor)
        music_seg = _clone(roles["music"], mats, cursor, chunk, 0, volume)
        if loudness is not None and not any(g == "loudnesses" for g, _ in roles["music"]["extras"]):
            normalization = deepcopy(loudness)
            normalization["id"] = new_id()
            mats.setdefault("loudnesses", []).append(normalization)
            music_seg["extra_material_refs"].append(normalization["id"])
        music_segs.append(music_seg)
        cursor += chunk

    for index, seg in enumerate([avatar_first, avatar_rest], start=3):
        seg["render_index"] = seg["track_render_index"] = index
    ending["render_index"] = ending["track_render_index"] = 4
    avatar_track = _make_track(video_template, "avatar", [avatar_first, avatar_rest])
    ending_track = _make_track(video_template, "final", [ending])
    music_track = _make_track(audio_template, "music", music_segs)

    order = []
    for t in tracks:
        if t.get("name") == "narration":
            order += [avatar_track, ending_track]
        order.append(t)
    order.append(music_track)

    # clipes compostos: pastas subdraft/, áudios em Resources/combination/ e entradas da lista de mídia
    for sub in (pack["folder"] / "subdraft").glob("*"):
        shutil.copytree(sub, project / "subdraft" / sub.name, dirs_exist_ok=True)
    (project / "Resources" / "combination").mkdir(parents=True, exist_ok=True)
    for filename in (pack["folder"] / "Resources" / "combination").glob("*"):
        shutil.copy2(filename, project / "Resources" / "combination" / filename.name)
    group18 = next((g for g in meta["draft_materials"] if g.get("type") == 18), None)
    if group18 is not None:
        for entry in pack.get("meta18", []):
            new_entry = deepcopy(entry)
            new_entry["id"] = new_id()
            group18["value"].append(new_entry)
    return order, total
