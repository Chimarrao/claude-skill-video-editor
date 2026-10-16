"""Geometria dos grafos para o controle de qualidade: onde ficam rótulo, ícone e setas, e se algo se corta ou se sobrepõe.

Usado pelo plan.py (falha o build em STRICT) e por scripts/quality/gate_plan.py (confere de novo os JSONs gerados).
As constantes espelham src/lib/figure.tsx e src/lib/arrowBetween.tsx: se mudar o desenho lá, mude aqui (e rode
scripts/tests/test_engine_geometry.py).
"""

SIZE_LABEL = 36  # fonte do rótulo (px)
LABEL_DROP = 80  # seta que sai por baixo de um disco/foto redonda com rótulo começa depois do texto (figure.tsx → labelDrop)


def _core(o):
    """(largura, altura) do miolo desenhado do item (placa ou imagem), em px."""
    h = o["h"]
    if o.get("plate") and o.get("ph"):
        return o["pw"] or h, o["ph"]
    return (o.get("iw") or h), (o.get("ih") or h)


def label_rect(o):
    """Retângulo do texto do rótulo (aproximado: fonte de 36 px) ou None. Disco/foto redonda: texto 46 px abaixo da borda; logo/imagem em coluna: na reserva de baixo."""
    if not o.get("label"):
        return None
    cw, ch = _core(o)
    w = max(40.0, len(o["label"]) * SIZE_LABEL * 0.56)
    solto = o.get("bezel") or o.get("circular")
    cy = o["y"] + ch / 2 + (46 if solto else 8 + SIZE_LABEL * 1.35 / 2)
    return (o["x"] - w / 2, cy - 20, o["x"] + w / 2, cy + 20)


def image_rect(o):
    """Retângulo do miolo (placa/imagem/disco)."""
    cw, ch = _core(o)
    return (o["x"] - cw / 2, o["y"] - ch / 2, o["x"] + cw / 2, o["y"] + ch / 2)


def edge_points(a, b, e):
    """Pontos do caminho da seta a→b exatamente como o arrowBetween.tsx desenha (reta ou cotovelo com barramento)."""
    ca, cb = _core(a), _core(b)
    sa, sb = e["sides"]

    def borda(o, side, drop):
        cw, ch = _core(o)
        solto = o.get("bezel") or o.get("circular")
        col_extra = 0 if solto else (8 + SIZE_LABEL * 1.35 if o.get("label") else 0)  # reserva (e vão) abaixo/acima do miolo nas colunas
        if side == "bottom":
            return (o["x"], o["y"] + ch / 2 + col_extra + (LABEL_DROP if (solto and o.get("label") and drop) else 0))
        if side == "top":
            return (o["x"], o["y"] - ch / 2 - (col_extra if o.get("label") else 0))
        if side == "right":
            return (o["x"] + cw / 2, o["y"])
        return (o["x"] - cw / 2, o["y"])

    p0, p3 = borda(a, sa, True), borda(b, sb, False)
    if e["style"] == "straight":
        return [p0, p3]
    bus = e.get("bus")
    if sa in ("bottom", "top"):
        m = bus if bus is not None else (p0[1] + p3[1]) / 2
        return [p0, (p0[0], m), (p3[0], m), p3]
    m = bus if bus is not None else (p0[0] + p3[0]) / 2
    return [p0, (m, p0[1]), (m, p3[1]), p3]


def _seg_hits_rect(p, q, r, tol=3.0):
    """O segmento p→q atravessa o retângulo r (encolhido em `tol` px)? (Liang–Barsky)"""
    x0, y0, x1, y1 = r[0] + tol, r[1] + tol, r[2] - tol, r[3] - tol
    if x0 >= x1 or y0 >= y1:
        return False
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if abs(pp) < 1e-9:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                if t > t1:
                    return False
                t0 = max(t0, t)
            else:
                if t < t0:
                    return False
                t1 = min(t1, t)
    return t0 <= t1


def problems(items, edges):
    """Lista de problemas geométricos: seta cortando rótulo/ícone de qualquer item, ou rótulos/ícones sobrepostos."""
    erros = []
    for e in edges:
        a, b = items[e["src"]], items[e["dst"]]
        pts = edge_points(a, b, e)
        for k, it in enumerate(items):
            if not it.get("img"):
                continue
            rects = [("rótulo", label_rect(it))]
            if k not in (e["src"], e["dst"]):
                rects.append(("ícone", image_rect(it)))
            for nome, r in rects:
                if r and any(_seg_hits_rect(p, q, r) for p, q in zip(pts, pts[1:])):
                    erros.append(f"seta {e['src'] + 1}→{e['dst'] + 1} corta o {nome} do item {k + 1} ({it.get('label') or it['img']})")
    rs = [(k, label_rect(it), image_rect(it)) for k, it in enumerate(items) if it.get("img")]
    for i, (k1, l1, im1) in enumerate(rs):
        for k2, l2, im2 in rs[i + 1 :]:
            for n1, r1 in (("rótulo", l1), ("ícone", im1)):
                for n2, r2 in (("rótulo", l2), ("ícone", im2)):
                    if r1 and r2 and r1[0] < r2[2] - 2 and r2[0] < r1[2] - 2 and r1[1] < r2[3] - 2 and r2[1] < r1[3] - 2 and (n1, n2) != ("ícone", "ícone"):
                        erros.append(f"{n1} do item {k1 + 1} sobrepõe o {n2} do item {k2 + 1}")
    return list(dict.fromkeys(erros))
