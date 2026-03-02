from lxml import etree

def tei_para_html(tei_xml):
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(tei_xml.encode(), parser=parser)

    # remover namespace
    for elem in root.iter():
        if isinstance(elem.tag, str):
            elem.tag = etree.QName(elem).localname

    etree.cleanup_namespaces(root)

    # 🎯 pegar apenas o corpo do texto
    body = root.find(".//body")
    if body is not None:
        root = body

    # <lg> → <div class="estrofe">
    for lg in root.findall(".//lg"):
        lg.tag = "div"
        lg.attrib.clear()
        lg.attrib["class"] = "estrofe"

    # <l> → <div class="verso">
    for l in root.findall(".//l"):
        l.tag = "div"
        l.attrib.clear()
        l.attrib["class"] = "verso"

    # <lb> → <br>
    for lb in root.findall(".//lb"):
        lb.tag = "br"
        lb.attrib.clear()

    # <head> → <h3>
    for head in root.findall(".//head"):
        head.tag = "h3"

    return etree.tostring(root, encoding="unicode", method="html")
