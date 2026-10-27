#!/usr/bin/env python3
"""TESTE das peças do tipo "Webdoc com rounds" (DSL do plan.py + fonte TS), sem rede nem projeto. Rode de qualquer pasta.
 R1 Side/Round/Duel/Verdict/Bars/Profile/ProfileRow/ScoreStrip geram peças `center` com as chaves que o scene1.tsx lê    R2 limites de texto são recusados (chips, título, resultado, traços)
 R3 o scene1.tsx tem um `case` para cada `kind` novo e o rounds.tsx exporta as funções usadas                         R4 nenhuma peça nova mexe nos tipos antigos (kinds antigos intactos)"""

import os, re, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "template"
tmp = Path(tempfile.mkdtemp(prefix="rounds_"))
(tmp / "src/images").mkdir(parents=True)
from PIL import Image

for n, (w, h) in dict(logo_a=(200, 200), logo_b=(300, 150)).items():
    Image.new("RGBA", (w, h), (255, 0, 0, 255)).save(tmp / f"src/images/{n}.png")
import json

json.dump(dict(duration=30.0, segments=[dict(words=[dict(word="x", start=1.0, end=1.1)], start=1.0, end=1.1, text="")]), open(tmp / "t.json", "w"))
os.environ["TRANSCRIPTION"] = str(tmp / "t.json")
os.chdir(tmp)
sys.path.insert(0, str(TEMPLATE))
import plan  # noqa: E402

ok, falhas = [], []


def teste(nome, cond, msg=""):
    (ok if cond else falhas).append(nome if cond else f"{nome}: {msg}")


A = plan.Side("Cinnamon", "logo_a", "#ff7b3a", ["um", "dois"])
B = plan.Side("XFCE", "logo_b", "#3fa3ff", ["três"])
pecas = dict(
    round=plan.Round(1, "Batalha Visual", A, B, "Look & Feel"),
    duel=plan.Duel(A, B, "A"),
    verdict=plan.Verdict("ROUND 1", "EMPATE", "#ccc", "gosto pessoal"),
    bars=plan.Bars("RAM", [("XFCE", 600, "~600 MB", "#3fa3ff", "logo_a"), ("Cinnamon", 950, "~900 MB", "#ff7b3a", "logo_b")], "MB"),
    profile=plan.Profile(1, "Iniciante", ["a", "b"], "Cinnamon", "#ff7b3a", "logo_a"),
)
pecas["profiles"] = plan.ProfileRow([pecas["profile"]])
pecas["scorestrip"] = plan.ScoreStrip([("Visual", "EMPATE", "#ccc")])
teste("R1 todas as peças novas são `center` com o kind esperado", all(p["slot"] == "center" and p["kind"] == k for k, p in pecas.items()), str({k: (p["slot"], p["kind"]) for k, p in pecas.items()}))
teste("R1 Side mede a proporção do logo", abs(A["asp"] - 1.0) < 0.01 and abs(B["asp"] - 2.0) < 0.01, f"{A['asp']} {B['asp']}")
teste("R1 o duelo leva o foco e os dois lados", pecas["duel"]["props"]["focus"] == "A" and pecas["duel"]["props"]["b"]["name"] == "XFCE")
teste("R1 ProfileRow reaproveita as cartas (não recria)", pecas["profiles"]["props"]["profiles"][0]["edition"] == "Cinnamon")


def recusa(f, *a, **k):
    try:
        f(*a, **k)
        return False
    except SystemExit:
        return True


teste("R2 mais de 4 chips é recusado", recusa(plan.Side, "X", None, "#fff", ["1", "2", "3", "4", "5"]))
teste("R2 chip longo é recusado", recusa(plan.Side, "X", None, "#fff", ["x" * 40]))
teste("R2 título de round longo é recusado", recusa(plan.Round, 1, "x" * 40, A, B))
teste("R2 resultado de veredito longo é recusado", recusa(plan.Verdict, "R", "x" * 30, "#fff"))
teste("R2 mais de 3 traços no perfil é recusado", recusa(plan.Profile, 1, "t", ["a", "b", "c", "d"], "X", "#fff"))
teste("R2 barras: de 2 a 5", recusa(plan.Bars, "t", [("a", 1, "1", "#fff", None)]))

tsx = (TEMPLATE / "src/scenes/scene1.tsx").read_text(encoding="utf8")
lib = (TEMPLATE / "src/lib/rounds.tsx").read_text(encoding="utf8")
for kind, fn in (("round", "roundCard"), ("duel", "duel"), ("verdict", "verdictBadge"), ("bars", "barsChart"), ("profile", "profileCard"), ("profiles", "profileRow"), ("scorestrip", "scoreStrip")):
    teste(f"R3 scene1.tsx trata '{kind}' e rounds.tsx exporta {fn}", f"case '{kind}':" in tsx and f"export function {fn}(" in lib)
teste("R4 kinds antigos continuam no scene1.tsx", all(f"case '{k}':" in tsx for k in ("freelogo", "logo", "people", "stat", "facts", "comparison", "screen", "graph", "section", "code")))

print("\n".join(f"  ok    {n}" for n in ok))
if falhas:
    print("\nFALHOU:\n  - " + "\n  - ".join(falhas))
    sys.exit(1)
print(f"\nOK: {len(ok)} verificações do tipo Webdoc com rounds passaram")
