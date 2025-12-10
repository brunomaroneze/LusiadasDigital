import xml.etree.ElementTree as ET
import re

def limpar_texto(texto):
    """Remove espaços extras e normaliza quebras de linha no texto."""
    texto = re.sub(r"\s+", " ", texto)  # Substitui múltiplos espaços por um único
    return texto.strip()

def extrair_versos(arquivo):
    """Extrai os versos dos arquivos TEI-XML e retorna um dicionário no formato {(estrofe, verso): texto}."""
    tree = ET.parse(arquivo)
    root = tree.getroot()
    
    # Capturar namespace automaticamente
    ns = "" if root.tag[0] != "{" else root.tag.split("}")[0] + "}"
    
    versos = {}
    
    for lg in root.findall(f".//{ns}lg"):
        num_estrofe = lg.get("n", "?")
        try:
            num_estrofe = int(num_estrofe)  # Converter para número se possível
        except ValueError:
            pass  # Se não for possível, mantém como string
        
        for idx, l in enumerate(lg.findall(f"{ns}l"), start=1):
            texto = "".join(l.itertext()).strip()
            texto = limpar_texto(texto)  # Normaliza o texto
            versos[(num_estrofe, idx)] = texto
    
    return versos, ns

def gerar_tei_combinado(versos1, versos2, ns, saida):
    """Gera um arquivo TEI combinado com as duas versões, usando <app> e <rdg> para marcar diferenças."""
    # Cria a estrutura básica do TEI
    tei = ET.Element(f"{ns}TEI")
    header = ET.SubElement(tei, f"{ns}teiHeader")
    text = ET.SubElement(tei, f"{ns}text")
    body = ET.SubElement(text, f"{ns}body")
    
    # Adiciona metadados básicos ao header (opcional)
    file_desc = ET.SubElement(header, f"{ns}fileDesc")
    title_stmt = ET.SubElement(file_desc, f"{ns}titleStmt")
    title = ET.SubElement(title_stmt, f"{ns}title")
    title.text = "Os Lusíadas - Versões Combinadas"
    author = ET.SubElement(title_stmt, f"{ns}author")
    author.text = "Luís de Camões"
    
    # Variável para controlar a estrofe atual
    estrofe_atual = None
    lg = None
    
    # Itera sobre os versos e adiciona ao corpo do TEI
    for chave in sorted(versos1.keys(), key=lambda x: (int(x[0]) if isinstance(x[0], str) and x[0].isdigit() else x[0], x[1])):
        num_estrofe = chave[0]
        v1 = versos1[chave]
        v2 = versos2[chave]
        
        # Cria um novo <lg> para cada estrofe
        if num_estrofe != estrofe_atual:
            lg = ET.SubElement(body, f"{ns}lg", n=str(num_estrofe))
            estrofe_atual = num_estrofe
        
        # Adiciona o verso
        if v1 != v2:
            # Se houver diferença, usa <app> dentro de <l>
            l = ET.SubElement(lg, f"{ns}l")
            app = ET.SubElement(l, f"{ns}app")
            rdg1 = ET.SubElement(app, f"{ns}rdg", wit="#V1")
            rdg1.text = v1
            rdg2 = ET.SubElement(app, f"{ns}rdg", wit="#V2")
            rdg2.text = v2
        else:
            # Se não houver diferença, adiciona o verso diretamente
            l = ET.SubElement(lg, f"{ns}l")
            l.text = v1
    
    # Salva o arquivo TEI
    tree = ET.ElementTree(tei)
    tree.write(saida, encoding="utf-8", xml_declaration=True)
    print(f"Arquivo TEI combinado salvo em {saida}")

# Exemplo de uso
arquivo1 = "LusiadasDireita.xml"
arquivo2 = "LusiadasEsquerda.xml"
saida = "LusiadasCombinado.xml"

# Extrai os versos
versos1, ns1 = extrair_versos(arquivo1)
versos2, ns2 = extrair_versos(arquivo2)

# Gera o arquivo TEI combinado
gerar_tei_combinado(versos1, versos2, ns1, saida)