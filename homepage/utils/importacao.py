"""Funções compartilhadas pelos comandos de importação (importar_canto e
importar_tudo): leitura do TEI-XML, gravação de um canto no banco e
verificação de integridade dos arquivos de origem."""

from collections import Counter
from copy import deepcopy
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
# Paginação real (alinhada ao fac-símile)
# ---------------------------------------------------------------------------
#
# Nos originais (LusiadasEsquerda/Direita.xml) cada <pb facs="..."/> marca o
# início de uma página do fac-símile. As <pb> nunca caem dentro de uma <lg>,
# então cada página tem estrofes inteiras. Três páginas têm o fim de um canto
# e o começo do seguinte (cantos 7, 9 e 10 começam no meio da página): essas
# páginas são gravadas nos DOIS cantos, inteiras, para que o texto ao lado
# da imagem corresponda exatamente ao que se vê nela.
#
# O texto modernizado não tem <pb>; ele é paginado pelas mesmas estrofes da
# edição de referência (canto + número da estrofe).

# elementos de um <div type="canto"> que vão para a página; <fw> (cabeço,
# reclamo, assinatura) e <lb> soltos ficam de fora, como antes.
ELEMENTOS_DA_PAGINA = {"head", "lg"}


@dataclass
class PaginaReal:
    facs: str = ""          # caminho da imagem, como está no atributo facs
    n: str = ""             # número impresso da folha, quando houver
    partes: list = None     # [(posição do canto, [elementos])], na ordem

    def __post_init__(self):
        if self.partes is None:
            self.partes = []

    def adicionar(self, canto, elemento):
        if not self.partes or self.partes[-1][0] != canto:
            self.partes.append((canto, []))
        self.partes[-1][1].append(elemento)

    @property
    def cantos(self):
        return [c for c, _ in self.partes]

    def estrofes(self):
        """[(canto, n)] das estrofes desta página."""
        return [(c, el.get("n")) for c, els in self.partes for el in els if el.tag == "lg"]

    def tei(self):
        """TEI da página inteira: um <div type="canto"> por canto presente."""
        pagina = etree.Element("div")
        pagina.set("type", "pagina")
        if self.facs:
            pagina.set("facs", self.facs)
        for canto, elementos in self.partes:
            div = etree.SubElement(pagina, "div")
            div.set("type", "canto")
            div.set("n", str(canto))
            for el in elementos:
                div.append(deepcopy(el))
        return etree.tostring(pagina, encoding="unicode")


def tem_paginacao(root):
    body = root.find(".//body")
    return body is not None and body.find(".//pb") is not None


def paginas_por_pb(root):
    """Divide o <body> em páginas pelas <pb>. Cantos identificados pela posição."""
    paginas = []
    atual = None
    body = root.find(".//body")
    posicao = 0

    def nova(pb):
        paginas.append(PaginaReal(facs=pb.get("facs", ""), n=pb.get("n", "")))
        return paginas[-1]

    for filho in body:
        if filho.tag == "pb":
            atual = nova(filho)
        elif filho.tag == "div" and filho.get("type") == "canto":
            posicao += 1
            for el in filho:
                if el.tag == "pb":
                    atual = nova(el)
                elif el.tag in ELEMENTOS_DA_PAGINA:
                    if atual is None:
                        atual = nova(etree.Element("pb"))
                    atual.adicionar(posicao, el)
    return [p for p in paginas if p.partes]


def paginas_por_referencia(root, referencia):
    """Pagina um texto sem <pb> (o modernizado) seguindo as estrofes de `referencia`.

    Os <head> vão para a página da estrofe seguinte. Estrofes que não existem
    na referência ficam na página da estrofe anterior.
    """
    onde = {}
    for i, pagina in enumerate(referencia):
        for chave in pagina.estrofes():
            onde.setdefault(chave, i)

    paginas = [PaginaReal(facs=p.facs, n=p.n) for p in referencia]
    ultima = 0
    for posicao, div in enumerate(divs_de_canto(root), start=1):
        pendentes = []
        for el in div:
            if el.tag not in ELEMENTOS_DA_PAGINA:
                continue
            if el.tag != "lg":
                pendentes.append(el)
                continue
            ultima = onde.get((posicao, el.get("n")), ultima)
            for p in pendentes + [el]:
                paginas[ultima].adicionar(posicao, p)
            pendentes = []
        for p in pendentes:
            paginas[ultima].adicionar(posicao, p)
    return paginas


def paginas_de_cada_canto(paginas):
    """{canto: [índices das páginas em que ele aparece]}, na ordem."""
    resultado = {}
    for i, pagina in enumerate(paginas):
        for canto in pagina.cantos:
            resultado.setdefault(canto, []).append(i)
    return resultado


def gravar_paginas_reais(paginas, indices, numero_canto, versao, titulo=None):
    """Grava em PaginaTexto as páginas `indices` (globais) como 1..N do canto."""
    canto_obj, canto_criado = Canto.objects.get_or_create(
        numero=numero_canto, defaults={"titulo": titulo or f"Canto {numero_canto}"})
    criadas = atualizadas = 0
    for local, i in enumerate(indices, start=1):
        _, criado = PaginaTexto.objects.update_or_create(
            canto=canto_obj, numero=local, versao=versao,
            defaults={"tei_xml": paginas[i].tei()},
        )
        criadas += criado
        atualizadas += not criado
    return {"paginas": len(indices), "criadas": criadas, "atualizadas": atualizadas,
            "canto_criado": canto_criado}


def titulo_do_canto(div_canto, numero_canto):
    head = div_canto.find("head")
    texto = _texto(head) if head is not None else ""
    return texto or f"Canto {numero_canto}"


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
