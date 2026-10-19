#!/usr/bin/env python3
"""NEWS — orquestrador do tipo "só cortes". O usuário diz "faça o news NN"; pasta `Tecnologia/News/NN - <tema>/`.

  python news.py prepare NN   → passo 1 (funde o áudio tratado) + features + passo 2 (transcrição large-v3 + alinhamento; ~2-4× a duração)
  python news.py cut NN       → passo 3 (editor automático) + cortes.md; depois O AGENTE REVISA (ver SKILL.md → "Revisão do agente") e, se mudar algo, grava work/edits.json e roda `cut` de novo
  python news.py deliver NN   → passo 4: prévia PRONTO_auto.mp4 + projeto no CapCut «News NN - <tema>» + validação (inclui transcrição da prévia)
Se `prepare` sair com código 3 (mais de um vídeo/áudio candidato), PERGUNTE ao usuário qual usar e rode de novo com --video/--wav."""

import argparse, glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.environ.get("NEWS_ROOT") or os.path.abspath(os.path.join(SK, "..", "..", "..", "News"))
PY = sys.executable
sys.path.insert(0, HERE)
from news_lib import achar_candidatos


def pasta_ep(nn):
    """Pasta `NN - <tema>` do episódio."""
    c = sorted(glob.glob(os.path.join(ROOT, f"{int(nn):02d} - *")))
    if len(c) != 1:
        sys.exit(f"esperava 1 pasta '{int(nn):02d} - …' em {ROOT}, achei {len(c)}")
    return c[0]


def run(cmd, **kw):
    """Executa mostrando o comando; propaga o código de saída."""
    print("$", " ".join(str(x) for x in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        sys.exit(r.returncode)


def fundido(pasta):
    """Arquivo `-limpo.mov` gerado pelo passo 1 (relatório fuse_report.json)."""
    return json.load(open(os.path.join(pasta, "work", "fuse_report.json")))["out"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("etapa", choices=["prepare", "cut", "deliver"])
    ap.add_argument("nn")
    ap.add_argument("--video")
    ap.add_argument("--wav")
    ap.add_argument("--vocab", default="", help="vocabulário da notícia (nomes, empresas, siglas) para a transcrição")
    a = ap.parse_args()
    pasta = pasta_ep(a.nn)
    tema = os.path.basename(pasta).split(" - ", 1)[1]
    nome = f"News {int(a.nn):02d} - {tema}"
    w = os.path.join(pasta, "work")
    os.makedirs(w, exist_ok=True)
    if a.etapa == "prepare":
        cmd = [PY, os.path.join(HERE, "fuse_audio.py"), pasta] + (["--video", a.video] if a.video else []) + (["--wav", a.wav] if a.wav else [])
        run(cmd)
        f = fundido(pasta)
        run([PY, os.path.join(HERE, "media_features.py"), f, os.path.join(w, "features.npz")])
        run(["bash", os.path.join(HERE, "transcribe_news.sh"), pasta, f, a.vocab or tema])
    elif a.etapa == "cut":
        run([PY, os.path.join(HERE, "plan_cuts.py"), pasta])
        run([PY, os.path.join(HERE, "report_cuts.py"), pasta, "--nome", nome])
        print("AGORA: leia cortes.md e work/transcription.txt, revise (regras 3 e 6 = CONFIRA) e, se mudar algo, grave work/edits.json e rode `cut` de novo.")
    else:
        f = fundido(pasta)
        cuts = os.path.join(w, "cuts.json")
        previa = os.path.join(pasta, "PRONTO_auto.mp4")
        run([PY, os.path.join(HERE, "render_preview.py"), f, cuts, previa])
        run([PY, os.path.join(HERE, "build_news_draft.py"), f, cuts, nome])
        run([PY, os.path.join(HERE, "validate_news.py"), pasta, f, previa, "--transcribe"])
        run([PY, os.path.join(HERE, "report_cuts.py"), pasta, "--nome", nome])


if __name__ == "__main__":
    main()
