from django.shortcuts import render
from django.http import Http404, JsonResponse
from django.conf import settings
from lxml import etree
import os
from .models import Canto, PaginaImagem, PaginaTexto
from .utils.tei import tei_para_html, pretextual_para_html
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

def canto_index(request, canto):
    paginas = PaginaImagem.objects.filter(canto__numero=canto).order_by("numero")
    return render(request, "poema/canto_index.html", {
        "canto": canto,
        "paginas": paginas
    })

def canto(request, canto):
    pagina_num = int(request.GET.get("p", 1))
    estrofe_alvo = request.GET.get("estrofe")

    imagem = PaginaImagem.objects.filter(canto__numero=canto, numero=pagina_num).first()
    texto_esq = PaginaTexto.objects.filter(canto__numero=canto, numero=pagina_num, versao="modernizado").first()
    texto_dir = PaginaTexto.objects.filter(canto__numero=canto, numero=pagina_num, versao="original").first()

    html_esq = tei_para_html(texto_esq.tei_xml) if texto_esq else ""
    html_dir = tei_para_html(texto_dir.tei_xml) if texto_dir else ""
    paginas = PaginaImagem.objects.filter(canto__numero=canto).order_by("numero")

    contexto = {
        "canto": canto,
        "esq": "modernizado",
        "dir": "original",
        "pagina": imagem,
        "pagina_num": pagina_num,
        "paginas": paginas,
        "html_esq": html_esq,
        "html_dir": html_dir,
        "estrofe_alvo": estrofe_alvo,
    }
    return render(request, "poema/canto.html", contexto)

def leitura(request, canto, conteudo, coluna, pagina=None):
    opcoes_validas = ["original", "modernizado", "imagem"]
    if coluna not in ["esq", "dir"] or conteudo not in opcoes_validas:
        raise Http404("Parâmetros de leitura inválidos ou página não encontrada.")

    # ponto de partida: o que a OUTRA coluna já estava mostrando (vem na
    # querystring, preservado pelos links das abas em base.html) -- sem
    # isso, trocar a aba de uma coluna resetava a outra pro padrão.
    esq = request.GET.get("esq", "modernizado")
    dir = request.GET.get("dir", "original")
    if esq not in opcoes_validas:
        esq = "modernizado"
    if dir not in opcoes_validas:
        dir = "original"

    if coluna == "esq":
        esq = conteudo
    elif coluna == "dir":
        dir = conteudo

    pagina_num = int(request.GET.get("p", 1))
    estrofe_alvo = request.GET.get("estrofe")

    imagem = PaginaImagem.objects.filter(canto__numero=canto, numero=pagina_num).first()
    texto_esq = PaginaTexto.objects.filter(canto__numero=canto, numero=pagina_num, versao=esq).first()
    texto_dir = PaginaTexto.objects.filter(canto__numero=canto, numero=pagina_num, versao=dir).first()

    html_esq = tei_para_html(texto_esq.tei_xml) if texto_esq else ""
    html_dir = tei_para_html(texto_dir.tei_xml) if texto_dir else ""
    paginas = PaginaImagem.objects.filter(canto__numero=canto).order_by("numero")

    contexto = {
        "canto": canto,
        "pagina_num": pagina_num,
        "imagem": imagem,
        "paginas": paginas,
        "esq": esq,
        "dir": dir,
        "html_esq": html_esq,
        "html_dir": html_dir,
        "estrofe_alvo": estrofe_alvo,
    }
    return render(request, "poema/canto.html", contexto)

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
