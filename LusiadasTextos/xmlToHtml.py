from lxml import etree

# Carregar o arquivo TEI e o XSLT
tei = etree.parse("LusiadasCombinado.xml")
xslt = etree.parse("transform.xsl")

# Aplicar a transformação
transform = etree.XSLT(xslt)
html = transform(tei)

# Salvar o resultado em um arquivo HTML
with open("output.html", "wb") as f:
    f.write(etree.tostring(html, pretty_print=True))