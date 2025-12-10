<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    exclude-result-prefixes="tei">

  <xsl:output method="html" indent="yes" />

  <!-- Template principal -->
  <xsl:template match="/">
    <html>
      <head>
        <title>Os Lusíadas - Versões Combinadas</title>
        <style>
          .estrofe { margin-bottom: 20px; }
          .dialog { display: none; margin-top: 10px; padding: 10px; background: #f0f0f0; }
        </style>
        <script>
          function toggleDialog(id) {
            var dialog = document.getElementById(id);
            if (dialog.style.display === "none") {
              dialog.style.display = "block";
            } else {
              dialog.style.display = "none";
            }
          }
        </script>
      </head>
      <body>
        <h1>Os Lusíadas - Versões Combinadas</h1>
        <xsl:apply-templates select="//tei:lg" />
      </body>
    </html>
  </xsl:template>

  <!-- Template para estrofes -->
  <xsl:template match="tei:lg">
    <div class="estrofe">
      <xsl:apply-templates select="tei:l | tei:app" />
    </div>
    <hr/>
  </xsl:template>

  <!-- Template para versos -->
  <xsl:template match="tei:l">
    <p><xsl:value-of select="." /></p>
  </xsl:template>

  <!-- Template para variações (app) -->
  <xsl:template match="tei:app">
    <div>
      <p>
        <xsl:value-of select="tei:rdg[@wit='#V1']" />
        <button onclick="toggleDialog('dialog-{generate-id()}')">Ver V2</button>
      </p>
      <div id="dialog-{generate-id()}" class="dialog">
        <xsl:value-of select="tei:rdg[@wit='#V2']" />
      </div>
    </div>
  </xsl:template>

</xsl:stylesheet>