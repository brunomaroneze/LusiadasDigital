from lxml import etree

def tei_para_html(tei_xml):
    if not tei_xml:
        return ""
        
    parser = etree.XMLParser(remove_blank_text=True)
    
    try:
        root = etree.fromstring(tei_xml.encode(), parser=parser)
    except etree.XMLSyntaxError:
        return '<div class="aviso-erro">Erro na formatação: O XML TEI inserido é inválido ou está malformado.</div>'
    except Exception:
        return '<div class="aviso-erro">Erro inesperado ao processar o texto XML.</div>'

    # remover namespace
    for elem in root.iter():
        if isinstance(elem.tag, str):
            elem.tag = etree.QName(elem).localname
    etree.cleanup_namespaces(root)

    # pegar apenas o corpo do texto
    body = root.find(".//body")
    if body is not None:
        root = body

    # <lg> -> <div class="estrofe" data-estrofe="N">
    # (preserva o número da estrofe do TEI-XML original, que antes era
    #  descartado por attrib.clear(). Isso não muda a aparência da página —
    #  só adiciona um atributo novo que o JS de navegação vai usar depois
    #  para rolar/destacar a estrofe certa. Não usamos "id" aqui de propósito:
    #  como a mesma página renderiza duas colunas (esq/dir) com os mesmos
    #  números de estrofe, um "id" duplicado geraria HTML inválido.)
    for lg in root.findall(".//lg"):
        numero_estrofe = lg.attrib.get("n")
        lg.tag = "div"
        lg.attrib.clear()
        lg.attrib["class"] = "estrofe"
        if numero_estrofe:
            lg.attrib["data-estrofe"] = numero_estrofe

    # <l> -> <div class="verso">
    for l in root.findall(".//l"):
        l.tag = "div"
        l.attrib.clear()
        l.attrib["class"] = "verso"

    # <lb> -> <br>
    for lb in root.findall(".//lb"):
        lb.tag = "br"
        lb.attrib.clear()

    # <head> -> <h3>
    for head in root.findall(".//head"):
        head.tag = "h3"

    return etree.tostring(root, encoding="unicode", method="html")


def pretextual_para_html(tei_xml):
    """
    Converte os elementos pré-textuais (folha de rosto, alvará régio,
    licença do Santo Ofício etc.) de TEI-XML para HTML simples.

    Diferente de tei_para_html (que lida com a estrutura do poema —
    <lg>/<l>), este conversor lida com a estrutura de prosa/documento
    desses elementos de abertura do livro: <front>, <titlePage>,
    <docTitle>, <docAuthor>, <docImprint>, <titlePart>, <div type="...">,
    <p>, <name>, <pubPlace>, <date>, <supplied>.

    Segue o mesmo padrão defensivo de tei_para_html: nunca levanta
    exceção, devolve uma mensagem amigável em caso de XML vazio ou
    malformado.
    """
    if not tei_xml:
        return ""

    parser = etree.XMLParser(remove_blank_text=True)

    try:
        root = etree.fromstring(tei_xml.encode(), parser=parser)
    except etree.XMLSyntaxError:
        return '<div class="aviso-erro">Erro na formatação: O XML TEI inserido é inválido ou está malformado.</div>'
    except Exception:
        return '<div class="aviso-erro">Erro inesperado ao processar o texto XML.</div>'

    # remover namespace, igual a tei_para_html
    for elem in root.iter():
        if isinstance(elem.tag, str):
            elem.tag = etree.QName(elem).localname
    etree.cleanup_namespaces(root)

    # <pb/> (quebra de página) não carrega texto — remove
    for pb in root.findall(".//pb"):
        pai = pb.getparent()
        if pai is not None:
            pai.remove(pb)

    # <lb> -> <br>, mesma convenção de tei_para_html
    for lb in root.findall(".//lb"):
        lb.tag = "br"
        lb.attrib.clear()

    # trechos reconstruídos pelo editor (ilegíveis no original) — mantém
    # visível qual texto foi suprido, com o motivo em title="" (tooltip)
    for supplied in root.findall(".//supplied"):
        motivo = supplied.attrib.get("reason", "")
        supplied.tag = "span"
        supplied.attrib.clear()
        supplied.attrib["class"] = "suprido"
        if motivo:
            supplied.attrib["title"] = f"Texto suprido pelo editor ({motivo})"

    # realces sutis (nome próprio, local de publicação, data), sem
    # mudar a estrutura do texto — só viram <span> com classe própria
    for tag, classe in (
        ("name", "nome-proprio"),
        ("pubPlace", "local-publicacao"),
        ("date", "data-publicacao"),
    ):
        for el in root.findall(f".//{tag}"):
            el.tag = "span"
            el.attrib.clear()
            el.attrib["class"] = classe

    # blocos da folha de rosto (título, autor, dados de impressão)
    for tag, classe in (
        ("docTitle", "doc-titulo"),
        ("docAuthor", "doc-autor"),
        ("docImprint", "doc-impressao"),
        ("titlePart", "titulo-parte"),
    ):
        for el in root.findall(f".//{tag}"):
            el.tag = "div"
            el.attrib.clear()
            el.attrib["class"] = classe

    # <titlePage> -> contêiner com classe própria
    for tp in root.findall(".//titlePage"):
        tp.tag = "div"
        tp.attrib.clear()
        tp.attrib["class"] = "folha-rosto"

    # <div type="AlvaraRegio"> / <div type="LicencaSantoOficio"> -> contêiner
    # com classe genérica + classe específica do tipo de documento
    for div in root.findall(".//div[@type]"):
        tipo = div.attrib.get("type", "")
        div.attrib.clear()
        classes = "documento-pretextual"
        if tipo:
            classes += f" documento-{tipo.lower()}"
        div.attrib["class"] = classes

    # a raiz <front> também vira um contêiner genérico (não é uma tag HTML válida)
    if root.tag == "front":
        root.tag = "div"
        root.attrib.clear()
        root.attrib["class"] = "elementos-pretextuais"

    return etree.tostring(root, encoding="unicode", method="html")