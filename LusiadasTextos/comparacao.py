"""Compara duas edições TEI-XML d'Os Lusíadas verso a verso e grava um CSV
com os versos que diferem (útil para conferência fora do site).

Uso (na pasta LusiadasTextos):
    python comparacao.py [arquivo1.xml] [arquivo2.xml] [saida.csv]
Sem argumentos, compara LusiadasDireita.xml com LusiadasEsquerda.xml.

Observações:
- A chave de comparação é (canto, estrofe, verso). Antes ela ignorava o canto,
  então estrofes de cantos diferentes se sobrescreviam, e a comparação quebrava
  (KeyError) quando uma edição tinha cantos que a outra não tem.
- Versos que só existem em uma das edições aparecem no CSV com a outra coluna vazia.
- O site faz a comparação palavra a palavra por conta própria
  (homepage/utils/diferencas.py); este script é só para conferência.
"""
import csv
import re
import sys
import xml.etree.ElementTree as ET


def limpar_texto(texto):
    """Remove espaços extras e normaliza quebras de linha no texto."""
    return re.sub(r"\s+", " ", texto).strip()


def extrair_versos(arquivo):
    """Devolve {(canto, estrofe, verso): texto} de um arquivo TEI-XML."""
    root = ET.parse(arquivo).getroot()
    ns = "" if root.tag[0] != "{" else root.tag.split("}")[0] + "}"

    versos = {}
    for canto in root.findall(f".//{ns}div[@type='canto']"):
        num_canto = int(canto.get("n", 0))
        for lg in canto.findall(f".//{ns}lg"):
            try:
                num_estrofe = int(lg.get("n", 0))
            except ValueError:
                continue
            for idx, l in enumerate(lg.findall(f"{ns}l"), start=1):
                versos[(num_canto, num_estrofe, idx)] = limpar_texto("".join(l.itertext()))
    return versos


def comparar_arquivos(arquivo1, arquivo2, saida):
    versos1 = extrair_versos(arquivo1)
    versos2 = extrair_versos(arquivo2)

    diferencas = []
    for chave in sorted(set(versos1) | set(versos2)):
        v1, v2 = versos1.get(chave, ""), versos2.get(chave, "")
        if v1 != v2:
            canto, estrofe, verso = chave
            diferencas.append([f"Canto {canto}, estrofe {estrofe}, verso {verso}", v1, v2])

    with open(saida, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Canto, estrofe e verso", "Versão 1", "Versão 2"])
        writer.writerows(diferencas)

    print(f"Comparação concluída: {len(diferencas)} versos diferem. Salvo em {saida}")


if __name__ == "__main__":
    args = sys.argv[1:]
    comparar_arquivos(
        args[0] if len(args) > 0 else "LusiadasDireita.xml",
        args[1] if len(args) > 1 else "LusiadasEsquerda.xml",
        args[2] if len(args) > 2 else "diferencas.csv",
    )
