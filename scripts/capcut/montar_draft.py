#!/usr/bin/env python3
"""Monta um projeto NOVO no CapCut (Mac) a partir de um spec JSON: voz + B-roll (velocidade por segmento, com buracos)
+ overlay .mov com alpha numa 2ª trilha de vídeo por cima. Baseado no gerador do VideoGen (teste2/services/capcut-draft/cli.py):
clona um draft que abre no CapCut (aqui: scripts/capcut/template_draft, cópia mínima do VideoGen-UNIX-Sovietico) e reescreve draft_info.json.

Uso:  python3 montar_draft.py spec.json [--sem-backup] [--forcar]
spec.json:
{ "nome": "Título do vídeo", "voz": "/abs/pronto.wav", "overlay": "/abs/animacao/output/project.mov" | null,
  "capa_frame": "/abs/frame.png" | null (senão extrai da voz/overlay), "preenchimento": "/abs/outro_fundo.mp4" (opcional),
  "clipes": [ {"arquivo": "/abs/Assets/x.mp4", "in": 12.0, "out": 30.0,      # trecho da FONTE (s)
               "velocidade": 2.0,                                           # 1.0 | 1.5 | 2.0 (aplicada no CapCut)
               "t_inicio": 85.4,                                            # posição na timeline (s); buracos permitidos
               "item": "Rust"} ] }
Ordem das trilhas (de baixo p/ cima): 1) "preenchimento" = vídeo de preenchimento (spec "preenchimento", padrão ../../assets/fundo_preenchimento.mp4)
contínuo cobrindo 100% da narração (cópias em sequência, última recortada, 1x, mudo) — NUNCA tem buraco (o CapCut não aceita vazio na 1ª trilha);
2) "clipes" = os trechos de B-roll nas posições exatas, 1.5x/2x, mudos, COM buracos (onde aparece o preenchimento de baixo; é onde o usuário coloca vídeo na mão);
3) "overlay" = .mov alpha; 4) "narracao". Opcional no spec: "janelas" e "menu_duracao" (de plano.json) só para o resumo por item.
Formato (descoberto no VideoGen e confirmado aqui): IDs = UUID MAIÚSCULO; tempos em microssegundos; mídia copiada para <draft>/media e
referenciada por `##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/media/<arq>`; speed no segmento + material `speeds`;
source_timerange.duration = (out-in); target_timerange.duration = (out-in)/velocidade."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marca  # pacote de marca: música, avatar, propaganda, vinheta final

AQUI = Path(__file__).resolve().parent
TEMPLATE = AQUI / "template_draft"
DRAFTS = Path(
    os.environ.get("CAPCUT_DRAFTS_DIR")
    or (Path.home() / "Movies/CapCut/User Data/Projects/com.lveditor.draft")
)  # CAPCUT_DRAFTS_DIR + CAPCUT_TESTE=1: teste em pasta temporária (symlink em vez de cópia)
PH = "##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##"
CANVAS_W, CANVAS_H = 1920, 1080
BASE_NAMES = ("VideoGen-macos-FIX", "VideoGen-UNIX-Sovietico", "VideoGen-unix-sovietico")

uid = lambda: str(uuid.uuid4()).upper()
us = lambda s: int(round(float(s) * 1_000_000))
now = lambda: int(time.time() * 1_000_000)

FPS = 30


def qf(t):  # segundos -> frames inteiros
    return int(round(float(t) * FPS))


def usf(n):  # frames -> microssegundos
    return int(round(n * 1_000_000 / FPS))


FILLER_PADRAO = AQUI.parent.parent / "assets" / "fundo_preenchimento.mp4"  # 20 s (fallback: várias cópias)
FILLER_LONGO = (
    AQUI.parent.parent / "assets" / "fundo_preenchimento_20min.mp4"
)  # 20 min (padrão: 1 segmento aparado)


def categorias(spec, total_s):
    """Intervalos nomeados [(t0, t1, nome, item_idx|None)] cobrindo 0..total_s, p/ nomear os preenchimentos."""
    jan = spec.get("janelas") or {}
    menu = float(spec.get("menu_duracao", 3.7))
    cats = []
    ordem = sorted(jan.items(), key=lambda kv: kv[1][0])
    n_item = 0
    itens = [k for k, v in ordem if v[2] == "item"]
    pos = 0.0
    for k, (a, b, tipo) in ordem:
        if a > pos + 1e-6:
            cats.append((pos, a, "PREENCHER_intro" if not cats else f"PREENCHER_entre", None))
        if tipo == "item":
            n_item += 1
            cats.append((a, min(a + menu, b), f"PREENCHER_troca_{n_item:02d}", n_item))
            cats.append((min(a + menu, b), b, f"PREENCHER_item_{n_item:02d}", n_item))
        else:
            nome = "PREENCHER_intro" if not cats else f"PREENCHER_{k}"
            cats.append((a, b, nome, None))
        pos = b
    if total_s > pos + 1e-6:
        cats.append((pos, total_s, "PREENCHER_fim", None))
    if cats and not any(c[2] == "PREENCHER_intro" for c in cats):
        cats[0] = (cats[0][0], cats[0][1], "PREENCHER_intro", cats[0][3])
    if not cats:
        cats = [(0.0, total_s, "PREENCHER_intro", None)]
    if cats[-1][2] != "PREENCHER_fim" and not jan:
        cats[-1] = (cats[-1][0], cats[-1][1], "PREENCHER_fim", None)
    return cats, itens


def probe(p):
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(p),
        ],
        capture_output=True,
        text=True,
    )
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    return (
        float((d.get("format") or {}).get("duration") or 0),
        int(st.get("width") or CANVAS_W),
        int(st.get("height") or CANVAS_H),
    )


def audio_dur(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True,
        text=True,
    )
    return float(r.stdout.strip() or 0)


def mat_by_id(materials, mid):
    for key, items in materials.items():
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and it.get("id") == mid:
                    return key, it
    return None, None


def clone_extras(refs, old_mats, out, velocidade=None):
    novos = []
    for rid in refs or []:
        key, it = mat_by_id(old_mats, rid)
        if it is None:
            continue
        n = deepcopy(it)
        nid = uid()
        n["id"] = nid
        if key == "speeds" and velocidade is not None:
            n["speed"] = float(velocidade)  # mesmo valor do segmento (obrigatório)
        out.setdefault(key, []).append(n)
        novos.append(nid)
    return novos


def copiar(src, dst):
    """Copia a mídia ORIGINAL (sem recodificar/proxy): clonefile no APFS, senão cópia normal; confere o tamanho."""
    _copiar(src, dst)
    assert dst.stat().st_size == Path(src).stat().st_size, f"cópia incompleta: {src}"


def _copiar(src, dst):
    if dst.exists():
        return
    if os.environ.get("CAPCUT_TESTE") == "1":
        os.symlink(os.path.abspath(src), dst)
        return
    if (
        subprocess.run(["cp", "-c", str(src), str(dst)], capture_output=True).returncode != 0
    ):  # clonefile (APFS), senão cópia normal
        shutil.copy2(src, dst)


def escala_cobrir(w, h):
    """Escala do CapCut p/ preencher 16:9 sem barras. Convenção: scale 1.0 = material 'contido' (fit) na tela; cobrir = razão entre os dois ajustes."""
    contain = min(CANVAS_W / w, CANVAS_H / h)
    cover = max(CANVAS_W / w, CANVAS_H / h)
    return round(cover / contain, 4)


def capa(spec, voz_dur, dest, tmp):
    f = spec.get("capa_frame")
    if not f:
        ov = spec.get("overlay")
        fonte = spec["clipes"][0]["arquivo"] if spec.get("clipes") else ov
        t = spec["clipes"][0]["in"] + 1 if spec.get("clipes") else 1
        f = str(tmp / "capa_src.png")
        subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", fonte, "-frames:v", "1", f], capture_output=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            f,
            "-vf",
            "scale=640:360:force_original_aspect_ratio=increase,crop=640:360",
            "-frames:v",
            "1",
            str(dest),
        ],
        capture_output=True,
    )
    if not dest.exists():
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=640x360:d=0.1",
                "-frames:v",
                "1",
                str(dest),
            ],
            capture_output=True,
        )


def montar(spec, backup=True, forcar=False):
    capcut_aberto = subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0
    if capcut_aberto and not forcar:
        sys.exit("O CapCut está aberto (ele reescreve drafts abertos). Feche-o ou use --forcar.")
    nome = spec["nome"]
    voz = Path(spec["voz"])
    overlay = Path(spec["overlay"]) if spec.get("overlay") else None
    assert voz.exists(), f"voz não encontrada: {voz}"
    proj = DRAFTS / nome
    if proj.exists():
        if backup:
            bk = DRAFTS / f".backup_{nome}_{time.strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(proj), str(bk))
            print(f"[capcut] backup do draft anterior: {bk}")
        else:
            shutil.rmtree(proj)
    shutil.copytree(TEMPLATE, proj)
    media = proj / "media"
    media.mkdir(exist_ok=True)
    tmp = Path("/tmp") / f"capcut_{uuid.uuid4().hex[:6]}"
    tmp.mkdir()

    old = json.loads((proj / "draft_info.json").read_text())
    old_tid = old["id"]
    new_tid = uid()
    ct = now()
    v_tracks = [t for t in old["tracks"] if t["type"] == "video"]
    a_track = next(t for t in old["tracks"] if t["type"] == "audio")
    vseg_t = deepcopy(v_tracks[0]["segments"][0])
    oseg_t = deepcopy(v_tracks[1]["segments"][0])
    aseg_t = deepcopy(a_track["segments"][0])
    vmat_t = next(v for v in old["materials"]["videos"] if v["id"] == vseg_t["material_id"])
    omat_t = next(v for v in old["materials"]["videos"] if v["id"] == oseg_t["material_id"])
    amat_t = next(a for a in old["materials"]["audios"] if a["id"] == aseg_t["material_id"])
    old_mats = old["materials"]
    mats = deepcopy(old_mats)
    for k, v in list(mats.items()):
        if isinstance(v, list):
            mats[k] = []

    # ---- B-roll + PREENCHIMENTO (trilha principal contínua, sem buracos) ----
    vd = us(audio_dur(voz))
    total_f = int(vd * FPS // 1_000_000)  # voz inteira em frames
    # preenchimento: padrão = arquivo longo de 20 min (UM segmento aparado pela borda até a duração da narração; o arquivo inteiro fica no material,
    # então dá para puxar a borda no CapCut). Fallback: arquivo de 20 s em cópias sequenciais. Trocável via spec["preenchimento"].
    filler_p = Path(spec.get("preenchimento") or (FILLER_LONGO if FILLER_LONGO.exists() else FILLER_PADRAO))
    assert filler_p.exists(), f"vídeo de preenchimento não encontrado: {filler_p}"
    f_dur, fw, fh = probe(filler_p)
    f_frames = max(
        1, qf(f_dur) - (0 if f_dur > 120 else 1)
    )  # longo: usa todos os frames; curto: evita o último
    copiar(filler_p, media / filler_p.name)

    def novo_video_seg(src_path, dest_name, d_arq, w, h, i0_us, src_dur_us, t0_us, tl_dur_us, vel, nome_mat):
        mat = deepcopy(vmat_t)
        mid = uid()
        mat.update(
            {
                "id": mid,
                "duration": us(d_arq),
                "path": f"{PH}/media/{dest_name}",
                "material_name": nome_mat,
                "width": w,
                "height": h,
                "has_audio": False,
                "type": "video",
            }
        )
        mats["videos"].append(mat)
        refs = clone_extras(vseg_t.get("extra_material_refs"), old_mats, mats, velocidade=vel)
        seg = deepcopy(vseg_t)
        seg["clip"] = deepcopy(seg.get("clip") or {})
        e = escala_cobrir(w, h)
        seg["clip"]["scale"] = {"x": e, "y": e}
        seg.update(
            {
                "id": uid(),
                "material_id": mid,
                "extra_material_refs": refs,
                "source_timerange": {"start": i0_us, "duration": src_dur_us},
                "target_timerange": {"start": t0_us, "duration": tl_dur_us},
                "render_timerange": {"start": 0, "duration": 0},
                "volume": 0.0,
                "speed": vel,
                "render_index": 0,
                "track_render_index": 0,
            }
        )
        return seg

    reais = []  # (f0, f1, seg, resumo)
    for c in sorted(spec.get("clipes", []), key=lambda c: c["t_inicio"]):
        src = Path(c["arquivo"])
        assert src.exists(), src
        copiar(src, media / src.name)
        d_arq, w, h = probe(src)
        vel = float(c.get("velocidade", 1.0))
        i0, i1 = float(c["in"]), float(c["out"])
        assert 0 <= i0 < i1 <= d_arq + 0.05, f"trecho fora do arquivo: {src.name} {i0}-{i1} (dur {d_arq:.1f})"
        f0 = qf(c["t_inicio"])
        nf = max(1, qf((i1 - i0) / vel))
        f1 = min(f0 + nf, total_f)
        tl_us = usf(f1 - f0)
        src_us = int(round(tl_us * vel))
        seg = novo_video_seg(src, src.name, d_arq, w, h, us(i0), src_us, usf(f0), tl_us, vel, src.name)
        reais.append((f0, f1, seg, (c.get("item", ""), src.name, i0, i1, vel, f0 / FPS, (f1 - f0) / FPS)))
    reais.sort(key=lambda r: r[0])
    for a, b in zip(reais, reais[1:]):
        assert a[1] <= b[0], f"clipes sobrepostos na timeline: {a[3][1]} e {b[3][1]}"
    # lacunas -> preenchimento, quebrado por categoria (intro/troca/item/fim) para nomear
    cats, itens_ids = categorias(spec, total_f / FPS)
    cats_f = [(qf(a), qf(b), n, it) for a, b, n, it in cats]
    cats_f[-1] = (cats_f[-1][0], total_f, cats_f[-1][2], cats_f[-1][3])
    lacunas = []
    cur = 0
    for f0, f1, _, _ in reais:
        if f0 > cur:
            lacunas.append((cur, f0))
        cur = max(cur, f1)
    if cur < total_f:
        lacunas.append((cur, total_f))
    # estatística dos vazios (clipes) por item — quem fica sem clipe = vazio na trilha 2 (o usuário põe vídeo na mão)
    fill_por_item = {}
    fill_total = 0
    for a_, b_ in lacunas:
        for ca, cb, nm, it in cats_f:
            x, y = max(a_, ca), min(b_, cb)
            if y <= x:
                continue
            fill_total += y - x
            if it:
                fill_por_item[it] = fill_por_item.get(it, 0) + (y - x) / FPS
    # TRILHA 1 (base): preenchimento contínuo cobrindo 100% da narração, cópias em sequência, última recortada
    fill_segs = []
    fcur = 0
    while fcur < total_f:
        n = min(f_frames, total_f - fcur)
        fill_segs.append(
            (
                fcur,
                fcur + n,
                novo_video_seg(
                    filler_p, filler_p.name, f_dur, fw, fh, 0, usf(n), usf(fcur), usf(n), 1.0, "PREENCHIMENTO"
                ),
            )
        )
        fcur += n
    pos = 0
    for _, _, sg in fill_segs:
        sg["target_timerange"]["start"] = pos
        pos += sg["target_timerange"]["duration"]
    assert abs(pos - usf(total_f)) <= 2, "preenchimento não cobre a narração"
    # TRILHA 2: clipes nas posições exatas (quantizadas), com buracos
    segs = [r[2] for r in reais]
    resumo = [r[3] for r in reais]

    # ---- voz ----
    copiar(voz, media / "voz_narracao.wav")
    aud = deepcopy(amat_t)
    aid = uid()
    aud.update(
        {
            "id": aid,
            "duration": vd,
            "path": f"{PH}/media/voz_narracao.wav",
            "name": "voz_narracao.wav",
            "type": "extract_music",
        }
    )
    mats["audios"].append(aud)
    arefs = clone_extras(aseg_t.get("extra_material_refs"), old_mats, mats)
    aseg = deepcopy(aseg_t)
    aseg.update(
        {
            "id": uid(),
            "material_id": aid,
            "extra_material_refs": arefs,
            "source_timerange": {"start": 0, "duration": vd},
            "target_timerange": {"start": 0, "duration": vd},
            "volume": 1.0,
        }
    )

    # ---- overlay (2ª trilha de vídeo, por cima) ----
    tracks = [
        {
            **deepcopy(v_tracks[0]),
            "id": uid(),
            "name": "preenchimento",
            "segments": [x[2] for x in fill_segs],
        },
        {**deepcopy(v_tracks[0]), "id": uid(), "name": "clipes", "segments": segs},
    ]
    for i_t, t_ in enumerate(tracks):
        for sg in t_["segments"]:
            sg["track_render_index"] = i_t
            sg["render_index"] = i_t
    if overlay:
        d_ov, w, h = probe(overlay)
        copiar(overlay, media / overlay.name)
        mat = deepcopy(omat_t)
        mid = uid()
        mat.update(
            {
                "id": mid,
                "duration": us(d_ov),
                "path": f"{PH}/media/{overlay.name}",
                "material_name": overlay.name,
                "width": w,
                "height": h,
                "has_audio": False,
                "type": "video",
            }
        )
        mats["videos"].append(mat)
        # overlay RECORTADO nas janelas sem B-roll (spec["overlay_segmentos"], gerado por spec_do_plano.py); sem a chave: 1 segmento contínuo
        janelas_ov = spec.get("overlay_segmentos") or [[0, min(d_ov, vd / 1e6)]]
        ov_segs = []
        for s0, s1 in janelas_ov:
            f0, f1 = qf(s0), min(qf(s1), qf(d_ov), total_f)
            if f1 - f0 < 1:
                continue
            refs = clone_extras(oseg_t.get("extra_material_refs"), old_mats, mats, velocidade=1.0)
            seg = deepcopy(oseg_t)
            seg["clip"] = deepcopy(seg.get("clip") or {})
            seg["clip"]["scale"] = {"x": 1.0, "y": 1.0}
            seg.update(
                {
                    "id": uid(),
                    "material_id": mid,
                    "extra_material_refs": refs,
                    "source_timerange": {"start": usf(f0), "duration": usf(f1 - f0)},
                    "target_timerange": {"start": usf(f0), "duration": usf(f1 - f0)},
                    "render_timerange": {"start": 0, "duration": 0},
                    "volume": 0.0,
                    "speed": 1.0,
                    "track_render_index": 2,
                    "render_index": 2,
                }
            )
            ov_segs.append(seg)
        tracks.append({**deepcopy(v_tracks[1]), "id": uid(), "name": "overlay", "segments": ov_segs})
    tracks.append({**deepcopy(a_track), "id": uid(), "name": "narracao", "segments": [aseg]})

    # ---- marca (música, avatar, propaganda após o gancho, vinheta final) — só se o spec pedir e o pacote privado existir ----
    meta_path = proj / "draft_meta_info.json"
    meta = json.loads(meta_path.read_text())
    marca_spec = spec.get("marca")
    total_marca = None
    if marca_spec:
        pacote = marca.carregar(marca_spec.get("pacote") or marca.PACOTE_PADRAO)
        if pacote is None:
            print(
                "[capcut] AVISO: spec pede 'marca' mas o pacote privado não existe (rode extrair_pacote_marca.py); projeto sem marca"
            )
        else:
            tracks, total_marca = marca.aplicar(
                pacote,
                tracks,
                mats,
                proj,
                meta,
                vd,
                us(marca_spec["propaganda_t"]),
                us(marca_spec.get("propaganda_retoma", marca_spec["propaganda_t"])),
                us(marca_spec.get("final_antes_do_fim", 6.9)),
            )
            print(
                f"[capcut] marca aplicada: propaganda em {marca_spec['propaganda_t']:.1f}s (tudo depois desloca), "
                f"música + avatar + vinheta final; duração total {total_marca / 1e6:.1f}s"
            )

    total = total_marca or max(
        vd, max((s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in segs), default=0)
    )
    info = deepcopy(old)
    info.update(
        {
            "id": new_tid,
            "name": nome,
            "duration": total,
            "create_time": ct,
            "update_time": ct,
            "materials": mats,
            "tracks": tracks,
        }
    )
    payload = json.dumps(info, ensure_ascii=False, separators=(",", ":"))
    for n in ("draft_info.json", "draft_info.json.bak", "draft_content.json", "template-2.tmp"):
        (proj / n).write_text(payload)

    # ---- capa + timelines ----
    capa(spec, vd / 1e6, proj / "draft_cover.jpg", tmp)
    tl_root = proj / "Timelines"
    old_tl = tl_root / old_tid
    new_tl = tl_root / new_tid
    if old_tl.exists():
        old_tl.rename(new_tl)
    else:
        dirs = [d for d in tl_root.iterdir() if d.is_dir()]
        (dirs[0].rename(new_tl) if dirs else new_tl.mkdir(parents=True))
    for n in ("draft_info.json", "draft_info.json.bak", "template-2.tmp"):
        (new_tl / n).write_text(payload)
    shutil.copy2(proj / "draft_cover.jpg", new_tl / "draft_cover.jpg")
    pj_path = tl_root / "project.json"
    pj = json.loads(pj_path.read_text()) if pj_path.exists() else {}
    pj.update(
        {
            "create_time": ct,
            "id": uid(),
            "main_timeline_id": new_tid,
            "timelines": [
                {
                    "create_time": ct,
                    "id": new_tid,
                    "is_marked_delete": False,
                    "name": "Linha do tempo 01",
                    "update_time": ct,
                }
            ],
            "update_time": ct,
            "version": pj.get("version", 0),
        }
    )
    pj.setdefault(
        "config",
        {
            "color_space": -1,
            "mixed_track_mode_on": False,
            "render_index_track_mode_on": False,
            "use_float_render": False,
        },
    )
    pj_path.write_text(json.dumps(pj, ensure_ascii=False, separators=(",", ":")))
    (tl_root / "project.json.bak").write_text(pj_path.read_text())
    (proj / "timeline_layout.json").write_text(
        json.dumps(
            {
                "dockItems": [
                    {
                        "dockIndex": 0,
                        "ratio": 1,
                        "timelineIds": [new_tid],
                        "timelineNames": ["Linha do tempo 01"],
                    }
                ]
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    meta.update(
        {
            "draft_id": new_tid,
            "draft_name": nome,
            "draft_fold_path": str(proj),
            "draft_root_path": str(DRAFTS),
            "draft_cover": "draft_cover.jpg",
            "tm_draft_create": ct,
            "tm_draft_modified": ct,
            "tm_draft_removed": 0,
            "tm_duration": total,
        }
    )
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))

    # ---- root_meta_info (lista de projetos do CapCut) ----
    root_path = DRAFTS / "root_meta_info.json"
    if not root_path.exists() and os.environ.get("CAPCUT_TESTE") == "1":
        root_path.write_text(json.dumps({"all_draft_store": [], "draft_ids": []}))
    shutil.copy2(root_path, DRAFTS / f"root_meta_info.json.bak_{time.strftime('%Y%m%d_%H%M%S')}")
    root = json.loads(root_path.read_text())
    store = root.get("all_draft_store") or []
    store = [
        e
        for e in store
        if e.get("draft_name") != nome
        and not str(e.get("draft_fold_path", "")).rstrip("/").endswith("/" + nome)
    ]
    base = next(
        (deepcopy(e) for e in root.get("all_draft_store") or [] if e.get("draft_name") in BASE_NAMES), None
    ) or (deepcopy(store[0]) if store else {})
    msize = sum(f.stat().st_size for f in media.rglob("*") if f.is_file())
    base.update(
        {
            "draft_id": new_tid,
            "draft_name": nome,
            "draft_fold_path": str(proj),
            "draft_root_path": str(DRAFTS),
            "draft_json_file": str(proj / "draft_info.json"),
            "draft_cover": str(proj / "draft_cover.jpg"),
            "tm_draft_create": ct,
            "tm_draft_modified": ct,
            "tm_draft_removed": 0,
            "tm_duration": total,
            "draft_timeline_materials_size": msize,
            "draft_is_invisible": False,
            "streaming_edit_draft_ready": True,
        }
    )
    store.insert(0, base)
    root["all_draft_store"] = store
    if isinstance(root.get("draft_ids"), list):
        root["draft_ids"] = [new_tid] + [i for i in root["draft_ids"] if i != new_tid]
    root_path.write_text(json.dumps(root, ensure_ascii=False, separators=(",", ":")))
    shutil.rmtree(tmp, ignore_errors=True)

    print(
        f"[capcut] OK «{nome}» · {total/1e6:.1f}s · {len(reais)} clipes de B-roll (trilha 2, com buracos) + base de preenchimento contínua ({len(fill_segs)} segmento(s), {fill_total/FPS:.1f}s de vazios na trilha 2) · overlay: {'sim' if overlay else 'não'} · {proj}"
    )
    for it, f, a, b, v, t0, dd in resumo:
        print(f"   {t0:7.1f}s  {dd:5.1f}s  {v}x  {f} [{a:.1f}-{b:.1f}]  {it}")
    # tabela final: item | tem B-roll? | arquivos/trechos/velocidade | segundos de preenchimento
    tab = [
        "| item | tem B-roll? | arquivos / trechos / velocidade | vazio na trilha de clipes (s) |",
        "|---|---|---|---|",
    ]
    jan = spec.get("janelas") or {}
    ids_item = [k for k, v in sorted(jan.items(), key=lambda kv: kv[1][0]) if v[2] == "item"]
    por = {}
    for it, f, a, b, v, t0, dd in resumo:
        por.setdefault(it, []).append(f"{f} [{a:.1f}–{b:.1f}] {v}x")
    for n, k in enumerate(ids_item or sorted(por), 1):
        tab.append(
            f"| {n:02d} {k} | {'sim' if k in por else 'NÃO (vazio: colocar vídeo)'} | {'; '.join(por.get(k, [])) or '—'} | {fill_por_item.get(n, 0):.1f} |"
        )
    outros = fill_total / FPS - sum(fill_por_item.values())
    tab.append(f"| intro/seções/conclusão | — | — | {outros:.1f} |")
    print("\n".join(tab))
    (proj / "RESUMO_BROLL.md").write_text("\n".join(tab) + "\n")
    return proj


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--sem-backup", action="store_true")
    ap.add_argument("--forcar", action="store_true")
    a = ap.parse_args()
    montar(json.load(open(a.spec)), backup=not a.sem_backup, forcar=a.forcar)
