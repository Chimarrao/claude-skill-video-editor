"""Transforma as remoções (em palavras) em intervalos de tempo: respiro, encolhimento de pausas, ponto de corte em silêncio (energia baixa) e,
entre os candidatos, o par (saída, entrada) com tela mais parecida (continuidade visual: gravação de tela parada = corte invisível)."""

import numpy as np

HOP = 0.01  # 10 ms por janela de energia


def energia(feats, t):
    """dB (suavizado ~30 ms) no instante t."""
    e = feats["energy_db"]
    i = int(round(t / HOP))
    i = min(max(i, 1), len(e) - 2)
    return float(e[i - 1 : i + 2].mean())


def quadro(feats, t):
    """Miniatura em cinza (10 fps) mais próxima de t."""
    fr = feats["frames"]
    i = int(round(t * float(feats["fps"])))
    return fr[min(max(i, 0), len(fr) - 1)].astype(np.int16)


def limiar_silencio(feats, folga_db):
    """Energia (dB) até a qual um instante conta como SILÊNCIO: piso de ruído (percentil 5) + folga."""
    return float(np.percentile(feats["energy_db"], 5)) + folga_db


def candidatos(feats, lo, hi, alvo, n=4, passo=0.02, livre=False):
    """Até `n` instantes em [lo, hi] com energia mais baixa (mistura energia e distância ao alvo). Só entram instantes em SILÊNCIO (piso + 20 dB);
    se a fala é colada e não há silêncio de verdade, aceita o vale de energia (piso + 35 dB, quase sempre o intervalo entre duas palavras)."""
    if hi <= lo:
        return []
    ts = np.arange(lo, hi + 1e-9, passo)
    es = [energia(feats, t) for t in ts]
    for folga in (20.0, 35.0):
        thr = limiar_silencio(feats, folga)
        idx = [k for k, e in enumerate(es) if e <= thr]
        if idx:
            sc = [es[k] + 12.0 * abs(ts[k] - alvo) for k in idx]
            return [float(ts[idx[k]]) for k in np.argsort(sc)[:n]]
    if livre:  # fala colada (corte apertado): fica com o vale de energia entre as palavras, mesmo sem silêncio de verdade
        sc = [e + 12.0 * abs(t - alvo) for t, e in zip(ts, es)]
        return [float(ts[k]) for k in np.argsort(sc)[:n]]
    return []


def ponto_par(feats, a_end, b_start, nxt_start, prv_end, P):
    """Escolhe (lo, hi): lo logo depois de a_end (respiro), hi logo antes de b_start; ambos em silêncio; menor diferença visual entre os dois quadros.
    `nxt_start` = início da próxima palavra ORIGINAL depois de a (limite para lo); `prv_end` = fim da palavra original antes de b (limite para hi).
    Margem de segurança das palavras: `word_margin_s` (80 ms, regra do usuário: nunca dentro/colado em palavra); `margin_tiers` (opcional) permite margens menores quando a fala é colada."""
    for m in P.get("margin_tiers", [P["word_margin_s"]]):
        lo_min, lo_max = a_end + m, min(a_end + 0.5, nxt_start - m)
        hi_min, hi_max = max(b_start - 0.5, prv_end + m), b_start - m
        if lo_max < lo_min or hi_max < hi_min:
            continue
        lo_alvo = min(max(a_end + P["breath_after_s"], lo_min), lo_max)
        hi_alvo = max(min(b_start - P["breath_before_s"], hi_max), hi_min)
        los = candidatos(feats, lo_min, lo_max, lo_alvo, livre=bool(P.get("free_valley")))
        his = candidatos(feats, hi_min, hi_max, hi_alvo, livre=bool(P.get("free_valley")))
        melhor = None
        for lo in los:
            for hi in his:
                if hi - lo < P["min_cut_s"]:
                    continue
                d = float(np.abs(quadro(feats, lo) - quadro(feats, hi)).mean())
                custo = d + 0.3 * (energia(feats, lo) + energia(feats, hi)) / 10 + 8 * (abs(lo - lo_alvo) + abs(hi - hi_alvo))
                if melhor is None or custo < melhor[0]:
                    melhor = (custo, lo, hi, d)
        if melhor:
            return melhor[1:]
    return None


def constroi(words, rem, feats, P):
    """Remoções (Remocao) → {kept, removed, stats}. Tempos em segundos."""
    n = len(words)
    fps = P.get("fps_out", 60)
    dur = len(feats["energy_db"]) * HOP
    morta = [None] * n
    for r in rem:
        for i in range(r.i0, r.i1):
            if morta[i] is None:
                morta[i] = r
    keep = [i for i in range(n) if morta[i] is None]
    if not keep:
        raise SystemExit("nenhuma palavra mantida")
    cortes = []  # dicts start,end,reason,text,confira
    # início
    ini = max(0.0, words[keep[0]]["s"] - P["start_preroll_s"])
    # fim
    fim = min(dur, words[keep[-1]]["e"] + P["end_postroll_s"])
    # entre palavras mantidas consecutivas
    for a, b in zip(keep, keep[1:]):
        g = words[b]["s"] - words[a]["e"]
        sep = b - a > 1
        if not sep and g <= P["pause_max_s"]:
            continue
        nxt = words[a + 1]["s"] if a + 1 < n else words[a]["e"] + 1
        prv = words[b - 1]["e"]
        par = ponto_par(feats, words[a]["e"], words[b]["s"], nxt, prv, P)
        apertado = False
        if not par and sep:  # fala colada (< 2 margens entre as palavras): 2ª tentativa com margem menor, marcada como CORTE APERTADO (vai para CONFIRA)
            par = ponto_par(feats, words[a]["e"], words[b]["s"], nxt, prv, dict(P, margin_tiers=P.get("tight_margin_tiers", [0.05, 0.03]), free_valley=True))
            apertado = bool(par)
        if not par:
            continue
        lo, hi = par[0], par[1]
        if hi - lo < P["min_cut_s"]:
            continue
        if sep:
            rs = [morta[i] for i in range(a + 1, b) if morta[i] is not None]
            motivos = list(dict.fromkeys(r.motivo for r in rs))
            cortes.append(dict(start=lo, end=hi, reason=" + ".join(motivos), text=" ".join(w["w"] for w in words[a + 1 : b]), confira=any(r.confira for r in rs) or apertado, apertado=apertado, nota="; ".join(r.nota for r in rs if r.nota) + (" · CORTE APERTADO (fala colada, < 80 ms da palavra)" if apertado else "")))
        else:
            cortes.append(dict(start=lo, end=hi, reason="pausa", text="", confira=False, nota=f"pausa de {g:.2f}s"))
    # grade de quadros
    q = lambda t: round(t * fps) / fps
    cortes = [dict(c, start=q(c["start"]), end=q(c["end"])) for c in cortes]
    cortes = [c for c in cortes if c["end"] - c["start"] >= 1 / fps]
    ini, fim = q(ini), q(fim)
    kept, cur = [], ini
    for c in cortes:
        if c["start"] > cur:
            kept.append([cur, c["start"]])
        cur = max(cur, c["end"])
    if fim > cur:
        kept.append([cur, fim])
    removed = []
    if ini > 0:
        removed.append(dict(start=0.0, end=ini, reason="início", text="", confira=False, nota=""))
    removed += cortes
    if fim < dur - 0.05:
        removed.append(dict(start=fim, end=dur, reason="fim", text="", confira=False, nota=""))
    kept_s = sum(b - a for a, b in kept)
    return dict(kept=kept, removed=removed, stats=dict(dur_s=dur, kept_s=kept_s, n_words=n, n_kept_words=len(keep)))


def aplica_cortes_tempo(res, cortes, feats, P):
    """Revisão do agente: cortes por TEMPO exato ({t0, t1, motivo, nota}) — para o que o Whisper não registrou (fala repetida que ele colapsa em uma só).
    t0/t1 são ajustados para o silêncio mais próximo (±0,2 s) e para a grade de quadros; unidos aos cortes existentes; recalcula os trechos mantidos."""
    fps = P.get("fps_out", 60)
    dur = res["stats"]["dur_s"]
    q = lambda t: round(t * fps) / fps
    novos = []
    for c in cortes:
        lo = (candidatos(feats, max(0.0, c["t0"] - 0.2), c["t0"] + 0.2, c["t0"], n=1, livre=True) or [c["t0"]])[0]
        hi = (candidatos(feats, c["t1"] - 0.2, min(dur, c["t1"] + 0.2), c["t1"], n=1, livre=True) or [c["t1"]])[0]
        novos.append(dict(start=q(lo), end=q(hi), reason=c.get("motivo", "revisão"), text=c.get("texto", ""), confira=True, nota=c.get("nota", "corte por tempo (revisão do agente)")))
    ini = res["removed"][0]["end"] if res["removed"] and res["removed"][0]["reason"] == "início" else 0.0
    fim = res["removed"][-1]["start"] if res["removed"] and res["removed"][-1]["reason"] == "fim" else dur
    todos = sorted([r for r in res["removed"] if r["reason"] not in ("início", "fim")] + novos, key=lambda r: r["start"])
    uni = []
    for r in todos:
        if uni and r["start"] <= uni[-1]["end"] + 1e-9:
            uni[-1]["end"] = max(uni[-1]["end"], r["end"])
            uni[-1]["reason"] = " + ".join(dict.fromkeys(uni[-1]["reason"].split(" + ") + r["reason"].split(" + ")))
            uni[-1]["text"] = (uni[-1]["text"] + " " + r["text"]).strip()
            uni[-1]["confira"] = uni[-1]["confira"] or r["confira"]
            uni[-1]["nota"] = "; ".join(x for x in (uni[-1].get("nota", ""), r.get("nota", "")) if x)
        else:
            uni.append(dict(r))
    kept, cur = [], ini
    for r in uni:
        if r["start"] > cur:
            kept.append([cur, r["start"]])
        cur = max(cur, r["end"])
    if fim > cur:
        kept.append([cur, fim])
    removed = ([res["removed"][0]] if ini > 0 else []) + uni + ([res["removed"][-1]] if fim < dur - 0.05 else [])
    res.update(kept=kept, removed=removed)
    res["stats"]["kept_s"] = sum(b - a for a, b in kept)
    return res
