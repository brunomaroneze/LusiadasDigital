# Código gerado pelo ChatGPT para comparar duas versões do texto dos Lusíadas.

import xml.etree.ElementTree as ET
import re
import csv

def limpar_texto(texto):
    """Remove espaços extras e normaliza quebras de linha no texto."""
    texto = re.sub(r"\s+", " ", texto)  # Substitui múltiplos espaços por um único
    return texto.strip()

def extrair_versos(arquivo):
    """Extrai os versos dos arquivos TEI-XML e retorna um dicionário no formato {(estrofe, verso): texto} """
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
    
    return versos

def comparar_arquivos(arquivo1, arquivo2, saida):
    versos1 = extrair_versos(arquivo1)
    versos2 = extrair_versos(arquivo2)
    
    diferencas = []
    
    for chave in sorted(versos1.keys(), key=lambda x: (int(x[0]) if isinstance(x[0], str) and x[0].isdigit() else x[0], x[1])):  # Ordenação numérica
        v1 = versos1[chave]
        v2 = versos2[chave]
        
        if v1 != v2:
            diferencas.append([f"Estrofe {chave[0]}, verso {chave[1]}", v1, v2])
    
    with open(saida, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Estrofe e Verso", "Versão 1", "Versão 2"])
        writer.writerows(diferencas)
    
    print(f"Comparação concluída. Diferenças salvas em {saida}")

# Exemplo de uso
arquivo1 = "LusiadasDireita.xml"
arquivo2 = "LusiadasEsquerda.xml"
saida = "diferencas.csv"
comparar_arquivos(arquivo1, arquivo2, saida)
