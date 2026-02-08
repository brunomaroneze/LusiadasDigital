from lxml import etree

def tei_para_html(tei_xml):
    if not tei_xml:
        return ""

    xml = etree.XML(tei_xml.encode("utf-8"))
    xslt = etree.XML("""
    <xsl:stylesheet version="1.0"
      xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
      xmlns:tei="http://www.tei-c.org/ns/1.0">

      <xsl:template match="/">
        <div class="tei">
          <xsl:apply-templates/>
        </div>
      </xsl:template>

      <xsl:template match="tei:p">
        <p><xsl:apply-templates/></p>
      </xsl:template>

      <xsl:template match="tei:w">
        <span class="w"><xsl:apply-templates/></span>
      </xsl:template>

      <xsl:template match="text()">
        <xsl:value-of select="."/>
      </xsl:template>

    </xsl:stylesheet>
    """)

    transform = etree.XSLT(xslt)
    html = transform(xml)

    return str(html)
