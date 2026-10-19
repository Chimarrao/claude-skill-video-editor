"""Regras de detecção do editor NEWS (regravação, falso começo, comando falado, fragmento, explicação refeita, início/fim).
Cada regra devolve `Remocao`s em índices de palavra. A ordem das palavras NUNCA muda: só se remove."""

from difflib import SequenceMatcher

from plan_cuts import Remocao, texto  # noqa: E402

PARTICULAS = {"e", "mas", "que", "entao", "ta", "si", "ou", "de", "do", "da", "o", "a", "um", "uma", "ne", "ai", "tipo", "ate", "porque", "eh", "e", "sao", "ja", "pra", "pro", "em"}


def _toks(words, i0, i1):
    return [w["n"] for w in words[i0:i1] if w["n"]]


def _ratio(a, b):
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def comandos(words, utts, P):
    """Regra 5: comando falado ("corta", "de novo", "errei", "vou repetir", "pera"…). Só vale quando o comando é (quase) o enunciado inteiro
    (<= command_max_utt_words palavras): "a empresa corta custos" é conteúdo, "corta." sozinho é comando. Sai do início da tentativa que falhou
    (enunciado anterior) até o fim do comando."""
    cmds = [[_n(t) for t in c.split()] for c in P["command_words"]]
    out = []
    for u, (a, b) in enumerate(utts):
        if b - a > P["command_max_utt_words"]:
            continue
        toks = [w["n"] for w in words[a:b]]
        for c in cmds:
            for i in range(0, len(toks) - len(c) + 1):
                if toks[i : i + len(c)] == c:
                    ini = a if (i > 0 or u == 0) else utts[u - 1][0]
                    out.append(Remocao(ini, b, "comando", nota=f"«{texto(words, a, b)}»"))
                    break
    return out


def _n(t):
    from plan_cuts import norm

    return norm(t)


def repeticoes(words, utts, P):
    """Regra 3 e 4: regravação / reinício. Um enunciado cujo COMEÇO se repete no enunciado seguinte (ignorando partículas iniciais como "e", "mas", "então")
    sai inteiro, junto com tudo que veio entre as duas tentativas; fica a última versão. Âncora: o 1º token (não-partícula) tem que casar."""
    out = []
    K = P["retake_prefix_words"]
    for j in range(1, len(utts)):
        tj = _toks(words, *utts[j])
        while len(tj) > 2 and tj[0] in PARTICULAS:
            tj = tj[1:]
        if len(tj) < 2:
            continue
        for i in range(max(0, j - P["retake_lookback_utts"]), j):
            ti = _toks(words, *utts[i])
            while len(ti) > 2 and ti[0] in PARTICULAS:
                ti = ti[1:]
            if len(ti) < 2:
                continue
            if words[utts[j][0]]["s"] - words[utts[i][1] - 1]["e"] > P["retake_lookback_s"]:
                continue
            k = min(K, len(ti), len(tj))
            sm = SequenceMatcher(None, ti[:k], tj[:k])
            blocos = [b for b in sm.get_matching_blocks() if b.size]
            casados = sum(b.size for b in blocos)
            ancora = bool(blocos) and blocos[0].a == 0 and blocos[0].b == 0
            if ancora and casados >= 2 and sm.ratio() >= P["retake_prefix_ratio"]:
                out.append(Remocao(utts[i][0], utts[j][0], "regravação", nota=f"«{texto(words, *utts[i])[:70]}» repetido em {words[utts[j][0]]['s']:.1f}s"))
                break
    return out


def repeticao_interna(words, utts, P):
    """Regra 3: a mesma sequência de >= internal_ngram palavras dita duas vezes DENTRO do enunciado, a no máx. internal_max_dist palavras uma da outra
    ("Isso depende do plano que estamos falando, isso depende do plano", "É um bom agregador, é um bom agregador", "ou seja ou seja"): sai da 1ª ocorrência
    até o começo da 2ª (reinício da frase). Repetição de 2 palavras só vale se for colada ("ou seja ou seja")."""
    out = []
    N = P["internal_ngram"]
    for a, b in utts:
        t = [w["n"] for w in words[a:b]]
        k = 0
        while k < len(t) - 1:
            achou = False
            for L in range(min(8, (len(t) - k) // 2), 1, -1):
                g = t[k : k + L]
                if not all(g):
                    continue
                lim = 0 if L < N else P["internal_max_dist"]  # curtas (2 palavras): só coladas
                for d in range(L, L + lim + 1):
                    if t[k + d : k + d + L] == g and k + d + L <= len(t):
                        out.append(Remocao(a + k, a + k + d, "regravação", nota=f"«{texto(words, a + k, a + k + d)}» dito de novo logo depois"))
                        k += d
                        achou = True
                        break
                if achou:
                    break
            if not achou:
                k += 1
    return out


def reticencias(words, utts, P):
    """Regra 4: enunciado que termina em "..." (a fala morreu no meio) e continua depois = frase abandonada."""
    out = []
    for j, (a, b) in enumerate(utts[:-1]):
        if words[b - 1]["w"].endswith(("...", "…")):
            out.append(Remocao(a, b, "falso começo", nota=f"«{texto(words, a, b)[:70]}» (reticências)"))
    return out


def sufixo_repetido(words, utts, P):
    """Regra 3: o FIM de um enunciado repete o COMEÇO do seguinte ("É uma | É uma plataforma", "ou seja ou seja", "então acredito | então acredito que"):
    sai o trecho repetido do enunciado anterior; fica a versão completa que vem depois."""
    out = []
    for j in range(1, len(utts)):
        a, b = utts[j - 1]
        c, d = utts[j]
        gap = words[c]["s"] - words[b - 1]["e"]
        if gap < P["suffix_min_gap_s"] or gap > P["retake_lookback_s"]:
            continue
        ti = [w["n"] for w in words[a:b]]
        tj = [w["n"] for w in words[c:d]]
        melhor = None
        for k in range(min(P["suffix_max_words"], len(ti), len(tj)), 0, -1):
            suf, pre = ti[-k:], tj[:k]
            r = _ratio(suf, pre)
            if r >= P["suffix_ratio"] and (k >= 2 or len(suf[0]) >= P["suffix_min_len1"]):
                melhor = k
                break
        if melhor:
            out.append(Remocao(b - melhor, b, "regravação", nota=f"«{texto(words, b - melhor, b)}» repetido logo depois"))
    return out


def fragmentos(words, utts, P):
    """Regra 4: enunciado curto (<= fragment_max_words palavras) que NÃO termina em ponto final/interrogação/exclamação = frase abandonada."""
    out = []
    for j, (a, b) in enumerate(utts):
        toks = _toks(words, a, b)
        if not toks or len(toks) > P["fragment_max_words"] or j == len(utts) - 1:
            continue
        ultima = words[b - 1]["w"]
        if ultima.endswith((".", "?", "!")) and not ultima.endswith("..."):
            continue
        out.append(Remocao(a, b, "falso começo", nota=f"«{texto(words, a, b)}»"))
    return out


def blocos_repetidos(words, utts, P):
    """Regra 6 (explicação refeita, o corte mais arriscado): uma sequência de >= block_ngram palavras IGUAIS aparece duas vezes (<= block_max_gap_s entre elas):
    a 1ª é a tentativa antiga. Sai do começo do enunciado da 1ª ocorrência até o começo do enunciado da 2ª — SE o conteúdo removido reaparece (>= block_overlap)
    na versão que fica (senão seria perder informação: só vira CONFIRA, não corta). Sempre marcado `confira`."""
    n = len(words)
    toks = [w["n"] for w in words]
    N = P["block_ngram"]
    uidx = {}
    for u, (a, b) in enumerate(utts):
        for k in range(a, b):
            uidx[k] = u
    visto, pares = {}, []
    for k in range(n - N + 1):
        if not all(toks[k : k + N]):
            continue
        g = tuple(toks[k : k + N])
        if g in visto:
            pares.append((visto[g], k))
        visto[g] = k  # a ocorrência mais recente
    out, usados = [], set()
    for i, j in pares:
        ui, uj = uidx[i], uidx[j]
        if ui == uj or j - i < N + 2:
            continue
        if words[j]["s"] - words[i]["e"] > P["block_max_gap_s"]:
            continue
        ini, fim = utts[ui][0], utts[uj][0]
        if fim <= ini or any(k in usados for k in range(ini, fim)):
            continue
        antigo = set(t for t in toks[ini:fim] if len(t) > 3)
        depois = set(t for t in toks[fim : fim + 2 * (fim - ini) + 10] if len(t) > 3)
        sobreposicao = len(antigo & depois) / max(1, len(antigo))
        if sobreposicao >= P["block_overlap"]:
            out.append(Remocao(ini, fim, "explicação refeita", confira=True, nota=f"trecho repetido «{texto(words, i, i + N)}…» (sobreposição {sobreposicao:.0%})"))
            usados.update(range(ini, fim))
    return out


def detecta(words, utts, feats, P):
    """Todas as regras; remoções sobrepostas são unidas na etapa de construção (a primeira vence o motivo)."""
    rem = []
    rem += comandos(words, utts, P)
    rem += repeticoes(words, utts, P)
    rem += blocos_repetidos(words, utts, P)
    rem += repeticao_interna(words, utts, P)
    rem += reticencias(words, utts, P)
    rem += sufixo_repetido(words, utts, P)
    rem += fragmentos(words, utts, P)
    rem.sort(key=lambda r: (r.i0, r.i1))
    return rem
