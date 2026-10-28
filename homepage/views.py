from django.shortcuts import render
from django.db.models import Max
from django.http import Http404, JsonResponse
from django.conf import settings
from lxml import etree
import os
from .models import Canto, PaginaImagem, PaginaTexto
from .utils.tei import tei_para_html, tei_para_html_comparado, pretextual_para_html
from .utils.indice_estrofes import construir_indice_estrofes

def homepage(request):
    return render(request, "homepage.html")

def sobre(request):
    return render(request, "sobre.html")

def autor(request):
    return render(request, "autor.html")

def pretextuais(request):
    """
    Mostra os elementos pré-textuais da edição de 1572 (folha de rosto,
    alvará régio e licença do Santo Ofício), lidos direto do arquivo
    fonte LusiadasDireita.xml -- não depende do banco, então não requer
    nenhuma importação prévia. Falha graciosamente (mostra um aviso em
    vez de derrubar a página) se o arquivo não existir ou estiver
    malformado.
    """
    caminho = os.path.join(settings.BASE_DIR, "LusiadasTextos", "LusiadasDireita.xml")
    html_pretextual = ""
    erro = None

    try:
        parser_xml = etree.XMLParser(remove_blank_text=True)
        with open(caminho, "rb") as f:
            root = etree.parse(f, parser=parser_xml).getroot()

        for elem in root.iter():
            if isinstance(elem.tag, str):
                elem.tag = etree.QName(elem).localname
        etree.cleanup_namespaces(root)

        front = root.find(".//front")
        if front is not None:
            tei_xml_front = etree.tostring(front, encoding="unicode")
            html_pretextual = pretextual_para_html(tei_xml_front)
        else:
            erro = "Não encontrei a seção de elementos pré-textuais no arquivo fonte."
    except FileNotFoundError:
        erro = "Arquivo fonte dos elementos pré-textuais não encontrado."
    except etree.XMLSyntaxError:
        erro = "O arquivo fonte dos elementos pré-textuais está com XML inválido."

    return render(request, "pretextual.html", {
        "titulo": "Elementos pré-textuais",
        "css_extra": "css/pretextual.css",
        "html_pretextual": html_pretextual,
        "erro": erro,
    })

# Opções de leitura disponíveis nas abas de cada coluna (slug, rótulo).
# O slug é o que vai na URL; o rótulo é o que aparece para o leitor.
ABAS_LEITURA = [
    ("modernizado", "Versão modernizada"),
    ("original_a", "Versão original A"),
    ("original_b", "Versão original B"),
    ("imagem_a", "Imagem A"),
    ("imagem_b", "Imagem B"),
]
OPCOES_VALIDAS = [slug for slug, _ in ABAS_LEITURA]

# URLs antigas (/leitura/original/..., /imagem/...) continuam funcionando
ALIASES_LEGADOS = {"original": "original_a", "imagem": "imagem_a"}
PADRAO_ESQ = "modernizado"
PADRAO_DIR = "original_a"


def _normalizar(valor, padrao):
    valor = ALIASES_LEGADOS.get(valor, valor)
    if valor in OPCOES_VALIDAS:
        return valor
    return padrao


def _montar_coluna(canto, pagina_num, opcao):
    """Devolve (tei_xml, pagina_imagem) de uma coluna, conforme a opção escolhida."""
    if opcao.startswith("imagem_"):
        edicao = opcao.split("_")[1].upper()
        imagem = PaginaImagem.objects.filter(
            canto__numero=canto, numero=pagina_num, edicao=edicao
        ).first()
        return "", imagem
    texto = PaginaTexto.objects.filter(
        canto__numero=canto, numero=pagina_num, versao=opcao
    ).first()
    return (texto.tei_xml if texto else ""), None


def _total_paginas(canto):
    """Maior número de página cadastrado para o canto (texto ou imagem)."""
    maior_imagem = PaginaImagem.objects.filter(canto__numero=canto).aggregate(m=Max("numero"))["m"] or 0
    maior_texto = PaginaTexto.objects.filter(canto__numero=canto).aggregate(m=Max("numero"))["m"] or 0
    return max(maior_imagem, maior_texto)


def _renderizar_leitura(request, canto, esq, dir, pagina=None):
    # a página vem da URL (/leitura/.../<pagina>/) ou, se não houver, de ?p=
    try:
        pagina_num = int(pagina if pagina is not None else request.GET.get("p", 1))
    except (TypeError, ValueError):
        pagina_num = 1

    total = _total_paginas(canto)
    pagina_num = max(1, min(pagina_num, total)) if total else 1
    estrofe_alvo = request.GET.get("estrofe")

    tei_esq, imagem_esq = _montar_coluna(canto, pagina_num, esq)
    tei_dir, imagem_dir = _montar_coluna(canto, pagina_num, dir)

    # Duas versões de texto diferentes lado a lado: dá para comparar palavra
    # a palavra (o leitor liga o realce com o botão "Realçar diferenças").
    pode_comparar = not esq.startswith("imagem_") and not dir.startswith("imagem_") and esq != dir
    if pode_comparar:
        html_esq, html_dir, total_diferencas = tei_para_html_comparado(tei_esq, tei_dir)
    else:
        html_esq = tei_para_html(tei_esq) if tei_esq else ""
        html_dir = tei_para_html(tei_dir) if tei_dir else ""
        total_diferencas = 0

    contexto = {
        "canto": canto,
        "pagina_num": pagina_num,
        "total_paginas": total,
        "pagina_anterior": pagina_num - 1 if pagina_num > 1 else None,
        "pagina_seguinte": pagina_num + 1 if pagina_num < total else None,
        "abas": ABAS_LEITURA,
        "esq": esq,
        "dir": dir,
        "html_esq": html_esq,
        "html_dir": html_dir,
        "pode_comparar": pode_comparar,
        "tem_texto": not (esq.startswith("imagem_") and dir.startswith("imagem_")),
        "total_diferencas": total_diferencas,
        "imagem_esq": imagem_esq,
        "imagem_dir": imagem_dir,
        "estrofe_alvo": estrofe_alvo,
    }
    return render(request, "poema/canto.html", contexto)


def canto_index(request, canto):
    paginas = PaginaImagem.objects.filter(canto__numero=canto, edicao="A").order_by("numero")
    return render(request, "poema/canto_index.html", {
        "canto": canto,
        "paginas": paginas
    })


def canto(request, canto):
    return _renderizar_leitura(request, canto, PADRAO_ESQ, PADRAO_DIR)


def leitura(request, canto, conteudo, coluna, pagina=None):
    conteudo = ALIASES_LEGADOS.get(conteudo, conteudo)
    if coluna not in ["esq", "dir"] or conteudo not in OPCOES_VALIDAS:
        raise Http404("Parâmetros de leitura inválidos ou página não encontrada.")

    # ponto de partida: o que a OUTRA coluna já estava mostrando (vem na
    # querystring, preservado pelos links das abas em base.html)
    esq = _normalizar(request.GET.get("esq"), PADRAO_ESQ)
    dir = _normalizar(request.GET.get("dir"), PADRAO_DIR)

    if coluna == "esq":
        esq = conteudo
    else:
        dir = conteudo

    return _renderizar_leitura(request, canto, esq, dir, pagina)


def indice_estrofes_view(request, canto):
    """
    Rota de teste/depuração -- NAO usada por nenhuma pagina ainda.
    Devolve em JSON o mapa {estrofe: pagina} para o canto pedido, para
    conferirmos que o indice bate certo antes de construir a interface
    (a aba lateral de navegacao) em cima dele.

    Exemplo: /canto/1/estrofes/?versao=modernizado
    """
    versao = request.GET.get("versao", "modernizado")
    indice = construir_indice_estrofes(canto_numero=canto, versao=versao)
    return JsonResponse({
        "canto": canto,
        "versao": versao,
        "total_estrofes_encontradas": len(indice),
        "indice": indice,
    })


def listar_cantos_view(request):
    """
    Lista os cantos já cadastrados (numero + titulo), em JSON.
    Usada pela barra de navegação por estrofe (barra-estrofes.js) para montar o
    primeiro passo do menu ("escolha o canto"). Não altera nem depende
    de nenhuma view existente.
    """
    cantos = list(Canto.objects.order_by("numero").values("numero", "titulo"))
    return JsonResponse({"cantos": cantos})
