"""Funções compartilhadas pelos comandos de importação (importar_canto e
importar_tudo): leitura do TEI-XML, gravação de um canto no banco e
verificação de integridade dos arquivos de origem."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from lxml import etree

from homepage.models import Canto, PaginaTexto

# versão gravada no banco -> arquivo de origem em LusiadasTextos/
# (A = pelicano à esquerda no frontispício, B = pelicano à direita)
FONTES = [
    ("modernizado", "LusiadasModernizado.xml"),
    ("original_a", "LusiadasEsquerda.xml"),
    ("original_b", "LusiadasDireita.xml"),
]

# Estrofes de cada canto n'Os Lusíadas (1102 no total).
ESTROFES_ESPERADAS = {1: 106, 2: 113, 3: 143, 4: 104, 5: 100, 6: 99, 7: 87, 8: 99, 9: 95, 10: 156}
VERSOS_POR_ESTROFE = 8  # oitava rima de decassílabos


class ErroDeArquivo(Exception):
    """Arquivo ausente ou XML malformado."""


def carregar_xml(caminho):
    """Lê o TEI-XML e devolve a raiz já sem namespace."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroDeArquivo(f"Arquivo não encontrado: {caminho}")
    try:
        root = etree.fromstring(caminho.read_bytes(), parser=etree.XMLParser(remove_blank_text=True))
    except etree.XMLSyntaxError as erro:
        raise ErroDeArquivo(f"XML inválido em {caminho}: {erro}")

    for elem in root.iter():
        if isinstance(elem.tag, str):
            elem.tag = etree.QName(elem).localname
    etree.cleanup_namespaces(root)
    return root


def divs_de_canto(root):
    """Os <div type="canto"> na ordem do arquivo."""
    return [d for d in root.iter("div") if d.get("type") == "canto"]


def _texto(el):
    return " ".join("".join(el.itertext()).split())


def gravar_canto(div_canto, numero_canto, versao, por_pagina):
    """Grava um canto em PaginaTexto, em páginas sintéticas de N estrofes.

    ATENÇÃO: move as <lg> para fora do <div> de origem — rode a verificação de
    integridade antes de gravar.
    """
    head = div_canto.find("head")
    titulo = head.text.strip() if head is not None and head.text else f"Canto {numero_canto}"

    estrofes = div_canto.findall("lg")
    if not estrofes:
        raise ErroDeArquivo(f"Nenhuma <lg> encontrada no canto {numero_canto}.")

    canto_obj, canto_criado = Canto.objects.get_or_create(numero=numero_canto, defaults={"titulo": titulo})

    grupos = [estrofes[i:i + por_pagina] for i in range(0, len(estrofes), por_pagina)]
    criadas = atualizadas = 0
    with transaction.atomic():
        for indice, grupo in enumerate(grupos, start=1):
            div_pagina = etree.Element("div")
            div_pagina.set("type", "canto")
            div_pagina.set("n", str(numero_canto))
            if indice == 1:
                etree.SubElement(div_pagina, "head").text = titulo
            for lg in grupo:
                div_pagina.append(lg)

            _, criado = PaginaTexto.objects.update_or_create(
                canto=canto_obj, numero=indice, versao=versao,
                defaults={"tei_xml": etree.tostring(div_pagina, encoding="unicode")},
            )
            criadas += criado
            atualizadas += not criado

    return {
        "titulo": titulo, "estrofes": len(estrofes), "paginas": len(grupos),
        "criadas": criadas, "atualizadas": atualizadas, "canto_criado": canto_criado,
    }


# ---------------------------------------------------------------------------
# Verificação de integridade
# ---------------------------------------------------------------------------

@dataclass
class Problema:
    nivel: str      # "ERRO" | "AVISO" | "INFO"
    canto: int      # 0 = problema do arquivo como um todo
    mensagem: str

    def __str__(self):
        onde = f"Canto {self.canto}: " if self.canto else ""
        return f"[{self.nivel}] {onde}{self.mensagem}"


def verificar_integridade(root, esperados=ESTROFES_ESPERADAS):
    """Procura problemas no arquivo de origem. Não altera nada.

    Os cantos são identificados pela POSIÇÃO no arquivo (1º <div> = canto 1...),
    não pelo atributo n, que em alguns arquivos está errado.
    """
    problemas = []
    divs = divs_de_canto(root)
    total_esperado = len(esperados)

    if len(divs) < total_esperado:
        faltam = ", ".join(str(n) for n in range(len(divs) + 1, total_esperado + 1))
        problemas.append(Problema("INFO", 0, f"arquivo parcial: tem {len(divs)} de {total_esperado} cantos (faltam: {faltam})."))
    elif len(divs) > total_esperado:
        problemas.append(Problema("ERRO", 0, f"tem {len(divs)} cantos, mais que os {total_esperado} esperados."))

    for posicao, div in enumerate(divs, start=1):
        if posicao > total_esperado:
            break
        n_attr = div.get("n")
        if n_attr != str(posicao):
            problemas.append(Problema(
                "AVISO", posicao,
                f'o <div> na posição {posicao} está marcado n="{n_attr}"; será importado como canto {posicao}.'))

        estrofes = div.findall("lg")
        parcial = len(divs) < total_esperado and posicao == len(divs)
        if len(estrofes) != esperados[posicao]:
            nivel = "INFO" if (parcial or len(estrofes) < esperados[posicao] and len(divs) < total_esperado) else "AVISO"
            problemas.append(Problema(
                nivel, posicao, f"{len(estrofes)} estrofes (esperado: {esperados[posicao]})."))

        # numeração das estrofes
        numeros = []
        for lg in estrofes:
            try:
                numeros.append(int(lg.get("n")))
            except (TypeError, ValueError):
                problemas.append(Problema("ERRO", posicao, f'estrofe sem número válido (n="{lg.get("n")}"): "{_texto(lg)[:40]}…"'))
        for n, vezes in sorted(Counter(numeros).items()):
            if vezes > 1:
                problemas.append(Problema("ERRO", posicao, f"número de estrofe repetido: {n} aparece {vezes} vezes."))
        conhecidos = set(numeros)
        faltantes = [n for n in range(1, max(numeros, default=0) + 1) if n not in conhecidos]
        if faltantes:
            problemas.append(Problema("AVISO", posicao, f"lacuna na numeração: falta(m) {', '.join(map(str, faltantes[:10]))}."))

        # versos por estrofe e versos vazios
        for lg in estrofes:
            versos = lg.findall("l")
            n = lg.get("n")
            if len(versos) != VERSOS_POR_ESTROFE:
                primeiro = _texto(versos[0])[:45] if versos else ""
                dica = ""
                if len(versos) == 1:
                    dica = " Parece fragmento/reclamo da edição antiga: se for, desloca a numeração das estrofes seguintes."
                elif len(versos) > VERSOS_POR_ESTROFE:
                    dica = " Pode haver um título ou verso a mais na estrofe."
                problemas.append(Problema(
                    "AVISO", posicao,
                    f'estrofe {n} tem {len(versos)} verso(s) (esperado: {VERSOS_POR_ESTROFE}): "{primeiro}…".{dica}'))
            vazios = sum(1 for v in versos if not _texto(v))
            if vazios:
                problemas.append(Problema("AVISO", posicao, f"estrofe {n} tem {vazios} verso(s) vazio(s)."))

    return problemas
