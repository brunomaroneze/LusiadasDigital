"""Comparação palavra a palavra entre duas versões do mesmo texto.

Usada pela tela de leitura em colunas: dadas as árvores TEI das duas colunas
(já sem namespace), marca com <span class="dif"> as palavras que diferem entre
versos correspondentes — mesma estrofe (atributo n) e mesma posição dentro da
estrofe. O realce só fica visível quando o leitor liga a opção "Realçar
diferenças" (ver leitura.js / style.css).

Dois níveis de diferença:
  .dif            palavra diferente (ex.: "edificáram" x "edificarão")
  .dif.dif--leve  só pontuação ou hifenização (ex.: "Lusi-tana" x "Lusitana",
                  ou "humana:" x "humana."), que costuma ser ruído gráfico e
                  por isso aparece mais discreto.
"""
import difflib
import re

from lxml import etree

# palavra (letras/dígitos) ou um sinal de pontuação isolado
_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_PALAVRA = re.compile(r"\w", re.UNICODE)


def _so_pontuacao(tokens):
    return all(not _PALAVRA.match(t) for t in tokens)


def _classe(tokens_a, tokens_b):
    """'dif--leve' se a diferença é só de pontuação/hifenização; senão 'dif'."""
    if _so_pontuacao(tokens_a) and _so_pontuacao(tokens_b):
        return "dif dif--leve"
    if "".join(tokens_a).replace("-", "") == "".join(tokens_b).replace("-", ""):
        return "dif dif--leve"  # ex.: "ba-" + "rões" x "barões"
    return "dif"


def _decompor(verso):
    """Quebra o verso em pedaços de texto (antes/entre/depois dos <lb/>) e tokens.

    Cada token é (texto, trechos), onde trechos = [(pedaço, início, fim), ...]
    diz onde ele está no verso. Uma palavra hifenizada ("Lusi-tana", ou
    "ba-" + <lb/> + "rões") vira um token só, para ser comparada inteira com a
    forma sem hífen da outra edição.

    Devolve None se o verso tiver algo além de texto e <lb/> (raro: <sic>,
    <fw>...), para não arriscar desmontar a marcação — nesses casos o verso
    simplesmente fica sem realce.
    """
    filhos = list(verso)
    for f in filhos:
        if not isinstance(f.tag, str) or f.tag != "lb":
            return None
    pedacos = [verso.text or ""] + [f.tail or "" for f in filhos]

    atomos = []  # (pedaço, início, fim, texto)
    for i, pedaco in enumerate(pedacos):
        for m in _TOKEN.finditer(pedaco):
            atomos.append((i, m.start(), m.end(), m.group()))

    tokens, k = [], 0
    while k < len(atomos):
        pa, sa, ea, ta = atomos[k]
        if k + 2 < len(atomos) and _PALAVRA.match(ta) and atomos[k + 1][3] == "-":
            ph, sh, eh, _ = atomos[k + 1]
            pb, sb, eb, tb = atomos[k + 2]
            colado = ph == pa and sh == ea                      # palavra + hífen
            seguinte = (pb == ph and sb == eh) or (             # hífen + palavra, na mesma linha
                pb == ph + 1 and eh == len(pedacos[ph]) and sb == 0  # ou depois do <lb/>
            )
            if colado and seguinte and _PALAVRA.match(tb):
                tokens.append((ta + "-" + tb, [(pa, sa, ea), (ph, sh, eh), (pb, sb, eb)]))
                k += 3
                continue
        tokens.append((ta, [(pa, sa, ea)]))
        k += 1
    return filhos, pedacos, tokens


def _intervalos(tokens, i1, i2, classe, destino):
    """Converte tokens [i1:i2] em intervalos de texto, um por pedaço."""
    grupo = None
    for _, trechos in tokens[i1:i2]:
        for pedaco, ini, fim in trechos:
            if grupo and grupo[0] == pedaco:
                grupo[2] = fim
            else:
                if grupo:
                    destino.setdefault(grupo[0], []).append((grupo[1], grupo[2], classe))
                grupo = [pedaco, ini, fim]
    if grupo:
        destino.setdefault(grupo[0], []).append((grupo[1], grupo[2], classe))


def _aplicar(verso, filhos, pedacos, intervalos):
    """Reescreve o conteúdo do verso envolvendo os intervalos em <span>."""
    if not intervalos:
        return
    for f in filhos:
        verso.remove(f)  # no lxml, remove() leva o 'tail' junto
        f.tail = None
    verso.text = None
    ultimo = None

    def texto(s):
        if not s:
            return
        if ultimo is None:
            verso.text = (verso.text or "") + s
        else:
            ultimo.tail = (ultimo.tail or "") + s

    for i, pedaco in enumerate(pedacos):
        if i > 0:
            ultimo = filhos[i - 1]
            verso.append(ultimo)
        pos = 0
        for ini, fim, classe in sorted(intervalos.get(i, [])):
            texto(pedaco[pos:ini])
            span = etree.SubElement(verso, "span")
            span.set("class", classe)
            span.text = pedaco[ini:fim]
            ultimo = span
            pos = fim
        texto(pedaco[pos:])


def _comparar_versos(verso_a, verso_b):
    """Marca as diferenças entre dois versos. Devolve quantas encontrou."""
    dec_a, dec_b = _decompor(verso_a), _decompor(verso_b)
    if dec_a is None or dec_b is None:
        return 0
    filhos_a, pedacos_a, tokens_a = dec_a
    filhos_b, pedacos_b, tokens_b = dec_b

    textos_a = [t[0] for t in tokens_a]
    textos_b = [t[0] for t in tokens_b]
    ops = difflib.SequenceMatcher(None, textos_a, textos_b, autojunk=False).get_opcodes()

    int_a, int_b, achadas = {}, {}, 0
    for tag, a1, a2, b1, b2 in ops:
        if tag == "equal":
            continue
        if tag == "replace" and a2 - a1 == b2 - b1:
            # mesmo número de palavras: compara par a par, para que uma troca
            # de pontuação não "contamine" a palavra vizinha, e vice-versa
            blocos = [(a1 + i, a1 + i + 1, b1 + i, b1 + i + 1) for i in range(a2 - a1)]
        else:
            blocos = [(a1, a2, b1, b2)]
        for x1, x2, y1, y2 in blocos:
            achadas += 1
            classe = _classe(textos_a[x1:x2], textos_b[y1:y2])
            _intervalos(tokens_a, x1, x2, classe, int_a)
            _intervalos(tokens_b, y1, y2, classe, int_b)

    _aplicar(verso_a, filhos_a, pedacos_a, int_a)
    _aplicar(verso_b, filhos_b, pedacos_b, int_b)
    return achadas


def marcar_diferencas(raiz_a, raiz_b):
    """Marca, nas duas árvores, as diferenças entre estrofes de mesmo número.

    Devolve o total de diferenças encontradas (para exibir ao leitor).
    """
    por_numero = {}
    for lg in raiz_b.iter("lg"):
        n = lg.get("n")
        if n and n not in por_numero:
            por_numero[n] = lg

    total = 0
    for lg_a in raiz_a.iter("lg"):
        lg_b = por_numero.get(lg_a.get("n"))
        if lg_b is None:
            continue
        # compara verso a verso, pela posição na estrofe
        for verso_a, verso_b in zip(lg_a.findall("l"), lg_b.findall("l")):
            total += _comparar_versos(verso_a, verso_b)
    return total
