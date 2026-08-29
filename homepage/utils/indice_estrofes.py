"""
Índice estrofe -> página, para a futura navegação "ir para a estrofe N".

Este módulo é independente do tei.py (não altera nada lá) e não muda o
banco de dados nem os models — apenas lê o TEI-XML que já existe em
PaginaTexto e extrai os números de estrofe (atributo `n` de <lg>) usando
lxml, sem converter para HTML (mais leve que tei_para_html, já que aqui
só precisamos dos números, não do texto renderizado).

Uso futuro (quando a UI da aba lateral for construída):

    from homepage.utils.indice_estrofes import construir_indice_estrofes
    indice = construir_indice_estrofes(canto_numero=1, versao="modernizado")
    # indice == {1: 1, 2: 1, 3: 2, ...}  -> estrofe: número da página
"""

from lxml import etree


def extrair_numeros_estrofes(tei_xml):
    """
    Recebe uma string de TEI-XML (o mesmo conteúdo salvo em
    PaginaTexto.tei_xml) e devolve a lista de números de estrofe
    (atributo `n` de cada <lg>) encontrados nela, na ordem em que
    aparecem no documento.

    Nunca levanta exceção: em caso de XML vazio ou malformado,
    devolve lista vazia — o chamador decide o que fazer (no índice,
    isso simplesmente significa "nenhuma estrofe identificada nesta
    página", sem quebrar a página inteira).
    """
    if not tei_xml:
        return []

    parser = etree.XMLParser(remove_blank_text=True)

    try:
        root = etree.fromstring(tei_xml.encode(), parser=parser)
    except etree.XMLSyntaxError:
        return []
    except Exception:
        return []

    numeros = []
    for lg in root.iter():
        # remove namespace do nome da tag antes de comparar, mesma lógica do tei.py
        tag = etree.QName(lg).localname if isinstance(lg.tag, str) else None
        if tag != "lg":
            continue
        n = lg.attrib.get("n")
        if n is not None:
            numeros.append(n)

    return numeros


def construir_indice_estrofes(canto_numero, versao="modernizado"):
    """
    Monta o mapa {numero_da_estrofe: numero_da_pagina} para um canto e
    uma versão de texto (ex: "modernizado" ou "original").

    Faz uma consulta simples ao banco (PaginaTexto), ordenada por página,
    e para cada página extrai os números de estrofe presentes nela.
    Se a mesma estrofe aparecer em mais de uma página (não deveria
    acontecer, mas por segurança), fica valendo a primeira ocorrência.

    Import de model feito dentro da função (não no topo do arquivo) de
    propósito: mantém este módulo importável em contextos sem Django
    totalmente configurado (ex: os testes manuais que rodei no terminal).
    """
    from ..models import PaginaTexto

    paginas = (
        PaginaTexto.objects
        .filter(canto__numero=canto_numero, versao=versao)
        .order_by("numero")
        .values_list("numero", "tei_xml")
    )

    indice = {}
    for numero_pagina, tei_xml in paginas:
        for n in extrair_numeros_estrofes(tei_xml):
            try:
                chave = int(n)
            except (TypeError, ValueError):
                chave = n
            indice.setdefault(chave, numero_pagina)

    return indice
