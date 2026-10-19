#!/usr/bin/env python3
"""NEWS · PASSO 4a — projeto NOVO no CapCut (Mac) só com cortes: UMA trilha de vídeo com os trechos do `-limpo.mov` (áudio embutido no próprio vídeo,
SEM trilha de áudio separada), velocidade 1.0, canvas 1920x1080, 60 fps. Sem zoom, transição, música, texto ou marca.
Uso: python build_news_draft.py <fundido.mov> <cuts.json> "News NN - tema" [--force]
Clona o `template_draft` da skill (o mesmo do build_draft.py) e reescreve draft_info.json. NUNCA sobrescreve um projeto existente (sai com código 4).
Cortes com precisão de quadro a 60 fps; a mídia é clonada (clonefile do APFS) para <draft>/media."""

import argparse, json, os, shutil, subprocess, sys, time, uuid
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "capcut"))
import build_draft as bd  # noqa: E402  (constantes e helpers do gerador de drafts da skill)

FPS = 60
f2us = lambda n: int(round(n * 1_000_000 / FPS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fundido")
    ap.add_argument("cuts")
    ap.add_argument("nome")
    ap.add_argument("--force", action="store_true", help="roda mesmo com o CapCut aberto (ele reescreve drafts abertos: feche e reabra)")
    args = ap.parse_args()
    if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0 and not args.force:
        sys.exit("O CapCut está aberto (ele reescreve drafts abertos). Feche-o ou use --force.")
    media = Path(args.fundido).resolve()
    kept = json.load(open(args.cuts))["kept"]
    name = args.nome
    project = bd.DRAFTS / name
    if project.exists():
        print(f"JÁ EXISTE um projeto «{name}» — não sobrescrevo. Apague/renomeie na mão ou escolha outro nome.")
        sys.exit(4)
    shutil.copytree(bd.TEMPLATE, project)
    media_dir = project / "media"
    media_dir.mkdir(exist_ok=True)
    bd.copy_media(media, media_dir / media.name)
    dur, w, h = bd.probe(media)
    tmp = Path("/tmp") / f"capcut_news_{uuid.uuid4().hex[:6]}"
    tmp.mkdir()

    old = json.loads((project / "draft_info.json").read_text())
    old_id, new_id, now_us = old["id"], bd.uid(), bd.now()
    v_tracks = [t for t in old["tracks"] if t["type"] == "video"]
    vseg_t = deepcopy(v_tracks[0]["segments"][0])
    vmat_t = next(v for v in old["materials"]["videos"] if v["id"] == vseg_t["material_id"])
    old_mats = old["materials"]
    mats = deepcopy(old_mats)
    for k, v in list(mats.items()):
        if isinstance(v, list):
            mats[k] = []
    segs, tl = [], 0
    for a, b in kept:
        f0, f1 = round(a * FPS), round(b * FPS)
        if f1 <= f0:
            continue
        mat = deepcopy(vmat_t)
        mid = bd.uid()
        mat.update({"id": mid, "duration": bd.us(dur), "path": f"{bd.PH}/media/{media.name}", "material_name": media.name, "width": w, "height": h, "has_audio": True, "type": "video"})
        mats["videos"].append(mat)
        refs = bd.clone_extras(vseg_t.get("extra_material_refs"), old_mats, mats, speed=1.0)
        seg = deepcopy(vseg_t)
        seg["clip"] = deepcopy(seg.get("clip") or {})
        e = bd.cover_scale(w, h)
        seg["clip"]["scale"] = {"x": e, "y": e}
        seg.update(
            {
                "id": bd.uid(),
                "material_id": mid,
                "extra_material_refs": refs,
                "source_timerange": {"start": f2us(f0), "duration": f2us(f1 - f0)},
                "target_timerange": {"start": f2us(tl), "duration": f2us(f1 - f0)},
                "render_timerange": {"start": 0, "duration": 0},
                "volume": 1.0,
                "speed": 1.0,
                "render_index": 0,
                "track_render_index": 0,
            }
        )
        segs.append(seg)
        tl += f1 - f0
    total = f2us(tl)
    track = {**deepcopy(v_tracks[0]), "id": bd.uid(), "name": "", "segments": segs}  # a ÚNICA trilha (sem áudio separado)
    info = deepcopy(old)
    info.update({"id": new_id, "name": name, "duration": total, "create_time": now_us, "update_time": now_us, "materials": mats, "tracks": [track], "fps": float(FPS)})
    info.setdefault("canvas_config", {}).update({"width": bd.CANVAS_W, "height": bd.CANVAS_H, "ratio": "original"})
    payload = json.dumps(info, ensure_ascii=False, separators=(",", ":"))
    for n in ("draft_info.json", "draft_info.json.bak", "draft_content.json", "template-2.tmp"):
        (project / n).write_text(payload)

    # capa: quadro do 1º trecho
    cover = project / "draft_cover.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{kept[0][0] + 1.0:.2f}", "-i", str(media), "-frames:v", "1", "-vf", "scale=1920:1080", str(cover)], check=True)
    tl_root = project / "Timelines"
    old_tl, new_tl = tl_root / old_id, tl_root / new_id
    if old_tl.exists():
        old_tl.rename(new_tl)
    else:
        dirs = [d for d in tl_root.iterdir() if d.is_dir()]
        (dirs[0].rename(new_tl) if dirs else new_tl.mkdir(parents=True))
    for n in ("draft_info.json", "draft_info.json.bak", "template-2.tmp"):
        (new_tl / n).write_text(payload)
    shutil.copy2(cover, new_tl / "draft_cover.jpg")
    pj_path = tl_root / "project.json"
    pj = json.loads(pj_path.read_text()) if pj_path.exists() else {}
    pj.update({"create_time": now_us, "id": bd.uid(), "main_timeline_id": new_id, "timelines": [{"create_time": now_us, "id": new_id, "is_marked_delete": False, "name": "Linha do tempo 01", "update_time": now_us}], "update_time": now_us, "version": pj.get("version", 0)})
    pj.setdefault("config", {"color_space": -1, "mixed_track_mode_on": False, "render_index_track_mode_on": False, "use_float_render": False})
    pj_path.write_text(json.dumps(pj, ensure_ascii=False, separators=(",", ":")))
    (tl_root / "project.json.bak").write_text(pj_path.read_text())
    (project / "timeline_layout.json").write_text(json.dumps({"dockItems": [{"dockIndex": 0, "ratio": 1, "timelineIds": [new_id], "timelineNames": ["Linha do tempo 01"]}]}, ensure_ascii=False, separators=(",", ":")))
    meta_path = project / "draft_meta_info.json"
    meta = json.loads(meta_path.read_text())
    meta.update({"draft_id": new_id, "draft_name": name, "draft_fold_path": str(project), "draft_root_path": str(bd.DRAFTS), "draft_cover": "draft_cover.jpg", "tm_draft_create": now_us, "tm_draft_modified": now_us, "tm_draft_removed": 0, "tm_duration": total})
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))

    # lista de projetos do CapCut (root_meta_info.json), com cópia de segurança
    root_path = bd.DRAFTS / "root_meta_info.json"
    if not root_path.exists() and os.environ.get("CAPCUT_TEST") == "1":
        root_path.write_text(json.dumps({"all_draft_store": [], "draft_ids": []}))
    shutil.copy2(root_path, bd.DRAFTS / f"root_meta_info.json.bak_{time.strftime('%Y%m%d_%H%M%S')}")
    root = json.loads(root_path.read_text())
    store = [e for e in (root.get("all_draft_store") or []) if e.get("draft_name") != name]
    base = next((deepcopy(e) for e in root.get("all_draft_store") or [] if e.get("draft_name") in bd.BASE_NAMES), None) or (deepcopy(store[0]) if store else {})
    msize = sum(f.stat().st_size for f in media_dir.rglob("*") if f.is_file())
    base.update({"draft_id": new_id, "draft_name": name, "draft_fold_path": str(project), "draft_root_path": str(bd.DRAFTS), "draft_json_file": str(project / "draft_info.json"), "draft_cover": str(cover), "tm_draft_create": now_us, "tm_draft_modified": now_us, "tm_draft_removed": 0, "tm_duration": total, "draft_timeline_materials_size": msize, "draft_is_invisible": False, "streaming_edit_draft_ready": True})
    store.insert(0, base)
    root["all_draft_store"] = store
    if isinstance(root.get("draft_ids"), list):
        root["draft_ids"] = [new_id] + [i for i in root["draft_ids"] if i != new_id]
    root_path.write_text(json.dumps(root, ensure_ascii=False, separators=(",", ":")))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"[capcut] OK «{name}» · {total / 1e6:.1f}s · {len(segs)} trechos em UMA trilha · {FPS} fps · {project}")


if __name__ == "__main__":
    main()
